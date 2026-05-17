"""Парсер Leica GSI — исправленная версия без ошибок UnboundLocal"""
import re
from pathlib import Path
from typing import List, Optional
from ..base import BaseParser, Observation, ObsType


class GSIParser(BaseParser):
    BLOCK_PATTERN = re.compile(r'(\d{2,3})\.{1,3}(\d{1,2})([+-])(\d+)')

    def parse(self, file_path: Path) -> List[Observation]:
        text = self.read_with_fallback(file_path)
        observations: List[Observation] = []
        points = {}

        for line in text.splitlines():
            line = line.strip()
            if not line.startswith('11'):
                continue

            # Извлекаем ID точки
            m = re.search(r'\+([A-Za-z0-9.]+)', line)
            if not m:
                continue
            point_id = m.group(1)

            # Парсим измерения
            measurements = {}
            for match in self.BLOCK_PATTERN.finditer(line):
                code = match.group(1)
                dec = int(match.group(2))
                sign = match.group(3)
                val = int(match.group(4))
                measurements[code] = float(sign + str(val)) / (10 ** dec)

            if point_id not in points:
                points[point_id] = {'measurements': {}, 'codes': set()}

            points[point_id]['measurements'].update(measurements)
            points[point_id]['codes'].update(measurements.keys())

        # Строим наблюдения (только нивелирование)
        sorted_points = sorted(points.keys())
        prev = None
        for pid in sorted_points:
            data = points[pid]
            codes = data['codes']
            meas = data['measurements']

            if '333' in codes and not any(c in codes for c in ['573', '574']):
                continue  # боковая точка

            dh = meas.get('573') or meas.get('571') or meas.get('574') or meas.get('572')
            dist = meas.get('331') or meas.get('332') or meas.get('335') or meas.get('336') or 0.1

            if prev is not None and dh is not None:
                observations.append(Observation(
                    station_id=prev,
                    target_id=pid,
                    value=dh,
                    distance=dist,
                    type=ObsType.LEVELING,
                    setup_id='lev'
                ))
            prev = pid

        return observations
