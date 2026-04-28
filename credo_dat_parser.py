#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер Excel файлов с данными нивелирования из Credo DAT
"""

import sys
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

class CredoDATParser:
    """Парсер данных нивелирования из Credo DAT (Excel)"""
    
    def __init__(self):
        pass
    
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Парсинг Excel файла с данными нивелирования"""
        
        # Читаем Excel файл
        df = pd.read_excel(file_path)
        
        points = []
        observations = []
        station_sessions = []
        
        current_station = None
        session_counter = 0

        # Словарь для точек
        point_dict = {}

        # Читаем данные по индексам колонок (не по именам)
        for idx, row in df.iterrows():
            try:
                # Колонка 3 - точка, 4 - превышение, 5 - тип, 6 - расстояние
                if len(row) <= 3 or pd.isna(row.iloc[3]):
                    continue

                point_name = str(row.iloc[3]).strip()
                if not point_name:
                    continue

                height_diff = 0.0
                if len(row) > 4 and pd.notna(row.iloc[4]):
                    height_diff_str = str(row.iloc[4]).replace(',', '.')
                    try:
                        height_diff = float(height_diff_str)
                    except ValueError:
                        height_diff = 0.0

                measurement_type = ''
                if len(row) > 5 and pd.notna(row.iloc[5]):
                    measurement_type = str(row.iloc[5]).strip()

                distance = None
                if len(row) > 6 and pd.notna(row.iloc[6]):
                    distance_str = str(row.iloc[6]).replace(',', '.')
                    try:
                        distance = float(distance_str)
                    except ValueError:
                        distance = None
                    
                # height_diff и distance уже конвертированы выше
                
                # Определяем тип измерения
                if '������' in measurement_type:  # Задняя рейка - станция
                    current_station = point_name
                    session_counter += 1
                    
                    # Добавляем станцию в точки
                    if point_name not in point_dict:
                        point_dict[point_name] = {
                            'point_id': point_name,
                            'point_type': 'station',
                            'x': None,
                            'y': None,
                            'h': None
                        }
                        points.append(point_dict[point_name])
                    
                    # Создаем сессию станции
                    session = {
                        'session_id': f"SESSION_{session_counter:03d}",
                        'station_name': point_name,
                        'instrument_height': None,
                        'observations': []
                    }
                    station_sessions.append(session)
                    
                elif '�������' in measurement_type:  # Передняя рейка - цель
                    if current_station and point_name != current_station:
                        # Добавляем цель в точки
                        if point_name not in point_dict:
                            point_dict[point_name] = {
                                'point_id': point_name,
                                'point_type': 'target', 
                                'x': None,
                                'y': None,
                                'h': None
                            }
                            points.append(point_dict[point_name])
                        
                        # Создаем измерение превышения
                        obs = {
                            'obs_type': 'leveling_height_diff',
                            'from_point': current_station,
                            'to_point': point_name,
                            'value': height_diff,
                            'distance': distance,
                            'instrument_height': None,
                            'station_session_id': f"SESSION_{session_counter:03d}",
                            'line_number': idx + 1
                        }
                        observations.append(obs)
                        
                        # Добавляем в сессию
                        if station_sessions:
                            station_sessions[-1]['observations'].append(obs)
                            
                elif '�������������' in measurement_type:  # Промежуточная - боковое нивелирование
                    # Для бокового нивелирования создаем отдельное измерение
                    if current_station:
                        obs = {
                            'obs_type': 'intermediate_leveling',
                            'from_point': current_station,
                            'to_point': point_name,
                            'value': height_diff,
                            'distance': distance,
                            'instrument_height': None,
                            'station_session_id': f"SESSION_{session_counter:03d}",
                            'line_number': idx + 1
                        }
                        observations.append(obs)
                        
                        # Добавляем точку
                        if point_name not in point_dict:
                            point_dict[point_name] = {
                                'point_id': point_name,
                                'point_type': 'intermediate',
                                'x': None,
                                'y': None,
                                'h': None
                            }
                            points.append(point_dict[point_name])
                
            except Exception as e:
                print(f"Ошибка обработки строки {idx}: {e}")
                continue
        
        return {
            'points': points,
            'observations': observations,
            'station_sessions': station_sessions,
            'format': 'CredoDAT',
            'total_lines': len(df),
            'num_observations': len(observations),
            'num_points': len(points),
            'success': len(observations) > 0,
            'errors': [],
            'warnings': []
        }

def test_credo_parser():
    """Тест парсера Credo DAT"""
    parser = CredoDATParser()
    result = parser.parse(Path("test_real_mes/b_g/niv/GRO2209.xlsx"))
    
    print("Результаты парсинга Excel файла:")
    print(f"  Точек: {len(result['points'])}")
    print(f"  Измерений: {len(result['observations'])}")
    print(f"  Сессий: {len(result['station_sessions'])}")
    
    if result['observations']:
        print(f"  Типы измерений: {set(obs['obs_type'] for obs in result['observations'])}")
        print("  Первые 10 измерений:")
        for i, obs in enumerate(result['observations'][:10]):
            print(f"    {i+1}. {obs['obs_type']}: {obs['from_point']} -> {obs['to_point']} = {obs['value']:.6f}")
    
    # Показываем станции
    if result['station_sessions']:
        print("\nСтанции:")
        for session in result['station_sessions'][:5]:
            print(f"  {session['station_name']}: {len(session['observations'])} измерений")
    
    return result

if __name__ == "__main__":
    test_credo_parser()