"""Свободное уравнивание для обнаружения грубых ошибок (Baarda's Data Snooping)"""
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from loguru import logger

from geoadjust.io.base import Observation

from .equations import apply_constraints, build_linearized_equations
from .weights import InstrumentSpec


@dataclass
class FreeAdjustmentResult:
    """Результат свободного уравнивания"""
    residuals: np.ndarray           # Невязки наблюдений
    normalized_residuals: np.ndarray  # Нормализованные невязки (w_i)
    gross_errors: List[int]         # Индексы подозрительных наблюдений
    sigma_0: float                  # СКП единицы веса
    status: str                     # Статус выполнения

def run_free_adjustment(
    observations: List[Observation],
    spec: InstrumentSpec,
    threshold: float = 3.0
) -> FreeAdjustmentResult:
    """
    Предварительное свободное уравнивание для обнаружения грубых ошибок.
    
    Алгоритм:
    1. Фиксируем один пункт (снимаем ранговую дефектность)
    2. Выполняем одно итерационное уравнивание
    3. Вычисляем нормализованные невязки w_i = v_i * √P_ii / σ₀
    4. Помечаем наблюдения с |w_i| > threshold как потенциально грубые
    
    Args:
        observations: Список наблюдений
        spec: Характеристики прибора
        threshold: Порог отсечки (обычно 2.5-3.5)
        
    Returns:
        FreeAdjustmentResult: Результаты диагностики
    """
    if not observations:
        return FreeAdjustmentResult(
            residuals=np.array([]),
            normalized_residuals=np.array([]),
            gross_errors=[],
            sigma_0=0.0,
            status="no_observations"
        )

    try:
        # 1. Построение индексов пунктов
        point_indices, approx_coords = _build_initial_indices(observations)

        # Фиксируем первый пункт для снятия ранговой дефектности
        first_point = observations[0].station_id
        fixed_points = {first_point: 0.0}

        # 2. Построение уравнений
        A, L, P = build_linearized_equations(
            observations, point_indices, approx_coords, spec
        )

        if A.shape[0] == 0 or A.shape[1] == 0:
            return FreeAdjustmentResult(
                residuals=np.array([]),
                normalized_residuals=np.array([]),
                gross_errors=[],
                sigma_0=0.0,
                status="empty_matrices"
            )

        # 3. Применение ограничений
        A_free, L_corr, P_free, _, free_indices = apply_constraints(
            A, L, P, fixed_points, point_indices
        )

        # 4. Решение нормальной системы
        from .solver import compute_sigma_0, solve_normal_equations

        dx_free, _ = solve_normal_equations(A_free, L_corr, P_free)

        # 5. Вычисление невязок v = A·dx - L
        # Восстанавливаем полный вектор dx
        dx_full = np.zeros(len(point_indices))
        for i, idx in enumerate(free_indices):
            dx_full[idx] = dx_free[i]

        residuals = A @ dx_full - L

        # 6. Вычисление σ₀
        redundancy = A.shape[0] - len(free_indices)
        sigma_0 = compute_sigma_0(residuals, P_free, redundancy)

        if sigma_0 < 1e-10:
            logger.warning("Очень малый σ₀, возможна переопределённость")
            sigma_0 = 1e-10

        # 7. Нормализованные невязки w_i = v_i * √P_ii / σ₀
        P_diag = P_free.diagonal() if hasattr(P_free, 'diagonal') else P_diag
        sqrt_P = np.sqrt(np.abs(P_diag))
        normalized_residuals = (residuals * sqrt_P) / sigma_0

        # 8. Обнаружение грубых ошибок
        gross_error_indices = np.where(np.abs(normalized_residuals) > threshold)[0].tolist()

        if gross_error_indices:
            logger.warning(
                f"⚠️ Обнаружено {len(gross_error_indices)} потенциально грубых измерений "
                f"(порог {threshold}): {gross_error_indices[:5]}..."
            )

        return FreeAdjustmentResult(
            residuals=residuals,
            normalized_residuals=normalized_residuals,
            gross_errors=gross_error_indices,
            sigma_0=sigma_0,
            status="success"
        )

    except Exception as e:
        logger.error(f"Ошибка свободного уравнивания: {e}")
        return FreeAdjustmentResult(
            residuals=np.array([]),
            normalized_residuals=np.array([]),
            gross_errors=[],
            sigma_0=0.0,
            status=f"error: {str(e)}"
        )

def _build_initial_indices(
    observations: List[Observation]
) -> Tuple[Dict[str, int], Dict[str, float]]:
    """Построение начальных индексов и приближённых координат"""
    all_points = set()
    for obs in observations:
        all_points.add(obs.station_id)
        all_points.add(obs.target_id)

    point_indices = {pid: i for i, pid in enumerate(sorted(all_points))}
    approx_coords = {pid: 0.0 for pid in point_indices}

    return point_indices, approx_coords

def filter_gross_errors(
    observations: List[Observation],
    gross_indices: List[int]
) -> List[Observation]:
    """Удаление наблюдений с грубыми ошибками из списка"""
    if not gross_indices:
        return observations

    gross_set = set(gross_indices)
    filtered = [obs for i, obs in enumerate(observations) if i not in gross_set]

    logger.info(f"Удалено {len(gross_indices)} наблюдений с грубыми ошибками")
    return filtered
