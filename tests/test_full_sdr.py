#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест полного уравнивания с использованием всех SDR данных
"""

import sys
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser
from geo_adjust_pro import NetworkPoint
from geo_adjust_pro.engine import GeoAdjustEngine

print("Тест полного уравнивания SDR данных...")

# Парсим SDR файл
parser = SDRParser()
result = parser.parse('test_real_mes/b_g/plan/badgro16093_const.sdr')

points = result.get('points', [])
observations = result.get('observations', [])

print(f"Загружено точек: {len(points)}")
print(f"Загружено наблюдений: {len(observations)}")

# Преобразуем точки
points_dict = {}
for p in points:
    points_dict[p['point_id']] = NetworkPoint(
        id=p['point_id'],
        x=p.get('x'),
        y=p.get('y'),
        z=p.get('h'),
        plan_status='working',
        height_status='working'
    )

print(f"Степени свободы: {len(observations)} - {len(points)*2} = {len(observations) - len(points)*2}")

# Создаем движок и загружаем данные
engine = GeoAdjustEngine()
engine.load_network(points_dict, observations)

print("\nЗапуск свободного уравнивания плана...")
result_plan = engine.adjust_plan(points_dict, observations, free_adjustment=True)

print(f"Успех: {result_plan.success}")
print(f"СКП: {result_plan.sigma0:.6f} мм")
print(f"Итераций: {result_plan.iterations}")
print(f"Остатков: {len(result_plan.residuals)}")

if result_plan.success and result_plan.points_stats:
    print("\nПервые 5 результатов:")
    for i, (pid, stats) in enumerate(sorted(result_plan.points_stats.items())[:5]):
        print(".3f")

    # Проверяем распределение остатков
    if result_plan.residuals:
        import numpy as np
        residuals = np.array(result_plan.residuals)
        print("\nСтатистика остатков:")
        print(f"Среднее: {np.mean(residuals):.6f} угл.сек")
        print(f"Стд. отклонение: {np.std(residuals):.6f} угл.сек")
        print(f"Минимум: {np.min(residuals):.6f} угл.сек")
        print(f"Максимум: {np.max(residuals):.6f} угл.сек")
        print(f"RMSE: {np.sqrt(np.mean(residuals**2)):.6f} угл.сек")
print("\nТест завершен.")