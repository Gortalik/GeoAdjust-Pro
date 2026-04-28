# src/geoadjust/gui/delegates/visual_delegates.py
"""
Делегаты для отображения визуальных индикаторов в таблицах
"""

from PyQt5.QtWidgets import QStyledItemDelegate, QWidget, QHBoxLayout, QLabel, QTableView
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QFont, QPainter, QPalette
from typing import Optional, Any
from geoadjust.gui.visual_indicators import VisualIndicator


class PointTypeDelegate(QStyledItemDelegate):
    """Делегат для отображения типов пунктов с визуальными индикаторами"""

    def __init__(self, parent: Optional[QTableView] = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: Any, index: Any):
        """Отрисовка индикатора типа пункта"""
        # Получаем текст из модели
        text = index.data(Qt.DisplayRole)
        if not text:
            text = "свободный"  # По умолчанию

        # Определяем тип пункта по тексту
        point_type = "FREE"
        if text == "опорный":
            point_type = "FIXED"
        elif text == "приближенный":
            point_type = "APPROXIMATE"

        # Создаем виджет индикатора
        indicator_widget = VisualIndicator.create_point_type_indicator(point_type)

        # Устанавливаем размер виджета
        indicator_widget.setFixedSize(option.rect.size())

        # Отрисовываем виджет в painter
        painter.save()

        # Устанавливаем фон
        if option.state & QStyledItemDelegate.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            # Цвет фона в зависимости от типа
            if point_type == "FIXED":
                painter.fillRect(option.rect, Qt.lightGray)
            elif point_type == "APPROXIMATE":
                painter.fillRect(option.rect, QColor("#FFF3CD"))  # Светло-желтый
            else:
                painter.fillRect(option.rect, option.palette.base())

        # Перемещаем painter в нужную позицию
        painter.translate(option.rect.topLeft())

        # Отрисовываем виджет
        indicator_widget.render(painter, option.rect.topLeft())

        painter.restore()

    def sizeHint(self, option: Any, index: Any) -> QSize:
        """Предпочтительный размер ячейки"""
        return QSize(120, 24)  # Ширина для текста + иконки


class ObservationTypeDelegate(QStyledItemDelegate):
    """Делегат для отображения типов измерений с визуальными индикаторами"""

    def __init__(self, parent: Optional[QTableView] = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: Any, index: Any):
        """Отрисовка индикатора типа измерения"""
        # Получаем текст из модели
        obs_type = index.data(Qt.DisplayRole)
        if not obs_type:
            obs_type = "direction"  # По умолчанию

        # Создаем виджет индикатора
        indicator_widget = VisualIndicator.create_observation_type_indicator(obs_type)

        # Устанавливаем размер виджета
        indicator_widget.setFixedSize(option.rect.size())

        # Отрисовываем виджет в painter
        painter.save()

        # Устанавливаем фон
        if option.state & QStyledItemDelegate.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # Перемещаем painter в нужную позицию
        painter.translate(option.rect.topLeft())

        # Отрисовываем виджет
        indicator_widget.render(painter, option.rect.topLeft())

        painter.restore()

    def sizeHint(self, option: Any, index: Any) -> QSize:
        """Предпочтительный размер ячейки"""
        return QSize(140, 24)  # Ширина для текста + иконки


class StatusDelegate(QStyledItemDelegate):
    """Делегат для отображения статуса с визуальными индикаторами"""

    def __init__(self, parent: Optional[QTableView] = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: Any, index: Any):
        """Отрисовка индикатора статуса"""
        # Получаем данные статуса из модели
        status_data = index.data(Qt.UserRole)  # Сохраняем полные данные в UserRole
        if not status_data:
            status = "unknown"
            message = ""
        elif isinstance(status_data, dict):
            status = status_data.get('status', 'unknown')
            message = status_data.get('message', '')
        else:
            status = str(status_data)
            message = ""

        # Создаем виджет индикатора
        indicator_widget = VisualIndicator.create_status_indicator(status, message)

        # Устанавливаем размер виджета
        indicator_widget.setFixedSize(option.rect.size())

        # Отрисовываем виджет в painter
        painter.save()

        # Устанавливаем фон
        if option.state & QStyledItemDelegate.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # Перемещаем painter в нужную позицию
        painter.translate(option.rect.topLeft())

        # Отрисовываем виджет
        indicator_widget.render(painter, option.rect.topLeft())

        painter.restore()

    def sizeHint(self, option: Any, index: Any) -> QSize:
        """Предпочтительный размер ячейки"""
        return QSize(160, 24)  # Ширина для статуса + сообщения


class TraverseTypeDelegate(QStyledItemDelegate):
    """Делегат для отображения типов ходов в дереве"""

    def __init__(self, parent: Optional[QTableView] = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: Any, index: Any):
        """Отрисовка индикатора типа хода"""
        # Получаем данные из модели
        traverse_data = index.data(Qt.UserRole)
        traverse_type = index.data(Qt.DisplayRole)

        if not traverse_data:
            traverse_data = {}
        if not traverse_type:
            traverse_type = "unknown"

        # Создаем виджет индикатора
        indicator_widget = VisualIndicator.create_traverse_indicator(traverse_type, traverse_data)

        # Устанавливаем размер виджета
        indicator_widget.setFixedSize(option.rect.size())

        # Отрисовываем виджет в painter
        painter.save()

        # Устанавливаем фон
        if option.state & QStyledItemDelegate.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # Перемещаем painter в нужную позицию
        painter.translate(option.rect.topLeft())

        # Отрисовываем виджет
        indicator_widget.render(painter, option.rect.topLeft())

        painter.restore()

    def sizeHint(self, option: Any, index: Any) -> QSize:
        """Предпочтительный размер ячейки"""
        return QSize(180, 24)  # Ширина для типа + информации