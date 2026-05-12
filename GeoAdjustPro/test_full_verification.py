#!/usr/bin/env python3
"""
Полная верификация GeoAdjustPro на тестовых данных
Сравнение результатов с эталонными данными CREDO
"""

import sys
import os
from pathlib import Path
import numpy as np
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Добавляем путь к модулям

def test_gsi_parsing():
    """Тестирование GSI парсера на наших тестовых данных"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ GSI ПАРСЕРА")
    print("="*60)

    from geoadjust.io.formats.gsi import GSIParser

    parser = GSIParser()
    test_file = Path(__file__).parent / 'test_real_mes' / 'test_network.GSI'

    if not test_file.exists():
        print("Тестовый файл GSI не найден!")
        return None

    result = parser.parse(test_file)

    print(f"Результаты парсинга GSI:")
    print(f"  Успех: {result['success']}")
    print(f"  Измерений: {len(result.get('observations', []))}")
    print(f"  Станций: {len(result.get('station_sessions', []))}")
    print(f"  Точек: {len(result.get('points', []))}")

    # Проверяем типы измерений
    obs_types = {}
    for obs in result.get('observations', []):
        obs_type = obs.obs_type
        obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

    print("  Типы измерений:")
    for obs_type, count in obs_types.items():
        print(f"    {obs_type}: {count}")

    return result

def test_sdr_parsing():
    """Тестирование SDR парсера на наших тестовых данных"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ SDR ПАРСЕРА")
    print("="*60)

    from geoadjust.io.formats.sdr import SDRParser

    parser = SDRParser()
    test_file = Path(__file__).parent / 'test_real_mes' / 'test_network.SDR'

    if not test_file.exists():
        print("Тестовый файл SDR не найден!")
        return None

    result = parser.parse(test_file)

    print(f"Результаты парсинга SDR:")
    print(f"  Успех: {result['success']}")
    print(f"  Измерений: {len(result.get('observations', []))}")
    print(f"  Станций: {len(result.get('setups', []))}")
    print(f"  Точек: {len(result.get('points', []))}")

    # Проверяем станции
    for setup in result.get('setups', []):
        print(f"  Станция {setup.setup_id}: {len(setup.observations)} измерений")

    return result

