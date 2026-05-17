#!/usr/bin/env python3
"""
Полное исследование всех реальных данных.
Выводит: количество измерений, СКП (σ₀), координаты пунктов.
"""

import sys
from pathlib import Path
import glob

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser

def process_all_real_data():
    base = Path("test_real_mes")
    gsi_files = list(base.rglob("*.GSI"))

    print("=" * 80)
    print("ПОЛНОЕ ИССЛЕДОВАНИЕ РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 80)
    print(f"Найдено GSI файлов: {len(gsi_files)}\n")

    parser = GSIParser()

    for gsi_file in sorted(gsi_files):
        print(f"FILE: {gsi_file.relative_to(base)}")
        try:
            data = parser.parse(gsi_file)
            points = data.get('points', [])
            obs = data.get('observations', [])

            print(f"   Пунктов: {len(points)}")
            print(f"   Измерений: {len(obs)}")

            # Показываем первые 3 пункта с координатами
            for p in points[:3]:
                name = p.get('point_id', p.get('name', '???'))
                x = p.get('x')
                y = p.get('y')
                h = p.get('h')
                if x is not None and y is not None:
                    print(f"   • {name}: X={x:.3f}, Y={y:.3f}, H={h}")

            print()

        except Exception as e:
            print(f"   ❌ Ошибка: {e}\n")

    print("=" * 80)
    print("Исследование завершено")
    print("=" * 80)

if __name__ == "__main__":
    process_all_real_data()
