"""
Модуль полного цикла обработки геодезических данных

Этот модуль интегрирует все компоненты системы GeoAdjust-Pro в единый
конвейер обработки от полевых измерений до финальных результатов.

Автор: GeoAdjust-Pro Team
Версия: 2.0
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

from .network.models import NetworkPoint, Observation
from .preprocessing.module import PreprocessingModule
from .adjustment.equations_builder import EquationsBuilder
from .adjustment.weight_builder import WeightBuilder
from .adjustment.engine import AdjustmentEngine
from .reliability.baarda_method import BaardaReliability
from .analysis.gross_errors import GrossErrorAnalyzer
from .adjustment.instruments import Instrument

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """
    Полный цикл обработки геодезических данных от полевых измерений до результатов.
    
    Конвейер обработки включает следующие этапы:
    
    1. ИМПОРТ ДАННЫХ
       - Парсинг формата прибора (GSI, SDR, RINEX, TXT)
       - Распознавание станций, приемов, измерений
       - Формирование списка наблюдений и пунктов
    
    2. ПРЕДВАРИТЕЛЬНАЯ ОБРАБОТКА
       - Распознавание топологии сети
       - Формирование ходов и секций
       - Обработка приемов и замыкания горизонта
       - Контроль 27 допусков СП 11-104-97
       - Применение редукций (атмосфера, рефракция, кривизна)
       - Расчёт предварительных координат
    
    3. ФОРМИРОВАНИЕ МАТЕМАТИЧЕСКОЙ МОДЕЛИ
       - Построение матрицы коэффициентов А ← EquationsBuilder
       - Расчёт вектора свободных членов L
       - Формирование весовой матрицы Р ← WeightBuilder
       - Проверка ранга системы
    
    4. УРАВНИВАНИЕ
       - Решение нормальных уравнений (МНК, робастные методы)
       - Расчёт остатков и СКО единицы веса
       - Расчёт ковариационной матрицы
    
    5. АНАЛИЗ РЕЗУЛЬТАТОВ
       - Расчёт СКО положения пунктов
       - Построение эллипсов ошибок
       - Анализ надёжности по Баарду
       - Поиск грубых ошибок
       - Анализ соответствия нормативным классам
    
    6. ФОРМИРОВАНИЕ ОТЧЁТОВ
       - Ведомость уравненных координат
       - Ведомость поправок в измерения
       - Отчёт по ГОСТ 7.32-2017
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Инициализация конвейера обработки.
        
        Параметры:
        -----------
        config : Dict[str, Any], optional
            Конфигурация обработки:
            - 'preprocessing': настройки предобработки
            - 'instruments': библиотека приборов
            - 'adjustment': параметры уравнивания
            - 'analysis': параметры анализа
        """
        self.config = config or {}
        self.preprocessing = PreprocessingModule()
        self.equations_builder = EquationsBuilder()
        self.engine = AdjustmentEngine()
        self.logger = logger
        
        # Инициализация библиотеки приборов
        self.instrument_library = self._init_instrument_library()
    
    def _init_instrument_library(self) -> Dict[str, Instrument]:
        """Инициализация библиотеки приборов из конфигурации"""
        instrument_library = {}
        
        instruments_config = self.config.get('instruments', {})
        for instr_name, instr_config in instruments_config.items():
            try:
                instrument_library[instr_name] = Instrument(**instr_config)
            except Exception as e:
                self.logger.error(f"Ошибка при создании прибора {instr_name}: {e}")
        
        return instrument_library
    
    def process_field_data(
        self,
        field_observations: List[Observation],
        control_points: Dict[str, NetworkPoint],
        initial_approximate_points: Dict[str, NetworkPoint] = None
    ) -> Dict[str, Any]:
        """
        Полная обработка полевых геодезических данных.
        
        Параметры:
        -----------
        field_observations : List[Observation]
            Список полевых измерений
        control_points : Dict[str, NetworkPoint]
            Словарь исходных пунктов {point_id: NetworkPoint}
        initial_approximate_points : Dict[str, NetworkPoint], optional
            Словарь приближённых координат определяемых пунктов
        
        Возвращает:
        ------------
        result : Dict[str, Any]
            Словарь с полными результатами обработки, включающий:
            - 'preprocessing': результаты предобработки
            - 'adjustment': результаты уравнивания
            - 'reliability': анализ надёжности
            - 'gross_errors': обнаруженные грубые ошибки
            - 'matrices': матрицы A, L, P
            - 'statistics': статистика обработки
        
        Пример:
        -------
        >>> pipeline = ProcessingPipeline(config)
        >>> result = pipeline.process_field_data(observations, control_points, approx_points)
        >>> print(f"СКО единицы веса: {result['adjustment']['sigma0']:.6f}")
        >>> print(f"Число избыточных измерений: {result['statistics']['redundancy']}")
        """
        self.logger.info("=" * 80)
        self.logger.info("НАЧАЛО ПОЛНОЙ ОБРАБОТКИ ГЕОДЕЗИЧЕСКИХ ДАННЫХ")
        self.logger.info("=" * 80)
        
        # Этап 1: Предварительная обработка
        self.logger.info("\n[ЭТАП 1] Предварительная обработка данных")
        preprocessing_result = self.preprocessing.run_all_stages(
            raw_data={'observations': field_observations, 'points': control_points},
            config=self.config.get('preprocessing', {})
        )
        
        # Получение обработанных данных
        processed_observations = preprocessing_result.get(
            'corrected_observations', 
            field_observations
        )
        topology = preprocessing_result.get('topology', {})
        
        # Объединение всех пунктов
        all_points = control_points.copy()
        if initial_approximate_points:
            all_points.update(initial_approximate_points)
        
        self.logger.info(f"  ✓ Обработано измерений: {len(processed_observations)}")
        self.logger.info(f"  ✓ Всего пунктов: {len(all_points)}")
        self.logger.info(f"  ✓ Исходных пунктов: {len(control_points)}")
        
        # Определение списка исходных пунктов
        fixed_point_ids = [
            pid for pid, p in control_points.items() 
            if p.coord_type == 'FIXED'
        ]
        
        # Этап 2: Построение матрицы коэффициентов уравнений поправок
        self.logger.info("\n[ЭТАП 2] Формирование математической модели")
        self.logger.info("  Построение матрицы коэффициентов уравнений поправок...")
        
        try:
            A, L, validation = self.equations_builder.build_adjustment_matrix(
                observations=processed_observations,
                points=all_points,
                fixed_points=fixed_point_ids
            )
            
            self.logger.info(f"  ✓ Матрица А: {A.shape[0]}×{A.shape[1]}")
            self.logger.info(f"  ✓ Вектор свободных членов L: {len(L)}")
            self.logger.info(f"  ✓ Статус валидации: {validation['status']}")
            self.logger.info(f"  → {validation['message']}")
            
            # Проверка статуса валидации
            if validation["status"] == "FAILED":
                self.logger.error(f"Критическая ошибка валидации: {validation['message']}")
                raise ValueError(validation['message'])
            elif validation["status"] == "WARNING":
                self.logger.warning(f"Предупреждение валидации: {validation['message']}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при построении матрицы А: {e}", exc_info=True)
            raise
        
        # Этап 3: Формирование весовой матрицы
        self.logger.info("\n[ЭТАП 3] Формирование весовой матрицы")
        
        weight_builder = WeightBuilder(self.instrument_library)
        
        try:
            P = weight_builder.build_weight_matrix(processed_observations, all_points)
            self.logger.info(f"  ✓ Весовая матрица P: {P.shape[0]}×{P.shape[1]}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при формировании весовой матрицы: {e}", exc_info=True)
            raise
        
        # Этап 4: Уравнивание
        self.logger.info("\n[ЭТАП 4] Уравнивание сети")
        
        try:
            adjustment_result = self.engine.adjust(A, L, P)
            
            self.logger.info(f"  ✓ СКО единицы веса: {adjustment_result['sigma0']:.6f}")
            self.logger.info(f"  ✓ Число итераций: {adjustment_result['iterations']}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при уравнивании: {e}", exc_info=True)
            raise
        
        # Этап 5: Анализ надёжности по Баарду
        self.logger.info("\n[ЭТАП 5] Анализ надёжности сети по Баарду")
        
        try:
            baarda = BaardaMethod(A, P, adjustment_result['sigma0'])
            reliability_analysis = baarda.analyze()
            
            self.logger.info(
                f"  ✓ Внутренняя надёжность (средняя): "
                f"{reliability_analysis['avg_internal_reliability']:.4f}"
            )
            self.logger.info(
                f"  ✓ Обнаружено грубых ошибок: "
                f"{reliability_analysis['blunder_detection']['num_blunders']}"
            )
            
        except Exception as e:
            self.logger.warning(f"Анализ надёжности не выполнен: {e}")
            reliability_analysis = {'error': str(e)}
        
        # Этап 6: Поиск грубых ошибок
        self.logger.info("\n[ЭТАП 6] Поиск грубых ошибок")
        
        try:
            gross_error_analyzer = GrossErrorAnalyzer(
                A=A,
                P=P,
                V=adjustment_result['residuals'],
                sigma0=adjustment_result['sigma0'],
                observations_ids=[obs.obs_id for obs in processed_observations]
            )
            
            gross_errors = gross_error_analyzer.detect_gross_errors()
            
            self.logger.info(f"  ✓ Методов анализа: {len(gross_errors)}")
            for method_name, results in gross_errors.items():
                if isinstance(results, (list, np.ndarray)):
                    num_suspicious = len(results)
                    self.logger.info(
                        f"    - {method_name}: {num_suspicious} подозрительных измерений"
                    )
            
        except Exception as e:
            self.logger.warning(f"Поиск грубых ошибок не выполнен: {e}")
            gross_errors = {'error': str(e)}
        
        # Формирование полного результата
        full_result = {
            'preprocessing': preprocessing_result,
            'adjustment': adjustment_result,
            'reliability': reliability_analysis,
            'gross_errors': gross_errors,
            'matrices': {
                'A': A,
                'L': L,
                'P': P
            },
            'statistics': {
                'num_observations': len(processed_observations),
                'num_points': len(all_points),
                'num_fixed_points': len(fixed_point_ids),
                'num_unknowns': A.shape[1],
                'redundancy': len(processed_observations) - A.shape[1],
                'degrees_of_freedom': len(processed_observations) - A.shape[1]
            }
        }
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО")
        self.logger.info("=" * 80)
        
        return full_result
    
    def process_free_network(
        self,
        field_observations: List[Observation],
        initial_approximate_points: Dict[str, NetworkPoint]
    ) -> Dict[str, Any]:
        """
        Обработка свободной сети (без исходных пунктов).
        
        Свободная сеть уравнивается с применением минимальных ограничений
        для устранения дефекта ранга нормальной матрицы.
        
        Параметры:
        -----------
        field_observations : List[Observation]
            Список полевых измерений
        initial_approximate_points : Dict[str, NetworkPoint]
            Словарь приближённых координат всех пунктов
        
        Возвращает:
        ------------
        result : Dict[str, Any]
            Словарь с результатами свободного уравнивания
        
        Пример:
        -------
        >>> pipeline = ProcessingPipeline(config)
        >>> result = pipeline.process_free_network(observations, approx_points)
        >>> print(f"СКО единицы веса: {result['adjustment']['sigma0']:.6f}")
        """
        self.logger.info("=" * 80)
        self.logger.info("НАЧАЛО ОБРАБОТКИ СВОБОДНОЙ СЕТИ")
        self.logger.info("=" * 80)
        
        # Этап 1: Предварительная обработка
        preprocessing_result = self.preprocessing.run_all_stages(
            raw_data={'observations': field_observations, 'points': initial_approximate_points},
            config=self.config.get('preprocessing', {})
        )
        
        processed_observations = preprocessing_result.get(
            'corrected_observations', 
            field_observations
        )
        
        # Этап 2: Построение матрицы коэффициентов
        self.logger.info("\n[ЭТАП 2] Построение матрицы коэффициентов")
        
        A, L, validation = self.equations_builder.build_adjustment_matrix(
            observations=processed_observations,
            points=initial_approximate_points,
            fixed_points=[]  # Нет исходных пунктов
        )
        
        self.logger.info(f"  ✓ Матрица А: {A.shape[0]}×{A.shape[1]}")
        self.logger.info(f"  ✓ Статус валидации: {validation['status']}")
        self.logger.info(f"  → {validation['message']}")
        
        # Этап 3: Формирование весовой матрицы
        self.logger.info("\n[ЭТАП 3] Формирование весовой матрицы")
        
        weight_builder = WeightBuilder(self.instrument_library)
        P = weight_builder.build_weight_matrix(processed_observations, initial_approximate_points)
        
        self.logger.info(f"  ✓ Весовая матрица P: {P.shape[0]}×{P.shape[1]}")
        
        # Этап 4: Свободное уравнивание с минимальными ограничениями
        self.logger.info("\n[ЭТАП 4] Свободное уравнивание")
        
        from .free_network import FreeNetworkAdjustment
        
        # Определение размерности сети
        has_heights = any(p.h is not None for p in initial_approximate_points.values())
        dimension = '3d' if has_heights else '2d'
        
        free_adjustment = FreeNetworkAdjustment(dimension=dimension)
        
        # Получение начальных координат в виде вектора
        initial_coords = []
        for point in sorted(initial_approximate_points.values(), key=lambda p: p.point_id):
            initial_coords.extend([point.x, point.y])
            if point.h is not None:
                initial_coords.append(point.h)
        
        initial_coords_array = np.array(initial_coords, dtype=np.float64)
        
        result = free_adjustment.adjust_free_network(
            A, L, initial_coords_array
        )
        
        self.logger.info(f"\nСвободное уравнивание завершено:")
        self.logger.info(f"  ✓ СКО единицы веса: {result['sigma0']:.6f}")
        self.logger.info(f"  ✓ Размерность: {result['dimension']}")
        
        return {
            'adjustment': result,
            'preprocessing': preprocessing_result,
            'matrices': {'A': A, 'L': L, 'P': P}
        }
    
    def update_instrument_library(self, instrument_name: str, **kwargs):
        """
        Добавление или обновление прибора в библиотеке.
        
        Параметры:
        -----------
        instrument_name : str
            Название прибора
        **kwargs : dict
            Параметры прибора:
            - angular_accuracy: точность угловых измерений (секунды)
            - distance_accuracy_const: постоянная составляющая СКО расстояний (мм)
            - distance_accuracy_ppm: коэффициент ppm (мм/км)
            - centering_error: ошибка центрирования (мм)
            - target_centering_error: ошибка центрирования цели (мм)
            - double_run_error_per_km: СКО нивелирного хода на 1 км (мм)
        """
        try:
            self.instrument_library[instrument_name] = Instrument(**kwargs)
            self.logger.info(f"Прибор {instrument_name} добавлен в библиотеку")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении прибора {instrument_name}: {e}")
            raise
    
    def get_processing_summary(self, result: Dict[str, Any]) -> str:
        """
        Формирование текстовой сводки результатов обработки.
        
        Параметры:
        -----------
        result : Dict[str, Any]
            Результаты обработки
        
        Возвращает:
        ------------
        summary : str
            Текстовая сводка
        """
        lines = []
        lines.append("=" * 80)
        lines.append("СВОДКА РЕЗУЛЬТАТОВ ОБРАБОТКИ")
        lines.append("=" * 80)
        
        # Статистика
        stats = result.get('statistics', {})
        lines.append("\nСТАТИСТИКА СЕТИ:")
        lines.append(f"  Число измерений: {stats.get('num_observations', 'N/A')}")
        lines.append(f"  Число пунктов: {stats.get('num_points', 'N/A')}")
        lines.append(f"  Число исходных пунктов: {stats.get('num_fixed_points', 'N/A')}")
        lines.append(f"  Число неизвестных: {stats.get('num_unknowns', 'N/A')}")
        lines.append(f"  Избыточность: {stats.get('redundancy', 'N/A')}")
        
        # Результаты уравнивания
        adj = result.get('adjustment', {})
        lines.append("\nРЕЗУЛЬТАТЫ УРАВНИВАНИЯ:")
        lines.append(f"  СКО единицы веса: {adj.get('sigma0', 'N/A'):.6f}")
        lines.append(f"  Число итераций: {adj.get('iterations', 'N/A')}")
        
        # Надёжность
        rel = result.get('reliability', {})
        if 'avg_internal_reliability' in rel:
            lines.append("\nНАДЁЖНОСТЬ СЕТИ:")
            lines.append(
                f"  Средняя внутренняя надёжность: "
                f"{rel.get('avg_internal_reliability', 'N/A'):.4f}"
            )
        
        # Грубые ошибки
        ge = result.get('gross_errors', {})
        if 'error' not in ge:
            lines.append("\nГРУБЫЕ ОШИБКИ:")
            for method, errors in ge.items():
                if isinstance(errors, (list, np.ndarray)) and len(errors) > 0:
                    lines.append(f"  {method}: {len(errors)} подозрительных измерений")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
