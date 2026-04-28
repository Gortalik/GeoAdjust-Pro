# src/geoadjust/core/processing/pipeline.py
import numpy as np
from scipy import sparse
from typing import List, Dict, Any, Callable
from geoadjust.core.network.models import InstrumentSetup, Observation
import logging

logger = logging.getLogger(__name__)

class ProcessingPipeline:
    def __init__(self, config: Dict):
        self.config = config
        self.progress_callback: Callable = None

    def set_progress_callback(self, callback: Callable):
        self.progress_callback = callback

    def _emit_progress(self, stage: str, percent: int, message: str, warnings: List[str] = None):
        if self.progress_callback:
            self.progress_callback(stage, percent, message, warnings or [])

    def process_network(self, setups: List[InstrumentSetup]) -> Dict[str, Any]:
        self._emit_progress("INIT", 0, "Инициализация обработки...")
        
        # ЭТАП 1: Индивидуальная обработка установок (0-40%)
        stage_warnings = []
        for i, setup in enumerate(setups):
            percent = int((i / len(setups)) * 40)
            self._emit_progress("STATION", percent, f"Обработка установки {setup.setup_id}...")
            
            closure = self._check_closure(setup)
            if closure and closure > 5.0:
                setup.warnings.append(f"Замыкание горизонта {closure:.2f}\" > 5.0\"")
                stage_warnings.append(setup.warnings[-1])
                
            setup.is_processed = True
            
        # ЭТАП 2: Построение глобальной системы (40-70%)
        self._emit_progress("MATRIX", 40, "Формирование матрицы коэффициентов...")
        A, L, P = self._build_matrices(setups)
        
        # ЭТАП 3: Сетевое уравнивание (70-100%)
        self._emit_progress("ADJUST", 70, "Запуск уравнивания сети...")
        try:
            from geoadjust.core.adjustment.engine import AdjustmentEngine
            engine = AdjustmentEngine()
            result = engine.adjust(A, L, P)
            self._emit_progress("DONE", 100, "Уравнивание завершено", stage_warnings)
            return {'success': True, 'result': result, 'warnings': stage_warnings}
        except Exception as e:
            self._emit_progress("ERROR", 100, f"Ошибка уравнивания: {e}")
            return {'success': False, 'error': str(e), 'warnings': stage_warnings}

    def _check_closure(self, setup: InstrumentSetup) -> float:
        dirs = [o for o in setup.observations if o.obs_type == 'direction']
        if len(dirs) < 2: return 0.0
        # Упрощённая проверка замыкания
        return abs(dirs[-1].value - dirs[0].value - 360.0)

    def _build_matrices(self, setups: List[InstrumentSetup]):
        # Здесь должна быть полная реализация из EquationsBuilder и WeightBuilder
        # Для краткости приведена заглушка, совместимая с вашим кодом
        n, u = 10, 6  # Замените на реальный расчёт
        A = sparse.random(n, u, density=0.2, format='csr')
        L = np.zeros(n)
        P = sparse.eye(n)
        return A, L, P