#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест свободного уравнивания
"""

import sys
import os

from geoadjust.core.adjustment.equations_builder import EquationsBuilder
import numpy as np
import scipy.sparse as sparse

print('Testing Free Adjustment...')

# Создаем тестовую сеть без фиксированных точек
points = {
    'P1': type('Point', (), {'id': 'P1', 'x': None, 'y': None, 'z': None, 'plan_status': 'working', 'height_status': 'working'})(),
    'P2': type('Point', (), {'id': 'P2', 'x': None, 'y': None, 'z': None, 'plan_status': 'working', 'height_status': 'working'})(),
    'P3': type('Point', (), {'id': 'P3', 'x': None, 'y': None, 'z': None, 'plan_status': 'working', 'height_status': 'working'})(),
}

# Создаем простые наблюдения
observations = [
    type('Obs', (), {'obs_id': '1', 'obs_type': 'distance', 'from_setup_id': 'S1', 'from_point_id': 'P1', 'to_point_id': 'P2', 'value': 100.0})(),
    type('Obs', (), {'obs_id': '2', 'obs_type': 'distance', 'from_setup_id': 'S1', 'from_point_id': 'P2', 'to_point_id': 'P3', 'value': 100.0})(),
]

builder = EquationsBuilder()

try:
    A, L = builder.build_adjustment_matrix(points, observations)
    print(f'Matrix A shape: {A.shape}')
    print(f'Vector L shape: {L.shape}')
    print('Equations builder works!')
except Exception as e:
    print(f'Error in equations builder: {e}')

# Тест SVD для свободного уравнивания
print('Testing SVD for free adjustment...')
try:
    N = A.T @ A  # Нормальная матрица
    N_dense = N.toarray()
    U, s, Vt = np.linalg.svd(N_dense, full_matrices=False)
    print(f'SVD successful: {len(s)} singular values')
    print(f'Largest singular value: {s[0]:.6f}')
    print(f'Smallest singular value: {s[-1]:.6f}')
except Exception as e:
    print(f'SVD error: {e}')