# -*- coding: utf-8 -*-
"""
Парсер данных нивелирования из Credo DAT (Excel)
"""

from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class CredoDATParser:
    """Парсер данных нивелирования из Credo DAT (Excel)"""
    
    def __init__(self):
        pass
    
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Парсинг Excel файла с данными нивелирования"""

        # Читаем Excel файл
        df = pd.read_excel(file_path)

        # Определяем колонки по названиям
        columns = list(df.columns)
        # Определяем колонки по индексам (на основе анализа файла)
        # Известная структура: индекс 3 = имя, 4 = превышение, 5 = тип, 6 = расстояние
        point_col = columns[3] if len(columns) > 3 else None
        height_diff_col = columns[4] if len(columns) > 4 else None
        measurement_type_col = columns[5] if len(columns) > 5 else None
        distance_col = columns[6] if len(columns) > 6 else None



        points = []
        observations = []
        station_sessions = []

        current_station = None
        session_counter = 0

        # Словарь для точек
        point_dict = {}

        # Обрабатываем все строки последовательно
        for idx, row in df.iterrows():
            try:
                # Получаем значения из соответствующих колонок
                point_name = None
                if point_col and pd.notna(row.get(point_col)):
                    point_name = str(row.get(point_col)).strip()

                if not point_name:
                    continue

                height_diff = 0.0
                if height_diff_col and pd.notna(row.get(height_diff_col)):
                    height_diff_str = str(row.get(height_diff_col)).replace(',', '.')
                    try:
                        height_diff = float(height_diff_str)
                    except ValueError:
                        height_diff = 0.0

                measurement_type = ''
                if measurement_type_col and pd.notna(row.get(measurement_type_col)):
                    measurement_type = str(row.get(measurement_type_col)).strip()

                distance = None
                if distance_col and pd.notna(row.get(distance_col)):
                    distance_str = str(row.get(distance_col)).replace(',', '.')
                    try:
                        distance = float(distance_str)
                    except ValueError:
                        distance = None

                # Определяем тип измерения
                if 'задняя' in measurement_type.lower() or '������' in measurement_type:
                    # Это установка станции
                    current_station = point_name
                    session_counter += 1

                    # Добавляем станцию в точки
                    if point_name not in point_dict:
                        point_dict[point_name] = {
                            'point_id': point_name,
                            'point_type': 'station',
                            'x': None,
                            'y': None,
                            'h': None
                        }
                        points.append(point_dict[point_name])

                    # Создаем сессию станции
                    session = {
                        'session_id': f"SESSION_{session_counter:03d}",
                        'station_name': point_name,
                        'instrument_height': None,
                        'observations': []
                    }
                    station_sessions.append(session)

                elif ('передняя' in measurement_type.lower() or '�������' in measurement_type) and current_station:
                    # Это измерение превышения от станции к цели
                    if point_name != current_station:
                        # Добавляем цель в точки
                        if point_name not in point_dict:
                            point_dict[point_name] = {
                                'point_id': point_name,
                                'point_type': 'target',
                                'x': None,
                                'y': None,
                                'h': None
                            }
                            points.append(point_dict[point_name])

                        # Создаем измерение превышения
                        obs = {
                            'obs_type': 'leveling_height_diff',
                            'from_point': current_station,
                            'to_point': point_name,
                            'value': height_diff,
                            'distance': distance,
                            'instrument_height': None,
                            'station_session_id': f"SESSION_{session_counter:03d}",
                            'line_number': idx + 1
                        }
                        observations.append(obs)

                        # Добавляем в сессию
                        if station_sessions:
                            station_sessions[-1]['observations'].append(obs)

                elif 'промежуточная' in measurement_type.lower() or '�������������' in measurement_type:
                    # Боковое нивелирование
                    obs = {
                        'obs_type': 'intermediate_leveling',
                        'from_point': current_station if current_station else point_name,
                        'to_point': point_name,
                        'value': height_diff,
                        'distance': distance,
                        'instrument_height': None,
                        'station_session_id': f"SESSION_{session_counter:03d}" if station_sessions else None,
                        'line_number': idx + 1
                    }
                    observations.append(obs)

                    # Добавляем точку
                    if point_name not in point_dict:
                        point_dict[point_name] = {
                            'point_id': point_name,
                            'point_type': 'intermediate',
                            'x': None,
                            'y': None,
                            'h': None
                        }
                        points.append(point_dict[point_name])

            except Exception as e:
                logger.warning(f"Ошибка обработки строки {idx}: {e}")
                continue

        # Пост-обработка: группируем измерения нивелирования в ходы
        leveling_courses = self._build_leveling_courses(observations, points)

        return {
            'points': points,
            'observations': observations,
            'station_sessions': station_sessions,
            'leveling_courses': leveling_courses,
            'format': 'CredoDAT',
            'total_lines': len(df),
            'num_observations': len(observations),
            'num_points': len(points),
            'num_courses': len(leveling_courses),
            'success': len(observations) > 0,
            'errors': [],
            'warnings': []
        }

    def _build_leveling_courses(self, observations, points):
        """Построение ходов нивелирования из измерений"""
        # Фильтруем только основные измерения нивелирования
        leveling_obs = [obs for obs in observations if obs.get('obs_type') == 'leveling_height_diff']

        if not leveling_obs:
            return []

        # Группируем измерения по начальной точке
        from_groups = {}
        for obs in leveling_obs:
            from_point = obs['from_point']
            if from_point not in from_groups:
                from_groups[from_point] = []
            from_groups[from_point].append(obs)

        # Находим цепочки станций (ходы)
        courses = []
        processed_points = set()

        def build_course_chain(start_point):
            """Строим цепочку от начальной точки"""
            if start_point in processed_points:
                return []

            chain = []
            current = start_point

            while current in from_groups and current not in processed_points:
                processed_points.add(current)
                obs_list = from_groups[current]

                # Добавляем все измерения от этой станции
                for obs in obs_list:
                    chain.append({
                        'from_point': obs['from_point'],
                        'to_point': obs['to_point'],
                        'value': obs['value'],
                        'distance': obs.get('distance'),
                        'type': 'leveling_height_diff'
                    })

                    # Переходим к следующей точке
                    next_point = obs['to_point']
                    if next_point not in processed_points and next_point in from_groups:
                        current = next_point
                        break
                else:
                    # Нет больше измерений от этой точки
                    break

            return chain

        # Ищем реперные точки как начало ходов
        repers = [p['point_id'] for p in points if p.get('point_type') == 'station' and any(p['point_id'].startswith(prefix) for prefix in ['R', 'GR', 'р', 'гр'])]

        for start_point in repers:
            if start_point not in processed_points:
                chain = build_course_chain(start_point)
                if chain:
                    course = {
                        'course_id': f"COURSE_{len(courses) + 1:03d}",
                        'stations': list(set([m['from_point'] for m in chain] + [m['to_point'] for m in chain])),
                        'measurements': chain
                    }
                    courses.append(course)

        # Добавляем оставшиеся цепочки
        for start_point in from_groups.keys():
            if start_point not in processed_points:
                chain = build_course_chain(start_point)
                if chain:
                    course = {
                        'course_id': f"COURSE_{len(courses) + 1:03d}",
                        'stations': list(set([m['from_point'] for m in chain] + [m['to_point'] for m in chain])),
                        'measurements': chain
                    }
                    courses.append(course)

        return courses