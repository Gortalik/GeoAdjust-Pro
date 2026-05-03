"""
Расширенная поддержка систем координат РФ
Дополнение к существующему CRS модулю GeoAdjustPro
"""

import numpy as np
from typing import Dict, Tuple, Optional
import json
from pathlib import Path

class RussianCRS:
    """Расширенная поддержка систем координат Российской Федерации"""

    # Параметры эллипсоидов
    ELLIPSOIDS = {
        'Красовского': {
            'a': 6378245.0,      # Большая полуось
            'b': 6356863.019,    # Малая полуось
            'f': 1/298.3         # Сжатие
        },
        'WGS84': {
            'a': 6378137.0,
            'b': 6356752.3142,
            'f': 1/298.257223563
        }
    }

    # Параметры зон Гаусса-Крюгера для РФ
    GK_ZONES_RF = {
        # Формат: номер зоны -> (центральный меридиан, ложный восток)
        4: (21, 400000),
        5: (27, 500000),
        6: (33, 600000),
        7: (39, 700000),
        8: (45, 800000),
        9: (51, 900000),
        10: (57, 1000000),
        11: (63, 1100000),
        12: (69, 1200000),
        13: (75, 1300000),
        14: (81, 1400000),
        15: (87, 1500000),
        16: (93, 1600000),
        17: (99, 1700000),
        18: (105, 1800000),
        19: (111, 1900000),
    }

    # Системы координат РФ
    COORDINATE_SYSTEMS = {
        'СК-42': {
            'ellipsoid': 'Красовского',
            'epoch': 1942,
            'description': 'Система координат 1942 года'
        },
        'СК-95': {
            'ellipsoid': 'Красовского',
            'epoch': 1995,
            'description': 'Система координат 1995 года'
        },
        'ГСК-2011': {
            'ellipsoid': 'Красовского',
            'epoch': 2011,
            'description': 'Геодезическая система координат 2011 года'
        },
        'МСК': {
            'ellipsoid': 'Красовского',
            'epoch': 2011,
            'description': 'Местные системы координат'
        }
    }

    def __init__(self):
        self.current_ellipsoid = 'Красовского'
        self.current_system = 'СК-42'

    def set_coordinate_system(self, system_name: str) -> bool:
        """Установка системы координат"""
        if system_name in self.COORDINATE_SYSTEMS:
            self.current_system = system_name
            self.current_ellipsoid = self.COORDINATE_SYSTEMS[system_name]['ellipsoid']
            return True
        return False

    def get_ellipsoid_parameters(self, ellipsoid_name: str = None) -> Dict:
        """Получение параметров эллипсоида"""
        name = ellipsoid_name or self.current_ellipsoid
        return self.ELLIPSOIDS.get(name, self.ELLIPSOIDS['Красовского'])

    def geographic_to_gauss_kruger(self, lat: float, lon: float, zone: int) -> Tuple[float, float]:
        """
        Преобразование географических координат в Гаусса-Крюгера

        Параметры:
        - lat, lon: широта и долгота в градусах
        - zone: номер зоны (4-19 для РФ)

        Возвращает:
        - (x, y): координаты в метрах
        """
        if zone not in self.GK_ZONES_RF:
            raise ValueError(f"Неверный номер зоны: {zone}")

        # Параметры эллипсоида
        ell = self.get_ellipsoid_parameters()
        a = ell['a']
        b = ell['b']
        e2 = (a**2 - b**2) / a**2  # Квадрат эксцентриситета

        # Центральный меридиан зоны
        lon0 = self.GK_ZONES_RF[zone][0]

        # Преобразование в радианы
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)
        lon0_rad = np.radians(lon0)

        # Разность долгот
        dlon = lon_rad - lon0_rad

        # Параметры проекции
        N = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)  # Радиус кривизны первого вертикала

        # Коэффициенты ряда
        A = (dlon**2) * N * np.sin(lat_rad) * np.cos(lat_rad) / 2
        B = (dlon**4) * N * np.sin(lat_rad) * np.cos(lat_rad)**3 * (5 - np.tan(lat_rad)**2 + 9*e2*np.cos(lat_rad)**2 + 4*e2**2*np.cos(lat_rad)**4) / 24
        C = (dlon**6) * N * np.sin(lat_rad) * np.cos(lat_rad)**5 * (61 - 58*np.tan(lat_rad)**2 + np.tan(lat_rad)**4) / 720

        # Северное смещение (координата X)
        x = 6367558.4968 * lat_rad - 16036.4803 * np.sin(2*lat_rad) + 16.8281 * np.sin(4*lat_rad) - 0.022 * np.sin(6*lat_rad)

        # Восточное смещение (координата Y)
        y = N * np.cos(lat_rad) * dlon * (1 + A + B + C)

        # Добавление ложного востока
        y += self.GK_ZONES_RF[zone][1]

        return x, y

    def gauss_kruger_to_geographic(self, x: float, y: float, zone: int) -> Tuple[float, float]:
        """
        Преобразование координат Гаусса-Крюгера в географические

        Параметры:
        - x, y: координаты в метрах
        - zone: номер зоны

        Возвращает:
        - (lat, lon): широта и долгота в градусах
        """
        if zone not in self.GK_ZONES_RF:
            raise ValueError(f"Неверный номер зоны: {zone}")

        # Параметры эллипсоида
        ell = self.get_ellipsoid_parameters()
        a = ell['a']
        b = ell['b']
        e2 = (a**2 - b**2) / a**2

        # Удаление ложного востока
        y -= self.GK_ZONES_RF[zone][1]
        lon0 = self.GK_ZONES_RF[zone][0]

        # Приближенная широта
        lat_rad = x / 6367558.4968

        # Итеративное уточнение широты
        for _ in range(5):
            N = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)
            lat_rad = (x + 16036.4803 * np.sin(2*lat_rad) - 16.8281 * np.sin(4*lat_rad) + 0.022 * np.sin(6*lat_rad)) / 6367558.4968

        # Вычисление долготы
        N = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)
        t = np.tan(lat_rad)
        eta2 = e2 * np.cos(lat_rad)**2 / (1 - e2)

        lon_rad = lon0 + (y / (N * np.cos(lat_rad))) * (1 - (y**2)/(2*(N*np.cos(lat_rad))**2) * (1 + eta2) + (y**4)/(24*(N*np.cos(lat_rad))**4) * (5 + 3*t**2 + 6*eta2*(1 - t**2) - 6*eta2))

        return np.degrees(lat_rad), np.degrees(lon_rad)

    def transform_coordinates(self, x: float, y: float, from_zone: int, to_zone: int) -> Tuple[float, float]:
        """
        Преобразование координат между зонами Гаусса-Крюгера

        Параметры:
        - x, y: координаты в метрах
        - from_zone, to_zone: номера зон

        Возвращает:
        - (x_new, y_new): преобразованные координаты
        """
        # Преобразование в географические координаты
        lat, lon = self.gauss_kruger_to_geographic(x, y, from_zone)

        # Преобразование в новую зону
        x_new, y_new = self.geographic_to_gauss_kruger(lat, lon, to_zone)

        return x_new, y_new

    def get_zone_from_longitude(self, lon: float) -> int:
        """Определение номера зоны по долготе"""
        # Для РФ: зоны с 4 по 19, каждая 6 градусов
        zone = int((lon + 3) // 6) + 1

        # Ограничение диапазона для РФ
        return max(4, min(19, zone))

    def get_available_systems(self) -> Dict:
        """Получение списка доступных систем координат"""
        return self.COORDINATE_SYSTEMS.copy()

    def get_zone_info(self, zone: int) -> Optional[Dict]:
        """Получение информации о зоне"""
        if zone in self.GK_ZONES_RF:
            lon0, false_easting = self.GK_ZONES_RF[zone]
            return {
                'zone': zone,
                'central_meridian': lon0,
                'false_easting': false_easting,
                'longitude_range': f"{lon0-3}° to {lon0+3}°"
            }
        return None

def demonstrate_rf_crs():
    """Демонстрация работы с системами координат РФ"""
    crs = RussianCRS()

    print("=== СИСТЕМЫ КООРДИНАТ РФ ===")
    for name, info in crs.get_available_systems().items():
        print(f"{name}: {info['description']} (эпоха {info['epoch']})")

    print("\n=== ЗОНЫ ГАУССА-КРЮГЕРА ===")
    for zone in range(4, 20):
        info = crs.get_zone_info(zone)
        if info:
            print(f"Зона {zone}: центральный меридиан {info['central_meridian']}°, ложный восток {info['false_easting']}м")

    # Пример преобразования
    print("\n=== ПРИМЕР ПРЕОБРАЗОВАНИЯ ===")
    lat, lon = 55.7558, 37.6176  # Москва
    zone = crs.get_zone_from_longitude(lon)

    print(f"Географические координаты Москвы: {lat}°, {lon}°")
    print(f"Определена зона: {zone}")

    # Преобразование в Гаусса-Крюгера
    x, y = crs.geographic_to_gauss_kruger(lat, lon, zone)
    print(f"Координаты в Гауссе-Крюгере (зона {zone}): X={x:.2f}м, Y={y:.2f}м")

    # Обратное преобразование
    lat2, lon2 = crs.gauss_kruger_to_geographic(x, y, zone)
    print(f"Обратное преобразование: {lat2:.6f}°, {lon2:.6f}°")
    print(f"Разница: {(lat2-lat)*3600:.2f}\", {(lon2-lon)*3600:.2f}\"")

if __name__ == "__main__":
    demonstrate_rf_crs()