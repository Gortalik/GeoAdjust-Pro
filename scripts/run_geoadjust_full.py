#!/usr/bin/env python3
"""
GeoAdjustPro - Полный цикл работы с реальными данными
Используем существующий парсер из GeoAdjustPro
"""
import sys
import os
from pathlib import Path

# Добавляем путь к модулям GeoAdjustPro
sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))
sys.path.insert(0, '/workspace')

from geo_adjust_pro import GeoAdjustEngine, NetworkPoint, Observation, NetworkData
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def import_gsi_with_existing_parser(gsi_file):
    """Использование существующего парсера GeoAdjustPro"""
    try:
        from geoadjust.io.formats.gsi import GSIParser
        
        parser = GSIParser()
        result = parser.parse(Path(gsi_file))
        
        points = {}
        observations = []
        
        # Конвертация точек в нашу модель
        for pt in result.get('points', []):
            pt_id = pt.point_id if hasattr(pt, 'point_id') else str(pt)
            
            # Получаем координаты
            x = getattr(pt, 'x', None)
            y = getattr(pt, 'y', None)
            z = getattr(pt, 'z', None)
            
            # Определяем статусы
            plan_status = 'working'
            height_status = 'working'
            
            if x is not None and y is not None:
                plan_status = 'initial'
            if z is not None:
                height_status = 'initial'
            
            points[pt_id] = NetworkPoint(
                id=pt_id,
                x=x,
                y=y,
                z=z,
                plan_status=plan_status,
                height_status=height_status
            )
        
        # Конвертация наблюдений
        for obs in result.get('observations', []):
            obs_type_map = {
                'leveling_height_diff': 'leveling_height_diff',
                'slope_distance': 'distance',
                'horizontal_direction': 'direction',
                'horizontal_angle': 'angle',
                'zenith_angle': 'zenith_angle'
            }
            
            raw_type = getattr(obs, 'obs_type', 'unknown')
            mapped_type = obs_type_map.get(raw_type, raw_type)
            
            from_pt = getattr(obs, 'from_point', None)
            to_pt = getattr(obs, 'to_point', None)
            value = getattr(obs, 'value', 0.0)
            distance = getattr(obs, 'distance', 0.0)
            
            if from_pt and to_pt:
                observations.append(Observation(
                    id=f"obs_{len(observations)}",
                    type=mapped_type,
                    from_point=str(from_pt),
                    to_point=str(to_pt),
                    value=value,
                    distance=distance if distance else 0.05
                ))
        
        logger.info(f"GSI {gsi_file}: {len(points)} точек, {len(observations)} наблюдений")
        return points, observations
        
    except Exception as e:
        logger.error(f"Ошибка импорта GSI {gsi_file}: {e}")
        return {}, []

