#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Подробный анализ Excel файла с данными нивелирования
"""

import sys
from pathlib import Path


def analyze_excel_detailed(file_path):
    """Подробный анализ Excel файла"""
    print(f"Подробный анализ: {file_path}")
    
    try:
        import pandas as pd
        
        df = pd.read_excel(file_path)
        
        print("Структура колонок:")
        for i, col in enumerate(df.columns):
            print(f"  {i}: {col}")
        
        print(f"\nВсего строк: {len(df)}")
        
        # Ищем непустые строки
        non_empty_rows = df.dropna(how='all')
        print(f"Непустых строк: {len(non_empty_rows)}")
        
        # Показываем первые 20 строк
        print("\nПервые 20 строк:")
        for i in range(min(20, len(df))):
            row = df.iloc[i]
            print(f"Строка {i+1}: {dict(row)}")
            
        # Ищем паттерны в данных
        print("\nАнализ паттернов:")
        
        # Ищем колонки с числовыми данными
        numeric_cols = []
        for col in df.columns:
            try:
                pd.to_numeric(df[col], errors='coerce')
                numeric_cols.append(col)
            except:
                pass
        
        print(f"Числовые колонки: {numeric_cols}")
        
        # Анализируем колонку с превышениями
        height_col = None
        for col in df.columns:
            if 'превыш' in col.lower() or 'высот' in col.lower():
                height_col = col
                break
        
        if height_col:
            print(f"\nАнализ колонки превышений '{height_col}':")
            values = pd.to_numeric(df[height_col], errors='coerce').dropna()
            print(f"  Количество значений: {len(values)}")
            print(f"  Min: {values.min()}")
            print(f"  Max: {values.max()}")
            print(f"  Mean: {values.mean()}")
            print(f"  Std: {values.std()}")
            print(f"  Первые 10 значений: {values.head(10).tolist()}")
        
        return df
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

if __name__ == "__main__":
    analyze_excel_detailed(Path("test_real_mes/b_g/niv/GRO2209.xlsx"))