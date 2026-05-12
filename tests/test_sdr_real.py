#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест SDR парсера на реальных данных
"""

import sys
from pathlib import Path


from geoadjust.io.formats.sdr import SDRParser

if __name__ == "__main__":
    parser = SDRParser()
    result = parser.parse(Path("test_real_mes/b_g/plan/badgro16093_const.sdr"))

    print(f"\nРезультаты SDR парсера:")
    print(f"Точек: {len(result.get('points', []))}")
    print(f"Измерений: {len(result.get('observations', []))}")
    print(f"Установок: {len(result.get('setups', []))}")

    # Подсчет типов измерений
    obs_types = {}
    for obs in result.get('observations', []):
        obs_type = obs.obs_type if hasattr(obs, 'obs_type') else obs.get('obs_type', 'unknown')
        obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

    print(f"Типы измерений: {obs_types}")
    print(f"Ошибок: {len(result.get('errors', []))}")
    print(f"Предупреждений: {len(result.get('warnings', []))}")