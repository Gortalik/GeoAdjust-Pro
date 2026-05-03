#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка типа наблюдений в SDR данных
"""

import sys
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser

print("Проверка типов наблюдений в SDR файле...")

parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

observations = result.get('observations', [])

print(f"Всего наблюдений: {len(observations)}")

# Анализ типов наблюдений
obs_types = {}
for obs in observations[:10]:  # Первые 10 для примера
    obs_type = type(obs).__name__
    print(f"Тип объекта: {obs_type}")

    # Проверяем атрибуты
    if hasattr(obs, 'obs_type'):
        print(f"  obs_type: {obs.obs_type}")
    if hasattr(obs, 'horizontal_angle'):
        print(f"  horizontal_angle: {obs.horizontal_angle}")
    if hasattr(obs, 'slope_distance'):
        print(f"  slope_distance: {obs.slope_distance}")
    if hasattr(obs, 'from_point_id'):
        print(f"  from_point: {obs.from_point_id}")
    if hasattr(obs, 'to_point_id'):
        print(f"  to_point: {obs.to_point_id}")
    print()

# Статистика по типам
obs_type_counts = {}
for obs in observations:
    obs_type = getattr(obs, 'obs_type', 'unknown')
    obs_type_counts[obs_type] = obs_type_counts.get(obs_type, 0) + 1

print("Статистика типов наблюдений:")
for obs_type, count in obs_type_counts.items():
    print(f"  {obs_type}: {count}")

# Проверяем, есть ли CombinedObservation
combined_count = sum(1 for obs in observations if 'Combined' in type(obs).__name__)
print(f"\nCombinedObservation: {combined_count}")

# Проверяем, есть ли обычные Observation
from geoadjust.core.network.models import Observation
simple_count = sum(1 for obs in observations if isinstance(obs, Observation))
print(f"Простые Observation: {simple_count}")

print("\nПроверка завершена.")