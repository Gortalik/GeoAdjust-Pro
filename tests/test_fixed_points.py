#!/usr/bin/env python3
"""
Тест уравнивания с правильными фиксированными точками
"""
from pathlib import Path
from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.sdr import SDRParser
from geoadjust.processing_pipeline import ProcessingPipeline
from geoadjust.core.processing_context import ProcessingContext

def test_nivelirovanie():
    """Тест нивелирования - задать любой ходовой пункт за 0"""
    print("=" * 60)
    print("ТЕСТ НИВЕЛИРОВАНИЯ")
    print("=" * 60)

    parser = GSIParser()
    obs = parser.parse(Path('test_real_mes/b_g/niv/GRO2209.GSI'))

    print(f"Загружено: {len(obs)} наблюдений")

    # Для нивелирования - задать любой ходовой пункт за 0
    # Используем первую станцию как 0
    stations = sorted(set(o.station_id for o in obs))
    fixed = {stations[0]: 0.0}  # Первый пункт за 0

    print(f"Фиксированные точки: {fixed}")

    ctx = ProcessingContext(observations=obs, fixed_points=fixed, config={})
    pipeline = ProcessingPipeline()
    result = pipeline.run(ctx)

    print(f"Статус: {result.status}")
    print(f"Валидация: {result.validation_report}")

    return result

def test_planovye():
    """Тест плановых данных - пункт за 0,0 и дирекционный угол"""
    print("\n" + "=" * 60)
    print("ТЕСТ ПЛАНОВЫХ ДАННЫХ (SDR)")
    print("=" * 60)

    parser = SDRParser()
    obs = parser.parse(Path('test_real_mes/b_g/plan/badgro16093_const.sdr'))

    print(f"Загружено: {len(obs)} наблюдений")

    # Для плановых - выбрать измерения между станциями
    # Задать один пункт за 0,0 и дирекционный угол за 0 на другую станцию
    points = sorted(set(o.target_id for o in obs if o.target_id))
    if len(points) >= 2:
        fixed = {
            points[0]: 0.0,  # Первый пункт за 0,0
            # Дирекционный угол за 0 на вторую станцию
        }
    else:
        fixed = {points[0]: 0.0}

    print(f"Фиксированные точки: {fixed}")

    ctx = ProcessingContext(observations=obs, fixed_points=fixed, config={})
    pipeline = ProcessingPipeline()
    result = pipeline.run(ctx)

    print(f"Статус: {result.status}")
    print(f"Валидация: {result.validation_report}")

    return result

if __name__ == "__main__":
    test_nivelirovanie()
    test_planovye()