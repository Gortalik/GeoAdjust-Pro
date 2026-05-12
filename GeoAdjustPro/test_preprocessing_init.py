#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления инициализации PreprocessingModule
"""

import sys
import os

# Добавляем путь к исходному коду
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:

def test_preprocessing_init():
    """Тест инициализации PreprocessingModule с параметрами"""
    print("Тестирование инициализации PreprocessingModule...")

    try:
        from geoadjust.core.preprocessing.module import PreprocessingModule

        # Тест инициализации без параметров (должен работать с дефолтными)
        preprocessor1 = PreprocessingModule()
        print("[OK] PreprocessingModule() создан успешно")

        # Тест инициализации с параметром tolerances
        preprocessor2 = PreprocessingModule(tolerances={'test': 1.0})
        print("[OK] PreprocessingModule(tolerances={}) создан успешно")

        # Тест инициализации с None
        preprocessor3 = PreprocessingModule(tolerances=None)
        print("[OK] PreprocessingModule(tolerances=None) создан успешно")

        return True

    except Exception as e:
        print(f"[ERROR] Ошибка инициализации PreprocessingModule: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_preprocessing_run():
    """Тест запуска предобработки"""
    print("Тестирование запуска предобработки...")

    try:
        from geoadjust.core.preprocessing.module import PreprocessingModule
        from geoadjust.core.network.models import Observation

        # Создаем тестовые измерения
        observations = [
            Observation(obs_id='dist1', obs_type='distance', from_setup_id='STA1_SETUP',
                       from_point_id='STA1', to_point_id='P1', value=100.0, sigma_apriori=0.001),
        ]

        preprocessor = PreprocessingModule()
        results = preprocessor.run_preprocessing(observations, {}, {})

        if results is not None:
            print(f"[OK] Предобработка выполнена, получены результаты: {list(results.keys())}")
            return True
        else:
            print("[ERROR] Предобработка вернула None")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка запуска предобработки: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("ТЕСТ ИСПРАВЛЕНИЙ: ИНИЦИАЛИЗАЦИЯ PREPROCESSINGMODULE")
    print("=" * 60)

    results = []
    results.append(test_preprocessing_init())
    results.append(test_preprocessing_run())

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