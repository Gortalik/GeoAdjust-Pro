# -*- coding: utf-8 -*-
"""
Объединенный виджет для левой панели с переключением
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QLabel, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

class LeftPanelWidget(QWidget):
    """Объединенный виджет для левой панели с переключением между станциями, ходами и пунктами ПВО"""

    # Сигналы для связи с главным окном
    station_selected = pyqtSignal(str)
    point_selected = pyqtSignal(str)
    course_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Панель переключения
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(2)

        # Кнопки переключения
        self.stations_btn = QPushButton("Станции")
        self.stations_btn.setCheckable(True)
        self.stations_btn.setChecked(True)
        self.stations_btn.clicked.connect(lambda: self.switch_to_tab(0))

        self.courses_btn = QPushButton("Ходы")
        self.courses_btn.setCheckable(True)
        self.courses_btn.clicked.connect(lambda: self.switch_to_tab(1))

        self.points_btn = QPushButton("Пункты ПВО")
        self.points_btn.setCheckable(True)
        self.points_btn.clicked.connect(lambda: self.switch_to_tab(2))

        buttons_layout.addWidget(self.stations_btn)
        buttons_layout.addWidget(self.courses_btn)
        buttons_layout.addWidget(self.points_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Стекированный виджет для содержимого
        self.stack = QStackedWidget()

        # Вкладка станций
        self.stations_widget = self.create_stations_tab()
        self.stack.addWidget(self.stations_widget)

        # Вкладка ходов
        self.courses_widget = self.create_courses_tab()
        self.stack.addWidget(self.courses_widget)

        # Вкладка пунктов ПВО
        self.points_widget = self.create_points_tab()
        self.stack.addWidget(self.points_widget)

        layout.addWidget(self.stack)

        # Настройка стилей
        self.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
            }
            QPushButton:checked {
                background-color: #e0e0e0;
                border: 1px solid #999;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)

    def create_stations_tab(self):
        """Создание вкладки станций"""
        from ..widgets.stations_widget import StationsDockContent

        # Создаем контейнер для совместимости с существующим кодом
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Создаем виджет станций
        self.stations_content = StationsDockContent(self)
        layout.addWidget(self.stations_content)

        return widget

    def create_courses_tab(self):
        """Создание вкладки ходов"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Заголовок
        title = QLabel("Нивелирные ходы")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        # Дерево ходов
        self.courses_tree = QTreeWidget()
        self.courses_tree.setHeaderLabel("Ходы и измерения")
        self.courses_tree.itemClicked.connect(self._on_course_item_clicked)

        # Добавляем корневой элемент
        root = QTreeWidgetItem(self.courses_tree)
        root.setText(0, "Нивелирные ходы")
        root.setExpanded(True)

        layout.addWidget(self.courses_tree)

        return widget

    def create_points_tab(self):
        """Создание вкладки пунктов ПВО"""
        from ..components.tables import PointsTableView

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Создаем таблицу пунктов
        self.points_table = PointsTableView()
        layout.addWidget(self.points_table)

        return widget

    def switch_to_tab(self, index):
        """Переключение на вкладку"""
        self.stack.setCurrentIndex(index)

        # Обновляем состояние кнопок
        self.stations_btn.setChecked(index == 0)
        self.courses_btn.setChecked(index == 1)
        self.points_btn.setChecked(index == 2)

    def update_stations(self, stations_data):
        """Обновление данных станций"""
        # Сохраняем mapping от имени станции к session_id для фильтрации
        self._station_to_session = {session.get('station_name', ''): session.get('session_id', '') for session in stations_data or []}

        if hasattr(self.stations_content, 'update_stations'):
            self.stations_content.update_stations(stations_data)

    def update_courses(self, courses_data):
        """Обновление данных ходов"""
        self.courses_tree.clear()

        root = QTreeWidgetItem(self.courses_tree)
        root.setText(0, "Нивелирные ходы")
        root.setExpanded(True)

        for course in courses_data or []:
            course_item = QTreeWidgetItem(root)
            course_item.setText(0, f"Ход {course['course_id']}")

            # Добавляем станции хода
            for station in course.get('stations', []):
                station_item = QTreeWidgetItem(course_item)
                station_item.setText(0, f"Станция: {station}")

            # Добавляем измерения хода
            measurements_item = QTreeWidgetItem(course_item)
            measurements_item.setText(0, f"Измерения ({len(course.get('measurements', []))})")

            for measurement in course.get('measurements', []):
                # measurement - словарь после конвертации в main_window.py
                if isinstance(measurement, dict):
                    from_point = measurement.get('from_point', 'unknown')
                    to_point = measurement.get('to_point', 'unknown')
                    value = measurement.get('value', 0.0)
                    meas_item = QTreeWidgetItem(measurements_item)
                    meas_item.setText(0, f"{from_point} → {to_point}: {value:.6f}")

        self.courses_tree.expandAll()

    def update_points(self, points_data):
        """Обновление данных пунктов ПВО"""
        if hasattr(self.points_table, 'set_points'):
            self.points_table.set_points(points_data)

    def _on_course_item_clicked(self, item, column):
        """Обработка клика по элементу хода"""
        text = item.text(column)
        if text == "Нивелирные ходы":
            # Двойной клик на корне - показать все измерения
            self.course_selected.emit("ALL_COURSES")
        elif text.startswith("Ход "):
            course_id = text.replace("Ход ", "")
            self.course_selected.emit(course_id)
        elif text.startswith("Станция: "):
            station_name = text.replace("Станция: ", "")
            # Передаем session_id для фильтрации
            session_id = self._station_to_session.get(station_name, station_name)
            self.station_selected.emit(session_id)
        elif " → " in text:
            # Это измерение - можно выделить соответствующую станцию
            parts = text.split(" → ")
            if parts:
                station_name = parts[0].strip()
                session_id = self._station_to_session.get(station_name, station_name)
                self.station_selected.emit(session_id)

    # Методы для совместимости с существующим кодом
    def get_stations_content(self):
        """Получение виджета станций для совместимости"""
        return self.stations_content

    def get_points_table(self):
        """Получение таблицы пунктов для совместимости"""
        return self.points_table