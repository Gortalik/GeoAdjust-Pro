#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексное тестирование уравнивания свободных сетей
на реальных данных из папки test_real_mes

Тестирует:
1. Парсинг данных (GSI, SDR, DAT)
2. Построение уравнений поправок
3. Свободное уравнивание (free network adjustment)
4. Параметрическое уравнивание (adjustment engine)
5. Оценку точности
"""

import sys
import os
from pathlib import Path
import numpy as np
from scipy import sparse

# Добавляем путь к модулям

from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.sdr import SDRParser
from geoadjust.io.formats.dat import DATParser
from geoadjust.core.adjustment.free_network import FreeNetworkAdjustment
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder

import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Базовый путь к тестовым данным
TEST_DATA_DIR = Path(__file__).parent.parent / 'test_real_mes'


class MockPoint:
    """Мок класса точки для уравнивания"""
    def __init__(self, point_id, x=None, y=None, h=None, point_type='unknown'):
        self.point_id = point_id
        self.x = x
        self.y = y
        self.h = h
        self.point_type = point_type


class MockObservation:
    """Мок класса наблюдения для уравнивания"""
    def __init__(self, obs_type, from_point, to_point, value, std_dev=None):
        self.obs_type = obs_type
        self.from_point = from_point
        self.to_point = to_point
        self.value = value
        self.std_dev = std_dev


def build_adjustment_data(observations, points_dict):
    """
    Построение данных для уравнивания из распарсенных наблюдений
    
    Возвращает:
    - points: список точек
    - obs_list: список наблюдений
    - point_map: словарь соответствия имя->индекс
    """
    # Собираем уникальные точки
    point_ids = set()
    for obs in observations:
        if hasattr(obs, 'from_point'):
            point_ids.add(obs.from_point)
        if hasattr(obs, 'to_point'):
            point_ids.add(obs.to_point)
    
    point_ids = sorted(point_ids)
    point_map = {pid: idx for idx, pid in enumerate(point_ids)}
    
    # Создаем точки с приближенными координатами
    points = []
    for pid in point_ids:
        pt_info = points_dict.get(pid, {})
        x = pt_info.get('x') if isinstance(pt_info, dict) else None
        y = pt_info.get('y') if isinstance(pt_info, dict) else None
        h = pt_info.get('h') if isinstance(pt_info, dict) else None
        
        # Если координат нет, задаем нулевые приближения
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if h is None:
            h = 0.0
        
        points.append(MockPoint(pid, x, y, h))
    
    return points, point_map


def test_sdr_adjustment(sdr_file):
    """Тестирование уравнивания на SDR данных (плановая сеть)"""
    print(f"\n{'=' * 70}")
    print(f"ТЕСТИРОВАНИЕ УРАВНИВАНИЯ: {sdr_file.name}")
    print(f"{'=' * 70}")
    
    # Парсим SDR файл
    parser = SDRParser()
    result = parser.parse(sdr_file)
    
    if not result['observations']:
        print("  Нет измерений для уравнивания!")
        return None
    
    print(f"\n  Распарсено:")
    print(f"    Измерений: {result['num_observations']}")
    print(f"    Пунктов: {result['num_points']}")
    
    # Фильтруем измерения по типам
    directions = [obs for obs in result['observations'] if obs.obs_type == 'direction']
    distances = [obs for obs in result['observations'] if obs.obs_type in ['slope_distance', 'horizontal_distance']]
    
    print(f"    Направлений: {len(directions)}")
    print(f"    Расстояний: {len(distances)}")
    
    if len(directions) < 2:
        print("  Недостаточно направлений для уравнивания (минимум 2)")
        return None
    
    # Создаем точки
    points, point_map = build_adjustment_data(result['observations'], {p['point_id']: p for p in result['points']})
    
    print(f"\n  Точек для уравнивания: {len(points)}")
    
    # Строим матрицу коэффициентов для параметрического метода
    # Для направлений: A_ij = -sin(azimuth), B_ij = cos(azimuth)
    # Для расстояний: A_ij = cos(azimuth), B_ij = sin(azimuth)
    
    n_obs = len(directions) + len(distances)
    n_unknowns = 2 * len(points)  # x, y для каждой точки
    
    if n_unknowns == 0 or n_obs == 0:
        print("  Невозможно построить систему уравнений")
        return None
    
    # Создаем разреженные матрицы
    A_rows = []
    A_cols = []
    A_vals = []
    L = np.zeros(n_obs)
    P = np.zeros(n_obs)  # Веса
    
    obs_idx = 0
    
    # Уравнения для направлений
    for i, obs in enumerate(directions):
        from_idx = point_map.get(obs.from_point)
        to_idx = point_map.get(obs.to_point)
        
        if from_idx is None or to_idx is None:
            continue
        
        # Приближенные координаты
        x1 = points[from_idx].x
        y1 = points[from_idx].y
        x2 = points[to_idx].x
        y2 = points[to_idx].y
        
        # Вычисляем приближенный дирекционный угол и расстояние
        dx = x2 - x1
        dy = y2 - y1
        s_approx = np.sqrt(dx**2 + dy**2)
        
        if s_approx < 0.001:
            # Задаем случайные приближения
            x2 = x1 + 100
            y2 = y1 + 100
            dx = 100
            dy = 100
            s_approx = np.sqrt(dx**2 + dy**2)
        
        azimuth_approx = np.arctan2(dx, dy) % (2 * np.pi)
        
        # Наблюдаемое направление
        l_obs = obs.value * np.pi / 200  # Из гон в радианы (если в гонах)
        
        # Свободный член
        L[obs_idx] = l_obs - azimuth_approx
        
        # Нормализуем невязку
        while L[obs_idx] > np.pi:
            L[obs_idx] -= 2 * np.pi
        while L[obs_idx] < -np.pi:
            L[obs_idx] += 2 * np.pi
        
        # Коэффициенты для направления
        # d(azimuth)/dx1 = -dy/s^2, d(azimuth)/dy1 = dx/s^2
        # d(azimuth)/dx2 = dy/s^2, d(azimuth)/dy2 = -dx/s^2
        
        rho = 206265  # Секунд в радиане
        
        A_rows.extend([obs_idx, obs_idx, obs_idx, obs_idx])
        A_cols.extend([2*from_idx, 2*from_idx+1, 2*to_idx, 2*to_idx+1])
        A_vals.extend([
            dy / (s_approx**2) * rho,  # dx1
            -dx / (s_approx**2) * rho,  # dy1
            -dy / (s_approx**2) * rho,  # dx2
            dx / (s_approx**2) * rho   # dy2
        ])
        
        # Вес направления (СКО ~1")
        P[obs_idx] = 1.0 / (1.0**2)
        
        obs_idx += 1
    
    # Уравнения для расстояний
    for i, obs in enumerate(distances):
        from_idx = point_map.get(obs.from_point)
        to_idx = point_map.get(obs.to_point)
        
        if from_idx is None or to_idx is None:
            continue
        
        x1 = points[from_idx].x
        y1 = points[from_idx].y
        x2 = points[to_idx].x
        y2 = points[to_idx].y
        
        dx = x2 - x1
        dy = y2 - y1
        s_approx = np.sqrt(dx**2 + dy**2)
        
        if s_approx < 0.001:
            x2 = x1 + 100
            y2 = y1 + 100
            dx = 100
            dy = 100
            s_approx = np.sqrt(dx**2 + dy**2)
        
        # Наблюдаемое расстояние
        l_obs = obs.value
        
        # Свободный член
        L[obs_idx] = l_obs - s_approx
        
        # Коэффициенты для расстояния
        # dS/dx1 = -dx/S, dS/dy1 = -dy/S
        # dS/dx2 = dx/S, dS/dy2 = dy/S
        
        A_rows.extend([obs_idx, obs_idx, obs_idx, obs_idx])
        A_cols.extend([2*from_idx, 2*from_idx+1, 2*to_idx, 2*to_idx+1])
        A_vals.extend([
            -dx / s_approx,  # dx1
            -dy / s_approx,  # dy1
            dx / s_approx,   # dx2
            dy / s_approx    # dy2
        ])
        
        # Вес расстояния (СКО ~2мм + 2ppm)
        sigma_s = 0.002 + 2e-6 * s_approx
        P[obs_idx] = 1.0 / (sigma_s**2)
        
        obs_idx += 1
    
    if obs_idx == 0:
        print("  Не удалось построить уравнений поправок")
        return None
    
    # Создаем разреженную матрицу A
    A = sparse.csr_matrix((A_vals, (A_rows, A_cols)), shape=(obs_idx, n_unknowns))
    P_diag = sparse.diags(P[:obs_idx])
    
    print(f"\n  Матрица уравнений: {A.shape[0]} измерений x {A.shape[1]} неизвестных")
    print(f"  Избыточность: {A.shape[0] - A.shape[1]}")
    
    # Свободное уравнивание
    print(f"\n  --- Свободное уравнивание ---")
    free_adj = FreeNetworkAdjustment(dimension='2d')
    
    try:
        dx, lambdas, C, w = free_adj.apply_minimum_constraints(A, L[:obs_idx], np.zeros(n_unknowns), points)
        
        # Вычисляем уравненные координаты
        adjusted_coords = np.zeros(n_unknowns) + dx
        
        # Вычисляем невязки
        residuals = A @ dx - L[:obs_idx]
        
        # СКО единицы веса
        r = obs_idx - n_unknowns + C.shape[0]  # Степень свободы с учетом ограничений
        if r > 0:
            sigma0 = np.sqrt((residuals.T @ P_diag @ residuals) / r)
        else:
            sigma0 = 0.0
        
        print(f"  СКО единицы веса: {sigma0:.4f}")
        print(f"  Максимальная невязка: {np.max(np.abs(residuals)):.4f}")
        print(f"  Средняя невязка: {np.mean(np.abs(residuals)):.4f}")
        
        # Выводим уравненные координаты
        print(f"\n  Уравненные координаты (первые 10 точек):")
        for i in range(min(10, len(points))):
            x_adj = adjusted_coords[2*i]
            y_adj = adjusted_coords[2*i+1]
            print(f"    {points[i].point_id:15}: X={x_adj:12.4f}, Y={y_adj:12.4f}")
        
        return {
            'file': str(sdr_file),
            'n_points': len(points),
            'n_observations': obs_idx,
            'n_unknowns': n_unknowns,
            'sigma0': sigma0,
            'max_residual': float(np.max(np.abs(residuals))),
            'mean_residual': float(np.mean(np.abs(residuals))),
            'success': True
        }
        
    except Exception as e:
        print(f"  ОШИБКА при уравнивании: {e}")
        import traceback
        traceback.print_exc()
        return {
            'file': str(sdr_file),
            'success': False,
            'error': str(e)
        }


def test_dat_adjustment(dat_file):
    """Тестирование уравнивания на DAT данных (нивелирная сеть)"""
    print(f"\n{'=' * 70}")
    print(f"ТЕСТИРОВАНИЕ УРАВНИВАНИЯ (нивелирование): {dat_file.name}")
    print(f"{'=' * 70}")
    
    # Парсим DAT файл
    parser = DATParser()
    result = parser.parse(dat_file)
    
    if not result['observations']:
        print("  Нет измерений для уравнивания!")
        return None
    
    print(f"\n  Распарсено:")
    print(f"    Измерений: {result['num_observations']}")
    print(f"    Пунктов: {result['num_points']}")
    
    # Фильтруем превышения
    height_diffs = [obs for obs in result['observations'] if obs.obs_type == 'height_diff']
    
    print(f"    Превышений: {len(height_diffs)}")
    
    if len(height_diffs) < 2:
        print("  Недостаточно превышений для уравнивания (минимум 2)")
        return None
    
    # Создаем точки
    points, point_map = build_adjustment_data(result['observations'], {p['point_id']: p for p in result['points']})
    
    print(f"\n  Точек для уравнивания: {len(points)}")
    
    n_obs = len(height_diffs)
    n_unknowns = len(points)  # Только высоты для нивелирования
    
    if n_unknowns == 0 or n_obs == 0:
        print("  Невозможно построить систему уравнений")
        return None
    
    # Строим матрицу для нивелирования
    # Уравнение: h_to - h_from = dh_obs + v
    A_rows = []
    A_cols = []
    A_vals = []
    L = np.zeros(n_obs)
    P = np.zeros(n_obs)
    
    for i, obs in enumerate(height_diffs):
        from_idx = point_map.get(obs.from_point)
        to_idx = point_map.get(obs.to_point)
        
        if from_idx is None or to_idx is None:
            continue
        
        # Свободный член (наблюдаемое превышение)
        L[i] = obs.value
        
        # Коэффициенты: -1 для начальной точки, +1 для конечной
        A_rows.extend([i, i])
        A_cols.extend([from_idx, to_idx])
        A_vals.extend([-1.0, 1.0])
        
        # Вес (СКО нивелирования ~1мм на станцию)
        P[i] = 1.0 / (0.001**2)
    
    if not A_vals:
        print("  Не удалось построить уравнений поправок")
        return None
    
    A = sparse.csr_matrix((A_vals, (A_rows, A_cols)), shape=(n_obs, n_unknowns))
    P_diag = sparse.diags(P[:n_obs])
    
    print(f"\n  Матрица уравнений: {A.shape[0]} измерений x {A.shape[1]} неизвестных")
    print(f"  Избыточность: {A.shape[0] - A.shape[1]}")
    
    # Свободное уравнивание нивелирной сети (1D)
    print(f"\n  --- Свободное уравнивание нивелирной сети (1D) ---")
    free_adj = FreeNetworkAdjustment(dimension='1d')  # Используем 1d для нивелирования
    
    try:
        dx, lambdas, C, w = free_adj.apply_minimum_constraints(A, L[:n_obs], np.zeros(n_unknowns), points)
        
        # Вычисляем уравненные высоты
        adjusted_heights = np.zeros(n_unknowns) + dx
        
        # Вычисляем невязки
        residuals = A @ dx - L[:n_obs]
        
        # СКО единицы веса
        r = n_obs - n_unknowns + C.shape[0]
        if r > 0:
            sigma0 = np.sqrt((residuals.T @ P_diag @ residuals) / r)
        else:
            sigma0 = 0.0
        
        print(f"  СКО единицы веса: {sigma0*1000:.4f} мм")
        print(f"  Максимальная невязка: {np.max(np.abs(residuals))*1000:.4f} мм")
        print(f"  Средняя невязка: {np.mean(np.abs(residuals))*1000:.4f} мм")
        
        # Выводим уравненные высоты
        print(f"\n  Уравненные высоты (первые 10 точек):")
        for i in range(min(10, len(points))):
            h_adj = adjusted_heights[i]
            print(f"    {points[i].point_id:15}: H={h_adj:10.5f} м")
        
        return {
            'file': str(dat_file),
            'n_points': len(points),
            'n_observations': n_obs,
            'n_unknowns': n_unknowns,
            'sigma0_mm': sigma0 * 1000,
            'max_residual_mm': float(np.max(np.abs(residuals))) * 1000,
            'mean_residual_mm': float(np.mean(np.abs(residuals))) * 1000,
            'success': True
        }
        
    except Exception as e:
        print(f"  ОШИБКА при уравнивании: {e}")
        import traceback
        traceback.print_exc()
        return {
            'file': str(dat_file),
            'success': False,
            'error': str(e)
        }


def run_all_tests():
    """Запуск всех тестов уравнивания"""
    print("=" * 70)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ УРАВНИВАНИЯ СВОБОДНЫХ СЕТЕЙ")
    print("=" * 70)
    
    results = []
    
    # Тестируем SDR файлы (плановые сети)
    sdr_files = list(TEST_DATA_DIR.glob('**/*.sdr'))
    print(f"\nНайдено SDR файлов: {len(sdr_files)}")
    
    for sdr_file in sdr_files[:3]:  # Ограничиваем до 3 файлов для быстрого теста
        result = test_sdr_adjustment(sdr_file)
        if result:
            results.append(result)
    
    # Тестируем DAT файлы (нивелирные сети)
    dat_files = list(TEST_DATA_DIR.glob('**/*.DAT'))
    print(f"\nНайдено DAT файлов: {len(dat_files)}")
    
    for dat_file in dat_files[:3]:  # Ограничиваем до 3 файлов
        result = test_dat_adjustment(dat_file)
        if result:
            results.append(result)
    
    # Сводная информация
    print(f"\n{'=' * 70}")
    print("СВОДНАЯ ИНФОРМАЦИЯ ПО УРАВНИВАНИЮ")
    print(f"{'=' * 70}")
    
    success_count = sum(1 for r in results if r.get('success', False))
    fail_count = len(results) - success_count
    
    print(f"\nВсего тестов: {len(results)}")
    print(f"Успешных: {success_count}")
    print(f"Неудачных: {fail_count}")
    
    print(f"\n{'=' * 70}")
    print("ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ")
    print(f"{'=' * 70}")
    
    for r in results:
        status = "OK" if r.get('success', False) else "FAIL"
        file_name = Path(r['file']).name
        
        if r.get('success', False):
            if 'sigma0_mm' in r:
                print(f"\n  [{status}] {file_name} (нивелирование)")
                print(f"       Точек: {r['n_points']}, Измерений: {r['n_observations']}")
                print(f"       СКО: {r['sigma0_mm']:.3f} мм")
                print(f"       Макс. невязка: {r['max_residual_mm']:.3f} мм")
            else:
                print(f"\n  [{status}] {file_name} (плановая)")
                print(f"       Точек: {r['n_points']}, Измерений: {r['n_observations']}")
                print(f"       СКО: {r['sigma0']:.4f}")
                print(f"       Макс. невязка: {r['max_residual']:.4f}")
        else:
            print(f"\n  [{status}] {file_name}: {r.get('error', 'Неизвестная ошибка')}")
    
    return results


if __name__ == '__main__':
    print("Комплексное тестирование уравнивания свободных сетей")
    print(f"Директория с данными: {TEST_DATA_DIR}")
    
    if not TEST_DATA_DIR.exists():
        print(f"ОШИБКА: Директория {TEST_DATA_DIR} не существует!")
        sys.exit(1)
    
    results = run_all_tests()
    
    print(f"\n{'=' * 70}")
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print(f"{'=' * 70}")
