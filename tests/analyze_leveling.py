#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ Excel файлов с данными нивелирования
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

def analyze_excel_file(file_path):
    """Анализ Excel файла с данными нивелирования"""
    print(f"Анализ файла: {file_path}")
    
    try:
        import pandas as pd
        
        # Читаем Excel файл
        df = pd.read_excel(file_path)
        print(f"Колонки: {list(df.columns)}")
        print(f"Количество строк: {len(df)}")
        print(f"Первые 10 строк:")
        print(df.head(10))
        
        # Анализируем структуру данных
        print("\nАнализ структуры:")
        for col in df.columns:
            non_null = df[col].notna().sum()
            print(f"  {col}: {non_null}/{len(df)} непустых значений")
            
        return df
        
    except ImportError:
        print("pandas не установлен")
        return None
    except Exception as e:
        print(f"Ошибка чтения Excel: {e}")
        return None

def analyze_gsi_file(file_path):
    """Анализ GSI файла"""
    print(f"Анализ GSI файла: {file_path}")
    
    from geoadjust.io.formats.gsi import GSIParser
    
    parser = GSIParser()
    result = parser.parse(file_path)
    
    print(f"Результат парсинга GSI:")
    print(f"  Точек: {len(result['points'])}")
    print(f"  Измерений: {len(result['observations'])}")
    print(f"  Сессий станций: {len(result['station_sessions'])}")
    
    if result['observations']:
        print(f"  Типы измерений: {set(obs.obs_type for obs in result['observations'])}")
        print("  Первые 5 измерений:")
        for i, obs in enumerate(result['observations'][:5]):
            print(f"    {i+1}. {obs.obs_type}: {obs.from_point} -> {obs.to_point} = {obs.value}")
    
    return result

def compare_excel_gsi(excel_df, gsi_result):
    """Сравнение данных из Excel и GSI"""
    if excel_df is None:
        print("Нет данных Excel для сравнения")
        return
        
    print("\nСравнение Excel и GSI:")
    
    # Ищем колонки с превышениями в Excel
    height_cols = [col for col in excel_df.columns if 'превыш' in col.lower() or 'высот' in col.lower() or 'diff' in col.lower()]
    print(f"Колонки с превышениями в Excel: {height_cols}")
    
    # Ищем колонки с точками
    point_cols = [col for col in excel_df.columns if 'точк' in col.lower() or 'point' in col.lower() or 'репер' in col.lower()]
    print(f"Колонки с точками в Excel: {point_cols}")
    
    # Показываем примеры данных
    if height_cols:
        print("Примеры превышений из Excel:")
        for col in height_cols[:3]:  # Первые 3 колонки
            values = excel_df[col].dropna().head(5)
            print(f"  {col}: {list(values)}")

if __name__ == "__main__":
    # Анализируем файлы
    excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
    gsi_file = Path("test_real_mes/b_g/niv/GRO2209.GSI")
    
    excel_data = analyze_excel_file(excel_file)
    gsi_data = analyze_gsi_file(gsi_file)
    
    compare_excel_gsi(excel_data, gsi_data)