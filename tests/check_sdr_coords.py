#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка реальных данных SDR на предмет одинаковых координат
"""

import sys

from geoadjust.io.formats.sdr import SDRParser

print("Проверка координат в SDR файле...")

parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

points = result.get('points', [])

print(f"Загружено {len(points)} точек")

# Проверяем координаты
coords = []
for p in points:
    x = p.get('x')
    y = p.get('y')
    if x is not None and y is not None:
        coords.append((x, y))
        print(".3f")

if coords:
    import numpy as np
    coords_array = np.array(coords)
    print("\nСтатистика координат:")
    print(f"X: от {coords_array[:, 0].min():.3f} до {coords_array[:, 0].max():.3f}")
    print(f"Y: от {coords_array[:, 1].min():.3f} до {coords_array[:, 1].max():.3f}")

    # Проверяем, все ли координаты одинаковые
    unique_coords = set((round(x, 3), round(y, 3)) for x, y in coords)
    print(f"Уникальных координат: {len(unique_coords)}")

    if len(unique_coords) == 1:
        print("ОШИБКА: Все точки имеют одинаковые координаты!")
    elif len(unique_coords) < len(coords):
        print(f"ПРЕДУПРЕЖДЕНИЕ: {len(coords) - len(unique_coords)} точек имеют совпадающие координаты")

    # Проверяем минимальные расстояния
    from scipy.spatial.distance import pdist
    if len(coords) > 1:
        distances = pdist(coords_array)
        min_dist = np.min(distances)
        max_dist = np.max(distances)
        print(f"Минимальное расстояние: {min_dist:.3f} м")
        print(f"Максимальное расстояние: {max_dist:.3f} м")
else:
    print("ОШИБКА: Нет координат в данных!")

print("\nПроверка завершена.")