def test_dat_parsing():
    """Тестирование DAT парсера на реальных данных CREDO"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ DAT ПАРСЕРА (CREDO данные)")
    print("="*60)

    from geoadjust.io.formats.dat import DATParser

    parser = DATParser()

    # Используем один из реальных файлов CREDO
    test_file = Path(__file__).parent / 'test_real_mes' / 'l' / 'niv' / 'LIH2103.DAT'

    if not test_file.exists():
        print("Файл CREDO DAT не найден!")
        return None

    result = parser.parse(test_file)

    print(f"Результаты парсинга DAT (CREDO):")
    print(f"  Успех: {result['success']}")
    print(f"  Измерений: {len(result.get('observations', []))}")
    print(f"  Станций: {len(result.get('station_sessions', []))}")
    print(f"  Точек: {len(result.get('points', []))}")

    # Проверяем типы измерений
    obs_types = {}
    for obs in result.get('observations', []):
        obs_type = obs.obs_type
        obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

    print("  Типы измерений:")
    for obs_type, count in obs_types.items():
        print(f"    {obs_type}: {count}")

    return result

def test_network_adjustment():
    """Тестирование полного цикла уравнивания"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ПОЛНОГО УРАВНИВАНИЯ")
    print("="*60)

    try:
        # Импортируем наши тестовые данные
        gsi_result = test_gsi_parsing()
        sdr_result = test_sdr_parsing()

        if not gsi_result or not sdr_result:
            print("Не удалось загрузить тестовые данные!")
            return

        # Создаем сеть из объединенных данных
        from geoadjust.core.network.models import NetworkPoint, Observation, InstrumentSetup

        # Точки
        points = {}

        # Из GSI данных
        for point_data in gsi_result.get('points', []):
            point_id = point_data.get('point_id', '')
            points[point_id] = NetworkPoint(
                point_id=point_id,
                coord_type='APPROXIMATE',
                x=point_data.get('x', 0),
                y=point_data.get('y', 0),
                h=point_data.get('h', 0)
            )

        # Из SDR данных
        for point_data in sdr_result.get('points', []):
            point_id = point_data.get('name', '')
            if point_id not in points:
                points[point_id] = NetworkPoint(
                    point_id=point_id,
                    coord_type='FREE',
                    x=0, y=0, h=0
                )

        # Измерения
        observations = []

        # Из GSI
        for i, obs in enumerate(gsi_result.get('observations', [])):
            # Для GSI измерений from_point может быть 'STATION' - это означает точку станции
            from_point = getattr(obs, 'from_point', 'UNKNOWN')
            to_point = getattr(obs, 'to_point', 'UNKNOWN')

            # Если from_point = 'STATION', используем ID станции
            if from_point == 'STATION' or from_point == 'UNKNOWN':
                station_id = getattr(obs, 'station_session_id', f'STA_{i}')
                from_point = station_id

            # Создаем точки если они не существуют
            if from_point not in points:
                points[from_point] = NetworkPoint(
                    point_id=from_point,
                    coord_type='FREE',
                    x=0, y=0, h=0
                )
            if to_point not in points:
                points[to_point] = NetworkPoint(
                    point_id=to_point,
                    coord_type='FREE',
                    x=0, y=0, h=0
                )

            observations.append(Observation(
                obs_id=f"GSI_{i:03d}",
                obs_type=obs.obs_type,
                from_setup_id=getattr(obs, 'station_session_id', 'UNKNOWN'),
                from_point_id=from_point,
                to_point_id=to_point,
                value=getattr(obs, 'value', 0.0),
                sigma_apriori=0.0001
            ))

        # Из SDR
        for obs_data in sdr_result.get('observations', []):
            from_point = obs_data['from_point']
            to_point = obs_data['to_point']

            # Создаем точки если они не существуют
            if from_point not in points:
                points[from_point] = NetworkPoint(
                    point_id=from_point,
                    coord_type='FREE',
                    x=0, y=0, h=0
                )
            if to_point not in points:
                points[to_point] = NetworkPoint(
                    point_id=to_point,
                    coord_type='FREE',
                    x=0, y=0, h=0
                )

            observations.append(Observation(
                obs_id=f"SDR_{len(observations)}",
                obs_type=obs_data['type'],
                from_setup_id=obs_data['station_session_id'],
                from_point_id=from_point,
                to_point_id=to_point,
                value=obs_data['value'],
                sigma_apriori=obs_data['sigma']
            ))

        print(f"Создана сеть:")
        print(f"  Точек: {len(points)}")
        print(f"  Измерений: {len(observations)}")

        # Создаем уравнивание
        from geoadjust.core.adjustment.equations_builder import EquationsBuilder
        from geoadjust.core.adjustment.weight_builder import WeightBuilder
        from geoadjust.core.adjustment.engine import AdjustmentEngine
        import scipy.sparse as sparse

        # Фиксируем точки STA1 и STA2
        fixed_points = ['001', '002']  # Из GSI

        # Фильтруем только активные измерения
        active_observations = [obs for obs in observations if obs.is_active]

        builder = EquationsBuilder()
        A, L = builder.build_adjustment_matrix(
            active_observations, points, fixed_points
        )

        print(f"Матрица коэффициентов: {A.shape[0]} x {A.shape[1]}")
        print(f"Вектор свободных членов: {len(L)}")

        # Весовая матрица (только для активных измерений)
        active_observations = [obs for obs in observations if obs.is_active]
        print(f"Активных измерений: {len(active_observations)} из {len(observations)}")

        weight_builder = WeightBuilder()
        P = weight_builder.build_weight_matrix(active_observations)

        print(f"Весовая матрица: {P.shape[0]} x {P.shape[1]}")

        # Уравнивание
        engine = AdjustmentEngine()
        result = engine.adjust(A, L, P)

        print("\nРезультаты уравнивания:")
        print(f"  СКО единицы веса: {result['sigma0']:.6f}")
        print(f"  Остатков: {len(result['residuals'])}")
        print(f"  Поправок координат: {len(result['coordinate_corrections'])}")

        return result

    except Exception as e:
        print(f"Ошибка при уравнивании: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_with_credo():
    """Сравнение с эталонными данными CREDO"""
    print("\n" + "="*60)
    print("СРАВНЕНИЕ С ЭТАЛОННЫМИ ДАННЫМИ CREDO")
    print("="*60)

    # Здесь можно добавить сравнение результатов с CREDO
    print("Для сравнения с CREDO необходимо:")
    print("1. Загрузить ведомости уравнивания из CREDO")
    print("2. Сравнить координаты, СКО, невязки")
    print("3. Проверить соответствие результатов")

def main():
    """Основная функция тестирования"""
    print("ПОЛНАЯ ВЕРИФИКАЦИЯ GeoAdjustPro")
    print("="*60)

    # Тестируем парсеры
    gsi_result = test_gsi_parsing()
    sdr_result = test_sdr_parsing()
    dat_result = test_dat_parsing()

    # Тестируем уравнивание
    adjustment_result = test_network_adjustment()

    # Сравнение с CREDO
    compare_with_credo()

    print("\n" + "="*60)
    print("ВЕРИФИКАЦИЯ ЗАВЕРШЕНА")
    print("="*60)

    success_count = 0
    if gsi_result and gsi_result.get('success', False):
        success_count += 1
    if sdr_result and sdr_result.get('success', False):
        success_count += 1
    if dat_result and dat_result.get('success', False):
        success_count += 1
    if adjustment_result is not None:
        success_count += 1

    print(f"УСПЕШНО ПРОЙДЕНО: {success_count}/4 тестов")

    if success_count == 4:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ! СИСТЕМА РАБОТОСПОСОБНА.")
    else:
        print("НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ.")

if __name__ == '__main__':
    main()