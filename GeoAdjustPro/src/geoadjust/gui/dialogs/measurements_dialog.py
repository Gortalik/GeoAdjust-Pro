#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диалог отображения измерений нивелирного хода
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QLabel, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Dict, Any

class MeasurementsDialog(QDialog):
    """Диалог для отображения измерений нивелирного хода"""

    def __init__(self, traverse: 'Traverse', parent=None):
        super().__init__(parent)
        self.traverse = traverse
        self.setWindowTitle(f"Измерения хода: {traverse.name}")
        self.setModal(True)
        self.resize(1000, 600)

        logger.info(f"MeasurementsDialog created for traverse {traverse.name}, records: {len(traverse.records)}, side_points: {len(traverse.side_points)}")

        self._setup_ui()
        self._populate_data()

    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel(f"Нивелирный ход: {self.traverse_data.get('course_id', '')}")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)

        # Табы
        self.tabs = QTabWidget()

        # Таб 1: Нивелирный ход
        self.leveling_tab = QWidget()
        self._setup_leveling_tab()
        self.tabs.addTab(self.leveling_tab, "Нивелирный ход")

        # Таб 2: Боковое нивелирование
        self.side_tab = QWidget()
        self._setup_side_tab()
        self.tabs.addTab(self.side_tab, "Боковое нивелирование")

        layout.addWidget(self.tabs)

    def _setup_leveling_tab(self):
        """Настройка таба нивелирного хода"""
        layout = QVBoxLayout(self.leveling_tab)

        self.leveling_table = QTableWidget()
        self.leveling_table.setColumnCount(8)
        self.leveling_table.setHorizontalHeaderLabels([
            "Комментарий", "Примечания", "Пункт", "№ секции", "∆h, м", "L, км", "Штативы", "T, C", "∆Hn, м"
        ])
        self.leveling_table.setAlternatingRowColors(True)
        self.leveling_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.leveling_table)

    def _setup_side_tab(self):
        """Настройка таба бокового нивелирования"""
        layout = QVBoxLayout(self.side_tab)

        self.side_table = QTableWidget()
        self.side_table.setColumnCount(11)
        self.side_table.setHorizontalHeaderLabels([
            "Флаг", "Комментарий", "Примечания", "Точка", "Отсчёт, м", "Расстояние, м",
            "N, м", "E, м", "H, м", "vHср, м", "СКО H, м"
        ])
        self.side_table.setAlternatingRowColors(True)
        self.side_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.side_table)

    def _populate_data(self):
        """Заполнение данными"""
        # Данные нивелирного хода
        measurements = self.traverse_data.get('measurements', [])
        self.leveling_table.setRowCount(len(measurements))

        for row, measurement in enumerate(measurements):
            # Комментарий
            comment_item = QTableWidgetItem("")
            self.leveling_table.setItem(row, 0, comment_item)

            # Примечания
            notes_item = QTableWidgetItem("")
            self.leveling_table.setItem(row, 1, notes_item)

            # Пункт
            point_item = QTableWidgetItem(measurement.get('to_point', ''))
            self.leveling_table.setItem(row, 2, point_item)

            # № секции
            section_item = QTableWidgetItem(str(self.traverse_data.get('section_number', 1)))
            self.leveling_table.setItem(row, 3, section_item)

            # ∆h, мм (в Credo превышения в мм)
            dh_item = QTableWidgetItem(f"{measurement.get('value', 0) * 1000:.1f}")
            self.leveling_table.setItem(row, 4, dh_item)

            # L, км
            distance = measurement.get('distance', 0)
            length_item = QTableWidgetItem(f"{distance / 1000:.3f}" if distance else "")
            self.leveling_table.setItem(row, 5, length_item)

            # Штативы, T, C, ∆Hn, м - оставляем пустыми
            for col in range(6, 9):
                empty_item = QTableWidgetItem("")
                self.leveling_table.setItem(row, col, empty_item)

        # Боковое нивелирование
        side_points = getattr(self.traverse, 'side_points', [])
        self.side_table.setRowCount(len(side_points))

        for row, side_point in enumerate(side_points):
            # Флаг
            flag_item = QTableWidgetItem("")
            self.side_table.setItem(row, 0, flag_item)

            # Комментарий
            comment_item = QTableWidgetItem("")
            self.side_table.setItem(row, 1, comment_item)

            # Примечания
            notes_item = QTableWidgetItem("")
            self.side_table.setItem(row, 2, notes_item)

            # Точка
            point_item = QTableWidgetItem(side_point.point_name)
            self.side_table.setItem(row, 3, point_item)

            # Отсчёт, м
            rod_item = QTableWidgetItem(f"{side_point.rod_reading:.4f}")
            self.side_table.setItem(row, 4, rod_item)

            # Расстояние, м
            dist_item = QTableWidgetItem(f"{side_point.distance:.4f}")
            self.side_table.setItem(row, 5, dist_item)

            # N, E, H, vHср, СКО H - оставляем пустыми
            for col in range(6, 11):
                empty_item = QTableWidgetItem("")
                self.side_table.setItem(row, col, empty_item)