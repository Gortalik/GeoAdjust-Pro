"""
Главное окно приложения GeoAdjust Pro

Поддерживает два типа интерфейса:
- Классический (меню и тулбары)
- Ленточный (современный ribbon-интерфейс)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import logging

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenuBar, QMenu, QAction,
    QToolBar, QStatusBar, QLabel, QProgressBar, QDockWidget, QSplitter,
    QTreeWidget, QTreeWidgetItem, QStackedWidget, QTabWidget,
    QDialog, QDialogButtonBox, QLineEdit, QTextEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QFormLayout,
    QMessageBox, QFileDialog, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont

# Импорт центральной функции для работы с ресурсами
from geoadjust.utils import get_resource_path

# Импорт визуальных индикаторов
from geoadjust.gui.visual_indicators import VisualIndicator

# Импорт моделей данных
from geoadjust.core.network.models import CombinedObservation

logger = logging.getLogger(__name__)


class InterfaceType(Enum):
    """Тип интерфейса программы"""
    CLASSIC = "classic"  # Меню и тулбары (как в КРЕДО ДАТ 3.х)
    RIBBON = "ribbon"    # Ленточный интерфейс (современный)


@dataclass
class MainWindowConfig:
    """Конфигурация главного окна"""
    interface_type: InterfaceType = InterfaceType.RIBBON
    window_title: str = "GeoAdjust Pro"
    window_size: Tuple[int, int] = (1600, 900)
    window_state: str = "maximized"  # normal, maximized, fullscreen
    theme: str = "light"  # light, dark, system


class MainWindow(QMainWindow):
    """Главное окно приложения GeoAdjust Pro"""
    
    # Сигналы
    project_created = pyqtSignal(str)
    project_opened = pyqtSignal(str)
    project_saved = pyqtSignal()
    data_imported = pyqtSignal(str)
    
    def __init__(self, config: Optional[MainWindowConfig] = None, parent=None):
        super().__init__(parent)
        
        self.config = config or MainWindowConfig()
        self.current_project = None
        
        # Создание интеграции обработки
        self.processing_integration = None
        
        # Защита от рекурсивных вызовов
        self._updating_properties = False
        self._refreshing_data = False

        
        # Настройка окна
        self.setWindowTitle(self.config.window_title)
        self._load_icon()
        
        # Загрузка стилей из файла
        self._load_styles()
        
        if self.config.window_state == "maximized":
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.resize(*self.config.window_size)
        
        # Центральный виджет
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        
        # Основной макет - убираем все отступы
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Создание компонентов интерфейса
        # Menu bar создаётся всегда
        self._create_menu_bar()
        
        # Тулбары (ribbon убран, так как дублирует меню)
        self._create_classic_toolbars()
        
        self._create_status_bar()
        self._create_dock_widgets()
        self._create_main_area()
        
        # Загрузка конфигурации рабочей области
        self._load_workspace_config()
    
    def _load_styles(self):
        """Загрузка стилей из файла QSS"""
        try:
            styles_path = get_resource_path("gui/resources/styles/styles.qss")
            if hasattr(styles_path, 'exists') and styles_path.exists():
                with open(str(styles_path), 'r', encoding='utf-8') as f:
                    styles = f.read()
                self.setStyleSheet(styles)
                logger.info(f"Стили загружены из: {styles_path}")
            else:
                logger.warning(f"Файл стилей не найден: {styles_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки стилей: {e}")
    
    def _load_icon(self):
        """Загрузка иконки приложения с обработкой ошибок"""
        try:
            icon_path = get_resource_path("gui/resources/icons/app_icon.ico")
            if hasattr(icon_path, 'exists') and icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
            else:
                # Использовать стандартную иконку
                self.setWindowIcon(QIcon.fromTheme("applications-science"))
                logger.warning(f"Иконка не найдена: {icon_path}, используется стандартная")
        except Exception as e:
            logger.error(f"Ошибка загрузки иконки: {e}")
            # Продолжить без иконки или использовать стандартную
            self.setWindowIcon(QIcon.fromTheme("applications-science"))
    
    def _create_menu_bar(self):
        """Создание главного меню"""
        menu_bar = self.menuBar()
        
        # Меню Файл
        file_menu = menu_bar.addMenu("Файл")
        
        # Создание проекта
        new_project_action = QAction("Создать проект", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.triggered.connect(self._create_project)
        file_menu.addAction(new_project_action)
        
        # Открытие проекта
        open_project_action = QAction("Открыть проект", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self._open_project)
        file_menu.addAction(open_project_action)
        
        # Сохранение проекта
        save_project_action = QAction("Сохранить проект", self)
        save_project_action.setShortcut("Ctrl+S")
        save_project_action.triggered.connect(self._save_project)
        file_menu.addAction(save_project_action)
        
        # Сохранить как
        save_as_action = QAction("Сохранить как...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Свойства проекта
        properties_action = QAction("Свойства проекта", self)
        properties_action.triggered.connect(self._project_properties)
        file_menu.addAction(properties_action)
        
        file_menu.addSeparator()
        
        # Параметры программы
        settings_action = QAction("Параметры программы", self)
        settings_action.triggered.connect(self._program_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Выход
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Данные
        data_menu = menu_bar.addMenu("Данные")
        
        # Импорт
        import_file_action = QAction("Импорт из файла...", self)
        import_file_action.setShortcut("Ctrl+I")
        import_file_action.triggered.connect(self._import_file)
        data_menu.addAction(import_file_action)

        data_menu.addSeparator()

        # Экспорт
        export_file_action = QAction("Экспорт в файл...", self)
        export_file_action.setShortcut("Ctrl+E")
        export_file_action.triggered.connect(self._export_file)
        data_menu.addAction(export_file_action)
        
        # Меню Редактирование
        edit_menu = menu_bar.addMenu("Редактирование")
        
        undo_action = QAction("Отменить", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Повторить", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        copy_action = QAction("Копировать", self)
        copy_action.setShortcut("Ctrl+C")
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Вставить", self)
        paste_action.setShortcut("Ctrl+V")
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        # Добавление данных
        add_point_action = QAction("Добавить пункт", self)
        add_point_action.setShortcut("Ctrl+P")
        add_point_action.triggered.connect(self._add_point)
        edit_menu.addAction(add_point_action)
        
        add_obs_action = QAction("Добавить измерение", self)
        add_obs_action.setShortcut("Ctrl+M")
        add_obs_action.triggered.connect(self._add_observation)
        edit_menu.addAction(add_obs_action)
        
        # Меню Вид
        view_menu = menu_bar.addMenu("Вид")
        
        scheme_action = QAction("Схема сети", self)
        scheme_action.setShortcut("F5")
        scheme_action.triggered.connect(self._show_scheme)
        view_menu.addAction(scheme_action)
        
        view_menu.addSeparator()
        
        # Панели - с возможностью восстановления
        panels_menu = view_menu.addMenu("Панели")
        
        # Действия для панелей с проверкой состояния
        self.points_dock_action = QAction("Пункты ПВО", self)
        self.points_dock_action.setCheckable(True)
        self.points_dock_action.setChecked(True)
        self.points_dock_action.triggered.connect(self._toggle_points_dock)
        panels_menu.addAction(self.points_dock_action)
        
        self.observations_dock_action = QAction("Измерения", self)
        self.observations_dock_action.setCheckable(True)
        self.observations_dock_action.setChecked(True)
        self.observations_dock_action.triggered.connect(self._toggle_observations_dock)
        panels_menu.addAction(self.observations_dock_action)
        
        self.traverses_dock_action = QAction("Ходы и секции", self)
        self.traverses_dock_action.setCheckable(True)
        self.traverses_dock_action.setChecked(True)
        self.traverses_dock_action.triggered.connect(self._toggle_traverses_dock)
        panels_menu.addAction(self.traverses_dock_action)

        self.stations_dock_action = QAction("Станции", self)
        self.stations_dock_action.setCheckable(True)
        self.stations_dock_action.setChecked(True)
        self.stations_dock_action.triggered.connect(self._toggle_stations_dock)
        panels_menu.addAction(self.stations_dock_action)

        panels_menu.addSeparator()
        
        self.log_dock_action = QAction("Журнал", self)
        self.log_dock_action.setCheckable(True)
        self.log_dock_action.setChecked(True)
        self.log_dock_action.triggered.connect(self._toggle_log_dock)
        panels_menu.addAction(self.log_dock_action)
        
        self.properties_dock_action = QAction("Свойства", self)
        self.properties_dock_action.setCheckable(True)
        self.properties_dock_action.setChecked(True)
        self.properties_dock_action.triggered.connect(self._toggle_properties_dock)
        panels_menu.addAction(self.properties_dock_action)
        
        panels_menu.addSeparator()
        
        # Действие для восстановления всех панелей
        restore_all_action = QAction("Восстановить все панели", self)
        restore_all_action.setShortcut("Ctrl+Shift+R")
        restore_all_action.triggered.connect(self._restore_all_panels)
        panels_menu.addAction(restore_all_action)
        
        # Меню Обработка
        process_menu = menu_bar.addMenu("Обработка")
        
        preprocessing_action = QAction("Предобработка", self)
        preprocessing_action.triggered.connect(self._run_preprocessing)
        process_menu.addAction(preprocessing_action)
        
        process_menu.addSeparator()
        
        adjust_classic_action = QAction("Классический МНК", self)
        adjust_classic_action.triggered.connect(self._adjust_classic)
        process_menu.addAction(adjust_classic_action)
        
        adjust_robust_action = QAction("Робастное уравнивание", self)
        adjust_robust_action.triggered.connect(self._adjust_robust)
        process_menu.addAction(adjust_robust_action)
        
        # Меню Отчёты
        report_menu = menu_bar.addMenu("Отчёты")

        coordinate_schedule_action = QAction("Ведомость координат", self)
        coordinate_schedule_action.triggered.connect(self._coordinate_schedule)
        report_menu.addAction(coordinate_schedule_action)

        topology_schedule_action = QAction("Ведомость топологии сети", self)
        topology_schedule_action.triggered.connect(self._topology_schedule)
        report_menu.addAction(topology_schedule_action)

        accuracy_schedule_action = QAction("Ведомость оценки точности", self)
        accuracy_schedule_action.triggered.connect(self._accuracy_schedule)
        report_menu.addAction(accuracy_schedule_action)

        report_menu.addSeparator()

        correction_schedule_action = QAction("Ведомость поправок", self)
        correction_schedule_action.triggered.connect(self._correction_schedule)
        report_menu.addAction(correction_schedule_action)

        report_menu.addSeparator()

        gost_report_action = QAction("Отчёт по ГОСТ 7.32-2017", self)
        gost_report_action.triggered.connect(self._gost_report)
        report_menu.addAction(gost_report_action)
        
        # Меню Справка
        help_menu = menu_bar.addMenu("Справка")
        
        help_content_action = QAction("Содержание", self)
        help_content_action.setShortcut("F1")
        help_content_action.triggered.connect(self._show_help)
        help_menu.addAction(help_content_action)
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._about_program)
        help_menu.addAction(about_action)
    
    def _create_ribbon_interface(self):
        """Создание ленточного интерфейса"""
        from .widgets.ribbon_widget import RibbonWidget
        
        self.ribbon = RibbonWidget(self)
        self.ribbon.setObjectName("ribbon")
        
        # Вкладка "Главная"
        home_tab = self.ribbon.add_tab("Главная")
        home_tab.add_group("Проект", [
            ("Новый проект", "new_project", "Ctrl+N", self._create_project),
            ("Открыть", "open_project", "Ctrl+O", self._open_project),
            ("Сохранить", "save_project", "Ctrl+S", self._save_project),
        ])
        home_tab.add_group("Буфер обмена", [
            ("Копировать", "copy", "Ctrl+C", self._copy_selected),
            ("Вставить", "paste", "Ctrl+V", self._paste_data),
        ])
        
        # Вкладка "Данные"
        data_tab = self.ribbon.add_tab("Данные")
        data_tab.add_group("Импорт", [
            ("Импорт файла", "import_file", None, self._import_file),
        ])
        data_tab.add_group("Экспорт", [
            ("Экспорт в файл", "export_file", None, self._export_file),
        ])
        
        # Вкладка "Редактирование"
        edit_tab = self.ribbon.add_tab("Редактирование")
        edit_tab.add_group("Добавление данных", [
            ("Добавить пункт", "add_point", "Ctrl+P", self._add_point),
            ("Добавить измерение", "add_observation", "Ctrl+M", self._add_observation),
        ])
        edit_tab.add_group("Буфер обмена", [
            ("Копировать", "copy", "Ctrl+C", None),
            ("Вставить", "paste", "Ctrl+V", None),
        ])
        
        # Вкладка "Обработка"
        process_tab = self.ribbon.add_tab("Обработка")
        process_tab.add_group("Предобработка", [
            ("Контроль допусков", "check_tolerances", None, self._check_tolerances),
            ("Применение редукций", "apply_corrections", None, self._apply_corrections),
        ])
        process_tab.add_group("Уравнивание", [
            ("Классический МНК", "adjust_classic", None, self._adjust_classic),
            ("Робастное уравнивание", "adjust_robust", None, self._adjust_robust),
        ])
        
        # Вкладка "Анализ"
        analysis_tab = self.ribbon.add_tab("Анализ")
        analysis_tab.add_group("Надёжность", [
            ("Анализ по Баарду", "baarda_analysis", None, self._baarda_analysis),
            ("Поиск грубых ошибок", "gross_error_search", None, self._gross_error_search),
        ])
        analysis_tab.add_group("Визуализация", [
            ("Эллипсы ошибок", "error_ellipses", None, self._error_ellipses),
            ("Тепловые карты", "heatmaps", None, self._heatmaps),
        ])
        
        # Вкладка "Отчёты"
        report_tab = self.ribbon.add_tab("Отчёты")
        report_tab.add_group("Ведомости", [
            ("Ведомость координат", "coordinate_schedule", None, self._coordinate_schedule),
            ("Ведомость поправок", "correction_schedule", None, self._correction_schedule),
        ])
        report_tab.add_group("ГОСТ", [
            ("Отчёт по ГОСТ 7.32-2017", "gost_report", None, self._gost_report),
            ("Сертификат соответствия", "compliance_certificate", None, self._compliance_certificate),
        ])
        
        # Добавляем ribbon в главный layout
        self.main_layout.addWidget(self.ribbon)
    
    def _create_classic_toolbars(self):
        """Создание классических тулбаров"""
        # Тулбар "Стандартный"
        standard_toolbar = QToolBar("Стандартный", self)
        standard_toolbar.addAction("Новый проект", self._create_project)
        standard_toolbar.addAction("Открыть", self._open_project)
        standard_toolbar.addAction("Сохранить", self._save_project)
        self.addToolBar(Qt.TopToolBarArea, standard_toolbar)
        
        # Тулбар "Редактирование"
        edit_toolbar = QToolBar("Редактирование", self)
        edit_toolbar.addAction("Отменить")
        edit_toolbar.addAction("Повторить")
        edit_toolbar.addAction("Копировать")
        edit_toolbar.addAction("Вставить")
        self.addToolBar(Qt.TopToolBarArea, edit_toolbar)
        
        # Тулбар "Данные"
        data_toolbar = QToolBar("Данные", self)
        
        # Добавить пункт с иконкой
        add_point_action = QAction("Добавить пункт", self)
        add_point_icon_path = get_resource_path("icons/toolbar/add_point.svg")
        if hasattr(add_point_icon_path, 'exists') and add_point_icon_path.exists():
            add_point_action.setIcon(QIcon(str(add_point_icon_path)))
        add_point_action.triggered.connect(self._add_point)
        data_toolbar.addAction(add_point_action)
        
        # Добавить измерение с иконкой
        add_obs_action = QAction("Добавить измерение", self)
        add_obs_icon_path = get_resource_path("icons/toolbar/add_observation.svg")
        if hasattr(add_obs_icon_path, 'exists') and add_obs_icon_path.exists():
            add_obs_action.setIcon(QIcon(str(add_obs_icon_path)))
        add_obs_action.triggered.connect(self._add_observation)
        data_toolbar.addAction(add_obs_action)
        
        self.addToolBar(Qt.TopToolBarArea, data_toolbar)
        
        # Тулбар "Обработка"
        process_toolbar = QToolBar("Обработка", self)
        process_toolbar.addAction("Предобработка", self._run_preprocessing)
        process_toolbar.addAction("МНК", self._adjust_classic)
        process_toolbar.addAction("Робастное", self._adjust_robust)
        self.addToolBar(Qt.TopToolBarArea, process_toolbar)
    
    def _create_status_bar(self):
        """Создание строки состояния"""
        status_bar = self.statusBar()
        
        # Информация о проекте
        self.project_label = QLabel("Проект: не открыт")
        status_bar.addWidget(self.project_label)
        
        # Информация о текущем режиме
        self.mode_label = QLabel("Режим: ожидание")
        status_bar.addWidget(self.mode_label)
        
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        spacer.setMinimumWidth(20)
        status_bar.addPermanentWidget(spacer)
        
        # Прогресс выполнения операций
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        status_bar.addPermanentWidget(self.progress_bar)
        
        # Информация о координатах (для графического окна)
        self.coords_label = QLabel("")
        status_bar.addPermanentWidget(self.coords_label)
    
    def _create_dock_widgets(self):
        """Создание док-виджетов"""
        from .components.dock_widgets import ObservationsDockWidget
        from .widgets.observations_table import ObservationsTableWidget
        from .components.plan_view import PlanGraphicsView
        from .components.log_widget import LogWidget
        from .components.properties_widget import PropertiesWidget

        # Настройка углов для док-виджетов (убираем зазоры между панелями)
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        # Объединенное левое окно "Станции / Ходы / Пункты ПВО"
        from .widgets.left_panel_widget import LeftPanelWidget
        self.left_panel_dock = QDockWidget("Данные", self)
        self.left_panel_dock.setObjectName("leftPanelDock")
        self.left_panel = LeftPanelWidget(self)
        self.left_panel_dock.setWidget(self.left_panel)
        self.traverses_tree = self.left_panel.courses_tree
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_panel_dock)
        self.left_panel_dock.setMinimumWidth(300)
        self.left_panel_dock.setVisible(True)
        self.left_panel_dock.visibilityChanged.connect(self._on_left_panel_dock_visibility_changed)

        # Подключаем сигналы от левой панели
        self.left_panel.station_selected.connect(self._on_station_selected_from_panel)
        self.left_panel.course_selected.connect(self._on_course_selected_from_panel)

        # Сохраняем ссылки для совместимости
        self.stations_content = self.left_panel.get_stations_content()
        self.points_table = self.left_panel.get_points_table()
        
        # Окно "Измерения" - с вкладками по типам
        self.observations_dock = ObservationsDockWidget("Измерения", self)
        self.observations_dock.setObjectName("observationsDock")
        self.observations_table = ObservationsTableWidget()
        self.observations_dock.setWidget(self.observations_table)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.observations_dock)
        self.observations_dock.setMinimumWidth(350)
        self.observations_dock.visibilityChanged.connect(self._on_observations_dock_visibility_changed)
        
        # План - центральный виджет
        self.plan_view = PlanGraphicsView()
        self.plan_view.setObjectName("planView")
        
        # Окно "Журнал"
        self.log_dock = QDockWidget("Журнал", self)
        self.log_dock.setObjectName("logDock")
        self.log_widget = LogWidget()
        self.log_dock.setWidget(self.log_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.log_dock.setMinimumHeight(100)
        self.log_dock.visibilityChanged.connect(self._on_log_dock_visibility_changed)
        
        # Окно "Свойства/История" - большое окно справа
        self.properties_dock = QDockWidget("Свойства", self)
        self.properties_dock.setObjectName("propertiesDock")
        from .components.history_widget import PropertiesHistoryTabWidget
        self.properties_history = PropertiesHistoryTabWidget(self)
        self.properties_dock.setWidget(self.properties_history)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)
        self.properties_dock.setMinimumWidth(400)  # Увеличенная ширина
        self.properties_dock.setMinimumHeight(600)  # Увеличенная высота
        self.properties_dock.visibilityChanged.connect(self._on_properties_dock_visibility_changed)
        
        # Ссылки на вложенные виджеты для совместимости
        self.properties_widget = self.properties_history.properties_widget
        self.history_widget = self.properties_history.history_widget

        # Данные ходов для левой панели
        self.leveling_courses = []
        
        # Настройка размеров док-виджетов при запуске
        self.resizeDocks(
            [self.left_panel_dock, self.observations_dock, self.properties_dock],
            [300, 350, 400],
            Qt.Horizontal
        )
        
        # Подключение сигналов выбора к виджету свойств
        self._connect_properties_signals()

        # Временно отключим остальные сигналы для безопасности
        # self.properties_widget.properties_changed.connect(self._on_properties_changed)
        # self.history_widget.undo_requested.connect(self._on_history_undo)
        # self.history_widget.redo_requested.connect(self._on_history_redo)
        # self.history_widget.jump_to_entry.connect(self._on_jump_to_entry)
    
    def _connect_properties_signals(self):
        """Подключение сигналов выбора к виджету свойств"""
        # Сигнал от станций теперь работает через прямой вызов
        pass

    def _convert_observations_to_objects(self, observations: List[Dict[str, Any]]) -> List[Any]:
        """Конвертация словарей измерений обратно в объекты CombinedObservation

        Args:
            observations: Список словарей измерений из проекта

        Returns:
            Список объектов CombinedObservation или словарей для других типов
        """
        from geoadjust.io.formats.sdr import SDRObservation
        from geoadjust.core.network.models import CombinedObservation

        converted_observations = []

        for obs in observations:
            # Проверяем, является ли измерение CombinedObservation (судим по наличию специфичных полей)
            if isinstance(obs, dict) and 'horizontal_angle' in obs and 'zenith_angle' in obs and 'slope_distance' in obs:
                # Это CombinedObservation, конвертируем обратно в объект
                combined_obs = CombinedObservation(
                    obs_id=obs.get('obs_id', ''),
                    from_setup_id=obs.get('from_setup_id', ''),
                    from_point_id=obs.get('from_point_id', ''),
                    to_point_id=obs.get('to_point_id', ''),
                    face_position=obs.get('face_position'),
                    horizontal_angle=obs.get('horizontal_angle'),
                    zenith_angle=obs.get('zenith_angle'),
                    slope_distance=obs.get('slope_distance'),
                    raw_line=obs.get('raw_line')
                )
                converted_observations.append(combined_obs)
            elif isinstance(obs, SDRObservation):
                # Конвертируем SDRObservation в CombinedObservation
                combined_obs = CombinedObservation(
                    obs_id=getattr(obs, 'obs_type', 'sdr'),
                    from_setup_id=getattr(obs, 'setup_id', ''),
                    from_point_id=getattr(obs, 'from_point', ''),
                    to_point_id=getattr(obs, 'to_point', ''),
                    face_position=getattr(obs, 'face_position'),
                    horizontal_angle=getattr(obs, 'horizontal_angle'),
                    zenith_angle=getattr(obs, 'vertical_angle'),  # zenith_angle from vertical_angle
                    slope_distance=getattr(obs, 'distance'),
                    raw_line=getattr(obs, 'raw_line')
                )
                converted_observations.append(combined_obs)
            else:
                # Оставляем как есть (другие типы измерений)
                converted_observations.append(obs)

        return converted_observations

    def _on_point_selected(self, point_id: str):
        """Обработка выбора пункта"""
        self._show_point_properties(point_id)



        # Автоматическое переключение на вкладку тахеометрии
        # Принудительно переключимся на вкладку тахеометрии
        if hasattr(self, 'observations_table') and hasattr(self.observations_table, 'tabs'):
            for i in range(self.observations_table.tabs.count()):
                tab_text = self.observations_table.tabs.tabText(i)
                if "тахеометр" in tab_text.lower():
                    self.observations_table.tabs.setCurrentIndex(i)
                    break

        # Обновление статуса
        station_name = session_id.split('_S')[0] if '_S' in session_id else session_id
        self.statusBar().showMessage(f"Показаны измерения станции {station_name}", 3000)

        logger.info(f"Выбрана станция: {session_id}")
    
    def _on_points_selection_changed(self, selected, deselected):
        """Обработка изменения выбора в таблице пунктов"""
        if self._updating_properties or not hasattr(self, 'properties_widget'):
            return
        
        indexes = self.points_table.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            # Используем model() метод QTableView
            model = self.points_table.model
            if model and hasattr(model, 'index'):
                point_id = model.index(row, 0).data()
                if point_id:
                    self._show_point_properties(point_id)
        else:
            self.properties_widget.clear()
    
    def _on_observations_selection_changed(self, selected, deselected):
        """Обработка изменения выбора в таблице измерений"""
        if hasattr(self, 'observations_table'):
            obs_table = self.observations_table.table_view if hasattr(self.observations_table, 'table_view') else self.observations_table
            if hasattr(obs_table, 'selectionModel'):
                indexes = obs_table.selectionModel().selectedRows()
                if indexes:
                    row = indexes[0].row()
                    model = obs_table.model()
                    if model:
                        obs_id = model.index(row, 0).data()
                        if obs_id:
                            self._show_observation_properties(obs_id)
                else:
                    self.properties_widget.clear()
    
    def _show_point_properties(self, point_id: str):
        """Отображение свойств пункта"""
        if not self.current_project or self._updating_properties:
            return
        
        self._updating_properties = True
        
        try:
            # Поиск пункта в проекте
            points = self.current_project.get_points()
            for point in points:
                if isinstance(point, dict) and (point.get('id') == point_id or point.get('name') == point_id):
                    self.properties_widget.set_point_properties(point_id, point)
                    return
            
            # Если не нашли в проекте, пробуем получить из модели
            model = self.points_table.model()
            if model:
                for row in range(model.rowCount()):
                    item_id = model.index(row, 0).data()
                    if item_id == point_id:
                        properties = {
                            'id': point_id,
                            'name': model.index(row, 1).data() or point_id,
                            'coord_type': model.index(row, 2).data() or 'FREE',
                            'x': float(model.index(row, 3).data() or 0),
                            'y': float(model.index(row, 4).data() or 0),
                            'h': float(model.index(row, 5).data() or 0),
                            'normative_class': '',
                            'sigma_x': 0.0,
                            'sigma_y': 0.0
                        }
                        self.properties_widget.set_point_properties(point_id, properties)
                        return
        finally:
            self._updating_properties = False
        
        self._updating_properties = True
        
        try:
            # Поиск пункта в проекте
            points = self.current_project.get_points()
            for point in points:
                if isinstance(point, dict) and (point.get('id') == point_id or point.get('name') == point_id):
                    self.properties_widget.set_point_properties(point_id, point)
                    return
            
            # Если не нашли в проекте, пробуем получить из модели
            model = self.points_table.model()
            if model:
                for row in range(model.rowCount()):
                    item_id = model.index(row, 0).data()
                    if item_id == point_id:
                        properties = {
                            'id': point_id,
                            'name': model.index(row, 1).data() or point_id,
                            'coord_type': model.index(row, 2).data() or 'FREE',
                            'x': float(model.index(row, 3).data() or 0),
                            'y': float(model.index(row, 4).data() or 0),
                            'h': float(model.index(row, 5).data() or 0),
                            'normative_class': '',
                            'sigma_x': 0.0,
                            'sigma_y': 0.0
                        }
                        self.properties_widget.set_point_properties(point_id, properties)
                        return
        finally:
            self._updating_properties = False
    
    def _show_observation_properties(self, obs_id: str):
        """Отображение свойств измерения"""
        if not self.current_project:
            return
        
        # Поиск измерения в проекте
        observations = self.current_project.get_observations()
        for obs in observations:
            if isinstance(obs, dict) and obs.get('id') == obs_id:
                self.properties_widget.set_observation_properties(obs_id, obs)
                return
        
        # Если не нашли в проекте, пробуем получить из модели
        obs_table = self.observations_table.table_view if hasattr(self.observations_table, 'table_view') else self.observations_table
        model = obs_table.model()
        if model:
            for row in range(model.rowCount()):
                item_id = model.index(row, 0).data()
                if item_id == obs_id:
                    properties = {
                        'id': obs_id,
                        'obs_type': model.index(row, 3).data() or 'direction',
                        'from_point': model.index(row, 1).data() or '',
                        'to_point': model.index(row, 2).data() or '',
                        'value': float(model.index(row, 4).data() or 0),
                        'instrument_name': model.index(row, 6).data() or '',
                        'sigma_apriori': float(model.index(row, 5).data() or 0),
                        'is_active': True,
                        'weight_multiplier': 1.0
                    }
                    self.properties_widget.set_observation_properties(obs_id, properties)
                    return
    
    def _on_properties_changed(self, changes: dict):
        """Обработка изменения свойств объекта"""
        if not self.current_project or not self.properties_widget.current_object:
            return
        
        obj = self.properties_widget.current_object
        if obj['type'] == 'point':
            self._update_point_in_project(obj['id'], changes)
        elif obj['type'] == 'observation':
            self._update_observation_in_project(obj['id'], changes)
    
    def _update_point_in_project(self, point_id: str, changes: dict):
        """Обновление пункта в проекте"""
        try:
            points = self.current_project.get_points()
            for i, point in enumerate(points):
                if isinstance(point, dict) and (point.get('id') == point_id or point.get('name') == point_id):
                    # Сохраняем старые данные для отмены
                    old_data = dict(point)
                    point.update(changes)
                    if hasattr(self.current_project, 'update_point'):
                        self.current_project.update_point(point)
                    elif hasattr(self.current_project, 'save'):
                        self.current_project.save()
                    self._refresh_data_views()
                    self._add_history_entry('edit_point', f"Редактирование пункта '{point_id}'",
                                           {'old': old_data, 'new': dict(point)})
                    self.statusBar().showMessage(f"Пункт '{point_id}' обновлён", 2000)
                    logger.info(f"Пункт '{point_id}' обновлён")
                    return
        except Exception as e:
            logger.error(f"Ошибка обновления пункта: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить пункт:\n{str(e)}")
    
    def _update_observation_in_project(self, obs_id: str, changes: dict):
        """Обновление измерения в проекте"""
        try:
            observations = self.current_project.get_observations()
            for i, obs in enumerate(observations):
                if isinstance(obs, dict) and obs.get('id') == obs_id:
                    obs.update(changes)
                    if hasattr(self.current_project, 'update_observation'):
                        self.current_project.update_observation(obs)
                    elif hasattr(self.current_project, 'save'):
                        self.current_project.save()
                    self._refresh_data_views()
                    self.statusBar().showMessage("Измерение обновлено", 2000)
                    logger.info("Измерение обновлено")
                    return
        except Exception as e:
            logger.error(f"Ошибка обновления измерения: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить измерение:\n{str(e)}")
    
    def _add_history_entry(self, action_type: str, description: str, data: Dict[str, Any] = None):
        """Добавление записи в историю"""
        if hasattr(self, 'history_widget'):
            from .components.history_widget import HistoryEntry
            entry = HistoryEntry(action_type, description, data)
            self.history_widget.add_entry(entry)
    
    def _on_history_undo(self, entry):
        """Обработка запроса на отмену"""
        logger.info(f"Отмена действия: {entry.description}")
        # TODO: Реализовать отмену действия на основе entry.undo_data
        self.statusBar().showMessage(f"Отменено: {entry.description}", 2000)
    
    def _on_history_redo(self, entry):
        """Обработка запроса на повтор"""
        logger.info(f"Повтор действия: {entry.description}")
        # TODO: Реализовать повтор действия на основе entry.data
        self.statusBar().showMessage(f"Повторено: {entry.description}", 2000)
    
    def _on_jump_to_entry(self, index):
        """Переход к записи в истории"""
        entry = self.history_widget.history_manager.get_entry_at(index)
        if entry:
            logger.info(f"Переход к записи: {entry.description}")
            self.statusBar().showMessage(f"Запись: {entry.description}", 2000)
    
    def _create_main_area(self):
        """Создание центральной области"""
        # Док-виджеты уже добавлены через addDockWidget в _create_dock_widgets
        # QMainWindow автоматически управляет ими, plan_view занимает центральную область
        
        # Установка минимального размера для плана
        self.plan_view.setMinimumSize(400, 300)
        
        # Добавляем план в главный layout как центральный виджет
        self.main_layout.addWidget(self.plan_view)
    
    def _load_workspace_config(self):
        """Загрузка конфигурации рабочей области"""
        # TODO: Загрузка сохранённой конфигурации из файла
        pass
    
    # Обработчики действий меню
    def _create_project(self):
        """Создание нового проекта"""
        logger.info("Создание нового проекта")
        from .dialogs.project_wizard import ProjectWizard
        
        wizard = ProjectWizard(self)
        if wizard.exec_() == QDialog.Accepted:
            project_data = wizard.get_project_data()
            self._setup_project(project_data)
    
    def _setup_project(self, project_data: Dict[str, Any]):
        """Настройка созданного проекта"""
        try:
            from geoadjust.io.project.project_manager import ProjectManager
            
            project_manager = ProjectManager()
            # Исправлен порядок аргументов: сначала path, затем name
            project = project_manager.create_project(
                Path(project_data['path']),
                project_data['name']
            )
            self.current_project = project
            
            # Обновление интерфейса
            self.project_label.setText(f"Проект: {project_data['name']}")
            self.statusBar().showMessage(f"Проект '{project_data['name']}' создан", 3000)
            
            logger.info(f"Проект создан: {project_data['name']}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать проект:\n{str(e)}")
            logger.error(f"Ошибка при создании проекта: {e}", exc_info=True)
    
    def _open_project(self):
        """Открытие существующего проекта"""
        logger.info("Открытие проекта")
        
        # Используем getExistingDirectory для выбора директории .gad
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку проекта (.gad)",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if not dir_path:
            return
        
        # Проверяем, что это действительно папка проекта .gad
        path = Path(dir_path)
        if not path.suffix.lower() == '.gad':
            # Проверяем, содержит ли папка файл project.gadproj
            project_file = path / 'project.gadproj'
            if not project_file.exists():
                QMessageBox.warning(
                    self,
                    "Неверный формат",
                    f"Выбранная папка не является проектом GeoAdjust:\n{dir_path}\n\n"
                    f"Пожалуйста, выберите папку с расширением .gad или папку, содержащую файл project.gadproj"
                )
                return
            file_path = str(project_file)
        else:
            # Это папка .gad, проверяем наличие project.gadproj внутри
            project_file = path / 'project.gadproj'
            if not project_file.exists():
                QMessageBox.warning(
                    self,
                    "Ошибка проекта",
                    f"В папке проекта отсутствует файл project.gadproj:\n{dir_path}"
                )
                return
            file_path = str(project_file)
        
        if file_path:
            try:
                from geoadjust.io.project.project_manager import ProjectManager
                
                project_manager = ProjectManager()
                self.current_project = project_manager.open_project(Path(file_path))
                
                # Обновление интерфейса
                self.project_label.setText(f"Проект: {self.current_project.name}")
                self.statusBar().showMessage(f"Проект '{self.current_project.name}' загружен", 3000)
                
                logger.info(f"Проект загружен: {self.current_project.name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть проект:\n{str(e)}")
                logger.error(f"Ошибка при открытии проекта: {e}")
    
    def _save_project(self):
        """Сохранение проекта"""
        logger.info("Сохранение проекта")
        
        if self.current_project:
            try:
                from geoadjust.io.project.project_manager import ProjectManager
                
                project_manager = ProjectManager()
                project_manager.save_project()
                
                self.statusBar().showMessage(f"Проект '{self.current_project.name}' сохранён", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить проект:\n{str(e)}")
                logger.error(f"Ошибка при сохранении проекта: {e}")
        else:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
    
    def _save_project_as(self):
        """Сохранение проекта в новое место"""
        logger.info("Сохранение проекта как...")
        
        if self.current_project:
            file_path = QFileDialog.getSaveFileName(
                self,
                "Сохранить проект как...",
                "",
                "GeoAdjust Project (*.gad)"
            )[0]
            
            if file_path:
                try:
                    from pathlib import Path
                    from geoadjust.io.project.project_manager import ProjectManager
                    
                    project_manager = ProjectManager()
                    project_manager.save_project_as(Path(file_path))
                    
                    self.statusBar().showMessage(f"Проект сохранён в {file_path}", 3000)
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить проект:\n{str(e)}")
                    logger.error(f"Ошибка при сохранении проекта: {e}")
        else:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
    
    def _project_properties(self):
        """Открытие диалога свойств проекта"""
        from .dialogs.project_properties import ProjectPropertiesDialog
        
        dialog = ProjectPropertiesDialog(self.current_project, self)
        if dialog.exec_() == QDialog.Accepted:
            logger.info("Свойства проекта обновлены")
    
    def _program_settings(self):
        """Открытие диалога параметров программы"""
        from .dialogs.program_settings import ProgramSettingsDialog
        
        dialog = ProgramSettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            logger.info("Параметры программы обновлены")
    
    def _run_preprocessing(self):
        """Запуск предобработки"""
        logger.info("=" * 60)
        logger.info("ЗАПУСК ПРЕДОБРАБОТКИ ДАННЫХ")
        logger.info("=" * 60)

        if not self.current_project:
            logger.warning("Нет открытого проекта для предобработки")
            QMessageBox.warning(self, "Предупреждение", "Сначала откройте проект")
            return

        try:
            # Получение данных проекта
            observations = self.current_project.get_observations()
            points = self.current_project.get_points()

            if not observations:
                logger.warning("В проекте нет измерений")
                QMessageBox.warning(self, "Предупреждение", "В проекте нет измерений")
                return

            self.mode_label.setText("Режим: предобработка")
            self.statusBar().showMessage("Выполняется предобработка...", 0)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(10)

            # Создание модуля предобработки
            from geoadjust.core.preprocessing.module import PreprocessingModule
            preprocessor = PreprocessingModule()

            # Конфигурация предобработки
            config = {
                'refraction_coefficient': 0.14,
                'earth_radius': 6371000.0
            }

            # Запуск предобработки
            logger.info("Запуск модуля предобработки...")
            results = preprocessor.run_preprocessing(observations, points, config)

            self.progress_bar.setValue(90)

            # Обновление данных проекта
            if results.get('corrected_observations'):
                # Сохраняем исправленные измерения обратно в проект
                corrected_obs = results['corrected_observations']
                for i, obs in enumerate(corrected_obs):
                    if i < len(observations):
                        # Обновляем значения в оригинальных объектах
                        if hasattr(observations[i], 'value'):
                            observations[i].value = getattr(obs, 'value', observations[i].value)

            # Обновление интерфейса
            self._refresh_data_views()

            # Отображение результатов
            stages_completed = results.get('stages_completed', 0)
            num_violations = len(results.get('reciprocal_violations', []))
            num_errors = len(results.get('errors', []))

            message = f"Предобработка завершена: {stages_completed}/9 этапов"
            if num_violations > 0:
                message += f", {num_violations} нарушений"
            if num_errors > 0:
                message += f", {num_errors} ошибок"

            self.statusBar().showMessage(message, 5000)
            self.progress_bar.setValue(100)

            # Показать отчёт если есть проблемы
            if num_violations > 0 or num_errors > 0:
                self._show_preprocessing_report(results)

            logger.info(f"Предобработка завершена: {stages_completed} этапов, {num_violations} нарушений")

        except Exception as e:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при предобработке: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при предобработке:\n{str(e)}")
            self.statusBar().showMessage("Ошибка предобработки", 3000)
        finally:
            self.mode_label.setText("Режим: ожидание")
            self.progress_bar.setVisible(False)

    def _show_preprocessing_report(self, results: Dict[str, Any]):
        """Показать отчёт о предобработке"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Отчёт предобработки")
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        # Формирование отчёта
        report = []
        report.append("ОТЧЁТ ПРЕДОБРАБОТКИ ДАННЫХ")
        report.append("=" * 50)

        topology = results.get('topology', {})
        if topology:
            report.append("1. Топология сети:")
            report.append(f"   Пунктов: {len(topology.get('points', []))}")
            report.append(f"   Станций: {len(topology.get('stations', []))}")
            report.append(f"   Измерений: {topology.get('num_observations', 0)}")
            report.append(f"   Тип сети: {topology.get('network_type', 'unknown')}")

        traverses = results.get('traverses', {})
        if traverses:
            report.append("\n2. Ходы и секции:")
            report.append(f"   Тахеометрических ходов: {len(traverses.get('traverses', []))}")
            report.append(f"   Нивелирных секций: {len(traverses.get('sections', []))}")
            report.append(f"   GNSS базовых линий: {len(traverses.get('gnss_baselines', []))}")

        violations = results.get('reciprocal_violations', [])
        if violations:
            report.append(f"\n3. Нарушения сходимости: {len(violations)}")
            for v in violations[:5]:  # Показываем первые 5
                pair = v.get('pair', ('', ''))
                disc = v.get('discrepancy', 0)
                allow = v.get('allowable', 0)
                report.append(f"   {pair[0]}-{pair[1]}: {disc:.3f} > {allow:.3f}")

        errors = results.get('errors', [])
        if errors:
            report.append(f"\n4. Ошибки: {len(errors)}")
            for err in errors[:3]:
                report.append(f"   {err}")

        text_edit.setPlainText('\n'.join(report))
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec_()
    
    def _adjust_classic(self):
        """Классическое МНК уравнивание"""
        logger.info("=" * 60)
        logger.info("ЗАПУСК КЛАССИЧЕСКОГО МНК УРАВНИВАНИЯ")
        logger.info("=" * 60)

        self.current_adjustment_method = 'classic'

        # Проверка 1: Наличие открытого проекта
        if not self.current_project:
            logger.error("Нет открытого проекта для уравнивания")
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        # Проверка 2: Наличие данных в проекте
        observations = self.current_project.get_observations()
        points = self.current_project.get_points()

        if not observations:
            logger.error("В проекте нет измерений")
            QMessageBox.warning(self, "Предупреждение", "В проекте нет измерений.\n\nВыполните импорт данных из файла или добавьте измерения вручную.")
            return

        if not points:
            logger.error("В проекте нет пунктов")
            QMessageBox.warning(self, "Предупреждение", "В проекте нет пунктов.\n\nВыполните импорт данных из файла или добавьте пункты вручную.")
            return

        # Автоматическая предобработка данных перед уравниванием
        if not hasattr(self.current_project, 'preprocessing_completed') or not self.current_project.preprocessing_completed:
            logger.info("Выполняется автоматическая предобработка перед уравниванием...")

            # Выполняем предобработку синхронно
            try:
                from geoadjust.core.preprocessing.module import PreprocessingModule
                preprocessing = PreprocessingModule(self.current_project)
                results = preprocessing.run_all_stages()

                if results and results.get('success'):
                    self.current_project.preprocessing_completed = True
                    self.current_project.preprocessing_results = results
                    logger.info("Предобработка выполнена успешно")
                else:
                    logger.warning("Предобработка завершилась с предупреждениями")
            except Exception as e:
                logger.error(f"Ошибка при предобработке: {e}")
                QMessageBox.warning(self, "Предупреждение", f"Ошибка при автоматической предобработке:\n{str(e)}")
        
        try:
            logger.info(f"Текущий проект: {self.current_project.name}")
            logger.info("Проверка данных проекта...")
            
            # Получение данных из проекта для проверки
            observations = self.current_project.get_observations()
            control_points = self.current_project.get_points()
            
            logger.info(f"Количество измерений: {len(observations) if observations else 0}")
            logger.info(f"Количество пунктов: {len(control_points) if control_points else 0}")
            
            if not observations:
                logger.error("В проекте нет измерений")
                QMessageBox.warning(self, "Предупреждение", "В проекте нет измерений")
                return
            
            self.mode_label.setText("Режим: уравнивание")
            self.statusBar().showMessage("Выполняется уравнивание...", 0)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            
            logger.info("Создание интеграции обработки...")
            # Создание интеграции обработки если ещё не создана
            if self.processing_integration is None:
                from geoadjust.gui.processing.integration import ProcessingIntegration
                self.processing_integration = ProcessingIntegration(self)
                
                # Подключение сигналов
                self.processing_integration.progress_updated.connect(self._on_progress_updated)
                self.processing_integration.processing_finished.connect(self._on_adjustment_finished)
                self.processing_integration.processing_error.connect(self._on_adjustment_error)
                logger.info("Интеграция обработки создана и настроена")
            
            # Установка моделей данных
            logger.info("Установка моделей данных...")
            # Передаём данные проекта напрямую
            if hasattr(self, 'current_project') and self.current_project:
                # Используем методы проекта для получения данных
                points = self.current_project.get_points() if hasattr(self.current_project, 'get_points') else []
                observations = self.current_project.get_observations() if hasattr(self.current_project, 'get_observations') else []
                logger.info(f"Передаём в уравнивание: {len(points)} пунктов, {len(observations)} измерений")
                self.processing_integration.set_project_data(points, observations)
            else:
                # Передаём таблицы как fallback
                self.processing_integration.set_models(
                    self.points_table,
                    self.observations_table
                )
            
            # Запуск уравнивания в отдельном потоке
            logger.info("Запуск потока обработки...")
            from geoadjust.gui.processing.processing_thread import ProcessingThread
            self.processing_thread = ProcessingThread(self.processing_integration)
            self.processing_thread.finished.connect(self._on_adjustment_finished)
            self.processing_thread.error_occurred.connect(self._on_adjustment_error)
            self.processing_thread.progress_updated.connect(self._on_progress_updated)
            self.processing_thread.start()
            
            logger.info("Поток обработки запущен")
            
        except Exception as e:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при уравнивании: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при уравнивании:\n{str(e)}")
            self.statusBar().showMessage("Ошибка уравнивания", 3000)
            self._reset_ui_state()
    
    def _on_progress_updated(self, percent: int, message: str):
        """Обработчик обновления прогресса"""
        self.progress_bar.setValue(percent)
        self.statusBar().showMessage(message, 0)
    
    def _on_adjustment_finished(self, result: Dict[str, Any]):
        """Обработчик завершения уравнивания"""
        # Добавление метода в результат
        if hasattr(self, 'current_adjustment_method'):
            result['method'] = self.current_adjustment_method
            delattr(self, 'current_adjustment_method')

        # Сохранение результатов в проект
        if self.current_project:
            self.current_project.save_adjustment_result(result)

        # Обновление интерфейса с результатами
        self._update_ui_with_results(result)

        sigma0 = result.get('sigma0', 0)
        method = result.get('method', 'unknown')
        method_name = 'классическое' if method == 'classic' else 'робастное' if method == 'robust' else method
        self.statusBar().showMessage(f"Уравнивание выполнено ({method_name}): μ₀ = {sigma0:.6f}", 5000)

        # Добавление записи в историю
        self._add_history_entry('adjustment_completed', f"Уравнивание выполнено ({method_name}): μ₀ = {sigma0:.6f}", result)

        self._reset_ui_state()
    
    def _on_adjustment_error(self, error_msg: str):
        """Обработчик ошибки уравнивания"""
        # Очистка метода уравнивания при ошибке
        if hasattr(self, 'current_adjustment_method'):
            delattr(self, 'current_adjustment_method')

        QMessageBox.critical(self, "Ошибка", f"Ошибка при уравнивании:\n{error_msg}")
        self.statusBar().showMessage("Ошибка уравнивания", 3000)
        self._reset_ui_state()
    
    def _adjust_robust(self):
        """Робастное уравнивание"""
        logger.info("=" * 60)
        logger.info("ЗАПУСК РОБАСТНОГО УРАВНИВАНИЯ")
        logger.info("=" * 60)

        self.current_adjustment_method = 'robust'

        # Проверка 1: Наличие открытого проекта
        if not self.current_project:
            logger.error("Нет открытого проекта для уравнивания")
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        # Проверка 2: Наличие данных в проекте
        observations = self.current_project.get_observations()
        points = self.current_project.get_points()

        if not observations:
            logger.error("В проекте нет измерений")
            QMessageBox.warning(self, "Предупреждение", "В проекте нет измерений.\n\nВыполните импорт данных из файла или добавьте измерения вручную.")
            return

        if not points:
            logger.error("В проекте нет пунктов")
            QMessageBox.warning(self, "Предупреждение", "В проекте нет пунктов.\n\nВыполните импорт данных из файла или добавьте пункты вручную.")
            return

        # Автоматическая предобработка данных перед уравниванием
        if not hasattr(self.current_project, 'preprocessing_completed') or not self.current_project.preprocessing_completed:
            logger.info("Выполняется автоматическая предобработка перед робастным уравниванием...")

            # Выполняем предобработку синхронно
            try:
                from geoadjust.core.preprocessing.module import PreprocessingModule
                preprocessing = PreprocessingModule(self.current_project)
                results = preprocessing.run_all_stages()

                if results and results.get('success'):
                    self.current_project.preprocessing_completed = True
                    self.current_project.preprocessing_results = results
                    logger.info("Предобработка выполнена успешно")
                else:
                    logger.warning("Предобработка завершилась с предупреждениями")
            except Exception as e:
                logger.error(f"Ошибка при предобработке: {e}")
                QMessageBox.warning(self, "Предупреждение", f"Ошибка при автоматической предобработке:\n{str(e)}")
        
        try:
            self.mode_label.setText("Режим: робастное уравнивание")
            self.statusBar().showMessage("Выполняется робастное уравнивание...", 0)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            
            from geoadjust.core.adjustment.robust_methods import RobustMethods
            
            # Получение данных из проекта
            observations = self.current_project.get_observations()
            control_points = self.current_project.get_points()
            
            if not observations:
                QMessageBox.warning(self, "Предупреждение", "В проекте нет измерений")
                self._reset_ui_state()
                return
            
            # Создание интеграции обработки если ещё не создана
            if self.processing_integration is None:
                from geoadjust.gui.processing.integration import ProcessingIntegration
                self.processing_integration = ProcessingIntegration(self)
                
                # Подключение сигналов
                self.processing_integration.progress_updated.connect(self._on_progress_updated)
                self.processing_integration.processing_finished.connect(self._on_adjustment_finished)
                self.processing_integration.processing_error.connect(self._on_adjustment_error)
            
            # Установка моделей данных
            self.processing_integration.set_models(
                self.points_table.model(),
                self.observations_table.model()
            )
            
            # Запуск робастного уравнивания в отдельном потоке
            from geoadjust.gui.processing.processing_thread import ProcessingThread
            self.processing_thread = ProcessingThread(
                self.processing_integration,
                method='robust'
            )
            self.processing_thread.finished.connect(self._on_adjustment_finished)
            self.processing_thread.error_occurred.connect(self._on_adjustment_error)
            self.processing_thread.progress_updated.connect(self._on_progress_updated)
            self.processing_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при робастном уравнивании:\n{str(e)}")
            logger.error(f"Ошибка при робастном уравнивании: {e}", exc_info=True)
            self.statusBar().showMessage("Ошибка уравнивания", 3000)
            self._reset_ui_state()
    
    def _reset_ui_state(self):
        """Сброс UI в исходное состояние"""
        self.mode_label.setText("Режим: ожидание")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)

    def _show_status_indicator(self, status: str, message: str, duration: int = 3000):
        """Показать статусный индикатор в статусной строке"""
        # Создаем виджет индикатора
        indicator = VisualIndicator.create_status_indicator(status, message)

        # Добавляем в статусную строку (временно, заменяя обычное сообщение)
        # Для постоянного отображения можно добавить отдельный виджет в статусную строку
        self.statusBar().showMessage(message, duration)

        # В будущем можно добавить постоянный виджет:
        # if not hasattr(self, 'status_indicator'):
        #     self.status_indicator = QWidget()
        #     self.statusBar().addPermanentWidget(self.status_indicator)
        #
        # layout = QHBoxLayout(self.status_indicator)
        # layout.addWidget(indicator)
    
    def _update_ui_with_results(self, result: Dict[str, Any]):
        """Обновление интерфейса результатами уравнивания
        
        Args:
            result: Словарь с результатами уравнивания
        """
        # Обновление таблицы пунктов
        if hasattr(self, 'points_table') and 'adjusted_points' in result:
            self.points_table.update_data(result['adjusted_points'])
        
        # Обновление таблицы измерений
        if hasattr(self, 'observations_table') and 'residuals' in result:
            self.observations_table.update_residuals(result['residuals'])
        
        # Перерисовка плана с результатами уравнивания
        if hasattr(self, 'plan_view'):
            self.plan_view.draw_network(self.current_project)
            
            # Отрисовка эллипсов ошибок (если есть)
            if 'accuracy' in result and 'error_ellipses' in result['accuracy']:
                self.plan_view.draw_error_ellipses(result['accuracy']['error_ellipses'])
    
    def _import_file(self):
        """Импорт данных из файла"""
        logger.info("=" * 60)
        logger.info("ЗАПУСК ИМПОРТА ДАННЫХ ИЗ ФАЙЛА")
        logger.info("=" * 60)
        
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или откройте проект")
            return
        
        try:
            from .dialogs.import_dialog import ImportDialog

            dialog = ImportDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                imported_data = dialog.get_imported_data()
                if imported_data:
                    self._process_imported_data(imported_data)

        except Exception as e:
            logger.error(f"Ошибка при открытии диалога импорта: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог импорта:\n{str(e)}")

    def _process_imported_data(self, imported_data):
        """Обработка импортированных данных"""
        try:
            # Проверяем, что проект существует
            if not self.current_project:
                return

            # Добавление данных в проект
            points = imported_data.get('points', [])
            observations = imported_data.get('observations', [])

            # Обновление проекта
            if points:
                for point in points:
                    self.current_project.add_point(point)

            if observations:
                for obs in observations:
                    # Конвертируем объект Observation в словарь
                    try:
                        # Для dataclass используем asdict
                        from dataclasses import asdict
                        obs_dict = asdict(obs)
                    except (TypeError, ImportError):
                        # Для обычных объектов используем vars или __dict__
                        if hasattr(obs, '__dict__'):
                            obs_dict = vars(obs)
                        elif hasattr(obs, '__annotations__'):
                            obs_dict = {k: getattr(obs, k) for k in obs.__annotations__}
                        else:
                            obs_dict = dict(obs) if hasattr(obs, 'keys') else obs

                    self.current_project.add_observation(obs_dict)

            # Обновление интерфейса
            self._refresh_data_views()

            # Обновление станций, если есть данные о сессиях
            station_sessions = imported_data.get('station_sessions', [])
            if not station_sessions and imported_data.get('format') == 'SDR':
                # Для SDR создать station_sessions из setups
                setups = imported_data.get('setups', [])
                station_sessions = []
                for setup in setups:
                    session = {
                        'session_id': getattr(setup, 'setup_id', f"SETUP_{len(station_sessions)}"),
                        'station_name': getattr(setup, 'station_name', 'UNKNOWN'),
                        'instrument_height': getattr(setup, 'instrument_height', None),
                        'temperature': getattr(setup, 'temperature', None),
                        'pressure': getattr(setup, 'pressure', None),
                        'num_observations': len([obs for obs in observations if getattr(obs, 'setup_id', None) == getattr(setup, 'setup_id', None)])
                    }
                    station_sessions.append(session)
                imported_data['station_sessions'] = station_sessions

            if station_sessions and hasattr(self, '_update_stations_view'):
                self._update_stations_view(station_sessions)

            # Обновление ходов, если есть данные о ходах
            leveling_courses = imported_data.get('leveling_courses', [])
            if leveling_courses:
                # Конвертируем измерения ходов в словари
                converted_courses = []
                for course in leveling_courses:
                    converted_course = {
                        'course_id': course['course_id'],
                        'section_number': course.get('section_number', 1),
                        'stations': course.get('stations', []),
                        'measurements': course.get('measurements', [])
                    }
                    converted_courses.append(converted_course)

                self.leveling_courses = converted_courses
                self.left_panel.update_courses(converted_courses)

                # Добавляем leveling_courses в preprocessing_result для отображения в дереве
                if not hasattr(self.current_project, 'preprocessing_result') or self.current_project.preprocessing_result is None:
                    self.current_project.preprocessing_result = {}
                if 'traverses' not in self.current_project.preprocessing_result:
                    self.current_project.preprocessing_result['traverses'] = {}
                self.current_project.preprocessing_result['traverses']['sections'] = converted_courses

                # Обновляем дерево ходов
                if hasattr(self, '_update_traverses_tree'):
                    self._update_traverses_tree()

            # Обновление левой панели после импорта
            self._refresh_data_views()

            # Обновление станций в левой панели
            if station_sessions:
                if hasattr(self.left_panel, 'update_stations'):
                    self.left_panel.update_stations(station_sessions)

            logger.info(f"Импортировано: {len(points)} пунктов, {len(observations)} измерений")
            self.statusBar().showMessage(
                f"Импортировано: {len(points)} пунктов, {len(observations)} измерений",
                5000
            )
                
        except Exception as e:
            logger.error(f"ОШИБКА при импорте файла: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при импорте:\n{str(e)}")
    
    def _export_file(self):
        """Экспорт данных в файл"""
        logger.info("=" * 60)
        logger.info("ЗАПУСК ЭКСПОРТА ДАННЫХ В ФАЙЛ")
        logger.info("=" * 60)
        
        if not self.current_project:
            logger.warning("Нет открытого проекта для экспорта")
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from .dialogs.export_dialog import ExportDialog
            
            dialog = ExportDialog(self.current_project, self)
            dialog.exec_()
                
        except Exception as e:
            logger.error(f"ОШИБКА при экспорте файла: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте:\n{str(e)}")
    

    def _copy_selected(self):
        """Копирование выбранных данных"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        # Копирование из текущей активной таблицы
        copied_data = []

        # Проверяем таблицу пунктов
        if hasattr(self, 'points_table'):
            selected_rows = set()
            for index in self.points_table.selectionModel().selectedRows():
                selected_rows.add(index.row())

            if selected_rows:
                points = self.current_project.get_points()
                for row in selected_rows:
                    if row < len(points):
                        point_data = list(points.values())[row]
                        copied_data.append({
                            'type': 'point',
                            'data': point_data
                        })

        # Проверяем таблицу измерений
        if hasattr(self, 'observations_table') and hasattr(self.observations_table, 'get_selected_observations'):
            selected_obs = self.observations_table.get_selected_observations()
            if selected_obs:
                for obs in selected_obs:
                    copied_data.append({
                        'type': 'observation',
                        'data': obs
                    })

        if copied_data:
            import json
            # Сохраняем в буфер обмена
            clipboard_data = json.dumps(copied_data)
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_data)

            self.statusBar().showMessage(f"Скопировано {len(copied_data)} элементов", 2000)
            logger.info(f"Скопировано {len(copied_data)} элементов в буфер обмена")
        else:
            self.statusBar().showMessage("Ничего не выбрано для копирования", 2000)

    def _paste_data(self):
        """Вставка данных из буфера обмена"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()

        if not clipboard_text:
            self.statusBar().showMessage("Буфер обмена пуст", 2000)
            return

        try:
            import json
            pasted_data = json.loads(clipboard_text)

            points_added = 0
            observations_added = 0

            for item in pasted_data:
                if item['type'] == 'point':
                    # Генерируем новое имя для пункта
                    original_name = item['data'].get('name', 'POINT')
                    new_name = original_name
                    counter = 1
                    while new_name in self.current_project.get_points():
                        new_name = f"{original_name}_{counter}"
                        counter += 1

                    point_data = item['data'].copy()
                    point_data['name'] = new_name
                    self.current_project.add_point(point_data)
                    points_added += 1

                elif item['type'] == 'observation':
                    obs_data = item['data'].copy()
                    # Генерируем новый ID для измерения
                    obs_data['obs_id'] = f"COPY_{len(self.current_project.get_observations())}"
                    self.current_project.add_observation(obs_data)
                    observations_added += 1

            if points_added or observations_added:
                self._refresh_data_views()
                self.statusBar().showMessage(f"Вставлено: {points_added} пунктов, {observations_added} измерений", 3000)
                logger.info(f"Вставлено: {points_added} пунктов, {observations_added} измерений")
            else:
                self.statusBar().showMessage("Ничего не вставлено", 2000)

        except (json.JSONDecodeError, KeyError) as e:
            self.statusBar().showMessage("Ошибка вставки данных", 2000)
            logger.error(f"Ошибка вставки данных: {e}")


    def _add_point(self):
        """Добавление нового пункта"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или откройте проект")
            return
        
        from .dialogs.point_editor import PointEditorDialog
        
        dialog = PointEditorDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            point_data = dialog.get_point_data()
            self.current_project.add_point(point_data)
            self._refresh_data_views()
            logger.info(f"Добавлен пункт: {point_data['name']}")
    
    def _edit_point(self, point_data: Dict[str, Any]):
        """Редактирование пункта"""
        from .dialogs.point_editor import PointEditorDialog
        
        dialog = PointEditorDialog(point_data=point_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_point_data()
            self.current_project.update_point(updated_data)
            self._refresh_data_views()
            logger.info(f"Обновлен пункт: {updated_data['name']}")
    
    def _delete_point(self, point_name: str):
        """Удаление пункта"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить пункт '{point_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.current_project.delete_point(point_name)
            self._refresh_data_views()
            logger.info(f"Удален пункт: {point_name}")
    
    def _add_observation(self):
        """Добавление нового измерения"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или откройте проект")
            return
        
        from .dialogs.observation_editor import ObservationEditorDialog
        
        # Получение списка доступных пунктов
        points = self.current_project.get_points()
        point_names = [p['name'] for p in points] if points else []
        
        dialog = ObservationEditorDialog(available_points=point_names, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            obs_data = dialog.get_observation_data()
            self.current_project.add_observation(obs_data)
            self._refresh_data_views()
            logger.info(f"Добавлено измерение: {obs_data['from_point']} -> {obs_data['to_point']}")
    
    def _edit_observation(self, obs_data: Dict[str, Any]):
        """Редактирование измерения"""
        from .dialogs.observation_editor import ObservationEditorDialog
        
        points = self.current_project.get_points()
        point_names = [p['name'] for p in points] if points else []
        
        dialog = ObservationEditorDialog(
            observation_data=obs_data,
            available_points=point_names,
            parent=self
        )
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_observation_data()
            self.current_project.update_observation(updated_data)
            self._refresh_data_views()
            logger.info(f"Обновлено измерение")
    
    def _delete_observation(self, obs_id: int):
        """Удаление измерения"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить измерение?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.current_project.delete_observation(obs_id)
            self._refresh_data_views()
            logger.info(f"Удалено измерение")
    
    def _show_scheme(self):
        """Показать схему сети"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        from .dialogs.scheme_viewer import SchemeViewerDialog
        
        dialog = SchemeViewerDialog(project=self.current_project, parent=self)
        dialog.exec_()
    
    def _refresh_data_views(self):
        """Обновление всех представлений данных"""
        if self.current_project:
            # Обновление таблицы пунктов
            points = self.current_project.get_points()
            if points and hasattr(self, 'points_table'):
                self.points_table.update_data(points)

            # Обновление таблицы измерений
            observations = self.current_project.get_observations()
            logger.info(f"_refresh_data_views: got {len(observations)} observations from project")
            if observations and hasattr(self, 'observations_table'):
                # Конвертируем словари обратно в объекты CombinedObservation
                converted_observations = self._convert_observations_to_objects(observations)
                self.observations_table.update_data(converted_observations)
    
    def _check_tolerances(self):
        """Контроль допусков"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from geoadjust.core.preprocessing.tolerances import ToleranceChecker
            
            checker = ToleranceChecker()
            observations = self.current_project.get_observations()
            
            if not observations:
                QMessageBox.information(self, "Информация", "В проекте нет измерений")
                return
            
            results = checker.check_all(observations)
            
            # Показать результаты
            violations = [r for r in results if not r['passed']]
            
            if violations:
                msg = f"Обнаружено {len(violations)} нарушений допусков:\n\n"
                for v in violations[:10]:  # Первые 10
                    msg += f"- {v['description']}\n"
                
                if len(violations) > 10:
                    msg += f"\n... и еще {len(violations) - 10}"
                
                QMessageBox.warning(self, "Нарушения допусков", msg)
            else:
                QMessageBox.information(self, "Контроль допусков", "Все измерения в пределах допусков")
            
            logger.info(f"Контроль допусков: {len(violations)} нарушений из {len(results)}")
            
        except Exception as e:
            logger.error(f"Ошибка контроля допусков: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка контроля допусков:\n{str(e)}")
    
    def _apply_corrections(self):
        """Применение редукций"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from geoadjust.core.preprocessing.module import PreprocessingModule
            
            preprocessor = PreprocessingModule()
            observations = self.current_project.get_observations()
            
            if not observations:
                QMessageBox.information(self, "Информация", "В проекте нет измерений")
                return
            
            # Применение редукций
            corrected_obs = preprocessor.apply_corrections(observations)
            
            # Обновление измерений в проекте
            for obs in corrected_obs:
                self.current_project.update_observation(obs)
            
            self._refresh_data_views()
            
            QMessageBox.information(
                self,
                "Редукции применены",
                f"Редукции применены к {len(corrected_obs)} измерениям"
            )
            
            logger.info(f"Применены редукции к {len(corrected_obs)} измерениям")
            
        except Exception as e:
            logger.error(f"Ошибка применения редукций: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка применения редукций:\n{str(e)}")
    
    def _baarda_analysis(self):
        """Анализ надёжности по Баарду"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        # Проверка наличия результатов уравнивания
        if not hasattr(self.current_project, 'adjustment_result') or not self.current_project.adjustment_result:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Не найдены результаты уравнивания.\n\n"
                "Сначала выполните уравнивание сети:\n"
                "• Классическое МНК уравнивание\n"
                "• Робастное уравнивание"
            )
            return

        try:
            from geoadjust.core.reliability.baarda_method import BaardaMethod

            baarda = BaardaMethod()
            result = baarda.analyze(self.current_project.adjustment_result)
            
            # Показать результаты
            msg = f"Анализ надёжности по Баарду:\n\n"
            msg += f"Внутренняя надёжность: {result.get('internal_reliability', 'N/A')}\n"
            msg += f"Внешняя надёжность: {result.get('external_reliability', 'N/A')}\n"
            msg += f"Обнаружено подозрительных измерений: {len(result.get('suspicious', []))}"
            
            QMessageBox.information(self, "Анализ по Баарду", msg)
            
            logger.info("Выполнен анализ надёжности по Баарду")
            
        except Exception as e:
            logger.error(f"Ошибка анализа по Баарду: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка анализа:\n{str(e)}")
    
    def _gross_error_search(self):
        """Поиск грубых ошибок"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from geoadjust.core.analysis.gross_errors import GrossErrorAnalyzer
            
            if not hasattr(self.current_project, 'adjustment_result'):
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Сначала выполните уравнивание сети"
                )
                return
            
            # Получение данных из результатов уравнивания
            result = self.current_project.adjustment_result
            A = result.get('A')
            P = result.get('P')
            V = result.get('residuals')
            sigma0 = result.get('sigma0')
            obs_ids = result.get('observations_ids', [])
            
            if A is None or P is None or V is None:
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Недостаточно данных для анализа грубых ошибок"
                )
                return
            
            analyzer = GrossErrorAnalyzer(A, P, V, sigma0, obs_ids)
            errors = analyzer.detect_gross_errors()
            
            if errors:
                msg = f"Обнаружено {len(errors)} грубых ошибок:\n\n"
                for err in errors[:10]:
                    msg += f"- {err['description']}\n"
                
                if len(errors) > 10:
                    msg += f"\n... и еще {len(errors) - 10}"
                
                QMessageBox.warning(self, "Грубые ошибки", msg)
            else:
                QMessageBox.information(self, "Поиск грубых ошибок", "Грубых ошибок не обнаружено")
            
            logger.info(f"Поиск грубых ошибок: обнаружено {len(errors)}")
            
        except Exception as e:
            logger.error(f"Ошибка поиска грубых ошибок: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка поиска:\n{str(e)}")
    
    def _error_ellipses(self):
        """Визуализация эллипсов ошибок"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from geoadjust.core.analysis.visualization import Visualization
            
            if not hasattr(self.current_project, 'adjustment_result'):
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Сначала выполните уравнивание сети"
                )
                return
            
            # Получение данных о пунктах из результатов
            result = self.current_project.adjustment_result
            points = result.get('points', [])
            
            visualizer = Visualization()
            fig = visualizer.plot_error_ellipses(points, show=False)
            
            # Сохранение и показ
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            fig.savefig(temp_file.name, dpi=150, bbox_inches='tight')
            
            # Открыть в системном просмотрщике
            import os
            os.startfile(temp_file.name)
            
            logger.info("Визуализация эллипсов ошибок создана")
            
        except Exception as e:
            logger.error(f"Ошибка визуализации: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка визуализации:\n{str(e)}")
    
    def _heatmaps(self):
        """Визуализация тепловых карт"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from geoadjust.core.analysis.visualization import Visualization
            
            if not hasattr(self.current_project, 'adjustment_result'):
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Сначала выполните уравнивание сети"
                )
                return
            
            # Получение ковариационной матрицы из результатов
            result = self.current_project.adjustment_result
            cov_matrix = result.get('covariance_matrix')
            labels = result.get('point_ids', [])
            
            if cov_matrix is None:
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Ковариационная матрица недоступна"
                )
                return
            
            visualizer = Visualization()
            fig = visualizer.plot_correlation_heatmap(cov_matrix, labels=labels, show=False)
            
            # Сохранение и показ
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            fig.savefig(temp_file.name, dpi=150, bbox_inches='tight')
            
            # Открыть в системном просмотрщике
            import os
            os.startfile(temp_file.name)
            
            logger.info("Тепловая карта создана")
            
        except Exception as e:
            logger.error(f"Ошибка визуализации: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка визуализации:\n{str(e)}")
    
    def _coordinate_schedule(self):
        """Формирование ведомости координат"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        # Проверка наличия результатов уравнивания
        if not hasattr(self.current_project, 'adjustment_result') or not self.current_project.adjustment_result:
            reply = QMessageBox.question(
                self,
                "Рекомендация",
                "Результаты уравнивания не найдены.\n\n"
                "Ведомость координат будет содержать только исходные данные.\n"
                "Для получения уравненных координат выполните:\n"
                "• Классическое МНК уравнивание\n"
                "• Робастное уравнивание\n\n"
                "Продолжить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.No:
                return

        try:
            from geoadjust.core.reporting.reports import ReportGenerator

            generator = ReportGenerator()
            adjustment_result = getattr(self.current_project, 'adjustment_result', None)

            # Выбор файла для сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить ведомость координат",
                f"{self.current_project.name}_coordinates_report.html",
                "HTML файлы (*.html);;Все файлы (*)"
            )

            if file_path:
                # Генерируем HTML отчет
                html_content = generator.generate_coordinates_report(self.current_project, adjustment_result)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                QMessageBox.information(
                    self,
                    "Успех",
                    f"Ведомость координат сохранена:\n{file_path}\n\n"
                    "Отчет открывается в веб-браузере."
                )
                logger.info(f"Ведомость координат сохранена: {file_path}")

                # Предлагаем открыть файл
                import subprocess
                import platform
                try:
                    if platform.system() == 'Windows':
                        subprocess.run(['start', file_path], shell=True)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', file_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', file_path])
                except Exception as e:
                    logger.warning(f"Не удалось автоматически открыть файл: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования ведомости координат: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования ведомости координат:\n{str(e)}")
    
    def _topology_schedule(self):
        """Формирование ведомости топологии сети"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        # Проверка наличия данных в проекте
        observations = self.current_project.get_observations()
        if not observations:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "В проекте нет измерений.\n\n"
                "Для формирования ведомости топологии сети необходимо:\n"
                "• Импортировать данные из SDR файла\n"
                "• Добавить измерения вручную"
            )
            return

        try:
            from geoadjust.core.reporting.reports import ReportGenerator

            generator = ReportGenerator()
            adjustment_result = getattr(self.current_project, 'adjustment_result', None)

            # Выбор файла для сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить ведомость топологии сети",
                f"{self.current_project.name}_topology_report.html",
                "HTML файлы (*.html);;Все файлы (*)"
            )

            if file_path:
                # Генерируем HTML отчет
                html_content = generator.generate_topology_report(self.current_project, adjustment_result)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                QMessageBox.information(
                    self,
                    "Успех",
                    f"Ведомость топологии сети сохранена:\n{file_path}\n\n"
                    "Отчет открывается в веб-браузере."
                )
                logger.info(f"Ведомость топологии сети сохранена: {file_path}")

                # Предлагаем открыть файл
                import subprocess
                import platform
                try:
                    if platform.system() == 'Windows':
                        subprocess.run(['start', file_path], shell=True)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', file_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', file_path])
                except Exception as e:
                    logger.warning(f"Не удалось автоматически открыть файл: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования ведомости топологии: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования ведомости топологии:\n{str(e)}")

    def _accuracy_schedule(self):
        """Формирование ведомости оценки точности"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        # Проверка наличия результатов уравнивания
        if not hasattr(self.current_project, 'adjustment_result') or not self.current_project.adjustment_result:
            reply = QMessageBox.question(
                self,
                "Рекомендация",
                "Результаты уравнивания не найдены.\n\n"
                "Ведомость оценки точности будет содержать только априорные оценки.\n"
                "Для получения точных оценок выполните:\n"
                "• Классическое МНК уравнивание\n"
                "• Робастное уравнивание\n\n"
                "Продолжить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.No:
                return

        try:
            from geoadjust.core.reporting.reports import ReportGenerator

            generator = ReportGenerator()
            adjustment_result = getattr(self.current_project, 'adjustment_result', None)

            # Выбор файла для сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить ведомость оценки точности",
                f"{self.current_project.name}_accuracy_report.html",
                "HTML файлы (*.html);;Все файлы (*)"
            )

            if file_path:
                # Генерируем HTML отчет
                html_content = generator.generate_accuracy_report(self.current_project, adjustment_result)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                QMessageBox.information(
                    self,
                    "Успех",
                    f"Ведомость оценки точности сохранена:\n{file_path}\n\n"
                    "Отчет открывается в веб-браузере."
                )
                logger.info(f"Ведомость оценки точности сохранена: {file_path}")

                # Предлагаем открыть файл
                import subprocess
                import platform
                try:
                    if platform.system() == 'Windows':
                        subprocess.run(['start', file_path], shell=True)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', file_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', file_path])
                except Exception as e:
                    logger.warning(f"Не удалось автоматически открыть файл: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования ведомости точности: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования ведомости точности:\n{str(e)}")

    def _correction_schedule(self):
        """Формирование ведомости поправок"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return

        try:
            from geoadjust.io.export.dynadjust_report import ReportGenerator

            if not hasattr(self.current_project, 'adjustment_result'):
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Сначала выполните уравнивание сети"
                )
                return

            generator = ReportGenerator()

            # Выбор файла для сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить ведомость поправок",
                "",
                "PDF файлы (*.pdf);;Excel файлы (*.xlsx);;Все файлы (*)"
            )

            if file_path:
                generator.generate_correction_schedule(
                    self.current_project.adjustment_result,
                    file_path
                )
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Ведомость поправок сохранена:\n{file_path}"
                )
                logger.info(f"Ведомость поправок сохранена: {file_path}")

        except Exception as e:
            logger.error(f"Ошибка формирования ведомости: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования ведомости:\n{str(e)}")
    
    def _gost_report(self):
        """Формирование отчёта по ГОСТ"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from geoadjust.io.export.gost_report import GOSTReportGenerator
            
            if not hasattr(self.current_project, 'adjustment_result'):
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Сначала выполните уравнивание сети"
                )
                return
            
            generator = GOSTReportGenerator()
            
            # Выбор файла для сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить отчёт по ГОСТ",
                "",
                "PDF файлы (*.pdf);;DOCX файлы (*.docx);;Все файлы (*)"
            )
            
            if file_path:
                generator.generate_report(
                    self.current_project,
                    self.current_project.adjustment_result,
                    file_path
                )
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Отчёт по ГОСТ 7.32-2017 сохранён:\n{file_path}"
                )
                logger.info(f"Отчёт по ГОСТ сохранён: {file_path}")
            
        except Exception as e:
            logger.error(f"Ошибка формирования отчёта: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчёта:\n{str(e)}")
    
    def _compliance_certificate(self):
        """Формирование сертификата соответствия"""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        
        try:
            from geoadjust.io.export.gost_report import GOSTReportGenerator
            
            if not hasattr(self.current_project, 'adjustment_result'):
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Сначала выполните уравнивание сети"
                )
                return
            
            generator = GOSTReportGenerator()
            
            # Выбор файла для сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить сертификат соответствия",
                "",
                "PDF файлы (*.pdf);;Все файлы (*)"
            )
            
            if file_path:
                generator.generate_compliance_certificate(
                    self.current_project,
                    self.current_project.adjustment_result,
                    file_path
                )
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Сертификат соответствия сохранён:\n{file_path}"
                )
                logger.info(f"Сертификат соответствия сохранён: {file_path}")
            
        except Exception as e:
            logger.error(f"Ошибка формирования сертификата: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования сертификата:\n{str(e)}")
    
    def _show_help(self):
        """Показать справку"""
        QMessageBox.information(self, "Справка", "Справка по программе GeoAdjust Pro")
    
    def _about_program(self):
        """О программе"""
        QMessageBox.about(
            self,
            "О программе",
            "GeoAdjust Pro\nВерсия 1.0\n\nПрограмма для обработки геодезических измерений"
        )
    
    # Методы для переключения панелей
    def _toggle_stations_dock(self, checked: bool):
        """Показать/скрыть панель станций"""
        if hasattr(self, 'stations_dock'):
            self.stations_dock.setVisible(checked)

    def _toggle_points_dock(self, checked: bool):
        """Показать/скрыть панель пунктов ПВО"""
        if hasattr(self, 'points_dock'):
            self.points_dock.setVisible(checked)
    
    def _toggle_observations_dock(self, checked: bool):
        """Показать/скрыть панель измерений"""
        if hasattr(self, 'observations_dock'):
            self.observations_dock.setVisible(checked)
    
    def _toggle_traverses_dock(self, checked: bool):
        """Показать/скрыть панель ходов и секций"""
        if hasattr(self, 'traverses_dock'):
            self.traverses_dock.setVisible(checked)
    
    def _toggle_log_dock(self, checked: bool):
        """Показать/скрыть панель журнала"""
        if hasattr(self, 'log_dock'):
            self.log_dock.setVisible(checked)
    
    def _toggle_properties_dock(self, checked: bool):
        """Показать/скрыть панель свойств"""
        if hasattr(self, 'properties_dock'):
            self.properties_dock.setVisible(checked)
    
    # Обработчики изменения видимости док-виджетов
    def _on_left_panel_dock_visibility_changed(self, visible: bool):
        """Обработка изменения видимости левой панели"""
        if hasattr(self, 'left_panel_dock_action'):
            self.left_panel_dock_action.setChecked(visible)

    def _on_observations_dock_visibility_changed(self, visible: bool):
        """Обработка изменения видимости панели измерений"""
        if hasattr(self, 'observations_dock_action'):
            self.observations_dock_action.setChecked(visible)
    
    def _on_log_dock_visibility_changed(self, visible: bool):
        """Обработка изменения видимости панели журнала"""
        if hasattr(self, 'log_dock_action'):
            self.log_dock_action.setChecked(visible)
    
    def _on_properties_dock_visibility_changed(self, visible: bool):
        """Обработка изменения видимости панели свойств"""
        if hasattr(self, 'properties_dock_action'):
            self.properties_dock_action.setChecked(visible)

    def _on_station_selected_from_panel(self, station_id: str):
        """Обработка выбора станции из левой панели"""
        # Фильтруем измерения по станции
        if hasattr(self, 'observations_table'):
            self.observations_table.filter_by_station_session(station_id or None)

    def _on_course_selected_from_panel(self, course_id: str):
        """Обработка выбора хода из левой панели"""
        # Если выбрано "Все ходы" или сброс, показываем все измерения
        if course_id == "ALL_COURSES" or course_id is None:
            if hasattr(self, 'observations_table'):
                self._refresh_data_views()
            self.statusBar().showMessage("Показаны все измерения", 3000)
            return

        # Найдем измерения для выбранного хода
        course_measurements = []
        if hasattr(self, 'leveling_courses') and self.leveling_courses:
            for course in self.leveling_courses:
                if course.get('course_id') == course_id:
                    course_measurements = course.get('measurements', [])
                    break

        # Фильтруем наблюдения по измерениям хода
        if course_measurements and self.current_project:
            # Получаем все наблюдения
            all_observations = self.current_project.get_observations()

            # Создаем маппинг измерений хода для быстрого поиска
            course_obs_ids = set()
            for meas in course_measurements:
                # Создаем идентификатор на основе from_point и to_point
                if isinstance(meas, dict):
                    obs_key = f"{meas.get('from_point', '')}_{meas.get('to_point', '')}"
                else:
                    obs_key = f"{getattr(meas, 'from_point', '')}_{getattr(meas, 'to_point', '')}"
                course_obs_ids.add(obs_key)

            # Фильтруем наблюдения
            filtered_observations = []
            for obs in all_observations:
                if isinstance(obs, dict):
                    obs_key = f"{obs.get('from_point', '')}_{obs.get('to_point', '')}"
                    obs_type = obs.get('obs_type', '')
                else:
                    obs_key = f"{getattr(obs, 'from_point', '')}_{getattr(obs, 'to_point', '')}"
                    obs_type = getattr(obs, 'obs_type', '')

                if obs_key in course_obs_ids and obs_type == 'leveling_height_diff':
                    filtered_observations.append(obs)

            # Обновляем таблицу измерений только с измерениями выбранного хода
            if hasattr(self, 'observations_table'):
                converted_filtered = self._convert_observations_to_objects(filtered_observations)
                self.observations_table.set_observations(converted_filtered)

                # Автоматически переключаемся на вкладку нивелирования
                if hasattr(self.observations_table, 'tabs'):
                    for i in range(self.observations_table.tabs.count()):
                        tab_text = self.observations_table.tabs.tabText(i)
                        if "нивелир" in tab_text.lower():
                            self.observations_table.tabs.setCurrentIndex(i)
                            break

        self.statusBar().showMessage(f"Показаны измерения хода {course_id}", 3000)
    
    def _restore_all_panels(self):
        """Восстановить все панели"""
        # Показать все док-виджеты
        if hasattr(self, 'stations_dock'):
            self.stations_dock.setVisible(True)
            self.stations_dock_action.setChecked(True)

        if hasattr(self, 'points_dock'):
            self.points_dock.setVisible(True)
            self.points_dock_action.setChecked(True)
        
        if hasattr(self, 'observations_dock'):
            self.observations_dock.setVisible(True)
            self.observations_dock_action.setChecked(True)
        
        if hasattr(self, 'traverses_dock'):
            self.traverses_dock.setVisible(True)
            self.traverses_dock_action.setChecked(True)
        
        if hasattr(self, 'log_dock'):
            self.log_dock.setVisible(True)
            self.log_dock_action.setChecked(True)
        
        if hasattr(self, 'properties_dock'):
            self.properties_dock.setVisible(True)
            self.properties_dock_action.setChecked(True)
        
        self.statusBar().showMessage("Все панели восстановлены", 3000)
        logger.info("Все панели восстановлены")
