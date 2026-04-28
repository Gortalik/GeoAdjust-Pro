#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест чтения Excel
"""

import pandas as pd
from pathlib import Path

df = pd.read_excel(Path("test_real_mes/b_g/niv/GRO2209.xlsx"))

print("Колонки:", list(df.columns))
print("Типы данных:")
for col in df.columns:
    print(f"  {col}: {df[col].dtype}")

print("\nПервые 10 строк по колонкам:")
for i in range(min(10, len(df))):
    row = df.iloc[i]
    print(f"Строка {i}: {[repr(row[j]) for j in range(len(df.columns))]}")

print("\nПроверяем конкретные колонки по индексу:")
# Колонка 3 - точка, колонка 5 - тип
print("Колонка 3 (точка):")
for i in range(min(10, len(df))):
    val = df.iloc[i, 3] if len(df.columns) > 3 else None
    print(f"  Строка {i}: {repr(val)}")

print("Колонка 5 (тип):")
for i in range(min(10, len(df))):
    val = df.iloc[i, 5] if len(df.columns) > 5 else None
    print(f"  Строка {i}: {repr(val)}")