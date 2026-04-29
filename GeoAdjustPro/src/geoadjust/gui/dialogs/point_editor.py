"""
Диалог редактирования пунктов ПВО
"""

from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QDialogButtonBox, QGroupBox, QMessageBox, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class PointEditorDialog(QDialog):
    """Диалог для создания/редактирования пункта ПВО"""
    
    def __init__(self, point_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        
        self.point_data = point_data or {}
        self.is_edit_mode = bool(point_data)
        
        self.setWindowTitle("Редактирование пункта" if self.is_edit_mode else "Новый пункт")
        self.setMinimumWidth(500)
        
        self._create_ui()
        self._load_data()
    
    def _create_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout(self)
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка "Основные"
        main_tab = self._create_main_tab()
        tabs.addTab(main_tab, "Основные")
        
        # Вкладка "Координаты"
        coords_tab = self._create_coords_tab()
        tabs.addTab(coords_tab, "Координаты")
        
        # Вкладка "Точность"
        accuracy_tab = self._create_accuracy_tab()
        tabs.addTab(accuracy_tab, "Точность")
        
        layout.addWidget(tabs)
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _create_main_tab(self) -> QWidget:
        """Создание вкладки основных параметров"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Название пункта
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: ПЗ1, RP1, 101")
        layout.addRow("Название:", self.name_edit)
        
        # Тип пункта
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Исходный (фиксированный)",
            "Определяемый (свободный)",
            "Приближенный"
        ])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("Тип пункта:", self.type_combo)
        
        # Статус плановых координат
        self.plan_status_combo = QComboBox()
        self.plan_status_combo.addItems(["initial", "working"])
        layout.addRow("Статус плана:", self.plan_status_combo)
        
        # Статус высоты
        self.height_status_combo = QComboBox()
        self.height_status_combo.addItems(["initial", "working"])
        layout.addRow("Статус высоты:", self.height_status_combo)
        
        # Описание
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Описание местоположения")
        layout.addRow("Описание:", self.description_edit)
        
        # Класс пункта
        self.class_combo = QComboBox()
        self.class_combo.addItems([
            "1 класс",
            "2 класс",
            "3 класс",
            "4 класс",
            "1 разряд",
            "2 разряд",
            "Съемочная сеть"
        ])
        layout.addRow("Класс:", self.class_combo)
        
        return widget
    
    def _create_coords_tab(self) -> QWidget:
        """Создание вкладки координат"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Плановые координаты
        plan_group = QGroupBox("Плановые координаты")
        plan_layout = QFormLayout(plan_group)
        
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-999999999.999, 999999999.999)
        self.x_spin.setDecimals(4)
        self.x_spin.setSuffix(" м")
        plan_layout.addRow("X (Север):", self.x_spin)
        
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-999999999.999, 999999999.999)
        self.y_spin.setDecimals(4)
        self.y_spin.setSuffix(" м")
        plan_layout.addRow("Y (Восток):", self.y_spin)
        
        layout.addWidget(plan_group)
        
        # Высотные координаты
        height_group = QGroupBox("Высотные координаты")
        height_layout = QFormLayout(height_group)
        
        self.h_spin = QDoubleSpinBox()
        self.h_spin.setRange(-999.999, 9999.999)
        self.h_spin.setDecimals(4)
        self.h_spin.setSuffix(" м")
        height_layout.addRow("H (высота):", self.h_spin)
        
        self.has_height_check = QCheckBox("Высота определена")
        self.has_height_check.setChecked(True)
        height_layout.addRow("", self.has_height_check)
        
        layout.addWidget(height_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_accuracy_tab(self) -> QWidget:
        """Создание вкладки точности"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # СКО плановых координат
        plan_accuracy_group = QGroupBox("СКО плановых координат")
        plan_accuracy_layout = QFormLayout(plan_accuracy_group)
        
        self.mx_spin = QDoubleSpinBox()
        self.mx_spin.setRange(0.0001, 999.9999)
        self.mx_spin.setDecimals(4)
        self.mx_spin.setValue(0.01)
        self.mx_spin.setSuffix(" м")
        plan_accuracy_layout.addRow("mX:", self.mx_spin)
        
        self.my_spin = QDoubleSpinBox()
        self.my_spin.setRange(0.0001, 999.9999)
        self.my_spin.setDecimals(4)
        self.my_spin.setValue(0.01)
        self.my_spin.setSuffix(" м")
        plan_accuracy_layout.addRow("mY:", self.my_spin)
        
        layout.addWidget(plan_accuracy_group)
        
        # СКО высоты
        height_accuracy_group = QGroupBox("СКО высоты")
        height_accuracy_layout = QFormLayout(height_accuracy_group)
        
        self.mh_spin = QDoubleSpinBox()
        self.mh_spin.setRange(0.0001, 999.9999)
        self.mh_spin.setDecimals(4)
        self.mh_spin.setValue(0.01)
        self.mh_spin.setSuffix(" м")
        height_accuracy_layout.addRow("mH:", self.mh_spin)
        
        layout.addWidget(height_accuracy_group)
        
        layout.addStretch()
        
        return widget
    
    def _on_type_changed(self, index: int):
        """Обработчик изменения типа пункта"""
        # Для исходных пунктов координаты обязательны
        is_fixed = (index == 0)
        
        # Можно добавить логику блокировки/разблокировки полей
        pass
    
    def _load_data(self):
        """Загрузка данных в форму"""
        if not self.point_data:
            return
        
        self.name_edit.setText(self.point_data.get('name', ''))
        self.description_edit.setText(self.point_data.get('description', ''))
        
        # Тип пункта
        point_type = self.point_data.get('type', 'free')
        type_index = {'fixed': 0, 'free': 1, 'approximate': 2}.get(point_type, 1)
        self.type_combo.setCurrentIndex(type_index)
        
        # Статусы плана и высоты
        plan_status = self.point_data.get('plan_status', 'working')
        plan_idx = self.plan_status_combo.findText(plan_status)
        if plan_idx >= 0:
            self.plan_status_combo.setCurrentIndex(plan_idx)
        
        height_status = self.point_data.get('height_status', 'working')
        height_idx = self.height_status_combo.findText(height_status)
        if height_idx >= 0:
            self.height_status_combo.setCurrentIndex(height_idx)
        
        # Класс
        point_class = self.point_data.get('class', '4 класс')
        class_index = self.class_combo.findText(point_class)
        if class_index >= 0:
            self.class_combo.setCurrentIndex(class_index)
        
        # Координаты
        self.x_spin.setValue(self.point_data.get('x', 0.0))
        self.y_spin.setValue(self.point_data.get('y', 0.0))
        self.h_spin.setValue(self.point_data.get('h', 0.0))
        
        # Точность
        self.mx_spin.setValue(self.point_data.get('mx', 0.01))
        self.my_spin.setValue(self.point_data.get('my', 0.01))
        self.mh_spin.setValue(self.point_data.get('mh', 0.01))
        
        # Наличие высоты
        self.has_height_check.setChecked(self.point_data.get('has_height', True))
    
    def _validate_and_accept(self):
        """Валидация данных и принятие"""
        # Проверка названия
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название пункта")
            self.name_edit.setFocus()
            return
        
        # Проверка координат для исходных пунктов
        if self.type_combo.currentIndex() == 0:  # Исходный
            if self.x_spin.value() == 0.0 and self.y_spin.value() == 0.0:
                reply = QMessageBox.question(
                    self,
                    "Предупреждение",
                    "Координаты исходного пункта равны нулю. Продолжить?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
        
        self.accept()
    
    def get_point_data(self) -> Dict[str, Any]:
        """Получение данных пункта"""
        type_map = {0: 'fixed', 1: 'free', 2: 'approximate'}
        
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.text().strip(),
            'type': type_map[self.type_combo.currentIndex()],
            'class': self.class_combo.currentText(),
            'plan_status': self.plan_status_combo.currentText(),
            'height_status': self.height_status_combo.currentText(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'h': self.h_spin.value() if self.has_height_check.isChecked() else None,
            'mx': self.mx_spin.value(),
            'my': self.my_spin.value(),
            'mh': self.mh_spin.value(),
            'has_height': self.has_height_check.isChecked()
        }
