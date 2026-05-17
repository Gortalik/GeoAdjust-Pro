#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Таблица измерений с разделением по типам:
- Нивелирование (ходы с превышениями и боковые измерения)
- Тахеометрия (станции с горизонтальными/вертикальными углами и расстояниями)
- GNSS векторы (с СКП по средне-взвешенному)

Угловые величины отображаются в градусах, минутах и секундах.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView,
                             QAbstractItemView, QMenu, QAction, QHeaderView,
                             QPushButton, QTabWidget)
from PyQt5.QtCore import Qt, QAbstractTableModel, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from typing import List, Dict, Any, Optional, Union
import logging

from geoadjust.utils import decimal_to_dms, format_dms_compact

# Импорт визуальных делегатов
from geoadjust.gui.delegates.visual_delegates import ObservationTypeDelegate

logger = logging.getLogger(__name__)


class StationObservation:
    """Объединённое измерение на станции (все типы для одной цели)"""
    def __init__(self, station: str, target: str):
        self.station = station
        self.target = target
        self.from_setup_id = None  # ID установки станции
        self.direction = None  # горизонтальный угол
        self.zenith_angle = None  # зенитный угол
        self.slope_distance = None  # наклонное расстояние
        self.horizontal_distance = None  # горизонтальное проложение
        self.direction_value = None
        self.zenith_value = None
        self.slope_value = None
        self.horizontal_value = None
        self.is_active = True
        self.angle_unit = 'gons'
        self._original_obs = []

    def add_observation(self, obs):
        """Добавить измерение к группе"""
        self._original_obs.append(obs)

        # Устанавливаем from_setup_id из первого измерения
        if self.from_setup_id is None:
            if isinstance(obs, dict):
                self.from_setup_id = obs.get('from_setup_id')
            else:
                self.from_setup_id = getattr(obs, 'from_setup_id', None)

        obs_type = self._get_obs_type(obs)
        value = self._get_value(obs)

        if obs_type in ['direction', 'azimuth', 'horizontal_angle']:
            self.direction = obs_type
            self.direction_value = value
        elif obs_type in ['zenith_angle', 'vertical_angle']:
            self.zenith_angle = obs_type
            self.zenith_value = value
        elif obs_type in ['slope_distance', 'distance']:
            self.slope_distance = obs_type
            self.slope_value = value
        elif obs_type == 'horizontal_distance':
            self.horizontal_distance = obs_type
            self.horizontal_value = value

        if hasattr(obs, 'is_active'):
            self.is_active = self.is_active and obs.is_active
        if hasattr(obs, 'angle_unit'):
            self.angle_unit = obs.angle_unit

    def _get_obs_type(self, obs) -> str:
        """Получение типа измерения из объекта или словаря"""
        if isinstance(obs, dict):
            return obs.get('obs_type', obs.get('type', ''))
        return getattr(obs, 'obs_type', '')

    def _get_value(self, obs) -> float:
        """Получение значения измерения"""
        if isinstance(obs, dict):
            return obs.get('value', 0.0)
        return getattr(obs, 'value', 0.0)


class StationObservationTotal:
    """Объединённое измерение на станции с данными из обоих кругов"""
    def __init__(self, station: str, target: str):
        self.station = station
        self.target = target
        self.from_setup_id = None  # ID установки станции

        # Данные для левого круга
        self.left_direction = None
        self.left_zenith = None
        self.left_slope = None

        # Данные для правого круга
        self.right_direction = None
        self.right_zenith = None
        self.right_slope = None

        self.is_active = True
        self.angle_unit = 'gons'
        self._original_obs = []

    def _safe_str(self, value, fmt=".4f"):
        if value is None:
            return ""
        try:
            return f"{float(value):{fmt}}"
        except (ValueError, TypeError):
            return str(value) or ""
    
    def add_observation(self, obs):
        """Добавить измерение к группе"""
        self._original_obs.append(obs)

        # Устанавливаем from_setup_id из первого измерения
        if self.from_setup_id is None:
            if isinstance(obs, dict):
                self.from_setup_id = obs.get('from_setup_id')
            else:
                self.from_setup_id = getattr(obs, 'from_setup_id', None)

        obs_type = self._get_obs_type(obs)
        value = self._get_value(obs)

        if obs_type in ['direction', 'azimuth']:
            self.direction = obs_type
            self.direction_value = value
        elif obs_type in ['zenith_angle', 'vertical_angle']:
            self.zenith_angle = obs_type
            self.zenith_value = value
        elif obs_type == 'slope_distance':
            self.slope_distance = obs_type
            self.slope_value = value
        elif obs_type == 'horizontal_distance':
            self.horizontal_distance = obs_type
            self.horizontal_value = value

        if hasattr(obs, 'is_active'):
            self.is_active = self.is_active and obs.is_active
        if hasattr(obs, 'angle_unit'):
            self.angle_unit = obs.angle_unit


