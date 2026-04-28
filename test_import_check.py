#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест импорта GSI и проверки данных без GUI
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser

def test_gsi_import():
    """Тест импорта GSI файла и проверки данных"""
    print("=== ТЕСТ ИМПОРТА GSI ===")

    # Парсим файл
    parser = GSIParser()
    file_path = Path("test_real_mes/b_g/niv/GRO2209.GSI")
    result = parser.parse(file_path)

    print(f"Парсер вернул: points={len(result['points'])}, observations={len(result['observations'])}, courses={len(result.get('leveling_courses', []))}")

    # Создаем проект (dict like main_window.current_project)
    project = {}
    project['name'] = "Test Project"
    project['points'] = []
    project['observations'] = []

    # Добавляем точки
    for point in result['points']:
        project['points'].append(point)

    # Добавляем измерения
    for obs in result['observations']:
        # Конвертируем GSIObservation в dict
        obs_dict = {
            'obs_type': obs.obs_type,
            'from_point': obs.from_point,
            'to_point': obs.to_point,
            'value': obs.value,
            'station_session_id': obs.station_session_id,
            'instrument_height': obs.instrument_height,
            'target_height': obs.target_height,
            'line_number': obs.line_number
        }
        project['observations'].append(obs_dict)

    # Добавляем preprocessing_result
    converted_courses = []
    for course in result.get('leveling_courses', []):
        converted_course = {
            'course_id': course['course_id'],
            'section_number': course.get('section_number', 1),
            'stations': course.get('stations', []),
            'measurements': course.get('measurements', [])
        }
        converted_courses.append(converted_course)

    project['preprocessing_result'] = {'traverses': {'sections': converted_courses}}

    # Проверяем данные
    points = project['points']
    observations = project['observations']
    preprocessing_result = project.get('preprocessing_result', None)

    print(f"Проект: points={len(points)}, observations={len(observations)}")
    print(f"Preprocessing: {preprocessing_result is not None}")

    if preprocessing_result:
        sections = preprocessing_result.get('traverses', {}).get('sections', [])
        print(f"Sections: {len(sections)}")

    # Подсчет типов измерений
    obs_types = {}
    for obs in observations:
        obs_type = obs.get('obs_type', 'unknown')
        obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

    print(f"Типы измерений: {obs_types}")

    # Проверяем leveling_courses
    leveling_courses = result.get('leveling_courses', [])
    print(f"Leveling courses: {len(leveling_courses)}")
    for course in leveling_courses[:3]:  # Первые 3
        print(f"  {course['course_id']}: {len(course.get('stations', []))} stations, {len(course.get('measurements', []))} measurements")

    return project

if __name__ == "__main__":
    project = test_gsi_import()