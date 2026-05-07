"""Базовый класс для фоновых воркеров PyQt5"""
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger

class BaseWorker(QThread):
    """
    Базовый класс для фоновых задач с обработкой ошибок и безопасным завершением.
    
    Сигналы:
        started: Запуск задачи
        progress(int, str): Прогресс (процент, сообщение)
        finished(dict): Результаты
        error(str): Сообщение об ошибке
        log_message(str): Лог для вывода в UI
    """
    started = pyqtSignal()
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = True
    
    def run(self):
        """Шаблонный метод выполнения задачи"""
        try:
            self.started.emit()
            self._do_work()
        except Exception as e:
            logger.error(f"Ошибка воркера: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.is_running = False
    
    def _do_work(self):
        """Переопределить в подклассе для выполнения работы"""
        raise NotImplementedError("Подкласс должен реализовать _do_work()")
    
    def stop(self):
        """Безопасная остановка воркера"""
        self.is_running = False
        self.wait(1000)  # Ждём до 1 секунды
        if self.isRunning():
            self.terminate()
