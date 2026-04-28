#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка Credo DAT парсера
"""

import sys
from pathlib import Path
import pandas as pd

def debug_credo_parser():
    """Отладка парсера Credo DAT"""
    
    df = pd.read_excel(Path("test_real_mes/b_g/niv/GRO2209.xlsx"))
    
    print(f"Всего строк: {len(df)}")
    
    # Ищем станции (строки с "Задняя рейка")
    stations = []
    for idx, row in df.iterrows():
        try:
            if len(row) > 5 and pd.notna(row.iloc[5]):
                measurement_type = str(row.iloc[5]).strip()
                if '������' in measurement_type and len(row) > 3 and pd.notna(row.iloc[3]):
                    point_name = str(row.iloc[3]).strip()
                    if point_name:
                        stations.append((idx, point_name, measurement_type))
                        print(f"Станция найдена: строка {idx}, точка '{point_name}', тип '{measurement_type}'")
        except Exception as e:
            print(f"Ошибка в строке {idx}: {e}")
    
    print(f"\nВсего найдено станций: {len(stations)}")
    
    # Показываем первые 10 станций
    for idx, point, mtype in stations[:10]:
        print(f"  {idx}: {point} ({mtype})")

if __name__ == "__main__":
    debug_credo_parser()