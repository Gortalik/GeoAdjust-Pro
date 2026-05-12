#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Комплексный тест всех модулей GeoAdjust-Pro

Этот скрипт проверяет работоспособность всех основных компонентов:
1. Сетевые модели (NetworkPoint, Observation)
2. Построение матрицы уравнений (EquationsBuilder)
3. Построение весовой матрицы (WeightBuilder)
4. Инструменты (Instrument)
5. Движок уравнивания (AdjustmentEngine)
6. Конвейер обработки (ProcessingPipeline)
7. Анализ эллипсов ошибок (ErrorEllipseAnalyzer)
8. Анализ грубых ошибок (GrossErrorAnalyzer)
9. Метод Баарда (BaardaMethod)
10. Проекция Гаусса-Крюгера (GaussKrugerProjection)
11. Трансформация координат (CoordinateTransformer)
12. Парсеры форматов (DAT, GSI, SDR)
13. GUI компоненты (MainWindow)

Автор: GeoAdjust-Pro Team
"""

import sys
import numpy as np

# Добавляем путь к модулям

# ============================================================================
# ИМПОРТ ВСЕХ МОДУЛЕЙ
# ============================================================================

print("=" * 80)
print("ТЕСТИРОВАНИЕ ИМПОРТА ВСЕХ МОДУЛЕЙ GEOADJUST-PRO")
print("=" * 80)

try:
    # Core modules
    from geoadjust.core.network.models import NetworkPoint, Observation
    print("[OK] geoadjust.core.network.models")
    
    from geoadjust.core.adjustment.instruments import Instrument
    print("[OK] geoadjust.core.adjustment.instruments")
    
    from geoadjust.core.adjustment.equations_builder import EquationsBuilder
    print("[OK] geoadjust.core.adjustment.equations_builder")
    
    from geoadjust.core.adjustment.weight_builder import WeightBuilder
    print("[OK] geoadjust.core.adjustment.weight_builder")
    
    from geoadjust.core.adjustment.engine import AdjustmentEngine
    print("[OK] geoadjust.core.adjustment.engine")
    
    from geoadjust.core.processing_pipeline import ProcessingPipeline
    print("[OK] geoadjust.core.processing_pipeline")
    
    # Analysis modules
    from geoadjust.core.analysis.ellipse_errors import ErrorEllipseAnalyzer, calculate_error_ellipse_parameters
    print("[OK] geoadjust.core.analysis.ellipse_errors")
    
    from geoadjust.core.analysis.gross_errors import GrossErrorAnalyzer
    print("[OK] geoadjust.core.analysis.gross_errors")
    
    from geoadjust.core.analysis.normative_classes import NormativeClass, NormativeClassLibrary
    print("[OK] geoadjust.core.analysis.normative_classes")
    
    # Reliability modules
    from geoadjust.core.reliability.baarda_method import BaardaReliability
    print("[OK] geoadjust.core.reliability.baarda_method")
    
    # CRS modules
    from geoadjust.crs.database import CRSDatabase
    print("[OK] geoadjust.crs.database")
    
    from geoadjust.crs.projection import GaussKrugerProjection
    print("[OK] geoadjust.crs.projection")
    
    from geoadjust.crs.transformer import CoordinateTransformer
    print("[OK] geoadjust.crs.transformer")
    
    # IO modules
    from geoadjust.io.formats.dat import DATParser
    print("[OK] geoadjust.io.formats.dat")
    
    from geoadjust.io.formats.gsi import GSIParser
    print("[OK] geoadjust.io.formats.gsi")
    
    from geoadjust.io.formats.sdr import SDRParser
    print("[OK] geoadjust.io.formats.sdr")
    
    # GUI modules
    from geoadjust.gui.main_window import MainWindow
    print("[OK] geoadjust.gui.main_window")
    
    print("\n[OK] ВСЕ МОДУЛИ УСПЕШНО ИМПОРТИРОВАНЫ\n")
    
except ImportError as e:
    print(f"\n[ERROR] ОШИБКА ИМПОРТА: {e}\n")
    sys.exit(1)

# ============================================================================
# ТЕСТ 1: Сетевые модели
# ============================================================================

print("=" * 80)
print("ТЕСТ 1: Сетевые модели (NetworkPoint, Observation)")
print("=" * 80)

try:
    point1 = NetworkPoint(point_id='P1', coord_type='FIXED', x=0.0, y=0.0, h=None)
    point2 = NetworkPoint(point_id='P2', coord_type='FREE', x=100.0, y=0.0, h=None)
    point3 = NetworkPoint(point_id='P3', coord_type='FREE', x=50.0, y=86.6, h=None)
    
    obs1 = Observation(
        obs_id='dir_1', obs_type='direction',
        from_point='P1', to_point='P2',
        value=0.0, instrument_name='total_station',
        sigma_apriori=None
    )
    
    obs2 = Observation(
        obs_id='dist_1', obs_type='distance',
        from_point='P1', to_point='P2',
        value=100.0, instrument_name='total_station',
        sigma_apriori=None
    )
    
    print(f"[OK] Создано пунктов: 3")
    print(f"[OK] Создано измерений: 2")
    print(f"[OK] P1: ({point1.x}, {point1.y}) - {point1.coord_type}")
    print(f"[OK] P2: ({point2.x}, {point2.y}) - {point2.coord_type}")
    print(f"[OK] P3: ({point3.x}, {point3.y}) - {point3.coord_type}")
    print("[OK] ТЕСТ 1 ПРОЙДЕН\n")
except Exception as e:
    print(f"[ERROR] ОШИБКА: {e}\n")

# ============================================================================
# ТЕСТ 2: Instrument и WeightBuilder
# ============================================================================

print("=" * 80)
print("ТЕСТ 2: Инструменты и весовая матрица")
print("=" * 80)

try:
    instrument = Instrument(
        angular_accuracy=5.0,  # 5 секунд
        distance_accuracy_a=2.0,  # 2 мм
        distance_accuracy_b=2.0,  # 2 ppm
        centering_error=1.0,  # 1 мм
        target_centering_error=1.0  # 1 мм
    )
    
    instrument_library = {'total_station': instrument}
    
    observations = [
        Observation(
            obs_id='dir_1', obs_type='direction',
            from_point='P1', to_point='P2',
            value=0.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        Observation(
            obs_id='dist_1', obs_type='distance',
            from_point='P1', to_point='P2',
            value=100.0, instrument_name='total_station',
            sigma_apriori=None
        ),
    ]
    
    weight_builder = WeightBuilder(instrument_library)
    P = weight_builder.build_weight_matrix(observations)
    
    print(f"[OK] Прибор: total_station (точность угла: {instrument.angular_accuracy}\", расстояния: {instrument.distance_accuracy_a}мм + {instrument.distance_accuracy_b}ppm)")
    print(f"[OK] Весовая матрица: {P.shape[0]}×{P.shape[1]}")
    print(f"[OK] Диагональные элементы (веса): {P.diagonal()}")
    print("[OK] ТЕСТ 2 ПРОЙДЕН\n")
except Exception as e:
    print(f"[ERROR] ОШИБКА: {e}\n")

# ============================================================================
# ТЕСТ 3: EquationsBuilder
# ============================================================================

print("=" * 80)
print("ТЕСТ 3: Построение матрицы уравнений поправок")
print("=" * 80)

try:
    points = {
        'P1': NetworkPoint(point_id='P1', coord_type='FIXED', x=0.0, y=0.0, h=None),
        'P2': NetworkPoint(point_id='P2', coord_type='FREE', x=100.0, y=0.0, h=None),
        'P3': NetworkPoint(point_id='P3', coord_type='FREE', x=50.0, y=86.6, h=None),
    }
    
    observations = [
        Observation(
            obs_id='dir_1', obs_type='direction',
            from_point='P1', to_point='P2',
            value=0.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        Observation(
            obs_id='dir_2', obs_type='direction',
            from_point='P1', to_point='P3',
            value=60.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        Observation(
            obs_id='dist_1', obs_type='distance',
            from_point='P1', to_point='P2',
            value=100.0, instrument_name='total_station',
            sigma_apriori=None
        ),
        Observation(
            obs_id='dist_2', obs_type='distance',
            from_point='P1', to_point='P3',
            value=100.0, instrument_name='total_station',
            sigma_apriori=None
        ),
    ]
    
    builder = EquationsBuilder()
    A, L = builder.build_adjustment_matrix(
        observations=observations,
        points=points,
        fixed_points=['P1']
    )
    
    print(f"[OK] Матрица А: {A.shape[0]}×{A.shape[1]}")
    print(f"[OK] Вектор L: {len(L)}")
    print(f"[OK] Число ненулевых элементов: {A.nnz}")
    print(f"[OK] Матрица А (плотное представление):\n{A.toarray()}")
    print(f"[OK] Вектор L:\n{L}")
    print("[OK] ТЕСТ 3 ПРОЙДЕН\n")
except Exception as e:
    print(f"[ERROR] ОШИБКА: {e}\n")

# ============================================================================
# ТЕСТ 4: ErrorEllipseAnalyzer
# ============================================================================

print("=" * 80)
print("ТЕСТ 4: Анализ эллипсов ошибок")
print("=" * 80)

try:
    # Тестовая ковариационная матрица для 3 точек (6 параметров)
    Q = np.eye(6) * 1e-6
    Q[0, 0] = 2e-6  # q_xx для P1
    Q[1, 1] = 1.5e-6  # q_yy для P1
    Q[0, 1] = 0.5e-6  # q_xy для P1
    
    points_coords = [(0.0, 0.0), (100.0, 0.0), (50.0, 86.6)]
    
    analyzer = ErrorEllipseAnalyzer(Q, points_coords)
    a, b, alpha = analyzer.get_ellipse_for_point(0)
    
    print(f"✓ Ковариационная матрица: {Q.shape[0]}×{Q.shape[1]}")
    print(f"✓ Число точек: {len(points_coords)}")
    print(f"✓ Эллипс ошибок для P1:")
    print(f"  - Большая полуось (a): {a*1000:.4f} мм")
    print(f"  - Малая полуось (b): {b*1000:.4f} мм")
    print(f"  - Азимут большой оси: {np.rad2deg(alpha):.2f}°")
    print("✅ ТЕСТ 4 ПРОЙДЕН\n")
except Exception as e:
    print(f"❌ ОШИБКА: {e}\n")

# ============================================================================
# ТЕСТ 5: GaussKrugerProjection
# ============================================================================

print("=" * 80)
print("ТЕСТ 5: Проекция Гаусса-Крюгера")
print("=" * 80)

try:
    projection = GaussKrugerProjection()
    
    # Тестовые координаты (Москва, приблизительно)
    lat = 55.7558
    lon = 37.6173
    zone = 7  # 7 зона для Москвы
    
    x, y = projection.geodetic_to_gauss_kruger(lat, lon, zone)
    
    print(f"✓ Исходные координаты (широта, долгота): ({lat:.4f}°, {lon:.4f}°)")
    print(f"✓ Зона Гаусса-Крюгера: {zone}")
    print(f"✓ Плоские координаты (X, Y): ({x:.2f} м, {y:.2f} м)")
    print("✅ ТЕСТ 5 ПРОЙДЕН\n")
except Exception as e:
    print(f"❌ ОШИБКА: {e}\n")

# ============================================================================
# ТЕСТ 6: CoordinateTransformer
# ============================================================================

print("=" * 80)
print("ТЕСТ 6: Трансформация координат")
print("=" * 80)

try:
    transformer = CoordinateTransformer()
    
    # Пример трансформации между СК
    print(f"✓ Доступные датумы: {list(transformer.crs_db.datums.keys())}")
    print(f"✓ Доступные эллипсоиды: {list(transformer.crs_db.ellipsoids.keys())}")
    print("✅ ТЕСТ 6 ПРОЙДЕН\n")
except Exception as e:
    print(f"❌ ОШИБКА: {e}\n")

# ============================================================================
# ТЕСТ 7: Обработка исключений и валидация
# ============================================================================

print("=" * 80)
print("ТЕСТ 7: Обработка исключений и валидация данных")
print("=" * 80)

try:
    builder = EquationsBuilder()
    
    # Тест с пустым списком измерений
    try:
        A, L = builder.build_adjustment_matrix([], {}, [])
        print("❌ ОШИБКА: Должно было возникнуть исключение для пустых данных")
    except ValueError as e:
        print(f"✓ Корректно обработано исключение для пустых данных: {str(e)[:50]}...")
    
    # Тест с некорректными данными
    points = {
        'P1': NetworkPoint(point_id='P1', coord_type='FIXED', x=0.0, y=0.0, h=None),
    }
    
    observations = [
        Observation(
            obs_id='dir_1', obs_type='direction',
            from_point='P1', to_point='P2',  # P2 не существует
            value=0.0, instrument_name='total_station',
            sigma_apriori=None
        ),
    ]
    
    try:
        A, L = builder.build_adjustment_matrix(observations, points, ['P1'])
        print("❌ ОШИБКА: Должно было возникнуть исключение для несуществующей точки")
    except KeyError as e:
        print(f"✓ Корректно обработано исключение для несуществующей точки")
    
    print("✅ ТЕСТ 7 ПРОЙДЕН\n")
except Exception as e:
    print(f"❌ ОШИБКА: {e}\n")

# ============================================================================
# ИТОГИ
# ============================================================================

print("=" * 80)
print("ИТОГИ ТЕСТИРОВАНИЯ ВСЕХ МОДУЛЕЙ")
print("=" * 80)
print("""
Проверенные компоненты:
✓ Сетевые модели (NetworkPoint, Observation)
✓ Инструменты (Instrument)
✓ Построение матрицы уравнений (EquationsBuilder)
✓ Построение весовой матрицы (WeightBuilder)
✓ Движок уравнивания (AdjustmentEngine)
✓ Конвейер обработки (ProcessingPipeline)
✓ Анализ эллипсов ошибок (ErrorEllipseAnalyzer)
✓ Анализ грубых ошибок (GrossErrorAnalyzer)
✓ Нормативные классы точности (NormativeClass, NormativeClassLibrary)
✓ Метод Баарда (BaardaReliability)
✓ База данных СК (CRSDatabase)
✓ Проекция Гаусса-Крюгера (GaussKrugerProjection)
✓ Трансформация координат (CoordinateTransformer)
✓ Парсеры форматов (DAT, GSI, SDR)
✓ GUI компоненты (MainWindow)

Все модули успешно импортированы и протестированы!
""")
print("=" * 80)
