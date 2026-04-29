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
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    
    # Статусы для плана и высоты разделяются
    plan_status: str = 'working'  # 'initial', 'fixed', 'working', 'adjusted'
    height_status: str = 'working'  # 'initial', 'fixed', 'working', 'adjusted'
    
    # Дополнительные атрибуты
    code: str = ''
    description: str = ''
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def has_plan_coords(self) -> bool:
        return self.x is not None and self.y is not None
    
    def has_height(self) -> bool:
        return self.z is not None
    
    def is_plan_fixed(self) -> bool:
        return self.plan_status in ['initial', 'fixed']
    
    def is_height_fixed(self) -> bool:
        return self.height_status in ['initial', 'fixed']

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
