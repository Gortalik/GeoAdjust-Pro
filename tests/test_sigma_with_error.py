#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест с искусственной ошибкой для проверки СКП
"""

import sys
import os
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser
from geo_adjust_pro import NetworkPoint, Observation
from geo_adjust_pro.engine import GeoAdjustEngine
import numpy as np

print("Тест СКП с искусственной ошибкой...")

# Парсим SDR файл
parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

points = result.get('points', [])
observations = result.get('observations', [])

# Преобразуем точки
points_dict = {}
for p in points:
    points_dict[p['point_id']] = NetworkPoint(
        id=p['point_id'],
        x=p.get('x'),
        y=p.get('y'),
        z=p.get('h'),
        plan_status='working',  # Все рабочие
        height_status='working'
    )

# Создаем наблюдения расстояний
simple_observations = []
for obs in observations[:20]:  # Возьмем 20 наблюдений
    if hasattr(obs, 'slope_distance') and obs.slope_distance is not None:
        simple_obs = Observation(
            id=f"obs_{len(simple_observations)}",
            type='distance',
            from_point=obs.from_point_id,
            to_point=obs.to_point_id,
            value=obs.slope_distance
        )
        simple_observations.append(simple_obs)

print(f"Используем {len(simple_observations)} расстояний")

if simple_observations:
    # Тест без ошибки
    engine = GeoAdjustEngine()
    engine.load_network(points_dict, simple_observations)

    print("\nУравнивание без ошибки...")
    result_clean = engine.adjust_plan(points_dict, simple_observations, free_adjustment=False)
    print(f"СКП без ошибки: {result_clean.sigma0:.6f} мм")

    # Тест с ошибкой
    print("\nУравнивание с ошибкой...")
    modified_observations = simple_observations.copy()
    if modified_observations:
        # Добавим ошибку 1 мм в первое расстояние
        modified_observations[0] = Observation(
            id=modified_observations[0].id,
            type=modified_observations[0].type,
            from_point=modified_observations[0].from_point,
            to_point=modified_observations[0].to_point,
            value=modified_observations[0].value + 0.001  # +1 мм
        )

        result_with_error = engine.adjust_plan(points_dict, modified_observations, free_adjustment=False)
        print(f"СКП с ошибкой: {result_with_error.sigma0:.6f} мм")

        # Сравнение остатков
        if result_clean.residuals and result_with_error.residuals:
            clean_residuals = np.array(result_clean.residuals)
            error_residuals = np.array(result_with_error.residuals)

            print(f"Макс остаток без ошибки: {np.max(np.abs(clean_residuals))*1000:.3f} мм")
            print(f"Макс остаток с ошибкой: {np.max(np.abs(error_residuals))*1000:.3f} мм")

            # Ожидаемое увеличение СКП
            expected_sigma_increase = result_with_error.sigma0 / max(result_clean.sigma0, 1e-10)
            print(f"Увеличение СКП: {expected_sigma_increase:.2f} раз")

print("\nТест завершен!")