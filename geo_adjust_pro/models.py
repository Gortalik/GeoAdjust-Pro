"""
Модели данных для GeoAdjustPro
Совместимы с парсерами GSI/SDR и движком уравнивания
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class NetworkPoint:
    """Пункт геодезической сети"""
    id: str
    name: str = None  # Alias для id
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    h: Optional[float] = None  # Alias для z
    
    # Статусы для плана и высоты разделяются
    plan_status: str = 'working'  # 'initial', 'fixed', 'working', 'adjusted'
    height_status: str = 'working'  # 'initial', 'fixed', 'working', 'adjusted'
    
    # Дополнительные атрибуты
    code: str = ''
    description: str = ''
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.name is None:
            self.name = self.id
        if self.h is not None and self.z is None:
            self.z = self.h
        if self.z is not None and self.h is None:
            self.h = self.z
    
    @property
    def X(self):
        return self.x
    
    @property
    def Y(self):
        return self.y
    
    @property
    def H(self):
        return self.h or self.z

@dataclass
class Observation:
    """Геодезическое измерение"""
    id: str
    type: str  # 'distance', 'angle', 'direction', 'leveling_height_diff', 'zenith_angle'
    from_point: str
    to_point: Optional[str] = None
    value: float = 0.0
    distance: float = 0.0  # Для нивелирования - длина хода
    angle: Optional[float] = None
    zenith_angle: Optional[float] = None
    
    # Метаданные
    instrument_height: Optional[float] = None
    target_height: Optional[float] = None
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    time: str = ''
    date: str = ''
    
    # Статус обработки
    status: str = 'raw'  # 'raw', 'corrected', 'rejected'
    residual: Optional[float] = None
    weight: float = 1.0
    
    # Исходные данные из файла
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.id is None:
            self.id = f"obs_{id(self)}"

@dataclass
class NetworkData:
    """Контейнер для всей сети"""
    points: Dict[str, NetworkPoint] = field(default_factory=dict)
    observations: List[Observation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_point(self, point: NetworkPoint):
        self.points[point.id] = point
    
    def add_observation(self, obs: Observation):
        self.observations.append(obs)
    
    def merge_data(self, other: 'NetworkData'):
        """Объединение данных из другой сети"""
        for pid, point in other.points.items():
            if pid not in self.points:
                self.points[pid] = point
            else:
                existing = self.points[pid]
                if point.x is not None:
                    existing.x = point.x
                if point.y is not None:
                    existing.y = point.y
                if point.h is not None or point.z is not None:
                    existing.h = point.h or point.z
                    existing.z = existing.h
                if point.plan_status in ['fixed', 'initial']:
                    existing.plan_status = point.plan_status
                if point.height_status in ['fixed', 'initial']:
                    existing.height_status = point.height_status
        for obs in other.observations:
            self.observations.append(obs)

    def get_point(self, point_id: str) -> Optional[NetworkPoint]:
        return self.points.get(point_id)
    
    def get_observations_for_point(self, point_id: str) -> List[Observation]:
        return [obs for obs in self.observations 
                if obs.from_point == point_id or obs.to_point == point_id]
    
    def get_leveling_observations(self) -> List[Observation]:
        return [obs for obs in self.observations if obs.type == 'leveling_height_diff']
    
    def get_distance_observations(self) -> List[Observation]:
        return [obs for obs in self.observations if obs.type == 'distance']
    
    def count_points_by_status(self, status_type: str = 'plan') -> Dict[str, int]:
        """Подсчет точек по статусам"""
        counts = {'initial': 0, 'fixed': 0, 'working': 0, 'adjusted': 0}
        for point in self.points.values():
            if status_type == 'plan':
                status = point.plan_status
            else:
                status = point.height_status
            if status in counts:
                counts[status] += 1
        return counts

# Alias для совместимости
Network = NetworkData
