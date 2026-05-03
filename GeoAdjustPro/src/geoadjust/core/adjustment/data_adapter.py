#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Адаптер для конвертации данных парсеров в формат для уравнивания
Конвертирует результаты парсинга SDR/GSI/DAT в формат для AdjustmentEngine
"""

import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

from geoadjust.core.network.models import NetworkPoint, Observation, InstrumentSetup, CombinedObservation
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder

logger = logging.getLogger(__name__)


class DataAdapter:
    """Адаптер для конвертации данных парсеров в формат для уравнивания"""
    
    @staticmethod
    def convert_points_to_dict(points_data: List[Dict], observations_data: List[Any] = None) -> Dict[str, NetworkPoint]:
        """
        Конвертация списка точек из парсера в словарь NetworkPoint
        
        Параметры:
        -----------
        points_data : List[Dict]
            Список словарей с данными точек от парсера
            Формат: [{'point_id': 'P1', 'x': 100.0, 'y': 200.0, 'h': 50.0, 'point_type': 'FIXED'}, ...]
        observations_data : List[Any], optional
            Список наблюдений для добавления отсутствующих точек
            
        Возвращает:
        ------------
        Dict[str, NetworkPoint]
            Словарь {point_id: NetworkPoint}
        """
        points_dict = {}
        
        # Сначала добавляем точки из списка точек
        for p in points_data:
            point_id = p.get('point_id')
            if not point_id:
                continue
            
            # Нормализуем имя точки (приводим к верхнему регистру для консистентности)
            point_id_normalized = str(point_id).upper()
            
            # Определяем тип координат
            point_type = p.get('point_type', 'FREE').upper()
            if point_type == 'FIXED':
                coord_type = 'FIXED'
            elif point_type in ['STATION', 'FREE']:
                coord_type = 'APPROXIMATE'
            else:
                coord_type = 'FREE'
            
            # Получаем координаты (защита от None)
            x = p.get('x')
            y = p.get('y')
            h = p.get('h')
            
            # Если координат нет, используем 0.0 как приближение
            if x is None:
                x = 0.0
            if y is None:
                y = 0.0
            if h is None:
                h = 0.0
            
            point = NetworkPoint(
                point_id=point_id_normalized,
                coord_type=coord_type,
                x=float(x),
                y=float(y),
                h=float(h) if h is not None else None
            )
            points_dict[point_id_normalized] = point
        
        # Добавляем отсутствующие точки из наблюдений
        if observations_data:
            for obs in observations_data:
                from_point = None
                to_point = None
                
                if isinstance(obs, CombinedObservation):
                    from_point = obs.from_point_id
                    to_point = obs.to_point_id
                elif isinstance(obs, dict):
                    from_point = obs.get('from_point_id') or obs.get('from_point')
                    to_point = obs.get('to_point_id') or obs.get('to_point')
                
                # Добавляем точку станции если её нет
                if from_point:
                    from_point_normalized = str(from_point).upper()
                    if from_point_normalized not in points_dict:
                        points_dict[from_point_normalized] = NetworkPoint(
                            point_id=from_point_normalized,
                            coord_type='APPROXIMATE',
                            x=0.0,
                            y=0.0,
                            h=0.0
                        )
                        logger.debug(f"Добавлена точка {from_point_normalized} из наблюдений")
                
                # Добавляем точку цели если её нет
                if to_point:
                    to_point_normalized = str(to_point).upper()
                    if to_point_normalized not in points_dict:
                        points_dict[to_point_normalized] = NetworkPoint(
                            point_id=to_point_normalized,
                            coord_type='FREE',
                            x=0.0,
                            y=0.0,
                            h=0.0
                        )
                        logger.debug(f"Добавлена точка {to_point_normalized} из наблюдений")
        
        logger.info(f"Конвертировано {len(points_dict)} точек")
        return points_dict
    
    @staticmethod
    def normalize_project_data(raw_points, raw_observations):
        """
        Нормализация данных проекта в ожидаемые форматы для уравнивания

        Преобразует:
        - raw_points: List[Dict] -> Dict[str, NetworkPoint]
        - raw_observations: List[Dict] -> List[Observation]

        Параметры:
        -----------
        raw_points : List[Dict] или Dict[str, Any]
            Сырые данные точек от парсера
        raw_observations : List[Any]
            Сырые данные наблюдений от парсера

        Возвращает:
        ------------
        Tuple[Dict[str, NetworkPoint], List[Observation]]
            Нормализованные точки и наблюдения
        """
        # Преобразование точек в Dict[str, NetworkPoint]
        points_dict = {}
        if isinstance(raw_points, list):
            # points - список словарей
            for p in raw_points:
                if isinstance(p, dict):
                    point_id = p.get('point_id') or p.get('id', 'unknown')
                    point_id_normalized = str(point_id).upper()

                    # Определяем тип координат
                    point_type = p.get('point_type', 'FREE').upper()
                    if point_type == 'FIXED':
                        coord_type = 'FIXED'
                    elif point_type in ['STATION', 'APPROXIMATE']:
                        coord_type = 'APPROXIMATE'
                    else:
                        coord_type = 'FREE'

                    # Получаем координаты
                    x = p.get('x')
                    y = p.get('y')
                    h = p.get('h')

                    point = NetworkPoint(
                        point_id=point_id_normalized,
                        coord_type=coord_type,
                        x=float(x) if x is not None else None,
                        y=float(y) if y is not None else None,
                        h=float(h) if h is not None else None
                    )
                    points_dict[point_id_normalized] = point
                else:
                    # points - объект NetworkPoint
                    point_id = getattr(p, 'point_id', getattr(p, 'id', 'unknown'))
                    points_dict[str(point_id).upper()] = p
        else:
            # points - словарь
            for point_id, point in raw_points.items():
                if isinstance(point, dict):
                    point_id_normalized = str(point_id).upper()
                    points_dict[point_id_normalized] = NetworkPoint(
                        point_id=point_id_normalized,
                        coord_type=point.get('coord_type', 'FREE'),
                        x=point.get('x'),
                        y=point.get('y'),
                        h=point.get('h')
                    )
                else:
                    points_dict[str(point_id).upper()] = point

        # Валидация и фильтрация наблюдений
        valid_obs = []
        for obs in raw_observations:
            # Обработка GSIObservation объектов
            if hasattr(obs, 'from_point') and hasattr(obs, 'to_point'):
                # GSIObservation объект
                from_point_id = str(obs.from_point).upper()
                to_point_id = str(obs.to_point).upper()

                if from_point_id in points_dict and to_point_id in points_dict:
                    observation = Observation(
                        obs_id=getattr(obs, 'obs_id', getattr(obs, 'station_session_id', f'OBS_{len(valid_obs)}')),
                        obs_type=getattr(obs, 'obs_type', 'unknown'),
                        from_setup_id=getattr(obs, 'station_session_id', f'SETUP_{from_point_id}'),
                        from_point_id=from_point_id,
                        to_point_id=to_point_id,
                        value=getattr(obs, 'value', 0.0),
                        sigma_apriori=getattr(obs, 'sigma_apriori', None),
                        is_active=getattr(obs, 'is_active', True)
                    )
                    valid_obs.append(observation)
                else:
                    logger.debug(f"GSI измерение ссылается на несуществующий пункт: {from_point_id} -> {to_point_id}")

            elif isinstance(obs, dict):
                # Конвертация dict в Observation если нужно
                from_point_id = obs.get('from_point_id') or obs.get('from_point')
                to_point_id = obs.get('to_point_id') or obs.get('to_point')

                if from_point_id and to_point_id:
                    from_point_id = str(from_point_id).upper()
                    to_point_id = str(to_point_id).upper()

                    if from_point_id in points_dict and to_point_id in points_dict:
                        observation = Observation(
                            obs_id=obs.get('obs_id', obs.get('id', f'OBS_{len(valid_obs)}')),
                            obs_type=obs.get('obs_type', obs.get('type', 'unknown')),
                            from_setup_id=obs.get('from_setup_id', f'SETUP_{from_point_id}'),
                            from_point_id=from_point_id,
                            to_point_id=to_point_id,
                            value=obs.get('value', 0.0),
                            is_active=obs.get('is_active', True)
                        )
                        valid_obs.append(observation)
                    else:
                        logger.warning(f"Измерение ссылается на несуществующий пункт: {from_point_id} -> {to_point_id}")
            else:
                # Уже объект Observation
                if hasattr(obs, 'from_point_id') and hasattr(obs, 'to_point_id'):
                    from_point_id = str(obs.from_point_id).upper()
                    to_point_id = str(obs.to_point_id).upper()

                    if from_point_id in points_dict and to_point_id in points_dict:
                        # Убеждаемся что point_id в верхнем регистре
                        obs.from_point_id = from_point_id
                        obs.to_point_id = to_point_id
                        valid_obs.append(obs)
                    else:
                        logger.warning(f"Измерение ссылается на несуществующий пункт: {from_point_id} -> {to_point_id}")

        logger.info(f"Нормализовано: {len(points_dict)} точек, {len(valid_obs)} наблюдений")
        return points_dict, valid_obs

    @staticmethod
    def convert_observations(obs_data: List[Any]) -> List[Observation]:
        """
        Конвертация наблюдений из парсера в список Observation
        
        Параметры:
        -----------
        obs_data : List[Any]
            Список наблюдений от парсера (CombinedObservation или другие типы)
        
        Возвращает:
        ------------
        List[Observation]
            Список объектов Observation для уравнивания
        """
        observations = []
        
        for obs in obs_data:
            # Если это CombinedObservation, конвертируем в отдельные Observation
            if isinstance(obs, CombinedObservation):
                # Создаём direction observation если есть горизонтальный угол
                if obs.horizontal_angle is not None:
                    dir_obs = Observation(
                        obs_id=f"{obs.obs_id}_DIR",
                        obs_type='direction',
                        from_setup_id=obs.from_setup_id,
                        from_point_id=obs.from_point_id,
                        to_point_id=obs.to_point_id,
                        value=obs.horizontal_angle,
                        face_position=obs.face_position,
                        is_active=True
                    )
                    observations.append(dir_obs)
                
                # Создаём distance observation если есть расстояние
                if obs.slope_distance is not None:
                    dist_obs = Observation(
                        obs_id=f"{obs.obs_id}_DIST",
                        obs_type='distance',
                        from_setup_id=obs.from_setup_id,
                        from_point_id=obs.from_point_id,
                        to_point_id=obs.to_point_id,
                        value=obs.slope_distance,
                        face_position=obs.face_position,
                        is_active=True
                    )
                    observations.append(dist_obs)
                
                # Создаём zenith_angle observation если есть зенитный угол
                if obs.zenith_angle is not None:
                    zen_obs = Observation(
                        obs_id=f"{obs.obs_id}_ZEN",
                        obs_type='zenith_angle',
                        from_setup_id=obs.from_setup_id,
                        from_point_id=obs.from_point_id,
                        to_point_id=obs.to_point_id,
                        value=obs.zenith_angle,
                        face_position=obs.face_position,
                        is_active=True
                    )
                    observations.append(zen_obs)
            
            # Если это уже Observation, добавляем как есть
            elif isinstance(obs, Observation):
                observations.append(obs)
            
            # Если это словарь, конвертируем
            elif isinstance(obs, dict):
                obs_type = obs.get('obs_type', 'direction')
                
                # Для combined типа создаём несколько наблюдений
                if obs_type == 'combined':
                    if obs.get('horizontal_angle') is not None:
                        dir_obs = Observation(
                            obs_id=f"OBS_{len(observations):06d}_DIR",
                            obs_type='direction',
                            from_setup_id=obs.get('from_setup_id', ''),
                            from_point_id=obs.get('from_point_id', ''),
                            to_point_id=obs.get('to_point_id', ''),
                            value=obs.get('horizontal_angle'),
                            face_position=obs.get('face_position'),
                            is_active=True
                        )
                        observations.append(dir_obs)
                    
                    if obs.get('slope_distance') is not None:
                        dist_obs = Observation(
                            obs_id=f"OBS_{len(observations):06d}_DIST",
                            obs_type='distance',
                            from_setup_id=obs.get('from_setup_id', ''),
                            from_point_id=obs.get('from_point_id', ''),
                            to_point_id=obs.get('to_point_id', ''),
                            value=obs.get('slope_distance'),
                            face_position=obs.get('face_position'),
                            is_active=True
                        )
                        observations.append(dist_obs)
                else:
                    # Обычное наблюдение
                    observation = Observation(
                        obs_id=f"OBS_{len(observations):06d}",
                        obs_type=obs_type,
                        from_setup_id=obs.get('from_setup_id', ''),
                        from_point_id=obs.get('from_point_id', ''),
                        to_point_id=obs.get('to_point_id', ''),
                        value=obs.get('value', 0.0),
                        face_position=obs.get('face_position'),
                        is_active=True
                    )
                    observations.append(observation)
        
        logger.info(f"Конвертировано {len(observations)} наблюдений")
        return observations


class AdjustmentProcessor:
    """Процессор для полного цикла уравнивания"""
    
    def __init__(self):
        self.adapter = DataAdapter()
        self.builder = EquationsBuilder()
        self.weight_builder = WeightBuilder()
        self.engine = AdjustmentEngine()
    
    def process(self, parse_result: Dict[str, Any], fixed_points: List[str] = None) -> Dict[str, Any]:
        """
        Полный цикл обработки данных от парсинга до уравнивания
        
        Параметры:
        -----------
        parse_result : Dict[str, Any]
            Результат парсинга файла (SDR/GSI/DAT)
        fixed_points : List[str], optional
            Список идентификаторов твёрдых (исходных) пунктов
        
        Возвращает:
        ------------
        Dict[str, Any]
            Результаты уравнивания
        """
        # Извлекаем данные из результата парсинга
        points_data = parse_result.get('points', [])
        obs_data = parse_result.get('observations', [])
        
        logger.info(f"Обработка {len(points_data)} точек и {len(obs_data)} наблюдений")
        
        # Конвертируем точки в словарь NetworkPoint (с добавлением точек из наблюдений)
        points = self.adapter.convert_points_to_dict(points_data, obs_data)
        
        # Конвертируем наблюдения в список Observation
        observations = self.adapter.convert_observations(obs_data)
        
        if not points:
            raise ValueError("Нет точек для уравнивания")
        
        if not observations:
            raise ValueError("Нет наблюдений для уравнивания")
        
        # Определяем фиксированные точки если не указаны
        if fixed_points is None:
            fixed_points = [
                pid for pid, p in points.items() 
                if p.coord_type == 'FIXED'
            ]
            logger.info(f"Автоматически определены фиксированные точки: {fixed_points}")
        
        # Строим матрицу уравнений поправок
        logger.info("Построение матрицы уравнений поправок...")
        A, L = self.builder.build_adjustment_matrix(
            observations=observations,
            points=points,
            fixed_points=fixed_points
        )
        logger.info(f"Матрица A: {A.shape}, Вектор L: {L.shape}")
        
        # Строим весовую матрицу
        logger.info("Построение весовой матрицы...")
        P = self.weight_builder.build(observations)
        logger.info(f"Матрица P: {P.shape}")
        
        # Выполняем уравнивание
        logger.info("Выполнение уравнивания...")
        result = self.engine.adjust(A, L, P)
        
        # Добавляем информацию о точках и наблюдениях
        result['points'] = points
        result['observations'] = observations
        result['fixed_points'] = fixed_points
        
        return result


def full_cycle_test(file_path: str, parser_class, fixed_points: List[str] = None):
    """
    Тест полного цикла: парсинг -> конвертация -> уравнивание
    
    Параметры:
    -----------
    file_path : str
        Путь к файлу измерений
    parser_class : class
        Класс парсера (SDRParser, GSIParser, DATParser)
    fixed_points : List[str], optional
        Список фиксированных точек
    
    Возвращает:
    ------------
    Dict[str, Any]
        Результаты уравнивания или ошибку
    """
    try:
        # Парсинг файла
        logger.info(f"Парсинг файла: {file_path}")
        parser = parser_class()
        parse_result = parser.parse(Path(file_path))
        
        if not parse_result.get('success', False):
            logger.warning(f"Парсинг завершился с предупреждениями: {parse_result.get('errors', [])}")
        
        logger.info(f"Распаршено {parse_result.get('num_points', 0)} точек и {parse_result.get('num_observations', 0)} наблюдений")
        
        # Уравнивание
        processor = AdjustmentProcessor()
        adjustment_result = processor.process(parse_result, fixed_points)
        
        return {
            'success': True,
            'file': file_path,
            'parse_result': parse_result,
            'adjustment_result': adjustment_result
        }
    
    except Exception as e:
        logger.error(f"Ошибка при обработке файла {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'file': file_path,
            'error': str(e)
        }


if __name__ == "__main__":
    # Пример использования
    import sys
    sys.path.insert(0, '/workspace/GeoAdjustPro/src')
    
    from geoadjust.io.formats.sdr import SDRParser
    
    # Тест на примере SDR файла
    test_file = "/workspace/test_real_mes/kotlntss06042026.sdr"
    result = full_cycle_test(test_file, SDRParser, fixed_points=['S20'])
    
    if result['success']:
        print("\n" + "=" * 70)
        print(" УРАВНИВАНИЕ ВЫПОЛНЕНО УСПЕШНО")
        print("=" * 70)
        adj = result['adjustment_result']
        print(f"Итераций: {adj.get('iterations', 'N/A')}")
        print(f"СКО единицы веса: {adj.get('sigma0', 'N/A'):.6f}")
        print(f"Число неизвестных: {len(adj.get('coordinate_corrections', []))}")
        print(f"Число остатков: {len(adj.get('residuals', []))}")
    else:
        print(f"\nОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
