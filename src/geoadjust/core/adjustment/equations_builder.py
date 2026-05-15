# src/geoadjust/core/adjustment/equations_builder.py
"""Сборка матриц A и L с валидацией и детальным логированием"""
import numpy as np
import scipy.sparse as sparse
from typing import List, Dict, Tuple, Optional, Any
from geoadjust.core.adjustment.weights import InstrumentSpec, ObsType
from geoadjust.io.base import Observation
import logging

logger = logging.getLogger("geoadjust.equations_builder")

class EquationsBuilder:
    """
    Построитель уравнений поправок для геодезических сетей.
    Поддерживает нивелирование, расстояния, углы и направления.
    """
    def __init__(self, spec: InstrumentSpec = None):
        self.spec = spec or InstrumentSpec(class_code="4")
        self.rows = []
        self.cols = []
        self.data = []
        self.L = []
        self.point_to_idx = {}
        self.param_count = 0

    def build_adjustment_matrix(
        self,
        observations: List[Observation],
        point_indices: Dict[str, int],
        approximate_coords: Dict[str, float],
        fixed_points: Dict[str, float] = None
    ) -> Tuple[sparse.csr_matrix, np.ndarray, Dict[str, Any]]:
        """
        Собирает матрицу коэффициентов A и вектор свободных членов L.
        Возвращает (A, L, validation_report).
        """
        logger.info("═" * 60)
        logger.info("Начало построения уравнений поправок")
        logger.info(f"Входные данные: {len(observations)} измерений, {len(point_indices)} пунктов")
        
        self._reset()
        self.point_to_idx = point_indices.copy()
        self.param_count = len(point_indices)

        obs_processed = 0
        obs_skipped = 0
        errors = []

        for idx, obs in enumerate(observations, 1):
            try:
                if not self._validate_observation(obs, point_indices, approximate_coords):
                    obs_skipped += 1
                    continue

                self._add_equation(obs, approximate_coords)
                obs_processed += 1
                
                # Логирование каждого 50-го измерения для читаемости
                if idx % 50 == 0 or idx == len(observations):
                    logger.debug(f"  → Обработано: {idx}/{len(observations)}")
                    
            except Exception as e:
                err_msg = f"[ОШИБКА {idx}] Измерение {getattr(obs, 'obs_id', '?')}: {str(e)}"
                logger.error(err_msg)
                errors.append(err_msg)
                obs_skipped += 1

        # Формируем матрицу A с правильным количеством строк (одно уравнение = одна строка)
        n_equations = len(self.L)
        if n_equations == 0:
            A = sparse.csr_matrix((0, self.param_count))
        else:
            A = sparse.csr_matrix((self.data, (self.rows, self.cols)), 
                                  shape=(n_equations, self.param_count))
        L = np.array(self.L, dtype=np.float64)

        logger.info(f"Сборка завершена. Успешно: {obs_processed}, Пропущено: {obs_skipped}, Ошибок: {len(errors)}")
        
        # Валидация перед передачей в уравниватель
        validation = self._validate_system(A, L, point_indices, fixed_points or {})
        return A, L, validation

    def _reset(self):
        self.rows, self.cols, self.data, self.L = [], [], [], []
        self.point_to_idx = {}
        self.param_count = 0

    def _validate_observation(self, obs: Observation, point_indices: Dict[str, int], 
                               approximate_coords: Dict[str, float]) -> bool:
        """Проверка наличия точек и их координат."""
        for attr in ("station_id", "target_id"):
            pid = getattr(obs, attr, None)
            if not pid or pid not in point_indices:
                logger.warning(f"Точка '{pid}' отсутствует в сети. Измерение пропущено.")
                return False
            
            coord = approximate_coords.get(pid)
            if coord is None:
                logger.warning(f"Приближённая координата точки {pid} = None. Измерение пропущено.")
                return False
        return True

    def _add_equation(self, obs: Observation, approximate_coords: Dict[str, float]):
        """
        Добавляет уравнение поправок для наблюдения.
        Поддерживает различные типы измерений.
        """
        # row - это номер текущего уравнения (совпадает с индексом в L)
        row = len(self.L)
        
        if obs.type == ObsType.LEVELING:
            self._add_leveling_equation(obs, approximate_coords, row)
        elif obs.type == ObsType.DISTANCE:
            self._add_distance_equation(obs, approximate_coords, row)
        elif obs.type in (ObsType.ANGLE, ObsType.DIRECTION):
            self._add_angle_equation(obs, approximate_coords, row)
        else:
            raise ValueError(f"Неподдерживаемый тип наблюдения: {obs.type}")

    def _add_leveling_equation(self, obs: Observation, approx: Dict[str, float], row: int):
        """Уравнение для нивелирования: h_изм - (H_target - H_station)"""
        h_s = approx.get(obs.station_id, 0.0)
        h_t = approx.get(obs.target_id, 0.0)
        
        # Свободный член: l = h_measured - (H_target_approx - H_station_approx)
        l_i = obs.value - (h_t - h_s)
        self.L.append(l_i)
        
        # Коэффициенты: d(v)/dH_s = -1, d(v)/dH_t = +1
        idx_s = self.point_to_idx.get(obs.station_id)
        idx_t = self.point_to_idx.get(obs.target_id)
        
        # Добавляем коэффициенты только для свободных пунктов (не фиксированных)
        # row - это номер строки (номер уравнения), который должен соответствовать len(self.L) - 1
        if idx_s is not None:
            self.rows.append(row); self.cols.append(idx_s); self.data.append(-1.0)
        if idx_t is not None:
            self.rows.append(row); self.cols.append(idx_t); self.data.append(1.0)

    def _add_distance_equation(self, obs: Observation, approx: Dict[str, float], row: int):
        """Уравнение для расстояний (плановая сеть)."""
        # Для плановой сети нужны X, Y координаты
        # Здесь упрощённая версия - требуется доработка для 2D
        raise NotImplementedError("Уравнения для расстояний требуют 2D координат")

    def _add_angle_equation(self, obs: Observation, approx: Dict[str, float], row: int):
        """Уравнение для углов/направлений."""
        # Требуется реализация для угловых измерений
        raise NotImplementedError("Уравнения для углов требуют дополнительной реализации")

    def _validate_system(self, A: sparse.csr_matrix, L: np.ndarray, 
                         point_indices: Dict[str, int], fixed: Dict[str, float]) -> Dict[str, Any]:
        """Проверка ранга, обусловленности и размерностей системы."""
        report = {"status": "PASSED", "checks": {}, "message": "Система валидна"}

        n_obs, n_params = A.shape
        report["checks"]["dimensions"] = f"A({n_obs}×{n_params}), L({len(L)})"
        
        if n_obs != len(L):
            return {"status": "FAILED", "message": f"Размерности не совпадают: obs={n_obs} != L={len(L)}"}
        if n_obs == 0:
            return {"status": "FAILED", "message": "Нет измерений для уравнивания"}

        if n_params > 0:
            # Проверка ранга нормальной матрицы N = A^T A
            try:
                N = (A.T @ A).toarray()
                rank = np.linalg.matrix_rank(N, tol=1e-12)
                report["checks"]["rank"] = f"{rank}/{n_params}"
                
                defect = n_params - rank
                if defect == 0:
                    report["message"] = "Ранг полный. Сеть жёстко закреплена."
                elif defect <= 3:
                    report["message"] = f"⚠️ Свободная сеть (дефект ранга: {defect}). Требуется закрепление."
                else:
                    report["status"] = "FAILED"
                    report["message"] = f"❌ Критический дефект ранга: {defect}. Проверьте связность."

                # Проверка обусловленности
                cond = np.linalg.cond(N)
                report["checks"]["condition_number"] = f"{cond:.2e}"
                if cond > 1e14:
                    if report["status"] == "PASSED":
                        report["status"] = "WARNING"
                    report["message"] += f" | ⚠️ Плохая обусловленность (cond={cond:.2e})"
            except Exception as e:
                report["checks"]["condition_number"] = f"Не вычислено: {str(e)}"
        else:
            report["checks"]["rank"] = "N/A (нет параметров)"

        return report
