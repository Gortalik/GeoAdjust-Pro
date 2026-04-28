#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностика Excel файла
"""

import sys
from pathlib import Path

def diagnose_excel():
    """Диагностика содержимого Excel файла"""
    try:
        import pandas as pd
        
        excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
        print(f"Читаем файл: {excel_file}")
        
        # Читаем без заголовков
        df = pd.read_excel(excel_file, header=None)
        print(f"Размер: {df.shape}")
        
        # Показываем первые 10 строк
        print("\nПервые 10 строк (сырые данные):")
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            print(f"Строка {i}: {list(row)}")
        
        # Ищем строки с данными
        print("\nСтроки с данными:")
        for i in range(min(50, len(df))):
            row = df.iloc[i]
            # Ищем строки где есть числа
            has_numbers = any(isinstance(x, (int, float)) or (isinstance(x, str) and any(c.isdigit() for c in x)) for x in row if pd.notna(x))
            if has_numbers:
                print(f"Строка {i}: {list(row)}")
        
        # Показываем уникальные значения в колонках
        print("\nУникальные значения в колонках:")
        for col in range(min(10, df.shape[1])):
            unique_vals = df[col].dropna().unique()[:5]  # Первые 5 уникальных
            print(f"Колонка {col}: {list(unique_vals)}")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_excel()