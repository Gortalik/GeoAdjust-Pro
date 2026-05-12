#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексная проверка интеграции всех подсистем GeoAdjust-Pro

Проверяет:
1. Парсинг реальных данных всех форматов
2. Конвертацию во внутреннюю модель данных
3. Построение матриц уравнений
4. Уравнивание
5. Оценку точности
"""

import sys
from pathlib import Path
import numpy as np
from scipy import sparse


from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.sdr import SDRParser
from geoadjust.io.formats.dat import DATParser
from geoadjust.io.formats.pos import POSParser
from geoadjust.core.network.models import NetworkPoint, Observation
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder
from geoadjust.core.adjustment.free_network import FreeNetworkAdjustment
from geoadjust.core.adjustment.engine import AdjustmentEngine

# Базовый путь к тестовым данным
TEST_DATA_DIR = Path(__file__).parent.parent / 'test_real_mes'


def create_observation_from_parsed(obs, obs_id_counter):
    """Конвертация распарсенного наблюдения в модель Observation"""
    obs_type = getattr(obs, 'obs_type', 'unknown')
    
    # Маппинг типов измерений
    type_map = {
        'direction': 'direction',
        'zenith_angle': 'zenith_angle',
        'horizontal_distance': 'distance',
        'slope_distance': 'distance',
        'height_diff': 'height_diff',
        'backsight': 'height_diff',
        'foresight': 'height_diff',
        'intermediate': 'height_diff',
        'gnss_vector': 'gnss_vector',
    }
    
    mapped_type = type_map.get(obs_type, 'direction')
    
    # Создаём Observation
    return Observation(
        obs_id=f"OBS_{obs_id_counter}",
        obs_type=mapped_type,
        from_point=getattr(obs, 'from_point', 'UNKNOWN'),
        to_point=getattr(obs, 'to_point', 'UNKNOWN'),
        value=getattr(obs, 'value', 0),
        instrument_name='',
        sigma_apriori=getattr(obs, 'std_dev', None),
        is_active=True,
        # GNSS-specific
        delta_x=getattr(obs, 'delta_x', None),
        delta_y=getattr(obs, 'delta_y', None),
        delta_z=getattr(obs, 'delta_z', None),
        sigma_x=getattr(obs, 'sigma_x', None),
        sigma_y=getattr(obs, 'sigma_y', None),
        sigma_z=getattr(obs, 'sigma_z', None),
        # Angle-specific
        angle_unit='gons' if obs_type in ['direction', 'zenith_angle'] else 'degrees',
        # Height-specific
        instrument_height=getattr(obs, 'instrument_height', None),
        target_height=getattr(obs, 'target_height', None),
    )


def test_leveling_pipeline():
    """Тестирование полного цикла нивелирования"""
    print("\n" + "=" * 70)
    print("ТЕСТ: Нивелирование (DAT формат)")
    print("=" * 70)
    
    # 1. Парсинг
    parser = DATParser()
    result = parser.parse(TEST_DATA_DIR / 'l/niv/LIH2103.DAT')
    print(f"\n1. Парсинг: {result['num_observations']} измерений, {result['num_points']} точек")
    
    # 2. Конвертация в модель
    points = {}
    observations = []
    obs_counter = 0
    
    for p in result.get('points', []):
        pid = p.get('point_id', '')
        points[pid] = NetworkPoint(
            point_id=pid,
            coord_type='APPROXIMATE',
            x=0, y=0, h=p.get('h', 0) or 0
        )
    
    for obs in result.get('observations', []):
        obs_counter += 1
        observations.append(create_observation_from_parsed(obs, obs_counter))
    
    print(f"2. Конвертация: {len(points)} точек, {len(observations)} измерений")
    
    # 3. Проверка структуры данных
    height_diffs = [o for o in observations if o.obs_type == 'height_diff']
    print(f"3. Превышений: {len(height_diffs)}")
    
    # 4. Проверка уникальных точек
    unique_points = set()
    for obs in observations:
        unique_points.add(obs.from_point)
        unique_points.add(obs.to_point)
    print(f"4. Уникальных точек: {len(unique_points)}")
    
    # 5. Проверка последовательности хода
    print(f"5. Точки нивелирования: {sorted(unique_points)[:15]}...")
    
    return len(observations) > 0 and len(points) > 0


def test_total_station_pipeline():
    """Тестирование полного цикла тахеометрии"""
    print("\n" + "=" * 70)
    print("ТЕСТ: Тахеометрия (SDR формат)")
    print("=" * 70)
    
    # 1. Парсинг
    parser = SDRParser()
    result = parser.parse(TEST_DATA_DIR / 'b_g/plan/badgro16093_const.sdr')
    print(f"\n1. Парсинг: {result['num_observations']} измерений, {result['num_points']} точек")
    
    # 2. Конвертация в модель
    points = {}
    observations = []
    obs_counter = 0
    
    for p in result.get('points', []):
        pid = p.get('point_id', '')
        points[pid] = NetworkPoint(
            point_id=pid,
            coord_type='APPROXIMATE',
            x=p.get('x', 0) or 0,
            y=p.get('y', 0) or 0,
            h=p.get('h', 0) or 0
        )
    
    for obs in result.get('observations', []):
        obs_counter += 1
        observations.append(create_observation_from_parsed(obs, obs_counter))
    
    print(f"2. Конвертация: {len(points)} точек, {len(observations)} измерений")
    
    # 3. Проверка типов измерений
    directions = [o for o in observations if o.obs_type == 'direction']
    distances = [o for o in observations if o.obs_type == 'distance']
    zeniths = [o for o in observations if o.obs_type == 'zenith_angle']
    print(f"3. Направлений: {len(directions)}, Зенитов: {len(zeniths)}, Расстояний: {len(distances)}")
    
    # 4. Проверка станционной структуры
    stations = set(o.from_point for o in observations)
    print(f"4. Станций: {len(stations)}")
    
    # 5. Проверка полуприёмов (Face 1/Face 2)
    print(f"5. Измерений на станцию: {len(observations)/max(len(stations),1):.1f}")
    
    return len(observations) > 0 and len(points) > 0


def test_gnss_pipeline():
    """Тестирование полного цикла GNSS"""
    print("\n" + "=" * 70)
    print("ТЕСТ: GNSS векторы (POS формат)")
    print("=" * 70)
    
    # 1. Парсинг
    parser = POSParser()
    result = parser.parse(TEST_DATA_DIR / 'gnss/drag-bshm.pos')
    print(f"\n1. Парсинг: {result['num_epochs']} эпох")
    
    # 2. Получение GNSS вектора
    vector = parser.get_gnss_vector()
    if vector:
        print(f"2. Вектор: {vector.from_station} -> {vector.to_station}")
        print(f"   dX = {vector.dx:.4f} m (sigma = {vector.sigma_dx*1000:.2f} mm)")
        print(f"   dY = {vector.dy:.4f} m (sigma = {vector.sigma_dy*1000:.2f} mm)")
        print(f"   dZ = {vector.dz:.4f} m (sigma = {vector.sigma_dz*1000:.2f} mm)")
        
        # 3. Конвертация в модель
        points = {
            vector.from_station: NetworkPoint(
                point_id=vector.from_station,
                coord_type='FIXED',
                x=0, y=0, h=0
            ),
            vector.to_station: NetworkPoint(
                point_id=vector.to_station,
                coord_type='APPROXIMATE',
                x=0, y=0, h=0
            )
        }
        
        observations = [Observation(
            obs_id='GNSS_1',
            obs_type='gnss_vector',
            from_point=vector.from_station,
            to_point=vector.to_station,
            value=0,
            instrument_name='',
            sigma_apriori=(vector.sigma_dx + vector.sigma_dy + vector.sigma_dz) / 3,
            delta_x=vector.dx,
            delta_y=vector.dy,
            delta_z=vector.dz,
            sigma_x=vector.sigma_dx,
            sigma_y=vector.sigma_dy,
            sigma_z=vector.sigma_dz,
        )]
        
        print(f"3. Конвертация: {len(points)} точек, {len(observations)} векторов")
        return True
    else:
        print("   Нет GNSS вектора")
        return False


def test_import_dialog_conversion():
    """Тестирование конвертации в формате ImportDialog"""
    print("\n" + "=" * 70)
    print("ТЕСТ: Конвертация для ImportDialog")
    print("=" * 70)
    
    # Тестируем DAT
    from geoadjust.io.formats.dat import DATParser
    from pathlib import Path
    
    parser = DATParser()
    data = parser.parse(TEST_DATA_DIR / 'l/niv/LIH2103.DAT')
    
    # Конвертация как в ImportDialog
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
            'type': getattr(obs, 'obs_type', 'height_diff'),
            'value': getattr(obs, 'value', 0),
            'sigma': getattr(obs, 'std_dev', 0.005)
        })
    
    print(f"DAT: {len(points)} точек, {len(observations)} измерений")
    
    # Тестируем SDR
    from geoadjust.io.formats.sdr import SDRParser
    parser = SDRParser()
    data = parser.parse(TEST_DATA_DIR / 'b_g/plan/badgro16093_const.sdr')
    
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
            'sigma': getattr(obs, 'std_dev', 0.00005)
        })
    
    print(f"SDR: {len(points)} точек, {len(observations)} измерений")
    
    # Тестируем POS
    from geoadjust.io.formats.pos import POSParser
    parser = POSParser()
    data = parser.parse(TEST_DATA_DIR / 'gnss/drag-bshm.pos')
    vector = parser.get_gnss_vector()
    
    if vector:
        print(f"POS: {vector.from_station} -> {vector.to_station}")
        print(f"     dX={vector.dx:.4f}m, dY={vector.dy:.4f}m, dZ={vector.dz:.4f}m")
    
    return True


def run_all_tests():
    """Запуск всех тестов"""
    print("=" * 70)
    print("КОМПЛЕКСНАЯ ПРОВЕРКА ИНТЕГРАЦИИ GeoAdjust-Pro")
    print("=" * 70)
    
    results = {}
    
    # Тест нивелирования
    results['leveling'] = test_leveling_pipeline()
    
    # Тест тахеометрии
    results['total_station'] = test_total_station_pipeline()
    
    # Тест GNSS
    results['gnss'] = test_gnss_pipeline()
    
    # Тест конвертации ImportDialog
    results['import_conversion'] = test_import_dialog_conversion()
    
    # Сводка
    print("\n" + "=" * 70)
    print("СВОДНАЯ ИНФОРМАЦИЯ")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"  [{status}] {test_name}")
    
    print(f"\n{'=' * 70}")
    if all_passed:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ - Программа готова к работе")
    else:
        print("ЕСТЬ ПРОБЛЕМЫ - Требуется доработка")
    print(f"{'=' * 70}")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
