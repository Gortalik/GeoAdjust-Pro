#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест GSI парсера с отладкой
"""

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

logging.basicConfig(level=logging.DEBUG)

from geoadjust.io.formats.gsi import GSIParser

parser = GSIParser()
result = parser.parse(Path("test_real_mes/b_g/niv/GRO2209.GSI"))

print(f"Результаты:")
print(f"  Точек: {len(result['points'])}")
print(f"  Измерений: {len(result['observations'])}")
print(f"  Сессий: {len(result['station_sessions'])}")

if result['points']:
    print("Первые 5 точек:")
    for p in result['points'][:5]:
        print(f"  {p['point_id']} ({p['point_type']})")

if result['observations']:
    print("Первые 5 измерений:")
    for obs in result['observations'][:5]:
        print(f"  {obs.obs_type}: {obs.from_point} -> {obs.to_point} = {obs.value}")