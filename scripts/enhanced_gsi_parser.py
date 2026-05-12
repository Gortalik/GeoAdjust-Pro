#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправленный GSI парсер с боковым нивелированием
"""

import sys
from pathlib import Path


from geoadjust.io.formats.gsi import GSIParser

class EnhancedGSIParser(GSIParser):
    """Расширенный GSI парсер с поддержкой бокового нивелирования"""
    
    def _simple_parse(self, file_path: Path):
        """Улучшенный парсер с поддержкой бокового нивелирования"""
        # Сначала вызываем базовый парсер
        result = super()._simple_parse(file_path)
        
        # Теперь анализируем результаты и создаем боковое нивелирование
        self._create_intermediate_leveling(result)
        
        return result
    
    def _create_intermediate_leveling(self, result):
        """Создание бокового нивелирования на основе анализа структуры"""
        
        points = result['points']
        observations = result['observations']
        leveling_courses = result.get('leveling_courses', [])
        
        # Собираем все станции из ходов
        course_stations = set()
        for course in leveling_courses:
            course_stations.update(course.get('stations', []))
        
        # Собираем все точки назначения из основных измерений
        main_targets = set()
        for obs in observations:
            if hasattr(obs, 'obs_type') and obs.obs_type == 'leveling_height_diff':
                main_targets.add(obs.to_point if hasattr(obs, 'to_point') else obs.to_point)
            elif hasattr(obs, 'obs_type') and obs.obs_type == 'leveling_height_diff':
                main_targets.add(obs.to_point)
        
        # Определяем промежуточные точки (цели, которые не являются станциями)
        intermediate_targets = main_targets - course_stations
        
        print(f"DEBUG: Course stations: {len(course_stations)}")
        print(f"DEBUG: Main targets: {len(main_targets)}")
        print(f"DEBUG: Intermediate targets: {len(intermediate_targets)}")
        
        if intermediate_targets:
            print(f"DEBUG: Intermediate targets: {sorted(list(intermediate_targets))[:10]}")
            
            # Создаем измерения бокового нивелирования
        for obs in observations[:]:  # Копия списка для безопасного изменения
            target = obs.to_point if hasattr(obs, 'to_point') else obs.to_point
            if hasattr(obs, 'obs_type') and target in intermediate_targets and obs.obs_type == 'leveling_height_diff':
                # Создаем новое измерение бокового нивелирования
                intermediate_obs = type(obs)(
                    obs_type='intermediate_leveling',
                    from_point=obs.from_point if hasattr(obs, 'from_point') else obs.from_point,
                    to_point=target,
                    value=obs.value if hasattr(obs, 'value') else obs.value,
                    station_session_id=obs.station_session_id if hasattr(obs, 'station_session_id') else obs.station_session_id,
                    instrument_height=obs.instrument_height if hasattr(obs, 'instrument_height') else obs.instrument_height,
                    line_number=obs.line_number if hasattr(obs, 'line_number') else obs.line_number,
                    raw_words=obs.raw_words if hasattr(obs, 'raw_words') else obs.raw_words
                )
                observations.append(intermediate_obs)
                    
                    # Меняем тип основного измерения (опционально)
                    # obs.obs_type = 'intermediate_leveling'
        
        intermediate_count = len([obs for obs in observations if hasattr(obs, 'obs_type') and obs.obs_type == 'intermediate_leveling'])
        print(f"DEBUG: Created {intermediate_count} intermediate leveling measurements")

if __name__ == "__main__":
    parser = EnhancedGSIParser()
    result = parser.parse(Path("test_real_mes/b_g/niv/GRO2209.GSI"))
    
    print(f"\nРезультаты расширенного парсера:")
    print(f"Точек: {len(result['points'])}")
    print(f"Измерений: {len(result['observations'])}")
    print(f"Ходов: {len(result.get('leveling_courses', []))}")
    
    # Подсчет типов измерений
    obs_types = {}
    for obs in result['observations']:
        obs_type = obs.obs_type if hasattr(obs, 'obs_type') else obs.get('obs_type', 'unknown')
        obs_types[obs_type] = obs_types.get(obs_type, 0) + 1
    
    print(f"Типы измерений: {obs_types}")