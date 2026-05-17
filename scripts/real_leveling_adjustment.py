#!/usr/bin/env python3
"""
Реальное уравнивание нивелирного хода на реальных данных.
Фиксируем первый пункт H = 0.000 м.
Выводим уравненные высоты и СКО.
"""

import sys
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix, eye
from scipy.sparse.linalg import spsolve
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser


def adjust_real_leveling(file_path: Path):
    print("\n" + "="*70)
    print(f"РЕАЛЬНОЕ УРАВНИВАНИЕ НИВЕЛИРНОГО ХОДА")
    print(f"Файл: {file_path.name}")
    print("="*70)

    parser = GSIParser()
    data = parser.parse(file_path)

    obs = data.get('observations', [])
    points = data.get('points', [])

    # Извлекаем превышения
    dh = []
    from_p = []
    to_p = []

    for o in obs:
        # Берём только полноценные превышения (задняя-передняя), игнорируем промежуточные
        if hasattr(o, 'obs_type') and o.obs_type == 'leveling_height_diff':
            fp = getattr(o, 'from_point', '')
            tp = getattr(o, 'to_point', '')
            # Пропускаем кривые измерения, где from == to
            if fp and tp and fp != tp:
                dh.append(float(getattr(o, 'value', 0.0)))
                from_p.append(fp)
                to_p.append(tp)

    if len(dh) == 0:
        print("Нет превышений для уравнивания")
        return

    print(f"Измерений (превышений): {len(dh)}")

    # Все уникальные пункты
    all_points = sorted(set(from_p + to_p))
    n = len(all_points)
    m = len(dh)

    print(f"Пунктов в сети: {n}")

    # Фиксируем первый пункт (H = 0.000)
    fixed_point = all_points[0]
    fixed_idx = all_points.index(fixed_point)
    print(f"Исходный пункт: {fixed_point} (H = 0.000 м)")

    # Строим матрицу A (m x n)
    A = np.zeros((m, n))
    L = np.array(dh)

    point_index = {p: i for i, p in enumerate(all_points)}

    for i in range(m):
        j_from = point_index[from_p[i]]
        j_to = point_index[to_p[i]]
        A[i, j_from] = -1.0
        A[i, j_to] = 1.0

    # Убираем фиксированный пункт (делаем его столбец нулевым)
    A = np.delete(A, fixed_idx, axis=1)
    n_free = n - 1

    # Веса (простые, p=1)
    P = np.eye(m)

    # Нормальные уравнения
    N = A.T @ P @ A
    u = A.T @ P @ L

    # Решаем
    try:
        dx = np.linalg.solve(N, u)
    except np.linalg.LinAlgError:
        print("Система вырожденная, используем псевдообратную")
        dx = np.linalg.pinv(N) @ u

    # Восстанавливаем высоты
    H = np.zeros(n)
    H[fixed_idx] = 0.0
    free_idx = [i for i in range(n) if i != fixed_idx]
    H[free_idx] = dx

    # СКО
    v = A @ dx - L
    sigma0 = np.sqrt(np.sum(v**2) / (m - n_free))

    print(f"\nРезультаты уравнивания:")
    print(f"  sigma0 = {sigma0:.4f} m")
    print(f"  Число уравнений: {m}")
    print(f"  Число неизвестных: {n_free}")

    print(f"\nУравненные высоты (первые 10):")
    for i in range(min(10, n)):
        print(f"  {all_points[i]:12s}  H = {H[i]:8.3f} м")

    if n > 10:
        print(f"  ... и ещё {n-10} пунктов")


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "s5" / "niv" / "MIR0212.GSI"
    adjust_real_leveling(f)
