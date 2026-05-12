#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка итоговых результатов GSI парсера
"""

import sys
from pathlib import Path


from geoadjust.io.formats.gsi import GSIParser

def check_final_results():
    parser = GSIParser()
    result = parser.parse(Path("test_real_mes/b_g/niv/GRO2209.GSI"))
    
    print("=== ИТОГОВЫЕ РЕЗУЛЬТАТЫ GSI ПАРСЕРА ===")
    print(f"Точек: {len(result['points'])}")
    print(f"Измерений: {len(result['observations'])}")
    print(f"Ходов: {len(result.get('leveling_courses', []))}")

    # Подсчет типов измерений
    obs_types = {}
    for obs in result['observations']:
        obs_type = obs.obs_type if hasattr(obs, 'obs_type') else obs.get('obs_type', 'unknown')
        obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

    print(f"\nТипы измерений:")
    for obs_type, count in obs_types.items():
        print(f"   {obs_type}: {count}")

    # Проверка ходов
    courses = result.get('leveling_courses', [])
    if courses:
        print(f"\nХоды:")
        for i, course in enumerate(courses[:5]):
            stations = course.get('stations', [])
            measurements = course.get('measurements', [])
            print(f"   Ход {course['course_id']}: {len(stations)} станций, {len(measurements)} измерений")

    # Проверка что все данные корректны
    leveling_obs = [obs for obs in result['observations'] if hasattr(obs, 'obs_type') and obs.obs_type == 'leveling_height_diff']
    intermediate_obs = [obs for obs in result['observations'] if hasattr(obs, 'obs_type') and obs.obs_type == 'intermediate_leveling']

    print("\nПРОВЕРКА:")
    print(f"   Основное нивелирование: {len(leveling_obs)} измерений")
    print(f"   Боковое нивелирование: {len(intermediate_obs)} измерений")
    print(f"   Всего станций: {len([p for p in result['points'] if p.get('point_type') == 'station'])}")
    print(f"   Всего целей: {len([p for p in result['points'] if p.get('point_type') == 'target'])}")
    
    return result

if __name__ == "__main__":
    check_final_results()