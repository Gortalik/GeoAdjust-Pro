#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальный тест Credo DAT парсера
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

def final_test():
    print("=== Финальный тест Credo DAT парсера ===")
    
    try:
        from geoadjust.io.formats.credo_dat import CredoDATParser
        
        file_path = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
        parser = CredoDATParser()
        
        print(f"Файл существует: {file_path.exists()}")
        
        result = parser.parse(file_path)
        
        print(f"Результат:")
        print(f"  Точек: {len(result['points'])}")
        print(f"  Измерений: {len(result['observations'])}")
        print(f"  Сессий: {len(result['station_sessions'])}")
        
        if result['observations']:
            print(f"  Типы измерений: {set(obs['obs_type'] for obs in result['observations'])}")
            print("  Первые 5 измерений:")
            for i, obs in enumerate(result['observations'][:5]):
                print(f"    {obs['from_point']} -> {obs['to_point']} = {obs['value']:.6f}")
        
        return result
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    final_test()