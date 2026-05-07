"""Точка входа для запуска через python -m geoadjust"""
import sys
from pathlib import Path
from loguru import logger

def main():
    """Основная функция запуска CLI интерфейса"""
    from geoadjust.utils.paths import setup_logging
    
    # Настройка логирования
    log_dir = Path(__file__).parent.parent / "logs"
    setup_logging(log_dir)
    
    logger.info("🚀 GeoAdjust Pro v1.0.0 запущен")
    
    # Если переданы аргументы - режим CLI, иначе GUI
    if len(sys.argv) > 1:
        from geoadjust.cli import run_cli
        run_cli(sys.argv[1:])
    else:
        from geoadjust.gui.main_window import MainWindow
        from PyQt5.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        app.setApplicationName("GeoAdjust Pro")
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())

if __name__ == "__main__":
    main()
