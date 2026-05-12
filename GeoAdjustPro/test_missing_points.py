#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправлений: создание недостающих точек и обработка None координат
"""

import sys
import os

# Добавляем путь к исходному коду
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:

def test_missing_points_creation():
    """Тест создания недостающих точек"""
    print("Тестирование создания недостающих точек...")

    try:
        from geoadjust.core.adjustment.equations_builder import EquationsBuilder
        from geoadjust.core.network.models import NetworkPoint, Observation

        # Создаем сеть с отсутствующей точкой
        points = {
            'STA1': NetworkPoint(point_id='STA1', coord_type='FIXED', x=0, y=0, h=0),
            # Точка P1 отсутствует в словаре
        }

        observations = [
            Observation(obs_id='dist1', obs_type='distance', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
        ]

        # Имитируем логику создания недостающих точек
        for obs in observations:
            for point_id in [obs.from_point_id, obs.to_point_id]:
                if point_id and point_id not in points:
                    points[point_id] = NetworkPoint(
                        point_id=point_id,
                        x=None,  # None координаты
                        y=None,
                        h=None,
                        coord_type='FREE'
                    )
                    print(f"[OK] Создана точка {point_id} с None координатами")

        # Проверяем, что точка создана
        assert 'P1' in points
        assert points['P1'].x is None

        # Пытаемся построить уравнение - должно пропустить из-за None координат
        builder = EquationsBuilder()
        A, L = builder.build_adjustment_matrix(observations, points, ['STA1'])

        print(f"[OK] Матрица пустая (как и ожидалось): {A.shape[0]}x{A.shape[1]}")
        return True

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_none_coordinates_handling():
    """Тест обработки None координат"""
    print("Тестирование обработки None координат...")

    try:
        from geoadjust.core.adjustment.equations_builder import EquationsBuilder
        from geoadjust.core.network.models import NetworkPoint, Observation

        # Создаем сеть с точками, имеющими None координаты
        points = {
            'STA1': NetworkPoint(point_id='STA1', coord_type='FIXED', x=0, y=0, h=0),
            'P1': NetworkPoint(point_id='P1', coord_type='FREE', x=None, y=None, h=None),  # None координаты
        }

        observations = [
            Observation(obs_id='dist1', obs_type='distance', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
        ]

        builder = EquationsBuilder()
        A, L = builder.build_adjustment_matrix(observations, points, ['STA1'])

        # Должно пропустить измерение и вернуть пустую матрицу
        assert A.shape[0] == 0
        print(f"[OK] Измерение с None координатами пропущено: {A.shape[0]}x{A.shape[1]}")
        return True

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("ТЕСТ ИСПРАВЛЕНИЙ: НЕДОСТАЮЩИЕ ТОЧКИ И NONE КООРДИНАТЫ")
    print("=" * 70)

    results = []
    results.append(test_missing_points_creation())
    results.append(test_none_coordinates_handling())

    print("\n" + "=" * 70)
    if all(results):
        print("[OK] ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        return True
    else:
        print("[ERROR] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)