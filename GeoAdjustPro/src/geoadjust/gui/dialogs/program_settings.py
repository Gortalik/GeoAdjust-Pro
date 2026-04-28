# src/geoadjust/gui/dialogs/program_settings.py
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit,
    QTextEdit, QTabWidget, QWidget, QMessageBox, QDialogButtonBox
)
from PyQt5.QtCore import pyqtSignal, Qt
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'crs': {'base_crs': 'SK42', 'zone': 7, 'ellipsoid': 'Krasovsky1940'},
    'adjustment': {'method': 'classic', 'max_iterations': 10, 'convergence': 1e-6, 'robust': False},
    'preprocessing': {'check_closure': True, 'check_reciprocal': True, 'apply_corrections': True},
    'instruments': {'default_angular_accuracy': 5.0, 'default_distance_const': 2.0, 'default_distance_ppm': 2.0},
    'interface': {'theme': 'light', 'language': 'ru', 'autosave_interval': 5}
}

class ProgramSettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.config = self._load_config()
        self.setWindowTitle("Настройки программы")
        self.resize(850, 600)
        self._init_ui()
        self._load_to_ui()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки настроек: {e}")
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        self.settings_changed.emit(self.config)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._create_crs_tab(), "Система координат")
        tabs.addTab(self._create_adjustment_tab(), "Уравнивание")
        tabs.addTab(self._create_preprocessing_tab(), "Предобработка")
        tabs.addTab(self._create_interface_tab(), "Интерфейс")
        layout.addWidget(tabs)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        layout.addWidget(btn_box)

    def _create_crs_tab(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.crs_combo = QComboBox()
        self.crs_combo.addItems(['SK42', 'SK95', 'GSK2011', 'WGS84'])
        layout.addRow("Базовая СК:", self.crs_combo)
        self.zone_spin = QSpinBox()
        self.zone_spin.setRange(1, 60)
        layout.addRow("Номер зоны:", self.zone_spin)
        self.ellipsoid_combo = QComboBox()
        self.ellipsoid_combo.addItems(['Krasovsky1940', 'GRS80', 'WGS84'])
        layout.addRow("Эллипсоид:", self.ellipsoid_combo)
        return page

    def _create_adjustment_tab(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.method_combo = QComboBox()
        self.method_combo.addItems(['classic', 'robust_huber', 'robust_tukey', 'l1_min'])
        layout.addRow("Метод:", self.method_combo)
        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 50)
        layout.addRow("Макс. итераций:", self.max_iter_spin)
        self.conv_spin = QDoubleSpinBox()
        self.conv_spin.setRange(1e-10, 1e-1)
        layout.addRow("Порог сходимости:", self.conv_spin)
        self.robust_check = QCheckBox("Включить робастное уравнивание")
        layout.addRow("", self.robust_check)
        return page

    def _create_preprocessing_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.check_closure = QCheckBox("Контроль замыкания горизонта")
        self.check_reciprocal = QCheckBox("Контроль прямых/обратных измерений")
        self.apply_corrections = QCheckBox("Применять атмосферные и рефракционные поправки")
        layout.addWidget(self.check_closure)
        layout.addWidget(self.check_reciprocal)
        layout.addWidget(self.apply_corrections)
        layout.addStretch()
        return page

    def _create_interface_tab(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['light', 'dark', 'system'])
        layout.addRow("Тема:", self.theme_combo)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['ru', 'en'])
        layout.addRow("Язык:", self.lang_combo)
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(1, 60)
        layout.addRow("Автосохранение (мин):", self.autosave_spin)
        return page

    def _load_to_ui(self):
        c = self.config.get('crs', {})
        self.crs_combo.setCurrentText(c.get('base_crs', 'SK42'))
        self.zone_spin.setValue(c.get('zone', 7))
        self.ellipsoid_combo.setCurrentText(c.get('ellipsoid', 'Krasovsky1940'))
        
        a = self.config.get('adjustment', {})
        self.method_combo.setCurrentText(a.get('method', 'classic'))
        self.max_iter_spin.setValue(a.get('max_iterations', 10))
        self.conv_spin.setValue(a.get('convergence', 1e-6))
        self.robust_check.setChecked(a.get('robust', False))
        
        p = self.config.get('preprocessing', {})
        self.check_closure.setChecked(p.get('check_closure', True))
        self.check_reciprocal.setChecked(p.get('check_reciprocal', True))
        self.apply_corrections.setChecked(p.get('apply_corrections', True))
        
        i = self.config.get('interface', {})
        self.theme_combo.setCurrentText(i.get('theme', 'light'))
        self.lang_combo.setCurrentText(i.get('language', 'ru'))
        self.autosave_spin.setValue(i.get('autosave_interval', 5))

    def _save_from_ui(self):
        self.config['crs'] = {
            'base_crs': self.crs_combo.currentText(),
            'zone': self.zone_spin.value(),
            'ellipsoid': self.ellipsoid_combo.currentText()
        }
        self.config['adjustment'] = {
            'method': self.method_combo.currentText(),
            'max_iterations': self.max_iter_spin.value(),
            'convergence': self.conv_spin.value(),
            'robust': self.robust_check.isChecked()
        }
        self.config['preprocessing'] = {
            'check_closure': self.check_closure.isChecked(),
            'check_reciprocal': self.check_reciprocal.isChecked(),
            'apply_corrections': self.apply_corrections.isChecked()
        }
        self.config['interface'] = {
            'theme': self.theme_combo.currentText(),
            'language': self.lang_combo.currentText(),
            'autosave_interval': self.autosave_spin.value()
        }
        self._save_config()

    def _apply(self):
        self._save_from_ui()
        self.parent().statusBar().showMessage("Настройки применены", 3000)

    def accept(self):
        self._save_from_ui()
        super().accept()