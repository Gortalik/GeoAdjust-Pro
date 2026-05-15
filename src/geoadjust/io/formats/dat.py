"""Парсер DAT файлов (бинарные данные нивелирования)"""
import struct
from pathlib import Path
from typing import Optional
from ..base import BaseParser, Observation, ObsType


class DATParser(BaseParser):
    """Парсер бинарных DAT файлов с данными нивелирования"""

    def __init__(self):
        self.records = []

    def parse(self, file_path: Path) -> list[Observation]:
        """Парсинг DAT файла в список наблюдений"""
        observations = []

        try:
            with open(file_path, 'rb') as f:
                # Читаем заголовок (предполагаем 4 байта - количество записей)
                header = f.read(4)
                if len(header) < 4:
                    return observations

                num_records = struct.unpack('<I', header)[0]  # little-endian unsigned int

                # Читаем записи
                for _ in range(min(num_records, 10000)):  # Ограничение для безопасности
                    record = self._read_record(f)
                    if record:
                        self.records.append(record)
                    else:
                        break

            # Конвертируем записи в наблюдения
            observations = self._build_observations()

        except Exception:
            # Если бинарный парсинг не удался, пробуем текстовый
            try:
                return self._parse_text_dat(file_path)
            except Exception:
                pass

        return observations

    def _read_record(self, f) -> Optional[dict[str, float]]:
        """Чтение одной записи из бинарного файла"""
        try:
            # Предполагаем структуру записи:
            # station_id (32 байта string), target_id (32 байта string),
            # height_diff (double), distance (double)
            record_size = 32 + 32 + 8 + 8  # 80 байт

            data = f.read(record_size)
            if len(data) != record_size:
                return None

            station_bytes = data[0:32].rstrip(b'\x00')
            target_bytes = data[32:64].rstrip(b'\x00')
            height_diff = struct.unpack('<d', data[64:72])[0]  # little-endian double
            distance = struct.unpack('<d', data[72:80])[0]     # little-endian double

            station_id = station_bytes.decode('utf-8', errors='ignore').strip()
            target_id = target_bytes.decode('utf-8', errors='ignore').strip()

            if not station_id or not target_id:
                return None

            return {
                'station_id': station_id,
                'target_id': target_id,
                'height_diff': height_diff,
                'distance': distance if distance > 0.01 else 1.0
            }

        except Exception:
            return None

    def _parse_text_dat(self, file_path: Path) -> list[Observation]:
        """Парсинг DAT файла как текстового"""
        observations = []
        text = self.read_with_fallback(file_path)

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Предполагаем формат: station_id target_id height_diff [distance]
            parts = line.split()
            if len(parts) >= 3:
                try:
                    station_id = parts[0]
                    target_id = parts[1]
                    height_diff = float(parts[2])
                    distance = float(parts[3]) if len(parts) > 3 else 1.0

                    observations.append(Observation(
                        station_id=station_id,
                        target_id=target_id,
                        value=height_diff,
                        distance=distance,
                        type=ObsType.LEVELING,
                        setup_id=f"dat_{len(observations)+1}"
                    ))
                except (ValueError, IndexError):
                    continue

        return observations

    def _build_observations(self) -> list[Observation]:
        """Построение наблюдений из записей"""
        observations = []

        for record in self.records:
            observations.append(Observation(
                station_id=record['station_id'],
                target_id=record['target_id'],
                value=record['height_diff'],
                distance=record['distance'],
                type=ObsType.LEVELING,
                setup_id=f"dat_{len(observations)+1}"
            ))

        return observations
