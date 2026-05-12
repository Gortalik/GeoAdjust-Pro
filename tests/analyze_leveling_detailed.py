#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальный анализ структуры данных нивелирования из Excel
"""

import sys
from pathlib import Path


def analyze_leveling_structure():
    """Анализ структуры данных нивелирования"""
    print("=== Анализ структуры данных нивелирования ===\n")
    
    try:
        import pandas as pd
        
        # Читаем Excel файл
        excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
        df = pd.read_excel(excel_file)
        
        print("Структура Excel файла:")
        print(f"Всего строк: {len(df)}")
        print(f"Колонки: {list(df.columns)}")
        
        # Ищем паттерны в данных
        print("\nПервые 50 строк с данными:")
        for i in range(min(50, len(df))):
            row = df.iloc[i]
            # Проверяем, есть ли данные в строке
            if pd.notna(row.get('���', None)):  # Точка
                print(f"Строка {i+1}: Точка={row.get('���', '')}, "
                      f"Превышение={row.get('������, �', '')}, "
                      f"Тип={row.get('��� �������', '')}, "
                      f"Расстояние={row.get('����������, �', '')}")
        
        # Анализируем последовательность измерений
        print("\n=== Анализ последовательности ===")
        
        points_sequence = []
        current_station = None
        
        for i, row in df.iterrows():
            point = row.get('���', '').strip() if pd.notna(row.get('���')) else None
            measurement_type = row.get('��� �������', '').strip() if pd.notna(row.get('��� �������')) else None
            
            if point and measurement_type:
                points_sequence.append({
                    'index': i,
                    'point': point,
                    'type': measurement_type,
                    'height_diff': row.get('������, �'),
                    'distance': row.get('����������, �')
                })
                
                # Определяем станции (точки с "Задняя рейка")
                if "������" in measurement_type:
                    current_station = point
                    print(f"Станция {current_station} на строке {i+1}")
        
        # Группируем по станциям
        print("\n=== Группировка по станциям ===")
        station_groups = {}
        
        for item in points_sequence:
            if "������" in item['type']:
                current_station = item['point']
                if current_station not in station_groups:
                    station_groups[current_station] = []
            
            if current_station and item['point'] != current_station:
                station_groups[current_station].append(item)
        
        for station, measurements in station_groups.items():
            print(f"\nСтанция {station}:")
            for m in measurements[:5]:  # Первые 5 измерений
                print(f"  {m['point']} ({m['type']}): dh={m['height_diff']}, dist={m['distance']}")
            if len(measurements) > 5:
                print(f"  ... и еще {len(measurements) - 5} измерений")
        
        # Сравниваем с GSI данными
        print("\n=== Сравнение с GSI парсером ===")
        from geoadjust.io.formats.gsi import GSIParser
        
        gsi_file = Path("test_real_mes/b_g/niv/GRO2209.GSI")
        parser = GSIParser()
        gsi_result = parser.parse(gsi_file)
        
        print(f"GSI: {len(gsi_result['observations'])} измерений")
        print(f"Excel: {len(points_sequence)} точек с измерениями")
        
        # Показываем соответствие
        excel_stations = set(station_groups.keys())
        gsi_stations = set()
        for obs in gsi_result['observations']:
            if hasattr(obs, 'from_point'):
                gsi_stations.add(obs.from_point)
        
        print(f"Станции в Excel: {sorted(excel_stations)}")
        print(f"Станции в GSI: {sorted(gsi_stations)}")
        
        return df, points_sequence, station_groups
        
    except Exception as e:
        print(f"Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

if __name__ == "__main__":
    analyze_leveling_structure()