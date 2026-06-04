"""Парсер Sokkia SDR33 с данными тахеометра"""
import re
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from ..base import BaseParser, Observation, ObsType

class SDRParser(BaseParser):
    """Парсер файлов SDR33 с данными тахеометра согласно спецификации"""

    def __init__(self):
        self.stations: Dict[str, Dict] = {}  # station_id -> station data
        self.points: Dict[str, Dict] = {}    # point_id -> point coordinates
        self.measurements: List[Dict] = []   # list of measurements

    def parse(self, file_path: Path) -> list[Observation]:
        """Парсинг SDR33 файла в список наблюдений"""
        text = self.read_with_fallback(file_path)
        observations: list[Observation] = []

        self.stations = {}
        self.points = {}
        self.measurements = []

        for line in text.splitlines():
            line = line.strip()
            if len(line) < 4:  # Минимум ID + код источника
                continue

            record_type = line[:2]
            source_code = line[2:4]

            # Парсинг разных типов записей
            if record_type == '02' and source_code == 'TP':
                # Запись станции: 02TP Nst X Y H i Code
                self._parse_station_record(line)
            elif record_type == '08' and source_code in ['KI', 'TP']:
                # Запись координат: 08xx Np X Y H Code
                self._parse_coordinate_record(line)
            elif record_type == '09' and source_code in ['F1', 'F2']:
                # Запись измерения: 09Fx Nst Np D B R Code
                self._parse_measurement_record(line)

        # Конвертируем данные в наблюдения
        observations = self._build_observations()

        return observations

    def _parse_station_record(self, line: str):
        """Парсинг записи станции: 02TP Nst X Y H i Code"""
        try:
            # Позиции согласно спецификации
            station_name = line[4:20].strip()   # поз. 5-20
            northing = float(line[20:36].strip())  # поз. 21-36 (X - север)
            easting = float(line[36:52].strip())   # поз. 37-52 (Y - восток)
            elevation = float(line[52:68].strip()) # поз. 53-68 (H - высота)
            instrument_height = float(line[68:84].strip()) # поз. 69-84 (i - высота инструмента)
            code = line[84:100].strip()           # поз. 85-100

            self.stations[station_name] = {
                'northing': northing,
                'easting': easting,
                'elevation': elevation,
                'instrument_height': instrument_height,
                'code': code
            }
        except (ValueError, IndexError):
            pass

    def _parse_coordinate_record(self, line: str):
        """Парсинг записи координат: 08xx Np X Y H Code"""
        try:
            point_name = line[4:20].strip()      # поз. 5-20
            northing = float(line[20:36].strip())   # поз. 21-36 (X - север)
            easting = float(line[36:52].strip())    # поз. 37-52 (Y - восток)
            elevation = float(line[52:68].strip())  # поз. 53-68 (H - высота)
            code = line[68:84].strip()              # поз. 69-84

            self.points[point_name] = {
                'northing': northing,
                'easting': easting,
                'elevation': elevation,
                'code': code
            }
        except (ValueError, IndexError):
            pass

    def _parse_measurement_record(self, line: str):
        """Парсинг записи измерения: 09Fx Nst Np D B R Code"""
        try:
            station_name = line[4:20].strip()      # поз. 5-20
            target_name = line[20:36].strip()      # поз. 21-36
            distance = float(line[36:52].strip())  # поз. 37-52 (D - наклонное расстояние)
            vert_angle = float(line[52:68].strip()) # поз. 53-68 (B - вертикальный угол)
            horiz_reading = float(line[68:84].strip()) # поз. 69-84 (R - отсчет по гориз. кругу)
            code = line[84:100].strip()            # поз. 85-100

            self.measurements.append({
                'station': station_name,
                'target': target_name,
                'distance': distance,
                'vert_angle': vert_angle,
                'horiz_reading': horiz_reading,
                'code': code
            })
        except (ValueError, IndexError):
            pass

    def _build_observations(self) -> list[Observation]:
        """Создание наблюдений из всех собранных данных"""
        observations = []

        # 1. Наблюдения из координат точек (если есть станции, можно создать относительные измерения)
        for point_name, point_data in self.points.items():
            # Если есть станции, можно создать измерения от станции к точке
            # Пока создаем простые наблюдения координат
            observations.append(Observation(
                station_id="SDR_BASE",
                target_id=point_name,
                value=point_data['elevation'],  # Высота
                distance=1.0,
                type=ObsType.LEVELING,
                setup_id=f"sdr_coord_{point_name}",
                notes=f"SDR33_COORD N={point_data['northing']:.3f} E={point_data['easting']:.3f} H={point_data['elevation']:.3f}"
            ))

        # 2. Наблюдения из измерений тахеометра
        for meas in self.measurements:
            # Добавляем три типа наблюдений: дистанция, вертикальный угол, горизонтальный угол
            # 1) Дистанция (наклонное расстояние) – тип DISTANCE
            observations.append(Observation(
                station_id=meas['station'],
                target_id=meas['target'],
                value=meas['distance'],
                distance=meas['distance'],
                type=ObsType.DISTANCE,
                setup_id=f"sdr_dist_{meas['station']}_{meas['target']}",
                notes=f"SDR33_DIST D={meas['distance']:.3f}"
            ))
            # 2) Вертикальный угол – тип ANGLE_V (в радианах)
            observations.append(Observation(
                station_id=meas['station'],
                target_id=meas['target'],
                value=meas['vert_angle'],
                distance=meas['distance'],
                type=ObsType.ANGLE_V,
                setup_id=f"sdr_vert_{meas['station']}_{meas['target']}",
                notes=f"SDR33_VERT B={meas['vert_angle']:.4f}"
            ))
            # 3) Горизонтальный угол – тип ANGLE_HZ (в градусах)
            observations.append(Observation(
                station_id=meas['station'],
                target_id=meas['target'],
                value=meas['horiz_reading'],
                distance=meas['distance'],
                type=ObsType.ANGLE_HZ,
                setup_id=f"sdr_hz_{meas['station']}_{meas['target']}",
                notes=f"SDR33_HZ R={meas['horiz_reading']:.4f}"
            ))
            # При желании добавить высотную разность (примерная) как уровень
            try:
                vert_angle_rad = meas['vert_angle'] * 3.14159 / 180.0
                elevation_diff = meas['distance'] * np.sin(vert_angle_rad)
                observations.append(Observation(
                    station_id=meas['station'],
                    target_id=meas['target'],
                    value=elevation_diff,
                    distance=meas['distance'],
                    type=ObsType.LEVELING,
                    setup_id=f"sdr_lev_{meas['station']}_{meas['target']}",
                    notes=f"SDR33_LEV diff={elevation_diff:.3f}"
                ))
            except Exception:
                pass

        return observations
