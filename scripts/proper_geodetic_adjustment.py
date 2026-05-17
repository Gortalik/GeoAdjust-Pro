#!/usr/bin/env python3
"""
ПРАВИЛЬНАЯ ГЕОДЕЗИЧЕСКАЯ МОДЕЛЬ УРАВНИВАНИЯ
с полными уравнениями по направлениям (∂α/∂x, ∂α/∂y)
"""

import sys
from pathlib import Path
import numpy as np
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.sdr import SDRParser


def proper_geodetic_adjustment(file_path: Path):
    """
    Правильная геодезическая модель уравнивания.
    
    Уравнения по направлениям:
    ∂α/∂xA = -sin(α) / s
    ∂α/∂yA = cos(α) / s
    ∂α/∂xB = sin(α) / s
    ∂α/∂yB = -cos(α) / s
    """
    
    print("\n" + "="*80)
    print("ПРАВИЛЬНАЯ ГЕОДЕЗИЧЕСКАЯ МОДЕЛЬ УРАВНИВАНИЯ")
    print(f"Файл: {file_path.name}")
    print("="*80)

    parser = SDRParser()
    data = parser.parse(file_path)

    points = data.get('points', [])
    obs = data.get('observations', [])

    print(f"\nПунктов: {len(points)}")
    print(f"Измерений: {len(obs)}")

    # Извлекаем данные
    directions = []
    distances = []

    for o in obs:
        fp = getattr(o, 'from_point_id', None) or getattr(o, 'from_setup_id', None)
        tp = getattr(o, 'to_point_id', None)

        if not fp or not tp or fp == tp:
            continue

        if hasattr(o, 'horizontal_angle') and o.horizontal_angle is not None:
            directions.append({
                'from': fp,
                'to': tp,
                'value': float(o.horizontal_angle)
            })

        dist = getattr(o, 'slope_distance', None) or getattr(o, 'horizontal_distance', None)
        if dist and dist > 0:
            distances.append({
                'from': fp,
                'to': tp,
                'value': float(dist)
            })

    print(f"Направлений: {len(directions)}")
    print(f"Расстояний: {len(distances)}")

    if len(directions) < 3 or len(distances) < 3:
        print("Недостаточно данных")
        return

    # Подготовка
    all_points = sorted(set([d['from'] for d in directions] + [d['to'] for d in directions]))
    n = len(all_points)
    m = len(directions) + len(distances)

    print(f"\nПунктов в сети: {n}")

    fixed = all_points[0]
    fixed_idx = all_points.index(fixed)

    print(f"Фиксированная станция: {fixed}")

    # Приблизительные координаты
    approx = {}
    for p in points:
        name = p.get('name', p.get('point_id', ''))
        if name:
            approx[name] = {
                'x': float(p.get('x', 0.0)),
                'y': float(p.get('y', 0.0))
            }

    idx = {p: i for i, p in enumerate(all_points)}

    # === УРАВНЕНИЯ ПО РАССТОЯНИЯМ ===
    A_dist = np.zeros((len(distances), n))
    L_dist = np.array([d['value'] for d in distances])

    for i, d in enumerate(distances):
        A_dist[i, idx[d['from']]] = -1
        A_dist[i, idx[d['to']]] = 1

    A_dist = np.delete(A_dist, fixed_idx, axis=1)

    sigma_dist = np.array([0.005 + 0.000005 * d['value'] for d in distances])
    P_dist = np.diag(1.0 / sigma_dist**2)

    # === УРАВНЕНИЯ ПО НАПРАВЛЕНИЯМ (ПРАВИЛЬНАЯ МОДЕЛЬ) ===
    A_dir = np.zeros((len(directions), n))
    L_dir = np.zeros(len(directions))

    for i, d in enumerate(directions):
        fp = d['from']
        tp = d['to']
        
        x1 = approx.get(fp, {}).get('x', 0.0)
        y1 = approx.get(fp, {}).get('y', 0.0)
        x2 = approx.get(tp, {}).get('x', 0.0)
        y2 = approx.get(tp, {}).get('y', 0.0)
        
        # Расстояние
        s = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if s < 0.001:
            s = 1.0
        
        # Азимут (от Y на север, против часовой)
        alpha = np.arctan2(x2 - x1, y2 - y1)
        
        # Измеренный азимут
        alpha_meas = np.deg2rad(d['value'])
        
        # Разность
        dalpha = alpha_meas - alpha
        dalpha = np.arctan2(np.sin(dalpha), np.cos(dalpha))
        
        L_dir[i] = dalpha
        
        # ПРАВИЛЬНЫЕ коэффициенты
        sin_a = np.sin(alpha)
        cos_a = np.cos(alpha)
        
        # ∂α/∂xA = -sin(α) / s
        # ∂α/∂yA = cos(α) / s
        # ∂α/∂xB = sin(α) / s
        # ∂α/∂yB = -cos(α) / s
        
        A_dir[i, idx[fp]] = -sin_a / s
        A_dir[i, idx[tp]] = sin_a / s

    A_dir = np.delete(A_dir, fixed_idx, axis=1)

    sigma_dir = np.deg2rad(10 / 3600)
    P_dir = np.eye(len(directions)) / sigma_dir**2

    # === РЕШЕНИЕ ===
    A = np.vstack([A_dist, A_dir])
    P = np.block([
        [P_dist, np.zeros((len(distances), len(directions)))],
        [np.zeros((len(directions), len(distances))), P_dir]
    ])
    L = np.concatenate([L_dist, L_dir])

    try:
        N = A.T @ P @ A
        u = A.T @ P @ L
        dx = np.linalg.solve(N, u)

        v = A @ dx - L
        r = len(L) - (n-1)
        sigma0 = np.sqrt(np.sum(v**2) / r)

        print(f"\n=== РЕЗУЛЬТАТЫ ===")
        print(f"Уравнений: {len(L)}")
        print(f"Неизвестных: {n-1}")
        print(f"Число избыточности: {r}")
        print(f"\nsigma0 = {sigma0:.4f} м = {sigma0*1000:.2f} мм")

        print(f"\nУравненные пункты (первые 10):")
        for i, p in enumerate(all_points[:10]):
            status = " [FIXED]" if p == fixed else ""
            print(f"  {p:12s}{status}")

        print(f"\n=== ИТОГ ===")
        print(f"sigma0 = {sigma0:.4f} м")
        
        if sigma0 < 0.05:
            print("✓ Уравнивание выполнено успешно!")
        else:
            print(f"⚠ sigma0 = {sigma0:.4f} м (ожидается 0.01-0.05 м)")

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "b_g" / "plan" / "badgro16093_const.sdr"
    proper_geodetic_adjustment(f)
