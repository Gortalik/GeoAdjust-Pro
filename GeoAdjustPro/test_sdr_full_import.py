#!/usr/bin/env python3
import sys

from geoadjust.io.formats.sdr import SDRParser
from geoadjust.gui.dialogs.import_dialog import ImportDialog
from geoadjust.core.network.models import CombinedObservation
from pathlib import Path

# Имитируем импорт SDR файла
print("Testing SDR import process...")

# Шаг 1: Парсим файл
parser = SDRParser()
result = parser.parse(Path('../test_real_mes/b_g/plan/badgro16093_const.sdr'))
print(f"Parsed: {len(result['observations'])} observations")

# Шаг 2: Имитируем import_dialog._import_sdr
data = result
observations = []
for obs in data.get('observations', []):
    # Оставляем как объекты (как мы исправили)
    if hasattr(obs, 'horizontal_angle') or hasattr(obs, 'zenith_angle') or hasattr(obs, 'slope_distance'):
        observations.append(obs)

print(f"After import_dialog: {len(observations)} observations")

# Шаг 3: Имитируем добавление в проект (конвертация в словари)
project_observations = []
for obs in observations[:3]:  # Только первые 3 для теста
    from dataclasses import asdict
    obs_dict = asdict(obs)
    print(f"Converted to dict: keys={list(obs_dict.keys())}, horizontal_angle={obs_dict.get('horizontal_angle')}")
    project_observations.append(obs_dict)

# Шаг 4: Имитируем извлечение из проекта и конвертацию обратно
def convert_observations_to_objects(observations):
    converted_observations = []
    for obs in observations:
        if isinstance(obs, dict) and 'horizontal_angle' in obs and 'zenith_angle' in obs and 'slope_distance' in obs:
            combined_obs = CombinedObservation(
                obs_id=obs.get('obs_id', ''),
                from_setup_id=obs.get('from_setup_id', ''),
                from_point_id=obs.get('from_point_id', ''),
                to_point_id=obs.get('to_point_id', ''),
                face_position=obs.get('face_position'),
                horizontal_angle=obs.get('horizontal_angle'),
                zenith_angle=obs.get('zenith_angle'),
                slope_distance=obs.get('slope_distance'),
                raw_line=obs.get('raw_line')
            )
            converted_observations.append(combined_obs)
    return converted_observations

converted_obs = convert_observations_to_objects(project_observations)
print(f"After conversion back: {len(converted_obs)} observations")

# Шаг 5: Имитируем отображение в таблице
for obs in converted_obs:
    print(f"Observation: {type(obs)}, from_point_id={obs.from_point_id}, horizontal_angle={obs.horizontal_angle}")