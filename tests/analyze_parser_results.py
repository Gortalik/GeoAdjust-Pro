#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ результатов GSI парсера
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser

def analyze_parser_results():
    """Анализ результатов парсера"""
    parser = GSIParser()
    result = parser.parse(Path("test_real_mes/b_g/niv/GRO2209.GSI"))
    
    print("Анализ результатов GSI парсера:")
    print(f"Точек: {len(result['points'])}")
    print(f"Измерений: {len(result['observations'])}")
    print(f"Ходов: {len(result.get('leveling_courses', []))}")
    
    # Анализ точек
    points_by_type = {}
    for point in result['points']:
        pt = point.get('point_type', 'unknown')
        if pt not in points_by_type:
            points_by_type[pt] = []
        points_by_type[pt].append(point.get('point_id'))
    
    print("\nТочки по типам:")
    for pt, points in points_by_type.items():
        print(f"  {pt}: {len(points)} точек")
        print(f"    Примеры: {sorted(points)[:10]}")
    
    # Анализ измерений
    measurements_by_type = {}
    for obs in result['observations']:
        obs_type = obs.obs_type if hasattr(obs, 'obs_type') else obs.get('obs_type', 'unknown')
        if obs_type not in measurements_by_type:
            measurements_by_type[obs_type] = []
        measurements_by_type[obs_type].append(obs)
    
    print("\nИзмерения по типам:")
    for obs_type, obs_list in measurements_by_type.items():
        print(f"  {obs_type}: {len(obs_list)} измерений")
    
    # Анализ ходов
    courses = result.get('leveling_courses', [])
    print(f"\nХоды: {len(courses)}")
    
    if courses:
        # Группируем ходы по количеству станций
        course_lengths = {}
        for course in courses:
            stations = course.get('stations', [])
            length = len(stations)
            if length not in course_lengths:
                course_lengths[length] = []
            course_lengths[length].append(course)
        
        print("Ходы по количеству станций:")
        for length, course_list in sorted(course_lengths.items()):
            print(f"  {length} станций: {len(course_list)} ходов")
            
            # Показываем примеры
            if length <= 3:  # Показываем только короткие ходы
                for course in course_list[:3]:
                    stations = course.get('stations', [])
                    measurements = course.get('measurements', [])
                    print(f"    Ход: {stations} -> {len(measurements)} измерений")
    
    # Ищем потенциальные боковые измерения
    print("\nПоиск потенциальных боковых измерений:")
    
    # Боковое нивелирование может быть определено как измерения к точкам,
    # которые не являются станциями в ходах
    
    station_points = set()
    target_points = set()
    
    for course in courses:
        stations = course.get('stations', [])
        station_points.update(stations)
        
        for measurement in course.get('measurements', []):
            target_points.add(measurement.get('to_point', ''))
    
    all_points = set(p.get('point_id') for p in result['points'])
    
    # Точки, которые являются целями, но не станциями
    potential_intermediate = target_points - station_points
    
    print(f"Станций в ходах: {len(station_points)}")
    print(f"Целей в измерениях: {len(target_points)}")
    print(f"Потенциальных промежуточных точек: {len(potential_intermediate)}")
    
    if potential_intermediate:
        print(f"Примеры промежуточных точек: {sorted(list(potential_intermediate))[:10]}")

if __name__ == "__main__":
    analyze_parser_results()