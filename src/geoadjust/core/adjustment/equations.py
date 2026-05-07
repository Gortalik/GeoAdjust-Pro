"""Построение линеаризованных уравнений погрешностей"""
import numpy as np
import scipy.sparse as sp
from typing import List, Tuple, Dict
from dataclasses import dataclass
from .weights import InstrumentSpec, calculate_weight, ObsType

@dataclass
class Observation:
    """Модель наблюдения (дублирование для автономности модуля)"""
    station_id: str
    target_id: str
    value: float
    distance: float = 1.0
    type: ObsType = ObsType.LEVELING

def build_linearized_equations(
    observations: List[Observation],
    point_indices: Dict[str, int],
    approximate_coords: Dict[str, float],
    spec: InstrumentSpec
) -> Tuple[sp.csr_matrix, np.ndarray, sp.diags]:
    """
    Формирование матриц A, L, P для линеаризованных уравнений погрешностей.
    
    Для нивелирования: l = h_изм - (H_target₀ - H_station₀)
    Матрица A: d(h)/dH_s = -1, d(h)/dH_t = +1
    
    Args:
        observations: Список наблюдений
        point_indices: Маппинг {punkt_id: index_in_matrix}
        approximate_coords: Приближённые высоты {punkt_id: H_approx}
        spec: Характеристики прибора для расчёта весов
        
    Returns:
        Tuple[A, L, P]: 
            A - матрица коэффициентов (m×n, разреженная)
            L - вектор свободных членов (невязки)
            P - диагональная матрица весов
    """
    m = len(observations)
    n = len(point_indices)
    
    if m == 0 or n == 0:
        return sp.csr_matrix((0, n)), np.array([]), sp.diags([], format="csr")
    
    # Данные для разреженной матрицы A
    rows = []
    cols = []
    data = []
    
    # Вектора L и P
    L = np.zeros(m)
    P_diag = np.zeros(m)
    
    for i, obs in enumerate(observations):
        station_idx = point_indices.get(obs.station_id)
        target_idx = point_indices.get(obs.target_id)
        
        if station_idx is None or target_idx is None:
            raise ValueError(
                f"Пункт '{obs.station_id}' или '{obs.target_id}' "
                f"отсутствует в сети"
            )
        
        # Приближённые высоты
        h0_s = approximate_coords.get(obs.station_id, 0.0)
        h0_t = approximate_coords.get(obs.target_id, 0.0)
        
        # Свободный член (невязка)
        # l = h_measured - (H_target_approx - H_station_approx)
        l_i = obs.value - (h0_t - h0_s)
        L[i] = l_i
        
        # Коэффициенты матрицы A
        # Уравнение: v = dH_t - dH_s - l
        # d(v)/dH_s = -1, d(v)/dH_t = +1
        rows.extend([i, i])
        cols.extend([station_idx, target_idx])
        data.extend([-1.0, 1.0])
        
        # Вес наблюдения
        # Для нивелирования distance интерпретируется как длина хода в км
        P_diag[i] = calculate_weight(obs.type, obs.value, obs.distance, spec)
    
    # Создание разреженной матрицы A
    A = sp.csr_matrix((data, (rows, cols)), shape=(m, n))
    
    # Диагональная матрица весов P
    P = sp.diags(P_diag, format="csr")
    
    return A, L, P

def apply_constraints(
    A: sp.csr_matrix,
    L: np.ndarray,
    P: sp.diags,
    fixed_points: Dict[str, float],
    point_indices: Dict[str, int]
) -> Tuple[sp.csr_matrix, np.ndarray, sp.diags, np.ndarray, List[int]]:
    """
    Применение ограничений на фиксированные пункты.
    
    Использует метод исключения столбцов:
    1. Вычисляет вклад фиксированных пунктов в L
    2. Удаляет столбцы фиксированных пунктов из A
    
    Args:
        A, L, P: Исходные матрицы
        fixed_points: {punkt_id: фиксированная_высота}
        point_indices: Маппинг индексов
        
    Returns:
        Tuple[A_free, L_corr, P, H_fixed_values, free_indices]
    """
    if not fixed_points:
        free_indices = list(range(A.shape[1]))
        return A, L, P, np.array([]), free_indices
    
    # Индексы фиксированных столбцов
    fixed_cols = []
    fixed_values = []
    
    for pid, h_val in sorted(fixed_points.items(), key=lambda x: point_indices[x[0]]):
        if pid in point_indices:
            fixed_cols.append(point_indices[pid])
            fixed_values.append(h_val)
    
    if not fixed_cols:
        free_indices = list(range(A.shape[1]))
        return A, L, P, np.array([]), free_indices
    
    # L_corr = L - A_fixed @ H_fixed
    A_fixed = A[:, fixed_cols]
    H_fixed = np.array(fixed_values)
    L_corr = L - A_fixed @ H_fixed
    
    # Индексы свободных столбцов
    all_cols = set(range(A.shape[1]))
    free_cols = sorted(all_cols - set(fixed_cols))
    
    # Удаление фиксированных столбцов
    if free_cols:
        A_free = A[:, free_cols]
    else:
        A_free = sp.csr_matrix((A.shape[0], 0))
    
    return A_free, L_corr, P, H_fixed, free_cols
