#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Таблица пунктов ПВО
Реализует отображение и редактирование списка пунктов сети
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView,
                             QAbstractItemView, QMenu, QAction, QPushButton,
                             QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDialogButtonBox, QMessageBox, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon

# Импорт визуальных делегатов
from geoadjust.gui.delegates.visual_delegates import PointTypeDelegate, ComboBoxDelegate


class ManualPointInputDialog(QDialog):
    """Диалог ручного ввода пункта"""
    
    def __init__(self, parent=None, point_data=None):
        super().__init__(parent)
        self.setWindowTitle("Ввод пункта ПВО")
        self.resize(400, 300)
        
        layout = QFormLayout(self)
        
        # ID пункта
        self.id_edit = QLineEdit()
        if point_data:
            self.id_edit.setText(point_data.get('id', ''))
        layout.addRow("ID пункта:", self.id_edit)
        
        # Наименование
        self.name_edit = QLineEdit()
        if point_data:
            self.name_edit.setText(point_data.get('name', ''))
        layout.addRow("Наименование:", self.name_edit)
        
        # Тип пункта
        self.type_combo = QComboBox()
        self.type_combo.addItems(["FIXED", "FREE", "APPROXIMATE"])
        if point_data:
            idx = self.type_combo.findText(point_data.get('type', 'FREE'))
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        layout.addRow("Тип пункта:", self.type_combo)
        
        # Статус пункта (исходный/рабочий)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["working", "initial"])  # рабочий / исходный
        if point_data:
            idx = self.status_combo.findText(point_data.get('status', 'working'))
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
        layout.addRow("Статус пункта:", self.status_combo)
        
        # Координата X
        self.x_edit = QLineEdit()
        if point_data:
            self.x_edit.setText(str(point_data.get('x', '')))
        layout.addRow("X (м):", self.x_edit)
        
        # Координата Y
        self.y_edit = QLineEdit()
        if point_data:
            self.y_edit.setText(str(point_data.get('y', '')))
        layout.addRow("Y (м):", self.y_edit)
        
        # Высота H
        self.h_edit = QLineEdit()
        if point_data:
            self.h_edit.setText(str(point_data.get('h', '')))
        layout.addRow("H (м):", self.h_edit)
        
        # Прибор
        self.instrument_edit = QLineEdit()
        if point_data:
            self.instrument_edit.setText(point_data.get('instrument', ''))
        layout.addRow("Прибор:", self.instrument_edit)
        
        # Примечание
        self.notes_edit = QLineEdit()
        if point_data:
            self.notes_edit.setText(point_data.get('notes', ''))
        layout.addRow("Примечание:", self.notes_edit)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_point_data(self):
        """Получение данных пункта"""
        return {
            'id': self.id_edit.text().strip(),
            'name': self.name_edit.text().strip() or self.id_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'status': self.status_combo.currentText(),  # Добавлен статус
            'x': self.x_edit.text().strip(),
            'y': self.y_edit.text().strip(),
            'h': self.h_edit.text().strip(),
            'instrument': self.instrument_edit.text().strip(),
            'notes': self.notes_edit.text().strip()
        }


class PointsTableWidget(QWidget):
    """Виджет таблицы пунктов с кнопками управления"""
    
    # Сигналы
    point_selected = pyqtSignal(str)
    point_deleted = pyqtSignal(list)
    point_added = pyqtSignal(dict)
    point_edited = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Добавить пункт")
        self.add_btn.clicked.connect(self._add_point_manual)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ Редактировать")
        self.edit_btn.clicked.connect(self._edit_point_manual)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self._delete_point)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.import_btn = QPushButton("📂 Импорт")
        self.import_btn.clicked.connect(self._import_points)
        button_layout.addWidget(self.import_btn)
        
        layout.addLayout(button_layout)
        
        # Таблица
        self.table_view = PointsTableView(self)
        self.table_view.point_selected.connect(self.point_selected)
        self.table_view.point_deleted.connect(self.point_deleted)
        self.table_view.point_added.connect(self.point_added)
        layout.addWidget(self.table_view)
    
    def _add_point_manual(self):
        """Ручное добавление пункта"""
        dialog = ManualPointInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            point_data = dialog.get_point_data()
            if not point_data['id']:
                QMessageBox.warning(self, "Ошибка", "ID пункта не может быть пустым")
                return
            
            # Добавление в таблицу
            self.table_view.add_point_from_data(point_data)
            self.point_added.emit(point_data)
    
    def _edit_point_manual(self):
        """Ручное редактирование пункта"""
        selected = self.table_view.get_selected_points()
        if not selected:
            QMessageBox.information(self, "Информация", "Выберите пункт для редактирования")
            return
        
        point_data = selected[0]
        dialog = ManualPointInputDialog(self, point_data)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_point_data()
            self.table_view.update_point(point_data['id'], updated_data)
            self.point_edited.emit(updated_data)
    
    def _delete_point(self):
        """Удаление пункта"""
        self.table_view._delete_point()
    
    def _import_points(self):
        """Импорт пунктов из файла"""
        self.table_view._export_points()  # Используем существующий метод
    
    def load_from_data(self, points):
        """Загрузка данных"""
        self.table_view.load_from_data(points)
    
    def update_data(self, points):
        """Обновление данных"""
        self.table_view.update_data(points)


