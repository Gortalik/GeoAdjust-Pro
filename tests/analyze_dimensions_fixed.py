#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ размерности системы уравнивания
"""

import sys
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser
from geo_adjust_pro import NetworkPoint, Observation
from geo_adjust_pro.engine import GeoAdjustEngine

print("Анализ размерности системы...")

# Парсим SDR файл
parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

points = result.get('points', [])
observations = result.get('observations', [])

# Преобразуем точки
points_dict = {}
working_points = 0
for p in points:
    points_dict[p['point_id']] = NetworkPoint(
        id=p['point_id'],
        x=p.get('x'),
        y=p.get('y'),
        z=p.get('h'),
        plan_status='working',
        height_status='working'
    )
    working_points += 1

print(f"Всего точек: {len(points)}")
print(f"Рабочих точек: {working_points}")
print(f"Неизвестных параметров плана: {working_points * 2}")

# Создаем наблюдения расстояний
simple_observations = []
for obs in observations:
    if hasattr(obs, 'slope_distance') and obs.slope_distance is not None:
        simple_obs = Observation(
            id=f"obs_{len(simple_observations)}",
            type='distance',
            from_point=obs.from_point_id,
            to_point=obs.to_point_id,
            value=obs.slope_distance
        )
        simple_observations.append(simple_obs)

print(f"Наблюдений расстояний: {len(simple_observations)}")

# Расчет степеней свободы
unknowns = working_points * 2
observations_count = len(simple_observations)
degrees_of_freedom = observations_count - unknowns

print(f"Неизвестные параметры: {unknowns}")
print(f"Наблюдения: {observations_count}")
print(f"Степени свободы: {degrees_of_freedom}")

if degrees_of_freedom < 0:
    print("СИСТЕМА НЕДООПРЕДЕЛЕНА!")
    print(f"Нужно еще {-degrees_of_freedom} наблюдений")
elif degrees_of_freedom == 0:
    print("СИСТЕМА ОПРЕДЕЛЕНА (нулевые степени свободы)")
else:
    print("СИСТЕМА ПЕРЕОПРЕДЕЛЕНА")
    print(f"Избыточность: {degrees_of_freedom} наблюдений")

# Проверим свободное уравнивание
print("Тест свободного уравнивания...")
engine = GeoAdjustEngine()
engine.load_network(points_dict, simple_observations)

result_free = engine.adjust_plan(points_dict, simple_observations, free_adjustment=True)
print(f"Свободное уравнивание - успех: {result_free.success}")
print(f"СКП: {result_free.sigma0:.6f} мм")
print(f"Степени свободы для свободного: {observations_count - unknowns + 3}")