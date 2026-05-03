#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностика проблемы с уравниванием
"""

import sys
import os
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser
from geo_adjust_pro import NetworkPoint, Observation
from geo_adjust_pro.engine import GeoAdjustEngine
import numpy as np

print("Диагностика проблемы с уравниванием...")

# Парсим SDR файл
parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

points = result.get('points', [])
observations = result.get('observations', [])

print(f"Загружено точек: {len(points)}")
print(f"Загружено наблюдений: {len(observations)}")

# Преобразуем точки
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

# Проверим статусы точек
initial_count = sum(1 for p in points_dict.values() if p.plan_status == 'initial')
working_count = sum(1 for p in points_dict.values() if p.plan_status == 'working')
fixed_count = sum(1 for p in points_dict.values() if p.plan_status == 'fixed')

print(f"Точек initial: {initial_count}")
print(f"Точек working: {working_count}")
print(f"Точек fixed: {fixed_count}")

# Создадим простое уравнивание только с расстояниями
simple_observations = []
for obs in observations[:50]:  # Возьмем первые 50 наблюдений
    if hasattr(obs, 'slope_distance') and obs.slope_distance is not None:
        simple_obs = Observation(
            id=f"obs_{len(simple_observations)}",
            type='distance',
            from_point=obs.from_point_id,
            to_point=obs.to_point_id,
            value=obs.slope_distance
        )
        simple_observations.append(simple_obs)

print(f"Создано {len(simple_observations)} наблюдений расстояний")

if simple_observations:
    # Создадим движок
    engine = GeoAdjustEngine()
    engine.load_network(points_dict, simple_observations)

    print("Запуск уравнивания с расстояниями...")
    result_plan = engine.adjust_plan(points_dict, simple_observations, free_adjustment=False)

    print(f"Успех: {result_plan.success}")
    if not result_plan.success:
        print(f"Ошибка: {result_plan.message}")

    print(f"СКП: {result_plan.sigma0:.6f} мм")
    print(f"Итераций: {result_plan.iterations}")

else:
    print("Нет подходящих наблюдений для уравнивания!")

# Проверим геометрию сети
print("\nПроверка геометрии сети...")
if points:
    coords = []
    for p in points:
        if p.get('x') is not None and p.get('y') is not None:
            coords.append((p['x'], p['y']))

    if coords:
        coords = np.array(coords)
        print(f"Диапазон X: {coords[:, 0].min():.1f} - {coords[:, 0].max():.1f}")
        print(f"Диапазон Y: {coords[:, 1].min():.1f} - {coords[:, 1].max():.1f}")
        print(f"Среднее расстояние между точками: ~{np.mean(np.linalg.norm(coords[:, None] - coords, axis=2)[np.triu_indices(len(coords), k=1)]):.1f} м")
    else:
        print("Нет координат для анализа геометрии!")