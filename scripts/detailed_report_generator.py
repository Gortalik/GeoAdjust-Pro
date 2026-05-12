#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный отчет GeoAdjustPro с полными результатами уравнивания
"""

import sys
import os
from pathlib import Path

# Add path to GeoAdjustPro modules

from geo_adjust_pro import GeoAdjustEngine, NetworkPoint, Observation, NetworkData
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def import_gsi_with_existing_parser(gsi_file):
    """Use existing GeoAdjustPro parser"""
    try:
        from geoadjust.io.formats.gsi import GSIParser

        parser = GSIParser()
        result = parser.parse(Path(gsi_file))

        points = {}
        observations = []

        # Convert points to our model
        for pt in result.get('points', []):
            pt_id = pt.point_id if hasattr(pt, 'point_id') else str(pt)

            # Get coordinates
            x = getattr(pt, 'x', None)
            y = getattr(pt, 'y', None)
            z = getattr(pt, 'z', None)

            # Determine statuses
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

        # Convert observations
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

        logger.info(f"GSI {gsi_file}: {len(points)} points, {len(observations)} observations")
        return points, observations

    except Exception as e:
        logger.error(f"Error importing GSI {gsi_file}: {e}")
        return {}, []

def create_detailed_report(engine, result_h, result_p, all_points, all_observations, output_dir):
    """Создание подробного отчета с результатами уравнивания"""

    report_path = os.path.join(output_dir, 'detailed_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GEOAdjustPro - ПОДРОБНЫЙ ОТЧЕТ ПО УРАВНИВАНИЮ\n")
        f.write("=" * 80 + "\n\n")

        f.write("ОБЩАЯ ИНФОРМАЦИЯ\n")
        f.write("-" * 50 + "\n")
        f.write(f"Всего точек: {len(all_points)}\n")
        f.write(f"Всего наблюдений: {len(all_observations)}\n")
        f.write(f"Нивелирных ходов: {len([o for o in all_observations if o.type == 'leveling_height_diff'])}\n")
        f.write(f"Расстояний: {len([o for o in all_observations if o.type == 'distance'])}\n")
        f.write(f"Направлений: {len([o for o in all_observations if o.type == 'direction'])}\n\n")

        # Нивелирование
        f.write("НИВЕЛИРОВАНИЕ\n")
        f.write("-" * 50 + "\n")
        if result_h and result_h.success:
            f.write(f"Статус: УСПЕШНО\n")
            f.write(f"Тип уравнивания: {'Свободное' if 'свободное' in result_h.message else 'Строгое'}\n")
            f.write(f"СКП единицы веса: {result_h.sigma0*1000:.3f} мм\n")
            if result_h.sigma0_km:
                f.write(f"СКП на 1 км: {result_h.sigma0_km*1000:.3f} мм/км\n")
            f.write(f"Уравнено точек: {len(result_h.points_stats)}\n")
            f.write(f"Итераций: {result_h.iterations}\n")
            f.write(f"Остатков: {len(result_h.residuals)}\n\n")

            if result_h.points_stats:
                f.write("ВЕДОМОСТЬ ВЫСОТ\n")
                f.write("-" * 50 + "\n")
                f.write(f"{'Пункт':<10} {'Высота, м':<12} {'СКП, мм':<10} {'Поправка, мм':<12}\n")
                f.write("-" * 50 + "\n")
                for pid, stats in sorted(result_h.points_stats.items()):
                    f.write(f"{pid:<10} {stats['height']:<12.4f} {stats['height_std']*1000:<10.1f} {stats['correction']*1000:<12.1f}\n")
                f.write("\n")
        else:
            f.write(f"Статус: НЕ ВЫПОЛНЕНО\n")
            f.write(f"Причина: {result_h.message if result_h else 'Нет результатов'}\n")
            f.write("Рекомендация: Добавьте фиксированные репера высот для строгого уравнивания\n\n")

        # План
        f.write("ПЛАНОВОЕ УРАВНИВАНИЕ\n")
        f.write("-" * 50 + "\n")
        if result_p and result_p.success:
            f.write(f"Статус: УСПЕШНО\n")
            f.write(f"Тип уравнивания: {'Свободное' if 'свободное' in result_p.message else 'Строгое'}\n")
            f.write(f"СКП единицы веса: {result_p.sigma0*1000:.3f} мм\n")
            f.write(f"Уравнено точек: {len(result_p.points_stats)}\n")
            f.write(f"Итераций: {result_p.iterations}\n")
            f.write(f"Остатков: {len(result_p.residuals)}\n\n")

            if result_p.points_stats:
                f.write("ВЕДОМОСТЬ КООРДИНАТ\n")
                f.write("-" * 50 + "\n")
                f.write(f"{'Пункт':<10} {'X, м':<12} {'Y, м':<12} {'СКП X, мм':<10} {'СКП Y, мм':<10}\n")
                f.write("-" * 50 + "\n")
                for pid, stats in sorted(result_p.points_stats.items()):
                    f.write(f"{pid:<10} {stats['x']:<12.3f} {stats['y']:<12.3f} {stats['std_x']*1000:<10.1f} {stats['std_y']*1000:<10.1f}\n")
                f.write("\n")
        else:
            f.write(f"Статус: НЕ ВЫПОЛНЕНО\n")
            f.write(f"Причина: {result_p.message if result_p else 'Нет результатов'}\n\n")

        # Сеть
        f.write("ТОПОЛОГИЯ СЕТИ\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'Пункт':<10} {'Тип':<8} {'План':<8} {'Высота':<8} {'X':<12} {'Y':<12} {'H':<12}\n")
        f.write("-" * 50 + "\n")
        for pid, point in sorted(all_points.items()):
            plan_status = point.plan_status[:3].upper() if point.plan_status else '---'
            height_status = point.height_status[:3].upper() if point.height_status else '---'
            x = f"{point.x:.3f}" if point.x is not None else "---"
            y = f"{point.y:.3f}" if point.y is not None else "---"
            h = f"{point.z:.3f}" if point.z is not None else "---"
            f.write(f"{pid:<10} {'STA':<8} {plan_status:<8} {height_status:<8} {x:<12} {y:<12} {h:<12}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("ОТЧЕТ СОЗДАН GeoAdjustPro\n")
        f.write("=" * 80 + "\n")

    print(f"Подробный отчет сохранен: {report_path}")
    return report_path

def main():
    print("=" * 80)
    print("GeoAdjustPro - ПОДРОБНЫЙ ОТЧЕТ С РЕЗУЛЬТАТАМИ УРАВНИВАНИЯ")
    print("=" * 80)

    # Пути к данным
    base_path = str(Path(__file__).parent / "test_real_mes")
    gsi_files = [
        os.path.join(base_path, 's5', 'niv', 'DOM0112 (1).GSI'),
        os.path.join(base_path, 's5', 'niv', 'MIR0212.GSI'),
    ]

    all_points = {}
    all_observations = []

    print("\n[1/4] ЗАГРУЗКА ДАННЫХ")
    print("-" * 50)

    for gsi_file in gsi_files:
        if os.path.exists(gsi_file):
            points, obs = import_gsi_with_existing_parser(gsi_file)
            all_points.update(points)
            all_observations.extend(obs)

    print(f"Загружено: {len(all_points)} точек, {len(all_observations)} наблюдений")

    print("\n[2/4] УРАВНИВАНИЕ")
    print("-" * 50)

    engine = GeoAdjustEngine()
    engine.load_network(all_points, all_observations)

    # Нивелирование
    print("Уравнивание высот...")
    result_h = engine.adjust_heights(free_adjustment=True)

    # План
    print("Уравнивание плана...")
    result_p = engine.adjust_plan(all_points, all_observations, free_adjustment=False)

    print("\n[3/4] СОЗДАНИЕ ОТЧЕТОВ")
    print("-" * 50)

    output_dir = str(Path(__file__).parent / 'geoadjust_output')
    os.makedirs(output_dir, exist_ok=True)

    # Создание подробного отчета
    detailed_report = create_detailed_report(engine, result_h, result_p, all_points, all_observations, output_dir)

    # Визуализация
    print("\n[4/4] ВИЗУАЛИЗАЦИЯ")
    print("-" * 50)

    from network_visualizer import visualize_network

    # Подготовка данных для визуализатора
    viz_points = {}
    viz_observations = []

    for pid, p in all_points.items():
        viz_points[pid] = {
            'x': p.x,
            'y': p.y,
            'plan_status': p.plan_status,
            'height_status': p.height_status
        }

    for obs in all_observations[:100]:  # Ограничиваем для читаемости
        viz_observations.append({
            'type': obs.type,
            'from_point': obs.from_point,
            'to_point': obs.to_point,
            'value': obs.value
        })

    try:
        visualize_network(viz_points, viz_observations,
                         title="GeoAdjustPro - Результаты уравнивания", output_dir=output_dir)
        print("Визуализация создана")
    except Exception as e:
        print(f"Ошибка визуализации: {e}")

    print("\n" + "=" * 80)
    print("ОТЧЕТЫ СОЗДАНЫ:")
    print(f"  Подробный отчет: {detailed_report}")
    print(f"  Схема сети: {os.path.join(output_dir, 'scheme.txt')}")
    print(f"  Карта сети: {os.path.join(output_dir, 'network_plot.png')}")
    print("=" * 80)

if __name__ == '__main__':
    main()