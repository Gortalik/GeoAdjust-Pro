#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка текста в Excel (исправленная)
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
                val_str = str(val)
                print(f"  Колонка {col_idx}: {repr(val_str)}")
        
        # Специально проверим колонку 5 (тип измерения)
        if len(row) > 5:
            val = row.iloc[5]
            if pd.notna(val):
                val_str = str(val)
                print(f"  Колонка 5: {repr(val_str)}")
                # Проверяем наличие ключевых слов
                has_zad = 'Задняя' in val_str or '������' in val_str
                has_pered = 'Передняя' in val_str or '�������' in val_str
                print(f"    Содержит 'Задняя': {has_zad}")
                print(f"    Содержит '������': {'������' in val_str}")
                print(f"    Содержит 'Передняя': {has_pered}")
                print(f"    Содержит '�������': {'�������' in val_str}")