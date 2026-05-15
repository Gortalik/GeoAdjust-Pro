"""
Модуль единого контекста обработки данных GeoAdjust-Pro

Этот модуль предоставляет ProcessingContext - единый объект для передачи
данных, логов, матриц и статуса между этапами конвейера обработки.

Автор: GeoAdjust-Pro Team
Версия: 2.1
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger("geoadjust.context")


@dataclass
class ProcessingContext:
    """
    Единый контейнер состояния конвейера обработки.
    
    Заменяет передачу параметров по цепочке функций и гарантирует:
    - Сквозное логирование всех этапов
    - Безопасную передачу данных между модулями
    - Прозрачность предобработки и сборки матриц
    - Валидацию системы перед уравниванием
    
    Атрибуты:
    -----------
    observations : List[Any]
        Список измерений после предобработки
    points : Dict[str, Any]
        Словарь пунктов {point_id: NetworkPoint}
    fixed_points : List[str]
        Список идентификаторов исходных (твёрдых) пунктов
    config : Dict[str, Any]
        Конфигурация обработки
        
    logs : List[Dict[str, Any]]
        Структурированный журнал выполнения конвейера
    matrices : Dict[str, Any]
        Собранные матрицы A, P, L и метаданные
    validation_report : Dict[str, Any]
        Отчёт о валидации системы уравнений
        
    status : str
        Текущий статус конвейера (INIT, RUNNING, READY, FAILED, etc.)
    start_time : datetime
        Время начала выполнения конвейера
    """
    
    observations: List[Any] = field(default_factory=list)
    points: Dict[str, Any] = field(default_factory=dict)
    fixed_points: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    logs: List[Dict[str, Any]] = field(default_factory=list)
    matrices: Dict[str, Any] = field(default_factory=dict)
    validation_report: Dict[str, Any] = field(default_factory=dict)
    
    status: str = "INIT"
    start_time: datetime = field(default_factory=datetime.now)
    
    def add_log(self, level: str, stage: str, message: str, details: Optional[Dict] = None):
        """
        Добавляет структурированную запись в журнал и в стандартный логгер.
        
        Параметры:
        -----------
        level : str
            Уровень логирования (INFO, WARNING, ERROR, DEBUG, CRITICAL)
        stage : str
            Название этапа конвейера (PREPROCESS, MATRIX_ASSEMBLY, VALIDATION, etc.)
        message : str
            Текст сообщения
        details : Dict, optional
            Дополнительные данные (числа, идентификаторы, etc.)
        
        Пример:
        -------
        >>> ctx.add_log("INFO", "PREPROCESS", "Начало предобработки", 
        ...             {"observations": 142, "points": 25})
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "stage": stage,
            "message": message,
            "details": details or {}
        }
        self.logs.append(entry)
        
        # Формирование подробного сообщения для логгера
        log_msg = f"[{stage}] {message}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items() 
                                   if not isinstance(v, (dict, list)))
            if detail_str:
                log_msg += f" ({detail_str})"
        
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(log_msg)

    def set_matrices(self, A=None, P=None, L=None, validation: Optional[Dict] = None):
        """
        Сохраняет собранные матрицы и отчёт валидации.
        
        Параметры:
        -----------
        A : sparse.csr_matrix, optional
            Матрица коэффициентов уравнений поправок
        P : sparse.csr_matrix, optional
            Весовая матрица
        L : np.ndarray, optional
            Вектор свободных членов
        validation : Dict, optional
            Отчёт о валидации системы (статус, ранг, обусловленность)
        """
        self.matrices.update({
            "A": A,
            "P": P,
            "L": L,
            "built_at": datetime.now().isoformat()
        })
        
        if validation:
            self.validation_report = validation
            
            # Детальное логирование результатов валидации
            val_details = {
                "status": validation.get("status"),
            }
            if A is not None:
                val_details["A_shape"] = f"{A.shape[0]}×{A.shape[1]}"
            if L is not None:
                val_details["L_len"] = len(L)
            if hasattr(P, 'shape'):
                val_details["P_shape"] = f"{P.shape[0]}×{P.shape[1]}"
            
            self.add_log(
                "INFO", 
                "MATRIX_ASSEMBLY", 
                "Матрицы собраны и провалидированы",
                val_details
            )

    def get_pipeline_report(self) -> Dict:
        """
        Возвращает сводку выполнения конвейера.
        
        Возвращает:
        ------------
        report : Dict
            Словарь с полной информацией о выполнении:
            - status: итоговый статус
            - duration_sec: длительность выполнения
            - total_logs: число записей в журнале
            - matrices_ready: готовы ли матрицы к уравниванию
            - validation: отчёт валидации
            - warnings: список предупреждений
            - errors: список ошибок
        """
        return {
            "status": self.status,
            "duration_sec": (datetime.now() - self.start_time).total_seconds(),
            "total_logs": len(self.logs),
            "matrices_ready": all(k in self.matrices for k in ("A", "P", "L")),
            "validation": self.validation_report,
            "warnings": [l for l in self.logs if l["level"] == "WARNING"],
            "errors": [l for l in self.logs if l["level"] == "ERROR"]
        }
    
    def reset(self):
        """Сброс контекста к начальному состоянию"""
        self.logs.clear()
        self.matrices.clear()
        self.validation_report.clear()
        self.status = "INIT"
        self.start_time = datetime.now()
        self.add_log("INFO", "CONTEXT", "Контекст сброшен")
