#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка парсера Excel
"""

import sys
from pathlib import Path
import pandas as pd

def debug_excel_parsing():
    """Отладка парсинга Excel"""
    excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
    df = pd.read_excel(excel_file)
    
    print(f"Форма: {df.shape}")
    print(f"Колонки: {list(df.columns)}")
    
    # Проверим первые несколько строк
    for i in range(min(10, len(df))):
        row = df.iloc[i]
        print(f"\nСтрока {i}:")
        for j, col in enumerate(df.columns):
            val = row.iloc[j] if j < len(row) else None
            if pd.notna(val):
                print(f"  {col}: {repr(val)}")
    
    # Теперь попробуем нашу логику
    print("\n=== Наша логика парсинга ===")
    
    data_rows = []
    for idx, row in df.iterrows():
        if len(row) <= 3 or pd.isna(row.iloc[3]):
            continue

        point_name = str(row.iloc[3]).strip()
        if not point_name:
            continue
            
        print(f"Обработка строки {idx}: точка '{point_name}'")
        
        height_diff = 0.0
        if len(row) > 4 and pd.notna(row.iloc[4]):
            height_diff_str = str(row.iloc[4]).replace(',', '.')
            try:
                height_diff = float(height_diff_str)
                print(f"  Превышение: {height_diff}")
            except ValueError:
                print(f"  Ошибка конвертации превышения: {height_diff_str}")

        measurement_type = ''
        if len(row) > 5 and pd.notna(row.iloc[5]):
            measurement_type = str(row.iloc[5]).strip()
            print(f"  Тип измерения: '{measurement_type}'")
            
        if measurement_type:
            data_rows.append({
                'point': point_name,
                'type': measurement_type,
                'height_diff': height_diff
            })
    
    print(f"\nНайдено {len(data_rows)} строк данных")
    for item in data_rows[:5]:
        print(f"  {item}")

if __name__ == "__main__":
    debug_excel_parsing()