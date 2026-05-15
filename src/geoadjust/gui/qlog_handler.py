# src/geoadjust/gui/qlog_handler.py
"""Потокобезопасный обработчик логов для PyQt5"""
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QDateTime
from typing import Optional

class QLogHandler(logging.Handler, QObject):
    """
    Обработчик логов для PyQt5.
    Потокобезопасно передаёт записи в QTextEdit через сигналы.
    """
    log_signal = pyqtSignal(str, str)  # (formatted_text, level)

    def __init__(self, parent: Optional[QObject] = None):
        logging.Handler.__init__(self)
        QObject.__init__(self, parent)
        self.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(message)s',
                                            datefmt='%H:%M:%S'))

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            # Добавляем таймстамп GUI для точности отображения
            gui_ts = QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
            formatted = f"[{gui_ts}] {msg}"
            self.log_signal.emit(formatted, record.levelname)
        except Exception:
            self.handleError(record)

    def attach_to_widget(self, text_edit):
        """Привязывает обработчик к QTextEdit в главном окне."""
        self.log_signal.connect(lambda text, level: text_edit.append(text))
        
    def clear(self, text_edit):
        text_edit.clear()
