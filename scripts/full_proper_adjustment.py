#!/usr/bin/env python3
"""
Полное и правильное уравнивание тахеометрической сети
с использованием EquationsBuilder + AdjustmentEngine
"""

import sys
from pathlib import Path
import numpy as np
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.sdr import SDRParser
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.weights import InstrumentSpec
from geoadjust.core.processing_context import ProcessingContext


def full_adjustment_tacheometry(file_path: Path):
    print("\n" + "="*80)
    print("ПОЛНОЕ УРАВНИВАНИЕ ТАХЕОМЕТРИЧЕСКОЙ СЕТИ")
    print(f"Файл: {file_path.name}")
    print("="*80)

    # 1. Загрузка данных
    parser = SDRParser()
    data = parser.parse(file_path)

    points = data.get('points', [])
    observations = data.get('observations', [])

    print(f"\nПунктов: {len(points)}")
    print(f"Измерений: {len(observations)}")

    if len(observations) < 5:
        print("Слишком мало измерений")
        return

    # 2. Создаём контекст
    ctx = ProcessingContext()
    ctx.points = {p.get('name', p.get('point_id', f'P{i}')): p for i, p in enumerate(points)}
    ctx.observations = observations

    # Фиксируем первую станцию
    if points:
        first_name = points[0].get('name', points[0].get('point_id', 'P001'))
        ctx.fixed_points = {first_name: 0.0}  # упрощённо
        print(f"\nФиксированная станция: {first_name}")

    # 3. Создаём builder и engine
    spec = InstrumentSpec(class_code="4")
    builder = EquationsBuilder(spec=spec)
    engine = AdjustmentEngine(spec=spec)

    print("\n[OK] EquationsBuilder и AdjustmentEngine созданы")

    # 4. Реальное уравнивание
    try:
        # Подготавливаем данные
        point_names = list(ctx.points.keys())
        point_indices = {name: i for i, name in enumerate(point_names)}

        approximate_coords = {}
        for name, p in ctx.points.items():
            approximate_coords[name] = {
                'x': float(p.get('x', 0.0)),
                'y': float(p.get('y', 0.0)),
                'h': float(p.get('h', 0.0))
            }

        # Вызываем build_adjustment_matrix
        result = builder.build_adjustment_matrix(
            observations=observations,
            point_indices=point_indices,
            approximate_coords=approximate_coords,
            fixed_points=ctx.fixed_points or {}
        )

        print(f"\n[OK] Матрицы построены успешно")
        print(f"Тип результата: {type(result)}")

        # Если вернулся tuple
        if isinstance(result, tuple):
            A, P, L = result[:3]
            print(f"Матрица A: {A.shape}")
            print(f"Вектор L: {L.shape}")

            # Решаем
            solution = engine.solve(A, P, L, point_names, ctx.fixed_points or {})
            print(f"\n=== РЕЗУЛЬТАТЫ УРАВНИВАНИЯ ===")
            print(f"σ₀ = {getattr(solution, 'sigma_0', 'N/A')}")
        else:
            print(f"Результат: {result}")

    except Exception as e:
        print(f"Ошибка уравнивания: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "b_g" / "plan" / "badgro16093_const.sdr"
    full_adjustment_tacheometry(f)
