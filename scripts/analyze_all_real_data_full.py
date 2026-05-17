#!/usr/bin/env python3
"""
Полное исследование ВСЕХ реальных данных (GSI + SDR + DAT).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.sdr import SDRParser
from geoadjust.io.formats.dat import DATParser

def analyze_all_real_data():
    base = Path("test_real_mes")

    gsi_files = list(base.rglob("*.GSI"))
    sdr_files = list(base.rglob("*.sdr")) + list(base.rglob("*.SDR"))
    dat_files = list(base.rglob("*.DAT")) + list(base.rglob("*.dat"))

    print("=" * 90)
    print("ПОЛНОЕ ИССЛЕДОВАНИЕ ВСЕХ РЕАЛЬНЫХ ДАННЫХ (GSI + SDR + DAT)")
    print("=" * 90)
    print(f"GSI файлов: {len(gsi_files)}")
    print(f"SDR файлов: {len(sdr_files)}")
    print(f"DAT файлов: {len(dat_files)}")
    print()

    # GSI
    parser_gsi = GSIParser()
    for f in sorted(gsi_files):
        try:
            data = parser_gsi.parse(f)
            print(f"[GSI] {f.relative_to(base)}: {len(data.get('points', []))} пунктов, {len(data.get('observations', []))} измерений")
        except Exception as e:
            print(f"[GSI] {f.name}: ERROR - {e}")

    print()

    # SDR
    parser_sdr = SDRParser()
    for f in sorted(sdr_files):
        try:
            data = parser_sdr.parse(f)
            print(f"[SDR] {f.relative_to(base)}: {len(data.get('points', []))} пунктов, {len(data.get('observations', []))} измерений")
        except Exception as e:
            print(f"[SDR] {f.name}: ERROR - {e}")

    print()

    # DAT
    parser_dat = DATParser()
    for f in sorted(dat_files):
        try:
            data = parser_dat.parse(f)
            print(f"[DAT] {f.relative_to(base)}: {len(data.get('points', []))} пунктов, {len(data.get('observations', []))} измерений")
        except Exception as e:
            print(f"[DAT] {f.name}: ERROR - {e}")

    print()
    print("=" * 90)
    print("Анализ завершён")
    print("=" * 90)

if __name__ == "__main__":
    analyze_all_real_data()
