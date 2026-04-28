# src/geoadjust/gui/widgets/progress_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, QTextEdit, 
    QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import pyqtSignal, QObject
import logging

logger = logging.getLogger(__name__)

class ProcessingProgressDialog(QDialog):
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Обработка данных")
        self.resize(600, 350)
        self.setModal(True)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Прогресс
        self.lbl_stage = QLabel("Инициализация...")
        self.lbl_stage.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.lbl_stage)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        
        # Разделитель
        frame = QFrame()
        frame.setFrameShape(QFrame.HLine)
        frame.setFrameShadow(QFrame.Sunken)
        layout.addWidget(frame)
        
        # Мини-отчёт
        self.lbl_report_title = QLabel("📋 Мини-отчёт о состоянии и предупреждениях:")
        layout.addWidget(self.lbl_report_title)
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa; 
                border: 1px solid #ced4da; 
                border-radius: 4px; 
                font-family: 'Consolas', monospace; 
                font-size: 11px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.report_text, 1)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("⏹ Отменить")
        self.btn_cancel.clicked.connect(self.cancel_requested)
        self.btn_ok = QPushButton("OK")
        self.btn_ok.setEnabled(False)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

    def update_progress(self, stage: str, percent: int, message: str, warnings: list):
        self.lbl_stage.setText(f"⚙️ {stage}")
        self.progress.setValue(percent)
        self.report_text.append(f"[{percent}%] {message}")
        for w in warnings:
            self.report_text.append(f"⚠️ {w}")
        self.report_text.append("-" * 40)
        
        if percent >= 100:
            self.progress.setValue(100)
            self.btn_ok.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self.report_text.append("✅ Обработка завершена.")

    def reset(self):
        self.progress.setValue(0)
        self.report_text.clear()
        self.lbl_stage.setText("Инициализация...")
        self.btn_ok.setEnabled(False)
        self.btn_cancel.setEnabled(True)