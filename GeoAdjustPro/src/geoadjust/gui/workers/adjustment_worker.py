"""Воркер уравнивания для выполнения в фоне PyQt5"""
import traceback

from loguru import logger

from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.weights import InstrumentSpec

from .base_worker import BaseWorker


class AdjustmentWorker(BaseWorker):
    """
    Фоновый воркер для уравнивания сети.
    
    Выполняет тяжёлые вычисления в отдельном потоке,
    отправляя прогресс и результаты через сигналы Qt.
    """

    def __init__(
        self,
        engine: AdjustmentEngine,
        observations: list,
        fixed_points: dict,
        spec: InstrumentSpec = None
    ):
        super().__init__()
        self.engine = engine
        self.observations = observations
        self.fixed_points = fixed_points
        self.spec = spec or engine.spec

    def _do_work(self):
        """Выполнение уравнивания"""
        try:
            self.progress.emit(5, "Подготовка уравнений погрешностей...")
            self.log_message.emit("🔹 Запуск математического ядра...")

            # Вызов ядра
            result = self.engine.adjust_heights(
                self.observations,
                self.fixed_points,
                max_iter=10,
                tol=1e-5,
                detect_gross_errors=True,
                compute_covariance=True
            )

            self.progress.emit(85, "Расчёт ковариаций и эллипсов...")
            self.log_message.emit("✅ Уравновешивание завершено.")

            # Формирование результата для UI
            self.finished.emit({
                "corrections": result.corrections.tolist(),
                "residuals": result.residuals.tolist(),
                "sigma_0": result.sigma_0,
                "iterations": result.iterations,
                "status": result.status,
                "adjusted_heights": result.adjusted_heights,
                "diagnostics": result.diagnostics,
            })

        except Exception as e:
            logger.error(f"Критическая ошибка воркера:\n{traceback.format_exc()}")
            self.error.emit(f"Не удалось выполнить уравнивание: {str(e)}")

        finally:
            self.progress.emit(100, "Готово")
