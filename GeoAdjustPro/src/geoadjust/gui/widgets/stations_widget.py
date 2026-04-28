#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Виджет отображения станций с раскрывающимися измерениями.

Каждая станция (сессия) отображается как отдельный элемент.
При нажатии на станцию раскрываются все измерения на этой станции.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QHBoxLayout, QPushButton, QMenu, QAction
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from typing import List, Dict, Any, Optional


class StationsTableWidget(QTableWidget):
    """Таблица станций с информацией о высоте и метео параметрах"""

    station_selected = pyqtSignal(str)  # session_id

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Станция", "Высота станции (м)", "Температура (°C)", "Давление (hPa)", "Измерений"])

        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._show_header_context_menu)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # Используем itemClicked вместо itemSelectionChanged для избежания проблем
        self.itemClicked.connect(self._on_item_clicked)

        self._sessions_data = []

    def _show_header_context_menu(self, position):
        """Контекстное меню для заголовка таблицы"""
        from PyQt5.QtWidgets import QMenu
        from PyQt5.QtCore import Qt

        menu = QMenu(self)

        reset_sort_action = QAction("Сбросить сортировку", self)
        reset_sort_action.triggered.connect(self._reset_sorting)

        menu.addAction(reset_sort_action)
        menu.exec_(self.horizontalHeader().mapToGlobal(position))

    def _reset_sorting(self):
        """Сброс сортировки таблицы"""
        self.sortItems(-1, Qt.AscendingOrder)
        self.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)

    def set_station_sessions(self, sessions: List[Dict[str, Any]]):
        """Установка данных о сессиях станций"""
        print(f"StationsTableWidget.set_station_sessions called, self type: {type(self)}")
        self.clearContents()
        self._sessions_data = sessions

        self.setRowCount(len(sessions))

        for row, session in enumerate(sessions):
            session_id = session.get('session_id', '')
            station_name = session.get('station_name', '')
            num_obs = session.get('num_observations', 0)
            instr_h = session.get('instrument_height')
            temperature = session.get('temperature')
            pressure = session.get('pressure')

            # Станция
            station_item = QTableWidgetItem(station_name)
            station_item.setData(Qt.UserRole, {'type': 'station', 'session_id': session_id})
            station_item.setFlags(station_item.flags() & ~Qt.ItemIsEditable)
            font = station_item.font()
            font.setBold(True)
            station_item.setFont(font)
            self.setItem(row, 0, station_item)

            # Высота станции
            height_text = f"{instr_h:.4f}" if instr_h is not None else "-"
            height_item = QTableWidgetItem(height_text)
            height_item.setFlags(height_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 1, height_item)

            # Температура
            temp_text = f"{temperature:.1f}" if temperature is not None else "-"
            temp_item = QTableWidgetItem(temp_text)
            temp_item.setFlags(temp_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 2, temp_item)

            # Давление
            press_text = f"{pressure:.1f}" if pressure is not None else "-"
            press_item = QTableWidgetItem(press_text)
            press_item.setFlags(press_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 3, press_item)

            # Количество измерений
            obs_item = QTableWidgetItem(str(num_obs))
            obs_item.setFlags(obs_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 4, obs_item)

    def set_stations(self, stations_data):
        """Алиас для set_station_sessions для совместимости"""
        self.set_station_sessions(stations_data)
    
    def _on_item_clicked(self, item):
        """Обработка клика по элементу"""
        data = item.data(Qt.UserRole)
        if data and data.get('type') == 'station':
            session_id = data.get('session_id', '')
            self.station_selected.emit(session_id)


    
    def set_station_sessions(self, sessions: List[Dict[str, Any]]):
        """Установка данных о сессиях станций"""
        print(f"StationsTableWidget.set_station_sessions called, self type: {type(self)}")
        self.clearContents()
        self._sessions_data = sessions

        self.setRowCount(len(sessions))

        for row, session in enumerate(sessions):
            session_id = session.get('session_id', '')
            station_name = session.get('station_name', '')
            num_obs = session.get('num_observations', 0)
            instr_h = session.get('instrument_height')
            temperature = session.get('temperature')
            pressure = session.get('pressure')

            # Станция
            station_item = QTableWidgetItem(station_name)
            station_item.setData(Qt.UserRole, {'type': 'station', 'session_id': session_id})
            station_item.setFlags(station_item.flags() & ~Qt.ItemIsEditable)
            font = station_item.font()
            font.setBold(True)
            station_item.setFont(font)
            self.setItem(row, 0, station_item)

            # Высота станции
            height_text = f"{instr_h:.4f}" if instr_h is not None else "-"
            height_item = QTableWidgetItem(height_text)
            height_item.setFlags(height_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 1, height_item)

            # Температура
            temp_text = f"{temperature:.1f}" if temperature is not None else "-"
            temp_item = QTableWidgetItem(temp_text)
            temp_item.setFlags(temp_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 2, temp_item)

            # Давление
            press_text = f"{pressure:.1f}" if pressure is not None else "-"
            press_item = QTableWidgetItem(press_text)
            press_item.setFlags(press_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 3, press_item)

            # Количество измерений
            obs_item = QTableWidgetItem(str(num_obs))
            obs_item.setFlags(obs_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 4, obs_item)

    def clear(self):
        """Очистка данных"""
        self.table.clearContents()


class StationsDockContent(QWidget):
    """Виджет содержимого для dock-панели станций"""

    station_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Заголовок
        header_label = QLabel("Станции измерений")
        header_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(header_label)

        # Таблица станций
        self.table = StationsTableWidget(self)
        self.table.station_selected.connect(self._on_table_station_selected)
        layout.addWidget(self.table)

    def _on_table_station_selected(self, session_id: str):
        """Обработка выбора станции от таблицы"""
        self.station_selected.emit(session_id)

    def set_station_sessions(self, sessions: List[Dict[str, Any]]):
        """Установка данных о сессиях станций"""
        if not sessions:
            self.table.clearContents()
            return

        self.table.set_station_sessions(sessions)

        # Автоматически выбираем первую станцию для показа измерений
        if sessions:
            first_session = sessions[0]
            first_session_id = first_session.get('session_id', '')
            if first_session_id:
                self.station_selected.emit(first_session_id)

    def update_stations(self, stations_data):
        """Обновление списка станций"""
        if hasattr(self.table, 'set_stations'):
            self.table.set_stations(stations_data)

    def _show_all_measurements(self):
        """Показать все измерения"""
        self._on_table_station_selected("")

        # Кнопки
        btn_layout = QHBoxLayout()

        self.show_all_btn = QPushButton("Показать все измерения")

        btn_layout.addWidget(self.show_all_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self.show_all_btn.clicked.connect(self._show_all_measurements)

    def clear(self):
        """Очистка данных"""
        self.table.clearContents()
