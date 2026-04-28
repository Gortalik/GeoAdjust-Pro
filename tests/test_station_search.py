#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест поиска станций в Excel
"""

import pandas as pd
from pathlib import Path

df = pd.read_excel(Path("test_real_mes/b_g/niv/GRO2209.xlsx"))

print("Поиск станций:")

stations_found = []
for idx, row in df.iterrows():
    if len(row) > 5 and pd.notna(row.iloc[5]):
        measurement_type = str(row.iloc[5]).strip()
        print(f"Строка {idx}: '{measurement_type}' -> {'задняя' in measurement_type.lower()}")
        
        if 'задняя' in measurement_type.lower() and len(row) > 3 and pd.notna(row.iloc[3]):
            point_name = str(row.iloc[3]).strip()
            stations_found.append((idx, point_name, measurement_type))
            print(f"  -> СТАНЦИЯ: {point_name}")

print(f"\nНайдено станций: {len(stations_found)}")
for idx, name, mtype in stations_found:
    print(f"  Строка {idx}: {name} ({mtype})")