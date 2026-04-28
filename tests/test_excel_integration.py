#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест полной интеграции Excel импорта
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

def test_excel_integration():
    print("=== Тест интеграции Excel импорта ===")
    
    # Тестируем ImportDialog с Excel файлом
    class MockImportDialog:
        def __init__(self):
            self.file_path = "test_real_mes/b_g/niv/GRO2209.xlsx"
        
        def _import_excel(self):
            from geoadjust.io.formats.credo_dat import CredoDATParser
            from pathlib import Path

            parser = CredoDATParser()
            data = parser.parse(Path(self.file_path))

            # Конвертация в формат приложения
            points = []
            for p in data.get('points', []):
                points.append({
                    'name': p.get('point_id', ''),
                    'x': p.get('x', 0) or 0,
                    'y': p.get('y', 0) or 0,
                    'h': p.get('h', 0) or 0,
                    'type': p.get('point_type', 'free')
                })

            observations = []
            for obs in data.get('observations', []):
                observations.append({
                    'obs_type': obs.get('obs_type', ''),
                    'from_point': obs.get('from_point', ''),
                    'to_point': obs.get('to_point', ''),
                    'value': obs.get('value', 0),
                    'distance': obs.get('distance'),
                    'instrument_height': obs.get('instrument_height'),
                })

            return {
                'points': points,
                'observations': observations,
                'station_sessions': data.get('station_sessions', []),
                'metadata': {'format': 'Excel', 'type': 'leveling'}
            }
    
    dialog = MockImportDialog()
    result = dialog._import_excel()
    
    print(f"Результат импорта:")
    print(f"  Точек: {len(result['points'])}")
    print(f"  Измерений: {len(result['observations'])}")
    
    # Проверяем структуру данных
    if result['observations']:
        leveling_obs = [obs for obs in result['observations'] if obs['obs_type'] == 'leveling_height_diff']
        print(f"  Нивелирных измерений: {len(leveling_obs)}")
        
        # Проверяем станции
        stations = set()
        targets = set()
        for obs in leveling_obs:
            stations.add(obs['from_point'])
            targets.add(obs['to_point'])
        
        print(f"  Станций: {len(stations)}")
        print(f"  Целей: {len(targets)}")
        
        print(f"  Примеры станций: {sorted(list(stations))[:5]}")
        print(f"  Примеры целей: {sorted(list(targets))[:5]}")
    
    return result

if __name__ == "__main__":
    test_excel_integration()