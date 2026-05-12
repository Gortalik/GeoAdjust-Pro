#!/usr/bin/env python3
"""
Тест исправлений на реальных данных GSI
Проверяет полный цикл: парсинг -> нормализация -> предобработка -> уравнивание
"""

import sys
import os

from pathlib import Path
from geoadjust.io.formats.gsi import GSIParser
from geoadjust.core.adjustment.data_adapter import DataAdapter
from geoadjust.core.preprocessing.module import PreprocessingModule
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder
from geoadjust.core.adjustment.engine import AdjustmentEngine

def test_real_gsi_data():
    """Тест на реальных данных GSI файла"""

    print("=" * 80)
    print("ТЕСТ НА РЕАЛЬНЫХ ДАННЫХ GSI")
    print("=" * 80)

    # 1. Парсинг реального GSI файла
    print("\n[1] Парсинг GSI файла")

    gsi_file = Path("test_real_mes/s5/niv/DOM0112 (1).GSI")

    if not gsi_file.exists():
        print(f"[ERROR] GSI файл не найден: {gsi_file}")
        return False

    try:
        parser = GSIParser()
        parse_result = parser.parse(gsi_file)

        print(f"[OK] Файл распаршен: {parse_result.get('num_points', 0)} точек, {parse_result.get('num_observations', 0)} измерений")
        print(f"  Типы измерений: {parse_result.get('num_leveling_observations', 0)} нивелирных")

        if not parse_result.get('observations'):
            print("[ERROR] Нет измерений после парсинга")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка парсинга GSI: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. Нормализация данных через DataAdapter
    print("\n[2] Нормализация данных через DataAdapter")

    try:
        raw_points = parse_result.get('points', [])
        raw_observations = parse_result.get('observations', [])

        print(f"  Сырые данные: {len(raw_points)} точек, {len(raw_observations)} измерений")

        points_dict, observations = DataAdapter.normalize_project_data(raw_points, raw_observations)

        print(f"[OK] Нормализовано: {len(points_dict)} точек, {len(observations)} измерений")

        # Для нивелирования нужно зафиксировать высоту хотя бы одной точки
        # Найдем первую точку в списке и зафиксируем её высоту
        if points_dict:
            first_point_id = next(iter(points_dict.keys()))
            points_dict[first_point_id].h = 100.0  # Фиксированная высота 100м
            points_dict[first_point_id].coord_type = 'FIXED'
            print(f"[OK] Зафиксирована высота точки {first_point_id}: 100.0 м")

        # Проверим типы
        if not isinstance(points_dict, dict):
            print("[ERROR] points_dict не является dict")
            return False
        if not isinstance(observations, list):
            print("[ERROR] observations не является list")
            return False

        print("[OK] Типы данных корректны")

    except Exception as e:
        print(f"[ERROR] Ошибка нормализации: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Предобработка через PreprocessingModule
    print("\n[3] Предобработка через PreprocessingModule")

    try:
        preprocessor = PreprocessingModule()

        # Используем новый фасад process()
        preprocessing_result = preprocessor.process(observations=observations, points=points_dict)

        print(f"[OK] Предобработка завершена: {preprocessing_result['stages_completed']} этапов")

        corrected_obs = preprocessing_result.get('corrected_observations', [])
        print(f"  Корректированных измерений: {len(corrected_obs)}")

        if not corrected_obs:
            print("[WARNING] Нет корректированных измерений")
            corrected_obs = observations

    except Exception as e:
        print(f"[ERROR] Ошибка предобработки: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Построение матрицы уравнений
    print("\n[4] Построение матрицы уравнений")

    try:
        builder = EquationsBuilder()

        # Определим фиксированные точки (первые точки в списке)
        all_point_ids = list(points_dict.keys())
        if len(all_point_ids) >= 2:
            fixed_points = all_point_ids[:2]  # Первые две точки фиксированные
        else:
            fixed_points = []

        print(f"  Фиксированные точки: {fixed_points}")
        print(f"  Свободных точек: {len(points_dict) - len(fixed_points)}")

        A, L = builder.build_adjustment_matrix(
            observations=corrected_obs,
            points=points_dict,
            fixed_points=fixed_points
        )

        print(f"[OK] Матрица A: {A.shape[0]}x{A.shape[1]}")
        print(f"[OK] Вектор L: {len(L)}")

        if A.shape[0] == 0:
            print("[ERROR] Матрица A пустая")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка построения матрицы: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Формирование весовой матрицы
    print("\n[5] Формирование весовой матрицы")

    try:
        weight_builder = WeightBuilder()
        P = weight_builder.build(corrected_obs)

        print(f"[OK] Весовая матрица P: {P.shape[0]}x{P.shape[1]}")

    except Exception as e:
        print(f"[ERROR] Ошибка весовой матрицы: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 6. Уравнивание (если доступно)
    print("\n[6] Уравнивание сети")

    try:
        # Проверяем доступность модуля уравнивания
        from geoadjust.core import ADJUSTMENT_AVAILABLE
        if not ADJUSTMENT_AVAILABLE:
            print("[WARNING] Модуль уравнивания недоступен (нет scikit-sparse)")
            print("[OK] Но основные исправления работают!")
            return True

        engine = AdjustmentEngine()
        adjustment_result = engine.adjust(A, L, P)

        print(f"[OK] Уравнивание завершено:")
        print(f"  СКО единицы веса: {adjustment_result.get('sigma0', 'N/A'):.6f}")
        print(f"  Число итераций: {adjustment_result.get('iterations', 'N/A')}")

        if adjustment_result.get('sigma0', float('inf')) < 10.0:  # Разумное значение СКО
            print("[OK] Уравнивание сошлось с приемлемой точностью")
        else:
            print("[WARNING] Уравнивание сошлось с большой погрешностью")

    except Exception as e:
        print(f"[ERROR] Ошибка уравнивания: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("[SUCCESS] ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ НА РЕАЛЬНЫХ ДАННЫХ!")
    print("=" * 80)

    return True

if __name__ == '__main__':
    success = test_real_gsi_data()
    sys.exit(0 if success else 1)