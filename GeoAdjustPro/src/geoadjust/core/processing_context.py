# src/geoadjust/core/processing_context.py
"""Единый объект-контекст для конвейера обработки"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("geoadjust.context")

@dataclass
class ProcessingContext:
    """
    Единый контейнер состояния конвейера обработки.
    Заменяет передачу параметров по цепочке функций и гарантирует сквозное логирование.
    """
    observations: List[Any] = field(default_factory=list)
    points: Dict[str, Any] = field(default_factory=dict)
    fixed_points: Dict[str, float] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    logs: List[Dict[str, Any]] = field(default_factory=list)
    matrices: Dict[str, Any] = field(default_factory=dict)
    validation_report: Dict[str, Any] = field(default_factory=dict)

    status: str = "INIT"
    start_time: datetime = field(default_factory=datetime.now)

    def add_log(self, level: str, stage: str, message: str, details: Optional[Dict] = None):
        """Добавляет структурированную запись в журнал и в стандартный логгер."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "stage": stage,
            "message": message,
            "details": details or {}
        }
        self.logs.append(entry)

        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[{stage}] {message}")

    def set_matrices(self, A=None, P=None, L=None, validation: Optional[Dict] = None):
        """Сохраняет собранные матрицы и отчёт валидации."""
        self.matrices.update({
            "A": A, "P": P, "L": L,
            "built_at": datetime.now().isoformat()
        })
        if validation:
            self.validation_report = validation
            self.add_log("INFO", "MATRIX_ASSEMBLY", "Матрицы собраны и провалидированы", {
                "A_shape": A.shape if A is not None else None,
                "L_len": len(L) if L is not None else 0,
                "P_shape": P.shape if hasattr(P, 'shape') else None,
                "validation_status": validation.get("status")
            })

    def get_pipeline_report(self) -> Dict:
        """Возвращает сводку выполнения конвейера."""
        return {
            "status": self.status,
            "duration_sec": (datetime.now() - self.start_time).total_seconds(),
            "total_logs": len(self.logs),
            "matrices_ready": all(k in self.matrices for k in ("A", "P", "L")),
            "validation": self.validation_report,
            "warnings": [l for l in self.logs if l["level"] == "WARNING"],
            "errors": [l for l in self.logs if l["level"] == "ERROR"]
        }
