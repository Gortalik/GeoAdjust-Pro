"""Парсер Leica GSI (GSI16/GSI8) с поддержкой фиксированной ширины записей"""
import re
from pathlib import Path
from typing import List, Optional
from .base import BaseParser, Observation, ObsType

# Карта Word ID Leica GSI для основных типов наблюдений
GSI_WORD_MAP = {
    "81": ObsType.LEVELING,      # Превышение
    "82": ObsType.DISTANCE,      # Наклонное расстояние  
    "83": ObsType.ANGLE_HZ,      # Горизонтальный угол/направление
    "84": ObsType.ANGLE_V,       # Вертикальный угол
}

class GSIParser(BaseParser):
    """Парсер файлов Leica GSI с автоматическим определением кодировки"""
    
    def __init__(self):
        self.current_station: Optional[str] = None
        self.current_target: Optional[str] = None
        self.current_distance: float = 1.0
        self.setup_counter: int = 0
    
    def parse(self, file_path: Path) -> List[Observation]:
        """Парсинг GSI файла в список наблюдений"""
        text = self.read_with_fallback(file_path)
        observations: List[Observation] = []
        
        # Сброс состояния
        self.current_station = None
        self.current_target = None
        self.current_distance = 1.0
        self.setup_counter = 0
        
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        for line in lines:
            # Пропускаем строки не начинающиеся с цифры или спецсимвола GSI
            if not line or (not line[0].isdigit() and line[0] not in "+-"):
                continue
            
            # Извлекаем Word ID (формат XX.. или XX..YY)
            word_match = re.match(r"^(\d{2})\.\.([0-9A-Fa-f]*)", line)
            if not word_match:
                continue
                
            word_id = word_match.group(1)
            
            # Извлекаем значение после пробела
            value_match = re.search(r"\s+([+-]?\d*\.?\d+)", line)
            if not value_match:
                continue
            
            try:
                value = float(value_match.group(1))
            except ValueError:
                continue
            
            # Обработка по типу Word ID
            if word_id == "31" or word_id == "32":  # Имя точки или код
                # Новая станция если target ещё не установлен
                if self.current_target is None:
                    self.current_station = value_match.group(1).strip()
                    self.setup_counter += 1
                else:
                    self.current_target = value_match.group(1).strip()
                    self.current_distance = 1.0  # Сброс расстояния
                    
            elif word_id == "81":  # Превышение
                if self.current_station and self.current_target:
                    observations.append(Observation(
                        station_id=self.current_station,
                        target_id=self.current_target,
                        value=value,
                        distance=self.current_distance,
                        type=ObsType.LEVELING,
                        setup_id=f"setup_{self.setup_counter}"
                    ))
                    
            elif word_id == "82":  # Расстояние
                self.current_distance = abs(value) if abs(value) > 0.1 else 1.0
                
            elif word_id in GSI_WORD_MAP:
                # Угловые измерения (пока игнорируем для нивелирования)
                pass
        
        return observations
