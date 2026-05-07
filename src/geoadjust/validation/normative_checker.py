"""Нормативный контроль результатов уравнивания по СП 11-104-97"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from loguru import logger

@dataclass
class LevelingClassSpec:
    """Спецификация класса нивелирования по СП 11-104-97"""
    name: str                   # Название класса (I, II, III, IV, техн.)
    max_sigma_0_mm_per_km: float  # Предельная СКП единицы веса (мм/√км)
    max_closure_mm_per_km: float  # Предельная невязка на 1 км (мм)
    max_point_error_mm: float     # Предельная СКП пункта (мм)

# Нормативные значения для классов нивелирования
CLASS_SPECS = {
    "1": LevelingClassSpec("I", 0.8, 1.0, 0.5),
    "2": LevelingClassSpec("II", 1.2, 2.0, 1.0),
    "3": LevelingClassSpec("III", 3.0, 5.0, 3.0),
    "4": LevelingClassSpec("IV", 5.0, 10.0, 5.0),
    "tech": LevelingClassSpec("Технический", 10.0, 50.0, 10.0),
}

class NormativeChecker:
    """Проверка результатов уравнивания на соответствие нормативам"""
    
    @staticmethod
    def check_leveling_network(
        sigma_0_m: float,
        route_length_km: float,
        closure_m: float,
        point_errors_m: Optional[List[float]] = None,
        class_code: str = "4"
    ) -> Dict:
        """
        Проверка высотной сети на соответствие СП 11-104-97.
        
        Args:
            sigma_0_m: СКП единицы веса (м)
            route_length_km: Длина хода в км
            closure_m: Невязка хода (м)
            point_errors_m: Список СКП пунктов (м)
            class_code: Класс нивелирования (1, 2, 3, 4, tech)
            
        Returns:
            Dict: Результаты проверки с флагами соответствия
        """
        spec = CLASS_SPECS.get(class_code, CLASS_SPECS["4"])
        
        # Расчёт фактических значений
        sigma_0_mm_km = (sigma_0_m * 1000) / max(route_length_km ** 0.5, 0.001)
        closure_mm = closure_m * 1000
        closure_limit_mm = spec.max_closure_mm_per_km * (route_length_km ** 0.5)
        
        # Проверка по пунктам
        point_errors_ok = True
        if point_errors_m:
            point_errors_ok = all(
                e * 1000 <= spec.max_point_error_mm 
                for e in point_errors_m
            )
        
        results = {
            "class_name": spec.name,
            "class_code": class_code,
            "sigma_0_ok": sigma_0_mm_km <= spec.max_sigma_0_mm_per_km,
            "closure_ok": abs(closure_mm) <= closure_limit_mm,
            "point_errors_ok": point_errors_ok,
            "all_ok": (
                results["sigma_0_ok"] and 
                results["closure_ok"] and 
                results["point_errors_ok"]
            ),
            # Детальные значения для отчёта
            "sigma_0_mm_km": round(sigma_0_mm_km, 3),
            "sigma_0_limit_mm_km": spec.max_sigma_0_mm_per_km,
            "closure_mm": round(closure_mm, 2),
            "closure_limit_mm": round(closure_limit_mm, 2),
            "max_point_error_mm": round(max(point_errors_m or [0]) * 1000, 2),
            "point_error_limit_mm": spec.max_point_error_mm,
        }
        
        # Логирование результатов
        status = "✅" if results["all_ok"] else "⚠️"
        logger.info(
            f"{status} Нормативный контроль (Класс {spec.name}): "
            f"σ₀={results['sigma_0_mm_km']} мм/√км (допуск ≤{spec.max_sigma_0_mm_per_km}), "
            f"f={results['closure_mm']} мм (допуск ±{results['closure_limit_mm']})"
        )
        
        return results
    
    @staticmethod
    def get_tolerance_for_class(class_code: str, parameter: str) -> float:
        """
        Получение предельного значения параметра для класса.
        
        Args:
            class_code: Код класса (1, 2, 3, 4, tech)
            parameter: Имя параметра ('sigma_0', 'closure', 'point_error')
            
        Returns:
            float: Предельное значение
        """
        spec = CLASS_SPECS.get(class_code, CLASS_SPECS["4"])
        
        if parameter == "sigma_0":
            return spec.max_sigma_0_mm_per_km
        elif parameter == "closure":
            return spec.max_closure_mm_per_km
        elif parameter == "point_error":
            return spec.max_point_error_mm
        else:
            raise ValueError(f"Неизвестный параметр: {parameter}")
