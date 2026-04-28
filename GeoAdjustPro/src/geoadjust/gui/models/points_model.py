#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель данных для таблицы пунктов ПВО
Реализует QAbstractTableModel для интеграции с QTableView
"""

from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant
from typing import List, Dict, Any, Optional
from geoadjust.core.network.models import NetworkPoint

class PointsTableModel(QAbstractTableModel):
    """Модель данных для таблицы пунктов"""
    
    # Заголовки столбцов
    HEADERS = [
        "№",              # 0
        "Имя",            # 1
        "Тип",            # 2
        "X, м",           # 3
        "Y, м",           # 4
        "H, м",           # 5
        "σx, мм",         # 6
        "σy, мм",         # 7
        "σh, мм",         # 8
        "Класс"           # 9
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points: List[NetworkPoint] = []
        self.point_ids: List[str] = []  # Сохраняем порядок идентификаторов
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Количество строк"""
        return len(self.points)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Количество столбцов"""
        return len(self.HEADERS)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Данные для ячейки"""
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        col = index.column()
        
        if role == Qt.DisplayRole:
            point = self.points[row]

            if col == 0:
                return row + 1
            elif col == 1:
                return point.point_id
            elif col == 2:
                # Вместо простого текста используем визуальный индикатор
                # (в таблице будет отображаться текстовое представление)
                coord_type = point.coord_type or 'FREE'
                if coord_type == 'FIXED':
                    return "опорный"
                elif coord_type == 'FREE':
                    return "свободный"
                elif coord_type == 'APPROXIMATE':
                    return "приближенный"
                else:
                    return coord_type
            elif col == 3:
                return f"{point.x:.3f}" if point.x is not None else ""
            elif col == 4:
                return f"{point.y:.3f}" if point.y is not None else ""
            elif col == 5:
                return f"{point.h:.3f}" if point.h is not None else ""
            elif col == 6:
                return f"{point.sigma_x * 1000:.3f}" if point.sigma_x else ""
            elif col == 7:
                return f"{point.sigma_y * 1000:.3f}" if point.sigma_y else ""
            elif col == 8:
                return f"{point.sigma_h * 1000:.3f}" if point.sigma_h else ""
            elif col == 9:
                return point.normative_class or ""
        
        elif role == Qt.TextAlignmentRole:
            if col in [0, 3, 4, 5, 6, 7, 8]:
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        elif role == Qt.BackgroundRole:
            # Цвет фона в зависимости от типа пункта
            point = self.points[row]
            if point.coord_type == 'FIXED':
                return Qt.lightGray
            elif point.coord_type == 'APPROXIMATE':
                return Qt.yellow
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.DisplayRole) -> Any:
        """Заголовки таблицы"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return QVariant()
    
    def add_point(self, point: NetworkPoint):
        """Добавление пункта в модель"""
        self.beginInsertRows(QModelIndex(), len(self.points), len(self.points))
        self.points.append(point)
        self.point_ids.append(point.point_id)
        self.endInsertRows()
    
    def remove_point(self, row: int):
        """Удаление пункта из модели"""
        if 0 <= row < len(self.points):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.points[row]
            del self.point_ids[row]
            self.endRemoveRows()
    
    def update_point(self, row: int, point: NetworkPoint):
        """Обновление пункта в модели"""
        if 0 <= row < len(self.points):
            self.points[row] = point
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, self.columnCount() - 1)
            )
    
    def get_point(self, row: int) -> Optional[NetworkPoint]:
        """Получение пункта по индексу строки"""
        if 0 <= row < len(self.points):
            return self.points[row]
        return None
    
    def find_point_row(self, point_id: str) -> int:
        """Поиск строки по идентификатору пункта"""
        try:
            return self.point_ids.index(point_id)
        except ValueError:
            return -1
    
    def clear(self):
        """Очистка модели"""
        self.beginResetModel()
        self.points.clear()
        self.point_ids.clear()
        self.endResetModel()
