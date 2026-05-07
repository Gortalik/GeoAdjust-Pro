"""Универсальный парсер офисных форматов (RTF, Excel, CSV)"""
from pathlib import Path
from typing import List
import pandas as pd
from striprtf.striprtf import rtf_to_text
from .base import BaseParser, Observation, ObsType

class OfficeParser(BaseParser):
    """Парсер RTF и Excel/CSV ведомостей"""
    
    def parse(self, file_path: Path) -> List[Observation]:
        """Парсинг офисного файла в список наблюдений"""
        suffix = file_path.suffix.lower()
        
        if suffix == ".rtf":
            return self._parse_rtf(file_path)
        elif suffix in (".xlsx", ".xls", ".csv"):
            return self._parse_spreadsheet(file_path)
        else:
            raise ValueError(f"Неподдерживаемый формат: {suffix}")

    def _parse_rtf(self, path: Path) -> List[Observation]:
        """Парсинг RTF файла"""
        try:
            raw_text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            raw_text = path.read_bytes().decode("cp1251", errors="ignore")
            
        clean_text = rtf_to_text(raw_text)
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        return self._extract_from_lines(lines)

    def _parse_spreadsheet(self, path: Path) -> List[Observation]:
        """Парсинг Excel или CSV файла"""
        try:
            if path.suffix.lower() in (".xlsx", ".xls"):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path, encoding="utf-8")
        except Exception:
            # Попытка с другой кодировкой для CSV
            df = pd.read_csv(path, encoding="cp1251")
        
        # Нормализация имён столбцов
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Поиск нужных столбцов (варианты названий)
        station_col = self._find_column(df, ["станция", "station", "punkt", "punkt_st"])
        target_col = self._find_column(df, ["цель", "target", "vizir", "punkt_target"])
        value_col = self._find_column(df, ["превышение", "dh", "deltah", "heightdiff", "value"])
        dist_col = self._find_column(df, ["расстояние", "distance", "len", "length"], optional=True)
        
        if not all([station_col, target_col, value_col]):
            raise ValueError("Файл не содержит обязательных столбцов: Станция, Цель, Превышение")
        
        observations: List[Observation] = []
        
        for _, row in df.dropna(subset=[station_col, target_col, value_col]).iterrows():
            try:
                value_str = str(row[value_col]).replace(",", ".")
                distance_str = str(row.get(dist_col, 1.0)).replace(",", ".") if dist_col else "1.0"
                
                observations.append(Observation(
                    station_id=str(row[station_col]).strip(),
                    target_id=str(row[target_col]).strip(),
                    value=float(value_str),
                    distance=float(distance_str) if float(distance_str) > 0.1 else 1.0,
                    type=ObsType.LEVELING,
                    setup_id=""
                ))
            except (ValueError, TypeError):
                continue
                
        return observations

    def _find_column(self, df: pd.DataFrame, variants: List[str], optional: bool = False) -> str | None:
        """Поиск столбца по списку возможных названий"""
        for col in df.columns:
            if col in variants:
                return col
        if optional:
            return None
        raise ValueError(f"Не найден столбец среди вариантов: {variants}")

    def _extract_from_lines(self, lines: List[str]) -> List[Observation]:
        """Эвристическое извлечение данных из текстовых строк"""
        observations: List[Observation] = []
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    # Пытаемся найти число в конце строки
                    value_str = parts[-1].replace(",", ".")
                    value = float(value_str)
                    
                    observations.append(Observation(
                        station_id=parts[0],
                        target_id=parts[1] if len(parts) > 1 else "",
                        value=value,
                        distance=1.0,
                        type=ObsType.LEVELING,
                        setup_id=""
                    ))
                except ValueError:
                    continue
                    
        return observations
