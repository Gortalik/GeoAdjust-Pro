"""
Диалог импорта данных из различных форматов
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QTextEdit,
    QDialogButtonBox, QGroupBox, QMessageBox, QFileDialog,
    QProgressBar, QTabWidget, QWidget, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
import logging

logger = logging.getLogger(__name__)


class ImportWorker(QThread):
    """Рабочий поток для импорта данных"""
    
    progress_updated = pyqtSignal(int, str)
    import_finished = pyqtSignal(dict)
    import_error = pyqtSignal(str)
    
    def __init__(self, file_path: str, format_type: str, options: Dict):
        super().__init__()
        self.file_path = file_path
        self.format_type = format_type
        self.options = options
    
    def run(self):
        """Выполнение импорта (больше не используется)"""
        pass
    
    def _import_dat(self) -> Dict:
        """Импорт из формата DAT (цифровые нивелиры)"""
        from geoadjust.io.formats.dat import DATParser
        from pathlib import Path
        
        self.progress_updated.emit(30, "Парсинг DAT файла...")
        
        parser = DATParser()
        data = parser.parse(Path(self.file_path))
        
        self.progress_updated.emit(80, "Обработка данных...")
        
        # Конвертация в формат, ожидаемый приложением
        points = []
        for p in data.get('points', []):
            points.append({
                'name': p.get('point_id', ''),
                'x': p.get('x', 0) or 0,
                'y': p.get('y', 0) or 0,
                'h': p.get('h', 0) or 0,
                'type': p.get('point_type', 'free')
            })
        
        observations = []
        for obs in data.get('observations', []):
            # Преобразуем типы DAT в стандартные типы
            obs_type = getattr(obs, 'obs_type', 'height_diff')
            
            # Преобразование типов DAT в типы для уравнивания
            if obs_type in ['backsight', 'foresight', 'intermediate']:
                # Эти типы преобразуем в height_diff (превышение)
                obs_type = 'height_diff'
            
            # Для превышений используем стандартную точность
            std_dev = 0.005  # 5 мм для нивелирования
            if obs_type == 'height_diff':
                # Типичная точность нивелирования
                std_dev = 0.005  # 5 мм/км для IV класса
            elif obs_type == 'distance':
                std_dev = 0.001  # 1 мм для расстояний
            
            observations.append({
                'from_point': getattr(obs, 'from_point', ''),
                'to_point': getattr(obs, 'to_point', ''),
                'type': obs_type,
                'value': getattr(obs, 'value', 0),
                'sigma': std_dev
            })
        
        # Фильтруем только превышения для нивелирного хода
        height_diff_obs = [o for o in observations if o['type'] == 'height_diff']
        
        return {
            'points': points,
            'observations': height_diff_obs if height_diff_obs else observations,
            'metadata': data.get('header_info', {}),
            'original_observations': len(observations)
        }
    
    def _import_gsi(self) -> Dict:
        """Импорт из формата GSI (Leica)"""
        from geoadjust.io.formats.gsi import GSIParser
        from pathlib import Path

        parser = GSIParser()
        data = parser.parse(Path(self.file_path))
        
        # Конвертация в формат, ожидаемый приложением
        points = []
        for p in data.get('points', []):
            points.append({
                'name': p.get('point_id', ''),
                'x': p.get('x', 0) or 0,
                'y': p.get('y', 0) or 0,
                'h': p.get('h', 0) or 0,
                'type': p.get('point_type', 'free')
            })
        
        observations = []
        for obs in data.get('observations', []):
            observations.append({
                'from_point': getattr(obs, 'from_point', ''),
                'to_point': getattr(obs, 'to_point', ''),
                'type': getattr(obs, 'obs_type', 'direction'),
                'value': getattr(obs, 'value', 0),
                'sigma': getattr(obs, 'std_dev', 0.00005),
                'station_session_id': getattr(obs, 'station_session_id', ''),
                'instrument_height': getattr(obs, 'instrument_height', None),
                'target_height': getattr(obs, 'target_height', None),
            })
        
        # Конвертация сессий станций для UI
        station_sessions = []
        for session in data.get('station_sessions', []):
            session_data = {
                'session_id': session.session_id,
                'station_name': session.station_name,
                'instrument_height': session.instrument_height,
                'target_height': session.target_height,
                'temperature': session.temperature,
                'pressure': session.pressure,
                'num_observations': len(session.observations),
                'line_start': session.line_start,
                'line_end': session.line_end,
                'observations': []
            }
            for obs in session.observations:
                session_data['observations'].append({
                    'obs_type': obs.obs_type,
                    'from_point': obs.from_point,
                    'to_point': obs.to_point,
                    'value': obs.value,
                    'line_number': obs.line_number,
                })
            station_sessions.append(session_data)
        
        return {
            'points': points,
            'observations': observations,
            'station_sessions': station_sessions,
            'metadata': {
                'version': data.get('version', ''),
                'encoding': data.get('encoding', ''),
                'num_station_sessions': data.get('num_station_sessions', 0)
            }
        }
    
    def _import_sdr(self) -> Dict:
        """Импорт из формата SDR (Sokkia)"""
        from geoadjust.io.formats.sdr import SDRParser
        from pathlib import Path

        parser = SDRParser()
        data = parser.parse(Path(self.file_path))
        
        # Конвертация в формат, ожидаемый приложением
        points = []
        for p in data.get('points', []):
            points.append({
                'name': p.get('point_id', ''),
                'x': p.get('x', 0) or 0,
                'y': p.get('y', 0) or 0,
                'h': p.get('h', 0) or 0,
                'type': p.get('point_type', 'free')
            })
        
        observations = []
        for obs in data.get('observations', []):
            # Если это CombinedObservation, оставить как объект
            if hasattr(obs, 'horizontal_angle') or hasattr(obs, 'zenith_angle') or hasattr(obs, 'slope_distance'):
                observations.append(obs)
            else:
                # Обычное измерение
                observations.append({
                    'from_point': getattr(obs, 'from_point_id', ''),
                    'to_point': getattr(obs, 'to_point_id', ''),
                    'type': getattr(obs, 'obs_type', 'direction'),
                    'value': getattr(obs, 'value', 0),
                    'sigma': getattr(obs, 'sigma_apriori', 0.00005),
                    'from_setup_id': getattr(obs, 'from_setup_id', ''),
                    'face_position': getattr(obs, 'face_position', None)
                })
        
        # Конвертация сессий станций для UI
        station_sessions = []
        for setup in data.get('setups', []):
            # Группируем измерения по этой установке (сравниваем setup_id)
            # Для CombinedObservation используем from_setup_id
            setup_observations = [obs for obs in observations if getattr(obs, 'from_setup_id', getattr(obs, 'setup_id', '')) == setup.setup_id]

            # Конвертируем измерения в формат словарей для UI
            setup_observations_ui = []
            for obs in setup_observations:
                # Для CombinedObservation используем правильные атрибуты
                setup_observations_ui.append({
                    'obs_type': getattr(obs, 'obs_type', ''),
                    'from_point': getattr(obs, 'from_point_id', ''),
                    'to_point': getattr(obs, 'to_point_id', ''),
                    'value': getattr(obs, 'value', 0),
                    'setup_id': getattr(obs, 'from_setup_id', ''),
                    'face_position': getattr(obs, 'face_position', None),
                    # Дополнительные поля для CombinedObservation
                    'horizontal_angle': getattr(obs, 'horizontal_angle', None),
                    'zenith_angle': getattr(obs, 'zenith_angle', None),
                    'slope_distance': getattr(obs, 'slope_distance', None)
                })

            session_data = {
                'session_id': setup.setup_id,
                'station_name': setup.point_id,
                'instrument_height': setup.instrument_height,
                'target_height': setup.target_height,
                'orientation_angle': setup.orientation_angle,
                'temperature': getattr(setup, 'temperature', None),
                'pressure': getattr(setup, 'pressure', None),
                'num_observations': len(setup_observations),
                'timestamp': setup.timestamp,
                'observations': setup_observations_ui
            }
            station_sessions.append(session_data)

        return {
            'points': points,
            'observations': observations,
            'station_sessions': station_sessions,
            'metadata': {'job_name': data.get('job_name', ''), 'encoding': data.get('encoding', '')}
        }
    
    def _import_pos(self) -> Dict:
        """Импорт из формата POS (RTKLIB GNSS векторы)"""
        from geoadjust.io.formats.pos import POSParser
        from pathlib import Path
        
        self.progress_updated.emit(30, "Парсинг POS файла...")
        
        parser = POSParser()
        data = parser.parse(Path(self.file_path))
        
        self.progress_updated.emit(80, "Обработка данных...")
        
        # Получаем GNSS вектор
        vector = parser.get_gnss_vector()
        
        points = []
        observations = []
        
        if vector:
            # Добавляем точки
            points.append({
                'name': vector.from_station,
                'x': 0, 'y': 0, 'h': 0,
                'type': 'fixed'
            })
            points.append({
                'name': vector.to_station,
                'x': 0, 'y': 0, 'h': 0,
                'type': 'free'
            })
            
            # Добавляем GNSS вектор как измерение
            observations.append({
                'from_point': vector.from_station,
                'to_point': vector.to_station,
                'type': 'gnss_vector',
                'value': 0,  # Базовое значение
                'sigma': (vector.sigma_dx + vector.sigma_dy + vector.sigma_dz) / 3,
                'delta_x': vector.dx,
                'delta_y': vector.dy,
                'delta_z': vector.dz,
                'sigma_x': vector.sigma_dx,
                'sigma_y': vector.sigma_dy,
                'sigma_z': vector.sigma_dz
            })
        
        return {
            'points': points,
            'observations': observations,
            'metadata': {
                'from_station': data.get('from_station', ''),
                'to_station': data.get('to_station', ''),
                'ref_position': data.get('ref_position', None),
                'num_epochs': data.get('num_epochs', 0)
            }
        }
    
    def _import_csv(self) -> Dict:
        """Импорт из CSV файла"""
        import csv
        
        self.progress_updated.emit(30, "Чтение CSV файла...")
        
        points = []
        observations = []
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Определение типа данных по наличию полей
                if 'x' in row and 'y' in row:
                    # Это пункт
                    points.append({
                        'name': row.get('name', row.get('id', '')),
                        'x': float(row['x']),
                        'y': float(row['y']),
                        'h': float(row.get('h', row.get('z', 0))),
                        'type': row.get('type', 'free')
                    })
                elif 'from_point' in row and 'to_point' in row:
                    # Это измерение
                    observations.append({
                        'from_point': row['from_point'],
                        'to_point': row['to_point'],
                        'type': row.get('type', 'direction'),
                        'value': float(row.get('value', 0)),
                        'sigma': float(row.get('sigma', 5.0))
                    })
        
        self.progress_updated.emit(80, "Обработка данных...")
        
        return {
            'points': points,
            'observations': observations,
            'metadata': {}
        }
    
    def _import_txt(self) -> Dict:
        """Импорт из текстового файла"""
        self.progress_updated.emit(30, "Чтение текстового файла...")
        
        points = []
        observations = []
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Простой парсинг: каждая строка - пункт или измерение
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            
            if len(parts) >= 3:
                # Попытка распознать как пункт (имя x y [h])
                try:
                    name = parts[0]
                    x = float(parts[1])
                    y = float(parts[2])
                    h = float(parts[3]) if len(parts) > 3 else 0.0
                    
                    points.append({
                        'name': name,
                        'x': x,
                        'y': y,
                        'h': h,
                        'type': 'free'
                    })
                except ValueError:
                    # Не удалось распознать
                    pass
        
        self.progress_updated.emit(80, "Обработка данных...")
        
        return {
            'points': points,
            'observations': observations,
            'metadata': {}
        }


class ImportDialog(QDialog):
    """Диалог импорта данных"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.imported_data = None
        self.worker = None
        
        self.setWindowTitle("Импорт данных")
        self.setMinimumSize(700, 500)
        
        self._create_ui()
    
    def _create_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout(self)
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка "Файл"
        file_tab = self._create_file_tab()
        tabs.addTab(file_tab, "Выбор файла")
        
        # Вкладка "Параметры"
        options_tab = self._create_options_tab()
        tabs.addTab(options_tab, "Параметры")
        
        # Вкладка "Предпросмотр"
        preview_tab = self._create_preview_tab()
        tabs.addTab(preview_tab, "Предпросмотр")
        
        layout.addWidget(tabs)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Статус
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("Импортировать")
        self.import_btn.clicked.connect(self._start_import)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        button_layout.addWidget(self.ok_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_file_tab(self) -> QWidget:
        """Создание вкладки выбора файла"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Выбор файла
        file_group = QGroupBox("Файл для импорта")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        file_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # Формат файла
        format_group = QGroupBox("Формат данных")
        format_layout = QFormLayout(format_group)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Автоопределение",
            "DAT (цифровые нивелиры)",
            "GSI (Leica)",
            "SDR (Sokkia)",
            "Excel (Credo DAT)",
            "POS (RTKLIB GNSS)",
            "CSV (разделители запятыми)",
            "TXT (текстовый файл)"
        ])
        format_layout.addRow("Формат:", self.format_combo)
        
        layout.addWidget(format_group)
        
        # Информация о файле
        info_group = QGroupBox("Информация о файле")
        info_layout = QFormLayout(info_group)
        
        self.file_size_label = QLabel("-")
        info_layout.addRow("Размер:", self.file_size_label)
        
        self.file_encoding_label = QLabel("-")
        info_layout.addRow("Кодировка:", self.file_encoding_label)
        
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_options_tab(self) -> QWidget:
        """Создание вкладки параметров"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Параметры импорта
        import_group = QGroupBox("Параметры импорта")
        import_layout = QVBoxLayout(import_group)
        
        self.import_points_check = QCheckBox("Импортировать пункты")
        self.import_points_check.setChecked(True)
        import_layout.addWidget(self.import_points_check)
        
        self.import_observations_check = QCheckBox("Импортировать измерения")
        self.import_observations_check.setChecked(True)
        import_layout.addWidget(self.import_observations_check)
        
        self.skip_duplicates_check = QCheckBox("Пропускать дубликаты")
        self.skip_duplicates_check.setChecked(True)
        import_layout.addWidget(self.skip_duplicates_check)
        
        self.update_existing_check = QCheckBox("Обновлять существующие данные")
        import_layout.addWidget(self.update_existing_check)
        
        layout.addWidget(import_group)
        
        # Система координат
        crs_group = QGroupBox("Система координат")
        crs_layout = QFormLayout(crs_group)
        
        self.crs_combo = QComboBox()
        self.crs_combo.addItems([
            "Из файла",
            "МСК-33",
            "МСК-50",
            "МСК-63",
            "WGS-84",
            "ПЗ-90"
        ])
        crs_layout.addRow("СК:", self.crs_combo)
        
        layout.addWidget(crs_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_preview_tab(self) -> QWidget:
        """Создание вкладки предпросмотра"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Таблица предпросмотра
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(5)
        self.preview_table.setHorizontalHeaderLabels(["Тип", "Название", "X/От", "Y/До", "H/Значение"])
        layout.addWidget(self.preview_table)
        
        # Статистика
        stats_layout = QHBoxLayout()
        
        self.points_count_label = QLabel("Пунктов: 0")
        stats_layout.addWidget(self.points_count_label)
        
        self.observations_count_label = QLabel("Измерений: 0")
        stats_layout.addWidget(self.observations_count_label)
        
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        return widget
    
    def _browse_file(self):
        """Выбор файла для импорта"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбор файла для импорта",
            "",
            "Все поддерживаемые (*.dat *.gsi *.sdr *.pos *.csv *.txt);;"
            "DAT файлы (*.dat);;"
            "GSI файлы (*.gsi);;"
            "SDR файлы (*.sdr);;"
            "POS файлы (*.pos);;"
            "CSV файлы (*.csv);;"
            "Текстовые файлы (*.txt);;"
            "Все файлы (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self._analyze_file(file_path)
            self.import_btn.setEnabled(True)
    
    def _analyze_file(self, file_path: str):
        """Анализ файла"""
        try:
            path = Path(file_path)
            
            # Размер файла
            size = path.stat().st_size
            if size < 1024:
                size_str = f"{size} байт"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} КБ"
            else:
                size_str = f"{size / (1024 * 1024):.1f} МБ"
            
            self.file_size_label.setText(size_str)
            
            # Определение кодировки
            with open(file_path, 'rb') as f:
                raw_data = f.read(1024)
            
            try:
                raw_data.decode('utf-8')
                encoding = "UTF-8"
            except:
                encoding = "Windows-1251"
            
            self.file_encoding_label.setText(encoding)
            
            # Автоопределение формата
            ext = path.suffix.lower()
            format_map = {
                '.dat': 1,
                '.gsi': 2,
                '.sdr': 3,
                '.pos': 4,
                '.csv': 5,
                '.txt': 6
            }
            
            if ext in format_map and self.format_combo.currentIndex() == 0:
                self.format_combo.setCurrentIndex(format_map[ext])
            
        except Exception as e:
            logger.error(f"Ошибка анализа файла: {e}", exc_info=True)
    
    def _start_import(self):
        """Запуск импорта"""
        file_path = self.file_path_edit.text()
        if not file_path:
            # Показываем предупреждение в статусной строке вместо модального диалога
            self.status_label.setText("Предупреждение: Выберите файл для импорта")
            return


        
        # Определение формата
        format_index = self.format_combo.currentIndex()
        format_map = {
            0: 'auto',
            1: 'dat',
            2: 'gsi',
            3: 'sdr',
            4: 'excel',
            5: 'pos',
            6: 'csv',
            7: 'txt'
        }
        format_type = format_map.get(format_index, 'txt')

        # Автоопределение формата
        if format_type == 'auto':
            ext = Path(file_path).suffix.lower()
            if ext == '.xlsx' or ext == '.xls':
                format_type = 'excel'
            elif ext == '.gsi':
                format_type = 'gsi'
            elif ext == '.sdr':
                format_type = 'sdr'
            else:
                format_type = ext[1:] if ext else 'txt'

        # Параметры импорта
        options = {
            'import_points': self.import_points_check.isChecked(),
            'import_observations': self.import_observations_check.isChecked(),
            'skip_duplicates': self.skip_duplicates_check.isChecked(),
            'update_existing': self.update_existing_check.isChecked()
        }
        
        # Выполняем импорт синхронно в основном потоке
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.import_btn.setEnabled(False)

        # Устанавливаем путь к файлу для методов импорта
        self.file_path = file_path

        try:
            self._on_progress_updated(10, "Открытие файла...")

            if format_type == 'dat':
                result = self._import_dat()
            elif format_type == 'gsi':
                result = self._import_gsi()
            elif format_type == 'sdr':
                result = self._import_sdr()
            elif format_type == 'excel':
                result = self._import_excel()
            elif format_type == 'pos':
                result = self._import_pos()
            elif format_type == 'csv':
                result = self._import_csv()
            elif format_type == 'txt':
                result = self._import_txt()
            else:
                raise ValueError(f"Неподдерживаемый формат: {format_type}")

            self._on_progress_updated(100, "Импорт завершен")
            self._on_import_finished(result)

        except Exception as e:
            self._on_import_error(str(e))
    
    def _on_progress_updated(self, percent: int, message: str):
        """Обновление прогресса"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def _on_import_finished(self, data: Dict):
        """Завершение импорта"""
        self.imported_data = data

        # Обновление предпросмотра
        self._update_preview(data)

        # Обновление статистики
        points_count = len(data.get('points', []))
        observations_count = len(data.get('observations', []))

        self.points_count_label.setText(f"Пунктов: {points_count}")
        self.observations_count_label.setText(f"Измерений: {observations_count}")

        self.status_label.setText(f"Импорт завершен: {points_count} пунктов, {observations_count} измерений")
        self.ok_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
    
    def _on_import_error(self, error_msg: str):
        """Ошибка импорта"""
        self.status_label.setText(f"Ошибка: {error_msg}")
        self.import_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Не показываем QMessageBox, чтобы избежать конфликта event loop
        # Ошибка отображается в статусной строке


        
        QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{error_msg}")
    
    def _update_preview(self, data: Dict):
        """Обновление предпросмотра"""
        self.preview_table.setRowCount(0)
        
        # Добавление пунктов
        for point in data.get('points', [])[:50]:  # Первые 50
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)
            
            self.preview_table.setItem(row, 0, QTableWidgetItem("Пункт"))
            self.preview_table.setItem(row, 1, QTableWidgetItem(point.get('name', '')))
            self.preview_table.setItem(row, 2, QTableWidgetItem(f"{point.get('x', 0):.4f}"))
            self.preview_table.setItem(row, 3, QTableWidgetItem(f"{point.get('y', 0):.4f}"))
            self.preview_table.setItem(row, 4, QTableWidgetItem(f"{point.get('h', 0):.4f}"))
        
        # Добавление измерений
        for obs in data.get('observations', [])[:50]:  # Первые 50
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)

            # All observations are now dictionaries
            obs_type = obs.get('type', obs.get('obs_type', ''))
            from_point = obs.get('from_point', obs.get('from_point_id', ''))
            to_point = obs.get('to_point', obs.get('to_point_id', ''))
            value = obs.get('horizontal_angle', obs.get('value', 0))

            self.preview_table.setItem(row, 0, QTableWidgetItem("Измерение"))
            self.preview_table.setItem(row, 1, QTableWidgetItem(str(obs_type)))
            self.preview_table.setItem(row, 2, QTableWidgetItem(str(from_point)))
            self.preview_table.setItem(row, 3, QTableWidgetItem(str(to_point)))
            self.preview_table.setItem(row, 4, QTableWidgetItem(f"{value:.6f}"))
        
        self.preview_table.resizeColumnsToContents()

    def _import_gsi(self) -> Dict:
        """Импорт из формата GSI (Leica)"""
        from geoadjust.io.formats.gsi import GSIParser
        from pathlib import Path

        parser = GSIParser()
        data = parser.parse(Path(self.file_path))

        # Конвертация в формат, ожидаемый приложением
        points = []
        for p in data.get('points', []):
            points.append({
                'name': p.get('point_id', ''),
                'x': p.get('x', 0) or 0,
                'y': p.get('y', 0) or 0,
                'h': p.get('h', 0) or 0,
                'type': p.get('point_type', 'free')
            })

        observations = []
        for obs in data.get('observations', []):
            if hasattr(obs, 'horizontal_angle') or hasattr(obs, 'zenith_angle') or hasattr(obs, 'slope_distance'):
                observations.append(obs)
            else:
                observations.append({
                    'from_point': getattr(obs, 'from_point_id', ''),
                    'to_point': getattr(obs, 'to_point_id', ''),
                    'type': getattr(obs, 'obs_type', 'direction'),
                    'value': getattr(obs, 'value', 0),
                    'from_setup_id': getattr(obs, 'from_setup_id', ''),
                    'face_position': getattr(obs, 'face_position', None)
                })

        return {
            'points': points,
            'observations': observations,
            'metadata': {'format': 'GSI'}
        }

    def _import_sdr(self) -> Dict:
        """Импорт из формата SDR (Sokkia)"""
        from geoadjust.io.formats.sdr import SDRParser
        from pathlib import Path

        parser = SDRParser()
        data = parser.parse(Path(self.file_path))

        # Конвертация в формат, ожидаемый приложением
        points = []
        for p in data.get('points', []):
            points.append({
                'name': p.get('point_id', ''),
                'x': p.get('x', 0) or 0,
                'y': p.get('y', 0) or 0,
                'h': p.get('h', 0) or 0,
                'type': p.get('point_type', 'free')
            })

        observations = []
        for obs in data.get('observations', []):
            # Always convert to dictionary format for consistency
            obs_dict = {
                'obs_id': getattr(obs, 'obs_id', ''),
                'from_setup_id': getattr(obs, 'from_setup_id', ''),
                'from_point_id': getattr(obs, 'from_point_id', ''),
                'to_point_id': getattr(obs, 'to_point_id', ''),
                'obs_type': getattr(obs, 'obs_type', 'combined'),
                'face_position': getattr(obs, 'face_position', None),
                'horizontal_angle': getattr(obs, 'horizontal_angle', None),
                'zenith_angle': getattr(obs, 'zenith_angle', None),
                'slope_distance': getattr(obs, 'slope_distance', None),
                'raw_line': getattr(obs, 'raw_line', None)
            }
            observations.append(obs_dict)

        return {
            'points': points,
            'observations': observations,
            'station_sessions': data.get('station_sessions', []),
            'metadata': {'format': 'SDR'}
        }

    def _import_dat(self) -> Dict:
        """Импорт из формата DAT (цифровые нивелиры)"""
        from geoadjust.io.formats.dat import DATParser
        from pathlib import Path

        parser = DATParser()
        data = parser.parse(Path(self.file_path))

        # Конвертация в формат, ожидаемый приложением
        points = []
        for p in data.get('points', []):
            points.append({
                'name': p.get('point_id', ''),
                'x': p.get('x', 0) or 0,
                'y': p.get('y', 0) or 0,
                'h': p.get('h', 0) or 0,
                'type': p.get('point_type', 'free')
            })

        observations = []
        for obs in data.get('observations', []):
            observations.append({
                'from_point': getattr(obs, 'from_point_id', ''),
                'to_point': getattr(obs, 'to_point_id', ''),
                'type': getattr(obs, 'obs_type', 'direction'),
                'value': getattr(obs, 'value', 0),
                'from_setup_id': getattr(obs, 'from_setup_id', ''),
                'face_position': getattr(obs, 'face_position', None)
            })

        return {
            'points': points,
            'observations': observations,
            'metadata': {'format': 'DAT'}
        }

    def _import_excel(self) -> Dict:
        """Импорт из формата Excel (Credo DAT)"""
        print(f"DEBUG: Starting Excel import for file: {self.file_path}")

        try:
            from geoadjust.io.formats.credo_dat import CredoDATParser
            from pathlib import Path

            print("DEBUG: Creating CredoDATParser")
            parser = CredoDATParser()
            print(f"DEBUG: Parsing file {self.file_path}")

            data = parser.parse(Path(self.file_path))
            print(f"DEBUG: Parser returned: points={len(data.get('points', []))}, obs={len(data.get('observations', []))}")

            # Конвертация в формат, ожидаемый приложением
            points = []
            for p in data.get('points', []):
                points.append({
                    'name': p.get('point_id', ''),
                    'x': p.get('x', 0) or 0,
                    'y': p.get('y', 0) or 0,
                    'h': p.get('h', 0) or 0,
                    'type': p.get('point_type', 'free')
                })

            observations = []
            for obs in data.get('observations', []):
                observations.append({
                    'obs_type': obs.get('obs_type', ''),
                    'from_point': obs.get('from_point', ''),
                    'to_point': obs.get('to_point', ''),
                    'value': obs.get('value', 0),
                    'distance': obs.get('distance'),
                    'instrument_height': obs.get('instrument_height'),
                })

            result = {
                'points': points,
                'observations': observations,
                'station_sessions': data.get('station_sessions', []),
                'metadata': {'format': 'Excel', 'type': 'leveling'}
            }

            return result

        except Exception as e:
            return {
                'points': [],
                'observations': [],
                'station_sessions': [],
                'metadata': {'format': 'Excel', 'error': str(e)}
            }

    def get_imported_data(self) -> Optional[Dict]:
        """Получение импортированных данных"""
        return self.imported_data
