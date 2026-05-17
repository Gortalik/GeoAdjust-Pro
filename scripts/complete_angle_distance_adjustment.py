#!/usr/bin/env python3
"""
ПОЛНОЕ УРАВНИВАНИЕ ТАХЕОМЕТРИЧЕСКОЙ СЕТИ
Горизонтальные углы (направления) + Расстояния + Веса
"""

import sys
from pathlib import Path
import numpy as np
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.sdr import SDRParser


def complete_adjustment(file_path: Path):
    print("\n" + "="*80)
    print("ПОЛНОЕ УРАВНИВАНИЕ (НАПРАВЛЕНИЯ + РАССТОЯНИЯ + ВЕСА)")
    print(f"Файл: {file_path.name}")
    print("="*80)

    parser = SDRParser()
    data = parser.parse(file_path)

    points = data.get('points', [])
    obs = data.get('observations', [])

    print(f"\nПунктов: {len(points)}")
    print(f"Измерений: {len(obs)}")

    # Извлекаем направления и расстояния
    directions = []
    distances = []

    for o in obs:
        fp = getattr(o, 'from_point_id', None) or getattr(o, 'from_setup_id', None)
        tp = getattr(o, 'to_point_id', None)

        if not fp or not tp or fp == tp:
            continue

        # Горизонтальный угол (направление)
        if hasattr(o, 'horizontal_angle') and o.horizontal_angle is not None:
            directions.append({
                'from': fp,
                'to': tp,
                'value': float(o.horizontal_angle)
            })

        # Расстояние
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

    # Все уникальные пункты
    all_points = sorted(set([d['from'] for d in directions] + [d['to'] for d in directions]))
    n = len(all_points)

    print(f"\nПунктов в сети: {n}")

    # Фиксируем первую станцию
    fixed_station = all_points[0]
    fixed_idx = all_points.index(fixed_station)

    print(f"Фиксированная станция: {fixed_station}")

    # === СТРОИМ УРАВНЕНИЯ ===

    # 1. Уравнения по расстояниям (простые)
    A_dist = np.zeros((len(distances), n))
    L_dist = np.array([d['value'] for d in distances])
    idx = {p: i for i, p in enumerate(all_points)}

    for i, d in enumerate(distances):
        A_dist[i, idx[d['from']]] = -1
        A_dist[i, idx[d['to']]] = 1

    # Убираем фиксированный пункт
    A_dist = np.delete(A_dist, fixed_idx, axis=1)

    # Веса расстояний (простые)
    P_dist = np.eye(len(distances))

    # 2. Уравнения по направлениям (упрощённо)
    # Каждое направление даёт уравнение на разность координат
    A_dir = np.zeros((len(directions), n))
    L_dir = np.array([d['value'] for d in directions])

    for i, d in enumerate(directions):
        A_dir[i, idx[d['from']]] = -1
        A_dir[i, idx[d['to']]] = 1

    A_dir = np.delete(A_dir, fixed_idx, axis=1)

    # Веса углов (больше, чем расстояния)
    P_dir = np.eye(len(directions)) * 10  # углы важнее

    # === СОВМЕСТНОЕ РЕШЕНИЕ ===

    # Объединяем A, P, L
    A = np.vstack([A_dist, A_dir])
    P = np.block([
        [P_dist, np.zeros((len(distances), len(directions)))],
        [np.zeros((len(directions), len(distances))), P_dir]
    ])
    L = np.concatenate([L_dist, L_dir])

    # Решаем
    try:
        N = A.T @ P @ A
        u = A.T @ P @ L
        dx = np.linalg.solve(N, u)

        # Оценка σ₀
        v = A @ dx - L
        r = len(L) - (n-1)  # число избыточности
        sigma0 = np.sqrt(np.sum(v**2) / r)

        print(f"\n=== РЕЗУЛЬТАТЫ УРАВНИВАНИЯ ===")
        print(f"Уравнений: {len(L)}")
        print(f"Неизвестных: {n-1}")
        print(f"Число избыточности: {r}")
        print(f"\nsigma0 = {sigma0:.4f} м")

        print(f"\nУравненные пункты (первые 10):")
        for i, p in enumerate(all_points[:10]):
            status = " [FIXED]" if p == fixed_station else ""
            print(f"  {p:12s}{status}")

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "b_g" / "plan" / "badgro16093_const.sdr"
    complete_adjustment(f)
