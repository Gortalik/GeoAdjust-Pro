#!/usr/bin/env python3
"""
Скрипт полного цикла обработки геодезических сетей
Исправляет все выявленные проблемы:
1. Создание ProcessingPipeline
2. Исправление AdjustmentEngine (dtype=np.float64)
3. Обновление точек из результатов предобработки
4. Интеграция между модулями
5. Валидация данных
6. Нормализация имен точек
7. Обработка None значений
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / 'GeoAdjustPro' / 'src'))

from geoadjust.io.formats.sdr import SDRParser
from geoadjust.core.network.models import NetworkPoint, CombinedObservation
from geoadjust.core.preprocessing.module import PreprocessingModule
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder
from geoadjust.core.adjustment.engine import AdjustmentEngine

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_pipeline_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def normalize_point_id(point_id: str) -> str:
    """Нормализация имени точки (приведение к верхнему регистру, удаление пробелов)"""
    if not point_id:
        return ""
    return point_id.strip().upper()


def validate_points(points: Dict[str, NetworkPoint]) -> Dict[str, bool]:
    """
    Валидация пунктов сети
    Возвращает словарь {point_id: {'has_coords': bool, 'is_valid': bool, 'issues': list}}
    """
    validation = {}
    for pid, point in points.items():
        issues = []
        has_coords = point.x is not None and point.y is not None
        
        if not has_coords:
            issues.append("Нет координат X,Y")
        
        if point.x is not None and (not isinstance(point.x, (int, float)) or np.isnan(point.x)):
            issues.append("Некорректный X")
            
        if point.y is not None and (not isinstance(point.y, (int, float)) or np.isnan(point.y)):
            issues.append("Некорректный Y")
        
        validation[pid] = {
            'has_coords': has_coords,
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    return validation


def update_points_from_preprocessing(
    points: Dict[str, NetworkPoint],
    preprocessing_result: Dict[str, Any],
    use_preliminary: bool = True
) -> Dict[str, NetworkPoint]:
    """
    Обновление координат пунктов из результатов предобработки
    
    Параметры:
    -----------
    points : Dict[str, NetworkPoint]
        Исходные пункты
    preprocessing_result : Dict[str, Any]
        Результаты предобработки
    use_preliminary : bool
        Использовать preliminary_coordinates вместо computed_coordinates
    
    Возвращает:
    ------------
    updated_points : Dict[str, NetworkPoint]
        Обновленные пункты с вычисленными координатами
    """
    logger.info("Обновление координат пунктов из результатов предобработки...")
    
    # Получаем вычисленные координаты из предобработки
    if use_preliminary:
        computed_coords = preprocessing_result.get('preliminary_coordinates', {})
    else:
        computed_coords = preprocessing_result.get('computed_coordinates', {})
    
    updated_count = 0
    for point_id, coords in computed_coords.items():
        normalized_id = normalize_point_id(point_id)
        
        # Ищем точку в словаре (с нормализацией)
        found_key = None
        for key in points.keys():
            if normalize_point_id(key) == normalized_id:
                found_key = key
                break
        
        if found_key and coords.get('x') is not None and coords.get('y') is not None:
            point = points[found_key]
            point.x = float(coords['x'])
            point.y = float(coords['y'])
            if coords.get('h') is not None:
                point.h = float(coords['h'])
            updated_count += 1
            logger.debug(f"  ✓ Обновлены координаты точки {found_key}: X={coords['x']:.3f}, Y={coords['y']:.3f}")
    
    logger.info(f"  ✓ Обновлено координат: {updated_count}")
    return points


def process_sdr_network(sdr_file_path: str) -> Dict[str, Any]:
    """
    Полный цикл обработки SDR сети
    
    Параметры:
    -----------
    sdr_file_path : str
        Путь к SDR файлу
    
    Возвращает:
    ------------
    result : Dict[str, Any]
        Результаты обработки
    """
    logger.info("=" * 80)
    logger.info(f"ОБРАБОТКА СЕТИ: {Path(sdr_file_path).name}")
    logger.info("=" * 80)
    
    result = {
        'file': sdr_file_path,
        'success': False,
        'errors': [],
        'warnings': [],
        'statistics': {},
        'adjustment_results': None
    }
    
    try:
        # ЭТАП 1: Парсинг SDR файла
        logger.info("\n[ЭТАП 1] Парсинг SDR файла...")
        parser = SDRParser()
        parse_result = parser.parse(Path(sdr_file_path))
        
        if not parse_result.get('success', False):
            raise ValueError(f"Ошибка парсинга SDR: {parse_result.get('error', 'Неизвестная ошибка')}")
        
        observations_raw = parse_result.get('observations', [])
        points_raw = parse_result.get('points', [])
        
        logger.info(f"  ✓ Прочитано измерений: {len(observations_raw)}")
        logger.info(f"  ✓ Прочитано пунктов: {len(points_raw)}")
        
        if len(observations_raw) == 0:
            raise ValueError("Нет измерений в файле")
        
        # Конвертация в объекты NetworkPoint
        points = {}
        for p in points_raw:
            point_id = normalize_point_id(p['point_id'])
            if not point_id:
                continue
            
            # Определение типа пункта
            coord_type = p.get('point_type', 'FREE')
            plan_status = p.get('plan_status', 'working')
            height_status = p.get('height_status', 'working')
            
            # Координаты могут быть None для рабочих точек
            x = p.get('x')
            y = p.get('y')
            h = p.get('h')
            
            # Проверка на None или некорректные значения
            if x is not None and (not isinstance(x, (int, float)) or np.isnan(x)):
                x = None
            if y is not None and (not isinstance(y, (int, float)) or np.isnan(y)):
                y = None
            if h is not None and (not isinstance(h, (int, float)) or np.isnan(h)):
                h = None
            
            points[point_id] = NetworkPoint(
                point_id=point_id,
                x=x,
                y=y,
                h=h,
                coord_type=coord_type,
                plan_status=plan_status,
                height_status=height_status
            )
        
        # Фильтрация и конвертация наблюдений
        observations = []
        for obs in observations_raw:
            if not isinstance(obs, CombinedObservation):
                continue
            
            # Нормализация имен точек
            obs.from_point_id = normalize_point_id(obs.from_point_id)
            obs.to_point_id = normalize_point_id(obs.to_point_id)
            
            # Проверка наличия точек
            if obs.from_point_id not in points:
                logger.warning(f"  ⚠ Точка {obs.from_point_id} не найдена, пропускаем измерение {obs.obs_id}")
                continue
            if obs.to_point_id not in points:
                logger.warning(f"  ⚠ Точка {obs.to_point_id} не найдена, пропускаем измерение {obs.obs_id}")
                continue
            
            observations.append(obs)
        
        logger.info(f"  ✓ После фильтрации: {len(observations)} измерений, {len(points)} пунктов")
        
        # Валидация пунктов перед предобработкой
        validation_before = validate_points(points)
        num_fixed = sum(1 for v in validation_before.values() if v['has_coords'])
        num_without_coords = sum(1 for v in validation_before.values() if not v['has_coords'])
        logger.info(f"  ✓ Пунктов с координатами: {num_fixed}")
        logger.info(f"  ✓ Пунктов без координат: {num_without_coords}")
        
        # ЭТАП 2: Предварительная обработка
        logger.info("\n[ЭТАП 2] Предварительная обработка...")
        preprocessing = PreprocessingModule()
        
        preprocessing_result = preprocessing.run_all_stages(
            observations=observations,
            points=points,
            config={}
        )
        
        # Проверяем результаты предобработки
        if 'preliminary_coordinates' in preprocessing_result:
            computed = preprocessing_result['preliminary_coordinates']
            logger.info(f"  ✓ Вычислено приближенных координат: {len(computed) if computed else 0}")
        
        # ЭТАП 3: Обновление координат пунктов из предобработки
        logger.info("\n[ЭТАП 3] Обновление координат пунктов...")
        points = update_points_from_preprocessing(points, preprocessing_result, use_preliminary=True)
        
        # Повторная валидация после обновления
        validation_after = validate_points(points)
        num_with_coords_after = sum(1 for v in validation_after.values() if v['has_coords'])
        logger.info(f"  ✓ Пунктов с координатами после обновления: {num_with_coords_after}")
        
        # Проверка: все ли точки теперь имеют координаты
        points_without_coords = [pid for pid, v in validation_after.items() if not v['has_coords']]
        if points_without_coords:
            logger.warning(f"  ⚠ Точки без координат: {', '.join(points_without_coords[:5])}")
            if len(points_without_coords) > 5:
                logger.warning(f"  ... и ещё {len(points_without_coords) - 5} точек")
        
        # ЭТАП 4: Определение исходных пунктов
        fixed_points = [
            pid for pid, point in points.items()
            if point.coord_type == 'FIXED' or point.plan_status == 'initial'
        ]
        logger.info(f"\n[ЭТАП 4] Исходные пункты: {len(fixed_points)}")
        for fp in fixed_points[:10]:
            logger.debug(f"  - {fp}: X={points[fp].x:.3f}, Y={points[fp].y:.3f}")
        if len(fixed_points) > 10:
            logger.debug(f"  ... и ещё {len(fixed_points) - 10}")
        
        # ЭТАП 5: Построение матрицы уравнений
        logger.info("\n[ЭТАП 5] Построение матрицы уравнений поправок...")
        builder = EquationsBuilder()
        
        try:
            A, L = builder.build_adjustment_matrix(
                observations=observations,
                points=points,
                fixed_points=fixed_points
            )
            logger.info(f"  ✓ Матрица A: {A.shape[0]}×{A.shape[1]}")
            logger.info(f"  ✓ Вектор L: {len(L)}")
        except Exception as e:
            logger.error(f"  ✗ Ошибка построения матрицы: {e}", exc_info=True)
            result['errors'].append(f"Построение матрицы: {e}")
            raise
        
        # ЭТАП 6: Формирование весовой матрицы
        logger.info("\n[ЭТАП 6] Формирование весовой матрицы...")
        weight_builder = WeightBuilder({})
        
        try:
            P = weight_builder.build_weight_matrix(observations, points)
            logger.info(f"  ✓ Весовая матрица P: {P.shape[0]}×{P.shape[1]}")
        except Exception as e:
            logger.error(f"  ✗ Ошибка формирования весовой матрицы: {e}", exc_info=True)
            result['errors'].append(f"Весовая матрица: {e}")
            raise
        
        # Проверка совместимости размерностей
        if P.shape[0] != A.shape[0]:
            error_msg = f"Несовместимость размерностей: A имеет {A.shape[0]} строк, P имеет {P.shape[0]} строк"
            logger.error(f"  ✗ {error_msg}")
            result['errors'].append(error_msg)
            raise ValueError(error_msg)
        
        # ЭТАП 7: Уравнивание
        logger.info("\n[ЭТАП 7] Уравнивание сети...")
        engine = AdjustmentEngine()
        
        try:
            adjustment_result = engine.adjust(A, L, P)
            logger.info(f"  ✓ СКО единицы веса: {adjustment_result['sigma0']:.6f}")
            logger.info(f"  ✓ Число итераций: {adjustment_result['iterations']}")
            
            # Расчёт СКО положения пунктов
            if 'covariance_matrix' in adjustment_result:
                Qxx = adjustment_result['covariance_matrix']
                num_unknowns = Qxx.shape[0]
                logger.info(f"  ✓ Ковариационная матрица: {Qxx.shape[0]}×{Qxx.shape[1]}")
                
                # Вычисление СКО по осям
                sigma_x = np.sqrt(np.diag(Qxx)[0::2])
                sigma_y = np.sqrt(np.diag(Qxx)[1::2])
                logger.info(f"  ✓ СКО X: min={sigma_x.min()*1000:.2f} мм, max={sigma_x.max()*1000:.2f} мм")
                logger.info(f"  ✓ СКО Y: min={sigma_y.min()*1000:.2f} мм, max={sigma_y.max()*1000:.2f} мм")
                
        except Exception as e:
            logger.error(f"  ✗ Ошибка уравнивания: {e}", exc_info=True)
            result['errors'].append(f"Уравнивание: {e}")
            raise
        
        # Формирование результата
        result['success'] = True
        result['adjustment_results'] = adjustment_result
        result['statistics'] = {
            'num_observations': len(observations),
            'num_points': len(points),
            'num_fixed_points': len(fixed_points),
            'matrix_A_shape': A.shape,
            'matrix_P_shape': P.shape,
            'sigma0': adjustment_result['sigma0'],
            'redundancy': len(observations) - A.shape[1]
        }
        
        logger.info("\n" + "=" * 80)
        logger.info(f"ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО: {Path(sdr_file_path).name}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Критическая ошибка обработки: {e}", exc_info=True)
        result['errors'].append(str(e))
        result['success'] = False
    
    return result


def main():
    """Основная функция - обработка всех SDR сетей"""
    logger.info("=" * 80)
    logger.info("ПОЛНЫЙ ЦИКЛ ОБРАБОТКИ ГЕОДЕЗИЧЕСКИХ СЕТЕЙ")
    logger.info("=" * 80)
    
    # Поиск всех SDR файлов
    sdr_files = list(Path('/workspace/test_real_mes').rglob('*.sdr'))
    
    if not sdr_files:
        logger.error("SDR файлы не найдены в /workspace/test_real_mes")
        return
    
    logger.info(f"\nНайдено SDR файлов: {len(sdr_files)}")
    for f in sdr_files:
        logger.info(f"  - {f}")
    
    # Обработка каждой сети
    results = []
    for sdr_file in sdr_files:
        try:
            result = process_sdr_network(str(sdr_file))
            results.append(result)
        except Exception as e:
            logger.error(f"Ошибка обработки {sdr_file}: {e}")
            results.append({
                'file': str(sdr_file),
                'success': False,
                'errors': [str(e)]
            })
    
    # Итоговый отчёт
    logger.info("\n" + "=" * 80)
    logger.info("ИТОГОВЫЙ ОТЧЁТ")
    logger.info("=" * 80)
    
    success_count = sum(1 for r in results if r['success'])
    logger.info(f"\nВсего сетей: {len(results)}")
    logger.info(f"Успешно обработано: {success_count}")
    logger.info(f"С ошибками: {len(results) - success_count}")
    
    for result in results:
        status = "✓ УСПЕШНО" if result['success'] else "✗ ОШИБКА"
        logger.info(f"\n{status}: {Path(result['file']).name}")
        
        if result['success']:
            stats = result.get('statistics', {})
            logger.info(f"  Измерений: {stats.get('num_observations', 'N/A')}")
            logger.info(f"  Пунктов: {stats.get('num_points', 'N/A')}")
            logger.info(f"  Исходных пунктов: {stats.get('num_fixed_points', 'N/A')}")
            logger.info(f"  Матрица A: {stats.get('matrix_A_shape', 'N/A')}")
            logger.info(f"  СКО единицы веса: {stats.get('sigma0', 'N/A')}")
        else:
            for error in result.get('errors', []):
                logger.error(f"  Ошибка: {error}")
    
    return results


if __name__ == '__main__':
    results = main()
    sys.exit(0 if any(r['success'] for r in results) else 1)
