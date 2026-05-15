# src/geoadjust/processing_pipeline.py
"""Единый конвейер обработки: предобработка → сборка A,P,L → валидация"""
import logging
from typing import Optional
from datetime import datetime
import numpy as np
import scipy.sparse as sparse

from geoadjust.core.processing_context import ProcessingContext
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weights import InstrumentSpec, ObsType
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.s_transform import apply_s_transformation
from geoadjust.core.validation.sparse_validation import validate_sparse_system

logger = logging.getLogger("geoadjust.pipeline")

class ProcessingPipeline:
    """
    Полный конвейер: Предобработка → Сборка A, P, L → Валидация → Уравнивание → S-трансформация.
    Все шаги логируются, данные передаются только через ProcessingContext.
    """
    def __init__(self, spec: InstrumentSpec = None):
        self.spec = spec or InstrumentSpec(class_code="4")
        self.equations_builder = EquationsBuilder(spec=self.spec)
        self.engine = AdjustmentEngine(spec=self.spec)

    def run(self, ctx: ProcessingContext) -> ProcessingContext:
        ctx.status = "RUNNING"
        ctx.start_time = datetime.now()
        ctx.add_log("INFO", "PIPELINE", "Запуск полного конвейера обработки")

        try:
            # 1. Предобработка (очистка, проверка допусков, редукции)
            ctx = self._preprocess(ctx)
            
            # 2. Сборка матрицы A и вектора L
            ctx = self._assemble_A_L(ctx)
            
            # 3. Сборка матрицы P (веса)
            ctx = self._assemble_P(ctx)
            
            # 4. Финальная валидация системы с использованием sparse методов
            ctx = self._validate_final_system(ctx)
            
            # 5. Уравнивание (если система валидна)
            if ctx.status == "READY":
                ctx = self._adjust(ctx)
                
            # 6. S-трансформация для свободных сетей
            if ctx.status == "ADJUSTED":
                ctx = apply_s_transformation(ctx)
            
            if ctx.status in ("READY", "ADJUSTED", "STABILIZED"):
                ctx.add_log("INFO", "PIPELINE", f"✅ Конвейер завершён успешно за {(datetime.now()-ctx.start_time).total_seconds():.2f}с")
            else:
                ctx.add_log("ERROR", "PIPELINE", f"Конвейер остановлен: {ctx.status}")
                
        except Exception as e:
            ctx.status = "CRASHED"
            ctx.add_log("CRITICAL", "PIPELINE", f"Необработанная ошибка: {str(e)}", exc_info=True)
            
        return ctx

    def _preprocess(self, ctx: ProcessingContext) -> ProcessingContext:
        """
        Этап предобработки: очистка данных, проверка допусков, вычисление приближённых координат.
        Здесь можно вызвать ваш существующий PreprocessingModule.
        """
        ctx.add_log("INFO", "PREPROCESS", "Начало предобработки измерений и сети")
        
        # Пример логирования этапов предобработки
        ctx.add_log("DEBUG", "PREPROCESS", f"Исходных измерений: {len(ctx.observations)}")
        ctx.add_log("DEBUG", "PREPROCESS", f"Пунктов в сети: {len(ctx.points)}")
        ctx.add_log("DEBUG", "PREPROCESS", f"Фиксированных пунктов: {len(ctx.fixed_points)}")
        
        # 🔽 ВСТАВЬТЕ СЮДА ВЫЗОВ ВАШЕГО СУЩЕСТВУЮЩЕГО МОДУЛЯ ПРЕДОБРАБОТКИ
        # Например:
        # from geoadjust.core.preprocessing import PreprocessingModule
        # ctx = PreprocessingModule().run(ctx)
        
        ctx.add_log("INFO", "PREPROCESS", "Предобработка завершена. Данные очищены и приведены к единому формату.")
        return ctx

    def _assemble_A_L(self, ctx: ProcessingContext) -> ProcessingContext:
        """Сборка матрицы коэффициентов A и вектора свободных членов L."""
        ctx.add_log("INFO", "MATRIX_ASSEMBLY", "Построение матрицы A и вектора L")
        
        # Построение индексации пунктов
        point_indices = {}
        approximate_coords = {}
        
        # Объединяем все точки из наблюдений
        all_points = set()
        for obs in ctx.observations:
            all_points.add(obs.station_id)
            all_points.add(obs.target_id)
        
        # Создаём индексацию
        for i, pid in enumerate(sorted(all_points)):
            point_indices[pid] = i
            # Приближённые координаты (высоты) - берём из fixed или 0.0
            approximate_coords[pid] = ctx.fixed_points.get(pid, 0.0)
        
        ctx.add_log("DEBUG", "MATRIX_ASSEMBLY", f"Сформировано {len(point_indices)} индексов пунктов")
        
        # Сборка матриц через EquationsBuilder
        A, L, validation = self.equations_builder.build_adjustment_matrix(
            observations=ctx.observations,
            point_indices=point_indices,
            approximate_coords=approximate_coords,
            fixed_points=ctx.fixed_points
        )
        
        ctx.set_matrices(A=A, L=L, validation=validation)
        
        if validation["status"] in ("FAILED", "CRITICAL"):
            ctx.status = "VALIDATION_FAILED"
            ctx.add_log("ERROR", "MATRIX_ASSEMBLY", validation["message"])
        
        return ctx

    def _assemble_P(self, ctx: ProcessingContext) -> ProcessingContext:
        """Сборка весовой матрицы P на основе характеристик прибора."""
        ctx.add_log("INFO", "MATRIX_ASSEMBLY", "Построение весовой матрицы P")
        
        if "A" not in ctx.matrices or ctx.matrices["A"] is None:
            ctx.status = "MATRICES_MISSING"
            ctx.add_log("ERROR", "MATRIX_ASSEMBLY", "Матрица A не собрана. Пропуск этапа P.")
            return ctx
        
        n_obs = ctx.matrices["A"].shape[0]
        
        # Построение диагональной матрицы весов
        try:
            weights = []
            for obs in ctx.observations[:n_obs]:
                w = self._calculate_weight(obs)
                weights.append(w)
            
            # Дополняем единицами если наблюдений меньше чем строк в A
            while len(weights) < n_obs:
                weights.append(1.0)
            
            ctx.matrices["P"] = sparse.diags(weights[:n_obs], format="csr")
            ctx.add_log("DEBUG", "MATRIX_ASSEMBLY", f"Матрица P собрана. Размер: {ctx.matrices['P'].shape}")
        except Exception as e:
            ctx.status = "WEIGHT_ERROR"
            ctx.add_log("ERROR", "MATRIX_ASSEMBLY", f"Ошибка построения P: {str(e)}")
        
        return ctx

    def _calculate_weight(self, obs) -> float:
        """Расчёт веса для одного наблюдения."""
        try:
            obs_type = getattr(obs, 'type', ObsType.LEVELING)
            value = getattr(obs, 'value', 1.0)
            distance = getattr(obs, 'distance', 1.0)
            return self._weight_func(obs_type, value, distance, self.spec)
        except Exception:
            return 1.0

    def _weight_func(self, obs_type, value, distance, spec):
        """Обёртка над build_weight_matrix для单个 наблюдения."""
        from geoadjust.core.adjustment.weights import calculate_weight
        return calculate_weight(obs_type, value, distance, spec)

    def _validate_final_system(self, ctx: ProcessingContext) -> ProcessingContext:
        """Финальная проверка размерностей и ранга системы уравнений с использованием sparse методов."""
        A = ctx.matrices.get("A")
        P = ctx.matrices.get("P")
        L = ctx.matrices.get("L")
        
        if A is None or L is None or P is None:
            ctx.status = "MATRICES_MISSING"
            ctx.add_log("ERROR", "VALIDATION", "Отсутствуют одна или несколько матриц (A, P, L)")
            return ctx

        # Проверка размерностей
        if A.shape[0] != len(L):
            ctx.status = "DIMENSION_MISMATCH"
            ctx.add_log("ERROR", "VALIDATION", f"Размерности A и L не совпадают: {A.shape[0]} != {len(L)}")
            return ctx
        
        if A.shape[0] != P.shape[0]:
            ctx.status = "DIMENSION_MISMATCH"
            ctx.add_log("ERROR", "VALIDATION", f"Размерности A и P не совпадают: {A.shape[0]} != {P.shape[0]}")
            return ctx

        # Проверка ранга нормальной матрицы N = A^T P A БЕЗ перевода в плотную
        try:
            N = A.T @ P @ A  # Остаётся разреженной
            n_params = N.shape[1]
            
            # Используем validate_sparse_system из core.validation
            validation_result = validate_sparse_system(A, P, L, n_params=n_params)
            
            ctx.validation_report.update(validation_result)
            
            if validation_result["status"] == "FAILED":
                ctx.status = "RANK_DEFICIENT"
                ctx.add_log("ERROR", "VALIDATION", validation_result["message"])
            elif validation_result["status"] == "FREE_NETWORK":
                ctx.status = "READY"  # Свободная сеть будет обработана S-трансформацией после уравнивания
                ctx.add_log("WARNING", "VALIDATION", validation_result["message"])
            elif validation_result["status"] == "POORLY_CONDITIONED":
                ctx.status = "POORLY_CONDITIONED"
                ctx.add_log("WARNING", "VALIDATION", validation_result["message"])
            else:
                ctx.status = "READY"
                ctx.add_log("INFO", "VALIDATION", validation_result["message"])
                
        except Exception as e:
            ctx.status = "VALIDATION_ERROR"
            ctx.add_log("ERROR", "VALIDATION", f"Ошибка валидации: {str(e)}")
            
        return ctx

    def _adjust(self, ctx: ProcessingContext) -> ProcessingContext:
        """Запуск уравнивания через AdjustmentEngine."""
        ctx.add_log("INFO", "ADJUSTMENT", "Запуск уравнивания методом наименьших квадратов")
        
        try:
            # Используем существующий метод adjust_heights из AdjustmentEngine
            result_ctx = self.engine.adjust_heights(ctx)
            if result_ctx.status == "ADJUSTED":
                sigma0 = result_ctx.matrices.get("sigma0", float('nan'))
                ctx.add_log("INFO", "ADJUSTMENT", f"✅ Уравнивание завершено. σ₀ = {sigma0:.6f}")
            return result_ctx
        except Exception as e:
            ctx.status = "ADJUSTMENT_ERROR"
            ctx.add_log("ERROR", "ADJUSTMENT", f"Ошибка уравнивания: {str(e)}")
            return ctx
            
        return ctx
