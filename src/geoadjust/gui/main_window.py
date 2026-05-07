"""Главное окно приложения GeoAdjust Pro"""
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar, QLabel, QSplitter,
    QGroupBox, QFileDialog, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt
from loguru import logger

from geoadjust.gui.widgets.observations_table import ObservationsTableView, ObservationsModel
from geoadjust.gui.workers.adjustment_worker import AdjustmentWorker
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.weights import InstrumentSpec
from geoadjust.io.gsi import GSIParser
from geoadjust.io.sdr import SDRParser
from geoadjust.io.office import OfficeParser
from geoadjust.io.validators import validate_and_clean
from geoadjust.gui.reporting.exporter import ReportExporter


class MainWindow(QMainWindow):
    """Главное окно приложения с панелью инструментов, таблицей и логом"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GeoAdjust Pro v1.0")
        self.resize(1200, 800)
        
        # Инициализация компонентов
        self.engine = AdjustmentEngine(spec=InstrumentSpec(class_code="4"))
        self.worker: AdjustmentWorker = None
        self.obs_model = ObservationsModel()
        self._current_observations = []
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Создание интерфейса"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Панель кнопок (используем QVBoxLayout + addStretch вместо QFormLayout)
        btn_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("📥 Импорт измерений")
        self.btn_adjust = QPushButton("📐 Запустить уравнивание")
        self.btn_export = QPushButton("💾 Экспорт отчёта")
        
        self.btn_adjust.setEnabled(False)
        self.btn_export.setEnabled(False)
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_adjust)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addStretch()  # ✅ Корректное растягивание
        
        main_layout.addLayout(btn_layout)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        main_layout.addWidget(self.progress)

        # Статус
        self.status_label = QLabel("Готово к работе")
        self.status_label.setStyleSheet(
            "color: #2c3e50; font-weight: bold; font-size: 12px;"
        )
        main_layout.addWidget(self.status_label)

        # Разделитель: таблица / лог
        splitter = QSplitter(Qt.Vertical)
        
        # Таблица наблюдений
        self.table_view = ObservationsTableView()
        self.table_view.setModel(self.obs_model)
        splitter.addWidget(self.table_view)

        # Лог выполнения
        log_group = QGroupBox("Лог выполнения")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #f8f9fa; font-family: 'Consolas', monospace; font-size: 11px;"
        )
        log_layout.addWidget(self.log_text)
        splitter.addWidget(log_group)
        
        # Пропорции разделителя
        splitter.setSizes([400, 200])

        main_layout.addWidget(splitter)

    def _connect_signals(self):
        """Подключение сигналов к слотам"""
        self.btn_load.clicked.connect(self.load_data)
        self.btn_adjust.clicked.connect(self.start_adjustment)
        self.btn_export.clicked.connect(self.export_report)

    def _append_log(self, msg: str):
        """Добавление сообщения в лог с автопрокруткой"""
        self.log_text.append(msg)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def load_data(self):
        """Загрузка файла измерений"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите файл измерений", 
            "", 
            "Все файлы (*.*);; GSI (*.GSI *.gsi);; SDR (*.DAT *.dat);; Excel (*.XLSX *.xlsx);; CSV (*.CSV *.csv)"
        )
        if not file_path:
            return
            
        path = Path(file_path)
        self._append_log(f"📂 Загрузка: {path.name}")
        
        try:
            # Выбор парсера по расширению
            suffix = path.suffix.upper()
            if suffix in (".GSI", ".GSI16"):
                parser = GSIParser()
            elif suffix == ".DAT":
                parser = SDRParser()
            elif suffix in (".XLSX", ".CSV"):
                parser = OfficeParser()
            else:
                raise ValueError(f"Неподдерживаемый формат: {suffix}")

            obs = parser.parse(path)
            obs, report = validate_and_clean(obs)
            
            self._current_observations = obs
            self.obs_model.update_data(obs)
            
            self._append_log(
                f"✅ Загружено: {report['final']} наблюдений. "
                f"(дубли: {report['removed_duplicates']}, "
                f"петли: {report['removed_self_loops']})"
            )
            
            self.btn_adjust.setEnabled(report['final'] > 0)
            
        except Exception as e:
            self._append_log(f"❌ Ошибка импорта: {e}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def start_adjustment(self):
        """Запуск уравнивания в фоновом потоке"""
        if self.worker and self.worker.isRunning():
            return
            
        if not self._current_observations:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите данные")
            return
        
        self.btn_adjust.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText("Вычисление нормальных уравнений...")

        # Фиксированные пункты (в реальном GUI берутся из диалога)
        fixed_points = {} 

        # Создание и запуск воркера
        self.worker = AdjustmentWorker(
            self.engine, 
            self._current_observations, 
            fixed_points, 
            self.engine.spec
        )
        
        # Подключение сигналов
        self.worker.started.connect(lambda: self._append_log("🚀 Воркер запущен"))
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.log_message.connect(self._append_log)
        
        # 🔧 Безопасное управление памятью потока
        self.worker.finished.connect(self.worker.deleteLater)
        
        self.worker.start()

    def on_progress(self, percent: int, msg: str):
        """Обновление прогресс-бара"""
        self.progress.setValue(percent)
        self.status_label.setText(msg)

    def on_finished(self, result: dict):
        """Завершение уравнивания успешно"""
        self.progress.setVisible(False)
        self.btn_adjust.setEnabled(True)
        self.btn_export.setEnabled(True)
        
        self._append_log(
            f"📊 Итог: σ₀ = {result['sigma_0']:.6f} м, "
            f"Итераций: {result['iterations']}, "
            f"Статус: {result['status']}"
        )
        self.status_label.setText("Уравнивание завершено")
        
        QMessageBox.information(
            self, 
            "Готово", 
            f"Уравновешивание успешно.\n"
            f"Средняя квадратическая ошибка единицы веса: {result['sigma_0']:.6f} м"
        )

    def on_error(self, msg: str):
        """Ошибка выполнения"""
        self.progress.setVisible(False)
        self.btn_adjust.setEnabled(True)
        self._append_log(f"⛔ Ошибка: {msg}")
        self.status_label.setText("Ошибка выполнения")
        QMessageBox.critical(self, "Критическая ошибка", msg)

    def export_report(self):
        """Экспорт отчёта"""
        out_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить отчёт", 
            "", 
            "TXT (*.txt);; RTF (*.rtf);; CSV (*.csv)"
        )
        if not out_path:
            return
        
        try:
            # Получение результатов из движка
            if self.engine._last_result is None:
                raise ValueError("Нет результатов уравнивания для экспорта")
            
            result = {
                "sigma_0": self.engine._last_result.sigma_0,
                "iterations": self.engine._last_result.iterations,
                "status": self.engine._last_result.status,
                "corrections": self.engine._last_result.corrections.tolist(),
                "residuals": self.engine._last_result.residuals.tolist(),
                "adjusted_heights": self.engine._last_result.adjusted_heights,
            }
            
            ReportExporter.export_txt(result, self._current_observations, Path(out_path))
            self._append_log(f"💾 Отчёт сохранён: {out_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
