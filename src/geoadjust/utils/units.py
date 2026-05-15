"""Утилиты для работы с единицами измерения и безопасного доступа к данным"""
import math
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

# =============================================================================
# КОНВЕРТАЦИЯ ЕДИНИЦ ИЗМЕРЕНИЯ
# =============================================================================

# Константы
RAD2DEG = 180.0 / math.pi
DEG2RAD = math.pi / 180.0
GON2RAD = math.pi / 200.0
SEC2RAD = math.pi / (180.0 * 3600.0)  # Секунды дуги в радианы
RAD2SEC = 1.0 / SEC2RAD  # Радианы в секунды дуги (~206264.806)

def deg2rad(degrees: float) -> float:
    """Градусы → радианы"""
    return degrees * DEG2RAD

def rad2deg(radians: float) -> float:
    """Радианы → градусы"""
    return radians * RAD2DEG

def gon2rad(gons: float) -> float:
    """Грады → радианы"""
    return gons * GON2RAD

def rad2gon(radians: float) -> float:
    """Радианы → грады"""
    return radians * (200.0 / math.pi)

def dms2rad(degrees: int, minutes: int = 0, seconds: float = 0.0) -> float:
    """Градусы/минуты/секунды → радианы"""
    total_deg = degrees + minutes / 60.0 + seconds / 3600.0
    return deg2rad(total_deg)

def rad2dms(radians: float) -> tuple:
    """
    Радианы → Градусы/минуты/секунды
    
    Returns:
        Tuple[int, int, float]: (degrees, minutes, seconds)
    """
    total_deg = rad2deg(radians)
    sign = -1 if total_deg < 0 else 1
    total_deg = abs(total_deg)

    degrees = int(total_deg)
    minutes_total = (total_deg - degrees) * 60.0
    minutes = int(minutes_total)
    seconds = (minutes_total - minutes) * 60.0

    return (sign * degrees, minutes, seconds)

def sec2rad(seconds: float) -> float:
    """Секунды дуги → радианы"""
    return seconds * SEC2RAD

def rad2sec(radians: float) -> float:
    """Радианы → секунды дуги"""
    return radians * RAD2SEC

def meters2mm(meters: float) -> float:
    """Метры → миллиметры"""
    return meters * 1000.0

def mm2meters(mm: float) -> float:
    """Миллиметры → метры"""
    return mm / 1000.0

def km2meters(km: float) -> float:
    """Километры → метры"""
    return km * 1000.0

def meters2km(meters: float) -> float:
    """Метры → километры"""
    return meters / 1000.0


# =============================================================================
# БЕЗОПАСНЫЙ ДОСТУП К ДАННЫМ (dataclass vs dict)
# =============================================================================

def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """
    Универсальный безопасный доступ к атрибутам/ключам.
    
    Работает с:
    - dataclass объектами (через getattr)
    - словарями (через .get())
    - объектами с __getitem__
    
    Args:
        obj: Объект для доступа
        key: Ключ/атрибут
        default: Значение по умолчанию
        
    Returns:
        Значение атрибута/ключа или default
    """
    if obj is None:
        return default

    # Попытка доступа как к атрибуту (dataclass, обычный объект)
    if hasattr(obj, key):
        return getattr(obj, key, default)

    # Попытка доступа как к словарю
    if isinstance(obj, dict):
        return obj.get(key, default)

    # Попытка доступа через __getitem__
    try:
        return obj[key]
    except (TypeError, KeyError, IndexError):
        pass

    return default


def safe_get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Безопасный доступ только к атрибутам объекта"""
    if obj is None:
        return default
    return getattr(obj, key, default)


def safe_get_item(obj: Any, key: Any, default: Any = None) -> Any:
    """Безопасный доступ только к элементам словаря/списка"""
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    try:
        return obj[key]
    except (TypeError, KeyError, IndexError):
        return default


def to_dict(obj: Any) -> Dict:
    """
    Преобразование объекта в словарь.
    
    Поддерживает:
    - dataclass объекты (через asdict)
    - словари (возвращает как есть)
    - объекты с __dict__ атрибутом
    
    Args:
        obj: Объект для преобразования
        
    Returns:
        Словарь с данными объекта
    """
    if obj is None:
        return {}

    if isinstance(obj, dict):
        return obj.copy()

    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)

    if hasattr(obj, '__dict__'):
        return vars(obj).copy()

    return {'value': obj}


def get_obs_value(obs: Any) -> Optional[float]:
    """
    Безопасное получение значения наблюдения.
    
    Работает как с dataclass Observation, так и со словарями.
    
    Args:
        obs: Наблюдение (dataclass или dict)
        
    Returns:
        float или None
    """
    if obs is None:
        return None

    # Пробуем как атрибут
    value = getattr(obs, 'value', None)
    if value is not None:
        return float(value)

    # Пробуем как словарь
    if isinstance(obs, dict):
        return obs.get('value')

    return None


def get_obs_type(obs: Any) -> str:
    """
    Безопасное получение типа наблюдения.
    
    Args:
        obs: Наблюдение (dataclass или dict)
        
    Returns:
        str: Тип наблюдения или 'unknown'
    """
    if obs is None:
        return 'unknown'

    # Для dataclass с Enum типом
    obs_type = getattr(obs, 'type', None)
    if obs_type is not None:
        if hasattr(obs_type, 'value'):  # Enum
            return obs_type.value
        return str(obs_type)

    # Для словаря
    if isinstance(obs, dict):
        return obs.get('type', obs.get('obs_type', 'unknown'))

    return 'unknown'


def get_obs_station(obs: Any) -> str:
    """Безопасное получение имени станции"""
    if obs is None:
        return ''

    station = getattr(obs, 'station_id', None)
    if station is not None:
        return str(station)

    if isinstance(obs, dict):
        return obs.get('station_id', obs.get('from_point', obs.get('from_point_id', '')))

    return ''


def get_obs_target(obs: Any) -> str:
    """Безопасное получение имени целевой точки"""
    if obs is None:
        return ''

    target = getattr(obs, 'target_id', None)
    if target is not None:
        return str(target)

    if isinstance(obs, dict):
        return obs.get('target_id', obs.get('to_point', obs.get('to_point_id', '')))

    return ''
