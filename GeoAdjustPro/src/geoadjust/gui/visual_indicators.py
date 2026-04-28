# src/geoadjust/gui/visual_indicators.py
"""
Визуальные индикаторы для элементов интерфейса GeoAdjust Pro
Использует текст и стандартную графику Qt вместо иконок
"""

from PyQt5.QtWidgets import QLabel, QFrame, QHBoxLayout, QWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from typing import Dict, Any, Optional


class VisualIndicator:
    """Базовый класс для визуальных индикаторов"""

    @staticmethod
    def create_point_type_indicator(point_type: str) -> QWidget:
        """
        Создает индикатор типа пункта

        Args:
            point_type: Тип пункта ('FIXED', 'FREE', 'APPROXIMATE')

        Returns:
            QWidget с визуальным индикатором
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Текстовый индикатор
        label = QLabel()
        label.setFont(QFont("Arial", 8, QFont.Bold))

        if point_type.upper() == 'FIXED':
            label.setText("●")  # Круглый маркер
            label.setStyleSheet("color: #2E86C1;")  # Синий цвет для опорных
        elif point_type.upper() == 'FREE':
            label.setText("○")  # Пустой круг
            label.setStyleSheet("color: #E74C3C;")  # Красный для свободных
        elif point_type.upper() == 'APPROXIMATE':
            label.setText("△")  # Треугольник
            label.setStyleSheet("color: #F39C12;")  # Оранжевый для приближенных
        else:
            label.setText("?")
            label.setStyleSheet("color: #95A5A6;")  # Серый для неизвестных

        layout.addWidget(label)

        # Текстовое описание
        text_label = QLabel()
        text_label.setFont(QFont("Arial", 8))

        if point_type.upper() == 'FIXED':
            text_label.setText("опорный")
            text_label.setStyleSheet("color: #2E86C1;")
        elif point_type.upper() == 'FREE':
            text_label.setText("свободный")
            text_label.setStyleSheet("color: #E74C3C;")
        elif point_type.upper() == 'APPROXIMATE':
            text_label.setText("приближенный")
            text_label.setStyleSheet("color: #F39C12;")
        else:
            text_label.setText("неизвестный")
            text_label.setStyleSheet("color: #95A5A6;")

        layout.addWidget(text_label)
        layout.addStretch()

        return widget

    @staticmethod
    def create_observation_type_indicator(obs_type: str) -> QWidget:
        """
        Создает индикатор типа измерения

        Args:
            obs_type: Тип измерения ('direction', 'zenith_angle', 'slope_distance', etc.)

        Returns:
            QWidget с визуальным индикатором
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Символьный индикатор
        symbol_label = QLabel()
        symbol_label.setFont(QFont("Arial", 10, QFont.Bold))

        # Текстовый индикатор
        text_label = QLabel()
        text_label.setFont(QFont("Arial", 8))

        if obs_type == 'direction':
            symbol_label.setText("→")
            symbol_label.setStyleSheet("color: #27AE60;")  # Зеленый
            text_label.setText("направление")
            text_label.setStyleSheet("color: #27AE60;")
        elif obs_type == 'zenith_angle':
            symbol_label.setText("∠")
            symbol_label.setStyleSheet("color: #8E44AD;")  # Фиолетовый
            text_label.setText("зенитный угол")
            text_label.setStyleSheet("color: #8E44AD;")
        elif obs_type == 'slope_distance':
            symbol_label.setText("↗")
            symbol_label.setStyleSheet("color: #E67E22;")  # Оранжевый
            text_label.setText("расстояние")
            text_label.setStyleSheet("color: #E67E22;")
        elif obs_type == 'horizontal_distance':
            symbol_label.setText("→")
            symbol_label.setStyleSheet("color: #3498DB;")  # Голубой
            text_label.setText("горизонт")
            text_label.setStyleSheet("color: #3498DB;")
        elif obs_type == 'height_diff':
            symbol_label.setText("↕")
            symbol_label.setStyleSheet("color: #9B59B6;")  # Пурпурный
            text_label.setText("превышение")
            text_label.setStyleSheet("color: #9B59B6;")
        else:
            symbol_label.setText("?")
            symbol_label.setStyleSheet("color: #95A5A6;")
            text_label.setText("неизвестно")
            text_label.setStyleSheet("color: #95A5A6;")

        layout.addWidget(symbol_label)
        layout.addWidget(text_label)
        layout.addStretch()

        return widget

    @staticmethod
    def create_station_indicator(station_data: Dict[str, Any]) -> QWidget:
        """
        Создает индикатор станции

        Args:
            station_data: Данные станции

        Returns:
            QWidget с визуальным индикатором
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Иконка станции
        station_label = QLabel("📐")  # Теодолит
        station_label.setFont(QFont("Arial", 12))
        layout.addWidget(station_label)

        # Информация о станции
        info_label = QLabel()
        info_label.setFont(QFont("Arial", 8))

        session_id = station_data.get('session_id', 'unknown')
        point_id = station_data.get('point_id', 'unknown')

        info_label.setText(f"Станция {point_id}")
        info_label.setStyleSheet("color: #2C3E50;")

        layout.addWidget(info_label)
        layout.addStretch()

        return widget

    @staticmethod
    def create_traverse_indicator(traverse_type: str, traverse_data: Dict[str, Any]) -> QWidget:
        """
        Создает индикатор типа хода/секции

        Args:
            traverse_type: Тип ('taheometric', 'leveling', 'gnss')
            traverse_data: Данные хода

        Returns:
            QWidget с визуальным индикатором
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Символ типа
        symbol_label = QLabel()
        symbol_label.setFont(QFont("Arial", 10, QFont.Bold))

        # Описание
        desc_label = QLabel()
        desc_label.setFont(QFont("Arial", 8))

        if traverse_type == 'taheometric':
            symbol_label.setText("⊕")  # Крест в круге
            symbol_label.setStyleSheet("color: #27AE60;")
            desc_label.setText("тахеометрия")
            desc_label.setStyleSheet("color: #27AE60;")
        elif traverse_type == 'leveling':
            symbol_label.setText("━")  # Горизонтальная линия
            symbol_label.setStyleSheet("color: #8E44AD;")
            desc_label.setText("нивелирование")
            desc_label.setStyleSheet("color: #8E44AD;")
        elif traverse_type == 'gnss':
            symbol_label.setText("◎")  # Круг с точкой
            symbol_label.setStyleSheet("color: #3498DB;")
            desc_label.setText("GNSS")
            desc_label.setStyleSheet("color: #3498DB;")
        else:
            symbol_label.setText("?")
            symbol_label.setStyleSheet("color: #95A5A6;")
            desc_label.setText("неизвестно")
            desc_label.setStyleSheet("color: #95A5A6;")

        layout.addWidget(symbol_label)
        layout.addWidget(desc_label)

        # Дополнительная информация
        if traverse_data:
            info_text = []
            if 'num_stations' in traverse_data:
                info_text.append(f"{traverse_data['num_stations']} ст.")
            if 'length' in traverse_data:
                info_text.append(f"{traverse_data['length']:.1f}м")

            if info_text:
                info_label = QLabel(f"({' '.join(info_text)})")
                info_label.setFont(QFont("Arial", 7))
                info_label.setStyleSheet("color: #7F8C8D;")
                layout.addWidget(info_label)

        layout.addStretch()

        return widget

    @staticmethod
    def create_status_indicator(status: str, message: Optional[str] = None) -> QWidget:
        """
        Создает индикатор статуса операции

        Args:
            status: Статус ('success', 'warning', 'error', 'processing')
            message: Дополнительное сообщение

        Returns:
            QWidget с визуальным индикатором
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Статусный индикатор
        status_label = QLabel()
        status_label.setFont(QFont("Arial", 9, QFont.Bold))

        if status == 'success':
            status_label.setText("✓")
            status_label.setStyleSheet("color: #27AE60;")
        elif status == 'warning':
            status_label.setText("⚠")
            status_label.setStyleSheet("color: #F39C12;")
        elif status == 'error':
            status_label.setText("✗")
            status_label.setStyleSheet("color: #E74C3C;")
        elif status == 'processing':
            status_label.setText("⟳")
            status_label.setStyleSheet("color: #3498DB;")
        else:
            status_label.setText("?")
            status_label.setStyleSheet("color: #95A5A6;")

        layout.addWidget(status_label)

        # Сообщение
        if message:
            message_label = QLabel(message)
            message_label.setFont(QFont("Arial", 8))
            if status == 'success':
                message_label.setStyleSheet("color: #27AE60;")
            elif status == 'warning':
                message_label.setStyleSheet("color: #F39C12;")
            elif status == 'error':
                message_label.setStyleSheet("color: #E74C3C;")
            elif status == 'processing':
                message_label.setStyleSheet("color: #3498DB;")
            else:
                message_label.setStyleSheet("color: #95A5A6;")

            layout.addWidget(message_label)

        layout.addStretch()

        return widget

    @staticmethod
    def get_color_scheme() -> Dict[str, str]:
        """
        Возвращает цветовую схему для различных элементов

        Returns:
            Словарь с цветами для разных типов элементов
        """
        return {
            # Типы пунктов
            'point_fixed': '#2E86C1',      # Синий
            'point_free': '#E74C3C',       # Красный
            'point_approximate': '#F39C12', # Оранжевый

            # Типы измерений
            'obs_direction': '#27AE60',    # Зеленый
            'obs_zenith_angle': '#8E44AD', # Фиолетовый
            'obs_slope_distance': '#E67E22', # Оранжевый
            'obs_horizontal_distance': '#3498DB', # Голубой
            'obs_height_diff': '#9B59B6',  # Пурпурный

            # Типы ходов
            'traverse_taheometric': '#27AE60', # Зеленый
            'traverse_leveling': '#8E44AD',    # Фиолетовый
            'traverse_gnss': '#3498DB',        # Голубой

            # Статусы
            'status_success': '#27AE60',   # Зеленый
            'status_warning': '#F39C12',   # Оранжевый
            'status_error': '#E74C3C',     # Красный
            'status_processing': '#3498DB', # Голубой
            'status_unknown': '#95A5A6',   # Серый
        }

    @staticmethod
    def get_symbol_map() -> Dict[str, str]:
        """
        Возвращает карту символов для различных элементов

        Returns:
            Словарь с символами Unicode для разных типов элементов
        """
        return {
            # Типы пунктов
            'point_fixed': '●',        # Заполненный круг
            'point_free': '○',         # Пустой круг
            'point_approximate': '△',  # Треугольник

            # Типы измерений
            'obs_direction': '→',      # Стрелка вправо
            'obs_zenith_angle': '∠',   # Угол
            'obs_slope_distance': '↗', # Стрелка диагонально
            'obs_horizontal_distance': '→', # Стрелка вправо
            'obs_height_diff': '↕',    # Стрелка вверх-вниз

            # Типы ходов
            'traverse_taheometric': '⊕', # Крест в круге
            'traverse_leveling': '━',   # Горизонтальная линия
            'traverse_gnss': '◎',       # Круг с точкой

            # Станции
            'station': '📐',           # Теодолит

            # Статусы
            'status_success': '✓',     # Галочка
            'status_warning': '⚠',     # Предупреждение
            'status_error': '✗',       # Крест
            'status_processing': '⟳',  # Круговые стрелки
            'status_unknown': '?',     # Вопрос
        }