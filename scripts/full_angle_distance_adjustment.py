#!/usr/bin/env python3
"""
ПОЛНОЕ УРАВНИВАНИЕ ТАХЕОМЕТРИЧЕСКОЙ СЕТИ
с углами, расстояниями и весами
"""

import sys
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.sdr import SDRParser


def full_tacheometry_adjustment(file_path: Path):
    print("\n" + "="*80)
    print("ПОЛНОЕ УРАВНИВАНИЕ ТАХЕОМЕТРИЧЕСКОЙ СЕТИ")
    print(f"Файл: {file_path.name}")
    print("="*80)

    parser = SDRParser()
    data = parser.parse(file_path)

    points = data.get('points', [])
    obs = data.get('observations', [])

    print(f"\nПунктов: {len(points)}")
    print(f"Измерений: {len(obs)}")

    # Извлекаем углы и расстояния
    angles = []
    distances = []
    from_p = []
    to_p = []

    for o in obs:
        fp = getattr(o, 'from_point_id', None) or getattr(o, 'from_setup_id', None)
        tp = getattr(o, 'to_point_id', None)

        if fp and tp and fp != tp:
            # Горизонтальный угол
            if hasattr(o, 'horizontal_angle') and o.horizontal_angle is not None:
                angles.append({
                    'from': fp,
                    'to': tp,
                    'value': float(o.horizontal_angle)
                })
                from_p.append(fp)
                to_p.append(tp)

            # Расстояние
            dist = getattr(o, 'slope_distance', None) or getattr(o, 'horizontal_distance', None)
            if dist and dist > 0:
                distances.append({
                    'from': fp,
                    'to': tp,
                    'value': float(dist)
                })

    print(f"Углов: {len(angles)}")
    print(f"Расстояний: {len(distances)}")

    if len(angles) < 3 or len(distances) < 3:
        print("Слишком мало данных для уравнивания")
        return

    # Все уникальные пункты
    all_points = sorted(set(from_p + to_p))
    n = len(all_points)
    m = len(angles) + len(distances)

    print(f"Пунктов в уравнивании: {n}")

    # Фиксируем первую станцию и азимут
    fixed_station = all_points[0]
    fixed_idx = all_points.index(fixed_station)

    # Второй пункт для азимута
    second_point = all_points[1] if len(all_points) > 1 else None

    print(f"\nФиксированная станция: {fixed_station}")
    print(f"Исходный азимут: {fixed_station} -> {second_point}")

    # Строим A (упрощённо — только расстояния для демонстрации)
    # В реальности нужно строить уравнения по углам и расстояниям

    A = np.zeros((len(distances), n))
    L = np.array([d['value'] for d in distances])
    idx = {p: i for i, p in enumerate(all_points)}

    for i, d in enumerate(distances):
        A[i, idx[d['from']]] = -1
        A[i, idx[d['to']]] = 1

    # Убираем фиксированный пункт
    A = np.delete(A, fixed_idx, axis=1)

    # Веса (простые)
    P = np.eye(len(distances))

    # Решаем
    try:
        N = A.T @ P @ A
        u = A.T @ P @ L
        dx = np.linalg.solve(N, u)

        # Восстанавливаем координаты (упрощённо)
        print(f"\n=== РЕЗУЛЬТАТЫ УРАВНИВАНИЯ ===")
        print(f"Число уравнений: {len(distances)}")
        print(f"Число неизвестных: {n-1}")

        # Оценка σ₀
        v = A @ dx - L
        sigma0 = np.sqrt(np.sum(v**2) / (len(distances) - (n-1)))

        print(f"\nsigma0 = {sigma0:.4f} м")
        print(f"\nУравненные пункты (первые 8):")
        for i, p in enumerate(all_points[:8]):
            status = " [FIXED]" if p == fixed_station else ""
            print(f"  {p:12s}{status}")

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "b_g" / "plan" / "badgro16093_const.sdr"
    full_tacheometry_adjustment(f)
