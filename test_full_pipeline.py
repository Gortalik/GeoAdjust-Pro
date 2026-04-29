#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Полная проверка цикла работы программы через код GeoAdjustPro:
1. Импорт GSI файлов
2. Предобработка 
3. Уравнивание
4. Выгрузка отчетов
5. Схема сети (визуализация)
"""

import sys
import os
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/workspace/pipeline_test.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, '/workspace/GeoAdjustPro/src')

def print_section(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

# ============================================================================
# ЭТАП 1: ИМПОРТ
# ============================================================================
def test_import():
    print_section("ЭТАП 1: ИМПОРТ GSI ФАЙЛОВ")
    
    from geoadjust.io.formats.gsi import GSIParser
    
    gsi_files = [
        '/workspace/test_real_mes/s5/niv/DOM0112 (1).GSI',
        '/workspace/test_real_mes/s5/niv/MIR0212.GSI'
    ]
    
    all_points = []
    all_observations = []
    
    for gsi_file in gsi_files:
        if not os.path.exists(gsi_file):
            logger.warning(f"Файл не найден: {gsi_file}")
            continue
            
        logger.info(f"Парсинг файла: {gsi_file}")
        try:
            parser = GSIParser()
            result = parser.parse(gsi_file)
            
            points = result.get('points', [])
            observations = result.get('observations', [])
            
            logger.info(f"  ✓ Точек извлечено: {len(points)}")
            logger.info(f"  ✓ Наблюдений извлечено: {len(observations)}")
            
            all_points.extend(points)
            all_observations.extend(observations)
            
            if points:
                logger.info(f"  Пример точки: {points[0]}")
            if observations:
                logger.info(f"  Пример наблюдения (тип): {type(observations[0]).__name__}")
                
        except Exception as e:
            logger.error(f"  ✗ Ошибка парсинга {gsi_file}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\nВСЕГО после импорта:")
    logger.info(f"  Точек: {len(all_points)}")
    logger.info(f"  Наблюдений: {len(all_observations)}")
    
    return all_points, all_observations

# ============================================================================
# ЭТАП 2: ПРЕДОБРАБОТКА
# ============================================================================
def test_preprocessing(points, observations):
    print_section("ЭТАП 2: ПРЕДОБРАБОТКА ДАННЫХ")
    
    from geoadjust.core.preprocessing.module import PreprocessingModule
    from geoadjust.core.preprocessing.tolerances import ToleranceChecker
    
    logger.info(f"Входные данные: {len(points)} точек, {len(observations)} наблюдений")
    
    try:
        # Используем run_all_stages для предобработки
        preprocessor = PreprocessingModule()
        
        # Запуск всех этапов предобработки
        result = preprocessor.run_all_stages(observations, points)
        
        logger.info(f"  ✓ Предобработка завершена")
        
        processed_points = result.get('points', points)
        processed_obs = result.get('observations', observations)
        
        logger.info(f"    Точек после обработки: {len(processed_points) if hasattr(processed_points, '__len__') else 'N/A'}")
        logger.info(f"    Наблюдений после обработки: {len(processed_obs) if hasattr(processed_obs, '__len__') else 'N/A'}")
        
        # Проверка допусков
        try:
            tolerance_checker = ToleranceChecker()
            logger.info(f"  ✓ Модуль допусков доступен")
        except Exception as te:
            logger.warning(f"  ! Модуль допусков: {te}")
        
        return processed_points, processed_obs
        
    except Exception as e:
        logger.warning(f"  ! Предобработка не выполнена: {e}")
        import traceback
        traceback.print_exc()
        return points, observations

# ============================================================================
# ЭТАП 3: УРАВНИВАНИЕ
# ============================================================================
def test_adjustment(points, observations):
    print_section("ЭТАП 3: УРАВНИВАНИЕ")
    
    from geoadjust.core.adjustment.engine import AdjustmentEngine
    from geoadjust.core.adjustment.equations_builder import EquationsBuilder
    from geoadjust.core.adjustment.weight_builder import WeightBuilder
    from geoadjust.core.network.models import NetworkPoint
    
    logger.info(f"Данные для уравнивания: {len(points)} точек, {len(observations)} наблюдений")
    
    if len(points) < 2 or len(observations) < 1:
        logger.warning("  ! Недостаточно данных для уравнивания")
        return None
    
    try:
        # Конвертация точек в формат Dict[str, NetworkPoint]
        points_dict = {}
        for i, p in enumerate(points):
            if isinstance(p, dict):
                pid = p.get('point_id', f'P{i}')
                x = p.get('x')
                y = p.get('y')
                h = p.get('h')
                coord_type = 'FIXED' if (x is not None and y is not None) else 'APPROXIMATE'
                points_dict[pid] = NetworkPoint(point_id=pid, coord_type=coord_type, x=x, y=y, h=h)
            elif isinstance(p, NetworkPoint):
                points_dict[p.point_id] = p
            else:
                pid = f'P{i}'
                points_dict[pid] = NetworkPoint(point_id=pid, coord_type='APPROXIMATE')
        
        logger.info(f"  ✓ Преобразовано точек в NetworkPoint: {len(points_dict)}")
        
        # Построение матриц
        builder = EquationsBuilder()
        A, L = builder.build_adjustment_matrix(observations, points_dict)
        logger.info(f"  ✓ Матрица A: {A.shape}")
        logger.info(f"  ✓ Вектор L: {L.shape}")
        
        # Матрица весов
        weight_builder = WeightBuilder()
        P = weight_builder.build(observations)
        logger.info(f"  ✓ Матрица весов P: {P.shape}")
        
        # Уравнивание
        engine = AdjustmentEngine()
        result = engine.adjust(A, L, P)
        
        logger.info(f"  ✓ Уравнивание выполнено")
        logger.info(f"    Итераций: {result.get('iterations', 'N/A')}")
        logger.info(f"    RMS: {result.get('rms', 'N/A')}")
        logger.info(f"    Chi-squared: {result.get('chi_squared', 'N/A')}")
        
        if 'adjusted_coords' in result:
            logger.info(f"    Уравненных координат: {len(result['adjusted_coords'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"  ✗ Ошибка уравнивания: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# ЭТАП 4: ВЫГРУЗКА ОТЧЕТОВ (GOST Report)
# ============================================================================
def test_report_export(points, observations, adjustment_result):
    print_section("ЭТАП 4: ВЫГРУЗКА ОТЧЕТОВ (GOST)")
    
    output_dir = '/workspace/test_real_mes/s5/niv/excel_output'
    os.makedirs(output_dir, exist_ok=True)
    
    from geoadjust.io.export.gost_report import GOSTReportGenerator
    
    report_file = os.path.join(output_dir, 'отчет_уравнивания.txt')
    
    try:
        generator = GOSTReportGenerator()
        
        # Генерация отчета через run
        report_content = generator.run({
            'points': points,
            'observations': observations,
            'adjustment_result': adjustment_result
        })
        
        # Сохранение отчета
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"  ✓ Отчет создан: {report_file}")
        logger.info(f"  ✓ Размер файла: {os.path.getsize(report_file)} байт")
        
        # Показать первые строки отчета
        with open(report_file, 'r', encoding='utf-8') as f:
            first_lines = ''.join([f.readline() for _ in range(10)])
            logger.info(f"  Начало отчета:\n{first_lines}")
        
        return report_file
        
    except Exception as e:
        logger.error(f"  ✗ Ошибка экспорта отчета: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# ЭТАП 5: СХЕМА СЕТИ (визуализация в текстовом формате)
# ============================================================================
def test_network_scheme(points, observations):
    print_section("ЭТАП 5: СХЕМА СЕТИ (ВИЗУАЛИЗАЦИЯ)")
    
    output_dir = '/workspace/test_real_mes/s5/niv/excel_output'
    os.makedirs(output_dir, exist_ok=True)
    
    scheme_file = os.path.join(output_dir, 'схема_сети.txt')
    
    try:
        # Сбор информации о сети
        point_ids = set()
        connections = []
        
        for obs in observations[:100]:  # Ограничим первыми 100 для наглядности
            from_p = getattr(obs, 'from_point', getattr(obs, 'from_point_id', ''))
            to_p = getattr(obs, 'to_point', getattr(obs, 'to_point_id', ''))
            obs_type = getattr(obs, 'obs_type', 'unknown')
            
            if from_p:
                point_ids.add(from_p)
            if to_p:
                point_ids.add(to_p)
            if from_p and to_p:
                connections.append((from_p, to_p, obs_type))
        
        # Создание текстовой схемы
        with open(scheme_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("СХЕМА ГЕОДЕЗИЧЕСКОЙ СЕТИ\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Всего пунктов: {len(point_ids)}\n")
            f.write(f"Всего связей (показано первых 100): {len(connections)}\n\n")
            
            f.write("СПИСОК ПУНКТОВ:\n")
            f.write("-" * 40 + "\n")
            for pid in sorted(point_ids)[:50]:
                f.write(f"  {pid}\n")
            if len(point_ids) > 50:
                f.write(f"  ... и еще {len(point_ids) - 50} пунктов\n")
            
            f.write("\nСВЯЗИ МЕЖДУ ПУНКТАМИ:\n")
            f.write("-" * 40 + "\n")
            for from_p, to_p, obs_type in connections[:30]:
                f.write(f"  {from_p} --[{obs_type}]--> {to_p}\n")
            if len(connections) > 30:
                f.write(f"  ... и еще {len(connections) - 30} связей\n")
            
            f.write("\n" + "=" * 60 + "\n")
        
        logger.info(f"  ✓ Схема создана: {scheme_file}")
        logger.info(f"  ✓ Размер файла: {os.path.getsize(scheme_file)} байт")
        
        # Показать содержимое схемы
        with open(scheme_file, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"  Содержимое схемы:\n{content}")
        
        return scheme_file
        
    except Exception as e:
        logger.error(f"  ✗ Ошибка создания схемы: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================
def main():
    print_section("ПОЛНЫЙ ЦИКЛ РАБОТЫ ПРОГРАММЫ GeoAdjustPro")
    print(f"Дата начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Логирование: /workspace/pipeline_test.log")
    
    results = {}
    
    # Этап 1: Импорт
    points, observations = test_import()
    results['import'] = {'points': len(points), 'observations': len(observations)}
    
    # Этап 2: Предобработка
    cleaned_points, cleaned_obs = test_preprocessing(points, observations)
    results['preprocessing'] = {'points': len(cleaned_points) if hasattr(cleaned_points, '__len__') else 'N/A', 
                                 'observations': len(cleaned_obs) if hasattr(cleaned_obs, '__len__') else 'N/A'}
    
    # Этап 3: Уравнивание
    adjustment_result = test_adjustment(cleaned_points, cleaned_obs)
    results['adjustment'] = 'success' if adjustment_result else 'failed'
    
    # Этап 4: Выгрузка отчетов
    report_file = test_report_export(cleaned_points, cleaned_obs, adjustment_result)
    results['report_export'] = 'success' if report_file else 'failed'
    
    # Этап 5: Схема сети
    scheme_file = test_network_scheme(cleaned_points, cleaned_obs)
    results['network_scheme'] = 'success' if scheme_file else 'failed'
    
    # Итоговый отчет
    print_section("ИТОГОВЫЙ ОТЧЕТ")
    for stage, result in results.items():
        status = "✓" if result == 'success' or (isinstance(result, dict) and result.get('points', 0) > 0) else "✗"
        logger.info(f"{status} {stage}: {result}")
    
    # Проверка выходных файлов
    print_section("ВЫХОДНЫЕ ФАЙЛЫ")
    output_dir = '/workspace/test_real_mes/s5/niv/excel_output'
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        for f in files:
            filepath = os.path.join(output_dir, f)
            size = os.path.getsize(filepath)
            logger.info(f"  ✓ {f}: {size} байт")
    else:
        logger.warning(f"  ! Папка {output_dir} не создана")
    
    print(f"\nДата завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results

if __name__ == '__main__':
    main()
