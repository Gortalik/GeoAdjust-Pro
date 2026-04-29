# -*- coding: utf-8 -*-
"""
Объединенный виджет для левой панели с переключением
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QLabel, QTreeWidget, QTreeWidgetItem, QTableWidget, QHeaderView
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
        self.stations_content.station_selected.connect(self._on_station_selected)
        layout.addWidget(self.stations_content)

        return widget

    def _on_station_selected(self, station_name):
        """Передача сигнала выбора станции"""
        # Защита от рекурсии
        if hasattr(self, '_emitting') and self._emitting:
            return

        self._emitting = True
        try:
            self.station_selected.emit(station_name)
        finally:
            self._emitting = False

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
        self.traverses_table = QTableWidget()
        self.traverses_table.setColumnCount(7)
        self.traverses_table.setHorizontalHeaderLabels(["Флаг", "Примечания", "Ход", "Пункты", "Класс Н", "Комплект реек, пр.", "Комплект реек, обр."])
        self.traverses_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.traverses_table.setAlternatingRowColors(True)
        self.traverses_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.traverses_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.traverses_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.traverses_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.traverses_table.setSortingEnabled(True)
        self.traverses_table.itemDoubleClicked.connect(self._on_traverse_double_clicked)

        # Для совместимости
        self.courses_tree = self.traverses_table

        # Подключаем сигналы
        # self.courses_tree.itemClicked.connect(self._on_course_item_clicked)  # Убрано для таблицы

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
        self.traverses_table.setRowCount(0)

        for i, course in enumerate(courses_data or []):
            row = self.traverses_table.rowCount()
            self.traverses_table.insertRow(row)

            # Флаг - пусто или чекбокс
            flag_item = QTableWidgetItem("")
            flag_item.setFlags(flag_item.flags() & ~Qt.ItemIsEditable)
            self.traverses_table.setItem(row, 0, flag_item)

            # Примечания - пусто
            notes_item = QTableWidgetItem("")
            notes_item.setFlags(notes_item.flags() & ~Qt.ItemIsEditable)
            self.traverses_table.setItem(row, 1, notes_item)

            # Ход - название
            traverse_item = QTableWidgetItem(course.get('course_id', f'Course {i+1}'))
            traverse_item.setData(Qt.UserRole, course)  # Сохраняем данные хода
            traverse_item.setFlags(traverse_item.flags() & ~Qt.ItemIsEditable)
            self.traverses_table.setItem(row, 2, traverse_item)

            # Пункты - перечень через запятую
            points_str = ", ".join(course.get('stations', []))
            points_item = QTableWidgetItem(points_str)
            points_item.setFlags(points_item.flags() & ~Qt.ItemIsEditable)
            self.traverses_table.setItem(row, 3, points_item)

            # Класс Н
            class_item = QTableWidgetItem("IV класс")
            class_item.setFlags(class_item.flags() & ~Qt.ItemIsEditable)
            self.traverses_table.setItem(row, 4, class_item)

            # Комплект реек, пр.
            rods_pr_item = QTableWidgetItem("")
            rods_pr_item.setFlags(rods_pr_item.flags() & ~Qt.ItemIsEditable)
            self.traverses_table.setItem(row, 5, rods_pr_item)

            # Комплект реек, обр.
            rods_obr_item = QTableWidgetItem("")
            rods_obr_item.setFlags(rods_obr_item.flags() & ~Qt.ItemIsEditable)
            self.traverses_table.setItem(row, 6, rods_obr_item)

    def _on_traverse_double_clicked(self, item):
        """Обработка двойного клика по ходу - открываем окно измерений"""
        row = item.row()
        traverse_item = self.traverses_table.item(row, 2)  # Колонка "Ход"
        if traverse_item:
            traverse_data = traverse_item.data(Qt.UserRole)
            if traverse_data:
                course_id = traverse_data.get('course_id', '')
                logger.info(f"Double clicked on traverse {course_id}, opening measurements dialog")
                # Отправляем данные хода для открытия окна измерений
                self.course_selected.emit(course_id)



    # Методы для совместимости с существующим кодом
    def get_stations_content(self):
        """Получение виджета станций для совместимости"""
        return self.stations_content

    def get_points_table(self):
        """Получение таблицы пунктов для совместимости"""
        return self.points_table