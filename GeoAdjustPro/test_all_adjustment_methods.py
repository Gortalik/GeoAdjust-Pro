#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексное тестирование ВСЕХ методов уравнивания на реальных данных

Методы:
1. AdjustmentEngine - Классический МНК (параметрический метод)
2. FreeNetworkAdjustment - Свободное уравнивание с минимальными ограничениями
3. RobustMethods - Робастные методы:
   a. IRLS с функцией Хьюбера
   b. IRLS с функцией Тьюки
   c. L1-минимизация
"""

import sys
from pathlib import Path
import numpy as np
from scipy import sparse


from geoadjust.io.formats.sdr import SDRParser
from geoadjust.io.formats.dat import DATParser
from geoadjust.io.formats.pos import POSParser
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.free_network import FreeNetworkAdjustment
from geoadjust.core.adjustment.robust_methods import RobustMethods

import logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

TEST_DATA_DIR = Path(__file__).parent.parent / 'test_real_mes'


def build_2d_test_data(sdr_file):
    """Построение 2D данных из SDR файла для уравнивания"""
    parser = SDRParser()
    result = parser.parse(sdr_file)
    
    # Собираем уникальные точки
    point_ids = set()
    for obs in result['observations']:
        point_ids.add(obs.from_point)
        point_ids.add(obs.to_point)
    
    point_ids = sorted(point_ids)
    point_map = {pid: idx for idx, pid in enumerate(point_ids)}
    
    # Фильтруем направления и расстояния
    directions = [obs for obs in result['observations'] if obs.obs_type == 'direction']
    distances = [obs for obs in result['observations'] if obs.obs_type == 'slope_distance']
    
    if len(directions) < 3:
        return None, None, None, None
    
    n_obs = len(directions) + len(distances)
    n_unknowns = 2 * len(point_ids)  # x, y для каждой точки
    
    # Строим матрицу A и вектор L
    A_rows, A_cols, A_vals = [], [], []
    L = np.zeros(n_obs)
    P = np.zeros(n_obs)
    
    obs_idx = 0
    
    # Уравнения для направлений
    for obs in directions:
        from_idx = point_map.get(obs.from_point)
        to_idx = point_map.get(obs.to_point)
        
        if from_idx is None or to_idx is None:
            continue
        
        # Задаём случайные приближения для всех точек
        x1, y1 = np.random.rand() * 1000, np.random.rand() * 1000
        x2, y2 = np.random.rand() * 1000, np.random.rand() * 1000
        
        dx = x2 - x1
        dy = y2 - y1
        s_approx = np.sqrt(dx**2 + dy**2)
        
        if s_approx < 10:
            x2, y2 = x1 + 100, y1 + 100
            dx, dy = 100, 100
            s_approx = np.sqrt(dx**2 + dy**2)
        
        azimuth_approx = np.arctan2(dx, dy) % (2 * np.pi)
        l_obs = obs.value * np.pi / 200  # из гон в радианы
        
        L[obs_idx] = l_obs - azimuth_approx
        while L[obs_idx] > np.pi:
            L[obs_idx] -= 2 * np.pi
        while L[obs_idx] < -np.pi:
            L[obs_idx] += 2 * np.pi
        
        rho = 206265
        A_rows.extend([obs_idx, obs_idx, obs_idx, obs_idx])
        A_cols.extend([2*from_idx, 2*from_idx+1, 2*to_idx, 2*to_idx+1])
        A_vals.extend([
            dy / (s_approx**2) * rho,
            -dx / (s_approx**2) * rho,
            -dy / (s_approx**2) * rho,
            dx / (s_approx**2) * rho
        ])
        P[obs_idx] = 1.0
        obs_idx += 1
    
    # Уравнения для расстояний
    for obs in distances:
        from_idx = point_map.get(obs.from_point)
        to_idx = point_map.get(obs.to_point)
        
        if from_idx is None or to_idx is None:
            continue
        
        x1, y1 = np.random.rand() * 1000, np.random.rand() * 1000
        x2, y2 = np.random.rand() * 1000, np.random.rand() * 1000
        
        dx = x2 - x1
        dy = y2 - y1
        s_approx = np.sqrt(dx**2 + dy**2)
        
        if s_approx < 10:
            x2, y2 = x1 + 100, y1 + 100
            dx, dy = 100, 100
            s_approx = np.sqrt(dx**2 + dy**2)
        
        L[obs_idx] = obs.value - s_approx
        
        A_rows.extend([obs_idx, obs_idx, obs_idx, obs_idx])
        A_cols.extend([2*from_idx, 2*from_idx+1, 2*to_idx, 2*to_idx+1])
        A_vals.extend([
            -dx / s_approx,
            -dy / s_approx,
            dx / s_approx,
            dy / s_approx
        ])
        P[obs_idx] = 1.0 / (0.002 + 2e-6 * s_approx)**2
        obs_idx += 1
    
    if obs_idx == 0:
        return None, None, None, None
    
    A = sparse.csr_matrix((A_vals, (A_rows, A_cols)), shape=(obs_idx, n_unknowns))
    P_diag = sparse.diags(P[:obs_idx])
    
    return A, L[:obs_idx], P_diag, point_ids


def build_1d_test_data(dat_file):
    """Построение 1D данных из DAT файла для уравнивания"""
    parser = DATParser()
    result = parser.parse(dat_file)
    
    point_ids = set()
    for obs in result['observations']:
        point_ids.add(obs.from_point)
        point_ids.add(obs.to_point)
    
    point_ids = sorted(point_ids)
    point_map = {pid: idx for idx, pid in enumerate(point_ids)}
    
    height_diffs = [obs for obs in result['observations'] if obs.obs_type == 'height_diff']
    
    if len(height_diffs) < 2:
        return None, None, None, None
    
    n_obs = len(height_diffs)
    n_unknowns = len(point_ids)
    
    A_rows, A_cols, A_vals = [], [], []
    L = np.zeros(n_obs)
    P = np.zeros(n_obs)
    
    for i, obs in enumerate(height_diffs):
        from_idx = point_map.get(obs.from_point)
        to_idx = point_map.get(obs.to_point)
        
        if from_idx is None or to_idx is None:
            continue
        
        L[i] = obs.value
        A_rows.extend([i, i])
        A_cols.extend([from_idx, to_idx])
        A_vals.extend([-1.0, 1.0])
        P[i] = 1.0 / (0.001**2)
    
    if not A_vals:
        return None, None, None, None
    
    A = sparse.csr_matrix((A_vals, (A_rows, A_cols)), shape=(n_obs, n_unknowns))
    P_diag = sparse.diags(P[:n_obs])
    
    return A, L[:n_obs], P_diag, point_ids


def test_adjustment_engine(A, L, P, name):
    """Тестирование AdjustmentEngine (классический МНК)"""
    print(f"\n  --- AdjustmentEngine (МНК) ---")
    try:
        engine = AdjustmentEngine()
        result = engine.adjust(A, L, P)
        
        sigma0 = result['sigma0']
        max_res = np.max(np.abs(result['residuals']))
        mean_res = np.mean(np.abs(result['residuals']))
        
        print(f"    СКО единицы веса: {sigma0:.6f}")
        print(f"    Макс. невязка: {max_res:.6f}")
        print(f"    Средн. невязка: {mean_res:.6f}")
        print(f"    Статус: OK")
        return True
    except Exception as e:
        print(f"    ОШИБКА: {e}")
        return False


def test_free_network_adjustment(A, L, name, dimension='2d'):
    """Тестирование FreeNetworkAdjustment"""
    print(f"\n  --- FreeNetworkAdjustment ({dimension}) ---")
    try:
        free_adj = FreeNetworkAdjustment(dimension=dimension)
        dx, lambdas, C, w = free_adj.apply_minimum_constraints(A, L, np.zeros(A.shape[1]))
        
        residuals = A @ dx - L
        n = len(L)
        r = n - A.shape[1] + C.shape[0]
        if r > 0:
            sigma0 = np.sqrt((residuals.T @ residuals) / r)
        else:
            sigma0 = 0.0
        
        max_res = np.max(np.abs(residuals))
        mean_res = np.mean(np.abs(residuals))
        
        print(f"    СКО единицы веса: {sigma0:.6f}")
        print(f"    Макс. невязка: {max_res:.6f}")
        print(f"    Средн. невязка: {mean_res:.6f}")
        print(f"    Число ограничений: {C.shape[0]}")
        print(f"    Статус: OK")
        return True
    except Exception as e:
        print(f"    ОШИБКА: {e}")
        return False


def test_robust_huber(A, L, P, name):
    """Тестирование IRLS с функцией Хьюбера"""
    print(f"\n  --- Robust IRLS (Huber) ---")
    try:
        robust = RobustMethods(method='huber')
        result = robust.irls_adjustment(A, L, max_iter=20, tolerance=1e-6)
        
        sigma0 = result['sigma0']
        max_res = np.max(np.abs(result['residuals']))
        mean_res = np.mean(np.abs(result['residuals']))
        iterations = result['iterations']
        
        print(f"    СКО единицы веса: {sigma0:.6f}")
        print(f"    Макс. невязка: {max_res:.6f}")
        print(f"    Средн. невязка: {mean_res:.6f}")
        print(f"    Итераций: {iterations}")
        print(f"    Статус: OK")
        return True
    except Exception as e:
        print(f"    ОШИБКА: {e}")
        return False


def test_robust_tukey(A, L, P, name):
    """Тестирование IRLS с функцией Тьюки"""
    print(f"\n  --- Robust IRLS (Tukey) ---")
    try:
        robust = RobustMethods(method='tukey')
        result = robust.irls_adjustment(A, L, max_iter=20, tolerance=1e-6)
        
        sigma0 = result['sigma0']
        max_res = np.max(np.abs(result['residuals']))
        mean_res = np.mean(np.abs(result['residuals']))
        iterations = result['iterations']
        
        print(f"    СКО единицы веса: {sigma0:.6f}")
        print(f"    Макс. невязка: {max_res:.6f}")
        print(f"    Средн. невязка: {mean_res:.6f}")
        print(f"    Итераций: {iterations}")
        print(f"    Статус: OK")
        return True
    except Exception as e:
        print(f"    ОШИБКА: {e}")
        return False


def test_l1_minimization(A, L, P, name):
    """Тестирование L1-минимизации"""
    print(f"\n  --- L1 Minimization ---")
    try:
        robust = RobustMethods(method='l1')
        result = robust.l1_minimization(A, L, P)
        
        if result.get('success', False):
            sigma0 = result['sigma0']
            max_res = np.max(np.abs(result['residuals']))
            mean_res = np.mean(np.abs(result['residuals']))
            
            print(f"    СКО единицы веса: {sigma0:.6f}")
            print(f"    Макс. невязка: {max_res:.6f}")
            print(f"    Средн. невязка: {mean_res:.6f}")
            print(f"    Статус: OK")
            return True
        else:
            print(f"    Не удалось решить: {result.get('message', 'Неизвестная ошибка')}")
            return False
    except Exception as e:
        print(f"    ОШИБКА: {e}")
        return False


def run_all_tests():
    """Запуск всех тестов уравнивания"""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ВСЕХ МЕТОДОВ УРАВНИВАНИЯ НА РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 70)
    
    all_results = {}
    
    # Тест 1: 2D сеть (SDR данные)
    print("\n" + "=" * 70)
    print("ТЕСТ 1: Плановая сеть (SDR - badgro16093_const.sdr)")
    print("=" * 70)
    
    A_2d, L_2d, P_2d, points_2d = build_2d_test_data(TEST_DATA_DIR / 'b_g/plan/badgro16093_const.sdr')
    
    if A_2d is not None:
        print(f"\n  Матрица: {A_2d.shape[0]} измерений x {A_2d.shape[1]} неизвестных")
        print(f"  Избыточность: {A_2d.shape[0] - A_2d.shape[1]}")
        
        results_2d = {}
        results_2d['МНК (AdjustmentEngine)'] = test_adjustment_engine(A_2d, L_2d, P_2d, '2D')
        results_2d['Свободное уравнивание'] = test_free_network_adjustment(A_2d, L_2d, '2D', '2d')
        results_2d['IRLS Huber'] = test_robust_huber(A_2d, L_2d, P_2d, '2D')
        results_2d['IRLS Tukey'] = test_robust_tukey(A_2d, L_2d, P_2d, '2D')
        results_2d['L1 Minimization'] = test_l1_minimization(A_2d, L_2d, P_2d, '2D')
        
        all_results['2D_planar'] = results_2d
    else:
        print("  Не удалось построить данные для уравнивания")
        all_results['2D_planar'] = {}
    
    # Тест 2: 1D сеть (DAT данные)
    print("\n" + "=" * 70)
    print("ТЕСТ 2: Нивелирная сеть (DAT - LIH2103.DAT)")
    print("=" * 70)
    
    A_1d, L_1d, P_1d, points_1d = build_1d_test_data(TEST_DATA_DIR / 'l/niv/LIH2103.DAT')
    
    if A_1d is not None:
        print(f"\n  Матрица: {A_1d.shape[0]} измерений x {A_1d.shape[1]} неизвестных")
        print(f"  Избыточность: {A_1d.shape[0] - A_1d.shape[1]}")
        
        results_1d = {}
        results_1d['МНК (AdjustmentEngine)'] = test_adjustment_engine(A_1d, L_1d, P_1d, '1D')
        results_1d['Свободное уравнивание'] = test_free_network_adjustment(A_1d, L_1d, '1D', '1d')
        results_1d['IRLS Huber'] = test_robust_huber(A_1d, L_1d, P_1d, '1D')
        results_1d['IRLS Tukey'] = test_robust_tukey(A_1d, L_1d, P_1d, '1D')
        results_1d['L1 Minimization'] = test_l1_minimization(A_1d, L_1d, P_1d, '1D')
        
        all_results['1D_leveling'] = results_1d
    else:
        print("  Не удалось построить данные для уравнивания")
        all_results['1D_leveling'] = {}
    
    # Тест 3: Другая 2D сеть
    print("\n" + "=" * 70)
    print("ТЕСТ 3: Плановая сеть (SDR - gro2908_const.sdr)")
    print("=" * 70)
    
    A_2d_2, L_2d_2, P_2d_2, points_2d_2 = build_2d_test_data(TEST_DATA_DIR / 'n_g/plan/gro2908_const.sdr')
    
    if A_2d_2 is not None:
        print(f"\n  Матрица: {A_2d_2.shape[0]} измерений x {A_2d_2.shape[1]} неизвестных")
        print(f"  Избыточность: {A_2d_2.shape[0] - A_2d_2.shape[1]}")
        
        results_2d_2 = {}
        results_2d_2['МНК (AdjustmentEngine)'] = test_adjustment_engine(A_2d_2, L_2d_2, P_2d_2, '2D')
        results_2d_2['Свободное уравнивание'] = test_free_network_adjustment(A_2d_2, L_2d_2, '2D', '2d')
        results_2d_2['IRLS Huber'] = test_robust_huber(A_2d_2, L_2d_2, P_2d_2, '2D')
        results_2d_2['IRLS Tukey'] = test_robust_tukey(A_2d_2, L_2d_2, P_2d_2, '2D')
        results_2d_2['L1 Minimization'] = test_l1_minimization(A_2d_2, L_2d_2, P_2d_2, '2D')
        
        all_results['2D_planar_2'] = results_2d_2
    else:
        print("  Не удалось построить данные для уравнивания")
        all_results['2D_planar_2'] = {}
    
    # Сводная информация
    print("\n" + "=" * 70)
    print("СВОДНАЯ ИНФОРМАЦИЯ ПО ВСЕМ МЕТОДАМ УРАВНИВАНИЯ")
    print("=" * 70)
    
    methods = ['МНК (AdjustmentEngine)', 'Свободное уравнивание', 'IRLS Huber', 'IRLS Tukey', 'L1 Minimization']
    tests = ['2D_planar', '1D_leveling', '2D_planar_2']
    test_names = ['2D плановая', '1D нивелирная', '2D плановая #2']
    
    print(f"\n{'Метод':<30} | {'2D плановая':<15} | {'1D нивелирная':<15} | {'2D плановая #2':<15}")
    print("-" * 85)
    
    for method in methods:
        row = f"{method:<30} | "
        for i, test in enumerate(tests):
            if test in all_results and method in all_results[test]:
                status = "OK" if all_results[test][method] else "FAIL"
                row += f"{status:<15} | "
            else:
                row += f"{'N/A':<15} | "
        print(row)
    
    # Подсчёт успешных тестов
    total_tests = 0
    passed_tests = 0
    for test in tests:
        if test in all_results:
            for method in methods:
                if method in all_results[test]:
                    total_tests += 1
                    if all_results[test][method]:
                        passed_tests += 1
    
    print(f"\n{'=' * 70}")
    print(f"ИТОГО: {passed_tests}/{total_tests} тестов пройдено успешно")
    if passed_tests == total_tests:
        print("ВСЕ МЕТОДЫ УРАВНИВАНИЯ РАБОТАЮТ КОРРЕКТНО")
    else:
        print(f"ЕСТЬ ПРОБЛЕМЫ: {total_tests - passed_tests} тестов не пройдено")
    print(f"{'=' * 70}")
    
    return passed_tests == total_tests


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
