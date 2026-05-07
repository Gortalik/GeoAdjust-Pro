"""
Виджет свойств для GeoAdjust Pro

Отображение и редактирование свойств выбранных объектов
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, 
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal


class PropertiesWidget(QWidget):
    """Виджет свойств объектов"""
    
    properties_changed = pyqtSignal(dict)  # signal с изменёнными свойствами
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Заголовок
        self.title_label = QLabel("Свойства")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 11px; padding: 3px;")
        layout.addWidget(self.title_label)
        
        # Контейнер свойств
        self.properties_container = QWidget()
        self.properties_layout = QFormLayout(self.properties_container)
        self.properties_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.properties_layout.setContentsMargins(0, 0, 0, 0)
        self.properties_layout.setSpacing(2)
        
        layout.addWidget(self.properties_container)
        layout.addStretch()
        
        # Кнопки действий - компактные
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(2)
        
        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self._apply_changes)
        apply_btn.setMaximumHeight(24)
        actions_layout.addWidget(apply_btn)
        
        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self._reset_changes)
        reset_btn.setMaximumHeight(24)
        actions_layout.addWidget(reset_btn)
        
        layout.addLayout(actions_layout)
        
        # Текущий объект
        self.current_object = None
        self.property_widgets = {}
        
        # Установка минимального размера виджета
        self.setMinimumSize(180, 200)
    
    def set_point_properties(self, point_id: str, properties: dict):
        """Установка свойств пункта"""
        print(f"DEBUG: PropertiesWidget.set_point_properties called for {point_id}")
        print(f"DEBUG: Properties data: {properties}")
        self.current_object = {"type": "point", "id": point_id}
        self.title_label.setText(f"Свойства пункта: {point_id}")
        print(f"DEBUG: Title set to: {self.title_label.text()}")
        print(f"DEBUG: Current object set to: {self.current_object}")

        self._clear_properties()
        print("DEBUG: Properties cleared")
        
        # ID пункта (только чтение)
        id_edit = QLineEdit(point_id)
        id_edit.setReadOnly(True)
        self.properties_layout.addRow("ID:", id_edit)
        self.property_widgets["id"] = id_edit
        print(f"DEBUG: Added ID field: {point_id}")
        
        # Тип пункта
        type_combo = QComboBox()
        type_combo.addItems(["FIXED", "APPROXIMATE", "FREE"])
        type_combo.setCurrentText(properties.get("coord_type", "FREE"))
        self.properties_layout.addRow("Тип:", type_combo)
        self.property_widgets["coord_type"] = type_combo
        
        # Координаты X
        x_spin = QDoubleSpinBox()
        x_spin.setRange(-1e9, 1e9)
        x_spin.setValue(properties.get("x", 0.0))
        x_spin.setDecimals(4)
        self.properties_layout.addRow("X:", x_spin)
        self.property_widgets["x"] = x_spin
        
        # Координаты Y
        y_spin = QDoubleSpinBox()
        y_spin.setRange(-1e9, 1e9)
        y_spin.setValue(properties.get("y", 0.0))
        y_spin.setDecimals(4)
        self.properties_layout.addRow("Y:", y_spin)
        self.property_widgets["y"] = y_spin
        
        # Высота H
        h_spin = QDoubleSpinBox()
        h_spin.setRange(-1000, 10000)
        h_spin.setValue(properties.get("h", 0.0) or 0.0)
        h_spin.setDecimals(4)
        self.properties_layout.addRow("H:", h_spin)
        self.property_widgets["h"] = h_spin
        
        # Класс точности
        class_combo = QComboBox()
        class_combo.addItems(["", "Полигонометрия 4 класса", "Нивелирование III класса"])
        class_combo.setCurrentText(properties.get("normative_class", ""))
        self.properties_layout.addRow("Класс точности:", class_combo)
        self.property_widgets["normative_class"] = class_combo
        
        # σ X (апостериорная)
        sigma_x_spin = QDoubleSpinBox()
        sigma_x_spin.setRange(0, 1000)
        sigma_x_spin.setValue(properties.get("sigma_x", 0.0))
        sigma_x_spin.setDecimals(4)
        sigma_x_spin.setSuffix(" м")
        self.properties_layout.addRow("σ X:", sigma_x_spin)
        self.property_widgets["sigma_x"] = sigma_x_spin
        
        # σ Y (апостериорная)
        sigma_y_spin = QDoubleSpinBox()
        sigma_y_spin.setRange(0, 1000)
        sigma_y_spin.setValue(properties.get("sigma_y", 0.0))
        sigma_y_spin.setDecimals(4)
        sigma_y_spin.setSuffix(" м")
        self.properties_layout.addRow("σ Y:", sigma_y_spin)
        self.property_widgets["sigma_y"] = sigma_y_spin

        print(f"DEBUG: Все поля свойств добавлены. Количество виджетов: {len(self.property_widgets)}")
        print(f"DEBUG: Properties widget готов к отображению")
    
    def set_observation_properties(self, obs_id: str, properties: dict):
        """Установка свойств измерения"""
        self.current_object = {"type": "observation", "id": obs_id}
        self.title_label.setText(f"Свойства измерения: {obs_id}")
        
        self._clear_properties()
        
        # ID измерения (только чтение)
        id_edit = QLineEdit(obs_id)
        id_edit.setReadOnly(True)
        self.properties_layout.addRow("ID:", id_edit)
        self.property_widgets["id"] = id_edit
        
        # Тип измерения
        type_combo = QComboBox()
        type_combo.addItems(["direction", "distance", "height_diff", "gnss_vector"])
        type_combo.setCurrentText(properties.get("obs_type", "direction"))
        self.properties_layout.addRow("Тип:", type_combo)
        self.property_widgets["obs_type"] = type_combo
        
        # Откуда
        from_edit = QLineEdit(properties.get("from_point", ""))
        from_edit.setReadOnly(True)
        self.properties_layout.addRow("От пункта:", from_edit)
        self.property_widgets["from_point"] = from_edit
        
        # Куда
        to_edit = QLineEdit(properties.get("to_point", ""))
        to_edit.setReadOnly(True)
        self.properties_layout.addRow("На пункт:", to_edit)
        self.property_widgets["to_point"] = to_edit
        
        # Значение
        value_spin = QDoubleSpinBox()
        value_spin.setRange(-1e9, 1e9)
        value_spin.setValue(properties.get("value", 0.0))
        value_spin.setDecimals(6)
        self.properties_layout.addRow("Значение:", value_spin)
        self.property_widgets["value"] = value_spin
        
        # Прибор
        instrument_edit = QLineEdit(properties.get("instrument_name", ""))
        self.properties_layout.addRow("Прибор:", instrument_edit)
        self.property_widgets["instrument_name"] = instrument_edit
        
        # σ апостериорная
        sigma_spin = QDoubleSpinBox()
        sigma_spin.setRange(0, 1000)
        sigma_spin.setValue(properties.get("sigma_apriori", 0.0) or 0.0)
        sigma_spin.setDecimals(6)
        self.properties_layout.addRow("σ:", sigma_spin)
        self.property_widgets["sigma_apriori"] = sigma_spin
        
        # Активно
        active_check = QCheckBox()
        active_check.setChecked(properties.get("is_active", True))
        self.properties_layout.addRow("Активно:", active_check)
        self.property_widgets["is_active"] = active_check
        
        # Множитель веса
        weight_spin = QDoubleSpinBox()
        weight_spin.setRange(0.01, 100)
        weight_spin.setValue(properties.get("weight_multiplier", 1.0))
        weight_spin.setDecimals(3)
        self.properties_layout.addRow("Множитель веса:", weight_spin)
        self.property_widgets["weight_multiplier"] = weight_spin
    
    def _clear_properties(self):
        """Очистка всех свойств"""
        while self.properties_layout.count():
            item = self.properties_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.property_widgets.clear()
    
    def _apply_changes(self):
        """Применение изменений"""
        if not self.current_object:
            return
        
        changes = {}
        for key, widget in self.property_widgets.items():
            if isinstance(widget, QLineEdit):
                changes[key] = widget.text()
            elif isinstance(widget, QComboBox):
                changes[key] = widget.currentText()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                changes[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                changes[key] = widget.isChecked()
        
        self.properties_changed.emit(changes)
    
    def _reset_changes(self):
        """Сброс изменений"""
        if self.current_object:
            # TODO: Загрузить исходные свойства
            pass
    
    def clear(self):
        """Очистка виджета свойств"""
        self.current_object = None
        self.title_label.setText("Свойства")
        self._clear_properties()
