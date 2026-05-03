#!/usr/bin/env python3
"""
Отладка: посмотрим что возвращает GSI парсер
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GeoAdjustPro', 'src'))

from pathlib import Path
from geoadjust.io.formats.gsi import GSIParser

def debug_gsi_parser():
    """Посмотрим что возвращает GSI парсер"""

    gsi_file = Path("test_real_mes/s5/niv/DOM0112 (1).GSI")

    if not gsi_file.exists():
        print(f"Файл не найден: {gsi_file}")
        return

    parser = GSIParser()
    result = parser.parse(gsi_file)

    print(f"Результат парсинга: {len(result)} ключей")
    for key, value in result.items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)} элементов")
            if len(value) > 0:
                print(f"    Первый элемент типа: {type(value[0])}")
                if hasattr(value[0], '__dict__'):
                    print(f"    Атрибуты: {list(value[0].__dict__.keys())}")
                elif isinstance(value[0], dict):
                    print(f"    Ключи: {list(value[0].keys())}")
        else:
            print(f"  {key}: {value}")

    # Посмотрим на первые 3 измерения
    observations = result.get('observations', [])
    print(f"\nПервые 3 измерения:")
    for i, obs in enumerate(observations[:3]):
        print(f"  {i+1}: тип={type(obs)}")
        if hasattr(obs, '__dict__'):
            for attr, val in obs.__dict__.items():
                if val is not None:
                    print(f"    {attr}: {val}")
        elif isinstance(obs, dict):
            for key, val in obs.items():
                print(f"    {key}: {val}")

if __name__ == '__main__':
    debug_gsi_parser()