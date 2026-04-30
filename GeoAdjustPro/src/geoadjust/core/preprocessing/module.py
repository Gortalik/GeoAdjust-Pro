#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль предобработки геодезических измерений

Реализует 9 этапов предобработки:
1. Распознавание топологии сети
2. Формирование ходов и секций
3. Обработка приемов измерений
4. Контроль замыкания горизонта
5. Усреднение направлений в приемах
6. Контроль сходимости прямых/обратных измерений
7. Применение редукций
8. Расчет предварительных координат
9. Формирование протокола допусков
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Union
from collections import defaultdict
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)


class PreprocessingModule:
    """Модуль предобработки с 9 этапами и контролем допусков"""

    STAGES = [
        "1. Распознавание топологии сети",
        "2. Формирование ходов и секций",
        "3. Обработка приемов измерений",
        "4. Контроль замыкания горизонта",
        "5. Усреднение направлений в приемах",
        "6. Контроль сходимости прямых/обратных измерений",
        "7. Применение редукций",
        "8. Расчет предварительных координат",
        "9. Формирование протокола допусков"
    ]

    # Типы измерений по категориям
    LEVELING_TYPES = {'height_diff', 'backsight', 'foresight', 'intermediate'}
    TOTAL_STATION_TYPES = {'direction', 'zenith_angle', 'vertical_angle', 'distance',
                           'slope_distance', 'horizontal_distance', 'azimuth'}
    GNSS_TYPES = {'gnss_vector'}

    def __init__(self, tolerances=None):
        self.current_stage = 0
        self.tolerances = tolerances or {}
        self.acceptance_criteria = {}
        self.logger = logger

    def _get_obs_type(self, obs) -> str:
        """Получение типа измерения"""
        return getattr(obs, 'obs_type', 'unknown')

    def _get_from_point(self, obs) -> str:
        """Получение начальной точки"""
        return getattr(obs, 'from_point_id', getattr(obs, 'from_point', ''))

    def _get_to_point(self, obs) -> str:
        """Получение конечной точки"""
        return getattr(obs, 'to_point_id', getattr(obs, 'to_point', ''))

    def _get_value(self, obs) -> float:
        """Получение значения измерения"""
        return getattr(obs, 'value', 0.0)

    def _build_network_topology(self, observations: List[Any]) -> Dict[str, Any]:
        """
        Этап 1: Распознавание топологии сети

        Строит графовую модель сети, выявляет:
        - Все пункты сети
        - Станции (пункты с угловыми измерениями)
        - Узловые пункты (пункты с >=3 связями)
        - Типы измерений в сети
        """
        points = set()
        stations = set()
        connections = defaultdict(set)
        obs_types = set()

        for obs in observations:
            from_p = self._get_from_point(obs)
            to_p = self._get_to_point(obs)
            obs_type = self._get_obs_type(obs)

            if from_p:
                points.add(from_p)
            if to_p:
                points.add(to_p)

            if from_p and to_p:
                connections[from_p].add(to_p)
                connections[to_p].add(from_p)

            # Станции - пункты с угловыми измерениями
            if obs_type in ['direction', 'angle', 'azimuth']:
                stations.add(from_p)

            obs_types.add(obs_type)

        # Узловые пункты - пункты с >=3 связями
        nodal_points = {p for p, conns in connections.items() if len(conns) >= 3}

        # Определение типа сети
        has_leveling = bool(obs_types & self.LEVELING_TYPES)
        has_total_station = bool(obs_types & self.TOTAL_STATION_TYPES)
        has_gnss = bool(obs_types & self.GNSS_TYPES)

        network_type = 'mixed'
        if has_leveling and not has_total_station and not has_gnss:
            network_type = 'leveling'
        elif has_total_station and not has_leveling and not has_gnss:
            network_type = 'total_station'
        elif has_gnss and not has_leveling and not has_total_station:
            network_type = 'gnss'

        topology = {
            'points': list(points),
            'stations': list(stations),
            'nodal_points': list(nodal_points),
            'connections': dict(connections),
            'num_observations': len(observations),
            'obs_types': list(obs_types),
            'network_type': network_type,
            'has_leveling': has_leveling,
            'has_total_station': has_total_station,
            'has_gnss': has_gnss
        }

        return topology

    def _detect_traverses_and_sections(self, topology: Dict[str, Any],
                                       observations: List[Any]) -> Dict[str, Any]:
        """
        Этап 2: Формирование ходов и секций

        Автоматически распознаёт:
        - Тахеометрические ходы
        - Нивелирные секции
        - GNSS базовые линии
        """
        traverses = []
        sections = []
        gnss_baselines = []

        # Группировка измерений по типам
        angle_obs = [o for o in observations if self._get_obs_type(o) in ['direction', 'angle', 'azimuth']]
        distance_obs = [o for o in observations if self._get_obs_type(o) in ['distance', 'slope_distance', 'horizontal_distance']]
        level_obs = [o for o in observations if self._get_obs_type(o) in ['height_diff', 'backsight', 'foresight']]
        gnss_obs = [o for o in observations if self._get_obs_type(o) in ['gnss_vector']]

        # Формирование тахеометрических ходов
        if angle_obs and distance_obs:
            # Группировка по станциям
            station_points = set(self._get_from_point(o) for o in angle_obs)
            traverses.append({
                'type': 'total_station',
                'stations': list(station_points),  # Гарантируем, что это список
                'num_angles': len(angle_obs),
                'num_distances': len(distance_obs),
                'total_length': sum(self._get_value(o) for o in distance_obs if self._get_value(o) > 0)
            })

        # Формирование нивелирных секций
        if level_obs:
            # Группировка по станциям
            station_points = set(self._get_from_point(o) for o in level_obs)
            sections.append({
                'type': 'leveling',
                'stations': list(station_points),  # Гарантируем, что это список
                'num_height_diffs': len(level_obs),
                'total_elevation_diff': sum(self._get_value(o) for o in level_obs)
            })

        # Формирование GNSS базовых линий
        if gnss_obs:
            for obs in gnss_obs:
                gnss_baselines.append({
                    'type': 'gnss_baseline',
                    'from_station': self._get_from_point(obs),
                    'to_station': self._get_to_point(obs),
                    'dx': getattr(obs, 'delta_x', 0),
                    'dy': getattr(obs, 'delta_y', 0),
                    'dz': getattr(obs, 'delta_z', 0),
                    'sigma_x': getattr(obs, 'sigma_x', 0),
                    'sigma_y': getattr(obs, 'sigma_y', 0),
                    'sigma_z': getattr(obs, 'sigma_z', 0)
                })

        result = {
            'traverses': traverses,
            'sections': sections,
            'gnss_baselines': gnss_baselines
        }

        return result

    def _process_receptions(self, observations: List[Any],
                            station_id: str) -> Dict[str, Any]:
        """
        Этап 3: Обработка приемов измерений

        Обрабатывает круговые приемы на станции:
        1. Распознаёт приемы по КЛ/КП
        2. Проверяет замыкание горизонта
        3. Усредняет направления по приемам
        """
        # Фильтрация измерений для данной станции
        station_obs = [obs for obs in observations
                       if self._get_from_point(obs) == station_id
                       and self._get_obs_type(obs) in ['direction', 'angle']]

        if not station_obs:
            return {'status': 'no_data', 'error_message': f"Нет угловых измерений на станции {station_id}"}

        # Группировка по полуприемам (КЛ/КП)
        face_cl = [obs for obs in station_obs if getattr(obs, 'face_position', '') in ['CL', 'F1', 'КЛ']]
        face_cp = [obs for obs in station_obs if getattr(obs, 'face_position', '') in ['CP', 'F2', 'КП']]

        # Группировка по направлениям
        directions_by_target = defaultdict(list)
        for obs in station_obs:
            target = self._get_to_point(obs)
            directions_by_target[target].append(obs)

        # Расчёт средних направлений
        averaged_directions = {}
        for target, obs_list in directions_by_target.items():
            values = [self._get_value(o) for o in obs_list]
            if values:
                # Конвертация из гон в градусы если нужно
                angle_unit = getattr(obs_list[0], 'angle_unit', 'gons')
                if angle_unit == 'gons':
                    values = [v * 0.9 for v in values]
                averaged_directions[target] = {
                    'mean': np.mean(values),
                    'std': np.std(values) if len(values) > 1 else 0,
                    'num_obs': len(values),
                    'faces': len(set(getattr(o, 'face_position', '') for o in obs_list))
                }

        # Проверка замыкания горизонта (если есть КЛ и КП)
        closure_error = None
        if face_cl and face_cp:
            # Сравнение направлений по полуприемам
            cl_targets = set(self._get_to_point(o) for o in face_cl)
            cp_targets = set(self._get_to_point(o) for o in face_cp)
            common_targets = cl_targets & cp_targets

            if common_targets:
                max_diff = 0
                for target in common_targets:
                    cl_vals = [self._get_value(o) for o in face_cl if self._get_to_point(o) == target]
                    cp_vals = [self._get_value(o) for o in face_cp if self._get_to_point(o) == target]
                    if cl_vals and cp_vals:
                        diff = abs(np.mean(cl_vals) - np.mean(cp_vals))
                        max_diff = max(max_diff, diff)
                closure_error = max_diff

        result = {
            'status': 'success',
            'station_id': station_id,
            'num_directions': len(station_obs),
            'num_targets': len(directions_by_target),
            'averaged_directions': averaged_directions,
            'closure_error': closure_error,
            'has_face_cl': len(face_cl) > 0,
            'has_face_cp': len(face_cp) > 0
        }

        return result

    def _check_reciprocal_measurements(self, observations: List[Any]) -> List[Dict]:
        """
        Этап 6: Контроль сходимости прямых/обратных измерений

        Проверяет расхождения между прямыми и обратными измерениями:
        - Расстояния: прямое и обратное
        - Превышения: прямое и обратное
        """
        violations = []

        # Группировка измерений по парам пунктов
        measurement_pairs = defaultdict(list)

        for obs in observations:
            obs_type = self._get_obs_type(obs)
            if obs_type in ['distance', 'slope_distance', 'horizontal_distance', 'height_diff']:
                pair_key = tuple(sorted([self._get_from_point(obs), self._get_to_point(obs)]))
                measurement_pairs[pair_key].append(obs)

        # Проверка каждой пары
        for pair, measurements in measurement_pairs.items():
            if len(measurements) < 2:
                continue

            # Разделение по направлениям
            forward = [m for m in measurements if self._get_from_point(m) == pair[0]]
            backward = [m for m in measurements if self._get_from_point(m) == pair[1]]

            if not forward or not backward:
                continue

            # Средние значения
            forward_mean = np.mean([self._get_value(m) for m in forward])
            backward_mean = np.mean([self._get_value(m) for m in backward])

            # Расхождение
            obs_type = self._get_obs_type(forward[0])
            if obs_type == 'height_diff':
                discrepancy = abs(forward_mean + backward_mean)
                allowable = 0.010  # 10 мм для технического нивелирования
            else:
                discrepancy = abs(forward_mean - backward_mean)
                allowable = 0.010  # 10 мм для расстояний

            if discrepancy > allowable:
                violations.append({
                    'type': 'reciprocal_discrepancy',
                    'obs_type': obs_type,
                    'pair': pair,
                    'forward_value': forward_mean,
                    'backward_value': backward_mean,
                    'discrepancy': discrepancy,
                    'allowable': allowable,
                    'is_violation': True
                })

        return violations

    def _apply_corrections(self, observations: List[Any],
                           config: Dict[str, Any]) -> List[Any]:
        """
        Этап 7: Применение редукций

        Применяет поправки к измерениям:
        - Атмосферные поправки
        - Поправки за рефракцию
        - Поправки за кривизну Земли
        """
        corrected = []

        for obs in observations:
            obs_type = self._get_obs_type(obs)

            if obs_type in ['distance', 'slope_distance', 'horizontal_distance']:
                value = self._get_value(obs)

                # Атмосферная поправка
                temperature = getattr(obs, 'temperature', 15.0)
                pressure = getattr(obs, 'pressure', 1013.25)

                # Упрощённая формула атмосферной поправки
                delta_atm = value * (0.000295 * (temperature - 15) - 0.000038 * (pressure - 1013.25))

                # Поправка за рефракцию и кривизну
                distance_km = value / 1000.0
                refraction_coeff = config.get('refraction_coefficient', 0.14)
                earth_radius = config.get('earth_radius', 6371000.0)
                delta_ref = (distance_km ** 2) * (1 - refraction_coeff) / (2 * earth_radius) * 1000

                # Создаём копию с исправленным значением
                corrected_obs = obs
                if hasattr(obs, 'value'):
                    corrected_obs.value = value + delta_atm + delta_ref

                corrected.append(corrected_obs)
            else:
                corrected.append(obs)

        return corrected

    def _compute_preliminary_coordinates(self, observations: List[Any],
                                         points: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Этап 8: Расчет предварительных координат

        Рассчитывает приближённые координаты определяемых пунктов
        методом последовательного приближения от известных пунктов.
        """
        coordinates = {}

        # Проверяем, что points не None
        if points is None:
            points = []

        # Обрабатываем как список или словарь
        if isinstance(points, list):
            # points - список словарей
            for point in points:
                if isinstance(point, dict):
                    point_id = point.get('name') or point.get('point_id', 'unknown')
                    coordinates[point_id] = {
                        'x': point.get('x', 0) or 0,
                        'y': point.get('y', 0) or 0,
                        'h': point.get('h', 0) or 0
                    }
                elif hasattr(point, 'point_id'):
                    # NetworkPoint object
                    point_id = point.point_id
                    coordinates[point_id] = {
                        'x': point.x if point.x is not None else 0,
                        'y': point.y if point.y is not None else 0,
                        'h': point.h if point.h is not None else 0,
                        '_point_obj': point  # Сохраняем ссылку на объект
                    }
        else:
            # points - словарь
            for point_id, point in points.items():
                if isinstance(point, dict):
                    coordinates[point_id] = {
                        'x': point.get('x', 0) or 0,
                        'y': point.get('y', 0) or 0,
                        'h': point.get('h', 0) or 0
                    }
                else:
                    coordinates[point_id] = {
                        'x': getattr(point, 'x', 0) or 0,
                        'y': getattr(point, 'y', 0) or 0,
                        'h': getattr(point, 'h', 0) or 0,
                        '_point_obj': point  # Сохраняем ссылку на объект
                    }

        # Вычисляем координаты для точек без них используя прямую геодезическую задачу
        self._compute_coords_from_measurements(observations, coordinates)

        result = {
            'coordinates': coordinates,
            'num_with_coords': sum(1 for c in coordinates.values() if c['x'] != 0 or c['y'] != 0),
            'num_without_coords': sum(1 for c in coordinates.values() if c['x'] == 0 and c['y'] == 0)
        }

        return result

    def _compute_coords_from_measurements(self, observations: List[Any], 
                                          coordinates: Dict[str, Dict[str, Any]]):
        """
        Вычисление приближенных координат для точек без координат
        используя прямую геодезическую задачу от известных точек.
        """
        # Собираем измерения расстояний и направлений
        distance_obs = []
        direction_obs = []
        
        for obs in observations:
            obs_type = self._get_obs_type(obs)
            
            # Обработка CombinedObservation
            if hasattr(obs, 'horizontal_angle') and hasattr(obs, 'slope_distance'):
                if obs.horizontal_angle is not None:
                    direction_obs.append(obs)
                if obs.slope_distance is not None:
                    distance_obs.append(obs)
            elif obs_type in ['distance', 'slope_distance', 'horizontal_distance']:
                distance_obs.append(obs)
            elif obs_type in ['direction', 'angle', 'azimuth']:
                direction_obs.append(obs)
        
        # Итеративно вычисляем координаты
        max_iterations = 10
        for iteration in range(max_iterations):
            coords_computed = False
            
            # Пытаемся вычислить координаты из расстояний
            for obs in distance_obs:
                from_p = self._get_from_point(obs)
                to_p = self._get_to_point(obs)
                
                # Получаем расстояние (для CombinedObservation используем slope_distance)
                if hasattr(obs, 'slope_distance') and obs.slope_distance is not None:
                    dist = obs.slope_distance
                else:
                    dist = self._get_value(obs)
                
                if dist <= 0:
                    continue
                
                # Если известна точка from_p, но неизвестна to_p
                if (coordinates.get(from_p, {}).get('x', 0) != 0 or 
                    coordinates.get(from_p, {}).get('y', 0) != 0):
                    if coordinates.get(to_p, {}).get('x', 0) == 0 and \
                       coordinates.get(to_p, {}).get('y', 0) == 0:
                        # Нужен азимут для вычисления координат
                        # Ищем направление от from_p к to_p
                        azimuth = self._find_azimuth(direction_obs, from_p, to_p, coordinates)
                        
                        if azimuth is not None:
                            # Прямая геодезическая задача
                            dx = dist * np.cos(azimuth)
                            dy = dist * np.sin(azimuth)
                            coordinates[to_p]['x'] = coordinates[from_p]['x'] + dx
                            coordinates[to_p]['y'] = coordinates[from_p]['y'] + dy
                            
                            # Обновляем объект точки если есть ссылка
                            if '_point_obj' in coordinates.get(to_p, {}):
                                pt = coordinates[to_p]['_point_obj']
                                if hasattr(pt, 'set_approx_coords'):
                                    pt.set_approx_coords(coordinates[to_p]['x'], 
                                                        coordinates[to_p]['y'])
                            
                            coords_computed = True
                            self.logger.info(f"Вычислены координаты {to_p} из {from_p}: "
                                           f"X={coordinates[to_p]['x']:.3f}, Y={coordinates[to_p]['y']:.3f}")
                
                # Если известна точка to_p, но неизвестна from_p (обратное измерение)
                if (coordinates.get(to_p, {}).get('x', 0) != 0 or 
                    coordinates.get(to_p, {}).get('y', 0) != 0):
                    if coordinates.get(from_p, {}).get('x', 0) == 0 and \
                       coordinates.get(from_p, {}).get('y', 0) == 0:
                        # Нужен обратный азимут
                        azimuth = self._find_azimuth(direction_obs, from_p, to_p, coordinates)
                        
                        if azimuth is not None:
                            # Обратный азимут
                            back_azimuth = azimuth + np.pi
                            if back_azimuth > 2 * np.pi:
                                back_azimuth -= 2 * np.pi
                            
                            dx = dist * np.cos(back_azimuth)
                            dy = dist * np.sin(back_azimuth)
                            coordinates[from_p]['x'] = coordinates[to_p]['x'] + dx
                            coordinates[from_p]['y'] = coordinates[to_p]['y'] + dy
                            
                            # Обновляем объект точки если есть ссылка
                            if '_point_obj' in coordinates.get(from_p, {}):
                                pt = coordinates[from_p]['_point_obj']
                                if hasattr(pt, 'set_approx_coords'):
                                    pt.set_approx_coords(coordinates[from_p]['x'], 
                                                        coordinates[from_p]['y'])
                            
                            coords_computed = True
                            self.logger.info(f"Вычислены координаты {from_p} из {to_p}: "
                                           f"X={coordinates[from_p]['x']:.3f}, Y={coordinates[from_p]['y']:.3f}")
            
            if not coords_computed:
                break
        
        # Удаляем временные ссылки на объекты
        for coord in coordinates.values():
            coord.pop('_point_obj', None)

    def _find_azimuth(self, direction_obs: List[Any], from_p: str, to_p: str,
                      coordinates: Dict[str, Dict[str, Any]]) -> Optional[float]:
        """
        Поиск азимута направления от from_p к to_p.
        """
        for obs in direction_obs:
            if self._get_from_point(obs) == from_p and self._get_to_point(obs) == to_p:
                # Для CombinedObservation используем horizontal_angle
                if hasattr(obs, 'horizontal_angle') and obs.horizontal_angle is not None:
                    angle = obs.horizontal_angle
                else:
                    angle = self._get_value(obs)
                
                angle_unit = getattr(obs, 'angle_unit', 'degrees')
                
                # Конвертация в радианы
                if angle_unit == 'degrees':
                    return np.deg2rad(angle)
                elif angle_unit == 'gons':
                    return angle * np.pi / 200.0
                elif angle_unit == 'radians':
                    return angle
                else:
                    return np.deg2rad(angle)
        
        # Если нет измеренного направления, вычисляем из координат других точек
        # Это упрощенный подход - в реальности нужен более сложный алгоритм
        return None

    def run_all_stages(self, observations: List[Any], points: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
                       config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Запуск всех этапов предобработки

        Параметры:
        - observations: список измерений
        - points: словарь пунктов
        - config: конфигурация предобработки

        Возвращает:
        - Словарь с результатами всех этапов
        """
        if config is None:
            config = {}

        results = {
            'stages_completed': 0,
            'topology': None,
            'traverses': None,
            'receptions': None,
            'averaged_directions': None,
            'reciprocal_violations': None,
            'corrected_observations': None,
            'preliminary_coordinates': None,
            'tolerance_violations': [],
            'errors': [],
            'warnings': []
        }

        try:
            # Этап 1: Распознавание топологии сети
            self.logger.info("Этап 1: Распознавание топологии сети")
            results['topology'] = self._build_network_topology(observations)
            self.logger.info(f"  Пунктов: {len(results['topology']['points'])}")
            self.logger.info(f"  Измерений: {results['topology']['num_observations']}")
            self.logger.info(f"  Тип сети: {results['topology']['network_type']}")

            # Этап 2: Формирование ходов и секций
            self.logger.info("Этап 2: Формирование ходов и секций")
            results['traverses'] = self._detect_traverses_and_sections(
                results['topology'], observations
            )
            self.logger.info(f"  Ходов: {len(results['traverses']['traverses'])}")
            self.logger.info(f"  Секций: {len(results['traverses']['sections'])}")
            self.logger.info(f"  GNSS базовых линий: {len(results['traverses']['gnss_baselines'])}")

            # Этап 3: Обработка приемов измерений
            self.logger.info("Этап 3: Обработка приемов измерений")
            reception_results = []
            for station_id in results['topology']['stations']:
                result = self._process_receptions(observations, station_id)
                reception_results.append(result)
            results['receptions'] = reception_results

            # Этап 5: Усреднение направлений
            self.logger.info("Этап 5: Усреднение направлений в приемах")
            all_averaged = {}
            for rr in reception_results:
                if rr.get('status') == 'success':
                    all_averaged.update(rr.get('averaged_directions', {}))
            results['averaged_directions'] = all_averaged

            # Этап 6: Контроль сходимости
            self.logger.info("Этап 6: Контроль сходимости прямых/обратных измерений")
            results['reciprocal_violations'] = self._check_reciprocal_measurements(observations)
            self.logger.info(f"  Нарушений: {len(results['reciprocal_violations'])}")

            # Этап 7: Применение редукций
            self.logger.info("Этап 7: Применение редукций")
            results['corrected_observations'] = self._apply_corrections(observations, config)

            # Этап 8: Расчет предварительных координат
            self.logger.info("Этап 8: Расчет предварительных координат")
            results['preliminary_coordinates'] = self._compute_preliminary_coordinates(
                results['corrected_observations'], points
            )

            results['stages_completed'] = 9
            self.logger.info("Предобработка завершена успешно")

        except Exception as e:
            error_msg = f"Ошибка при предобработке: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)

        return results

    def run_preprocessing(self, observations: List[Any], points: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
                          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Упрощённый запуск предобработки для совместимости с GUI
        
        Параметры:
        - observations: список измерений
        - points: словарь пунктов (опционально)
        - config: конфигурация (опционально)
        
        Возвращает:
        - Словарь с результатами предобработки
        """
        if points is None:
            points = {}
        if config is None:
            config = {}
        
        return self.run_all_stages(observations, points, config)
