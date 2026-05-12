#!/usr/bin/env python3
"""
Отладка: посмотрим на нормализованные точки и измерения
"""

import sys
import os

from pathlib import Path
from geoadjust.io.formats.gsi import GSIParser
from geoadjust.core.adjustment.data_adapter import DataAdapter

def debug_normalized_data():
    """Посмотрим на нормализованные данные"""

    gsi_file = Path("test_real_mes/s5/niv/DOM0112 (1).GSI")

    parser = GSIParser()
    result = parser.parse(gsi_file)

    raw_points = result.get('points', [])
    raw_observations = result.get('observations', [])

    print(f"Сырые точки: {len(raw_points)}")
    for i, p in enumerate(raw_points[:5]):
        print(f"  {i+1}: {p}")

    points_dict, observations = DataAdapter.normalize_project_data(raw_points, raw_observations)

    print(f"\nНормализованные точки: {len(points_dict)}")
    for i, (pid, point) in enumerate(list(points_dict.items())[:10]):
        print(f"  {pid}: x={point.x}, y={point.y}, h={point.h}, coord_type={point.coord_type}")

    print(f"\nНормализованные измерения: {len(observations)}")
    for i, obs in enumerate(observations[:5]):
        print(f"  {i+1}: {obs.obs_type} от {obs.from_point_id} к {obs.to_point_id}, значение={obs.value}")

if __name__ == '__main__':
    debug_normalized_data()