def main():
    print("=" * 80)
    print("GeoAdjustPro - Полный цикл обработки данных")
    print("=" * 80)
    
    # Файлы для обработки
    gsi_files = [
        '/workspace/test_real_mes/s5/niv/DOM0112 (1).GSI',
        '/workspace/test_real_mes/s5/niv/MIR0212.GSI',
    ]
    
    all_points = {}
    all_observations = []
    
    # ЭТАП 1: ИМПОРТ
    print("\n[1/4] ИМПОРТ ДАННЫХ")
    print("-" * 50)
    
    for gsi_file in gsi_files:
        if os.path.exists(gsi_file):
            points, obs = import_gsi_with_existing_parser(gsi_file)
            all_points.update(points)
            all_observations.extend(obs)
        else:
            logger.warning(f"Файл не найден: {gsi_file}")
    
    print(f"Всего: {len(all_points)} точек, {len(all_observations)} наблюдений")
    
    # Статистика по типам наблюдений
    type_counts = {}
    for obs in all_observations:
        type_counts[obs.type] = type_counts.get(obs.type, 0) + 1
    print(f"Типы наблюдений: {type_counts}")
    
    # Статусы пунктов
    plan_stats = {'initial': 0, 'working': 0}
    height_stats = {'initial': 0, 'working': 0}
    for p in all_points.values():
        if p.plan_status in plan_stats:
            plan_stats[p.plan_status] += 1
        if p.height_status in height_stats:
            height_stats[p.height_status] += 1
    
    print(f"План: исходные={plan_stats['initial']}, рабочие={plan_stats['working']}")
    print(f"Высота: исходные={height_stats['initial']}, рабочие={height_stats['working']}")
    
    # ЭТАП 2: ПРЕДОБРАБОТКА
    print("\n[2/4] ПРЕДОБРАБОТКА")
    print("-" * 50)
    
    # Фильтрация
    initial_obs = len(all_observations)
    all_observations = [o for o in all_observations if abs(o.value) < 1000]
    print(f"Удалено грубых ошибок: {initial_obs - len(all_observations)}")
    print(f"Осталось наблюдений: {len(all_observations)}")
    
    # ЭТАП 3: УРАВНИВАНИЕ
    print("\n[3/4] УРАВНИВАНИЕ")
    print("-" * 50)
    
    engine = GeoAdjustEngine()
    engine.load_network(all_points, all_observations)
    
    # Нивелирование
    leveling_obs = [o for o in all_observations if o.type == 'leveling_height_diff']
    if leveling_obs:
        print(f"Нивелирных наблюдений: {len(leveling_obs)}")
        result_h = engine.adjust_heights()
        
        if result_h.success:
            print(f"✓ Уравнивание высот выполнено")
            print(f"  СКП: {result_h.sigma0*1000:.3f} мм")
            if result_h.sigma0_km:
                print(f"  СКП на 1 км: {result_h.sigma0_km*1000:.3f} мм/км")
            print(f"  Уравнено точек: {len(result_h.points_stats)}")
            
            # Первые результаты
            print("\n  Результаты (первые 5):")
            for i, (pid, st) in enumerate(sorted(result_h.points_stats.items())[:5]):
                print(f"    {pid}: H={st['height']:.4f}м ±{st['height_std']*1000:.1f}мм")
        else:
            print(f"✗ Ошибка: {result_h.message}")
    else:
        print("⚠ Нет нивелирных наблюдений")
    
    # План
    dist_obs = [o for o in all_observations if o.type == 'distance']
    if dist_obs:
        print(f"\nНаблюдений расстояний: {len(dist_obs)}")
        result_p = engine.adjust_plan()
        print(f"  {result_p.message}")
    
    # ЭТАП 4: ВЫГРУЗКА
    print("\n[4/4] ВЫГРУЗКА РЕЗУЛЬТАТОВ")
    print("-" * 50)
    
    out_dir = '/workspace/geoadjust_output'
    os.makedirs(out_dir, exist_ok=True)
    
    # Отчет
    report_path = f'{out_dir}/report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("ОТЧЕТ GEOADJUSTPRO\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Точек: {len(all_points)}\n")
        f.write(f"Наблюдений: {len(all_observations)}\n\n")
        
        if leveling_obs and result_h.success:
            f.write("УРАВНИВАНИЕ ВЫСОТ\n")
            f.write("-" * 60 + "\n")
            f.write(f"СКП: {result_h.sigma0*1000:.3f} мм\n")
            f.write(f"СКП на 1 км: {result_h.sigma0_km*1000:.3f} мм/км\n\n")
            f.write("ВЕДОМОСТЬ ВЫСОТ:\n")
            f.write(f"{'Пункт':<10} {'Высота':<12} {'СКП':<10} {'Поправка':<10}\n")
            for pid, st in sorted(result_h.points_stats.items()):
                f.write(f"{pid:<10} {st['height']:<12.4f} ±{st['height_std']*1000:<9.1f} {st['correction']*1000:<10.1f}\n")
    
    print(f"✓ Отчет: {report_path}")
    
    # Схема
    scheme_path = f'{out_dir}/scheme.txt'
    with open(scheme_path, 'w', encoding='utf-8') as f:
        f.write("СХЕМА СЕТИ\n")
        f.write("=" * 60 + "\n\n")
        for pid, p in sorted(all_points.items()):
            ps = "ИСХ" if p.plan_status == 'initial' else "РАБ"
            hs = "ИСХ" if p.height_status == 'initial' else "РАБ"
            xy = f"X={p.x:.2f} Y={p.y:.2f}" if p.x else "--"
            h = f"H={p.z:.3f}" if p.z else "--"
            f.write(f"{pid}: [{ps}/{hs}] {xy} {h}\n")
    
    print(f"✓ Схема: {scheme_path}")
    
    print("\n" + "=" * 80)
    print("ГОТОВО")
    print("=" * 80)

if __name__ == '__main__':
    main()
