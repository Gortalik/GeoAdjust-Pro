"""Парсер Trimble/Sokkia SDR с группировкой по InstrumentSetup"""
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base import BaseParser, Observation, ObsType

class SDRParser(BaseParser):
    """Парсер файлов SDR (Trimble/Sokkia) с валидацией setup'ов
    
    Поддерживает два формата:
    1. Sokkia (| разделители): KD1 R2 с Rb/Rf и Z в отдельных строках
    2. Стандартный SDR: Station:/Target:/HeightDiff:/Distance:
    """
    
    def __init__(self):
        self.current_setup: str = ""
        self.current_station: Optional[str] = None
        self.current_target: Optional[str] = None
        self.pending_data: Dict[str, Any] = {}
        self.setup_counter: int = 0
    
    def parse(self, file_path: Path) -> List[Observation]:
        """Парсинг SDR файла в список наблюдений"""
        text = self.read_with_fallback(file_path)
        observations: List[Observation] = []
        
        # Сброс состояния
        self.current_setup = ""
        self.current_station = None
        self.pending_data = {}
        self.setup_counter = 0
        
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Проверяем формат Sokkia (с | разделителями)
            # Важно: проверяем всю строку на наличие 'Adr', а не только первую часть
            if '|' in line and 'Adr' in line:
                obs = self._parse_sokkia_line(line, lines, i)
                if obs:
                    observations.append(obs)
            # Стандартный SDR формат
            elif ':' in line:
                self._parse_standard_sdr_line(line, observations)
            
            i += 1
        
        return observations
    
    def _parse_sokkia_line(self, line: str, all_lines: List[str], current_idx: int) -> Optional[Observation]:
        """Парсинг строки формата Sokkia (| разделители)
        
        Формат Sokkia использует последовательность:
        1. Строка с KD1 + R2 + Rb (задняя рейка) - начало станции
        2. Строка с KD1 + V1 + Rf (передняя рейка) - цель
        3. Строка с KD1 + V1 + Z (превышение между R2 и V1) - создание наблюдения
        
        Логика:
        - При Rb запоминаем станцию
        - При Rf запоминаем цель
        - При Z (без Rb/Rf) создаем наблюдение Station→Target с этим превышением
        """
        parts = line.split('|')
        if len(parts) < 3:
            return None
        
        # Проверяем наличие 'Adr' во всей строке (не только в header_part)
        if 'Adr' not in line:
            return None
        
        header_part = parts[0]
        
        # Извлекаем номер секции (BF 1, BF 2 и т.д.) из ВСЕЙ строки
        bf_match = re.search(r'BF\s+(\d+)', line)
        if bf_match:
            section_num = bf_match.group(1)
            if not self.current_setup:
                self.current_setup = f"section_{section_num}"
                self.setup_counter = int(section_num)
        
        # Парсим основную часть (колонка 3): KD1 <PointName> ...
        measure_part = parts[2].strip() if len(parts) > 2 else ""
        
        # Парсим Z поле (колонка 6) - это готовое превышение
        z_part = parts[5].strip() if len(parts) > 5 else ""
        z_match = re.search(r'Z\s+([+-]?\d+\.?\d*)\s*m', z_part)
        z_value = float(z_match.group(1)) if z_match else None
        
        # Парсим HD поле (колонка 5) - расстояние
        hd_part = parts[4].strip() if len(parts) > 4 else ""
        hd_match = re.search(r'HD\s+(\d+\.?\d*)\s*m', hd_part)
        hd_value = float(hd_match.group(1)) if hd_match else 1.0
        
        # Извлекаем имя точки из measure_part
        measure_tokens = measure_part.split()
        if not measure_tokens:
            return None
        
        # Пропускаем KD1, берем имя точки
        if measure_tokens[0] == 'KD1' and len(measure_tokens) > 1:
            point_name = measure_tokens[1]
        else:
            point_name = measure_tokens[0]
        
        # Пропускаем служебные записи
        if point_name in ('TO', 'Reading', 'Intermediate', 'End'):
            return None
        
        # Проверяем тип измерения по второй колонке (Rb, Rf, Rz и т.д.)
        rb_rf_part = parts[3].strip() if len(parts) > 3 else ""
        
        # Определяем тип точки по наличию Rb/Rf/Z
        has_rb = 'Rb' in rb_rf_part
        has_rf = 'Rf' in rb_rf_part
        has_z = z_value is not None
        
        # Логика обработки:
        # 1. Rb → запоминаем станцию
        # 2. Rf → запоминаем цель  
        # 3. Z без Rb/Rf → создаем наблюдение
        
        if has_rb:
            # Задняя рейка - это новая станция
            self.current_station = point_name
            self.pending_data['last_hd'] = hd_value
            return None
            
        elif has_rf:
            # Передняя рейка - запоминаем цель
            self.current_target = point_name
            self.pending_data['last_hd'] = hd_value
            return None
            
        elif has_z and not has_rb and not has_rf:
            # Строка с Z но без Rb/Rf - создаем наблюдение
            if self.current_station and self.current_target:
                obs = Observation(
                    station_id=self.current_station,
                    target_id=self.current_target,
                    value=z_value,
                    distance=self.pending_data.get('last_hd', hd_value) if hd_value > 0.1 else 1.0,
                    type=ObsType.LEVELING,
                    setup_id=self.current_setup or f"setup_{self.setup_counter}"
                )
                # Сброс после создания наблюдения
                self.current_station = None
                self.current_target = None
                self.pending_data.clear()
                return obs
            return None
        
        return None
    
    def _parse_standard_sdr_line(self, line: str, observations: List[Observation]):
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
                self.pending_data['height'] = float(line.split(":", 1)[1].strip())
            except ValueError:
                self.pending_data['height'] = None
        elif line_lower.startswith("distance:"):
            try:
                dist = float(line.split(":", 1)[1].strip())
                self.pending_data['distance'] = dist if dist > 0.1 else 1.0
                
                # Создаем наблюдение если все данные собраны
                if (self.current_station and 
                    self.current_target and 
                    self.pending_data.get('height') is not None):
                    
                    observations.append(Observation(
                        station_id=self.current_station,
                        target_id=self.current_target,
                        value=self.pending_data['height'],
                        distance=self.pending_data.get('distance', 1.0),
                        type=ObsType.LEVELING,
                        setup_id=self.current_setup
                    ))
                    # Сброс
                    self.current_target = None
                    self.pending_data.pop('height', None)
                    self.pending_data.pop('distance', None)
            except ValueError:
                pass
