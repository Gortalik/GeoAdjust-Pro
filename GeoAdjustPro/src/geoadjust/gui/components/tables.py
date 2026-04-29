"""
Табличные компоненты для GeoAdjust Pro

Включает:
- PointsTableView: таблица пунктов ПВО
- ObservationsTableView: таблица измерений
"""

from PyQt5.QtWidgets import QTableView, QHeaderView, QMenu, QAction
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem


class PointsTableView(QTableView):
    """Таблица пунктов ПВО"""
    
    point_double_clicked = pyqtSignal(str)  # signal с ID пункта
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Настройка заголовков
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionsMovable(True)
        self.verticalHeader().setVisible(False)
        
        # Контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Двойной клик
        self.doubleClicked.connect(self._on_double_click)
        
        # Модель данных
        self._setup_model()
    
    def _setup_model(self):
        """Настройка модели данных"""
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        self.model = QStandardItemModel(0, 10, self)
        self.model.setHorizontalHeaderLabels([
            "ID", "Наименование", "Тип", "Статус плана", "Статус высоты", 
            "X (м)", "Y (м)", "H (м)", "Прибор", "Примечание"
        ])
        self.setModel(self.model)
    
    def update_data(self, points: list):
        """Обновление данных таблицы"""
        from PyQt5.QtGui import QStandardItem
        self.model.setRowCount(0)
        
        for point in points:
            row_data = [
                point.get('id', ''),
                point.get('name', ''),
                point.get('coord_type', 'FREE'),
                point.get('plan_status', 'working'),
                point.get('height_status', 'working'),
                point.get('x', 0),
                point.get('y', 0),
                point.get('h', 0),
                point.get('instrument', ''),
                point.get('notes', '')
            ]
            items = [QStandardItem(str(val)) for val in row_data]
            self.model.appendRow(items)

    def _show_header_context_menu(self, position):
        """Контекстное меню для заголовка таблицы"""
        menu = QMenu(self)

        reset_sort_action = QAction("Сбросить сортировку", self)
        reset_sort_action.triggered.connect(self._reset_sorting)

        menu.addAction(reset_sort_action)
        menu.exec_(self.horizontalHeader().mapToGlobal(position))

    def _reset_sorting(self):
        """Сброс сортировки таблицы"""
        self.sortByColumn(-1)
        self.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)

    def _show_context_menu(self, position):
        """Показ контекстного меню"""
        menu = QMenu(self)
        
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")
        menu.addSeparator()
        properties_action = menu.addAction("Свойства")
        
        action = menu.exec_(self.mapToGlobal(position))
        
        if action == edit_action:
            self._edit_point()
        elif action == delete_action:
            self._delete_point()
        elif action == properties_action:
            self._show_properties()
    
    def _on_double_click(self, index):
        """Обработка двойного клика"""
        row = index.row()
        if self.model and row >= 0:
            point_id = self.model.index(row, 0).data()
            if point_id:
                self.point_double_clicked.emit(point_id)
    
    def _edit_point(self):
        """Редактирование пункта"""
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        model = self.model()
        if not model:
            return

        # Получение данных пункта
        point_data = {
            'name': model.index(row, 0).data() or '',
            'x': model.index(row, 5).data() or '',
            'y': model.index(row, 6).data() or '',
            'h': model.index(row, 7).data() or '',
            'type': model.index(row, 2).data() or 'free',
            'plan_status': model.index(row, 3).data() or 'working',
            'height_status': model.index(row, 4).data() or 'working'
        }

        # Вызов диалога редактирования
        from ..dialogs.point_editor import PointEditorDialog
        dialog = PointEditorDialog(point_data=point_data, parent=self.parent())
        if dialog.exec_() == dialog.Accepted:
            updated_data = dialog.get_point_data()
            # Обновление модели
            model.setData(model.index(row, 0), updated_data['name'])
            model.setData(model.index(row, 1), updated_data['name'])  # Наименование
            model.setData(model.index(row, 2), updated_data['type'])
            model.setData(model.index(row, 3), updated_data.get('plan_status', 'working'))
            model.setData(model.index(row, 4), updated_data.get('height_status', 'working'))
            model.setData(model.index(row, 5), str(updated_data['x']))
            model.setData(model.index(row, 6), str(updated_data['y']))
            model.setData(model.index(row, 7), str(updated_data['h']) if updated_data['h'] is not None else '')

    def _delete_point(self):
        """Удаление пункта"""
        from PyQt5.QtWidgets import QMessageBox

        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        # Подтверждение удаления
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить {len(indexes)} пункт(ов)?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Удаление строк в обратном порядке
            rows_to_delete = sorted([idx.row() for idx in indexes], reverse=True)
            for row in rows_to_delete:
                self.model().removeRow(row)

    def _show_properties(self):
        """Показ свойств пункта"""
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        model = self.model()
        if not model:
            return

        # Получение данных пункта
        point_data = {
            'name': model.index(row, 0).data() or '',
            'x': model.index(row, 5).data() or '',
            'y': model.index(row, 6).data() or '',
            'h': model.index(row, 7).data() or '',
            'type': model.index(row, 2).data() or 'free',
            'plan_status': model.index(row, 3).data() or 'working',
            'height_status': model.index(row, 4).data() or 'working'
        }

        # Показ диалога свойств
        from ..dialogs.point_editor import PointEditorDialog
        dialog = PointEditorDialog(point_data=point_data, parent=self.parent())
        dialog.setWindowTitle("Свойства пункта")
        dialog.exec_()