class StationObservationTotal:
    """Объединённое измерение на станции с данными из обоих кругов"""
    def __init__(self, station: str, target: str):
        self.station = station
        self.target = target
        self.from_setup_id = None  # ID установки станции

        # Данные для левого круга
        self.left_direction = None
        self.left_zenith = None
        self.left_slope = None

        # Данные для правого круга
        self.right_direction = None
        self.right_zenith = None
        self.right_slope = None

        self.is_active = True
        self.angle_unit = 'gons'
        self._original_obs = []

    def add_observation(self, obs):
        """Добавить измерение к группе с учетом круга"""
        self._original_obs.append(obs)

        # Устанавливаем from_setup_id из первого измерения
        if self.from_setup_id is None:
            if isinstance(obs, dict):
                self.from_setup_id = obs.get('from_setup_id')
            else:
                self.from_setup_id = getattr(obs, 'from_setup_id', None)

        # Определяем круг измерения
        if isinstance(obs, dict):
            face_pos = obs.get('face_position')
        else:
            face_pos = getattr(obs, 'face_position', None)

        obs_type = self._get_obs_type(obs)
        value = self._get_value(obs)

        if face_pos == 'CL':  # Левый круг
            if obs_type in ['direction', 'azimuth']:
                self.left_direction = value
            elif obs_type in ['zenith_angle', 'vertical_angle']:
                self.left_zenith = value
            elif obs_type in ['slope_distance', 'distance']:
                self.left_slope = value
        elif face_pos == 'CP':  # Правый круг
            if obs_type in ['direction', 'azimuth']:
                self.right_direction = value
            elif obs_type in ['zenith_angle', 'vertical_angle']:
                self.right_zenith = value
            elif obs_type in ['slope_distance', 'distance']:
                self.right_slope = value
        else:  # Если круг не указан, используем как есть
            if obs_type in ['direction', 'azimuth']:
                if self.left_direction is None:
                    self.left_direction = value
                else:
                    self.right_direction = value
            elif obs_type in ['zenith_angle', 'vertical_angle']:
                if self.left_zenith is None:
                    self.left_zenith = value
                else:
                    self.right_zenith = value
            elif obs_type in ['slope_distance', 'distance']:
                if self.left_slope is None:
                    self.left_slope = value
                else:
                    self.right_slope = value

        if hasattr(obs, 'is_active'):
            self.is_active = self.is_active and obs.is_active
        if hasattr(obs, 'angle_unit'):
            self.angle_unit = obs.angle_unit

    def _get_obs_type(self, obs) -> str:
        """Получение типа измерения из объекта или словаря"""
        if isinstance(obs, dict):
            return obs.get('obs_type', obs.get('type', ''))
        return getattr(obs, 'obs_type', '')

    def _get_value(self, obs) -> float:
        """Получение значения измерения"""
        if isinstance(obs, dict):
            return obs.get('value', 0.0)
        return getattr(obs, 'value', 0.0)


def _total_station_total_data(self, obs: StationObservationTotal, col):
    """Данные для сгруппированного измерения с обоими кругами"""
    if col == 0:  # №
        row = self._filtered_observations.index(obs)
        return str(row + 1)
    elif col == 1:  # Станция
        return obs.station
    elif col == 2:  # Цель
        return obs.target
    elif col == 3:  # Левый горизонтальный угол
        if obs.left_direction is not None:
            value = obs.left_direction
            if obs.angle_unit == 'gons':
                value = value * 0.9
            return format_dms_compact(value)
        return "-"
    elif col == 4:  # Левый зенитный угол
        if obs.left_zenith is not None:
            value = obs.left_zenith
            if obs.angle_unit == 'gons':
                value = value * 0.9
            return format_dms_compact(value)
        return "-"
    elif col == 5:  # Левое наклонное расстояние
        if obs.left_slope is not None:
            return self._safe_str(getattr(obs, 'left_slope', None), ".4f")
        return "-"
    elif col == 6:  # Правый горизонтальный угол
        if obs.right_direction is not None:
            value = obs.right_direction
            if obs.angle_unit == 'gons':
                value = value * 0.9
            return format_dms_compact(value)
        return "-"
    elif col == 7:  # Правый зенитный угол
        if obs.right_zenith is not None:
            value = obs.right_zenith
            if obs.angle_unit == 'gons':
                value = value * 0.9
            return format_dms_compact(value)
        return "-"
    elif col == 8:  # Правое наклонное расстояние
        if obs.right_slope is not None:
            return self._safe_str(getattr(obs, 'right_slope', None), ".4f")
        return "-"
    elif col == 9:  # Статус
        return "✓" if obs.is_active else "✗"


