"""
Модуль формирования весовой матрицы измерений

Этот модуль рассчитывает веса измерений на основе:
1. Метрологических характеристик приборов
2. Условий измерения (длина линии, число станций)
3. Ошибок центрирования и редуцирования
4. Индивидуальных множителей веса

Автор: GeoAdjust-Pro Team
Версия: 2.0
"""

import numpy as np
from scipy import sparse
from typing import List, Dict, Any, Optional
import logging

from ..network.models import Observation
from .instruments import Instrument

logger = logging.getLogger(__name__)


class WeightBuilder:
    """
    Формирование весовой матрицы на основе метрологии приборов.
    
    Веса измерений рассчитываются по формуле:
    
        P = 1 / σ²
    
    где σ - апостериорная СКО измерения, вычисленная с учётом:
    - Инструментальной погрешности прибора
    - Ошибок центрирования и редуцирования
    - Влияния внешних условий (атмосфера, рефракция)
    - Длины измеряемой линии (для дальномеров)
    - Числа станций (для нивелирования)
    """
    
    def __init__(self, instrument_library: Dict[str, Instrument] = None):
        """
        Инициализация построителя весовой матрицы.
        
        Параметры:
        -----------
        instrument_library : Dict[str, Instrument], optional
            Словарь приборов {instrument_name: Instrument}
        """
        self.instrument_library = instrument_library or {}
        self.logger = logging.getLogger(__name__)
    
    def build_weight_matrix(
        self,
        observations: List[Observation],
        points: Dict[str, Any] = None
    ) -> sparse.csr_matrix:
        """
        Построение весовой матрицы измерений.
        
        Параметры:
        -----------
        observations : List[Observation]
            Список измерений
        points : Dict[str, Any], optional
            Словарь пунктов (может использоваться для расчёта расстояний)
        
        Возвращает:
        ------------
        P : sparse.csr_matrix
            Диагональная весовая матрица (размерность n × n), где n - число измерений
        
        Пример:
        -------
        >>> weight_builder = WeightBuilder(instrument_library)
        >>> P = weight_builder.build_weight_matrix(observations, points)
        >>> print(f"Весовая матрица: {P.shape[0]}×{P.shape[1]}")
        """
        if not observations:
            raise ValueError("Список измерений пуст")
        
        weights = []
        
        for obs in observations:
            if not obs.is_active:
                continue
            
            try:
                # Расчёт априорной СКО измерения
                sigma = self._calculate_apriori_sigma(obs, points)
                
                # Вес = 1 / σ²
                if sigma > 0:
                    weight = 1.0 / (sigma ** 2)
                else:
                    self.logger.warning(f"СКО для {obs.obs_id} равно нулю, используется вес 1.0")
                    weight = 1.0
                
                # Учёт индивидуального множителя веса
                if hasattr(obs, 'weight_multiplier') and obs.weight_multiplier is not None:
                    weight *= obs.weight_multiplier
                
                weights.append(weight)
                
            except Exception as e:
                self.logger.error(f"Ошибка при расчёте веса для {obs.obs_id}: {e}", exc_info=True)
                # Используем вес по умолчанию
                weights.append(1.0)
        
        if not weights:
            raise ValueError("Не удалось рассчитать ни одного веса")
        
        # Формирование диагональной матрицы
        P = sparse.diags(weights, format='csr')
        
        self.logger.info(f"Построена весовая матрица: {len(weights)} измерений")
        self.logger.info(f"Диапазон весов: [{min(weights):.6f}, {max(weights):.6f}]")
        
        return P
    
    def _calculate_apriori_sigma(
        self,
        obs: Observation,
        points: Dict[str, Any] = None
    ) -> float:
        """
        Расчёт априорной СКО измерения.
        
        Параметры:
        -----------
        obs : Observation
            Измерение
        points : Dict[str, Any], optional
            Словарь пунктов для расчёта расстояний
        
        Возвращает:
        ------------
        sigma : float
            Априорная СКО измерения в единицах измерения
        """
        # Получение прибора из библиотеки
        instrument = None
        instrument_name = getattr(obs, 'instrument_name', None)
        if instrument_name and instrument_name in self.instrument_library:
            instrument = self.instrument_library[instrument_name]
        elif obs.sigma_apriori is not None:
            # Если указана априорная СКО в самом измерении
            return obs.sigma_apriori
        else:
            self.logger.warning(
                f"Прибор {instrument_name or 'не указан'} не найден в библиотеке. "
                f"Используется стандартная СКО для {obs.obs_type}."
            )
            return self._get_default_sigma(obs.obs_type, obs.value)
        
        # Расчёт СКО в зависимости от типа измерения
        if obs.obs_type in ['direction', 'azimuth']:
            sigma = self._calculate_angular_sigma(instrument, obs, points)
        
        elif obs.obs_type in ['vertical_angle', 'zenith_angle']:
            sigma = self._calculate_angular_sigma(instrument, obs, points)
        
        elif obs.obs_type == 'distance':
            sigma = self._calculate_distance_sigma(instrument, obs, points)
        
        elif obs.obs_type == 'height_diff':
            sigma = self._calculate_leveling_sigma(instrument, obs, points)
        
        elif obs.obs_type == 'gnss_vector':
            sigma = self._calculate_gnss_sigma(instrument, obs, points)
        
        else:
            sigma = self._get_default_sigma(obs.obs_type, obs.value)
        
        return max(sigma, 1e-9)  # Защита от нулевой СКО
    
    def _calculate_angular_sigma(
        self,
        instrument: Instrument,
        obs: Observation,
        points: Dict[str, Any] = None
    ) -> float:
        """
        Расчёт СКО углового измерения (направления, азимута).
        
        Учитываются:
        - Инструментальная погрешность прибора
        - Ошибки центрирования инструмента и цели
        - Длина измеряемой линии
        
        Формула влияния ошибок центрирования:
        ε = (Δ / S) · ρ
        где:
        - Δ - ошибка центрирования в метрах
        - S - расстояние в метрах
        - ρ - переводной множитель (1 для радиан, 206265 для секунд)
        """
        # Базовая СКО от прибора (перевод из секунд в радианы)
        sigma_base = instrument.angular_accuracy / 3600.0 * (np.pi / 180.0)
        
        # Учёт ошибок центрирования для угловых измерений
        centering_error_mm = np.sqrt(
            instrument.centering_error**2 +
            instrument.target_centering_error**2
        )
        
        # Расстояние между пунктами (если доступно)
        distance_m = self._get_distance(obs, points)
        
        if distance_m is not None and distance_m > 0:
            # Влияние ошибок центрирования на угол (в радианах)
            # Формула: ε = (Δ / S) · ρ, где ρ = 1 для радиан
            # Δ - ошибка центрирования в метрах, S - расстояние в метрах
            centering_error_m = centering_error_mm / 1000.0
            centering_influence = centering_error_m / distance_m
            
            # Суммарная СКО (квадратичное суммирование)
            sigma_base = np.sqrt(sigma_base**2 + centering_influence**2)
        
        self.logger.debug(
            f"Угловое измерение {obs.obs_id}: "
            f"σ_base={sigma_base*206265:.2f}\", σ_total={sigma_base*206265:.2f}\""
        )
        
        return sigma_base
    
    def _calculate_distance_sigma(
        self,
        instrument: Instrument,
        obs: Observation,
        points: Dict[str, Any] = None
    ) -> float:
        """
        Расчёт СКО линейного измерения.
        
        Используется формула: σ = √(a² + (b·D)²), где:
        - a - постоянная составляющая (мм)
        - b - пропорциональная ошибка (мм/км)
        - D - длина линии (км)
        
        Также учитываются атмосферные условия (если заданы).
        """
        # Расстояние между пунктами
        distance_m = self._get_distance(obs, points)
        if distance_m is None:
            distance_m = obs.value if hasattr(obs, 'value') else 100.0
        
        distance_km = distance_m / 1000.0
        
        # Базовая точность из паспорта прибора
        # σ = a + b·D, где a - постоянная составляющая (мм), b - пропорциональная (мм/км)
        a = getattr(instrument, 'distance_accuracy_a', 2.0)  # мм
        b = getattr(instrument, 'distance_accuracy_b', 2.0)  # мм/км
        
        # СКО линейного измерения (мм)
        sigma_mm = np.sqrt(a**2 + (b * distance_km)**2)
        
        # Учёт атмосферных условий (если заданы)
        temperature = getattr(obs, 'temperature', None)
        pressure = getattr(obs, 'pressure', None)
        
        if temperature is not None and pressure is not None:
            # Поправка на отклонение от стандартных условий
            temperature_default = getattr(instrument, 'temperature_default', 20.0)
            pressure_default = getattr(instrument, 'pressure_default', 1013.25)
            
            delta_t = abs(temperature - temperature_default)
            delta_p = abs(pressure - pressure_default)
            
            # Коэффициент влияния (упрощённая модель)
            atmospheric_factor = 1.0 + 0.01 * (delta_t / 10.0 + delta_p / 50.0)
            sigma_mm *= atmospheric_factor
        
        # Перевод в метры
        sigma_m = sigma_mm / 1000.0
        
        self.logger.debug(
            f"Линейное измерение {obs.obs_id}: "
            f"D={distance_m:.3f}м, σ={sigma_m*1000:.2f}мм"
        )
        
        return sigma_m
    
    def _calculate_leveling_sigma(
        self,
        instrument: Instrument,
        obs: Observation,
        points: Dict[str, Any] = None
    ) -> float:
        """
        Расчёт СКО нивелирного превышения.
        
        Учитываются:
        - СКО на 1 км хода (из паспорта прибора)
        - Число станций или длина хода
        """
        # Число станций (если указано)
        num_stands = getattr(obs, 'num_stands', None)
        
        # Длина хода (если доступна)
        distance_km = self._get_distance(obs, points)
        if distance_km is not None:
            distance_km = distance_km / 1000.0
        
        # Расчёт СКО
        if num_stands is not None and num_stands > 0:
            # По числу станций
            sigma = instrument.calculate_leveling_sigma(num_stands)
        elif distance_km is not None and distance_km > 0:
            # По длине хода
            sigma_mm = instrument.double_run_error_per_km * np.sqrt(distance_km)
            sigma = sigma_mm / 1000.0  # Перевод в метры
        else:
            # По умолчанию: одна станция
            sigma = instrument.calculate_leveling_sigma(1)
        
        self.logger.debug(
            f"Нивелирное измерение {obs.obs_id}: σ={sigma*1000:.2f}мм"
        )
        
        return sigma
    
    def build_gnss_weight_matrix(self, obs: Observation) -> sparse.csr_matrix:
        """
        Построение весовой матрицы для вектора ГНСС с учётом корреляций.
        
        Весовая матрица = обратная к ковариационной матрице.
        Для вектора ГНСС это матрица 3×3.
        
        Параметры:
        -----------
        obs : Observation
            Измерение вектора ГНСС
        
        Возвращает:
        ------------
        P : sparse.csr_matrix
            Весовая матрица 3×3
        """
        # Получение ковариационной матрицы из наблюдения
        cov_matrix = getattr(obs, 'covariance_matrix', None)
        
        if cov_matrix is None:
            # Если ковариационная матрица не задана, используем диагональную
            sigma_x = getattr(obs, 'sigma_x', 0.01)
            sigma_y = getattr(obs, 'sigma_y', 0.01)
            sigma_z = getattr(obs, 'sigma_z', 0.01)
            
            cov_matrix = np.array([
                [sigma_x**2, 0.0, 0.0],
                [0.0, sigma_y**2, 0.0],
                [0.0, 0.0, sigma_z**2]
            ])
        
        try:
            cov_matrix = np.array(cov_matrix)
            # Обратная ковариационная матрица = весовая матрица
            P = np.linalg.inv(cov_matrix)
            return sparse.csr_matrix(P)
        except Exception as e:
            self.logger.warning(f"Ошибка при инвертировании ковариационной матрицы ГНСС: {e}")
            # Возврат диагональной матрицы с обратными дисперсиями
            sigma_x = getattr(obs, 'sigma_x', 0.01)
            sigma_y = getattr(obs, 'sigma_y', 0.01)
            sigma_z = getattr(obs, 'sigma_z', 0.01)
            
            P = sparse.diags([1.0/sigma_x**2, 1.0/sigma_y**2, 1.0/sigma_z**2])
            return sparse.csr_matrix(P)
    
    def _calculate_gnss_sigma(
        self,
        instrument: Instrument,
        obs: Observation,
        points: Dict[str, Any] = None
    ) -> float:
        """
        Расчёт СКО вектора ГНСС.
        
        Для векторов ГНСС используется ковариационная матрица 3×3.
        Здесь возвращаем среднюю СКО по компонентам с учётом корреляций.
        """
        # Получаем полную ковариационную матрицу 3×3 (если доступна)
        cov_matrix = getattr(obs, 'covariance_matrix', None)
        
        if cov_matrix is not None:
            try:
                cov_matrix = np.array(cov_matrix)
                # Проверка положительной определённости
                eigenvalues = np.linalg.eigvalsh(cov_matrix)
                if np.all(eigenvalues > 0):
                    # Использование полной ковариационной матрицы
                    # След матрицы (сумма дисперсий по диагонали)
                    trace = np.trace(cov_matrix)
                    # Средняя СКО с учётом корреляций
                    sigma = np.sqrt(trace / 3.0)
                else:
                    self.logger.warning(f"Ковариационная матрица ГНСС не является положительно определённой")
                    cov_matrix = None
            except Exception as e:
                self.logger.warning(f"Ошибка при использовании ковариационной матрицы ГНСС: {e}")
                cov_matrix = None
        
        if cov_matrix is None:
            # Получаем индивидуальные СКО компонент (если указаны)
            sigma_x = getattr(obs, 'sigma_x', None)
            sigma_y = getattr(obs, 'sigma_y', None)
            sigma_z = getattr(obs, 'sigma_z', None)
            
            if sigma_x is not None and sigma_y is not None and sigma_z is not None:
                # Средняя СКО по компонентам
                sigma = np.sqrt((sigma_x**2 + sigma_y**2 + sigma_z**2) / 3.0)
            else:
                # Используем базовую точность ГНСС приёмника
                # Для статических измерений: 3-5 мм + 0.5 ppm
                distance_km = self._get_distance(obs, points)
                if distance_km is None:
                    distance_km = 1.0  # По умолчанию 1 км
                
                sigma_mm = np.sqrt(3.0**2 + (0.5 * distance_km)**2)
                sigma = sigma_mm / 1000.0  # Перевод в метры
        
        self.logger.debug(
            f"Вектор ГНСС {obs.obs_id}: σ={sigma*1000:.2f}мм"
        )
        
        return sigma
    
    def _get_distance(
        self,
        obs: Observation,
        points: Dict[str, Any] = None
    ) -> Optional[float]:
        """
        Получение расстояния между пунктами измерения.
        
        Параметры:
        -----------
        obs : Observation
            Измерение
        points : Dict[str, Any], optional
            Словарь пунктов
        
        Возвращает:
        ------------
        distance : float or None
            Расстояние в метрах или None, если невозможно вычислить
        """
        # Если расстояние уже указано в измерении
        if hasattr(obs, 'distance') and obs.distance is not None:
            return obs.distance
        
        # Вычисляем расстояние по координатам пунктов
        if points is not None:
            from_point = points.get(obs.from_point)
            to_point = points.get(obs.to_point)
            
            if from_point is not None and to_point is not None:
                dx = to_point.x - from_point.x
                dy = to_point.y - from_point.y
                
                # Для 3D учитываем высоту
                if hasattr(from_point, 'h') and hasattr(to_point, 'h'):
                    if from_point.h is not None and to_point.h is not None:
                        dz = to_point.h - from_point.h
                        return np.sqrt(dx**2 + dy**2 + dz**2)
                
                return np.sqrt(dx**2 + dy**2)
        
        return None
    
    def _get_default_sigma(self, obs_type: str, value: float) -> float:
        """
        Получение стандартной СКО для типа измерения (заглушка).
        
        Параметры:
        -----------
        obs_type : str
            Тип измерения
        value : float
            Значение измерения
        
        Возвращает:
        ------------
        sigma : float
            Стандартная СКО
        """
        default_sigmas = {
            'direction': 5.0 / 206265,  # 5 секунд в радианах
            'azimuth': 5.0 / 206265,
            'vertical_angle': 10.0 / 206265,
            'zenith_angle': 10.0 / 206265,
            'distance': 0.010,  # 10 мм
            'height_diff': 0.005,  # 5 мм
            'gnss_vector': 0.010,  # 10 мм
        }
        
        sigma = default_sigmas.get(obs_type, 0.01)
        
        self.logger.debug(f"Стандартная СКО для {obs_type}: {sigma}")
        
        return sigma
