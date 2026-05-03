#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полный тест уравнивания с проверкой СКП
"""

import sys
import os
import numpy as np
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser
from geo_adjust_pro import NetworkPoint, Observation
from geo_adjust_pro.engine import GeoAdjustEngine

print("Полный тест уравнивания с проверкой СКП...")

# Парсим SDR файл
parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

points = result.get('points', [])
observations = result.get('observations', [])

print(f"Загружено точек: {len(points)}")
print(f"Загружено наблюдений: {len(observations)}")

# Преобразуем точки в NetworkPoint объекты
points_dict = {}
for p in points:
    points_dict[p['point_id']] = NetworkPoint(
        id=p['point_id'],
        x=p.get('x'),
        y=p.get('y'),
        z=p.get('h'),
        plan_status=p.get('plan_status', 'working'),
        height_status=p.get('height_status', 'working')
    )

# Преобразуем наблюдения (возьмем только направления для простоты)
simple_observations = []
for obs in observations[:100]:  # Возьмем первые 100 наблюдений
    if hasattr(obs, 'horizontal_angle') and obs.horizontal_angle is not None:
        simple_obs = Observation(
            id=f"obs_{len(simple_observations)}",
            type='direction',
            from_point=obs.from_point_id,
            to_point=obs.to_point_id,
            value=obs.horizontal_angle
        )
        simple_observations.append(simple_obs)

print(f"Используем {len(simple_observations)} направлений")

# Создаем движок и тестируем
engine = GeoAdjustEngine()
engine.load_network(points_dict, simple_observations)

print("\nТестируем строгое уравнивание...")
result_plan = engine.adjust_plan(points_dict, simple_observations, free_adjustment=False)

print(f"Успех: {result_plan.success}")
print(f"СКП: {result_plan.sigma0:.6f} мм")
print(f"Итераций: {result_plan.iterations}")
print(f"Остатков: {len(result_plan.residuals)}")

# Проверим, что СКП рассчитывается правильно
if result_plan.residuals:
    residuals = np.array(result_plan.residuals)
    print(f"Средний остаток: {np.mean(np.abs(residuals)):.6f} угл.сек")
    print(f"Макс остаток: {np.max(np.abs(residuals)):.6f} угл.сек")

# Теперь добавим искусственную ошибку и проверим СКП
print("\nТестируем с искусственной ошибкой...")
modified_observations = simple_observations.copy()
if modified_observations:
    # Добавим ошибку в первое наблюдение
    modified_observations[0] = Observation(
        id=modified_observations[0].id,
        type=modified_observations[0].type,
        from_point=modified_observations[0].from_point,
        to_point=modified_observations[0].to_point,
        value=modified_observations[0].value + 10.0  # Добавим 10 угл.сек ошибки
    )

    result_with_error = engine.adjust_plan(points_dict, modified_observations, free_adjustment=False)
    print(f"СКП с ошибкой: {result_with_error.sigma0:.6f} мм")

    if result_with_error.residuals:
        residuals_error = np.array(result_with_error.residuals)
        print(f"Средний остаток с ошибкой: {np.mean(np.abs(residuals_error)):.6f} угл.сек")

print("\nТест завершен!")