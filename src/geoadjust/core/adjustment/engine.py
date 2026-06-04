"""Основной движок уравнивания 3D-сетей методом наименьших квадратов"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import scipy.sparse as sp
from loguru import logger

from geoadjust.io.base import Observation
from .equations import apply_constraints, build_linearized_equations
from .free_adjustment import filter_gross_errors, run_free_adjustment
from .solver import compute_sigma_0, solve_normal_equations
from .weights import InstrumentSpec


@dataclass
class AdjustmentResult:
    """Результат уравнивания"""
    corrections: np.ndarray
    residuals: np.ndarray
    sigma_0: float
    covariance_matrix: Optional[sp.csr_matrix]
    iterations: int
    status: str
    diagnostics: Dict
    point_indices: Dict[str, int]
    adjusted_coords: Dict[str, np.ndarray]


class AdjustmentEngine:
    """
    Движок уравнивания 3D-геодезических сетей.
    
    Поддерживает:
    - Итерационное уравнивание со линеаризацией
    - Свободное уравнивание для диагностики грубых ошибок
    - Разреженные матрицы с CHOLMOD
    - Расчёт весов по СП 11-104-97
    - Вычисление ковариационной матрицы
    - Робастное уравнивание с пересчётом весов
    """

    def __init__(self, spec: InstrumentSpec = None):
        self.spec = spec or InstrumentSpec(class_code="4")
        self.point_indices: Dict[str, int] = {}
        self.approx_coords: Dict[str, np.ndarray] = {}
        self._last_result: Optional[AdjustmentResult] = None

    def adjust_heights(
        self,
        observations: List[Observation],
        fixed_points: Dict[str, np.ndarray],
        max_iter: int = 10,
        tol: float = 1e-5,
        detect_gross_errors: bool = True,
        compute_covariance: bool = True
    ) -> AdjustmentResult:
        """
        Уравнивание 3D-сети.
        
        Args:
            observations: Список наблюдений (с полными координатами)
            fixed_points: {punkt_id: [x, y, z] или [h]}
            max_iter: Максимальное число итераций
            tol: Порог сходимости
            detect_gross_errors: Диагностика грубых ошибок
            compute_covariance: Вычисление ковариационной матрицы
            
        Returns:
            AdjustmentResult: Результаты уравнивания
        """
        logger.info("🔹 Запуск уравнивания 3D-сети...")
        logger.info(f"  Наблюдений: {len(observations)}, Фиксированных пунктов: {len(fixed_points)}")

        if not observations:
            raise ValueError("Список наблюдений пуст")

        # 1. Свободное уравнивание для поиска грубых ошибок
        gross_errors_indices = []
        if detect_gross_errors:
            free_result = run_free_adjustment(observations, self.spec)
            gross_errors_indices = free_result.gross_errors

            if gross_errors_indices:
                logger.warning(f"⚠️ Обнаружено {len(gross_errors_indices)} потенциально грубых измерений.")
                observations = filter_gross_errors(observations, gross_errors_indices)
                logger.info(f"  После фильтрации: {len(observations)} наблюдений")

        # 2. Построение индексации пунктов
        self._build_index_map(observations, fixed_points)

        # 3. Инициализация приближённых координат (3D)
        self.approx_coords = {pid: np.array([0.0, 0.0, 0.0]) for pid in self.point_indices}
        for pid, coords in fixed_points.items():
            if pid in self.approx_coords:
                if len(coords) == 1:  # Только высота
                    self.approx_coords[pid] = np.array([0.0, 0.0, coords[0]])
                else:
                    self.approx_coords[pid] = np.array(coords)

        # Загружаем приближённые координаты из observations
        for obs in observations:
            if hasattr(obs, 'approx_x'):
                self.approx_coords[obs.station_id] = np.array([obs.approx_x, obs.approx_y, obs.approx_z])
                self.approx_coords[obs.target_id] = np.array([obs.target_x, obs.target_y, obs.target_z])

        # 4. Итерационное уравнивание
        dx_total = np.zeros(3 * len(self.point_indices))
        residuals = np.zeros(len(observations))
        sigma_0 = 0.0
        cov_matrix = None

        huber_threshold = 2.5
        min_weight = 0.01

        converged = False
        for iteration in range(max_iter):
            logger.debug(f"  Итерация {iteration + 1}/{max_iter}")

            A, L, P = build_linearized_equations(
                observations, self.point_indices, self.approx_coords, self.spec
            )

            A_free, L_corr, P_free, H_fixed, free_indices = apply_constraints(
                A, L, P, fixed_points, self.point_indices
            )

            if A_free.shape[1] == 0:
                logger.warning("Нет свободных параметров")
                break

            dx_free, _ = solve_normal_equations(A_free, L_corr, P_free, compute_covariance=False)

            # Обновление координат
            for i, idx in enumerate(free_indices):
                dx_total[3*idx:3*idx+3] += dx_free[3*idx:3*idx+3] if len(dx_free) > 3*idx+3 else [0, 0, 0]
                pid = [k for k, v in self.point_indices.items() if v == idx][0]
                if pid not in fixed_points:
                    self.approx_coords[pid] += dx_free[3*idx:3*idx+3] if len(dx_free) > 3*idx+3 else np.array([0, 0, 0])

            dx_full = np.zeros(3 * len(self.point_indices))
            dx_full[:len(dx_free)] = dx_free
            residuals = A @ dx_full - L

            redundancy = A.shape[0] - len(free_indices)
            sigma_0 = compute_sigma_0(residuals, P, redundancy)

            if detect_gross_errors and sigma_0 > 1e-10:
                P_diag = P.diagonal()
                normalized_residuals = np.abs(residuals) / sigma_0
                
                new_weights = np.zeros_like(P_diag)
                for j, norm_res in enumerate(normalized_residuals):
                    if norm_res <= huber_threshold:
                        new_weights[j] = P_diag[j]
                    else:
                        new_weights[j] = P_diag[j] * (huber_threshold / norm_res) ** 2
                    new_weights[j] = max(new_weights[j], min_weight * P_diag[j])
                
                P = sp.diags(new_weights, format="csr")

            max_correction = np.max(np.abs(dx_free)) if len(dx_free) > 0 else 0.0
            logger.info(f"  Итерация {iteration + 1}: ‖Δx‖∞ = {max_correction:.2e}, σ₀ = {sigma_0:.4f} м")

            if max_correction < tol:
                converged = True
                logger.info("✅ Сходимость достигнута")
                break

        # Формируем результат
        adjusted_coords = {
            pid: self.approx_coords.get(pid, np.array([0.0, 0.0, 0.0]))
            for pid in self.point_indices
        }

        result = AdjustmentResult(
            corrections=dx_total,
            residuals=residuals,
            sigma_0=sigma_0,
            covariance_matrix=cov_matrix,
            iterations=iteration + 1,
            status="converged" if converged else "max_iterations_reached",
            diagnostics={
                "redundancy": redundancy,
                "gross_errors_detected": len(gross_errors_indices),
                "num_observations": len(observations),
                "num_points": len(self.point_indices),
            },
            point_indices=self.point_indices.copy(),
            adjusted_coords=adjusted_coords
        )

        self._last_result = result
        logger.info(f"📊 Уравнивание завершено: σ₀ = {sigma_0:.4f} м")
        return result

    def _build_index_map(
        self,
        observations: List[Observation],
        fixed_points: Dict[str, np.ndarray]
    ) -> None:
        """Построение маппинга пунктов в индексы матрицы (3D)"""
        all_points = set()
        for obs in observations:
            all_points.add(obs.station_id)
            all_points.add(obs.target_id)

        self.point_indices = {pid: i for i, pid in enumerate(sorted(all_points))}
        logger.debug(f"Построена индексация: {len(self.point_indices)} пунктов")

    def get_point_precision(self, point_id: str) -> Optional[float]:
        """
        Получение СКП высоты пункта из ковариационной матрицы.
        
        Args:
            point_id: Имя пункта
            
        Returns:
            float: СКП высоты в метрах (или None если матрица не вычислена)
        """
        if self._last_result is None or self._last_result.covariance_matrix is None:
            return None

        idx = self.point_indices.get(point_id)
        if idx is None:
            return None

        try:
            cov = self._last_result.covariance_matrix
            if idx < cov.shape[0]:
                variance = cov[idx, idx]
                return np.sqrt(abs(variance))
        except Exception:
            pass

        return None
