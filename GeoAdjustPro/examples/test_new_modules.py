#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестовый пример использования новых модулей GeoAdjust-Pro

Этот скрипт демонстрирует работу:
1. EquationsBuilder - построение матрицы коэффициентов уравнений поправок
2. WeightBuilder - формирование весовой матрицы
3. ProcessingPipeline - полный цикл обработки
"""

import sys
import numpy as np

# Добавляем путь к модулям

from geoadjust.core.network.models import NetworkPoint, Observation
from geoadjust.core.adjustment.instruments import Instrument


def test_equations_builder():
    """Тестирование EquationsBuilder"""
    print("=" * 80)
    print("ТЕСТ 1: EquationsBuilder - Построение матрицы коэффициентов")
    print("=" * 80)
    
    from geoadjust.core.adjustment.equations_builder import EquationsBuilder
    
    # Создаём тестовую сеть из 3 пунктов
    points = {
        'P1': NetworkPoint(point_id='P1', coord_type='FIXED', x=0.0, y=0.0, h=None),
        'P2': NetworkPoint(point_id='P2', coord_type='FREE', x=100.0, y=0.0, h=None),
        'P3': NetworkPoint(point_id='P3', coord_type='FREE', x=50.0, y=86.6, h=None),
    }
    
    # Создаём измерения
    observations = [
        # Направления с P1
        Observation(
            obs_id='dir_1', obs_type='direction',
            from_point='P1', to_point='P2',
            value=0.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        Observation(
            obs_id='dir_2', obs_type='direction',
            from_point='P1', to_point='P3',
            value=60.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        # Расстояния
        Observation(
            obs_id='dist_1', obs_type='distance',
            from_point='P1', to_point='P2',
            value=100.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        Observation(
            obs_id='dist_2', obs_type='distance',
            from_point='P1', to_point='P3',
            value=100.0, instrument_name='total_station',
            sigma_apriori=None
        ),
    ]
    
    # Построение матрицы
    builder = EquationsBuilder()
    A, L = builder.build_adjustment_matrix(
        observations=observations,
        points=points,
        fixed_points=['P1']
    )
    
    print(f"\n✓ Матрица А: {A.shape[0]}×{A.shape[1]}")
    print(f"✓ Вектор L: {len(L)}")
    print(f"✓ Число ненулевых элементов: {A.nnz}")
    print(f"\nМатрица А (плотное представление):\n{A.toarray()}")
    print(f"\nВектор L:\n{L}")
    
    return True


def test_weight_builder():
    """Тестирование WeightBuilder"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: WeightBuilder - Формирование весовой матрицы")
    print("=" * 80)
    
    from geoadjust.core.adjustment.weight_builder import WeightBuilder
    
    # Создаём библиотеку приборов
    instrument_library = {
        'total_station': Instrument(
            angular_accuracy=5.0,  # 5 секунд
            distance_accuracy_a=2.0,  # 2 мм
            distance_accuracy_b=2.0,  # 2 ppm
            centering_error=1.0,  # 1 мм
            target_centering_error=1.0  # 1 мм
        )
    }
    
    # Создаём измерения
    observations = [
        Observation(
            obs_id='dir_1', obs_type='direction',
            from_point='P1', to_point='P2',
            value=0.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        Observation(
            obs_id='dist_1', obs_type='distance',
            from_point='P1', to_point='P2',
            value=100.0, instrument_name='total_station',
            sigma_apriori=None
        ),
    ]
    
    # Построение весовой матрицы
    weight_builder = WeightBuilder(instrument_library)
    P = weight_builder.build_weight_matrix(observations)
    
    print(f"\n✓ Весовая матрица P: {P.shape[0]}×{P.shape[1]}")
    print(f"✓ Диагональные элементы (веса): {P.diagonal()}")
    
    return True


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ НОВЫХ МОДУЛЕЙ GEOADJUST-PRO")
    print("=" * 80 + "\n")
    
    # Тест 1: EquationsBuilder
    test1_passed = test_equations_builder()
    
    # Тест 2: WeightBuilder
    test2_passed = test_weight_builder()
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"✓ EquationsBuilder: {'PASS' if test1_passed else 'FAIL'}")
    print(f"✓ WeightBuilder: {'PASS' if test2_passed else 'FAIL'}")
    print("=" * 80 + "\n")
