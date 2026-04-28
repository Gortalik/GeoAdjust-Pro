#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест визуальных индикаторов GeoAdjust Pro
Демонстрирует работу индикаторов без иконок
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GeoAdjustPro', 'src'))

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from geoadjust.gui.visual_indicators import VisualIndicator


class IndicatorsDemo(QWidget):
    """Демо-виджет для демонстрации визуальных индикаторов"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Визуальные индикаторы GeoAdjust Pro")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout(self)

        # Заголовок
        title = QLabel("Визуальные индикаторы элементов интерфейса")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Типы пунктов
        points_widget = QWidget()
        points_layout = QVBoxLayout(points_widget)

        points_title = QLabel("Типы пунктов ПВО")
        points_title.setStyleSheet("font-weight: bold; font-size: 11pt; margin-bottom: 5px;")
        points_layout.addWidget(points_title)

        points_container = QWidget()
        points_container_layout = QHBoxLayout(points_container)

        # Создаем индикаторы для разных типов пунктов
        for point_type in ["FIXED", "FREE", "APPROXIMATE"]:
            indicator = VisualIndicator.create_point_type_indicator(point_type)
            points_container_layout.addWidget(indicator)

        points_container_layout.addStretch()
        points_layout.addWidget(points_container)
        layout.addWidget(points_widget)

        # Типы измерений
        obs_widget = QWidget()
        obs_layout = QVBoxLayout(obs_widget)

        obs_title = QLabel("Типы измерений")
        obs_title.setStyleSheet("font-weight: bold; font-size: 11pt; margin-bottom: 5px;")
        obs_layout.addWidget(obs_title)

        obs_container = QWidget()
        obs_container_layout = QHBoxLayout(obs_container)

        # Создаем индикаторы для разных типов измерений
        obs_types = ["direction", "zenith_angle", "slope_distance", "horizontal_distance", "height_diff"]
        for obs_type in obs_types:
            indicator = VisualIndicator.create_observation_type_indicator(obs_type)
            obs_container_layout.addWidget(indicator)

        obs_container_layout.addStretch()
        obs_layout.addWidget(obs_container)
        layout.addWidget(obs_widget)

        # Типы ходов
        traverse_widget = QWidget()
        traverse_layout = QVBoxLayout(traverse_widget)

        traverse_title = QLabel("Типы геодезических ходов")
        traverse_title.setStyleSheet("font-weight: bold; font-size: 11pt; margin-bottom: 5px;")
        traverse_layout.addWidget(traverse_title)

        traverse_container = QWidget()
        traverse_container_layout = QHBoxLayout(traverse_container)

        # Создаем индикаторы для разных типов ходов
        traverse_types = [
            ("taheometric", {"num_stations": 5, "length": 1250.5}),
            ("leveling", {"num_stations": 12, "length": 850.0}),
            ("gnss", {"num_stations": 3, "length": 5200.0})
        ]
        for traverse_type, traverse_data in traverse_types:
            indicator = VisualIndicator.create_traverse_indicator(traverse_type, traverse_data)
            traverse_container_layout.addWidget(indicator)

        traverse_container_layout.addStretch()
        traverse_layout.addWidget(traverse_container)
        layout.addWidget(traverse_widget)

        # Статусы операций
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)

        status_title = QLabel("Статусы операций")
        status_title.setStyleSheet("font-weight: bold; font-size: 11pt; margin-bottom: 5px;")
        status_layout.addWidget(status_title)

        status_container = QWidget()
        status_container_layout = QHBoxLayout(status_container)

        # Создаем индикаторы для разных статусов
        statuses = [
            ("success", "Операция выполнена успешно"),
            ("warning", "Требуется внимание"),
            ("error", "Произошла ошибка"),
            ("processing", "Выполняется обработка...")
        ]
        for status, message in statuses:
            indicator = VisualIndicator.create_status_indicator(status, message)
            status_container_layout.addWidget(indicator)

        status_container_layout.addStretch()
        status_layout.addWidget(status_container)
        layout.addWidget(status_widget)

        # Станции
        station_widget = QWidget()
        station_layout = QVBoxLayout(station_widget)

        station_title = QLabel("Станции наблюдений")
        station_title.setStyleSheet("font-weight: bold; font-size: 11pt; margin-bottom: 5px;")
        station_layout.addWidget(station_title)

        station_container = QWidget()
        station_container_layout = QHBoxLayout(station_container)

        # Создаем индикаторы для станций
        stations = [
            {"session_id": "ST001", "point_id": "P001"},
            {"session_id": "GR3.1", "point_id": "P015"},
            {"session_id": "BASE_A", "point_id": "P042"}
        ]
        for station_data in stations:
            indicator = VisualIndicator.create_station_indicator(station_data)
            station_container_layout.addWidget(indicator)

        station_container_layout.addStretch()
        station_layout.addWidget(station_container)
        layout.addWidget(station_widget)

        layout.addStretch()

        # Информация о символах
        info_label = QLabel(
            "Все индикаторы используют Unicode символы и стандартную цветовую схему.\n"
            "Не требуют внешних иконок или изображений."
        )
        info_label.setStyleSheet("color: #666; font-size: 10pt; margin: 10px;")
        # info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)


def main():
    """Главная функция"""
    app = QApplication(sys.argv)

    # Устанавливаем стиль для лучшего отображения
    app.setStyle("Fusion")

    # Создаем и показываем демо
    demo = IndicatorsDemo()
    demo.show()

    print("Запущено демо визуальных индикаторов")
    print("Закройте окно для выхода")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()