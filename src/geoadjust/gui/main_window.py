"""Главное окно приложения GeoAdjust Pro"""
import logging
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.weights import InstrumentSpec
from geoadjust.core.processing_context import ProcessingContext
from geoadjust.gui.qlog_handler import QLogHandler
from geoadjust.gui.reporting.exporter import ReportExporter
from geoadjust.gui.widgets.observations_table import ObservationsModel, ObservationsTableView
from geoadjust.gui.workers.adjustment_worker import AdjustmentWorker
from geoadjust.io.gsi import GSIParser
from geoadjust.io.office import OfficeParser
from geoadjust.io.sdr import SDRParser
from geoadjust.io.validators import validate_and_clean
from geoadjust.processing_pipeline import ProcessingPipeline


class PipelineWorker(QThread):
    """Фоновый воркер для запуска конвейера обработки"""
    finished = pyqtSignal(ProcessingContext)
    error = pyqtSignal(str)
    status_message = pyqtSignal(str)  # Сигнал для статусных сообщений вместо QMessageBox

    def __init__(self, ctx: ProcessingContext):
        super().__init__()
        self.ctx = ctx

    def run(self):
        try:
            pipeline = ProcessingPipeline()
            result = pipeline.run(self.ctx)

            # Emit status messages based on result
            if result.status == "READY":
                self.status_message.emit("✅ Конвейер завершён успешно")
            elif result.status in ("RANK_DEFICIENT", "POORLY_CONDITIONED"):
                self.status_message.emit(f"⚠️ Предупреждение: {result.status}")
            else:
                self.status_message.emit(f"❌ Ошибка: {result.status}")

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


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

        # Настройка логгера для GUI
        self.log_handler = QLogHandler()
        self.log_handler.attach_to_widget(self.log_text)
        logging.getLogger("geoadjust").addHandler(self.log_handler)
        logging.getLogger("geoadjust").setLevel(logging.DEBUG)

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
        """Запуск уравнивания в фоновом потоке с использованием нового конвейера"""
        if self.worker and self.worker.isRunning():
            return

        if not self._current_observations:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите данные")
            return

        self.btn_adjust.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText("⏳ Запуск конвейера обработки...")

        self._append_log("🚀 Запуск нового конвейера обработки с валидацией")

        # Создание контекста обработки
        ctx = ProcessingContext(
            observations=self._current_observations,
            points={},  # Заполняется в конвейере
            fixed_points={},  # В реальном приложении брать из диалога
            config={"spec": self.engine.spec}
        )

        # Создание и запуск воркера конвейера
        self.pipeline_worker = PipelineWorker(ctx)
        self.pipeline_worker.finished.connect(self.on_pipeline_finished)
        self.pipeline_worker.error.connect(self.on_pipeline_error)
        self.pipeline_worker.status_message.connect(lambda msg: self.status_label.setText(msg))
        self.pipeline_worker.start()

    def on_pipeline_finished(self, ctx: ProcessingContext):
        """Обработка результатов конвейера без QMessageBox в потоке - только сигналы и статусы"""
        self.progress.setVisible(False)

        if ctx.status == "READY":
            self.status_label.setText("✅ Система валидна. Запуск уравнивателя...")
            self._append_log(f"✅ Конвейер завершён. Статус: {ctx.status}")
            self._append_log(f"📊 Матрицы: A{ctx.matrices['A'].shape}, L={len(ctx.matrices['L'])}, P{ctx.matrices['P'].shape}")
            self._append_log(f"📈 Ранг: {ctx.validation_report.get('rank', 'N/A')}, Обусловленность: {ctx.validation_report.get('condition_number', 'N/A')}")

            # Запуск основного уравнивания через существующий AdjustmentWorker
            self.btn_adjust.setEnabled(True)
            self._run_legacy_adjustment(ctx)
        else:
            self.status_label.setText(f"❌ Конвейер остановлен: {ctx.status}")
            self._append_log(f"❌ Конвейер остановлен: {ctx.status}")
            self._append_log(f"📋 Отчёт валидации: {ctx.validation_report}")
            self.btn_adjust.setEnabled(True)
            # ✅ Убрали QMessageBox из фонового потока - теперь только логирование
            self._append_log(f"⚠️ Требуется внимание пользователя: {ctx.status} - {ctx.validation_report}")

    def on_pipeline_error(self, msg: str):
        """Ошибка выполнения конвейера - без QMessageBox, только логирование"""
        self.progress.setVisible(False)
        self.btn_adjust.setEnabled(True)
        self._append_log(f"⛔ Ошибка конвейера: {msg}")
        self.status_label.setText("Ошибка выполнения")
        # ✅ Убрали QMessageBox.critical - теперь только логирование в GUI

    def _run_legacy_adjustment(self, ctx: ProcessingContext):
        """Запуск уравнивания через существующий AdjustmentEngine"""
        # Фиксированные пункты (в реальном GUI берутся из диалога)
        fixed_points = ctx.fixed_points

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
        """Завершение уравнивания успешно - без QMessageBox, только логирование и статус"""
        self.progress.setVisible(False)
        self.btn_adjust.setEnabled(True)
        self.btn_export.setEnabled(True)

        self._append_log(
            f"📊 Итог: σ₀ = {result['sigma_0']:.6f} м, "
            f"Итераций: {result['iterations']}, "
            f"Статус: {result['status']}"
        )
        self.status_label.setText(f"✅ Уравнивание завершено. σ₀ = {result['sigma_0']:.6f} м")
        # ✅ Убрали QMessageBox.information - теперь только статус-бар и лог

    def on_error(self, msg: str):
        """Ошибка выполнения - без QMessageBox, только логирование"""
        self.progress.setVisible(False)
        self.btn_adjust.setEnabled(True)
        self._append_log(f"⛔ Ошибка: {msg}")
        self.status_label.setText("Ошибка выполнения")
        # ✅ Убрали QMessageBox.critical - теперь только логирование

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
            # ✅ Заменили QMessageBox на логирование
            self._append_log(f"❌ Ошибка экспорта: {e}")
            self.status_label.setText(f"Ошибка экспорта: {e}")
