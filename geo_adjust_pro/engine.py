"""
GeoAdjustPro Engine - Python implementation inspired by DynAdjust architecture.
Performs rigorous Least Squares Adjustment for Geodetic Networks.
Supports Plan (2D) and Height (Leveling) adjustments with status control.
"""

import math
import numpy as np
from scipy import sparse
from scipy.sparse import linalg as splinalg
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

@dataclass
class AdjustmentResult:
    """Результат уравнивания"""
    success: bool
    iterations: int
    sigma0: float  # СКП единицы веса
    sigma0_km: Optional[float] = None  # СКП на 1 км (для нивелирования)
    points_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    residuals: List[float] = field(default_factory=list)
    message: str = ""

class GeoAdjustEngine:
    """
    Ядро уравнивания, реализующее принципы DynAdjust:
    1. Параметрический метод МНК.
    2. Итерационный процесс для нелинейных задач (план).
    3. Разреженные матрицы для больших сетей.
    """
    
    def __init__(self):
        self.points = {}  # {point_id: PointData}
        self.observations = []  # List of Observation objects
        
    def load_network(self, points: Dict, observations: List):
        """Загрузка сети из данных парсера"""
        self.points = points
        self.observations = observations
        logger.info(f"Загружено точек: {len(points)}, наблюдений: {len(observations)}")

    def _get_unknown_indices_height(self) -> Tuple[Dict[str, int], int]:
        """Индексы неизвестных для высот (1 параметр на точку)"""
        unknowns = {}
        idx = 0
        for pid, pdata in self.points.items():
            if pdata.height_status not in ['initial', 'fixed']:
                unknowns[pid] = idx
                idx += 1
        return unknowns, idx

    def _get_unknown_indices_plan(self) -> Tuple[Dict[str, Tuple[int, int]], int]:
        """Индексы неизвестных для плана (2 параметра на точку: X, Y)"""
        unknowns = {}
        idx = 0
        for pid, pdata in self.points.items():
            if pdata.plan_status not in ['initial', 'fixed']:
                unknowns[pid] = (idx, idx + 1)
                idx += 2
        return unknowns, idx

    def adjust_heights(self, free_adjustment: bool = False) -> AdjustmentResult:
        """
        Уравнивание нивелирной сети (линейная задача).
        Модель: h_ij = H_j - H_i + v

        Параметры:
        - free_adjustment: использовать свободное уравнивание (без фиксированных высот)
        """
        logger.info(f"Запуск уравнивания высот (свободное={free_adjustment})...")

        # 1. Формирование списка неизвестных
        unknowns, n_unknowns = self._get_unknown_indices_height()

        if n_unknowns == 0:
            return AdjustmentResult(success=False, iterations=0, sigma0=0.0,
                                    message="Нет определяемых пунктов по высоте")

        # 2. Сбор данных для разреженной матрицы
        rows = []
        cols = []
        data = []
        L = [] # Вектор свободных членов
        weights = []

        # Приблизительные высоты
        approx_heights = {}
        for pid, p in self.points.items():
            if p.height_status in ['initial', 'fixed'] and p.z is not None:
                approx_heights[pid] = p.z
            else:
                approx_heights[pid] = p.z if p.z is not None else 0.0

        obs_count = 0
        for obs in self.observations:
            obs_type = getattr(obs, 'type', getattr(obs, 'obs_type', 'unknown'))
            if obs_type not in ['leveling_height_diff', 'leveling']:
                continue

            from_pt = getattr(obs, 'from_point', getattr(obs, 'from_point_id', None))
            to_pt = getattr(obs, 'to_point', getattr(obs, 'to_point_id', None))

            if from_pt not in self.points or to_pt not in self.points:
                continue

            measured_dh = getattr(obs, 'value', getattr(obs, 'height_diff', 0))
            H_from_approx = approx_heights.get(from_pt, 0.0)
            H_to_approx = approx_heights.get(to_pt, 0.0)

            # Свободный член: l = Измеренное - (H_to_0 - H_from_0)
            l = measured_dh - (H_to_approx - H_from_approx)

            # Веса (обратно пропорциональны длине хода)
            dist = getattr(obs, 'distance', getattr(obs, 'slope_distance', 1.0))
            if dist <= 0:
                dist = 1.0
            w = 1.0 / dist

            # Коэффициенты: -1 для From, +1 для To
            row_data = []
            col_data = []

            if from_pt in unknowns:
                row_data.append(-1.0)
                col_data.append(unknowns[from_pt])
            else:
                l -= (-1.0 * approx_heights.get(from_pt, 0.0))

            if to_pt in unknowns:
                row_data.append(1.0)
                col_data.append(unknowns[to_pt])
            else:
                l -= (1.0 * approx_heights.get(to_pt, 0.0))

            if row_data:
                rows.extend([obs_count] * len(row_data))
                cols.extend(col_data)
                data.extend(row_data)
                L.append(l)
                weights.append(w)
                obs_count += 1

        if obs_count == 0:
            return AdjustmentResult(success=False, iterations=0, sigma0=0.0, message="Нет нивелирных ходов")

        # 3. Построение разреженных матриц
        A = sparse.csr_matrix((data, (rows, cols)), shape=(obs_count, n_unknowns))
        L_vec = np.array(L)
        P_mat = sparse.diags(weights)

        # 4. Решение нормальных уравнений
        N = (A.T @ P_mat @ A).tocsc()
        R = A.T @ (P_mat @ L_vec)

        if free_adjustment:
            # Свободное уравнивание - используем псевдообратную матрицу
            dx = self._solve_free_adjustment(N, R, n_unknowns)
        else:
            # Обычное уравнивание
            try:
                dx = splinalg.spsolve(N, R)
            except Exception as e:
                return AdjustmentResult(success=False, iterations=0, sigma0=0.0, message=f"Ошибка решения СЛАУ: {str(e)}")

        # 5. Вычисление поправок и статистик
        v = A @ dx - L_vec
        vTv = float(v.T @ P_mat @ v)

        # Для свободного уравнивания степень свободы уменьшается на 1
        dof = obs_count - n_unknowns + (1 if free_adjustment else 0)
        sigma0 = np.sqrt(vTv / dof) if dof > 0 else 0.0

        # СКП на 1 км
        total_dist = sum(obs.distance for obs in self.observations
                        if obs.type == 'leveling_height_diff' and hasattr(obs, 'distance'))
        sigma0_km = sigma0 * np.sqrt(total_dist / obs_count) if obs_count > 0 and total_dist > 0 else sigma0

        # 6. Обновление координат и сбор статистики
        points_stats = {}

        # Оценка дисперсий (диагональ обратной матрицы)
        try:
            if n_unknowns < 5000:
                N_inv = sparse.linalg.inv(N)
                N_inv_diag = N_inv.diagonal()
            else:
                N_inv_diag = 1.0 / np.maximum(N.diagonal(), 1e-10)
        except:
            N_inv_diag = np.ones(n_unknowns)

        for pid, idx in unknowns.items():
            var = N_inv_diag[idx] * (sigma0 ** 2)
            std = np.sqrt(abs(var))

            if pid in self.points:
                old_h = approx_heights[pid]
                new_h = old_h + dx[idx]
                self.points[pid].z = new_h
                self.points[pid].height_status = 'adjusted'

                points_stats[pid] = {
                    'height': new_h,
                    'height_std': std,
                    'correction': dx[idx]
                }

        adjustment_type = "свободное" if free_adjustment else "строгое"
        logger.info(f"{adjustment_type.capitalize()} уравнивание высот завершено. СКП: {sigma0*1000:.2f} мм, на 1км: {sigma0_km*1000:.2f} мм/км")

        return AdjustmentResult(
            success=True,
            iterations=1,
            sigma0=sigma0,
            sigma0_km=sigma0_km,
            points_stats=points_stats,
            residuals=v.tolist(),
            message=f"{adjustment_type.capitalize()} уравнивание выполнено успешно"
        )

    def _solve_free_adjustment(self, N: sparse.csr_matrix, R: np.ndarray, n_unknowns: int) -> np.ndarray:
        """
        Решение системы для свободного уравнивания.
        Для 2D случая система имеет ранг на 3 меньше (масштаб, поворот, сдвиг).
        Используем минимально-нормированное решение.
        """
        try:
            # Преобразование в плотную матрицу
            N_dense = N.toarray()
            R_dense = R.toarray().flatten() if sparse.issparse(R) else R.flatten()

            # Проверяем ранг матрицы
            rank = np.linalg.matrix_rank(N_dense, tol=1e-10)
            logger.info(f"Матрица N: размер {N_dense.shape}, ранг {rank}")

            # Для свободного уравнивания всегда используем псевдообратную матрицу для решения недоопределенных систем
            N_pinv = np.linalg.pinv(N_dense, rcond=1e-10)
            dx = N_pinv @ R_dense
            logger.info(f"Свободное уравнивание: ранг={rank}/{n_unknowns}, использую псевдообратную")

            return dx

        except Exception as e:
            logger.error(f"Ошибка в свободном уравнивании: {e}")
            # Возврат тривиального решения
            return np.zeros(n_unknowns)

    def adjust_plan(self, points: Dict, observations: List, free_adjustment: bool = False) -> AdjustmentResult:
        """
        Уравнивание плановой сети (нелинейная задача, итерационный процесс).
        Принимает точки и наблюдения как аргументы.
        """
        # Загружаем данные во внутреннюю структуру
        self.points = points
        self.observations = observations
        
        adjustment_type = "свободное" if free_adjustment else "строгое"
        logger.info(f"Запуск {adjustment_type} уравнивания плана...")
        
        max_iter = 10
        tol = 1e-4
        
        # Подготовка приближенных координат
        approx_coords = {}
        for pid, p in self.points.items():
            if p.plan_status in ['initial', 'fixed'] and p.x is not None and p.y is not None:
                approx_coords[pid] = np.array([p.x, p.y])
            else:
                approx_coords[pid] = np.array([p.x or 0.0, p.y or 0.0])

        # Получение индексов неизвестных (постоянно)
        unknowns_map, n_unknowns = self._get_unknown_indices_plan()
        if n_unknowns == 0:
            return AdjustmentResult(success=False, iterations=0, sigma0=0.0, message="Нет определяемых пунктов по плану")

        # Для свободного уравнивания фиксируем первую точку для определения дат
        fixed_pid = None
        if free_adjustment and unknowns_map:
            fixed_pid = list(unknowns_map.keys())[0]
            logger.info(f"Свободное уравнивание: фиксация точки {fixed_pid} в (0,0) для определения дат")

        # Initialize dx to avoid UnboundLocalError
        dx = np.zeros(n_unknowns)

        final_iteration = 0
        for iteration in range(max_iter):
            rows, cols, data = [], [], []
            L_vec = []
            weights = []
            obs_count = 0

            for obs in self.observations:
                # Поддержка CombinedObservation из SDR парсера
                obs_type = getattr(obs, 'type', getattr(obs, 'obs_type', 'unknown'))

                # Конвертация углов из градусов в радианы
                if obs_type in ['direction', 'horizontal_angle'] and hasattr(obs, 'value'):
                    obs.value = math.radians(obs.value)
                elif obs_type in ['zenith_angle'] and hasattr(obs, 'value'):
                    obs.value = math.radians(obs.value)

                if obs_type in ['slope_distance', 'combined'] and hasattr(obs, 'slope_distance'):
                    i_pt = getattr(obs, 'from_point', getattr(obs, 'from_point_id', None))
                    j_pt = getattr(obs, 'to_point', getattr(obs, 'to_point_id', None))

                    if i_pt not in approx_coords or j_pt not in approx_coords:
                        continue

                    Xi, Yi = approx_coords[i_pt]
                    Xj, Yj = approx_coords[j_pt]

                    dX = Xj - Xi
                    dY = Yj - Yi
                    S0 = np.sqrt(dX**2 + dY**2)

                    # Расстояние
                    if hasattr(obs, 'slope_distance') and obs.slope_distance is not None:
                        s = obs.slope_distance
                        l = s - S0
                        w = 1.0 / (0.005**2)  # Вес для расстояния

                        row_entries = []
                        col_entries = []

                        if i_pt in unknowns_map:
                            idx_x, idx_y = unknowns_map[i_pt]
                            a_Xi = -dX / S0
                            a_Yi = -dY / S0
                            row_entries.extend([a_Xi, a_Yi])
                            col_entries.extend([idx_x, idx_y])
                        else:
                            l += (a_Xi * approx_coords[i_pt][0] + a_Yi * approx_coords[i_pt][1])

                        if j_pt in unknowns_map:
                            idx_x, idx_y = unknowns_map[j_pt]
                            a_Xj = dX / S0
                            a_Yj = dY / S0
                            row_entries.extend([a_Xj, a_Yj])
                            col_entries.extend([idx_x, idx_y])
                        else:
                            l -= (a_Xj * approx_coords[j_pt][0] + a_Yj * approx_coords[j_pt][1])

                        if row_entries:
                            rows.extend([obs_count] * len(row_entries))
                            cols.extend(col_entries)
                            data.extend(row_entries)
                            L_vec.append(l)
                            weights.append(w)
                            obs_count += 1

            # Добавляем фиксацию для свободного уравнивания
            if free_adjustment and fixed_pid and fixed_pid in unknowns_map:
                idx_x, idx_y = unknowns_map[fixed_pid]
                # Фиксируем X = 0
                rows.append(obs_count)
                cols.append(idx_x)
                data.append(1.0)
                L_vec.append(approx_coords[fixed_pid][0])
                weights.append(1e-6)
                obs_count += 1
                # Фиксируем Y = 0
                rows.append(obs_count)
                cols.append(idx_y)
                data.append(1.0)
                L_vec.append(approx_coords[fixed_pid][1])
                weights.append(1e-6)
                obs_count += 1

            if not rows:
                    i_pt = getattr(obs, 'from_point', getattr(obs, 'from_point_id', None))
                    j_pt = getattr(obs, 'to_point', getattr(obs, 'to_point_id', None))
                    
                    if i_pt not in approx_coords or j_pt not in approx_coords:
                        continue
                    
                    Xi, Yi = approx_coords[i_pt]
                    Xj, Yj = approx_coords[j_pt]
                    
                    dX = Xj - Xi
                    dY = Yj - Yi
                    S0 = np.sqrt(dX**2 + dY**2)
                    
                    if S0 < 1e-6:
                        continue
                    
                    az0 = np.arctan2(dX, dY) * 180 / np.pi
                    if az0 < 0:
                        az0 += 360
                    
                    measured_dir = getattr(obs, 'horizontal_angle', getattr(obs, 'value', 0))
                    
                    rho = 206264.806
                    a_Xi = dY / (S0**2) * rho
                    a_Yi = -dX / (S0**2) * rho
                    a_Xj = -dY / (S0**2) * rho
                    a_Yj = dX / (S0**2) * rho
                    
                    l = measured_dir - az0
                    
                    sigma_dir = 5.0 / rho
                    w = 1.0 / (sigma_dir ** 2)
                    
                    row_entries = []
                    col_entries = []
                    
                    if i_pt in unknowns_map:
                        idx_x, idx_y = unknowns_map[i_pt]
                        row_entries.extend([a_Xi, a_Yi])
                        col_entries.extend([idx_x, idx_y])
                    else:
                        l -= (a_Xi * approx_coords[i_pt][0] + a_Yi * approx_coords[i_pt][1])
                    
                    if j_pt in unknowns_map:
                        idx_x, idx_y = unknowns_map[j_pt]
                        row_entries.extend([a_Xj, a_Yj])
                        col_entries.extend([idx_x, idx_y])
                    else:
                        l -= (a_Xj * approx_coords[j_pt][0] + a_Yj * approx_coords[j_pt][1])
                    
                    if row_entries:
                        rows.extend([obs_count] * len(row_entries))
                        cols.extend(col_entries)
                        data.extend(row_entries)
                        L_vec.append(l)
                        weights.append(w)
                        obs_count += 1
            
            if not rows:
                break
                
            A = sparse.csr_matrix((data, (rows, cols)), shape=(obs_count, n_unknowns))
            L_arr = np.array(L_vec)
            P = sparse.diags(weights)
            
            N = (A.T @ P @ A).tocsc()
            R = A.T @ (P @ L_arr)

            dx = np.zeros(n_unknowns)  # Инициализация по умолчанию

            if free_adjustment:
                # Свободное уравнивание
                try:
                    dx = self._solve_free_adjustment(N, R, n_unknowns)
                except Exception as e:
                    logger.warning(f"Свободное уравнивание не удалось: {e}, используем тривиальное решение")
                    dx = np.zeros(n_unknowns)
            else:
                # Строгое уравнивание
                try:
                    dx = splinalg.spsolve(N, R)
                except:
                    logger.warning("Строгое уравнивание не удалось, используем тривиальное решение")
                    dx = np.zeros(n_unknowns)
            
            max_dx = 0
            for pid, (idx_x, idx_y) in unknowns_map.items():
                approx_coords[pid][0] += dx[idx_x]
                approx_coords[pid][1] += dx[idx_y]
                max_dx = max(max_dx, abs(dx[idx_x]), abs(dx[idx_y]))
            
            final_iteration = iteration + 1
            
            if max_dx < tol:
                logger.info(f"Сходимость на итерации {final_iteration}")
                break
        
        v = A @ dx - L_arr if obs_count > 0 else np.array([])
        vTv = float(v.T @ P @ v) if len(v) > 0 else 0.0

        # Для свободного уравнивания степень свободы уменьшается на 3 (масштаб, поворот, сдвиг)
        dof = obs_count - n_unknowns + (3 if free_adjustment else 0)
        sigma0 = np.sqrt(vTv / dof) if dof > 0 else 0.0

        logger.info(f"vTv = {vTv:.6f}, dof = {dof}, sigma0 = {sigma0:.6f}")

        # Проверка достоверности: если sigma0 = 0, данные могут быть некорректными
        if sigma0 == 0.0 and obs_count > 0:
            logger.warning("СКП = 0.000 мм. Возможные причины: нулевые измерения, недостаток данных или систематические ошибки. Проверьте входные данные.")
        
        try:
            if n_unknowns < 5000:
                N_inv = sparse.linalg.inv(N)
                N_inv_diag = N_inv.diagonal()
            else:
                N_inv_diag = 1.0 / np.maximum(N.diagonal(), 1e-10)
        except:
            N_inv_diag = np.ones(n_unknowns)
        
        points_stats = {}
        for pid, (idx_x, idx_y) in unknowns_map.items():
            var_x = N_inv_diag[idx_x] * (sigma0 ** 2)
            var_y = N_inv_diag[idx_y] * (sigma0 ** 2)
            std_x = np.sqrt(abs(var_x))
            std_y = np.sqrt(abs(var_y))

            if pid in self.points:
                # ОБНОВЛЯЕМ КООРДИНАТЫ РЕЗУЛЬТАТАМИ УРАВНИВАНИЯ!
                final_x = approx_coords[pid][0] + dx[idx_x]
                final_y = approx_coords[pid][1] + dx[idx_y]

                self.points[pid].x = final_x
                self.points[pid].y = final_y
                self.points[pid].plan_status = 'adjusted'
                # Сохраняем параметры точности в атрибуты точки для отчетов
                self.points[pid].x_std = std_x
                self.points[pid].y_std = std_y
                self.points[pid].xy_cov = 0.0  # Упрощенно, можно рассчитать через N_inv

                points_stats[pid] = {
                    'x': final_x,  # Используем окончательные координаты!
                    'y': final_y,  # Используем окончательные координаты!
                    'std_x': std_x,
                    'std_y': std_y,
                    'cov_xy': 0.0
                }
        
        logger.info(f"{adjustment_type.capitalize()} уравнивание плана завершено. СКП: {sigma0*1000:.2f} мм, итераций: {final_iteration}")

        return AdjustmentResult(
            success=True,
            iterations=final_iteration,
            sigma0=sigma0,
            points_stats=points_stats,
            message=f"{adjustment_type.capitalize()} плановое уравнивание завершено",
            residuals=v.tolist() if len(v) > 0 else []
        )


if __name__ == "__main__":
    print("GeoAdjustPro Engine loaded.")
    print("Ready for integration with GSI/SDR parsers.")
