"""Базовые классы и модели данных для импорта наблюдений"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List


class ObsType(Enum):
    """Типы геодезических наблюдений"""
    LEVELING = "leveling"        # Нивелирование (превышение)
    DISTANCE = "distance"        # Расстояние
    ANGLE_HZ = "angle_hz"        # Горизонтальный угол
    ANGLE_V = "angle_v"          # Вертикальный угол
    DIRECTION = "direction"      # Направление

@dataclass
class Observation:
    """Модель геодезического наблюдения"""
    station_id: str              # Имя станции
    target_id: str               # Имя целевой точки
    value: float                 # Измеренное значение (м, рад)
    distance: float = 1.0        # Длина хода/линии (для веса)
    type: ObsType = ObsType.LEVELING
    setup_id: str = ""           # ID инструмента/станции
    notes: str = ""              # Примечания

class BaseParser(ABC):
    """Абстрактный базовый класс для всех парсеров"""

    @abstractmethod
    def parse(self, file_path: Path) -> List[Observation]:
        """Парсинг файла измерений в список Observation"""
        pass

    @staticmethod
    def read_with_fallback(path: Path, encodings=("utf-8", "cp1251", "latin-1")) -> str:
        """Чтение файла с автоматическим подбором кодировки"""
        for enc in encodings:
            try:
                return path.read_text(encoding=enc, errors="ignore")
            except Exception:
                continue
        raise ValueError(f"Не удалось прочитать {path.name} в поддерживаемых кодировках")
