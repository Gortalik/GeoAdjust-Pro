#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка что возвращает GSI парсер
"""

import sys
from pathlib import Path


from geoadjust.io.formats.gsi import GSIParser

parser = GSIParser()
result = parser.parse(Path("test_real_mes/b_g/niv/GRO2209.GSI"))

print("Результаты GSI парсера:")
print(f"Точек: {len(result['points'])}")
print(f"Измерений: {len(result['observations'])}")
print(f"Сессий: {len(result['station_sessions'])}")
print(f"Ходов: {len(result.get('leveling_courses', []))}")

# Проверим типы измерений
obs_types = {}
for obs in result['observations']:
    obs_type = obs.obs_type if hasattr(obs, 'obs_type') else obs.get('obs_type', 'unknown')
    obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

print(f"Типы измерений: {obs_types}")

# Проверим первые 5 измерений
print("\nПервые 5 измерений:")
for i, obs in enumerate(result['observations'][:5]):
    if hasattr(obs, 'obs_type'):
        print(f"  {obs.obs_type}: {obs.from_point} -> {obs.to_point}")
    else:
        print(f"  {obs.get('obs_type')}: {obs.get('from_point')} -> {obs.get('to_point')}")

# Проверим ходы
courses = result.get('leveling_courses', [])
if courses:
    print(f"\nХоды: {len(courses)}")
    for i, course in enumerate(courses[:3]):
        print(f"Ход {i+1}: {course.get('course_id', 'unknown')}")
        print(f"  Станции: {course.get('stations', [])}")
        print(f"  Измерения: {len(course.get('measurements', []))}")
else:
    print("\nХоды: НЕТ")

# Проверим что в leveling_courses
print(f"\nleveling_courses в результате: {result.get('leveling_courses', 'НЕТ')}")