class PointsTableView(QTableView):
    """Таблица пунктов ПВО"""
    
    # Сигналы
    point_selected = pyqtSignal(str)  # Сигнал при выборе пункта
    point_deleted = pyqtSignal(list)  # Сигнал при удалении пунктов
    point_added = pyqtSignal(dict)    # Сигнал при добавлении пункта
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Настройка таблицы
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        
        # Контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Модель данных
        self._setup_model()

        # Разрешить редактирование двойным кликом
        self.setEditTriggers(QTableView.DoubleClicked)

        # Сигнал выбора при изменении selection
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _setup_model(self):
        """Настройка модели данных"""
        self.model = QStandardItemModel(0, 9, self)  # Добавлена колонка для статуса
        self.model.setHorizontalHeaderLabels([
            "ID", "Наименование", "Тип", "Статус", "X (м)", "Y (м)",
            "H (м)", "Прибор", "Примечание"
        ])
        self.setModel(self.model)

        # Настройка делегатов для визуальных индикаторов
        self.setItemDelegateForColumn(2, PointTypeDelegate(self))  # Колонка "Тип"
        self.setItemDelegateForColumn(3, ComboBoxDelegate(["working", "initial"], self))  # Колонка "Статус"
    
    def _show_context_menu(self, position):
        """Показ контекстного меню"""
        menu = QMenu(self)
        
        # Команды редактирования
        add_action = QAction("Добавить пункт", self)
        add_action.triggered.connect(self._add_point)
        menu.addAction(add_action)
        
        delete_action = QAction("Удалить пункт", self)
        delete_action.triggered.connect(self._delete_point)
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        # Команды экспорта
        export_action = QAction("Экспорт в файл", self)
        export_action.triggered.connect(self._export_points)
        menu.addAction(export_action)
        
        copy_action = QAction("Копировать в буфер", self)
        copy_action.triggered.connect(self._copy_to_clipboard)
        menu.addAction(copy_action)
        
        menu.exec_(self.mapToGlobal(position))
    
    def _on_selection_changed(self, selected, deselected):
        """Обработка изменения выбора"""
        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            point_id = self.model.index(row, 0).data()
            if point_id:
                self.point_selected.emit(point_id)

    def _on_double_click(self, index):
        """Обработка двойного клика (для совместимости)"""
        row = index.row()
        if row >= 0:
            point_id = self.model.index(row, 0).data()
            if point_id:
                self.point_selected.emit(point_id)
    
    def _add_point(self):
        """Добавление пункта"""
        # Генерация нового ID
        new_id = f"P{self.model.rowCount() + 1:03d}"
        
        # Добавление строки
        row_data = [
            new_id,           # ID
            new_id,           # Наименование
            "FREE",           # Тип
            "working",        # Статус (по умолчанию рабочий)
            "",               # X
            "",               # Y
            "",               # H
            "",               # Прибор
            ""                # Примечание
        ]
        
        items = [QStandardItem(str(val)) for val in row_data]
        self.model.appendRow(items)
        
        # Генерация сигнала
        self.point_added.emit({
            'id': new_id,
            'name': new_id,
            'type': 'FREE',
            'status': 'working'
        })
    
    def _delete_point(self):
        """Удаление пункта"""
        # Получение выбранных строк
        selected_rows = self.selectionModel().selectedRows()
        
        if selected_rows:
            point_ids = []
            # Удаление в обратном порядке чтобы индексы не смещались
            for index in sorted(selected_rows, reverse=True):
                row = index.row()
                point_id = self.model.index(row, 0).data()
                if point_id:
                    point_ids.append(point_id)
                self.model.removeRow(row)
            
            # Генерация сигнала удаления
            self.point_deleted.emit(point_ids)
    
    def _export_points(self):
        """Экспорт пунктов"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт пунктов",
            "",
            "CSV Files (*.csv);;JSON Files (*.json);;Все файлы (*)"
        )
        
        if file_path:
            self._save_to_file(file_path)
    
    def _save_to_file(self, file_path: str):
        """Сохранение в файл"""
        import json
        import csv
        
        points = []
        for row in range(self.model.rowCount()):
            point_data = {
                'id': self.model.index(row, 0).data(),
                'name': self.model.index(row, 1).data(),
                'type': self.model.index(row, 2).data(),
                'status': self.model.index(row, 3).data(),  # Добавлен статус
                'x': self.model.index(row, 4).data(),
                'y': self.model.index(row, 5).data(),
                'h': self.model.index(row, 6).data(),
                'instrument': self.model.index(row, 7).data(),
                'notes': self.model.index(row, 8).data()
            }
            points.append(point_data)
        
        if file_path.endswith('.json'):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(points, f, indent=2, ensure_ascii=False)
        elif file_path.endswith('.csv'):
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Name', 'Type', 'Status', 'X', 'Y', 'H', 'Instrument', 'Notes'])
                for point in points:
                    writer.writerow([
                        point['id'], point['name'], point['type'], point['status'],
                        point['x'], point['y'], point['h'],
                        point['instrument'], point['notes']
                    ])
    
    def _copy_to_clipboard(self):
        """Копирование в буфер обмена"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QMimeData
        
        clipboard = QApplication.clipboard()
        
        # Формирование текста
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            lines = []
            for index in selected_rows:
                row = index.row()
                row_data = []
                for col in range(self.model.columnCount()):
                    row_data.append(str(self.model.index(row, col).data() or ""))
                lines.append("\t".join(row_data))
            
            mime_data = QMimeData()
            mime_data.setText("\n".join(lines))
            clipboard.setMimeData(mime_data)
    
    def load_from_data(self, points: list):
        """Загрузка данных из списка"""
        self.model.setRowCount(0)
        
        for point in points:
            row_data = [
                point.get('id', ''),
                point.get('name', ''),
                point.get('type', 'FREE'),
                point.get('status', 'working'),  # Добавлен статус
                str(point.get('x', '')),
                str(point.get('y', '')),
                str(point.get('h', '')),
                point.get('instrument', ''),
                point.get('notes', '')
            ]
            items = [QStandardItem(str(val)) for val in row_data]
            self.model.appendRow(items)
    
    def update_data(self, points: list):
        """Обновление данных таблицы (алиас для load_from_data)"""
        self.load_from_data(points)
    
    def get_selected_points(self) -> list:
        """Получение выбранных пунктов"""
        selected_rows = self.selectionModel().selectedRows()
        points = []
        
        for index in selected_rows:
            row = index.row()
            point_data = {
                'id': self.model.index(row, 0).data(),
                'name': self.model.index(row, 1).data(),
                'type': self.model.index(row, 2).data(),
                'status': self.model.index(row, 3).data(),  # Добавлен статус
                'x': self.model.index(row, 4).data(),
                'y': self.model.index(row, 5).data(),
                'h': self.model.index(row, 6).data(),
                'instrument': self.model.index(row, 7).data(),
                'notes': self.model.index(row, 8).data()
            }
            points.append(point_data)
        
        return points
    
    def add_point_from_data(self, point_data: dict):
        """Добавление пункта из данных"""
        row_data = [
            point_data.get('id', ''),
            point_data.get('name', ''),
            point_data.get('type', 'FREE'),
            point_data.get('status', 'working'),  # Добавлен статус
            str(point_data.get('x', '')),
            str(point_data.get('y', '')),
            str(point_data.get('h', '')),
            point_data.get('instrument', ''),
            point_data.get('notes', '')
        ]
        items = [QStandardItem(str(val)) for val in row_data]
        self.model.appendRow(items)
        self.point_added.emit(point_data)
    
    def update_point(self, point_id: str, updated_data: dict):
        """Обновление данных пункта"""
        for row in range(self.model.rowCount()):
            if self.model.index(row, 0).data() == point_id:
                self.model.setItem(row, 0, QStandardItem(updated_data.get('id', '')))
                self.model.setItem(row, 1, QStandardItem(updated_data.get('name', '')))
                self.model.setItem(row, 2, QStandardItem(updated_data.get('type', 'FREE')))
                self.model.setItem(row, 3, QStandardItem(updated_data.get('status', 'working')))  # Статус
                self.model.setItem(row, 4, QStandardItem(str(updated_data.get('x', ''))))
                self.model.setItem(row, 5, QStandardItem(str(updated_data.get('y', ''))))
                self.model.setItem(row, 6, QStandardItem(str(updated_data.get('h', ''))))
                self.model.setItem(row, 7, QStandardItem(updated_data.get('instrument', '')))
                self.model.setItem(row, 8, QStandardItem(updated_data.get('notes', '')))
                break
