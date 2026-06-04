"""Парсер POS файлов (обработанные GNSS базовые линии)"""
from pathlib import Path
from typing import Dict
from ..base import BaseParser, Observation, ObsType

class POSParser(BaseParser):
    """Парсер файлов POS с GNSS координатами из RTKPOST"""

    def parse(self, file_path: Path) -> list[Observation]:
        """Парсинг POS файла RTKPOST в список наблюдений"""
        observations = []
        text = self.read_with_fallback(file_path)

        point_coords: Dict[str, list] = {}  # point_id -> list of (x,y,z) tuples

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Пропускаем строки комментариев
            if line.startswith('%'):
                continue

            # Парсинг строки данных: GPST x-ecef(m) y-ecef(m) z-ecef(m) Q ns ...
            # Формат: 2022/02/01 00:59:30.000   4395951.1870   3080707.3092   3433498.3389   1   9   ...
            parts = line.split()
            if len(parts) >= 7:  # Минимум: GPST, x, y, z, Q, ns, ...
                try:
                    # Извлекаем имя точки из пути файла
                    point_name = self._extract_point_name(file_path)

                    x = float(parts[2])  # x-ecef (parts[0]=date, parts[1]=time)
                    y = float(parts[3])  # y-ecef
                    z = float(parts[4])  # z-ecef
                    quality = int(parts[5])  # Q: 1=fix, 2=float, etc.
                    satellites = int(parts[6])  # ns: number of satellites

                    # Используем решения с качеством fix или float и достаточным количеством спутников
                    if quality in [1, 2] and satellites >= 4:
                        if point_name not in point_coords:
                            point_coords[point_name] = []
                        point_coords[point_name].append((x, y, z))

                except (ValueError, IndexError):
                    continue

        # Вычисляем средние координаты для каждой точки
        for point_id, coords_list in point_coords.items():
            if coords_list:
                # Средние координаты
                avg_x = sum(c[0] for c in coords_list) / len(coords_list)
                avg_y = sum(c[1] for c in coords_list) / len(coords_list)
                avg_z = sum(c[2] for c in coords_list) / len(coords_list)

                observations.append(Observation(
                    station_id="GNSS_BASE",
                    target_id=point_id,
                    value=avg_z,  # Высота в ECEF как основное значение
                    distance=1.0,
                    type=ObsType.LEVELING,
                    setup_id=f"gnss_{point_id}",
                    notes=f"GNSS_POS_ECEF epochs={len(coords_list)} x={avg_x:.3f} y={avg_y:.3f} z={avg_z:.3f}"
                ))

        return observations

    def _extract_point_name(self, file_path: Path) -> str:
        """Извлечение имени точки из имени файла"""
        # Например: drag-bshm.pos -> bshm или drag
        name = file_path.stem  # drag-bshm
        parts = name.split('-')
        if len(parts) >= 2:
            # Возвращаем вторую часть как имя точки
            return parts[1]
        else:
            return name