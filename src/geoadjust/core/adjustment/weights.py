"""Расчёт весов наблюдений по СП 11-104-97 и ГОСТ 22267-76"""
from dataclasses import dataclass
from enum import Enum

import numpy as np


class ObsType(Enum):
    """Типы наблюдений для расчёта весов"""
    LEVELING = "leveling"
    DISTANCE = "distance"
    ANGLE = "angle"
    DIRECTION = "direction"

@dataclass
class InstrumentSpec:
    """Характеристики прибора по паспорту"""
    a_mm: float = 2.0      # постоянная погрешность (мм)
    b_ppm: float = 2.0     # зависящая от расстояния (ppm)
    m_sec: float = 1.0     # точность угловых измерений (сек)
    class_code: str = "4"  # класс нивелира/тахеометра (1, 2, 3, 4, tech)

# Нормативные значения СКП для классов нивелирования (мм/√км)
LEVELING_CLASS_MH = {
    "1": 0.8,   # I класс
    "2": 1.2,   # II класс
    "3": 3.0,   # III класс
    "4": 5.0,   # IV класс
    "tech": 10.0,  # Техническое
}

def calculate_weight(
    obs_type: ObsType,
    value: float,
    distance: float = 1.0,
    spec: InstrumentSpec = None
) -> float:
    """
    Расчёт веса наблюдения по СП 11-104-97 / ГОСТ 22267-76.
    
    Args:
        obs_type: Тип наблюдения
        value: Измеренное значение (превышение в м, угол в рад)
        distance: Длина хода в км (для нивелирования) или расстояние в м (для линий)
        spec: Характеристики прибора
        
    Returns:
        float: Вес наблюдения (обратная дисперсия)
    """
    if spec is None:
        spec = InstrumentSpec()

    try:
        if obs_type == ObsType.LEVELING:
            return _calculate_leveling_weight(distance, spec.class_code)
        elif obs_type == ObsType.DISTANCE:
            return _calculate_distance_weight(distance, spec)
        elif obs_type in (ObsType.ANGLE, ObsType.DIRECTION):
            return _calculate_angle_weight(spec.m_sec)
        else:
            return 1.0
    except Exception:
        # Fallback для избежания деления на ноль
        return 1e6

def _calculate_leveling_weight(distance_km: float, class_code: str) -> float:
    """Вес для нивелирования: σ_h² = m_h² * L"""
    m_h_mm = LEVELING_CLASS_MH.get(class_code, 5.0)  # мм/√км
    m_h_m = m_h_mm * 1e-3  # перевод в метры

    # Дисперсия: σ² = m_h² * L (L в км)
    sigma_sq = (m_h_m ** 2) * max(distance_km, 0.001)

    # Вес = 1/σ²
    return 1.0 / sigma_sq if sigma_sq > 1e-12 else 1e6

def _calculate_distance_weight(distance_m: float, spec: InstrumentSpec) -> float:
    """Вес для расстояний: σ_d² = a² + (b·d)²"""
    a = spec.a_mm * 1e-3  # перевод в метры
    b = spec.b_ppm * 1e-6  # ppm

    # Дисперсия
    sigma_sq = a**2 + (b * distance_m)**2

    return 1.0 / sigma_sq if sigma_sq > 1e-12 else 1e6

def _calculate_angle_weight(m_sec: float) -> float:
    """Вес для углов: σ_α² = (m_сек / ρ_сек)²"""
    rho_sec = 206264.806  # количество секунд в радиане

    # Дисперсия в радианах
    sigma_sq = (m_sec / rho_sec) ** 2

    return 1.0 / sigma_sq if sigma_sq > 1e-12 else 1e6

def build_weight_matrix(
    observations: list,
    spec: InstrumentSpec = None
) -> np.ndarray:
    """
    Построение диагональной матрицы весов P для списка наблюдений.
    
    Args:
        observations: Список Observation
        spec: Характеристики прибора
        
    Returns:
        np.ndarray: Диагональная матрица весов (1D массив для scipy.sparse.diags)
    """
    if spec is None:
        spec = InstrumentSpec()

    weights = []
    for obs in observations:
        w = calculate_weight(obs.type, obs.value, obs.distance, spec)
        weights.append(w)

    return np.array(weights)
