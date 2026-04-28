#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Подробный анализ листа "Схема ходов"
"""

import sys
from pathlib import Path
import pandas as pd

def analyze_scheme_sheet():
    """Анализ листа схемы ходов"""
    excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
    
    # Читаем второй лист (индекс 1)
    df = pd.read_excel(excel_file, sheet_name=1)
    
    print("=== АНАЛИЗ ЛИСТА 'СХЕМА ХОДОВ' ===")
    print(f"Размер: {df.shape}")
    print(f"Колонки: {list(df.columns)}")
    print()
    
    # Показываем все содержимое
    print("Полное содержимое листа:")
    for i in range(len(df)):
        row = df.iloc[i]
        row_data = []
        for j, col in enumerate(df.columns):
            val = row.iloc[j]
            if pd.notna(val):
                row_data.append(f"{col}: {val}")
        
        if row_data:
            print(f"Строка {i+1}: {', '.join(row_data)}")
    
    print()
    print("=== АНАЛИЗ СТРУКТУРЫ ===")
    
    # Ищем ходы
    courses = []
    for i, row in df.iterrows():
        for j, col in enumerate(df.columns):
            val = row.iloc[j]
            if pd.notna(val) and 'ход' in str(val).lower():
                courses.append((i, j, val))
    
    print(f"Найдено упоминаний ходов: {len(courses)}")
    for i, j, val in courses:
        print(f"  Строка {i+1}, колонка {j}: {val}")
    
    # Ищем станции и цели
    stations = []
    targets = []
    
    for i, row in df.iterrows():
        for j, col in enumerate(df.columns):
            val = row.iloc[j]
            if pd.notna(val):
                val_str = str(val).strip()
                # Ищем паттерны типа "R52267 - V1" или подобное
                if ' - ' in val_str and len(val_str.split(' - ')) == 2:
                    parts = val_str.split(' - ')
                    if len(parts[0]) > 0 and len(parts[1]) > 0:
                        stations.append(parts[0])
                        targets.append(parts[1])
    
    print(f"Найдено связей станция-цель: {len(stations)}")
    for s, t in zip(stations, targets):
        print(f"  {s} -> {t}")

if __name__ == "__main__":
    analyze_scheme_sheet()