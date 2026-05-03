#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Полный цикл обработки реальных измерений через код GeoAdjustPro
Тестирует все файлы с реальными данными
Адаптировано для Windows путей
"""

import sys
import os

# Добавляем путь к модулям GeoAdjustPro
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GeoAdjustPro', 'src'))

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
    print_section("TEST 1: Adjustment Engine (simple network)")

    points, observations = create_test_network()
    print(f"Created {len(points)} points")
    print(f"Created {len(observations)} observations")

    try:
        builder = EquationsBuilder()
        # Use correct method build_adjustment_matrix
        A, L = builder.build_adjustment_matrix(points, observations)
        print(f"Matrix A: {A.shape}")
        print(f"Vector L: {L.shape}")

        weight_builder = WeightBuilder()
        P = weight_builder.build(observations)
        print(f"Matrix P: {P.shape}")

        engine = AdjustmentEngine()
        result = engine.adjust(A, L, P)
        print(f"Adjustment completed")
        print(f"  Iterations: {result.get('iterations', 'N/A')}")
        print(f"  RMS: {result.get('rms', 'N/A')}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sdr_file(filepath):
    """Test SDR file parsing"""
    print_section(f"TEST SDR: {os.path.basename(filepath)}")

    try:
        parser = SDRParser()
        result = parser.parse(filepath)
        points = result.get('points', [])
        observations = result.get('observations', [])
        print(f"Points: {len(points)}")
        print(f"Observations: {len(observations)}")
        if points:
            print(f"  First point: {points[0]}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_gsi_file(filepath):
    """Test GSI file parsing"""
    print_section(f"TEST GSI: {os.path.basename(filepath)}")

    try:
        parser = GSIParser()
        result = parser.parse(filepath)
        points = result.get('points', [])
        observations = result.get('observations', [])
        print(f"Points: {len(points)}")
        print(f"Observations: {len(observations)}")
        if points:
            print(f"  First point: {points[0]}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_dat_file(filepath):
    """Test DAT file parsing"""
    print_section(f"TEST DAT: {os.path.basename(filepath)}")

    try:
        parser = DATParser()
        result = parser.parse(filepath)
        points = result.get('points', [])
        observations = result.get('observations', [])
        print(f"Points: {len(points)}")
        print(f"Observations: {len(observations)}")
        if points:
            print(f"  First point: {points[0]}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 70)
    print(" FULL CYCLE TESTING OF GEOADJUSTPRO WITH REAL DATA")
    print("=" * 70)

    results = {
        'SDR': {'passed': 0, 'failed': 0},
        'GSI': {'passed': 0, 'failed': 0},
        'DAT': {'passed': 0, 'failed': 0},
        'Adjustment': {'passed': 0, 'failed': 0}
    }

    # Test 1: Adjustment Engine
    if test_adjustment_engine():
        results['Adjustment']['passed'] += 1
    else:
        results['Adjustment']['failed'] += 1

    # Test SDR files
    base_path = os.path.join(os.path.dirname(__file__), 'test_real_mes')
    sdr_files = [
        os.path.join(base_path, 'k', 'kotlntss06042026.sdr'),
        os.path.join(base_path, 'n_g', 'plan', 'gro2908_const.sdr'),
        os.path.join(base_path, 'p_l_g', 'plan', 'grocenter (1)_const.sdr'),
        os.path.join(base_path, 'k_n', 'plan', 'ntsskotl06022026_const.sdr'),
        os.path.join(base_path, 'b_g', 'plan', 'badgro16093_const.sdr'),
        os.path.join(base_path, 'b_o', 'plan', 'badokr_const.sdr'),
    ]

    for filepath in sdr_files:
        if os.path.exists(filepath):
            if test_sdr_file(filepath):
                results['SDR']['passed'] += 1
            else:
                results['SDR']['failed'] += 1
        else:
            print(f"\nFile not found: {filepath}")

    # Test GSI files
    gsi_files = [
        os.path.join(base_path, 'n_g', 'niv', 'GRO0109.GSI'),
        os.path.join(base_path, 'p_l_g', 'niv', 'GRO0509.GSI'),
        os.path.join(base_path, 'd_d_k', 'niv', 'KOL0708.GSI'),
        os.path.join(base_path, 'b_g', 'niv', 'GRO2209.GSI'),
        os.path.join(base_path, 's5', 'niv', 'DOM0112 (1).GSI'),
        os.path.join(base_path, 's5', 'niv', 'MIR0212.GSI'),
        os.path.join(base_path, 'd_d_o', 'niv', 'DAY1302.GSI'),
    ]

    for filepath in gsi_files:
        if os.path.exists(filepath):
            if test_gsi_file(filepath):
                results['GSI']['passed'] += 1
            else:
                results['GSI']['failed'] += 1
        else:
            print(f"\nFile not found: {filepath}")

    # Test DAT files
    dat_files = [
        os.path.join(base_path, 's_b', 'niv', 'BOT12210.DAT'),
        os.path.join(base_path, 's_b2', 'niv', 'BOT22110.DAT'),
        os.path.join(base_path, 'l', 'niv', 'LIH2103.DAT'),
    ]

    for filepath in dat_files:
        if os.path.exists(filepath):
            if test_dat_file(filepath):
                results['DAT']['passed'] += 1
            else:
                results['DAT']['failed'] += 1
        else:
            print(f"\nFile not found: {filepath}")

    # Final report
    print_section("FINAL REPORT")
    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total = total_passed + total_failed

    for category, data in results.items():
        print(f"{category}: {data['passed']} passed, {data['failed']} failed")

    print(f"\nTOTAL: {total_passed}/{total} tests passed ({100*total_passed/total:.1f}%)")
    print("=" * 70)

if __name__ == '__main__':
    main()