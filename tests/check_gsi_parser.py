#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка того, что возвращает GSI парсер
"""

import sys
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.io.formats.gsi import GSIParser
from pathlib import Path

print("Проверка GSI парсера...")

parser = GSIParser()
result = parser.parse(Path('test_real_mes/s5/niv/DOM0112 (1).GSI'))

print(f"Результат: {result.keys()}")

observations = result.get('observations', [])
print(f"Наблюдений: {len(observations)}")

for i, obs in enumerate(observations[:5]):
    print(f"Наблюдение {i+1}:")
    print(f"  Тип: {getattr(obs, 'obs_type', 'нет типа')}")
    print(f"  От: {getattr(obs, 'from_point', 'нет')}")
    print(f"  К: {getattr(obs, 'to_point', 'нет')}")
    print(f"  Значение: {getattr(obs, 'value', 'нет')}")
    print()

print("Проверка завершена.")