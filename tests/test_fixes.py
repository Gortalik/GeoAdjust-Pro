#!/usr/bin/env python3
"""
Тест исправлений: минимальный тест с 2 точками + 1 измерением
Проверяет работу исправленных модулей
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GeoAdjustPro', 'src'))

from geoadjust.core.preprocessing.module import PreprocessingModule
from geoadjust.core.adjustment.data_adapter import DataAdapter
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.network.models import NetworkPoint, Observation

def test_minimal_pipeline():
    """Тест минимального конвейера с исправлениями"""

    print("=" * 60)
    print("ТЕСТ ИСПРАВЛЕНИЙ: МИНИМАЛЬНЫЙ КОНВЕЙЕР")
    print("=" * 60)

    # 1. Создаём тестовые данные
    print("\n[1] Создание тестовых данных")

    # Две точки
    raw_points = [
        {'point_id': 'P1', 'x': 100.0, 'y': 200.0, 'h': 50.0, 'point_type': 'FIXED'},
        {'point_id': 'P2', 'x': 150.0, 'y': 250.0, 'h': 50.5, 'point_type': 'FREE'}
    ]

    # Одно измерение превышения
    raw_observations = [
        {'obs_id': 'OBS1', 'obs_type': 'height_diff', 'from_point_id': 'P1', 'to_point_id': 'P2', 'value': 0.5, 'from_setup_id': 'SETUP1'}
    ]

    print(f"Точки: {len(raw_points)}")
    print(f"Измерения: {len(raw_observations)}")

    # 2. Нормализация данных через DataAdapter
    print("\n[2] Нормализация данных через DataAdapter")

    try:
        points_dict, observations = DataAdapter.normalize_project_data(raw_points, raw_observations)
        print(f"[OK] Нормализовано: {len(points_dict)} точек, {len(observations)} измерений")

        # Проверяем типы
        assert isinstance(points_dict, dict), "points должен быть dict"
        assert isinstance(observations, list), "observations должен быть list"
        assert all(isinstance(obs, Observation) for obs in observations), "Все измерения должны быть Observation"

        print("[OK] Типы данных корректны")

    except Exception as e:
        print(f"[ERROR] Ошибка нормализации: {e}")
        return False

    # 3. Предобработка через PreprocessingModule
    print("\n[3] Предобработка через PreprocessingModule")

    try:
        preprocessor = PreprocessingModule()

        # Тестируем новый фасад process()
        result = preprocessor.process(observations=observations, points=points_dict)

        print(f"[OK] Предобработка завершена: {result['stages_completed']} этапов")
        print(f"  Корректированных измерений: {len(result.get('corrected_observations', []))}")

        # Проверяем что process() работает как фасад
        result2 = preprocessor.run_all_stages(observations=observations, points=points_dict)
        assert result['stages_completed'] == result2['stages_completed'], "process() должен работать как фасад"

        print("[OK] Фасад process() работает корректно")

    except Exception as e:
        print(f"[ERROR] Ошибка предобработки: {e}")
        return False

    # 4. Построение матрицы уравнений
    print("\n[4] Построение матрицы уравнений")

    try:
        builder = EquationsBuilder()

        # Определяем фиксированные точки
        fixed_points = ['P1']

        A, L = builder.build_adjustment_matrix(
            observations=observations,
            points=points_dict,
            fixed_points=fixed_points
        )

        print(f"[OK] Матрица A: {A.shape[0]}x{A.shape[1]}")
        print(f"[OK] Вектор L: {len(L)}")

        # Проверяем размеры
        expected_rows = len(observations)  # 1 измерение
        expected_cols = (len(points_dict) - len(fixed_points)) * 3  # 1 свободная точка × 3 параметра (x,y,h)

        assert A.shape[0] == expected_rows, f"Ожидалось {expected_rows} строк, получено {A.shape[0]}"
        assert A.shape[1] == expected_cols, f"Ожидалось {expected_cols} столбцов, получено {A.shape[1]}"

        print("[OK] Размеры матриц корректны")

    except Exception as e:
        print(f"[ERROR] Ошибка построения матрицы: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ КОРРЕКТНО!")
    print("=" * 60)

    return True

if __name__ == '__main__':
    success = test_minimal_pipeline()
    sys.exit(0 if success else 1)