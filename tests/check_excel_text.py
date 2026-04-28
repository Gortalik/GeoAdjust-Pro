#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка текста в Excel
"""

import pandas as pd
from pathlib import Path

df = pd.read_excel(Path("test_real_mes/b_g/niv/GRO2209.xlsx"))

# Проверим конкретные строки
for idx in [1, 4, 5]:  # Строки со станциями
    if idx < len(df):
        row = df.iloc[idx]
        print(f"\nСтрока {idx}:")
        for col_idx in range(min(10, len(df.columns))):
            val = row.iloc[col_idx]
            if pd.notna(val):
                print(f"  Колонка {col_idx}: {repr(str(val))} (тип: {type(val)})")
        
        # Специально проверим колонку 5 (тип измерения)
        if len(row) > 5:
            val = row.iloc[5]
            print(f"  Колонка 5 как есть: {repr(val)}")
            print(f"  Колонка 5 как строка: {repr(str(val))}")
            print(f"  Содержит '������': {'������' in str(val)}")
            print(f"  Содержит 'Задняя': {'Задняя' in str(val)}")