#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка поиска подстрок в Excel
"""

import pandas as pd
from pathlib import Path

df = pd.read_excel(Path("test_real_mes/b_g/niv/GRO2209.xlsx"))

# Проверим строку 4, колонка 5
row = df.iloc[4]
val = row.iloc[5]
val_str = str(val)

print(f"Значение: {repr(val_str)}")
print(f"Длина: {len(val_str)}")

# Проверим байты
print(f"Байты: {val_str.encode('utf-8', errors='replace')}")

# Попробуем разные поиски
test_strings = ['Задняя', '������', '������', 'Задняя', 'Передняя', '�������']

for test_str in test_strings:
    try:
        found = test_str in val_str
        print(f"'{test_str}' in string: {found}")
    except:
        print(f"Error with '{test_str}'")

# Попробуем поиск по байтам
val_bytes = val_str.encode('utf-8', errors='replace')
zad_bytes = '������'.encode('utf-8', errors='replace')
print(f"������ bytes: {zad_bytes}")
print(f"Value contains ������ bytes: {zad_bytes in val_bytes}")