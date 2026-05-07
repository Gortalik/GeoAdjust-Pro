"""Парсер Trimble/Sokkia SDR с группировкой по InstrumentSetup"""
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
            if not line or line.startswith("#"):
                continue
            
            line_lower = line.lower()
            
            # Парсинг по ключевым словам SDR
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
                    
                    # Если есть все данные - создаём наблюдение
                    if (self.current_station and 
                        self.current_target and 
                        self.current_height is not None):
                        
                        observations.append(Observation(
                            station_id=self.current_station,
                            target_id=self.current_target,
                            value=self.current_height,
                            distance=self.current_distance,
                            type=ObsType.LEVELING,
                            setup_id=self.current_setup or f"setup_{len(observations)}"
                        ))
                        
                        # Сброс после создания наблюдения
                        self.current_height = None
                        self.current_target = None
                        
                except ValueError:
                    pass
                    
            elif line_lower.startswith(("note:", "comment:")):
                pass  # Игнорируем комментарии
        
        return observations
