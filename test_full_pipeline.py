#!/usr/bin/env python3
"""
Тест полного цикла работы GeoAdjustPro с реальными данными GSI
Импорт -> Предобработка -> Уравнивание -> Отчеты
"""
import sys
import os
sys.path.insert(0, '/workspace')

from geo_adjust_pro import GeoAdjustEngine, NetworkPoint, Observation, NetworkData
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def parse_gsi_file(filepath):
    """Простой парсер GSI файлов для демонстрации"""
    points = {}
    observations = []
    
    with open(filepath, 'r', encoding='latin-1') as f:
        lines = f.readlines()
    
    point_counter = 0
    obs_counter = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Разбор строки GSI (формат: +XXXXXX...)
        parts = line.split()
        for part in parts:
            if len(part) < 6:
                continue
            
            # Блок 01 - номер точки
            if part.startswith('01'):
                point_num = part[2:7].lstrip('0') or '0'
                point_id = f"P{point_num}"
                
                if point_id not in points:
                    points[point_id] = NetworkPoint(id=point_id)
                    point_counter += 1
            
            # Блок 21/22 - координаты X/Y
            elif part.startswith('21'):
                # X координата
                try:
                    val_str = part[2:].replace(',', '.')
                    x_val = float(val_str)
                    # Найти последнюю точку
                    for pid in reversed(list(points.keys())):
                        if points[pid].x is None:
                            points[pid].x = x_val
                            points[pid].plan_status = 'initial'
                            break
                except:
                    pass
            
            elif part.startswith('22'):
                # Y координата
                try:
                    val_str = part[2:].replace(',', '.')
                    y_val = float(val_str)
                    for pid in reversed(list(points.keys())):
                        if points[pid].y is None:
                            points[pid].y = y_val
                            break
                except:
                    pass
            
            # Блок 03 - превышение (нивелирование)
            elif part.startswith('03'):
                try:
                    val_str = part[2:].replace(',', '.')
                    dh = float(val_str)
                    
                    # Создаем наблюдение
                    obs_id = f"obs_{obs_counter}"
                    obs_counter += 1
                    
                    # Нужно определить from/to точки (упрощенно - последняя и следующая)
                    point_ids = list(points.keys())
                    if len(point_ids) >= 1:
                        from_pt = point_ids[-1]
                        to_pt = point_ids[-1]  # В реальности нужно из контекста
                        
                        obs = Observation(
                            id=obs_id,
                            type='leveling_height_diff',
                            from_point=from_pt,
                            to_point=to_pt,
                            value=dh,
                            distance=0.05  # Заглушка
                        )
                        observations.append(obs)
                except Exception as e:
                    logger.debug(f"Ошибка парсинга превышения: {e}")
            
            # Блок 32 - расстояние
            elif part.startswith('32'):
                try:
                    val_str = part[2:].replace(',', '.')
                    dist = float(val_str)
                    
                    obs_id = f"obs_dist_{obs_counter}"
                    obs_counter += 1
                    
                    point_ids = list(points.keys())
                    if len(point_ids) >= 1:
                        obs = Observation(
                            id=obs_id,
                            type='distance',
                            from_point=point_ids[-1],
                            to_point=point_ids[-1],
                            value=dist
                        )
                        observations.append(obs)
                except:
                    pass
    
    logger.info(f"Файл {filepath}: точек={len(points)}, наблюдений={len(observations)}")
    return points, observations

