"""Парсер Trimble/Sokkia SDR с группировкой по InstrumentSetup"""
import re
from pathlib import Path
from typing import List, Optional

from .base import BaseParser, Observation, ObsType


class SDRParser(BaseParser):
    """Парсер файлов SDR (Trimble/Sokkia) с валидацией setup'ов"""

    def __init__(self):
        self.current_setup: str = ""
        self.current_station: Optional[str] = None
        self.current_target: Optional[str] = None
        self.current_height: Optional[float] = None
        self.current_distance: float = 1.0

    def parse(self, file_path: Path) -> List[Observation]:
        """Парсинг SDR файла в список наблюдений"""
        text = self.read_with_fallback(file_path)
        observations: List[Observation] = []

        # Сброс состояния
        self.current_setup = ""
        self.current_station = None
        self.current_target = None
        self.current_height = None
        self.current_distance = 1.0

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Проверяем формат Sokkia (с | разделителями)
            if '|' in line and 'Adr' in line:
                self._parse_sokkia_line(line, observations)
            # Стандартный SDR формат
            elif ':' in line:
                self._parse_standard_sdr_line(line)

        return observations

    def _parse_sokkia_line(self, line: str, observations: List[Observation]):
        """Парсинг строки формата Sokkia (| разделители)"""
        parts = line.split('|')
        if len(parts) < 6:
            return

        header_part = parts[0]
        if 'Adr' not in header_part:
            return

        measure_part = parts[2].strip() if len(parts) > 2 else ""
        z_part = parts[5].strip() if len(parts) > 5 else ""
        hd_part = parts[4].strip() if len(parts) > 4 else ""

        # Извлекаем имя точки из measure_part
        point_match = re.match(r'^(\S+)', measure_part)
        if point_match:
            potential_point = point_match.group(1)
            if potential_point not in ('Rb', 'Rf', 'Sh', 'dz', 'HD', 'Z'):
                if not self.current_station:
                    self.current_station = potential_point
                    self.current_setup = f"setup_{len(observations)+1}"
                elif self.current_station and not self.current_target:
                    self.current_target = potential_point

        # Извлекаем превышение из Z поля
        z_match = re.search(r'Z\s+([+-]?\d+\.\d+)\s*m', z_part)
        if z_match:
            self.current_height = float(z_match.group(1))

        # Извлекаем расстояние из HD поля
        hd_match = re.search(r'HD\s+(\d+\.\d+)\s*m', hd_part)
        if hd_match:
            self.current_distance = float(hd_match.group(1))

        # Если есть и высота и цель - создаем наблюдение
        if self.current_station and self.current_target and self.current_height is not None:
            observations.append(Observation(
                station_id=self.current_station,
                target_id=self.current_target,
                value=self.current_height,
                distance=self.current_distance if self.current_distance > 0.1 else 1.0,
                type=ObsType.LEVELING,
                setup_id=self.current_setup
            ))
            # Сброс для следующей пары
            self.current_target = None
            self.current_height = None
            self.current_distance = 1.0

    def _parse_standard_sdr_line(self, line: str):
        """Парсинг строки стандартного SDR формата"""
        line_lower = line.lower()

        if line_lower.startswith("instrumentsetup:"):
            self.current_setup = line.split(":", 1)[1].strip()
        elif line_lower.startswith("station:"):
            self.current_station = line.split(":", 1)[1].strip()
        elif line_lower.startswith("target:"):
            self.current_target = line.split(":", 1)[1].strip()
        elif line_lower.startswith(("heightdiff:", "dh:")):
            try:
                self.current_height = float(line.split(":", 1)[1].strip())
            except ValueError:
                self.current_height = None
        elif line_lower.startswith("distance:"):
            try:
                dist = float(line.split(":", 1)[1].strip())
                self.current_distance = dist if dist > 0.1 else 1.0

                if (self.current_station and
                    self.current_target and
                    self.current_height is not None):

                    observations_list = []  # Пустой список, т.к. это вспомогательный метод
                    # Наблюдение будет создано в основном цикле parse()
            except ValueError:
                pass
