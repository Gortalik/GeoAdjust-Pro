# src/geoadjust/processing_pipeline.py
"""Единый конвейер обработки: предобработка → сборка A,P,L → валидация"""
import logging
from typing import Optional
from datetime import datetime
import numpy as np
import scipy.sparse as sparse

from geoadjust.core.processing_context import ProcessingContext
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weights import InstrumentSpec, build_weight_matrix, ObsType

logger = logging.getLogger("geoadjust.pipeline")

class ProcessingPipeline:
    """
    Полный конвейер: Предобработка → Сборка A, P, L → Валидация → Готовность к уравниванию.
    Все шаги логируются, данные передаются только через ProcessingContext.
    """
    def __init__(self, spec: InstrumentSpec = None):
        self.spec = spec or InstrumentSpec(class_code="4")
        self.equations_builder = EquationsBuilder(spec=self.spec)

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
            
            # 4. Финальная валидация системы
            ctx = self._validate_final_system(ctx)
            
            if ctx.status == "READY":
                ctx.add_log("INFO", "PIPELINE", "Конвейер завершён успешно. Система готова к уравниванию.")
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
        """Финальная проверка размерностей и ранга системы уравнений."""
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

        # Проверка ранга нормальной матрицы N = A^T P A
        try:
            N = (A.T @ P @ A).toarray()
            rank = np.linalg.matrix_rank(N, tol=1e-10)
            defect = N.shape[1] - rank
            cond = np.linalg.cond(N) if rank == N.shape[1] else float('inf')

            ctx.validation_report.update({
                "rank": f"{rank}/{N.shape[1]}",
                "defect": defect,
                "condition_number": f"{cond:.2e}"
            })
            
            if defect > 3:
                ctx.status = "RANK_DEFICIENT"
                ctx.add_log("WARNING", "VALIDATION", f"Критический дефект ранга: {defect}. Сеть не жёстко закреплена.")
            elif cond > 1e12:
                ctx.status = "POORLY_CONDITIONED"
                ctx.add_log("WARNING", "VALIDATION", f"Плохая обусловленность: cond={cond:.2e}. Возможна неустойчивость решения.")
            else:
                ctx.status = "READY"
                ctx.add_log("INFO", "VALIDATION", "Система уравнений валидна. Готово к уравниванию.")
        except Exception as e:
            ctx.status = "VALIDATION_ERROR"
            ctx.add_log("ERROR", "VALIDATION", f"Ошибка валидации: {str(e)}")
            
        return ctx
