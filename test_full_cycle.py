#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Полный цикл обработки реальных измерений через код GeoAdjustPro
Тестирует все файлы с реальными данными
"""

import sys
import os

sys.path.insert(0, '/workspace/GeoAdjustPro/src')

import numpy as np
from scipy import sparse

from geoadjust.io.formats.sdr import SDRParser
from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.dat import DATParser
from geoadjust.core.network.models import NetworkPoint, Observation, InstrumentSetup
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder

def print_section(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def create_test_network():
    """Создать тестовую сеть для уравнивания"""
    points = {
        'P1': NetworkPoint(point_id='P1', coord_type='FIXED', x=1000.0, y=2000.0, h=100.0),
        'P2': NetworkPoint(point_id='P2', coord_type='FIXED', x=1100.0, y=2000.0, h=100.0),
        'P3': NetworkPoint(point_id='P3', coord_type='APPROXIMATE', x=1050.0, y=2100.0, h=100.0),
        'P4': NetworkPoint(point_id='P4', coord_type='APPROXIMATE', x=1050.0, y=1950.0, h=100.0),
    }
    
    observations = [
        Observation(obs_id='1', obs_type='direction', from_setup_id='S1', from_point_id='P1', to_point_id='P2', value=0.0),
        Observation(obs_id='2', obs_type='direction', from_setup_id='S1', from_point_id='P1', to_point_id='P3', value=0.785),
        Observation(obs_id='3', obs_type='direction', from_setup_id='S1', from_point_id='P1', to_point_id='P4', value=-0.785),
        Observation(obs_id='4', obs_type='distance', from_setup_id='S1', from_point_id='P1', to_point_id='P3', value=111.8),
        Observation(obs_id='5', obs_type='distance', from_setup_id='S1', from_point_id='P1', to_point_id='P4', value=50.0),
    ]
    
    return points, observations

def test_adjustment_engine():
    """Тест движка уравнивания на простых данных"""
    print_section("ТЕСТ 1: Движок уравнивания (простая сеть)")
    
    points, observations = create_test_network()
    print(f"✓ Создано {len(points)} точек")
    print(f"✓ Создано {len(observations)} наблюдений")
    
    try:
        builder = EquationsBuilder()
        # Используем правильный метод build_adjustment_matrix
        A, L = builder.build_adjustment_matrix(points, observations)
        print(f"✓ Матрица A: {A.shape}")
        print(f"✓ Вектор L: {L.shape}")
        
        weight_builder = WeightBuilder()
        P = weight_builder.build(observations)
        print(f"✓ Матрица P: {P.shape}")
        
        engine = AdjustmentEngine()
        result = engine.adjust(A, L, P)
        print(f"✓ Уравнивание выполнено")
        print(f"  Итераций: {result.get('iterations', 'N/A')}")
        print(f"  RMS: {result.get('rms', 'N/A')}")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sdr_file(filepath):
    """Тест парсинга SDR файла"""
    print_section(f"ТЕСТ SDR: {os.path.basename(filepath)}")
    
    try:
        parser = SDRParser()
        result = parser.parse(filepath)
        points = result.get('points', [])
        observations = result.get('observations', [])
        print(f"✓ Точек: {len(points)}")
        print(f"✓ Наблюдений: {len(observations)}")
        if points:
            print(f"  Первая точка: {points[0]}")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def test_gsi_file(filepath):
    """Тест парсинга GSI файла"""
    print_section(f"ТЕСТ GSI: {os.path.basename(filepath)}")
    
    try:
        parser = GSIParser()
        result = parser.parse(filepath)
        points = result.get('points', [])
        observations = result.get('observations', [])
        print(f"✓ Точек: {len(points)}")
        print(f"✓ Наблюдений: {len(observations)}")
        if points:
            print(f"  Первая точка: {points[0]}")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def test_dat_file(filepath):
    """Тест парсинга DAT файла"""
    print_section(f"ТЕСТ DAT: {os.path.basename(filepath)}")
    
    try:
        parser = DATParser()
        result = parser.parse(filepath)
        points = result.get('points', [])
        observations = result.get('observations', [])
        print(f"✓ Точек: {len(points)}")
        print(f"✓ Наблюдений: {len(observations)}")
        if points:
            print(f"  Первая точка: {points[0]}")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def main():
    print("=" * 70)
    print(" ПОЛНЫЙ ЦИКЛ ТЕСТИРОВАНИЯ GEOADJUSTPRO НА РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 70)
    
    results = {
        'SDR': {'passed': 0, 'failed': 0},
        'GSI': {'passed': 0, 'failed': 0},
        'DAT': {'passed': 0, 'failed': 0},
        'Adjustment': {'passed': 0, 'failed': 0}
    }
    
    # Тест 1: Adjustment Engine
    if test_adjustment_engine():
        results['Adjustment']['passed'] += 1
    else:
        results['Adjustment']['failed'] += 1
    
    # Тест SDR файлов
    sdr_files = [
        '/workspace/test_real_mes/k/kotlntss06042026.sdr',
        '/workspace/test_real_mes/n_g/plan/gro2908_const.sdr',
        '/workspace/test_real_mes/p_l_g/plan/grocenter (1)_const.sdr',
        '/workspace/test_real_mes/k_n/plan/ntsskotl06022026_const.sdr',
        '/workspace/test_real_mes/b_g/plan/badgro16093_const.sdr',
        '/workspace/test_real_mes/b_o/plan/badokr_const.sdr',
    ]
    
    for filepath in sdr_files:
        if os.path.exists(filepath):
            if test_sdr_file(filepath):
                results['SDR']['passed'] += 1
            else:
                results['SDR']['failed'] += 1
        else:
            print(f"\n⚠ Файл не найден: {filepath}")
    
    # Тест GSI файлов
    gsi_files = [
        '/workspace/test_real_mes/n_g/niv/GRO0109.GSI',
        '/workspace/test_real_mes/p_l_g/niv/GRO0509.GSI',
        '/workspace/test_real_mes/d_d_k/niv/KOL0708.GSI',
        '/workspace/test_real_mes/b_g/niv/GRO2209.GSI',
        '/workspace/test_real_mes/s5/niv/DOM0112 (1).GSI',
        '/workspace/test_real_mes/s5/niv/MIR0212.GSI',
        '/workspace/test_real_mes/d_d_o/niv/DAY1302.GSI',
    ]
    
    for filepath in gsi_files:
        if os.path.exists(filepath):
            if test_gsi_file(filepath):
                results['GSI']['passed'] += 1
            else:
                results['GSI']['failed'] += 1
        else:
            print(f"\n⚠ Файл не найден: {filepath}")
    
    # Тест DAT файлов
    dat_files = [
        '/workspace/test_real_mes/s_b/niv/BOT12210.DAT',
        '/workspace/test_real_mes/s_b2/niv/BOT22110.DAT',
        '/workspace/test_real_mes/l/niv/LIH2103.DAT',
    ]
    
    for filepath in dat_files:
        if os.path.exists(filepath):
            if test_dat_file(filepath):
                results['DAT']['passed'] += 1
            else:
                results['DAT']['failed'] += 1
        else:
            print(f"\n⚠ Файл не найден: {filepath}")
    
    # Итоговый отчет
    print_section("ИТОГОВЫЙ ОТЧЕТ")
    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total = total_passed + total_failed
    
    for category, data in results.items():
        print(f"{category}: {data['passed']} пройдено, {data['failed']} провалено")
    
    print(f"\nВСЕГО: {total_passed}/{total} тестов пройдено ({100*total_passed/total:.1f}%)")
    print("=" * 70)

if __name__ == '__main__':
    main()
