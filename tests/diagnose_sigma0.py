#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностика проблемы с СКО = 0.000
"""

import sys
import os
import numpy as np
sys.path.insert(0, 'GeoAdjustPro/src')

from geoadjust.core.adjustment.engine import AdjustmentEngine
import scipy.sparse as sparse

print("Диагностика проблемы с СКО = 0.000")
print("=" * 50)

# Создаем искусственные данные с известной точностью
print("Создаем тестовые данные...")

# Тестовая сеть: 3 точки, 3 расстояния (треугольник)
# Известные координаты
true_coords = {
    'A': np.array([0.0, 0.0]),
    'B': np.array([100.0, 0.0]),
    'C': np.array([50.0, 86.60254037844386])
}

# Расчет расстояний с добавлением ошибки
distances = {}
np.random.seed(42)  # Для воспроизводимости

for i, (p1, c1) in enumerate(true_coords.items()):
    for p2, c2 in list(true_coords.items())[i+1:]:
        true_dist = np.linalg.norm(c1 - c2)
        # Добавляем ошибку ±2мм
        error = np.random.normal(0, 0.002)
        measured_dist = true_dist + error
        distances[(p1, p2)] = measured_dist

print("Истинные расстояния:")
for (p1, p2), dist in distances.items():
    true_dist = np.linalg.norm(true_coords[p1] - true_coords[p2])
    error = (dist - true_dist) * 1000
    print(".1f")

# Создаем матрицы уравнивания вручную
points = ['A', 'B', 'C']
n_points = len(points)
n_unknowns = n_points * 2  # X и Y для каждой точки
n_obs = len(distances)

print(f"\nРазмерность: {n_obs} наблюдений, {n_unknowns} неизвестных")
print(f"Степени свободы: {n_obs - n_unknowns}")

# Создаем разреженную матрицу
rows = []
cols = []
data = []
L = []
weights = []

point_indices = {pt: i*2 for i, pt in enumerate(points)}

obs_idx = 0
for (p1, p2), measured_dist in distances.items():
    # Координаты точек (начальные приближения)
    x1, y1 = true_coords[p1] + np.random.normal(0, 0.1, 2)  # Добавляем шум к начальным
    x2, y2 = true_coords[p2] + np.random.normal(0, 0.1, 2)

    # Расчет приближенного расстояния
    dx = x2 - x1
    dy = y2 - y1
    S0 = np.sqrt(dx**2 + dy**2)

    # Производные
    a_x1 = -dx / S0
    a_y1 = -dy / S0
    a_x2 = dx / S0
    a_y2 = dy / S0

    # Свободный член
    l = measured_dist - S0

    # Вес (обратно пропорционален расстоянию)
    w = 1.0 / measured_dist

    # Добавляем коэффициенты
    idx1 = point_indices[p1]
    idx2 = point_indices[p2]

    row_entries = [a_x1, a_y1, a_x2, a_y2]
    col_entries = [idx1, idx1+1, idx2, idx2+1]

    rows.extend([obs_idx] * len(row_entries))
    cols.extend(col_entries)
    data.extend(row_entries)
    L.append(l)
    weights.append(w)
    obs_idx += 1

# Создаем матрицы
A = sparse.csr_matrix((data, (rows, cols)), shape=(n_obs, n_unknowns))
L_vec = np.array(L)
P = sparse.diags(weights)

print(f"\nМатрица A: {A.shape}")
print(f"Вектор L: {L_vec.shape}")
print(f"Матрица весов P: {P.shape}")

# Решение системы
engine = AdjustmentEngine()
result = engine.adjust(A, L_vec, P)

print("\nРезультаты уравнивания:")
print(f"Успех: {result is not None}")
if result:
    print(f"Поправки (dx): {result['coordinate_corrections']}")
    print(f"Остатки (v): {result['residuals']}")
    print(f"СКП (sigma0): {result['sigma0']:.6f} мм")

    # Проверяем компоненты СКО
    residuals = result['residuals']
    weights_array = np.array(weights)

    numerator = np.sum(weights_array * residuals**2)
    r = n_obs - n_unknowns

    print("\nКомпоненты СКО:")
    print(f"Числитель (v^T * P * v): {numerator:.10f}")
    print(f"Степени свободы (r): {r}")
    print(f"СКП = sqrt({numerator:.6f} / {r}) = {np.sqrt(numerator/r):.6f}")

    # Проверяем ранг матрицы
    N = A.T @ P @ A
    N_dense = N.toarray()
    rank = np.linalg.matrix_rank(N_dense, tol=1e-10)
    print(f"Ранг нормальной матрицы: {rank}/{n_unknowns}")

    # Проверяем определитель (для небольших матриц)
    if n_unknowns <= 10:
        det = np.linalg.det(N_dense)
        print(f"Определитель нормальной матрицы: {det:.2e}")

print("\nДиагностика завершена.")