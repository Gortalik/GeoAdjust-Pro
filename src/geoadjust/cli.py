"""CLI интерфейс для пакетной обработки"""
import argparse
import sys
from pathlib import Path

from loguru import logger


def run_cli(args: list):
    """Запуск CLI интерфейса с аргументами командной строки"""
    parser = argparse.ArgumentParser(
        prog="geoadjust",
        description="GeoAdjust Pro - уравнивание геодезических сетей"
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Файл измерений (GSI, SDR, XLSX, CSV)"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("report.txt"),
        help="Файл отчёта (по умолчанию report.txt)"
    )

    parser.add_argument(
        "-c", "--class",
        dest="network_class",
        choices=["1", "2", "3", "4", "tech"],
        default="4",
        help="Класс нивелирования (по умолчанию 4)"
    )

    parser.add_argument(
        "-f", "--fixed",
        nargs="+",
        metavar="PUNKT:H",
        help="Фиксированные пункты в формате PUNKT:ВЫСОТА"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробный вывод"
    )

    parsed = parser.parse_args(args)

    # Настройка логирования
    from geoadjust.utils.paths import setup_logging
    log_level = "DEBUG" if parsed.verbose else "INFO"
    setup_logging()
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    # Парсинг фиксированных пунктов
    fixed_points = {}
    if parsed.fixed:
        for item in parsed.fixed:
            try:
                punkt, height = item.split(":")
                fixed_points[punkt.strip()] = float(height.strip())
            except ValueError:
                logger.error(f"Неверный формат фиксированного пункта: {item}")
                sys.exit(1)

    # Импорт данных
    logger.info(f"📂 Загрузка файла: {parsed.input_file}")

    suffix = parsed.input_file.suffix.upper()
    if suffix == ".GSI":
        from geoadjust.io import GSIParser
        parser_obj = GSIParser()
    elif suffix == ".DAT":
        from geoadjust.io import SDRParser
        parser_obj = SDRParser()
    elif suffix in (".XLSX", ".CSV"):
        from geoadjust.io import OfficeParser
        parser_obj = OfficeParser()
    else:
        logger.error(f"Неподдерживаемый формат: {suffix}")
        sys.exit(1)

    observations = parser_obj.parse(parsed.input_file)

    # Валидация
    from geoadjust.io.validators import validate_and_clean
    observations, report = validate_and_clean(observations)

    logger.info(
        f"✅ Загружено: {report['final']} наблюдений "
        f"(удалено дубликатов: {report['removed_duplicates']}, "
        f"самопетель: {report['removed_self_loops']})"
    )

    if not observations:
        logger.error("Нет наблюдений после валидации")
        sys.exit(1)

    # Уравнивание
    from geoadjust.core.adjustment import AdjustmentEngine, InstrumentSpec

    spec = InstrumentSpec(class_code=parsed.network_class)
    engine = AdjustmentEngine(spec=spec)

    result = engine.adjust_heights(observations, fixed_points)

    logger.info("📊 Результаты:")
    logger.info(f"  σ₀ = {result.sigma_0 * 1000:.3f} мм")
    logger.info(f"  Итераций: {result.iterations}")
    logger.info(f"  Статус: {result.status}")

    # Нормативный контроль
    from geoadjust.validation import NormativeChecker

    total_length = sum(obs.distance for obs in observations) / 1000  # км
    norm_result = NormativeChecker.check_leveling_network(
        sigma_0_m=result.sigma_0,
        route_length_km=total_length,
        closure_m=0.0,  # Требуется вычисление невязок по ходам
        class_code=parsed.network_class
    )

    if not norm_result["all_ok"]:
        logger.warning("⚠️ Сеть не соответствует нормативам выбранного класса")

    # Экспорт
    from geoadjust.gui.reporting.exporter import ReportExporter

    ReportExporter.export_txt(
        {
            "sigma_0": result.sigma_0,
            "iterations": result.iterations,
            "status": result.status,
            "corrections": result.corrections.tolist(),
            "residuals": result.residuals.tolist(),
            "adjusted_heights": result.adjusted_heights,
        },
        observations,
        parsed.output
    )

    logger.info(f"💾 Отчёт сохранён: {parsed.output}")

    return 0 if result.status == "converged" and norm_result["all_ok"] else 1
