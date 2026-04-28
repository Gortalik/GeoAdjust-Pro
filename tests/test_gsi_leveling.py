#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправленного импорта GSI для нивелирования
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

def test_gsi_leveling_import():
    """Тест импорта GSI файла с нивелированием"""
    print("Тестирование импорта GSI с нивелированием...")
    
    from geoadjust.io.formats.gsi import GSIParser
    
    gsi_file = Path("test_real_mes/b_g/niv/GRO2209.GSI")
    parser = GSIParser()
    result = parser.parse(gsi_file)
    
    print(f"Результат парсинга:")
    print(f"  Точек: {len(result['points'])}")
    print(f"  Измерений: {len(result['observations'])}")
    print(f"  Сессий: {len(result['station_sessions'])}")
    
    if result['observations']:
        print(f"  Типы измерений: {set(obs.obs_type for obs in result['observations'])}")
        print("  Первые 10 измерений:")
        for i, obs in enumerate(result['observations'][:10]):
            print(f"    {i+1}. {obs.obs_type}: {obs.from_point} -> {obs.to_point} = {obs.value:.6f}")
    
    # Проверяем корректность данных
    leveling_obs = [obs for obs in result['observations'] if obs.obs_type == 'leveling_height_diff']
    print(f"\nНайдено нивелирных измерений: {len(leveling_obs)}")
    
    # Проверяем, что точки корректно определены
    points = set()
    for obs in leveling_obs[:20]:  # Первые 20 для проверки
        points.add(obs.from_point)
        points.add(obs.to_point)
    
    print(f"Уникальных точек в измерениях: {len(points)}")
    print(f"Примеры точек: {sorted(list(points))[:10]}")
    
    return result

def test_import_dialog_gsi():
    """Тест импорта через ImportDialog"""
    print("\nТестирование импорта через ImportDialog...")
    
    # Создаем mock ImportDialog
    class MockImportDialog:
        def __init__(self):
            self.file_path = "test_real_mes/b_g/niv/GRO2209.GSI"
        
        def _import_gsi(self):
            from geoadjust.io.formats.gsi import GSIParser
            from pathlib import Path

            parser = GSIParser()
            data = parser.parse(Path(self.file_path))

            # Конвертация в формат, ожидаемый приложением
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
                    'obs_type': getattr(obs, 'obs_type', ''),
                    'from_point': getattr(obs, 'from_point', ''),
                    'to_point': getattr(obs, 'to_point', ''),
                    'value': getattr(obs, 'value', 0),
                    'distance': getattr(obs, 'distance', None),
                    'instrument_height': getattr(obs, 'instrument_height', None),
                })

            return {
                'points': points,
                'observations': observations,
                'metadata': {'format': 'GSI', 'type': 'leveling'}
            }
    
    dialog = MockImportDialog()
    result = dialog._import_gsi()
    
    print(f"ImportDialog результат:")
    print(f"  Точек: {len(result['points'])}")
    print(f"  Измерений: {len(result['observations'])}")
    
    leveling_obs = [obs for obs in result['observations'] if obs['obs_type'] == 'leveling_height_diff']
    print(f"  Нивелирных измерений: {len(leveling_obs)}")
    
    return result

if __name__ == "__main__":
    gsi_result = test_gsi_leveling_import()
    dialog_result = test_import_dialog_gsi()
    
    print("\nТестирование завершено!")