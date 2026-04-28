#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка Credo DAT парсера
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

def debug_credo():
    print("Начинаем отладку Credo DAT парсера")
    
    from geoadjust.io.formats.credo_dat import CredoDATParser
    
    file_path = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
    print(f"Проверяем файл: {file_path.exists()}")
    
    parser = CredoDATParser()
    print("Парсер создан")
    
    try:
        result = parser.parse(file_path)
        print(f"Результат: {len(result['points'])} точек, {len(result['observations'])} измерений")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_credo()