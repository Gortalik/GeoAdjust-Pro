"""Базовый тест для проверки импорта и базовой функциональности"""
import pytest
from pathlib import Path

def test_import_geoadjust():
    """Проверка что пакет geoadjust импортируется корректно"""
    from geoadjust import AdjustmentEngine, InstrumentSpec, ObsType, Observation
    assert AdjustmentEngine is not None
    assert InstrumentSpec is not None

def test_adjustment_engine_creation():
    """Создание движка уравнивания"""
    from geoadjust.core.adjustment import AdjustmentEngine, InstrumentSpec
    
    spec = InstrumentSpec(class_code="4")
    engine = AdjustmentEngine(spec=spec)
    
    assert engine.spec.class_code == "4"
    assert len(engine.point_indices) == 0

def test_weight_calculation():
    """Проверка расчёта весов по СП 11-104-97"""
    from geoadjust.core.adjustment.weights import calculate_weight, ObsType, InstrumentSpec
    
    # Нивелирование IV класса, 1 км
    w = calculate_weight(ObsType.LEVELING, 0.005, distance=1.0, spec=InstrumentSpec(class_code="4"))
    assert w > 0
    assert w < 1e7  # Вес должен быть в разумных пределах
    
    # Более точное нивелирование → больший вес
    w_class1 = calculate_weight(ObsType.LEVELING, 0.005, distance=1.0, spec=InstrumentSpec(class_code="1"))
    assert w_class1 > w  # I класс точнее IV

def test_observation_model():
    """Проверка модели наблюдения"""
    from geoadjust.io.base import Observation, ObsType
    
    obs = Observation(
        station_id="ST1",
        target_id="ST2",
        value=0.123,
        distance=50.0,
        type=ObsType.LEVELING
    )
    
    assert obs.station_id == "ST1"
    assert obs.target_id == "ST2"
    assert abs(obs.value - 0.123) < 1e-6
    assert obs.type == ObsType.LEVELING
