#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест движка уравнивания
"""

import sys
import os

from geoadjust.core.adjustment.engine import AdjustmentEngine
import numpy as np
import scipy.sparse as sparse

print('Testing AdjustmentEngine...')

# Создаем тестовую систему
n_obs = 5
n_params = 4

# Матрица коэффициентов (пример для простого случая)
A_data = [
    [1, -1, 0, 0],  # уравнение 1: x1 - x2 = 0
    [0, 1, -1, 0],  # уравнение 2: x2 - x3 = 0
    [0, 0, 1, -1],  # уравнение 3: x3 - x4 = 0
    [1, 0, 0, -1],  # уравнение 4: x1 - x4 = 0
    [0, 1, 0, 0]    # уравнение 5: x2 = 0 (фиксация)
]

A = sparse.csr_matrix(A_data)
L = np.array([0, 0, 0, 0, 0])  # правые части
P = sparse.diags([1.0]*n_obs)   # веса

engine = AdjustmentEngine()
result = engine.adjust(A, L, P)

print(f'Success: {result is not None}')
if result:
    print(f'Iterations: {result.get("iterations", "N/A")}')
    print(f'Sigma0: {result.get("sigma0", 0):.6f}')
    residuals = result.get('residuals', [])
    print(f'Residuals count: {len(residuals)}')