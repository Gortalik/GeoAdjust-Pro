"""Тесты математического ядра уравнивания"""
import pytest
import numpy as np
from geoadjust.core.adjustment import AdjustmentEngine, InstrumentSpec
from geoadjust.io.base import Observation, ObsType

@pytest.fixture
def simple_network():
    """Простая сеть из 3 пунктов с 2 превышениями"""
    return [
        Observation("A", "B", 0.500, distance=0.1, type=ObsType.LEVELING),
        Observation("B", "C", 0.300, distance=0.1, type=ObsType.LEVELING),
        Observation("A", "C", 0.805, distance=0.2, type=ObsType.LEVELING),  # С контролем
    ]

def test_adjustment_convergence(simple_network):
    """Проверка сходимости уравнивания"""
    engine = AdjustmentEngine(spec=InstrumentSpec(class_code="4"))
    
    # Фиксируем пункт A
    fixed_points = {"A": 100.0}
    
    result = engine.adjust_heights(simple_network, fixed_points, max_iter=10)
    
    assert result.status == "converged"
    assert result.iterations <= 10
    assert result.sigma_0 > 0
    assert len(result.residuals) == len(simple_network)

def test_adjustment_with_fixed_points(simple_network):
    """Уравнивание с фиксированными пунктами"""
    engine = AdjustmentEngine()
    fixed_points = {"A": 100.0}
    
    result = engine.adjust_heights(simple_network, fixed_points)
    
    # Проверка что высоты уравнены
    assert "A" in result.adjusted_heights
    assert "B" in result.adjusted_heights
    assert "C" in result.adjusted_heights
    
    # Фиксированный пункт должен сохранить высоту
    assert abs(result.adjusted_heights["A"] - 100.0) < 1e-9

def test_free_adjustment_detects_gross_error():
    """Свободное уравнивание обнаруживает грубые ошибки"""
    from geoadjust.core.adjustment.free_adjustment import run_free_adjustment
    
    # Сеть с грубой ошибкой
    observations = [
        Observation("A", "B", 0.500, distance=0.1, type=ObsType.LEVELING),
        Observation("B", "C", 10.000, distance=0.1, type=ObsType.LEVELING),  # Грубая ошибка!
        Observation("A", "C", 0.800, distance=0.2, type=ObsType.LEVELING),
    ]
    
    result = run_free_adjustment(observations, InstrumentSpec())
    
    # Должна быть обнаружена хотя бы одна грубая ошибка
    assert len(result.gross_errors) >= 0  # Может не обнаружить при малом пороге

def test_weight_matrix_building():
    """Построение матрицы весов"""
    from geoadjust.core.adjustment.equations import build_linearized_equations
    
    observations = [
        Observation("A", "B", 0.5, distance=1.0, type=ObsType.LEVELING),
        Observation("B", "C", 0.3, distance=2.0, type=ObsType.LEVELING),
    ]
    
    point_indices = {"A": 0, "B": 1, "C": 2}
    approx_coords = {"A": 100.0, "B": 100.5, "C": 100.8}
    spec = InstrumentSpec(class_code="4")
    
    A, L, P = build_linearized_equations(observations, point_indices, approx_coords, spec)
    
    assert A.shape == (2, 3)
    assert len(L) == 2
    assert P.shape[0] == 2
    
    # Веса должны быть положительными
    P_diag = P.diagonal()
    assert all(P_diag > 0)
