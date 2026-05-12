#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправленный анализ структуры данных нивелирования из Excel
"""

import sys
from pathlib import Path


def analyze_excel_correctly():
    """Правильный анализ Excel файла"""
    print("=== Исправленный анализ Excel файла ===\n")
    
    try:
        import pandas as pd
        
        excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
        df = pd.read_excel(excel_file)
        
        print(f"Размер файла: {len(df)} строк")
        print(f"Колонки: {list(df.columns)}")
        
        # Печатаем первые несколько строк для анализа
        print("\nПервые 5 строк:")
        for i, row in df.head(5).iterrows():
            print(f"Строка {i}:")
            for col in df.columns:
                val = row.get(col, '')
                if pd.notna(val) and str(val).strip():
                    print(f"  {col}: {val}")

        print(f"\nАнализ колонок:")
        for col in df.columns:
            non_null = df[col].notna().sum()
            print(f"  {col}: {non_null} непустых значений")

            if point and point not in ['', 'nan', 'None'] and measurement_type:
                try:
                    # Пробуем конвертировать превышение в число
                    if isinstance(height_diff, str):
                        height_diff_val = float(height_diff.replace(',', '.'))
                    else:
                        height_diff_val = float(height_diff) if pd.notna(height_diff) else None
                    
                    data_rows.append({
                        'row': i + 1,
                        'point': point,
                        'type': measurement_type,
                        'height_diff': height_diff_val,
                        'distance': row.get('����������, �')
                    })
                except (ValueError, TypeError):
                    continue
        
        print(f"\nНайдено {len(data_rows)} строк с данными")
        
        # Показываем первые 20
        print("\nПервые 20 строк с данными:")
        for item in data_rows[:20]:
            print(f"Строка {item['row']:3d}: {item['point']:8s} | {item['type']:15s} | dh={item['height_diff']:8.4f} | dist={item['distance']}")
        
        # Анализируем последовательность
        print("\n=== Анализ последовательности ===")
        
        stations = []
        current_station = None
        
        for item in data_rows:
            if '������' in item['type']:  # Задняя рейка
                current_station = item['point']
                stations.append(current_station)
                print(f"Станция: {current_station} (строка {item['row']})")
            elif current_station and item['point'] != current_station:
                print(f"  Цель: {item['point']} (строка {item['row']})")
        
        print(f"\nВсего станций: {len(set(stations))}")
        print(f"Уникальные станции: {sorted(set(stations))}")
        
        return data_rows
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    analyze_excel_correctly()