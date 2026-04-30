# src/geoadjust/core/network/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal, Tuple
from datetime import datetime

@dataclass
class NetworkPoint:
    point_id: str
    coord_type: Literal['FIXED', 'APPROXIMATE', 'FREE']
    x: float
    y: float
    h: Optional[float]
    # Статусы для плана и высоты (отдельно)
    plan_status: Literal['initial', 'working'] = 'working'  # Статус плановых координат
    height_status: Literal['initial', 'working'] = 'working'  # Статус высотной отметки
    sigma_x_apriori: float = 0.0
    sigma_y_apriori: float = 0.0
    sigma_h_apriori: float = 0.0
    sigma_x: float = 0.0
    sigma_y: float = 0.0
    sigma_h: float = 0.0
    normative_class: Optional[str] = None
    # Географические координаты для работы с геоидом
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def has_plan_coords(self) -> bool:
        """Проверка наличия плановых координат (X, Y)"""
        return self.x is not None and self.y is not None and (self.x != 0.0 or self.y != 0.0)
    
    def has_height(self) -> bool:
        """Проверка наличия высоты (H)"""
        return self.h is not None and self.h != 0.0
    
    def get_approx_xy(self) -> Tuple[Optional[float], Optional[float]]:
        """Получение приближенных плановых координат
        
        Returns:
            Tuple[Optional[float], Optional[float]]: (x, y) координаты или (None, None) если отсутствуют
        """
        if self.has_plan_coords():
            return (self.x, self.y)
        return (None, None)
    
    def get_approx_h(self) -> Optional[float]:
        """Получение приближенной высоты
        
        Returns:
            Optional[float]: Высота или None если отсутствует
        """
        if self.has_height():
            return self.h
        return None
    
    def set_approx_coords(self, x: Optional[float] = None, y: Optional[float] = None, 
                          h: Optional[float] = None, update_status: bool = True) -> bool:
        """Установка приближенных координат
        
        Args:
            x: Плановая координата X
            y: Плановая координата Y
            h: Высота
            update_status: Обновлять ли статус точки на APPROXIMATE
            
        Returns:
            bool: True если координаты были обновлены
        """
        updated = False
        
        if x is not None and self.x != x:
            self.x = x
            updated = True
        
        if y is not None and self.y != y:
            self.y = y
            updated = True
        
        if h is not None and self.h != h:
            self.h = h
            updated = True
        
        # Обновление статуса точки с FREE на APPROXIMATE после вычисления координат
        if update_status and updated and self.coord_type == 'FREE':
            if self.has_plan_coords():
                self.coord_type = 'APPROXIMATE'
        
        return updated

@dataclass
class Observation:
    obs_id: str
    obs_type: Literal['direction', 'distance', 'height_diff', 'zenith_angle', 'azimuth', 'gnss_vector']
    from_setup_id: str      # Привязка к конкретной установке
    from_point_id: str
    to_point_id: str
    value: float
    sigma_apriori: Optional[float] = None
    weight: Optional[float] = None
    face_position: Optional[Literal['CL', 'CP']] = None
    reception_number: Optional[int] = None
    is_active: bool = True
    residual: Optional[float] = None
    raw_line: Optional[str] = None

@dataclass
class InstrumentSetup:
    setup_id: str
    point_id: str
    instrument_name: str
    instrument_height: float
    target_height: float
    orientation_angle: Optional[float] = None
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    timestamp: Optional[datetime] = None
    atmospheric_params: Dict = field(default_factory=dict)
    observations: List[Observation] = field(default_factory=list)
    is_processed: bool = False
    warnings: List[str] = field(default_factory=list)

@dataclass
class CombinedObservation:
    """Объединенное измерение для всей SDR строки (горизонтальный + вертикальный + расстояние)"""
    obs_id: str
    from_setup_id: str
    from_point_id: str
    to_point_id: str
    obs_type: str = 'combined'
    face_position: Optional[Literal['CL', 'CP']] = None
    horizontal_angle: Optional[float] = None
    zenith_angle: Optional[float] = None
    slope_distance: Optional[float] = None
    raw_line: Optional[str] = None
    is_active: bool = True  # Добавлено для совместимости с фильтрацией

    def __post_init__(self):
        # Добавляем поле для совместимости с фильтрацией
        self.from_setup_id = self.from_setup_id


@dataclass
class LevelingSection:
    section_id: str
    start_point: str
    end_point: str
    class_accuracy: Literal['I', 'II', 'III', 'IV', 'technical']
    length_km: float
    stations: List[InstrumentSetup] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    closure_error_mm: Optional[float] = None
    is_compliant: bool = False