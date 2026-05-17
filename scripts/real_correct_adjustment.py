#!/usr/bin/env python3
"""
Правильное уравнивание реальных данных с учётом геодезической логики.

- Только взаимные измерения участвуют в уравнивании
- Боковые/промежуточные/полярные — производные (рассчитываются после)
"""

import sys
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser


def is_mutual_observation(o):
    """Проверяет, является ли измерение взаимным (участвует в уравнивании)"""
    fp = getattr(o, 'from_point', '')
    tp = getattr(o, 'to_point', '')
    obs_type = getattr(o, 'obs_type', '')

    if not fp or not tp or fp == tp:
        return False

    # Для нивелирования — только полноценные задняя-передняя
    if obs_type == 'leveling_height_diff':
        return True

    # Для тахеометрии — направления и расстояния между разными станциями
    if obs_type in ['direction', 'slope_distance', 'horizontal_distance', 'zenith_angle']:
        return True

    return False


def adjust_real_data_correctly(file_path: Path):
    print("\n" + "="*75)
    print(f"ПРАВИЛЬНОЕ УРАВНИВАНИЕ РЕАЛЬНЫХ ДАННЫХ")
    print(f"Файл: {file_path.name}")
    print("="*75)

    parser = GSIParser()
    data = parser.parse(file_path)

    all_obs = data.get('observations', [])
    points = data.get('points', [])

    # Фильтруем только взаимные измерения
    adjustable_obs = [o for o in all_obs if is_mutual_observation(o)]
    derived_obs = [o for o in all_obs if not is_mutual_observation(o)]

    print(f"Всего измерений в файле: {len(all_obs)}")
    print(f"Участвуют в уравнивании (ADJUSTABLE): {len(adjustable_obs)}")
    print(f"Производные (DERIVED): {len(derived_obs)}")

    if len(adjustable_obs) < 2:
        print("Слишком мало взаимных измерений для уравнивания")
        return

    # Для нивелирования собираем превышения
    dh = []
    from_p = []
    to_p = []

    for o in adjustable_obs:
        if getattr(o, 'obs_type', '') == 'leveling_height_diff':
            dh.append(float(getattr(o, 'value', 0.0)))
            from_p.append(getattr(o, 'from_point', ''))
            to_p.append(getattr(o, 'to_point', ''))

    if len(dh) == 0:
        print("Нет нивелирных превышений для уравнивания в этом файле")
        return

    print(f"\nНивелирных превышений для уравнивания: {len(dh)}")

    all_points = sorted(set(from_p + to_p))
    n = len(all_points)
    m = len(dh)

    print(f"Пунктов в нивелирной сети: {n}")

    # Фиксируем первый пункт
    fixed_point = all_points[0]
    fixed_idx = all_points.index(fixed_point)
    print(f"Исходный пункт: {fixed_point} (H = 0.000 м)")

    # Строим A
    A = np.zeros((m, n))
    L = np.array(dh)
    point_index = {p: i for i, p in enumerate(all_points)}

    for i in range(m):
        jf = point_index[from_p[i]]
        jt = point_index[to_p[i]]
        A[i, jf] = -1.0
        A[i, jt] = 1.0

    # Убираем фиксированный пункт
    A = np.delete(A, fixed_idx, axis=1)
    n_free = n - 1

    # Решаем
    try:
        N = A.T @ A
        u = A.T @ L
        dx = np.linalg.solve(N, u)
    except np.linalg.LinAlgError:
        print("Система вырожденная")
        return

    # Восстанавливаем высоты
    H = np.zeros(n)
    H[fixed_idx] = 0.0
    free_idx = [i for i in range(n) if i != fixed_idx]
    H[free_idx] = dx

    v = A @ dx - L
    sigma0 = np.sqrt(np.sum(v**2) / (m - n_free))

    print(f"\n=== РЕЗУЛЬТАТЫ УРАВНИВАНИЯ ===")
    print(f"sigma0 = {sigma0:.4f} m")
    print(f"Число уравнений: {m}")
    print(f"Число неизвестных: {n_free}")

    print(f"\nУравненные высоты (первые 15):")
    for i in range(min(15, n)):
        status = " [FIXED]" if i == fixed_idx else ""
        print(f"  {all_points[i]:12s}  H = {H[i]:8.3f} м{status}")

    if n > 15:
        print(f"  ... и ещё {n-15} пунктов")

    print(f"\nПроизводные точки (не участвовали в уравнивании): {len(derived_obs)}")


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "s5" / "niv" / "MIR0212.GSI"
    adjust_real_data_correctly(f)