class ObservationsTableModel(QAbstractTableModel):
    """Модель таблицы измерений с разделением по типам"""
    
    # Типы измерений для каждой вкладки
    LEVELING_TYPES = ['height_diff', 'backsight', 'foresight', 'intermediate', 'leveling_height_diff']
    LEVELING_INTERMEDIATE_TYPES = ['intermediate_leveling']
    TOTAL_STATION_TYPES = ['direction', 'zenith_angle', 'vertical_angle', 'distance',
                          'slope_distance', 'horizontal_distance', 'combined']
    GNSS_TYPES = ['gnss_vector']
    
    HEADERS = {
        'leveling': ['№', 'Тип', 'От пункта', 'К пункту', 'Превышение (м)',
                      'Расстояние (м)', 'Высота инструмента (м)', 'Высота цели (м)', 'Статус'],
        'total_station': ['№', 'Станция', 'Цель', 'Круг', 'Гор. угол', 'Зен. угол',
                         'Накл. расст.', 'Гор. расст.', 'Статус'],
        'gnss': ['№', 'От станции', 'К станции', 'dX (м)', 'dY (м)', 'dZ (м)',
                 'σdX (мм)', 'σdY (мм)', 'σdZ (мм)', 'Качество', 'Спутников']
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._observations: List[Any] = []
        self._filtered_observations: List[Any] = []
        self._original_filtered_observations: List[Any] = []
        self._current_tab = 'total_station'  # По умолчанию тахеометрия
        self._station_filter: Optional[str] = None  # ID сессии станции для фильтрации
    
    def set_observations(self, observations: List[Any]):
        """Установка списка измерений"""
        logger.info(f"ObservationsTableView.set_observations: setting {len(observations)} observations")
        self._station_filter = None  # Сбрасываем фильтр по станции при новом импорте
        self.beginResetModel()
        self._observations = observations
        self._filter_observations()
        logger.info(f"ObservationsTableView: filtered to {len(self._filtered_observations)} for tab {self._current_tab}")
        self.endResetModel()
    
    def set_tab(self, tab: str):
        """Переключение вкладки"""
        self._current_tab = tab
        if hasattr(self, '_observations') and self._observations:
            self.beginResetModel()
            self._filter_observations()
            self.endResetModel()

        # Обновление интерфейса убрано, чтобы избежать бесконечного цикла
        # Qt автоматически обновит интерфейс при изменении модели

    def set_station_filter(self, station_filter: Optional[str]):
        """Установка фильтра по станции"""
        self._station_filter = station_filter
        # Не вызываем beginResetModel/endResetModel здесь, поскольку это делается в filter_by_station_session

    def _filter_observations(self):
        """Фильтрация измерений по текущей вкладке и станции"""
        # Сначала фильтруем по типу измерений
        if self._current_tab == 'leveling':
            filtered = [
                obs for obs in self._observations
                if self._get_obs_type(obs) in self.LEVELING_TYPES
            ]
        elif self._current_tab == 'leveling_intermediate':
            filtered = [
                obs for obs in self._observations
                if self._get_obs_type(obs) in self.LEVELING_INTERMEDIATE_TYPES
            ]
        elif self._current_tab == 'total_station':
            filtered = [
                obs for obs in self._observations
                if self._get_obs_type(obs) in self.TOTAL_STATION_TYPES
            ]
        elif self._current_tab == 'gnss':
            filtered = [
                obs for obs in self._observations
                if self._get_obs_type(obs) in self.GNSS_TYPES
            ]
        else:
            filtered = self._observations



        # Затем применяем фильтр по станции, если он установлен
        if self._station_filter:
            # Фильтруем по станции - показываем только измерения выбранной станции
            filtered_results = []
            for obs in filtered:
                from geoadjust.core.network.models import CombinedObservation
                from geoadjust.io.formats.gsi import GSIObservation
                if isinstance(obs, CombinedObservation):
                    # Для SDR данных from_setup_id содержит ID станции типа "STATION_SETUP_001"
                    obs_station = obs.from_setup_id
                    # Извлекаем имя станции из setup_id (до "_SETUP_")
                    if "_SETUP_" in obs_station:
                        obs_station = obs_station.split("_SETUP_")[0]
                elif isinstance(obs, GSIObservation):
                    obs_station = obs.station_session_id
                elif isinstance(obs, dict):
                    obs_station = obs.get('from_setup_id', obs.get('station_session_id', ''))
                    # Извлекаем имя станции из setup_id
                    if "_SETUP_" in obs_station:
                        obs_station = obs_station.split("_SETUP_")[0]
                else:
                    obs_station = getattr(obs, 'from_setup_id', getattr(obs, 'station_session_id', ''))

                print(f"FILTER: checking obs_station={obs_station} vs filter={self._station_filter}")
                if obs_station == self._station_filter:
                    filtered_results.append(obs)

            filtered = filtered_results
            print(f"FILTER: after station filter, {len(filtered_results)} observations")

        # Для тахеометрии показываем каждую SDR строку как отдельную запись в хронологическом порядке
        if self._current_tab == 'total_station':
            self._filtered_observations = filtered  # Сохраняем порядок из файла
        else:
            self._filtered_observations = filtered

        print(f"FILTER: final result, {len(self._filtered_observations)} observations in filtered")

        # Сохраняем оригинальный порядок для сброса сортировки
        self._original_filtered_observations = self._filtered_observations.copy()

    def _group_by_station_target(self, observations: List[Any]) -> List[StationObservation]:
        """Группировка измерений по станции и цели"""
        groups: Dict[str, StationObservation] = {}

        for obs in observations:
            station = self._get_from_point(obs)
            target = self._get_to_point(obs)
            key = f"{station}|{target}"

            if key not in groups:
                groups[key] = StationObservation(station, target)
            groups[key].add_observation(obs)

        return list(groups.values())

    def _group_by_station_target_total(self, observations: List[Any]) -> List[StationObservation]:
        """Группировка измерений по станции и цели для тахеометрии с учетом кругов"""
        groups: Dict[str, StationObservation] = {}

        for obs in observations:
            station = self._get_from_point(obs)
            target = self._get_to_point(obs)
            key = f"{station}|{target}"

            if key not in groups:
                groups[key] = StationObservationTotal(station, target)
            groups[key].add_observation(obs)

        return list(groups.values())

    def _sort_total_station_observations(self, observations: List[Any]) -> List[Any]:
        """Сортировка измерений тахеометрии для аккуратного отображения"""
        def sort_key(obs):
            station = self._get_from_point(obs)
            target = self._get_to_point(obs)
            obs_type = self._get_obs_type(obs)

            # Получаем круг измерения
            if isinstance(obs, dict):
                face_pos = obs.get('face_position')
            else:
                face_pos = getattr(obs, 'face_position', None)

            # Приоритет типов измерений
            type_priority = {
                'direction': 1,
                'azimuth': 1,
                'zenith_angle': 2,
                'vertical_angle': 2,
                'slope_distance': 3,
                'distance': 3,
                'horizontal_distance': 4
            }.get(obs_type, 5)

            # Приоритет кругов
            circle_priority = {
                'CL': 1,  # Левый круг первый
                'CP': 2,  # Правый круг второй
                None: 3   # Без круга последним
            }.get(face_pos, 3)

            return (station, target, type_priority, circle_priority)

        return sorted(observations, key=sort_key)

    def _sort_combined_observations(self, observations: List[Any]) -> List[Any]:
        """Сортировка объединенных измерений тахеометрии"""
        from geoadjust.core.network.models import CombinedObservation

        def sort_key(obs):
            if isinstance(obs, CombinedObservation):
                station = obs.from_point_id
                target = obs.to_point_id
                face_pos = obs.face_position
            else:
                station = self._get_from_point(obs)
                target = self._get_to_point(obs)
                if isinstance(obs, dict):
                    face_pos = obs.get('face_position')
                else:
                    face_pos = getattr(obs, 'face_position', None)

            # Приоритет кругов
            circle_priority = {
                'CL': 1,  # Левый круг первый
                'CP': 2,  # Правый круг второй
                None: 3   # Без круга последним
            }.get(face_pos, 3)

            return (station, target, circle_priority)

        return sorted(observations, key=sort_key)

    def _get_obs_type(self, obs) -> str:
        """Получение типа измерения"""
        from geoadjust.core.network.models import CombinedObservation
        if isinstance(obs, CombinedObservation):
            return 'combined'
        if isinstance(obs, dict):
            tacheo_fields = [
                'horizontal_angle', 'zenith_angle', 'slope_distance',
                'hz_angle', 'v_angle', 'distance', 'horizontal_distance',
                'direction', 'vertical_angle'
            ]
            if any(field in obs for field in tacheo_fields):
                return 'combined'
            return obs.get('type', obs.get('obs_type', ''))
        return getattr(obs, 'obs_type', '')
        obs_type = getattr(obs, 'obs_type', '')
        print(f"GET_TYPE: object -> '{obs_type}'")
        return obs_type
    
    def _get_from_point(self, obs) -> str:
        """Получение начальной точки"""
        from geoadjust.core.network.models import CombinedObservation

        if isinstance(obs, CombinedObservation):
            return obs.from_point_id
        elif isinstance(obs, dict):
            return obs.get('from_point', obs.get('from_point_id', ''))
        return getattr(obs, 'from_point', getattr(obs, 'from_point_id', ''))

    def _get_to_point(self, obs) -> str:
        """Получение конечной точки"""
        from geoadjust.core.network.models import CombinedObservation

        if isinstance(obs, CombinedObservation):
            return obs.to_point_id
        elif isinstance(obs, dict):
            return obs.get('to_point', obs.get('to_point_id', ''))
        return getattr(obs, 'to_point', getattr(obs, 'to_point_id', ''))
    
    def _get_value(self, obs) -> float:
        """Получение значения измерения"""
        if isinstance(obs, dict):
            return obs.get('value', 0)
        return getattr(obs, 'value', 0)
    
    def rowCount(self, parent=None):
        return len(self._filtered_observations)
    
    def columnCount(self, parent=None):
        return len(self.HEADERS.get(self._current_tab, []))
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            headers = self.HEADERS.get(self._current_tab, [])
            if section < len(headers):
                return headers[section]
        return None
    
    def _get_obs_type(self, obs):
        if isinstance(obs, dict):
            return obs.get('type', obs.get('obs_type', 'unknown'))
        return getattr(obs, 'type', getattr(obs, 'obs_type', 'unknown'))

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        
        row = index.row()
        col = index.column()
        
        if row >= len(self._filtered_observations):
            return None
        
        obs = self._filtered_observations[row]
        
        if self._current_tab == 'leveling':
            return self._leveling_data(obs, col)
        elif self._current_tab == 'total_station':
            return self._total_station_data(obs, col)
        elif self._current_tab == 'gnss':
            return self._gnss_data(obs, col)
        
        return None
    
    def _leveling_data(self, obs, col):
        """Данные для вкладки нивелирования"""
        obs_type = self._get_obs_type(obs)
        row = self._filtered_observations.index(obs)
        
        if col == 0:  # №
            return str(row + 1)
        elif col == 1:  # Тип
            type_names = {
                'height_diff': 'Превышение',
                'leveling_height_diff': 'Превышение нивелирное',
                'intermediate_leveling': 'Боковое нивелирование',
                'backsight': 'Задняя рейка',
                'foresight': 'Передняя рейка',
                'intermediate': 'Промежуточная'
            }
            return type_names.get(obs_type, obs_type)
        elif col == 2:  # От пункта
            return self._get_from_point(obs)
        elif col == 3:  # К пункту
            return self._get_to_point(obs)
        elif col == 4:  # Превышение
            value = self._get_value(obs)
            return self._safe_str(value, ".5f")
        elif col == 5:  # Расстояние
            dist = obs.get('distance') if isinstance(obs, dict) else getattr(obs, 'distance', None)
            if dist is not None:
                return f"{dist:.3f}"
            return "-"
        elif col == 6:  # Высота инструмента
            ih = obs.get('instrument_height') if isinstance(obs, dict) else getattr(obs, 'instrument_height', None)
            if ih is not None:
                return f"{ih:.4f}"
            return "-"
        elif col == 7:  # Высота цели
            th = obs.get('target_height') if isinstance(obs, dict) else getattr(obs, 'target_height', None)
            if th is not None:
                return f"{th:.4f}"
            return "-"
        elif col == 8:  # Статус
            is_active = obs.get('is_active', True) if isinstance(obs, dict) else getattr(obs, 'is_active', True)
            return "Активно" if is_active else "Исключено"
        return None
    
    def _total_station_data(self, obs, col):
        """Данные для вкладки тахеометрии"""
        from geoadjust.core.network.models import CombinedObservation

        is_grouped = isinstance(obs, StationObservation)
        is_combined = isinstance(obs, CombinedObservation)

        # Также считать CombinedObservation dicts как combined
        if not is_combined and isinstance(obs, dict):
            if 'horizontal_angle' in obs or 'zenith_angle' in obs or 'slope_distance' in obs:
                is_combined = True



        if is_grouped:
            return self._total_station_grouped_data(obs, col)
        elif is_combined:
            return self._total_station_combined_data(obs, col)

        # Обработка отдельных измерений (dict)
        row = self._filtered_observations.index(obs)
        return f"Row {row + 1}"
    
    def _total_station_grouped_data(self, obs: StationObservation, col):
        """Данные для сгруппированных измерений (станция + цель)"""
        row = self._filtered_observations.index(obs)

        if col == 0:  # №
            return str(row + 1)
        elif col == 1:  # Станция
            return obs.station
        elif col == 2:  # Цель
            return obs.target
        elif col == 3:  # Круг
            return "-"  # Пока не используется
        elif col == 4:  # Horizontal angle (degrees)
            if obs.direction_value is not None:
                return format_dms_compact(obs.direction_value)
            return "-"
        elif col == 5:  # Zenith angle (degrees)
            if obs.zenith_value is not None:
                return format_dms_compact(obs.zenith_value)
            return "-"
        elif col == 6:  # Наклонное расстояние
            if obs.slope_value is not None:
                return f"{obs.slope_value:.4f}"
            return "-"
        elif col == 7:  # Горизонтальное расстояние (расчетное)
            # Можно рассчитать, но пока оставим пустым
            return "-"
        elif col == 8:  # Статус
            return "✓" if obs.is_active else "✗"
        return None
    
    def _gnss_data(self, obs, col):
        """Данные для вкладки GNSS векторов"""
        row = self._filtered_observations.index(obs)
        
        if col == 0:  # №
            return str(row + 1)
        elif col == 1:  # От станции
            return self._get_from_point(obs)
        elif col == 2:  # К станции
            return self._get_to_point(obs)
        elif col == 3:  # dX
            dx = obs.get('delta_x') if isinstance(obs, dict) else getattr(obs, 'delta_x', None)
            if dx is not None:
                return f"{dx:.4f}"
            return "-"
        elif col == 4:  # dY
            dy = obs.get('delta_y') if isinstance(obs, dict) else getattr(obs, 'delta_y', None)
            if dy is not None:
                return f"{dy:.4f}"
            return "-"
        elif col == 5:  # dZ
            dz = obs.get('delta_z') if isinstance(obs, dict) else getattr(obs, 'delta_z', None)
            if dz is not None:
                return f"{dz:.4f}"
            return "-"
        elif col == 6:  # σdX
            sx = obs.get('sigma_x') if isinstance(obs, dict) else getattr(obs, 'sigma_x', None)
            if sx is not None:
                return f"{sx * 1000:.2f}"
            return "-"
        elif col == 7:  # σdY
            sy = obs.get('sigma_y') if isinstance(obs, dict) else getattr(obs, 'sigma_y', None)
            if sy is not None:
                return f"{sy * 1000:.2f}"
            return "-"
        elif col == 8:  # σdZ
            sz = obs.get('sigma_z') if isinstance(obs, dict) else getattr(obs, 'sigma_z', None)
            if sz is not None:
                return f"{sz * 1000:.2f}"
            return "-"
        elif col == 9:  # Качество
            quality_map = {1: 'Fix', 2: 'Float', 3: 'SBAS', 4: 'DGPS', 5: 'Single'}
            q = obs.get('quality') if isinstance(obs, dict) else getattr(obs, 'quality', None)
            return quality_map.get(q, str(q) if q else "-")
        elif col == 10:  # Спутников
            ns = obs.get('n_satellites') if isinstance(obs, dict) else getattr(obs, 'n_satellites', None)
            return str(ns) if ns is not None else "-"
        return None

    def _total_station_combined_data(self, obs, col):
        """Данные для объединенного измерения SDR строки"""
        from geoadjust.core.network.models import CombinedObservation



        if col == 0:  # №
            row = self._filtered_observations.index(obs)
            return str(row + 1)
        elif col == 1:  # Станция
            if isinstance(obs, CombinedObservation):
                return obs.from_point_id
            else:  # dict
                return obs.get('from_point_id', '')
        elif col == 2:  # Цель
            if isinstance(obs, CombinedObservation):
                return obs.to_point_id
            else:  # dict
                return obs.get('to_point_id', '')
        elif col == 3:  # Круг
            face_pos = obs.face_position if isinstance(obs, CombinedObservation) else obs.get('face_position')
            if face_pos == 'CL':
                return 'Левый'
            elif face_pos == 'CP':
                return 'Правый'
            else:
                return '-'
        elif col == 4:  # Горизонтальный угол
            horiz_angle = obs.horizontal_angle if isinstance(obs, CombinedObservation) else obs.get('horizontal_angle')
            if horiz_angle is not None:
                # SDR углы обычно в градах (гон), конвертируем в градусы
                value = horiz_angle
                if value > 100:  # Вероятно в градах
                    value = value * 0.9  # Конвертация из гонов в градусы
                return format_dms_compact(value)
            return "-"
        elif col == 5:  # Зенитный угол
            zenith_angle = obs.zenith_angle if isinstance(obs, CombinedObservation) else obs.get('zenith_angle')
            if zenith_angle is not None:
                value = zenith_angle
                if value > 100:  # Вероятно в градах
                    value = value * 0.9  # Конвертация из гонов в градусы
                return format_dms_compact(value)
            return "-"
        elif col == 6:  # Наклонное расстояние
            slope_dist = obs.slope_distance if isinstance(obs, CombinedObservation) else obs.get('slope_distance')
            if slope_dist is not None:
                return f"{slope_dist:.4f}"
            return "-"
        elif col == 7:  # Горизонтальное расстояние (расчетное)
            # Можно рассчитать, но пока оставим пустым
            return "-"
        elif col == 8:  # Статус
            return "✓"
        return "-"

    def get_observation(self, row: int) -> Optional[Any]:
        """Получение измерения по строке"""
        if 0 <= row < len(self._filtered_observations):
            return self._filtered_observations[row]
        return None
    
    def update_observation(self, row: int, obs: Any):
        """Обновление измерения"""
        if 0 <= row < len(self._filtered_observations):
            self._filtered_observations[row] = obs
            self.dataChanged.emit(self.index(row, 0),
                                  self.index(row, self.columnCount() - 1))

    def sort(self, column: int, order=Qt.AscendingOrder):
        """Сортировка модели по столбцу"""
        if column == -1:
            # Сброс сортировки - восстанавливаем оригинальный порядок
            self._filtered_observations = self._original_filtered_observations.copy()
            self.beginResetModel()
            self.endResetModel()
            return

        if column < 0 or column >= self.columnCount():
            return

        reverse = (order == Qt.DescendingOrder)

        # Получаем значения для сортировки заранее, чтобы избежать рекурсии
        values = []
        for row, obs in enumerate(self._filtered_observations):
            value = self.data(self.index(row, column), Qt.DisplayRole)
            if value is None:
                value = ""
            values.append((str(value), obs))

        values.sort(key=lambda x: x[0], reverse=reverse)
        self._filtered_observations = [obs for _, obs in values]

        self.beginResetModel()
        self.endResetModel()

    def _reset_sorting(self):
        """Сброс сортировки к оригинальному порядку"""
        self.sort(-1)


class ObservationsTableView(QTableView):
    """Таблица измерений с вкладками по типам"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.model = ObservationsTableModel(self)
        self.setModel(self.model)
        
        # Настройка отображения
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)
        
        # Настройка заголовков
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_context_menu)

        # Настройка делегатов для визуальных индикаторов
        self._setup_delegates()

        # Контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_delegates(self):
        """Настройка делегатов для визуальных индикаторов"""
        # Для нивелирования - колонка "Тип" (индекс 1)
        if self.model._current_tab == 'leveling':
            self.setItemDelegateForColumn(1, ObservationTypeDelegate(self))
        # Для тахеометрии делегаты настраиваются динамически
        elif self.model._current_tab == 'total_station':
            # Создаем специальный делегат для комбинированных измерений
            pass  # Будет реализовано отдельно
    
    def set_observations(self, observations: List[Any]):
        """Установка списка измерений"""
        self.model.set_observations(observations)
    
    def set_tab(self, tab: str):
        """Переключение вкладки"""
        self.model.set_tab(tab)
    
    def _show_context_menu(self, position):
        """Показ контекстного меню"""
        menu = QMenu(self)
        
        exclude_action = menu.addAction("Исключить измерение")
        include_action = menu.addAction("Включить измерение")
        menu.addSeparator()
        show_all_action = menu.addAction("Показать все измерения")
        
        action = menu.exec_(self.mapToGlobal(position))
        
        if action == exclude_action:
            self._exclude_selected()
        elif action == include_action:
            self._include_selected()
        elif action == show_all_action:
            self.set_tab('total_station')  # По умолчанию
    
    def _exclude_selected(self):
        """Исключение выбранных измерений"""
        for index in self.selectedIndexes():
            if index.column() == 0:
                obs = self.model.get_observation(index.row())
                if obs:
                    obs.is_active = False
        self.model.set_observations(self.model._observations)
    
    def _include_selected(self):
        """Включение выбранных измерений"""
        for index in self.selectedIndexes():
            if index.column() == 0:
                obs = self.model.get_observation(index.row())
                if obs:
                    obs.is_active = True
        self.model.set_observations(self.model._observations)

    def _show_header_context_menu(self, position):
        """Контекстное меню для заголовка таблицы"""
        menu = QMenu(self)

        reset_sort_action = QAction("Сбросить сортировку", self)
        reset_sort_action.triggered.connect(self.model._reset_sorting)

        menu.addAction(reset_sort_action)
        menu.exec_(self.horizontalHeader().mapToGlobal(position))

    def _reset_sorting(self):
        """Сброс сортировки таблицы"""
        self.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)


class ObservationsTableWidget(QWidget):
    """Виджет таблицы измерений с кнопками управления и вкладками по типам"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    def _get_obs_type(self, obs):
        if isinstance(obs, dict):
            return obs.get('type', obs.get('obs_type', 'unknown'))
        return getattr(obs, 'type', getattr(obs, 'obs_type', 'unknown'))
        
        # Вкладки по типам измерений
        from PyQt5.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        
        self.leveling_model = ObservationsTableModel()
        self.leveling_view = QTableView()
        self.leveling_view.setModel(self.leveling_model)
        self.leveling_view.setSortingEnabled(True)
        self.leveling_view.horizontalHeader().setSortIndicatorShown(True)

        self.leveling_intermediate_model = ObservationsTableModel()
        self.leveling_intermediate_view = QTableView()
        self.leveling_intermediate_view.setModel(self.leveling_intermediate_model)
        self.leveling_intermediate_view.setSortingEnabled(True)
        self.leveling_intermediate_view.horizontalHeader().setSortIndicatorShown(True)

        self.total_station_model = ObservationsTableModel()
        self.total_station_view = QTableView()
        self.total_station_view.setModel(self.total_station_model)
        self.total_station_view.setSortingEnabled(True)
        self.total_station_view.horizontalHeader().setSortIndicatorShown(True)

        self.gnss_model = ObservationsTableModel()
        self.gnss_view = QTableView()
        self.gnss_view.setModel(self.gnss_model)
        self.gnss_view.setSortingEnabled(True)
        self.gnss_view.horizontalHeader().setSortIndicatorShown(True)

        self.tabs.addTab(self.leveling_view, "Нивелирование")
        self.tabs.addTab(self.leveling_intermediate_view, "Боковое нивелирование")
        self.tabs.addTab(self.total_station_view, "Тахеометрия")
        self.tabs.addTab(self.gnss_view, "GNSS")
        
        layout.addWidget(self.tabs)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Добавить")
        self.exclude_btn = QPushButton("Исключить")
        self.include_btn = QPushButton("Включить")
        self.delete_btn = QPushButton("Удалить")
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.exclude_btn)
        btn_layout.addWidget(self.include_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Подключение сигналов переключения вкладок
        self.tabs.currentChanged.connect(self._on_tab_changed)
    
    def _on_tab_changed(self, index):
        """Обработка переключения вкладки"""
        tab_names = ['leveling', 'leveling_intermediate', 'total_station', 'gnss']
        if index < len(tab_names):
            model = [self.leveling_model, self.leveling_intermediate_model, self.total_station_model, self.gnss_model][index]
            model.set_tab(tab_names[index])
    
    def set_observations(self, observations):
        """Установка списка измерений"""
        logger.info(f"ObservationsTable.set_observations: setting {len(observations)} observations")
        print(f"SET_OBS: total observations = {len(observations)}")
        if observations:
            sample = observations[0]
            print(f"SET_OBS: sample type = {type(sample)}")
            if isinstance(sample, dict):
                print(f"SET_OBS: sample keys = {list(sample.keys())}")
                obs_type = self._get_obs_type(sample)
                print(f"SET_OBS: sample obs_type = {obs_type}")

        # Сначала устанавливаем вкладки
        self.leveling_model.set_tab('leveling')
        self.leveling_intermediate_model.set_tab('leveling_intermediate')
        self.total_station_model.set_tab('total_station')
        self.gnss_model.set_tab('gnss')

        # Затем передаём данные (фильтрация сработает правильно)
        self.leveling_model.set_observations(observations)
        self.leveling_intermediate_model.set_observations(observations)
        self.total_station_model.set_observations(observations)
        self.gnss_model.set_observations(observations)
    
    def update_data(self, observations):
        """Обновление данных (алиас для set_observations)"""
        self.set_observations(observations)

    def filter_by_station_session(self, session_id: Optional[str] = None):
        """Фильтрация измерений по сессии станции

        Args:
            session_id: ID сессии станции. Если None - показать все измерения.
        """
        # Устанавливаем фильтр по станции для каждой модели
        self.leveling_model.set_station_filter(session_id)
        self.leveling_intermediate_model.set_station_filter(session_id)
        self.total_station_model.set_station_filter(session_id)
        self.gnss_model.set_station_filter(session_id)

        # Перефильтровываем данные с правильным обновлением модели
        self._refilter_table(self.leveling_model)
        self._refilter_table(self.total_station_model)
        self._refilter_table(self.gnss_model)

    def _refilter_table(self, model):
        """Перефильтрация данных в модели с правильным обновлением"""
        model.beginResetModel()
        model._filter_observations()
        model.endResetModel()

    def model(self):
        """Возврат модели текущей вкладки"""
        current_table = self.tabs.currentWidget()
        if hasattr(current_table, 'model'):
            return current_table.model()
        return None
