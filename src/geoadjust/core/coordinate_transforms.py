"""Координатные преобразования и векторы для геодезической сети"""
import numpy as np
from typing import Tuple, Dict
from dataclasses import dataclass

@dataclass
class GeodeticPoint:
    """Геодетическая точка в разных системах координат"""
    point_id: str
    # WGS84
    latitude: float = 0.0
    longitude: float = 0.0  
    height: float = 0.0
    # SK42/MSK (Московская)
    x_sk42: float = 0.0
    y_sk42: float = 0.0
    # Балтийская высотная система
    height_baltic: float = 0.0
    
def wgs84_to_moscow(lat: float, lon: float, height: float) -> Tuple[float, float, float]:
    """
    Примерная трансформация WGS84 → Московская СК
    Для реальных преобразований нужны точные параметры трансформации
    """
    # Это упрощенное преобразование - для реальной работы нужны точные параметры
    # Здесь используем приближенные значения для демонстрации
    # В реальных проектах использовать точные параметры трансформации
    
    # Приближенные параметры для московской системы координат
    x_moscow = 9471.778 + (lon - 37.559521691) * 111320 * np.cos(np.radians(lat))
    y_moscow = 3852.404 + (lat - 55.752065013) * 111320
    h_moscow = height
    
    return x_moscow, y_moscow, h_moscow

def baltic_to_moscow_height(h_baltic: float, correction: float = -0.09) -> float:
    """Преобразование высот из Балтийской в Московскую систему"""
    return h_baltic + correction

def create_pos_vector_observation(point_id: str, point_name: str, 
                                x: float, y: float, z: float,
                                base_x: float, base_y: float, base_z: float) -> dict:
    """Создает наблюдение-вектор из POS координат"""
    dx = x - base_x
    dy = y - base_y  
    dz = z - base_z
    
    return {
        'station_id': point_name,
        'target_id': point_id,
        'dx': dx,
        'dy': dy,
        'dz': dz,
        'x': x,
        'y': y,
        'z': z,
        'base_x': base_x,
        'base_y': base_y,
        'base_z': base_z
    }

def calculate_vector_uncertainty(distance: float, angle_uncertainty: float = 0.001) -> Tuple[float, float, float]:
    """
    Рассчитывает СКП вектора на основе расстояния и СКП углов
    """
    # Примерные расчеты СКП вектора
    sigma_x = distance * angle_uncertainty * np.sin(np.radians(1))
    sigma_y = distance * angle_uncertainty * np.cos(np.radians(1))
    sigma_z = distance * angle_uncertainty * 0.5  # Высотная компонента обычно меньше
    
    return sigma_x, sigma_y, sigma_z