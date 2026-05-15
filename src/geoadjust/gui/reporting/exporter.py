"""Экспорт отчётов в TXT, RTF, CSV форматы"""
import datetime
from pathlib import Path
from typing import Dict, List

from loguru import logger


class ReportExporter:
    """Экспорт результатов уравнивания в различные форматы"""

    @staticmethod
    def export_txt(
        result: Dict,
        observations: List,
        output_path: Path
    ):
        """
        Формирование ведомости уравнивания в текстовом формате.
        
        Args:
            result: Результаты уравнивания (sigma_0, corrections, residuals и т.д.)
            observations: Список наблюдений
            output_path: Путь к выходному файлу
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("ВЕДОМОСТЬ УРАВНИВАНИЯ ВЫСОТНОЙ СЕТИ\n")
            f.write(f"Дата формирования: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write("=" * 70 + "\n\n")

            # Основные результаты
            f.write("ОСНОВНЫЕ РЕЗУЛЬТАТЫ:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Средняя квадратическая ошибка единицы веса (σ₀): {result.get('sigma_0', 0.0):.6f} м\n")
            f.write(f"Количество итераций: {result.get('iterations', 0)}\n")
            f.write(f"Статус решения: {result.get('status', 'N/A')}\n")
            f.write(f"Число наблюдений: {len(observations)}\n")
            f.write(f"Число пунктов: {len(result.get('adjusted_heights', {}))}\n\n")

            # Уравненные высоты
            adjusted = result.get('adjusted_heights', {})
            if adjusted:
                f.write("-" * 70 + "\n")
                f.write(f"{'№':<5} | {'Пункт':<15} | {'H (м)':<15} | {'m_H (мм)':<10}\n")
                f.write("-" * 70 + "\n")

                for i, (punkt_id, height) in enumerate(sorted(adjusted.items())):
                    # Попытка получить точность из ковариации
                    m_h = 0.0  # Заглушка, в реальном коде брать из covariance_matrix
                    f.write(f"{i+1:<5} | {punkt_id:<15} | {height:>12.4f}   | {m_h:>8.2f}\n")

                f.write("-" * 70 + "\n\n")

            # Невязки
            residuals = result.get('residuals', [])
            if residuals and len(residuals) > 0:
                f.write("-" * 70 + "\n")
                f.write(f"{'№':<5} | {'Станция':<12} | {'Цель':<12} | {'v (мм)':<10}\n")
                f.write("-" * 70 + "\n")

                for i, (obs, v) in enumerate(zip(observations[:50], residuals)):
                    v_mm = v * 1000  # перевод в мм
                    f.write(f"{i+1:<5} | {obs.station_id:<12} | {obs.target_id:<12} | {v_mm:>+8.2f}\n")

                if len(observations) > 50:
                    f.write(f"... и ещё {len(observations) - 50} наблюдений\n")

                f.write("-" * 70 + "\n\n")

            f.write("=" * 70 + "\n")
            f.write("Конец ведомости\n")

        logger.info(f"📄 TXT отчёт сохранён: {output_path}")

    @staticmethod
    def export_rtf(
        result: Dict,
        observations: List,
        output_path: Path
    ):
        """Упрощённый экспорт в RTF формат"""
        header = r"{\rtf1\ansi\deff0{\fonttbl{\f0\fswiss Arial;}}\f0\fs24"

        body = "\\b Ведомость уравнивания высотной сети \\b0\\par\\par\n"
        body += f"Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\\par\\par\n"
        body += f"σ₀ = {result.get('sigma_0', 0.0):.6f} м\\par\n"
        body += f"Итераций: {result.get('iterations', 0)}\\par\n"
        body += f"Статус: {result.get('status', 'N/A')}\\par\\par\n"

        # Таблица высот
        adjusted = result.get('adjusted_heights', {})
        if adjusted:
            body += "\\b Уравнённые высоты \\b0\\par\\par\n"
            body += r"\trowdef\cellx3000\cellx6000\cellx9000\par\n"

            for i, (punkt_id, height) in enumerate(sorted(adjusted.items())):
                body += f"\\intbl {i+1}\\cell {punkt_id}\\cell {height:.4f}\\cell\\row\n"

        footer = r"\par}"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + body + footer)

        logger.info(f"📄 RTF отчёт сохранён: {output_path}")

    @staticmethod
    def export_csv(
        result: Dict,
        observations: List,
        output_path: Path
    ):
        """Экспорт в CSV формат для импорта в Excel/GIS"""
        import csv

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")

            # Заголовок
            writer.writerow(["Тип", "ID", "Значение", "Поправка", "СКП"])

            # Уравнённые высоты
            adjusted = result.get('adjusted_heights', {})
            for punkt_id, height in sorted(adjusted.items()):
                writer.writerow(["HEIGHT", punkt_id, f"{height:.6f}", "", ""])

            # Невязки
            residuals = result.get('residuals', [])
            for i, (obs, v) in enumerate(zip(observations, residuals)):
                writer.writerow([
                    "RESIDUAL",
                    f"{obs.station_id}-{obs.target_id}",
                    f"{obs.value:.6f}",
                    f"{v * 1000:.3f}",  # мм
                    ""
                ])

        logger.info(f"📄 CSV отчёт сохранён: {output_path}")