class ObservationsTableView(QTableView):
    """Таблица измерений"""
    
    observation_double_clicked = pyqtSignal(str)  # signal с ID измерения
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Настройка заголовков
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionsMovable(True)
        self.verticalHeader().setVisible(False)
        
        # Контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Двойной клик
        self.doubleClicked.connect(self._on_double_click)
        
        # Модель данных
        self._setup_model()
    
    def _setup_model(self):
        """Настройка модели данных"""
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        self.model = QStandardItemModel(0, 10, self)
        self.model.setHorizontalHeaderLabels([
            "ID", "Откуда", "Куда", "Тип", "Значение", 
            "σ (априорная)", "Прибор", "Дата", "Время", "Примечание"
        ])
        self.setModel(self.model)
    
    def update_data(self, observations: list):
        """Обновление данных таблицы"""
        from PyQt5.QtGui import QStandardItem
        self.model.setRowCount(0)
        
        for obs in observations:
            row_data = [
                str(obs.get('id', '')),
                obs.get('from_point', ''),
                obs.get('to_point', ''),
                obs.get('obs_type', ''),
                str(obs.get('value', '')),
                str(obs.get('sigma_apriori', '')),
                obs.get('instrument_name', ''),
                obs.get('date', ''),
                obs.get('time', ''),
                obs.get('notes', '')
            ]
            items = [QStandardItem(str(val)) for val in row_data]
            self.model.appendRow(items)
    
    def _show_context_menu(self, position):
        """Показ контекстного меню"""
        menu = QMenu(self)
        
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")
        menu.addSeparator()
        exclude_action = menu.addAction("Исключить")
        
        action = menu.exec_(self.mapToGlobal(position))
        
        if action == edit_action:
            self._edit_observation()
        elif action == delete_action:
            self._delete_observation()
        elif action == exclude_action:
            self._exclude_observation()
    
    def _on_double_click(self, index):
        """Обработка двойного клика"""
        row = index.row()
        if self.model and row >= 0:
            obs_id = self.model.index(row, 0).data()
            if obs_id:
                self.observation_double_clicked.emit(obs_id)
    
    def _edit_observation(self):
        """Редактирование измерения"""
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        model = self.model()
        if not model:
            return

        # Получение данных измерения
        obs_data = {
            'from_point': model.index(row, 1).data() or '',
            'to_point': model.index(row, 2).data() or '',
            'type': model.index(row, 3).data() or 'direction',
            'value': model.index(row, 4).data() or '',
            'sigma': model.index(row, 5).data() or '0.00005'
        }

        # Вызов диалога редактирования
        from ..dialogs.observation_editor import ObservationEditorDialog
        dialog = ObservationEditorDialog(obs_data=obs_data, parent=self.parent())
        if dialog.exec_() == dialog.Accepted:
            updated_data = dialog.get_observation_data()
            # Обновление модели
            model.setData(model.index(row, 1), updated_data['from_point'])
            model.setData(model.index(row, 2), updated_data['to_point'])
            model.setData(model.index(row, 3), updated_data['type'])
            model.setData(model.index(row, 4), str(updated_data['value']))
            model.setData(model.index(row, 5), str(updated_data['sigma']))

    def _delete_observation(self):
        """Удаление измерения"""
        from PyQt5.QtWidgets import QMessageBox

        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        # Подтверждение удаления
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить {len(indexes)} измерение(ий)?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Удаление строк в обратном порядке
            rows_to_delete = sorted([idx.row() for idx in indexes], reverse=True)
            for row in rows_to_delete:
                self.model().removeRow(row)

    def _exclude_observation(self):
        """Исключение измерения из уравнивания"""
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        # Получение модели текущей вкладки
        current_widget = self.parent().tabs.currentWidget()
        if hasattr(current_widget, 'model'):
            model = current_widget.model()
            for index in indexes:
                row = index.row()
                # Отмечаем измерение как исключённое (например, меняем статус)
                status_item = model.index(row, model.columnCount() - 1)  # Последняя колонка - статус
                current_status = status_item.data() or ""
                new_status = "Исключено" if "Исключено" not in current_status else "Активно"
                model.setData(status_item, new_status)
