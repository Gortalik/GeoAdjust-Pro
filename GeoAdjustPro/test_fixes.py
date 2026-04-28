#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест исправлений в модулях предобработки и уравнивания
"""

import sys
import os

# Добавляем путь к исходному коду
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

def test_equations_builder():
    """Тест построения уравнений"""
    print("Тестирование EquationsBuilder...")

    try:
        from geoadjust.core.adjustment.equations_builder import EquationsBuilder
        from geoadjust.core.network.models import NetworkPoint, Observation

        # Создаем тестовую сеть
        points = {
            'STA1': NetworkPoint(point_id='STA1', coord_type='FIXED', x=0, y=0, h=0),
            'P1': NetworkPoint(point_id='P1', coord_type='FREE', x=100, y=0, h=0),
        }

        observations = [
            Observation(obs_id='dist1', obs_type='distance', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
            Observation(obs_id='dir1', obs_type='direction', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=0.0, sigma_apriori=0.001),
            Observation(obs_id='hdist1', obs_type='horizontal_distance', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
        ]

        builder = EquationsBuilder()
        A, L = builder.build_adjustment_matrix(observations, points, [])
        print(f"[OK] Матрица построена: {A.shape[0]}x{A.shape[1]}, уравнений: {len(L)}")
        return True

    except Exception as e:
        print(f"[ERROR] Ошибка в EquationsBuilder: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_preprocessing():
    """Тест предобработки"""
    print("Тестирование PreprocessingModule...")

    try:
        from geoadjust.core.preprocessing.module import PreprocessingModule
        from geoadjust.core.network.models import Observation

        # Создаем тестовые измерения
        observations = [
            Observation(obs_id='dist1', obs_type='distance', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
            Observation(obs_id='hdist1', obs_type='horizontal_distance', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
        ]

        preprocessor = PreprocessingModule()
        results = preprocessor.run_preprocessing(observations, {}, {})

        if results.get('corrected_observations'):
            print(f"[OK] Предобработка выполнена, обработано {len(results['corrected_observations'])} измерений")
            return True
        else:
            print("[ERROR] Предобработка не вернула исправленные измерения")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка в PreprocessingModule: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("ТЕСТ ИСПРАВЛЕНИЙ В МОДУЛЯХ ПРЕДОБРАБОТКИ И УРАВНИВАНИЯ")
    print("=" * 60)

    results = []
    results.append(test_preprocessing())
    results.append(test_equations_builder())

    print("\n" + "=" * 60)
    if all(results):
        print("[OK] ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        return True
    else:
        print("[ERROR] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)