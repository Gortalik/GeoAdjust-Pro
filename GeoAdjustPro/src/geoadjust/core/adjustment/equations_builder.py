"""
Модуль построения матрицы коэффициентов уравнений поправок

Этот модуль формирует математическую модель уравнивания из исходных геодезических измерений.
Для каждого типа измерения вычисляются частные производные по формулам Ю.И. Маркузе.

Автор: GeoAdjust-Pro Team
Версия: 2.0
"""

import numpy as np
from scipy import sparse
from typing import List, Dict, Tuple, Optional
import logging

from ..network.models import NetworkPoint, Observation

logger = logging.getLogger(__name__)


class EquationsBuilder:
    """
    Построение матрицы коэффициентов уравнений поправок из исходных измерений.
    
    Реализует параметрический метод уравнивания по Ю.И. Маркузе.
    Для каждого типа измерения формируются уравнения поправок вида:
    
        v = A · Δx - ℓ
    
    где:
    - v - поправка в измерение
    - A - матрица частных производных
    - Δx - поправки к приближённым координатам
    - ℓ - свободный член (разность измеренного и вычисленного значения)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def build_adjustment_matrix(
        self,
        observations: List[Observation],
        points: Dict[str, NetworkPoint],
        fixed_points: List[str] = None
    ) -> Tuple[sparse.csr_matrix, np.ndarray]:
        """
        Построение полной матрицы коэффициентов уравнений поправок.
        
        Параметры:
        -----------
        observations : List[Observation]
            Список измерений (направления, расстояния, превышения, векторы ГНСС)
        points : Dict[str, NetworkPoint]
            Словарь пунктов сети {point_id: NetworkPoint}
        fixed_points : List[str], optional
            Список идентификаторов исходных (твёрдых) пунктов
        
        Возвращает:
        ------------
        A : sparse.csr_matrix
            Разреженная матрица коэффициентов (n × u), где:
            - n - число уравнений (измерений)
            - u - число неизвестных (параметров)
        L : np.ndarray
            Вектор свободных членов (размерность n)
        
        Пример:
        -------
        >>> builder = EquationsBuilder()
        >>> A, L = builder.build_adjustment_matrix(observations, points, fixed_points=['P1', 'P2'])
        >>> print(f"Матрица А: {A.shape[0]}×{A.shape[1]}")
        >>> print(f"Вектор L: {len(L)}")
        """
        if fixed_points is None:
            fixed_points = []
        
        # Проверка входных данных
        if not observations:
            raise ValueError("Список измерений пуст")
        if not points:
            raise ValueError("Словарь пунктов пуст")

        # Валидация типов данных
        assert isinstance(points, dict), "points должен быть Dict[str, NetworkPoint]"
        assert isinstance(observations, list), "observations должен быть List[Observation]"

        # Проверка что все элементы правильного типа
        for obs in observations:
            if not hasattr(obs, 'obs_type'):
                raise ValueError(f"Неверный тип измерения: {type(obs)}. Ожидается Observation.")
        for point_id, point in points.items():
            if not hasattr(point, 'point_id'):
                raise ValueError(f"Неверный тип точки {point_id}: {type(point)}. Ожидается NetworkPoint.")
        
        # Определение размерности сети (2D или 3D)
        has_heights = any(p.h is not None for p in points.values())
        num_unknowns_per_point = 3 if has_heights else 2
        
        # Подсчёт числа неизвестных
        num_free_points = len([p for p in points.values() if p.point_id not in fixed_points])
        num_unknowns = num_free_points * num_unknowns_per_point
        
        # Создание словаря для быстрого доступа к индексам неизвестных
        unknown_indices = {}
        idx = 0
        for point_id, point in sorted(points.items()):
            if point_id not in fixed_points:
                unknown_indices[point_id] = idx
                idx += num_unknowns_per_point
        
        # Списки для формирования разреженной матрицы
        row_indices = []
        col_indices = []
        data_values = []
        L_vector = []
        
        obs_index = 0
        skipped_count = 0

        self.logger.info(f"Processing {len(observations)} observations")
        for obs in observations:
            self.logger.debug(f"Processing observation {obs.obs_id}: type={obs.obs_type}, active={obs.is_active}, from={obs.from_point_id}, to={obs.to_point_id}")
            if not obs.is_active:
                self.logger.debug(f"Skipping inactive observation {obs.obs_id}")
                skipped_count += 1
                continue
            
            try:
                # Check if points exist
                if obs.from_point_id not in points:
                    self.logger.error(f"Point {obs.from_point_id} not found in points dict for observation {obs.obs_id}")
                    continue
                if obs.to_point_id not in points:
                    self.logger.error(f"Point {obs.to_point_id} not found in points dict for observation {obs.obs_id}")
                    continue

                if obs.obs_type == 'direction':
                    indices, coeffs, ell = self._build_direction_equation(
                        obs, points, unknown_indices, num_unknowns_per_point
                    )
                elif obs.obs_type in ['distance', 'slope_distance', 'horizontal_distance']:
                    indices, coeffs, ell = self._build_distance_equation(
                        obs, points, unknown_indices, num_unknowns_per_point
                    )
                elif obs.obs_type in ['height_diff', 'leveling_height_diff']:
                    indices, coeffs, ell = self._build_height_diff_equation(
                        obs, points, unknown_indices, num_unknowns_per_point
                    )
                elif obs.obs_type == 'gnss_vector':
                    # Вектор ГНСС даёт три уравнения
                    indices_list, coeffs_list, ell_list = self._build_gnss_vector_equations(
                        obs, points, unknown_indices, num_unknowns_per_point
                    )

                    # Обработка трёх уравнений
                    for sub_indices, sub_coeffs, sub_ell in zip(indices_list, coeffs_list, ell_list):
                        if sub_indices:  # Если есть ненулевые коэффициенты
                            for col_idx, coeff in zip(sub_indices, sub_coeffs):
                                row_indices.append(obs_index)
                                col_indices.append(col_idx)
                                data_values.append(coeff)
                            L_vector.append(sub_ell)
                            obs_index += 1
                elif obs.obs_type == 'combined':
                    # Для combined измерений создаем несколько уравнений
                    equations_created = False



                    # Направление (горизонтальный угол)
                    if hasattr(obs, 'horizontal_angle') and obs.horizontal_angle is not None:
                        temp_obs = type('TempObs', (), {
                            'obs_id': f"{obs.obs_id}_dir",
                            'from_point_id': obs.from_point_id,
                            'to_point_id': obs.to_point_id,
                            'value': obs.horizontal_angle,
                            'is_active': getattr(obs, 'is_active', True)
                        })()
                        indices, coeffs, ell = self._build_direction_equation(
                            temp_obs, points, unknown_indices, num_unknowns_per_point
                        )
                        if indices:  # Если уравнение создано
                            for col_idx, coeff in zip(indices, coeffs):
                                row_indices.append(obs_index)
                                col_indices.append(col_idx)
                                data_values.append(coeff)
                            L_vector.append(ell)
                            obs_index += 1
                            equations_created = True

                    # Расстояние
                    if hasattr(obs, 'slope_distance') and obs.slope_distance is not None:
                        temp_obs = type('TempObs', (), {
                            'obs_id': f"{obs.obs_id}_dist",
                            'from_point_id': obs.from_point_id,
                            'to_point_id': obs.to_point_id,
                            'value': obs.slope_distance,
                            'is_active': getattr(obs, 'is_active', True)
                        })()
                        indices, coeffs, ell = self._build_distance_equation(
                            temp_obs, points, unknown_indices, num_unknowns_per_point
                        )
                        if indices:  # Если уравнение создано
                            for col_idx, coeff in zip(indices, coeffs):
                                row_indices.append(obs_index)
                                col_indices.append(col_idx)
                                data_values.append(coeff)
                            L_vector.append(ell)
                            obs_index += 1
                            equations_created = True

                    # Зенитный угол
                    if hasattr(obs, 'zenith_angle') and obs.zenith_angle is not None and num_unknowns_per_point >= 3:
                        # Для зенитного угла нужна высота
                        temp_obs = type('TempObs', (), {
                            'obs_id': f"{obs.obs_id}_zen",
                            'from_point_id': obs.from_point_id,
                            'to_point_id': obs.to_point_id,
                            'value': obs.zenith_angle,
                            'is_active': getattr(obs, 'is_active', True)
                        })()
                        indices, coeffs, ell = self._build_zenith_angle_equation(
                            temp_obs, points, unknown_indices, num_unknowns_per_point
                        )
                        if indices:  # Если уравнение создано
                            for col_idx, coeff in zip(indices, coeffs):
                                row_indices.append(obs_index)
                                col_indices.append(col_idx)
                                data_values.append(coeff)
                            L_vector.append(ell)
                            obs_index += 1
                            equations_created = True

                    if not equations_created:
                        self.logger.warning(f"Combined измерение {obs.obs_id} не создало ни одного уравнения")
                        continue
                    continue
                elif obs.obs_type == 'azimuth':
                    # Азимут обрабатывается как направление
                    indices, coeffs, ell = self._build_angle_equation(
                        obs, points, unknown_indices, num_unknowns_per_point
                    )
                elif obs.obs_type == 'vertical_angle':
                    # Вертикальный угол (зенитное расстояние)
                    indices, coeffs, ell = self._build_zenith_angle_equation(
                        obs, points, unknown_indices, num_unknowns_per_point
                    )
                elif obs.obs_type == 'zenith_angle':
                    # Зенитный угол
                    indices, coeffs, ell = self._build_zenith_angle_equation(
                        obs, points, unknown_indices, num_unknowns_per_point
                    )
                else:
                    self.logger.warning(f"Неизвестный тип измерения: {obs.obs_type} for observation {obs.obs_id}")
                    continue
                
                # Заполнение матрицы для одного уравнения
                if indices:  # Если есть ненулевые коэффициенты
                    self.logger.debug(f"Adding equation for {obs.obs_id} with {len(indices)} coefficients")
                    for col_idx, coeff in zip(indices, coeffs):
                        row_indices.append(obs_index)
                        col_indices.append(col_idx)
                        data_values.append(coeff)
                    L_vector.append(ell)
                    obs_index += 1
                else:
                    self.logger.warning(f"No coefficients generated for observation {obs.obs_id} (type: {obs.obs_type})")
                    
            except Exception as e:
                self.logger.error(f"Ошибка при построении уравнения для {obs.obs_id}: {e}", exc_info=True)
                raise
        
        # Формирование разреженной матрицы
        if obs_index == 0:
            raise ValueError("Не удалось построить ни одного уравнения. Проверьте данные.")
        
        A = sparse.csr_matrix(
            (data_values, (row_indices, col_indices)),
            shape=(obs_index, num_unknowns)
        )
        
        L = np.array(L_vector, dtype=np.float64)
        
        self.logger.info(f"Построена матрица А: {A.shape[0]}×{A.shape[1]}")
        self.logger.info(f"Вектор свободных членов L: {len(L)}")
        self.logger.info(f"Пропущено измерений: {skipped_count}")
        
        return A, L
    
    def _build_direction_equation(
        self,
        obs: Observation,
        points: Dict[str, NetworkPoint],
        unknown_indices: Dict[str, int],
        num_unknowns_per_point: int
    ) -> Tuple[List[int], List[float], float]:
        """
        Формирование уравнения поправок для направления.

        Уравнение поправок для направления (формула Маркузе):

            v = -(sin α / S) · Δx_i + (cos α / S) · Δy_i +
                (sin α / S) · Δx_j - (cos α / S) · Δy_j - ℓ

        где:
        - α - азимут направления
        - S - расстояние между пунктами
        - ℓ = M_изм - M_выч (разность измеренного и вычисленного направления)

        Частные производные:
        - ∂v/∂x_i = -sin α / S
        - ∂v/∂y_i = cos α / S
        - ∂v/∂x_j = sin α / S
        - ∂v/∂y_j = -cos α / S
        """
        from_point = points[obs.from_point_id]
        to_point = points[obs.to_point_id]
        
        # Проверяем, что координаты не None и не нулевые (для FREE точек)
        if from_point.x is None or from_point.y is None or to_point.x is None or to_point.y is None:
            self.logger.warning(f"Пропускаем измерение {obs.obs_id}: отсутствуют координаты точек {obs.from_point_id} или {obs.to_point_id}")
            return [], [], 0.0
        
        # Проверка на нулевые координаты (типично для точек со статусом FREE)
        if (from_point.x == 0.0 and from_point.y == 0.0) or (to_point.x == 0.0 and to_point.y == 0.0):
            self.logger.warning(f"Пропускаем измерение {obs.obs_id}: нулевые координаты у точки {obs.from_point_id if from_point.x == 0.0 and from_point.y == 0.0 else obs.to_point_id}")
            return [], [], 0.0
        
        # Приближенные координаты
        x_i, y_i = from_point.x, from_point.y
        x_j, y_j = to_point.x, to_point.y

        # Разности координат
        dx = x_j - x_i
        dy = y_j - y_i
        
        # Горизонтальное проложение
        S = np.sqrt(dx**2 + dy**2)
        
        if S < 1e-6:
            self.logger.warning(f"Нулевое расстояние между {obs.from_point_id} и {obs.to_point_id}")
            S = 1e-6
        
        # Азимут направления (в радианах)
        alpha = np.arctan2(dy, dx)
        
        # Коэффициенты уравнения поправок
        a_xi = -np.sin(alpha) / S
        a_yi = np.cos(alpha) / S
        a_xj = np.sin(alpha) / S
        a_yj = -np.cos(alpha) / S
        
        # Индексы неизвестных и коэффициенты
        indices = []
        coeffs = []
        
        # Станция (i)
        if obs.from_point_id in unknown_indices:
            idx_base = unknown_indices[obs.from_point_id]
            indices.extend([idx_base, idx_base + 1])
            coeffs.extend([a_xi, a_yi])
        
        # Целевая точка (j)
        if obs.to_point_id in unknown_indices:
            idx_base = unknown_indices[obs.to_point_id]
            indices.extend([idx_base, idx_base + 1])
            coeffs.extend([a_xj, a_yj])
        
        # Свободный член ℓ = M_изм - M_выч
        # Вычисленное направление из приближённых координат
        computed_azimuth = alpha
        
        # Определение единицы измерения угла
        angle_unit = getattr(obs, 'angle_unit', 'degrees')  # 'degrees', 'radians', 'gons'
        
        # Измеренное направление (конвертация в радианы)
        measured_value = obs.value
        
        if angle_unit == 'degrees':
            measured_azimuth = np.deg2rad(measured_value)
        elif angle_unit == 'gons':
            measured_azimuth = measured_value * np.pi / 200.0
        elif angle_unit == 'radians':
            measured_azimuth = measured_value
        else:
            # По умолчанию предполагаем градусы
            measured_azimuth = np.deg2rad(measured_value)
            self.logger.warning(f"Неизвестная единица измерения угла '{angle_unit}', "
                              f"используем градусы")
        
        # Приведение к диапазону [0, 2π]
        computed_azimuth = computed_azimuth % (2 * np.pi)
        measured_azimuth = measured_azimuth % (2 * np.pi)
        
        ell = measured_azimuth - computed_azimuth
        
        # Приведение разности к диапазону [-π, π]
        if ell > np.pi:
            ell -= 2 * np.pi
        elif ell < -np.pi:
            ell += 2 * np.pi
        
        return indices, coeffs, ell
    
    def _build_distance_equation(
        self,
        obs: Observation,
        points: Dict[str, NetworkPoint],
        unknown_indices: Dict[str, int],
        num_unknowns_per_point: int
    ) -> Tuple[List[int], List[float], float]:
        """
        Формирование уравнения поправок для расстояния.
        
        Уравнение поправок для расстояния (формула Маркузе):
        
            v = (cos α) · Δx_i + (sin α) · Δy_i -
                (cos α) · Δx_j - (sin α) · Δy_j - ℓ
        
        где:
        - α - азимут направления
        - ℓ = S_изм - S_выч (разность измеренного и вычисленного расстояния)
        
        Частные производные:
        - ∂v/∂x_i = cos α
        - ∂v/∂y_i = sin α
        - ∂v/∂x_j = -cos α
        - ∂v/∂y_j = -sin α
        """
        from_point = points[obs.from_point_id]
        to_point = points[obs.to_point_id]
        
        # Проверяем, что координаты не None и не нулевые (для FREE точек)
        if from_point.x is None or from_point.y is None or to_point.x is None or to_point.y is None:
            self.logger.warning(f"Пропускаем измерение {obs.obs_id}: отсутствуют координаты точек {obs.from_point_id} или {obs.to_point_id}")
            return [], [], 0.0
        
        # Проверка на нулевые координаты (типично для точек со статусом FREE)
        if (from_point.x == 0.0 and from_point.y == 0.0) or (to_point.x == 0.0 and to_point.y == 0.0):
            self.logger.warning(f"Пропускаем измерение {obs.obs_id}: нулевые координаты у точки {obs.from_point_id if from_point.x == 0.0 and from_point.y == 0.0 else obs.to_point_id}")
            return [], [], 0.0
        
        # Приближенные координаты
        x_i, y_i = from_point.x, from_point.y
        x_j, y_j = to_point.x, to_point.y
        
        # Разности координат
        dx = x_j - x_i
        dy = y_j - y_i
        
        # Горизонтальное проложение
        S = np.sqrt(dx**2 + dy**2)
        
        if S < 1e-6:
            self.logger.warning(f"Нулевое расстояние между {obs.from_point_id} и {obs.to_point_id}")
            S = 1e-6
        
        # Азимут направления (в радианах)
        alpha = np.arctan2(dy, dx)
        
        # Коэффициенты уравнения поправок (ИСПРАВЛЕНО: добавлено деление на S)
        a_xi = np.cos(alpha) / S
        a_yi = np.sin(alpha) / S
        a_xj = -np.cos(alpha) / S
        a_yj = -np.sin(alpha) / S
        
        # Индексы неизвестных и коэффициенты
        indices = []
        coeffs = []
        
        # Станция (i)
        if obs.from_point_id in unknown_indices:
            idx_base = unknown_indices[obs.from_point_id]
            indices.extend([idx_base, idx_base + 1])
            coeffs.extend([a_xi, a_yi])
        
        # Целевая точка (j)
        if obs.to_point_id in unknown_indices:
            idx_base = unknown_indices[obs.to_point_id]
            indices.extend([idx_base, idx_base + 1])
            coeffs.extend([a_xj, a_yj])
        
        # Свободный член ℓ = S_изм - S_выч
        ell = obs.value - S
        
        return indices, coeffs, ell
    
    def _build_height_diff_equation(
        self,
        obs: Observation,
        points: Dict[str, NetworkPoint],
        unknown_indices: Dict[str, int],
        num_unknowns_per_point: int
    ) -> Tuple[List[int], List[float], float]:
        """
        Формирование уравнения поправок для превышения.
        
        Уравнение поправок для превышения:
        
            v = Δh_i - Δh_j - ℓ
        
        где:
        - ℓ = h_изм - (H_j - H_i) (разность измеренного и вычисленного превышения)
        
        Частные производные:
        - ∂v/∂h_i = 1
        - ∂v/∂h_j = -1
        """
        indices = []
        coeffs = []
        
        # Определяем индекс высоты в векторе неизвестных
        # Для 2D сети: heights не обрабатываются
        # Для 3D сети: каждая точка имеет 3 неизвестных (x, y, h)
        
        if num_unknowns_per_point == 2:
            self.logger.warning(
                f"Измерение превышения {obs.obs_id} в 2D сети. "
                "Превышение будет пропущено."
            )
            return [], [], 0.0
        
        # Станция (i)
        if obs.from_point_id in unknown_indices:
            idx_base = unknown_indices[obs.from_point_id]
            idx_h = idx_base + 2  # Индекс высоты (третий параметр)
            indices.append(idx_h)
            coeffs.append(1.0)
        
        # Целевая точка (j)
        if obs.to_point_id in unknown_indices:
            idx_base = unknown_indices[obs.to_point_id]
            idx_h = idx_base + 2
            indices.append(idx_h)
            coeffs.append(-1.0)
        
        # Свободный член ℓ = h_изм - (H_j - H_i)
        from_point = points[obs.from_point_id]
        to_point = points[obs.to_point_id]
        
        # Проверяем, что координаты не None (для высоты нужны хотя бы x,y)
        if from_point.x is None or from_point.y is None or to_point.x is None or to_point.y is None:
            self.logger.warning(f"Пропускаем измерение {obs.obs_id}: отсутствуют координаты точек {obs.from_point_id} или {obs.to_point_id}")
            return [], [], 0.0
        
        # Приближенные высоты
        h_i = from_point.h if from_point.h is not None else 0.0
        h_j = to_point.h if to_point.h is not None else 0.0

        # Проверяем, что хотя бы одна высота не None (для 3D сети)
        if num_unknowns_per_point == 3 and h_i == 0.0 and h_j == 0.0 and from_point.h is None and to_point.h is None:
            self.logger.warning(f"Пропускаем измерение {obs.obs_id}: отсутствуют высоты точек {obs.from_point_id} или {obs.to_point_id}")
            return [], [], 0.0
        
        # Высоты инструмента и цели (если заданы)
        instrument_height = getattr(obs, 'instrument_height', 0.0)
        target_height = getattr(obs, 'target_height', 0.0)
        
        # Вычисленное превышение с учётом высот инструмента/цели
        computed_height_diff = (h_j + target_height) - (h_i + instrument_height)
        
        # Измеренное превышение
        measured_height_diff = obs.value
        
        # Свободный член
        ell = measured_height_diff - computed_height_diff
        
        return indices, coeffs, ell
    
    def _build_gnss_vector_equations(
        self,
        obs: Observation,
        points: Dict[str, NetworkPoint],
        unknown_indices: Dict[str, int],
        num_unknowns_per_point: int
    ) -> Tuple[List[List[int]], List[List[float]], List[float]]:
        """
        Формирование системы уравнений поправок для вектора ГНСС (3 уравнения).
        
        Вектор ГНСС даёт три независимых уравнения для компонент X, Y, Z:
        
            v_x = -Δx_i + Δx_j - ΔX_изм
            v_y = -Δy_i + Δy_j - ΔY_изм
            v_z = -Δz_i + Δz_j - ΔZ_изм
        
        Частные производные:
        - ∂v_x/∂x_i = -1, ∂v_x/∂x_j = 1
        - ∂v_y/∂y_i = -1, ∂v_y/∂y_j = 1
        - ∂v_z/∂z_i = -1, ∂v_z/∂z_j = 1
        """
        from_point = points[obs.from_point_id]
        to_point = points[obs.to_point_id]

        # Проверяем, что координаты не None
        if (from_point.x is None or from_point.y is None or
            (num_unknowns_per_point == 3 and from_point.h is None) or
            to_point.x is None or to_point.y is None or
            (num_unknowns_per_point == 3 and to_point.h is None)):
            self.logger.warning(f"Пропускаем GNSS измерение {obs.obs_id}: отсутствуют координаты точек {obs.from_point_id} или {obs.to_point_id}")
            return [], [], []

        indices_list = []
        coeffs_list = []
        ell_list = []

        # Получаем приращения координат из вектора ГНСС
        delta_x = getattr(obs, 'delta_x', None) or obs.value
        delta_y = getattr(obs, 'delta_y', None) or 0.0
        delta_z = getattr(obs, 'delta_z', None) or 0.0
        
        # Три уравнения для компонент вектора
        for component_idx in range(3):
            indices = []
            coeffs = []
            
            # Станция (i)
            if obs.from_point_id in unknown_indices:
                idx_base = unknown_indices[obs.from_point_id]
                
                if num_unknowns_per_point == 3:
                    # 3D сеть: x=0, y=1, z=2
                    idx_comp = idx_base + component_idx
                    indices.append(idx_comp)
                    coeffs.append(-1.0)
                elif component_idx < 2:
                    # 2D сеть: только x и y
                    idx_comp = idx_base + component_idx
                    indices.append(idx_comp)
                    coeffs.append(-1.0)
            
            # Целевая точка (j)
            if obs.to_point_id in unknown_indices:
                idx_base = unknown_indices[obs.to_point_id]
                
                if num_unknowns_per_point == 3:
                    idx_comp = idx_base + component_idx
                    indices.append(idx_comp)
                    coeffs.append(1.0)
                elif component_idx < 2:
                    idx_comp = idx_base + component_idx
                    indices.append(idx_comp)
                    coeffs.append(1.0)
            
            # Свободный член (значение компоненты вектора)
            if component_idx == 0:
                ell = delta_x
            elif component_idx == 1:
                ell = delta_y
            else:
                ell = delta_z
            
            indices_list.append(indices)
            coeffs_list.append(coeffs)
            ell_list.append(ell)
        
        return indices_list, coeffs_list, ell_list
    
    def _build_angle_equation(
        self,
        obs: Observation,
        points: Dict[str, NetworkPoint],
        unknown_indices: Dict[str, int],
        num_unknowns_per_point: int
    ) -> Tuple[List[int], List[float], float]:
        """
        Формирование уравнения поправок для угла (азимута, вертикального угла).
        
        Угол между двумя направлениями обрабатывается как разность двух направлений.
        """
        # Для простоты рассматриваем угол как направление
        # В полной реализации нужно учитывать оба направления
        return self._build_direction_equation(
            obs, points, unknown_indices, num_unknowns_per_point
        )
    
    def _build_zenith_angle_equation(
        self,
        obs: Observation,
        points: Dict[str, NetworkPoint],
        unknown_indices: Dict[str, int],
        num_unknowns_per_point: int
    ) -> Tuple[List[int], List[float], float]:
        """
        Формирование уравнения поправок для зенитного угла.
        
        Уравнение поправок для зенитного угла аналогично направлению,
        но с учётом вертикальной плоскости.
        """
        from_point = points[obs.from_point_id]
        to_point = points[obs.to_point_id]
        
        # Проверяем, что координаты не None
        if from_point.x is None or from_point.y is None or to_point.x is None or to_point.y is None:
            self.logger.warning(f"Пропускаем измерение {obs.obs_id}: отсутствуют плановые координаты точек {obs.from_point_id} или {obs.to_point_id}")
            return [], [], 0.0
        
        # Приближенные координаты
        x_i, y_i = from_point.x, from_point.y
        x_j, y_j = to_point.x, to_point.y
        
        # Разности координат
        dx = x_j - x_i
        dy = y_j - y_i
        
        # Горизонтальное проложение
        S_h = np.sqrt(dx**2 + dy**2)
        
        if S_h < 1e-6:
            self.logger.warning(f"Нулевое горизонтальное расстояние между {obs.from_point_id} и {obs.to_point_id}")
            S_h = 1e-6
        
        # Вертикальное превышение (если есть высоты)
        dh = 0.0
        if hasattr(from_point, 'h') and hasattr(to_point, 'h'):
            if from_point.h is not None and to_point.h is not None:
                dh = to_point.h - from_point.h
        
        # Наклонное расстояние
        S = np.sqrt(S_h**2 + dh**2)
        
        # Вычисленное зенитное расстояние из приближённых координат
        if S > 1e-6:
            computed_zenith = np.arctan2(S_h, dh)
            if computed_zenith < 0:
                computed_zenith += np.pi
        else:
            computed_zenith = np.pi / 2
        
        # Измеренное зенитное расстояние (в радианах)
        measured_zenith = np.deg2rad(obs.value)
        
        # Свободный член ℓ = Z_изм - Z_выч
        ell = measured_zenith - computed_zenith
        
        # Приведение разности к диапазону [-π, π]
        while ell > np.pi:
            ell -= 2 * np.pi
        while ell < -np.pi:
            ell += 2 * np.pi
        
        # Коэффициенты уравнения поправок
        # ∂v/∂x_i = -cos α · cos Z / S
        # ∂v/∂y_i = -sin α · cos Z / S
        # ∂v/∂z_i = sin Z / S
        # ∂v/∂x_j = cos α · cos Z / S
        # ∂v/∂y_j = sin α · cos Z / S
        # ∂v/∂z_j = -sin Z / S
        
        alpha = np.arctan2(dy, dx)
        zenith = computed_zenith
        
        a_xi = -np.cos(alpha) * np.cos(zenith) / S
        a_yi = -np.sin(alpha) * np.cos(zenith) / S
        a_xj = np.cos(alpha) * np.cos(zenith) / S
        a_yj = np.sin(alpha) * np.cos(zenith) / S
        
        indices = []
        coeffs = []
        
        # Станция (i)
        if obs.from_point_id in unknown_indices:
            idx_base = unknown_indices[obs.from_point_id]
            if num_unknowns_per_point >= 2:
                indices.extend([idx_base, idx_base + 1])
                coeffs.extend([a_xi, a_yi])
            if num_unknowns_per_point == 3:
                indices.append(idx_base + 2)
                coeffs.append(np.sin(zenith) / S)
        
        # Целевая точка (j)
        if obs.to_point_id in unknown_indices:
            idx_base = unknown_indices[obs.to_point_id]
            if num_unknowns_per_point >= 2:
                indices.extend([idx_base, idx_base + 1])
                coeffs.extend([a_xj, a_yj])
            if num_unknowns_per_point == 3:
                indices.append(idx_base + 2)
                coeffs.append(-np.sin(zenith) / S)
        
        return indices, coeffs, ell
