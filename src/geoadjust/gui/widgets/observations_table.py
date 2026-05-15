"""Модель и представление таблицы наблюдений (MVC паттерн)"""
from typing import List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtWidgets import QHeaderView, QTableView


class ObservationsModel(QAbstractTableModel):
    """
    Модель данных для таблицы наблюдений.
    
    Реализует паттерн MVC для корректного обновления UI
    через beginResetModel()/endResetModel().
    """

    HEADERS = ["Станция", "Цель", "Тип", "Значение (м)", "Расстояние (м)", "Setup ID"]

    def __init__(self, observations: Optional[List] = None):
        super().__init__()
        self._data = observations or []

    def update_data(self, observations: List):
        """Безопасное обновление данных с уведомлением View"""
        self.beginResetModel()
        self._data = observations
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = None) -> int:
        if parent and parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent: QModelIndex = None) -> int:
        if parent and parent.isValid():
            return 0
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        obs = self._data[index.row()]
        mapping = [
            obs.station_id,
            obs.target_id,
            obs.type.value,
            f"{obs.value:.6f}",
            f"{obs.distance:.2f}",
            obs.setup_id or ""
        ]

        return str(mapping[index.column()])

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole
    ):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index: QModelIndex):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class ObservationsTableView(QTableView):
    """
    Представление таблицы наблюдений.
    
    Настроено на работу с ObservationsModel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Установка модели по умолчанию
        self.setModel(ObservationsModel())

        # Настройка внешнего вида
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setEditTriggers(QTableView.NoEditTriggers)

        # Настройка заголовков
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Стиль
        self.setStyleSheet("""
            QTableView {
                gridline-color: #ddd;
                background-color: white;
            }
            QTableView::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 4px;
                border: 1px solid #bdc3c7;
                font-weight: bold;
            }
        """)

    def set_observations(self, observations: List):
        """Удобный метод для обновления данных"""
        self.model().update_data(observations)
