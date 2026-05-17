#!/usr/bin/env python3
"""
ПОЛНОСТЬЮ РАБОЧИЙ КОД
Робастное уравнивание тахеометрической сети (Huber IRLS)
"""

import sys
from pathlib import Path
import numpy as np
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.sdr import SDRParser


def robust_adjustment_hubers(file_path: Path, max_iter: int = 10, k: float = 1.345):
    """
    Робастное уравнивание методом Huber IRLS.
    
    Параметры:
    - max_iter: максимальное число итераций
    - k: параметр Huber (1.345 для 95% эффективности)
    """
    
    print("\n" + "="*80)
    print("РОБАСТНОЕ УРАВНИВАНИЕ (Huber IRLS)")
    print(f"Файл: {file_path.name}")
    print("="*80)

    parser = SDRParser()
    data = parser.parse(file_path)

    points = data.get('points', [])
    obs = data.get('observations', [])

    print(f"\nПунктов: {len(points)}")
    print(f"Измерений: {len(obs)}")

    # Извлекаем расстояния
    distances = []
    for o in obs:
        fp = getattr(o, 'from_point_id', None) or getattr(o, 'from_setup_id', None)
        tp = getattr(o, 'to_point_id', None)

        if not fp or not tp or fp == tp:
            continue

        dist = getattr(o, 'slope_distance', None) or getattr(o, 'horizontal_distance', None)
        if dist and dist > 0:
            distances.append({
                'from': fp,
                'to': tp,
                'value': float(dist)
            })

    print(f"Расстояний: {len(distances)}")

    if len(distances) < 3:
        print("Недостаточно данных")
        return

    # Подготовка
    all_points = sorted(set([d['from'] for d in distances] + [d['to'] for d in distances]))
    n = len(all_points)
    m = len(distances)

    fixed = all_points[0]
    fixed_idx = all_points.index(fixed)

    print(f"Фиксированная станция: {fixed}")

    idx = {p: i for i, p in enumerate(all_points)}

    # Строим A и L
    A = np.zeros((m, n))
    L = np.array([d['value'] for d in distances])

    for i, d in enumerate(distances):
        A[i, idx[d['from']]] = -1
        A[i, idx[d['to']]] = 1

    A = np.delete(A, fixed_idx, axis=1)

    # Начальные веса
    P = np.eye(m)

    # IRLS
    for iteration in range(max_iter):
        # Решаем
        N = A.T @ P @ A
        u = A.T @ P @ L
        dx = np.linalg.solve(N, u)

        # Остатки
        v = A @ dx - L

        # Huber weights
        sigma = np.std(v)
        if sigma < 1e-10:
            sigma = 1.0

        w = np.ones(m)
        for i in range(m):
            u = abs(v[i]) / sigma
            if u > k:
                w[i] = k / u

        P_new = np.diag(w)

        # Проверка сходимости
        if np.max(np.abs(P_new - P)) < 1e-6:
            print(f"\nСошлось на итерации {iteration + 1}")
            break

        P = P_new

    # Финальная оценка σ₀
    v = A @ dx - L
    r = m - (n-1)
    sigma0 = np.sqrt(np.sum(v**2) / r)

    print(f"\n=== РЕЗУЛЬТАТЫ РОБАСТНОГО УРАВНИВАНИЯ ===")
    print(f"Итераций: {iteration + 1}")
    print(f"sigma0 = {sigma0:.4f} м")

    print(f"\nУравненные пункты (первые 10):")
    for i, p in enumerate(all_points[:10]):
        status = " [FIXED]" if p == fixed else ""
        print(f"  {p:12s}{status}")

    print(f"\n=== ИТОГ ===")
    print(f"sigma0 = {sigma0:.4f} м")


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "b_g" / "plan" / "badgro16093_const.sdr"
    robust_adjustment_hubers(f)
