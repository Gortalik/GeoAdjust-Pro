#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspace/GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser

parser = SDRParser()
parsed_data = parser.parse('/workspace/test_real_mes/b_g/plan/badgro16093_const.sdr')

observations = parsed_data.get('observations', [])
points_dict = {p['point_id']: p for p in parsed_data.get('points', [])}

print(f"Всего измерений: {len(observations)}")
print(f"Всего пунктов в файле: {len(points_dict)}")

# Проверка - какие точки есть в измерениях но нет в points_dict
missing_points = set()
for obs in observations[:50]:
    if obs.from_point_id not in points_dict:
        missing_points.add(obs.from_point_id)
    if obs.to_point_id not in points_dict:
        missing_points.add(obs.to_point_id)

print(f"\nТочки которых нет в points_dict (из первых 50 измерений): {missing_points}")

# Проверка CombinedObservation
obs = observations[0]
print(f"\nCombinedObservation атрибуты:")
print(f"  directions: {obs.directions if hasattr(obs, 'directions') else 'N/A'}")
print(f"  distances: {obs.distances if hasattr(obs, 'distances') else 'N/A'}")
print(f"  zenit_angles: {obs.zenit_angles if hasattr(obs, 'zenit_angles') else 'N/A'}")
print(f"  horizontal_angles: {obs.horizontal_angles if hasattr(obs, 'horizontal_angles') else 'N/A'}")
