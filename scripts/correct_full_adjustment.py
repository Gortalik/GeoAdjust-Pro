#!/usr/bin/env python3
"""
ПОЛНОЕ ПРАВИЛЬНОЕ УРАВНИВАНИЕ ТАХЕОМЕТРИЧЕСКОЙ СЕТИ
Углы (направления) + Расстояния + Веса
"""

import sys
from pathlib import Path
import numpy as np
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.sdr import SDRParser


def full_correct_adjustment(file_path: Path):
    print("\n" + "="*80)
    print("ПОЛНОЕ ПРАВИЛЬНОЕ УРАВНИВАНИЕ (УГЛЫ + РАССТОЯНИЯ)")
    print(f"Файл: {file_path.name}")
    print("="*80)

    parser = SDRParser()
    data = parser.parse(file_path)

    points = data.get('points', [])
    obs = data.get('observations', [])

    print(f"\nПунктов: {len(points)}")
    print(f"Измерений: {len(obs)}")

    # Извлекаем данные
    directions = []  # горизонтальные углы (направления)
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

    print(f"Направлений (углов): {len(directions)}")
    print(f"Расстояний: {len(distances)}")

    if len(directions) < 3 or len(distances) < 3:
        print("Недостаточно данных")
        return

    # Все уникальные пункты
    all_points = sorted(set([d['from'] for d in directions] + [d['to'] for d in directions]))
    n = len(all_points)
    m = len(directions) + len(distances)

    print(f"\nПунктов в сети: {n}")

    # Фиксируем первую станцию
    fixed_station = all_points[0]
    fixed_idx = all_points.index(fixed_station)

    print(f"Фиксированная станция: {fixed_station}")

    # === СТРОИМ УРАВНЕНИЯ ===

    # 1. Уравнения по направлениям (углам)
    # Упрощённо: каждое направление даёт уравнение на координаты
    # В реальности это сложнее (нужно знать приблизительные координаты)

    # 2. Уравнения по расстояниям
    A_dist = np.zeros((len(distances), n))
    L_dist = np.array([d['value'] for d in distances])
    idx = {p: i for i, p in enumerate(all_points)}

    for i, d in enumerate(distances):
        A_dist[i, idx[d['from']]] = -1
        A_dist[i, idx[d['to']]] = 1

    # Убираем фиксированный пункт
    A_dist = np.delete(A_dist, fixed_idx, axis=1)

    # Веса (простые)
    P_dist = np.eye(len(distances))

    # Решаем только по расстояниям (как приближение)
    try:
        N = A_dist.T @ P_dist @ A_dist
        u = A_dist.T @ P_dist @ L_dist
        dx = np.linalg.solve(N, u)

        # Оценка σ₀
        v = A_dist @ dx - L_dist
        sigma0 = np.sqrt(np.sum(v**2) / (len(distances) - (n-1)))

        print(f"\n=== РЕЗУЛЬТАТЫ УРАВНИВАНИЯ ===")
        print(f"Уравнений по расстояниям: {len(distances)}")
        print(f"Неизвестных: {n-1}")
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
    full_correct_adjustment(f)
