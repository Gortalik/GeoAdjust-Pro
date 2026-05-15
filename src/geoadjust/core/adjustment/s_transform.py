# src/geoadjust/core/adjustment/s_transform.py
"""S-преобразование для стабилизации свободных сетей (дефект ранга 1–3)."""
import numpy as np
import logging
from typing import Dict

logger = logging.getLogger("geoadjust.s_transform")

def apply_s_transformation(ctx) -> "ProcessingContext":
    """
    Применяет S-преобразование к результатам уравнивания свободной сети.
    Устраняет дефект ранга 3 (2 переноса + 1 поворот в 2D).
    """
    if ctx.status != "ADJUSTED":
        ctx.add_log("WARNING", "S_TRANSFORM", "Пропущено: сеть не уравнена")
        return ctx

    defect = ctx.validation_report.get("defect", 0)
    if defect == 0:
        ctx.add_log("INFO", "S_TRANSFORM", "Пропущено: сеть жёстко закреплена")
        return ctx
    if defect > 3:
        ctx.add_log("WARNING", "S_TRANSFORM", "Пропущено: критический дефект ранга (>3)")
        return ctx

    ctx.add_log("INFO", "S_TRANSFORM", f"Применение S-преобразования (дефект: {defect})")
    
    try:
        # Собираем координаты до и после уравнивания
        pts_before = {}
        pts_after = {}
        for pid, pt in ctx.points.items():
            if hasattr(pt, '_x_initial') and hasattr(pt, '_y_initial'):
                pts_before[pid] = (pt._x_initial, pt._y_initial)
                pts_after[pid] = (pt.x, pt.y)
            elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                pts_after[pid] = (pt.x, pt.y)
        
        if not pts_before:
            # Если нет начальных координат, используем текущие как базу
            pts_before = pts_after.copy()
        
        if not pts_after:
            ctx.add_log("WARNING", "S_TRANSFORM", "Нет координат для трансформации")
            return ctx

        # Центроиды
        cx_b = np.mean([p[0] for p in pts_before.values()])
        cy_b = np.mean([p[1] for p in pts_before.values()])
        cx_a = np.mean([p[0] for p in pts_after.values()])
        cy_a = np.mean([p[1] for p in pts_after.values()])

        # Параметры Гельмерта (2D: сдвиг + поворот)
        dx_t = cx_b - cx_a
        dy_t = cy_b - cy_a
        
        # Оценка поворота через центрированные координаты
        S_xx = sum((p[0]-cx_a)*(p[0]-cx_b) + (p[1]-cy_a)*(p[1]-cy_b) for p in pts_before.values())
        S_xy = sum((p[1]-cy_a)*(p[0]-cx_b) - (p[0]-cx_a)*(p[1]-cy_b) for p in pts_before.values())
        S_rr = sum((p[0]-cx_a)**2 + (p[1]-cy_a)**2 for p in pts_after.values())
        
        if S_rr < 1e-10:
            logger.warning("Центроид вырожден. Применяется только сдвиг.")
            theta, scale = 0.0, 1.0
        else:
            theta = np.arctan2(S_xy, S_xx)
            scale = np.hypot(S_xx, S_xy) / S_rr if S_xx**2 + S_xy**2 > 0 else 1.0

        # Применяем трансформацию к уравненным координатам
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        for pid, pt in ctx.points.items():
            if hasattr(pt, 'x') and hasattr(pt, 'y'):
                x, y = pt.x - cx_a, pt.y - cy_a
                x_new = scale * (cos_t * x - sin_t * y) + cx_b + dx_t
                y_new = scale * (sin_t * x + cos_t * y) + cy_b + dy_t
                pt.x, pt.y = x_new, y_new

        ctx.matrices["S_transform"] = {
            "translation": (dx_t, dy_t),
            "rotation_rad": float(theta),
            "scale": float(scale)
        }
        ctx.status = "STABILIZED"
        ctx.add_log("INFO", "S_TRANSFORM", 
            f"✅ Сеть стабилизирована. Δ=({dx_t:.4f},{dy_t:.4f})м, θ={np.degrees(theta):.4f}°, k={scale:.8f}")
    except Exception as e:
        ctx.add_log("ERROR", "S_TRANSFORM", f"Ошибка S-преобразования: {e}", exc_info=True)
        
    return ctx
