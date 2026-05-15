"""
Виджет журнала событий для GeoAdjust Pro

Обеспечивает потокобезопасное логирование в GUI через PyQt5 сигналы.
Поддерживает фильтрацию по уровням, цветовое кодирование и сохранение.
"""

import logging
from datetime import datetime
from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QDateTime
from PyQt5.QtGui import QTextCursor, QColor


class QLogHandler(logging.Handler, QObject):
    """
    Потокобезопасный обработчик логов для PyQt5.
    
    Перехватывает записи Python logging и передаёт их в GUI через сигналы.
    Работает в любых потоках без блокировки интерфейса.
    
    Сигналы:
    ---------
    log_signal : pyqtSignal(str, str)
        Сигнал с форматированным сообщением и уровнем (text, level)
    """
    log_signal = pyqtSignal(str, str)  # (formatted_text, level)

    def __init__(self, parent: Optional[QObject] = None):
        logging.Handler.__init__(self)
        QObject.__init__(self, parent)
        
        # Формат с точным временем
        self.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] %(message)s',
            datefmt='%H:%M:%S'
        ))

    def emit(self, record: logging.LogRecord):
        """
        Эмитент записи лога.
        
        Форматирует запись и отправляет через pyqtSignal в главный поток.
        """
        try:
            msg = self.format(record)
            # Добавляем таймстамп GUI для точности до миллисекунд
            gui_ts = QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
            formatted = f"[{gui_ts}] {msg}"
            self.log_signal.emit(formatted, record.levelname)
        except Exception:
            self.handleError(record)

    def attach_to_widget(self, text_edit: QTextEdit):
        """
        Привязывает обработчик к QTextEdit в главном окне.
        
        Параметры:
        -----------
        text_edit : QTextEdit
            Виджет для отображения логов
        """
        self.log_signal.connect(lambda text, level: text_edit.append(text))
        
    def clear(self, text_edit: QTextEdit):
        """Очищает виджет логов"""
        text_edit.clear()


class LogWidget(QWidget):
    """Виджет журнала событий"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Текстовое поле журнала
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Consolas")
        self.log_text.setFontPointSize(9)
        
        layout.addWidget(self.log_text)
        
        # Создание обработчика логов
        self.log_handler = None
        self._setup_logging()
        
        # Панель инструментов - компактная
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(2)
        
        clear_btn = QPushButton("Очистить")
        clear_btn.clicked.connect(self.clear_log)
        clear_btn.setMaximumHeight(24)
        toolbar.addWidget(clear_btn)
        
        save_btn = QPushButton("Сохранить...")
        save_btn.clicked.connect(self.save_log)
        save_btn.setMaximumHeight(24)
        toolbar.addWidget(save_btn)
        
        toolbar.addStretch()
        
        # Фильтры - компактные
        self.filter_info_check = QPushButton("INFO")
        self.filter_info_check.setCheckable(True)
        self.filter_info_check.setChecked(True)
        self.filter_info_check.setMaximumWidth(45)
        self.filter_info_check.setMaximumHeight(24)
        toolbar.addWidget(self.filter_info_check)
        
        self.filter_warning_check = QPushButton("WARN")
        self.filter_warning_check.setCheckable(True)
        self.filter_warning_check.setChecked(True)
        self.filter_warning_check.setMaximumWidth(45)
        self.filter_warning_check.setMaximumHeight(24)
        toolbar.addWidget(self.filter_warning_check)
        
        self.filter_error_check = QPushButton("ERROR")
        self.filter_error_check.setCheckable(True)
        self.filter_error_check.setChecked(True)
        self.filter_error_check.setMaximumWidth(45)
        self.filter_error_check.setMaximumHeight(24)
        toolbar.addWidget(self.filter_error_check)
        
        layout.addLayout(toolbar)
        
        # Установка минимального размера виджета
        self.setMinimumSize(200, 100)
    
    def _setup_logging(self):
        """Настройка перехвата логов Python"""
        self.log_handler = QLogHandler()
        self.log_handler.log_signal.connect(self._handle_log_message)
        
        # Добавление обработчика к логгеру geoadjust
        geoadjust_logger = logging.getLogger("geoadjust")
        geoadjust_logger.addHandler(self.log_handler)
        geoadjust_logger.setLevel(logging.DEBUG)
        
        # Форматирование
        formatter = logging.Formatter('%(name)s - %(message)s')
        self.log_handler.setFormatter(formatter)
    
    def _handle_log_message(self, message: str, level: str):
        """Обработка лог-сообщения из Python logging"""
        self.log_message(message, level)
    
    def log_message(self, message: str, level: str = "INFO"):
        """Добавление сообщения в журнал"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Определение цвета по уровню
        if level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "orange"
        else:
            color = "black"
        
        # Форматирование сообщения
        html_message = f'<span style="color: gray;">[{timestamp}]</span> '
        html_message += f'<span style="color: {color}; font-weight: bold;">{level}:</span> '
        html_message += f'<span style="color: black;">{message}</span><br>'
        
        # Добавление в конец
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html_message)
        self.log_text.setTextCursor(cursor)
        
        # Автопрокрутка
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def info(self, message: str):
        """Добавление информационного сообщения"""
        self.log_message(message, "INFO")
    
    def warning(self, message: str):
        """Добавление предупреждения"""
        self.log_message(message, "WARNING")
    
    def error(self, message: str):
        """Добавление ошибки"""
        self.log_message(message, "ERROR")
    
    def success(self, message: str):
        """Добавление сообщения об успехе"""
        self.log_message(message, "SUCCESS")
    
    def clear_log(self):
        """Очистка журнала"""
        self.log_text.clear()
    
    def save_log(self):
        """Сохранение журнала в файл"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить журнал", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
