"""Тесты нормативного контроля по СП 11-104-97"""
import pytest
from geoadjust.validation import NormativeChecker

def test_class_iv_network_passes():
    """Сеть IV класса проходит контроль"""
    result = NormativeChecker.check_leveling_network(
        sigma_0_m=0.004,  # 4 мм
        route_length_km=1.0,
        closure_m=0.005,  # 5 мм
        class_code="4"
    )
    
    assert result["sigma_0_ok"] == True
    assert result["closure_ok"] == True
    assert result["all_ok"] == True
    assert result["class_name"] == "IV"

def test_class_iv_network_fails_sigma():
    """Сеть не проходит по σ₀"""
    result = NormativeChecker.check_leveling_network(
        sigma_0_m=0.010,  # 10 мм - слишком много для IV класса
        route_length_km=1.0,
        closure_m=0.005,
        class_code="4"
    )
    
    assert result["sigma_0_ok"] == False
    assert result["all_ok"] == False

def test_get_tolerance_for_class():
    """Получение допусков для классов"""
    assert NormativeChecker.get_tolerance_for_class("1", "sigma_0") == 0.8
    assert NormativeChecker.get_tolerance_for_class("4", "sigma_0") == 5.0
    assert NormativeChecker.get_tolerance_for_class("tech", "sigma_0") == 10.0
