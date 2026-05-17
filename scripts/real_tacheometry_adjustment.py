#!/usr/bin/env python3
"""
Уравнивание реальной тахеометрической сети (SDR).
Фиксируем одну станцию + азимут.
"""

import sys
from pathlib import Path
import numpy as np
import os

sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.sdr import SDRParser


def adjust_real_tacheometry(file_path: Path):
    print("\n" + "="*75)
    print(f"УРАВНИВАНИЕ РЕАЛЬНОЙ ТАХЕОМЕТРИЧЕСКОЙ СЕТИ (SDR)")
    print(f"Файл: {file_path.name}")
    print("="*75)

    parser = SDRParser()
    data = parser.parse(file_path)

    points = data.get('points', [])
    obs = data.get('observations', [])

    print(f"Пунктов: {len(points)}")
    print(f"Измерений: {len(obs)}")

    if len(points) < 2 or len(obs) < 2:
        print("Слишком мало данных")
        return

    # Берём первую станцию как исходную
    fixed_station = points[0]['name'] if 'name' in points[0] else points[0].get('point_id', 'P001')
    print(f"\nИсходная станция: {fixed_station}")

    # Для демонстрации просто показываем статистику
    print(f"\n=== ГОТОВО К УРАВНИВАНИЮ ===")
    print(f"Тип: Тахеометрическая сеть (горизонтальные углы + расстояния)")
    print(f"Фиксация: 1 станция + 1 исходный азимут")
    print(f"Измерений, участвующих в уравнивании: {len(obs)}")

    print(f"\nПервые 5 пунктов:")
    for p in points[:5]:
        name = p.get('name', p.get('point_id', '???'))
        x = p.get('x', 0)
        y = p.get('y', 0)
        print(f"  {name:12s}  X={x:10.3f}  Y={y:10.3f}")

    print(f"\n[ДЕМО] Сеть успешно загружена и готова к МНК уравниванию")


if __name__ == "__main__":
    base = Path("test_real_mes")
    f = base / "b_g" / "plan" / "badgro16093_const.sdr"
    adjust_real_tacheometry(f)
