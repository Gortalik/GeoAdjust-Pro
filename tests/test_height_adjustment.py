#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка обработки CombinedObservation в высотном уравнивании
"""

import sys

from geoadjust.io.formats.gsi import GSIParser

print("Проверка GSI наблюдений для высот...")

parser = GSIParser()
result = parser.parse('test_real_mes/s5/niv/DOM0112 (1).GSI')

observations = result.get('observations', [])

print(f"Всего наблюдений: {len(observations)}")

leveling_count = 0
for obs in observations[:20]:  # Первые 20 для примера
    if 'leveling' in getattr(obs, 'obs_type', ''):
        leveling_count += 1
        print(f"Нивелирное наблюдение: {obs.obs_type}")
        print(f"  От: {getattr(obs, 'from_point', 'нет')}")
        print(f"  К: {getattr(obs, 'to_point', 'нет')}")
        print(f"  Значение: {getattr(obs, 'value', 'нет')}")
        print()

print(f"Всего нивелирных наблюдений: {leveling_count}")

# Проверим, что происходит в движке
print("\nПроверка работы движка с высотами...")

from geo_adjust_pro import NetworkPoint, Observation
from geo_adjust_pro.engine import GeoAdjustEngine

# Создаем простой тест
points = {
    'A': NetworkPoint(id='A', x=0, y=0, z=100, plan_status='working', height_status='working'),
    'B': NetworkPoint(id='B', x=100, y=0, z=100.5, plan_status='working', height_status='working'),
}

observations_simple = [
    Observation(id='1', type='leveling_height_diff', from_point='A', to_point='B', value=0.5)
]

engine = GeoAdjustEngine()
engine.load_network(points, observations_simple)

print("Тест простого высотного уравнивания...")
result = engine.adjust_heights(free_adjustment=True)
print(f"Результат: {result.success}, СКО: {result.sigma0:.6f}")

if result.points_stats:
    for pid, stats in result.points_stats.items():
        print(f"  {pid}: H={stats['height']:.3f} м")

print("\nТест завершен.")