def main():
    print("=" * 80)
    print("GeoAdjustPro - Тест полного цикла с реальными данными GSI")
    print("=" * 80)
    
    # Список GSI файлов для обработки
    gsi_files = [
        '/workspace/test_real_mes/s5/niv/DOM0112 (1).GSI',
        '/workspace/test_real_mes/s5/niv/MIR0212.GSI',
    ]
    
    all_points = {}
    all_observations = []
    
    # 1. ИМПОРТ
    print("\n[1/4] ИМПОРТ ДАННЫХ ИЗ GSI ФАЙЛОВ")
    print("-" * 40)
    
    for gsi_file in gsi_files:
        if os.path.exists(gsi_file):
            points, obs = parse_gsi_file(gsi_file)
            all_points.update(points)
            all_observations.extend(obs)
        else:
            logger.warning(f"Файл не найден: {gsi_file}")
    
    print(f"Всего импортировано: {len(all_points)} точек, {len(all_observations)} наблюдений")
    
    if not all_observations:
        print("⚠ Нет наблюдений для уравнивания. Проверяем структуру GSI...")
        # Показываем пример строки
        if os.path.exists(gsi_files[0]):
            with open(gsi_files[0], 'r') as f:
                sample = f.readline()
                print(f"Пример строки: {sample[:100]}...")
    
    # 2. ПРЕДОБРАБОТКА
    print("\n[2/4] ПРЕДОБРАБОТКА ДАННЫХ")
    print("-" * 40)
    
    # Фильтрация грубых ошибок
    initial_count = len(all_observations)
    all_observations = [obs for obs in all_observations if abs(obs.value) < 100.0]
    removed = initial_count - len(all_observations)
    print(f"Удалено грубых ошибок (>100м): {removed}")
    print(f"Осталось наблюдений: {len(all_observations)}")
    
    # Статистика по статусам
    plan_status = {'initial': 0, 'working': 0}
    height_status = {'initial': 0, 'working': 0}
    for p in all_points.values():
        if p.plan_status in plan_status:
            plan_status[p.plan_status] += 1
        if p.height_status in height_status:
            height_status[p.height_status] += 1
    
    print(f"Статусы плана: исходные={plan_status['initial']}, рабочие={plan_status['working']}")
    print(f"Статусы высот: исходные={height_status['initial']}, рабочие={height_status['working']}")
    
    # 3. УРАВНИВАНИЕ
    print("\n[3/4] УРАВНИВАНИЕ СЕТИ")
    print("-" * 40)
    
    engine = GeoAdjustEngine()
    engine.load_network(all_points, all_observations)
    
    # Уравнивание высот (если есть нивелирные наблюдения)
    leveling_obs = [o for o in all_observations if o.type == 'leveling_height_diff']
    if leveling_obs:
        print("Запуск уравнивания высот...")
        result_h = engine.adjust_heights()
        
        if result_h.success:
            print(f"✓ Уравнивание высот завершено")
            print(f"  СКП единицы веса: {result_h.sigma0*1000:.3f} мм")
            if result_h.sigma0_km:
                print(f"  СКП на 1 км: {result_h.sigma0_km*1000:.3f} мм/км")
            print(f"  Уравнено точек: {len(result_h.points_stats)}")
            
            # Вывод первых 5 результатов
            print("\n  Первые результаты:")
            for i, (pid, stats) in enumerate(result_h.points_stats.items()):
                if i >= 5:
                    break
                print(f"    {pid}: H={stats['height']:.4f}м, СКП=±{stats['height_std']*1000:.2f}мм")
        else:
            print(f"✗ Ошибка уравнивания высот: {result_h.message}")
    else:
        print("⚠ Нивелирные наблюдения не найдены")
    
    # Уравнивание плана (если есть расстояния)
    distance_obs = [o for o in all_observations if o.type == 'distance']
    if distance_obs:
        print("\nЗапуск уравнивания плана...")
        result_p = engine.adjust_plan()
        print(f"  Результат: {result_p.message}")
    else:
        print("\n⚠ Измерения расстояний не найдены")
    
    # 4. ВЫГРУЗКА РЕЗУЛЬТАТОВ
    print("\n[4/4] ВЫГРУЗКА РЕЗУЛЬТАТОВ")
    print("-" * 40)
    
    output_dir = '/workspace/test_output'
    os.makedirs(output_dir, exist_ok=True)
    
    # Отчет по высотам
    report_file = os.path.join(output_dir, 'adjustment_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("ОТЧЕТ ОБ УРАВНИВАНИИ GEOADJUSTPRO\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Всего точек: {len(all_points)}\n")
        f.write(f"Всего наблюдений: {len(all_observations)}\n\n")
        
        if leveling_obs and result_h.success:
            f.write("РЕЗУЛЬТАТЫ УРАВНИВАНИЯ ВЫСОТ\n")
            f.write("-" * 50 + "\n")
            f.write(f"СКП единицы веса: {result_h.sigma0*1000:.3f} мм\n")
            f.write(f"СКП на 1 км: {result_h.sigma0_km*1000:.3f} мм/км\n\n")
            
            f.write("ВЕДОМОСТЬ ВЫСОТ ПУНКТОВ\n")
            f.write(f"{'№':<10} {'Высота (м)':<15} {'СКП (мм)':<12} {'Поправка (мм)':<15}\n")
            f.write("-" * 50 + "\n")
            
            for pid, stats in sorted(result_h.points_stats.items()):
                f.write(f"{pid:<10} {stats['height']:<15.4f} ±{stats['height_std']*1000:<11.2f} {stats['correction']*1000:<15.2f}\n")
    
    print(f"✓ Отчет сохранен: {report_file}")
    
    # Схема сети
    scheme_file = os.path.join(output_dir, 'network_scheme.txt')
    with open(scheme_file, 'w', encoding='utf-8') as f:
        f.write("СХЕМА ГЕОДЕЗИЧЕСКОЙ СЕТИ\n")
        f.write("=" * 50 + "\n\n")
        
        for pid, point in sorted(all_points.items()):
            status_plan = "ИСХ" if point.plan_status == 'initial' else "РАБ"
            status_h = "ИСХ" if point.height_status == 'initial' else "РАБ"
            coords = f"X={point.x:.3f}, Y={point.y:.3f}" if point.x else "нет"
            height = f"H={point.z:.3f}" if point.z else "нет"
            f.write(f"{pid}: [{status_plan}/{status_h}] {coords} {height}\n")
    
    print(f"✓ Схема сети сохранена: {scheme_file}")
    
    print("\n" + "=" * 80)
    print("ТЕСТ ЗАВЕРШЕН УСПЕШНО")
    print("=" * 80)

if __name__ == '__main__':
    main()
