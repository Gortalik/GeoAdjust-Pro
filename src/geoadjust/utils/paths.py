"""Утилиты для работы с путями и логирования"""
from pathlib import Path
from loguru import logger
import sys

def setup_logging(log_dir: Path | str = "logs"):
    """Настройка логирования с ротацией файлов"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger.remove()  # Убираем stdout по умолчанию
    
    # Логирование в файл с ротацией
    logger.add(
        log_path / "geoadjust_{time:YYYY-MM-DD}.log",
        rotation="5 MB",
        retention="30 days",
        level="DEBUG",
        format="{time:HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8"
    )
    
    # Дублирование в консоль
    logger.add(sys.stderr, level="INFO")
    logger.info(f"Логирование инициализировано: {log_path.absolute()}")

def get_resource_path(relative_path: str) -> Path:
    """Получение пути к ресурсу (иконки, шаблоны) независимо от способа запуска"""
    if hasattr(sys, '_MEIPASS'):
        # Запуск из PyInstaller bundle
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent.parent / relative_path
