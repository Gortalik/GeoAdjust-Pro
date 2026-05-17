"""Основной движок уравнивания высотных сетей методом наименьших квадратов"""
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
    corrections: np.ndarray                    # Поправки к высотам пунктов
    residuals: np.ndarray                      # Невязки наблюдений
    sigma_0: float                             # СКП единицы веса
    covariance_matrix: Optional[sp.csr_matrix] # Ковариационная матрица
    iterations: int                            # Число итераций
    status: str                                # Статус сходимости
    diagnostics: Dict                          # Дополнительная диагностика
    point_indices: Dict[str, int]              # Маппинг пунктов в индексы
    adjusted_heights: Dict[str, float]         # Уравненные высоты

class AdjustmentEngine:
    """
    Основной движок уравнивания высотных сетей.
    
    Поддерживает:
    - Итерационное уравнивание с линеаризацией
    - Свободное уравнивание для диагностики грубых ошибок
    - Разреженные матрицы (scipy.sparse) с ускорением CHOLMOD
    - Расчёт весов по СП 11-104-97
    - Вычисление ковариационной матрицы и точности пунктов
    """

    def __init__(self, spec: InstrumentSpec = None):
        """
        Инициализация движка.
        
        Args:
            spec: Характеристики прибора (по умолчанию техническое нивелирование)
        """
        self.spec = spec or InstrumentSpec(class_code="4")
        self.point_indices: Dict[str, int] = {}
        self.approx_coords: Dict[str, float] = {}
        self._last_result: Optional[AdjustmentResult] = None

    def adjust_heights(
        self,
        observations: List[Observation],
        fixed_points: Dict[str, float],
        max_iter: int = 10,
        tol: float = 1e-5,
        detect_gross_errors: bool = True,
        compute_covariance: bool = True
    ) -> AdjustmentResult:
        """
        Уравнивание высотной сети.
        
        Args:
            observations: Список наблюдений
            fixed_points: {punkt_id: фиксированная_высота}
            max_iter: Максимальное число итераций
            tol: Порог сходимости (макс. поправка)
            detect_gross_errors: Выполнять ли диагностику грубых ошибок
            compute_covariance: Вычислять ли ковариационную матрицу
            
        Returns:
            AdjustmentResult: Результаты уравнивания
        """
        logger.info("🔹 Запуск уравнивания высотной сети...")
        logger.info(f"  Наблюдений: {len(observations)}, Фиксированных пунктов: {len(fixed_points)}")

        if not observations:
            raise ValueError("Список наблюдений пуст")

        # 1. Предварительное свободное уравнивание для поиска грубых ошибок
        gross_errors_indices = []
        if detect_gross_errors:
            free_result = run_free_adjustment(observations, self.spec)
            gross_errors_indices = free_result.gross_errors

            if gross_errors_indices:
                logger.warning(
                    f"⚠️ Обнаружено {len(gross_errors_indices)} потенциально грубых измерений. "
                    f"Рекомендуется проверка перед основным уравниванием."
                )
                # Фильтрация грубых ошибок
                observations = filter_gross_errors(observations, gross_errors_indices)
                logger.info(f"  После фильтрации: {len(observations)} наблюдений")

        # 2. Построение индексации пунктов
        self._build_index_map(observations, fixed_points)

        # Инициализация приближённых высот
        self.approx_coords = {pid: 0.0 for pid in self.point_indices}
        self.approx_coords.update(fixed_points)

        # 3. Итерационный процесс
        dx_total = np.zeros(len(self.point_indices))
        residuals = np.zeros(len(observations))
        sigma_0 = 0.0
        cov_matrix = None

        converged = False
        for iteration in range(max_iter):
            logger.debug(f"  Итерация {iteration + 1}/{max_iter}")

            # Построение уравнений на текущей итерации
            A, L, P = build_linearized_equations(
                observations, self.point_indices, self.approx_coords, self.spec
            )

            # Применение ограничений (фиксированные пункты)
            A_free, L_corr, P_free, H_fixed, free_indices = apply_constraints(
                A, L, P, fixed_points, self.point_indices
            )

            if A_free.shape[1] == 0:
                logger.warning("Нет свободных параметров для уравнивания")
                break

            # Решение нормальной системы
            dx_free, _ = solve_normal_equations(A_free, L_corr, P_free, compute_covariance=False)

            # Обновление приближённых высот
            for i, idx in enumerate(free_indices):
                dx_total[idx] += dx_free[i]
                # Обновляем только свободные пункты
                for pid, pidx in self.point_indices.items():
                    if pidx == idx and pid not in fixed_points:
                        self.approx_coords[pid] += dx_free[i]

            # Вычисление невязок
            dx_full = np.zeros(len(self.point_indices))
            for i, idx in enumerate(free_indices):
                dx_full[idx] = dx_free[i]
            residuals = A @ dx_full - L

            # Вычисление σ₀
            redundancy = A.shape[0] - len(free_indices)
            sigma_0 = compute_sigma_0(residuals, P_free, redundancy)

            max_correction = np.max(np.abs(dx_free)) if len(dx_free) > 0 else 0.0
            logger.info(
                f"  Итерация {iteration + 1}: ‖Δx‖∞ = {max_correction:.2e}, "
                f"σ₀ = {sigma_0:.4f} м"
            )

            # Проверка сходимости
            if max_correction < tol:
                converged = True
                logger.info("✅ Сходимость достигнута")
                break

        # 4. Ковариационная матрица (опционально)
        if compute_covariance and converged:
            try:
                A_final, L_final, P_final = build_linearized_equations(
                    observations, self.point_indices, self.approx_coords, self.spec
                )
                A_free_final, _, P_free_final, _, free_indices = apply_constraints(
                    A_final, L_final, P_final, fixed_points, self.point_indices
                )

                N = (A_free_final.T @ P_free_final @ A_free_final).tocsc()
                from .solver import _compute_covariance_matrix
                Q_free = _compute_covariance_matrix(N)

                # Масштабирование на σ₀²
                cov_matrix = (sigma_0 ** 2) * Q_free
            except Exception as e:
                logger.warning(f"Не удалось вычислить ковариационную матрицу: {e}")

        # 5. Формирование результата
        adjusted_heights = {
            pid: self.approx_coords.get(pid, 0.0)
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
            adjusted_heights=adjusted_heights
        )

        self._last_result = result
        logger.info(f"📊 Уравнивание завершено: σ₀ = {sigma_0:.4f} м, итераций = {iteration + 1}")

        return result

    def _build_index_map(
        self,
        observations: List[Observation],
        fixed_points: Dict[str, float]
    ) -> None:
        """Построение маппинга пунктов в индексы матрицы"""
        all_points = set()
        for obs in observations:
            all_points.add(obs.station_id)
            all_points.add(obs.target_id)

        # Сортировка для детерминированного порядка
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
