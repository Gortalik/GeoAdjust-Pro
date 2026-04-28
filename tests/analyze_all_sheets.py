#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ всех листов Excel файла с данными нивелирования
"""

import sys
from pathlib import Path
import pandas as pd

def analyze_all_excel_sheets():
    """Анализ всех листов Excel файла"""
    excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
    
    # Читаем все листы
    xl = pd.ExcelFile(excel_file)
    print(f"Файл: {excel_file}")
    print(f"Листы: {xl.sheet_names}")
    print()
    
    for sheet_name in xl.sheet_names:
        print(f"=== ЛИСТ: {sheet_name} ===")
        
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            print(f"Размер: {df.shape}")
            
            if len(df.columns) > 0:
                print(f"Колонки: {list(df.columns)}")
                
                # Показываем первые несколько строк
                print("Первые 5 строк:")
                for i in range(min(5, len(df))):
                    row = df.iloc[i]
                    # Соберем непустые значения
                    values = []
                    for col in df.columns:
                        val = row.get(col)
                        if pd.notna(val):
                            values.append(f"{col}: {val}")
                    
                    if values:
                        print(f"  Строка {i+1}: {', '.join(values[:3])}")  # Первые 3 значения
                
                # Ищем ключевые слова
                text_content = df.to_string()
                if 'превыш' in text_content.lower():
                    print("✓ Содержит превышения")
                if 'ход' in text_content.lower():
                    print("✓ Содержит информацию о ходах")
                if 'боков' in text_content.lower():
                    print("✓ Содержит боковое нивелирование")
                if 'станц' in text_content.lower():
                    print("✓ Содержит станции")
                    
        except Exception as e:
            print(f"Ошибка чтения листа {sheet_name}: {e}")
        
        print()

if __name__ == "__main__":
    analyze_all_excel_sheets()