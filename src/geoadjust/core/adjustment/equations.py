"""Построение линеаризованных уравнений погрешностей"""

from dataclasses import dataclass
import numpy as np
import scipy.sparse as sp
from typing import Dict, List, Tuple
from .weights import InstrumentSpec, ObsType, calculate_weight

# Типы координат для 3D-сети
class CoordinateSystem:
    """Система координат для 3D-сети"""
    MERCATOR = "mercator"  # 2D Mercator
    M3D = "m3d"            # 3D (X, Y, Z)
    
@dataclass
class Observation:
    """Модель наблюдения для 3D-сети"""
    station_id: str
    target_id: str
    type: ObsType = ObsType.LEVELING
    distance: float = 1.0
    value: float = 0.0
    # Стратегия веса: ERROR_BOUND или RELATIVE
    weight_strategy: str = "ERROR_BOUND"
    # Оригинальные координаты в системах измерений
    source_system: str = "WGS84"

# 2) Уравнение для/class observations
FIGURE_DEFINITION = {
    ObsType.LEVELING: "height_difference",
    ObsType.DISTANCE: "distance",
    ObsType.ANGLE_HZ: "horizontal_angle",
    ObsType.ANGLE_V: "vertical_angle"
}

# РЕАЛИЗАЦИЯ УРАВНЕНИЙ:
# Для каждого типа наблюдения:
# - Определяем количество коэффициентов (параметров)
# - Формируем конкретные коэффициенты матрицы A
# - Определяем изменения в правой части L

def build_linearized_equations(
    observations: List[Observation],
    point_indices: Dict[str, int],
    approximate_coords: Dict[str, np.ndarray],  # Полные координаты {pid: [x, y, z]}
    spec: InstrumentSpec
) -> Tuple[sp.csr_matrix, np.ndarray, sp.diags]:
    """
    Формирование матриц A, L, P для линеаризованных уравнений 3D-сети.
    
    Поддерживаются типы наблюдений:
    - LEVELING: 1 параметр (высота)
    - DISTANCE: 1 параметр (расстояние) 
    - ANGLE_HZ: 1 параметр (горизонтальный угол)
    - ANGLE_V: 1 параметр (вертикальный угол)
    
    Args:
        observations: Список наблюдений
        point_indices: Маппинг {punkt_id: index_in_matrix}
        approximate_coords: Приближённые координаты {punkt_id: [x, y, z]}
        spec: Характеристики прибора
        
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

    # Векторы L и P
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
        
        # Оригинальные координаты в их системах
        x1, y1, z1 = approximate_coords.get(obs.station_id, [0.0, 0.0, 0.0])
        x2, y2, z2 = approximate_coords.get(obs.target_id, [0.0, 0.0, 0.0])
        
        # Вычисляем разницу координат
        dx = x2 - x1
        dy = y2 - y1  
        dz = z2 - z1
        
        # Список добавляемых параметров в зависимости от типа наблюдения
        if obs.type == ObsType.LEVELING:
            # Уравнение: l = measured_height_diff - (z_target - z_station)
            l_i = obs.value - (dz)  # Высота измеряется как разность высот
            
            # Коэффициенты A для высотной поправки
            rows.extend([i, i])
            cols.extend([station_idx, target_idx])
            data.extend([-1.0, 1.0])  # d(l)/d(h_station) = -1, d(l)/d(h_target) = +1
            
            # Вес для height_difference
            P_diag[i] = calculate_weight(obs.type, obs.value, obs.distance, spec)
            
        elif obs.type == ObsType.DISTANCE:
            # Уравнение: l = measured_distance - distance_target_station
            measured_dist = obs.value
            computed_dist = np.sqrt(dx*dx + dy*dy + dz*dz)
            l_i = measured_dist - computed_dist
            
            # Для расстояний: d(l)/dx = -dx/dist, d(l)/dy = -dy/dist, d(l)/dz = -dz/dist
            # В 1D-подходе учитываем только один параметр (расстояние)
            rows.extend([i])
            cols.extend([station_idx])  # Упрощаем: только один параметр
            data.extend([-1.0])  # Простой флаг для 1D
            
            # Вес для distance
            P_diag[i] = calculate_weight(obs.type, obs.value, obs.distance, spec)
            
        elif obs.type == ObsType.ANGLE_HZ:
            # Уравнение: l = measured_angle - computed_angle
            # Для угла вычисляем разность через тангенс
            computed_angle = np.arctan2(dy, dx) * 180/np.pi  # Угол в градусах
            l_i = obs.value - computed_angle
            
            # Коэффициенты A (упрощённая линейизация)
            rows.extend([i])
            cols.extend([station_idx])
            data.extend([-1.0])
            
            # Вес для angle_hz
            P_diag[i] = calculate_weight(obs.type, obs.value, obs.distance, spec)
            
        elif obs.type == ObsType.ANGLE_V:
            # Уравнение: l = measured_angle - computed_vertical_angle
            computed_angle = np.arctan2(dz, np.sqrt(dx*dx + dy*dy)) * 180/np.pi
            l_i = obs.value - computed_angle
            
            # Коэффициенты A
            rows.extend([i])
            cols.extend([station_idx])
            data.extend([-1.0])
            
            # Вес для angle_v
            P_diag[i] = calculate_weight(obs.type, obs.value, obs.distance, spec)
        
        else:
            raise ValueError(f"Неподдерживаемый тип наблюдения: {obs.type}")
        
        # Формируем вектор невязки
        L[i] = l_i
    
    # Создание разреженной матрицы A
    A = sp.csr_matrix((data, (rows, cols)), shape=(m, n))
    
    # Диагональная матрица весов P
    P = sp.diags(P_diag, format="csr")
    
    return A, L, P

def apply_constraints(
    A: sp.csr_matrix,
    L: np.ndarray,
    P: sp.diags,
    fixed_points: Dict[str, np.ndarray],
    point_indices: Dict[str, int]
) -> Tuple[sp.csr_matrix, np.ndarray, sp.diags, np.ndarray, List[int]]:
    """
    Применение ограничений на фиксированные пункты для 3D-сетей.
    
    Args:
        A, L, P: Исходные матрицы (A имеет вид (m, 3*n))
        fixed_points: {punkt_id: [x, y, z]}
        point_indices: Маппинг индексов
        
    Returns:
        Tuple[A_free, L_corr, P, H_fixed_values, free_indices]
    """
    if not fixed_points:
        free_indices = list(range(A.shape[1]))
        return A, L, P, np.array([]), free_indices

    fixed_cols = []
    fixed_values = []

    for pid, coords in sorted(fixed_points.items(), key=lambda x: point_indices.get(x[0], 0)):
        if pid in point_indices:
            idx = point_indices[pid]
            fixed_cols.extend([3*idx, 3*idx+1, 3*idx+2])
            fixed_values.extend(coords.tolist())

    if not fixed_cols:
        free_indices = list(range(A.shape[1]))
        return A, L, P, np.array([]), free_indices

    A_fixed = A[:, fixed_cols]
    H_fixed = np.array(fixed_values)
    L_corr = L - A_fixed @ H_fixed

    all_cols = set(range(A.shape[1]))
    free_cols = sorted(all_cols - set(fixed_cols))

    if free_cols:
        A_free = A[:, free_cols]
    else:
        A_free = sp.csr_matrix((A.shape[0], 0))

    return A_free, L_corr, P, H_fixed, free_cols
