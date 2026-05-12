#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест уравнивания с реальными SDR данными
"""

import sys
import os

from geoadjust.io.formats.sdr import SDRParser
from geo_adjust_pro.engine import GeoAdjustEngine

print("Тест уравнивания с SDR данными...")

# Парсим SDR файл
parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

points = result.get('points', [])
observations = result.get('observations', [])

print(f"Загружено точек: {len(points)}")
print(f"Загружено наблюдений: {len(observations)}")

# Посмотрим на статусы точек
initial_points = sum(1 for p in points if p.get('plan_status') == 'initial')
working_points = sum(1 for p in points if p.get('plan_status') == 'working')

print(f"Точек с начальными координатами: {initial_points}")
print(f"Рабочих точек: {working_points}")

# Посмотрим на типы наблюдений
obs_types = {}
for obs in observations:
    obs_type = getattr(obs, 'obs_type', 'unknown')
    obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

print(f"Типы наблюдений: {obs_types}")

# Преобразуем данные для движка
from geo_adjust_pro import NetworkPoint
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

# Преобразуем CombinedObservation в обычные Observation
simple_observations = []
for obs in observations:
    # Для теста возьмем только первые 10 наблюдений
    if len(simple_observations) >= 10:
        break

    simple_obs = type('SimpleObs', (), {
        'type': 'direction',  # Преобразуем combined в direction
        'from_point': obs.from_point_id,
        'to_point': obs.to_point_id,
        'value': obs.horizontal_angle,  # Используем горизонтальный угол
        'distance': obs.slope_distance if hasattr(obs, 'slope_distance') else None
    })()
    simple_observations.append(simple_obs)

print(f"Используем {len(simple_observations)} наблюдений для теста")

# Создаем движок и загружаем данные
engine = GeoAdjustEngine()
engine.load_network(points_dict, simple_observations)

print("\nЗапуск уравнивания плана...")
result_plan = engine.adjust_plan(points_dict, simple_observations, free_adjustment=False)

print(f"Результат: {result_plan.success}")
print(f"СКП: {result_plan.sigma0:.6f} мм")
print(f"Итераций: {result_plan.iterations}")

if result_plan.points_stats:
    print("Первые 3 результата:")
    for i, (pid, stats) in enumerate(sorted(result_plan.points_stats.items())[:3]):
        print(f"  {pid}: X={stats['x']:.3f}, Y={stats['y']:.3f}")

# Проверяем, какие наблюдения используются в уравнивании
print("\nПроверка использованных наблюдений...")
dist_count = sum(1 for obs in observations if hasattr(obs, 'slope_distance') and obs.slope_distance is not None)
dir_count = sum(1 for obs in observations if hasattr(obs, 'horizontal_angle') and obs.horizontal_angle is not None)

print(f"Наблюдений с расстояниями: {dist_count}")
print(f"Наблюдений с направлениями: {dir_count}")