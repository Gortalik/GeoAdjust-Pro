#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест проверки None координат
"""

import sys
import os

# Добавляем путь к исходному коду
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:

# Импортируем и проверяем
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.network.models import NetworkPoint, Observation

print("Создаем тестовые данные...")

# Создаем сеть с точками, имеющими None координаты
points = {
    'STA1': NetworkPoint(point_id='STA1', coord_type='FIXED', x=0, y=0, h=0),
    'P1': NetworkPoint(point_id='P1', coord_type='FREE', x=None, y=None, h=None),  # None координаты
}

observations = [
    Observation(obs_id='dist1', obs_type='distance', from_setup_id='STA1_SETUP',
               from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
]

print("Проверяем координаты точек:")
print(f"STA1: x={points['STA1'].x}, y={points['STA1'].y}")
print(f"P1: x={points['P1'].x}, y={points['P1'].y}")

print("Вызываем build_adjustment_matrix...")
builder = EquationsBuilder()
try:
    A, L = builder.build_adjustment_matrix(observations, points, ['STA1'])
    print(f"Результат: матрица {A.shape[0]}x{A.shape[1]}, вектор L длиной {len(L)}")
    print("Тест пройден успешно!")
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()