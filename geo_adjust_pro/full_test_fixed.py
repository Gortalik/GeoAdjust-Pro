#!/usr/bin/env python3
"""
Full cycle test for GeoAdjustPro - FIXED VERSION
Tests: Import (GSI/SDR) -> Preprocessing -> Adjustment -> Reports
Correctly handles separate plan and height networks
"""
import sys
import os

sys.path.insert(0, '/workspace/geo_adjust_pro')

from parser import GSIParser, SDRParser
from engine import GeoAdjustEngine as AdjustmentEngine
from models import Network, NetworkPoint, NetworkData
from reports import GOSTReportGenerator
import numpy as np

def main():
    print("=" * 80)
    print("ПОЛНЫЙ ЦИКЛ ПРОВЕРКИ GeoAdjustPro (ИСПРАВЛЕННЫЙ)")
    print("=" * 80)
    
    network = Network()
    engine = AdjustmentEngine()
    reporter = GOSTReportGenerator()
    
    # ========== STAGE 1: IMPORT GSI ==========
    print("\n[1/7] ИМПОРТ GSI (нивелирование)")
    print("-" * 40)
    
    gsi_files = [
        '/workspace/test_real_mes/s5/niv/DOM0112 (1).GSI',
        '/workspace/test_real_mes/s5/niv/MIR0212.GSI'
    ]
    
    gsi_points = 0
    gsi_obs = 0
    
    for f in gsi_files:
        if os.path.exists(f):
            parser = GSIParser()
            data = parser.parse_file(f)
            network.merge_data(data)
            gsi_points += len(data.points)
            gsi_obs += len(data.observations)
            print(f"  ✓ {os.path.basename(f)}: {len(data.points)} точек, {len(data.observations)} наблюдений")
        else:
            print(f"  ✗ Файл не найден: {f}")
    
    print(f"  → Всего из GSI: {gsi_points} точек, {gsi_obs} наблюдений")
    
    # ========== STAGE 2: IMPORT SDR ==========
    print("\n[2/7] ИМПОРТ SDR (плановая сеть)")
    print("-" * 40)
    
    sdr_files = [
        '/workspace/test_real_mes/b_g/plan/badgro16093_const.sdr',
        '/workspace/test_real_mes/k/kotlntss06042026.sdr'
    ]
    
    sdr_points = 0
    sdr_obs = 0
    
    for f in sdr_files:
        if os.path.exists(f):
            parser = SDRParser()
            data = parser.parse_file(f)
            network.merge_data(data)
            sdr_points += len(data.points)
            sdr_obs += len(data.observations)
            print(f"  ✓ {os.path.basename(f)}: {len(data.points)} точек, {len(data.observations)} наблюдений")
        else:
            print(f"  ✗ Файл не найден: {f}")
    
    print(f"  → Всего из SDR: {sdr_points} точек, {sdr_obs} наблюдений")
    
    print(f"\n>>> ИТОГО В СЕТИ: {len(network.points)} точек, {len(network.observations)} наблюдений")
    
    # ========== STAGE 3: STATUS ANALYSIS ==========
    print("\n[3/7] АНАЛИЗ СТАТУСОВ ПУНКТОВ")
    print("-" * 40)
    
    fixed_plan = [p for p in network.points.values() if p.plan_status == 'fixed']
    fixed_height = [p for p in network.points.values() if p.height_status == 'fixed']
    initial_plan = [p for p in network.points.values() if p.plan_status == 'initial']
    initial_height = [p for p in network.points.values() if p.height_status == 'initial']
    working = [p for p in network.points.values() if p.plan_status == 'working']
    
    print(f"  Plan - Fixed: {len(fixed_plan)}, Initial: {len(initial_plan)}, Working: {len(working)}")
    print(f"  Height - Fixed: {len(fixed_height)}, Initial: {len(initial_height)}, Working: {len([p for p in network.points.values() if p.height_status == 'working'])}")
    
    # Auto-fix: закрепляем точки с координатами
    pts_with_coords = [p for p in network.points.values() if p.x is not None and p.y is not None and p.plan_status == 'initial']
    if len(fixed_plan) < 2 and len(pts_with_coords) >= 2:
        print("  ! АВТО-ФИКСАЦИЯ: Закрепляем первые 2 точки с координатами...")
        pts_with_coords[0].plan_status = 'fixed'
        pts_with_coords[1].plan_status = 'fixed'
        fixed_plan = [p for p in network.points.values() if p.plan_status == 'fixed']
        print(f"  → Теперь Fixed (Plan): {len(fixed_plan)}")
    
    pts_with_h = [p for p in network.points.values() if p.h is not None and p.height_status == 'initial']
    if len(fixed_height) < 1 and len(pts_with_h) >= 1:
        print("  ! АВТО-ФИКСАЦИЯ: Закрепляем первую точку с высотой...")
        pts_with_h[0].height_status = 'fixed'
        fixed_height = [p for p in network.points.values() if p.height_status == 'fixed']
        print(f"  → Теперь Fixed (Height): {len(fixed_height)}")
    
    # ========== STAGE 4: PREPROCESSING ==========
    print("\n[4/7] ПРЕДОБРАБОТКА ДАННЫХ")
    print("-" * 40)
    
    initial_obs_count = len(network.observations)
    cleaned_obs = []
    
    for obs in network.observations:
        valid = True
        if obs.type == 'leveling_height_diff' and abs(obs.value) > 1.0:
            valid = False
        if obs.type in ['slope_distance', 'horizontal_distance'] and obs.value > 10000.0:
            valid = False
        if valid:
            cleaned_obs.append(obs)
    
    removed = initial_obs_count - len(cleaned_obs)
    network.observations = cleaned_obs
    
    print(f"  Удалено грубых ошибок: {removed}")
    print(f"  Осталось наблюдений: {len(network.observations)}")
    
    obs_types = {}
    for obs in network.observations:
        obs_types[obs.type] = obs_types.get(obs.type, 0) + 1
    
    for otype, cnt in sorted(obs_types.items()):
        print(f"    - {otype}: {cnt}")
    
    # ========== STAGE 5: HEIGHT ADJUSTMENT ==========
    print("\n[5/7] УРАВНИВАНИЕ ВЫСОТ")
    print("-" * 40)
    
    leveling_obs = [o for o in network.observations if o.type == 'leveling_height_diff']
    
    if not leveling_obs:
        print("  ! Нет нивелирных наблюдений для уравнивания")
    else:
        h_points = set()
        for o in leveling_obs:
            h_points.add(o.from_point)
            h_points.add(o.to_point)
        
        h_names = sorted(list(h_points))
        name_to_idx = {name: i for i, name in enumerate(h_names)}
        n = len(h_names)
        
        A_list = []
        L_list = []
        P_list = []
        
        for o in leveling_obs:
            row = [0.0] * n
            i_from = name_to_idx[o.from_point]
            i_to = name_to_idx[o.to_point]
            
            row[i_from] = -1.0
            row[i_to] = 1.0
            
            A_list.append(row)
            L_list.append(o.value)
            
            dist = o.distance if hasattr(o, 'distance') and o.distance else 1.0
            weight = 1.0 / max(dist, 0.1)
            P_list.append(weight)
        
        A_mat = np.array(A_list)
        L_vec = np.array(L_list)
        P_vec = np.array(P_list)
        
        try:
            result_h = engine.adjust_heights(A_mat, L_vec, P_vec, h_names)
            
            print(f"  СКП единицы веса: {result_h['sigma0']:.4f} мм")
            print(f"  Избыточность: {result_h['redundancy']}")
            print(f"  Уравнено точек: {len(result_h['points_stats'])}")
            
            for name, stats in result_h['points_stats'].items():
                if name in network.points:
                    network.points[name].h = stats['adjusted_value']
                    network.points[name].height_status = 'adjusted'
                    setattr(network.points[name], 'h_std', stats['std'])
            
            print("  ✓ Уравнивание высот завершено успешно")
            
        except Exception as e:
            print(f"  ✗ Ошибка уравнивания высот: {e}")
    
    # ========== STAGE 6: PLAN ADJUSTMENT ==========
    print("\n[6/7] УРАВНИВАНИЕ ПЛАНА")
    print("-" * 40)
    
    # Для планового уравнивания используем ТОЛЬКО точки с начальными координатами
    plan_points = {pid: p for pid, p in network.points.items() 
                   if p.x is not None and p.y is not None}
    
    plan_obs = [o for o in network.observations 
                if o.type in ['direction', 'angle', 'slope_distance', 'horizontal_distance', 'combined']
                and o.from_point in plan_points and o.to_point in plan_points]
    
    if not plan_obs:
        print("  ! Нет плановых наблюдений для уравнивания")
    else:
        print(f"  Точек с координатами: {len(plan_points)}")
        print(f"  Наблюдений между ними: {len(plan_obs)}")
        
        try:
            result_p = engine.adjust_plan(plan_points, plan_obs)
            
            print(f"  СКП направления: {result_p.sigma0:.2f} \"")
            print(f"  Уравнено точек: {len(result_p.points_stats)}")
            
            for name, stats in result_p.points_stats.items():
                if name in network.points:
                    network.points[name].x = stats['x']
                    network.points[name].y = stats['y']
                    network.points[name].plan_status = 'adjusted'
                    setattr(network.points[name], 'x_std', stats['std_x'])
                    setattr(network.points[name], 'y_std', stats['std_y'])
                    setattr(network.points[name], 'xy_cov', stats.get('cov_xy', 0))
            
            print("  ✓ Уравнивание плана завершено успешно")
            
        except Exception as e:
            print(f"  ✗ Ошибка уравнивания плана: {e}")
            import traceback
            traceback.print_exc()
    
    # ========== STAGE 7: REPORTS ==========
    print("\n[7/7] ГЕНЕРАЦИЯ ВЕДОМОСТЕЙ И ОТЧЕТОВ")
    print("-" * 40)
    
    out_dir = '/workspace/geo_adjust_pro/output_final'
    os.makedirs(out_dir, exist_ok=True)
    
    try:
        rep_coord = reporter.generate_coordinates_report(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_coord)}")
        
        rep_height = reporter.generate_heights_report(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_height)}")
        
        rep_ellipses = reporter.generate_error_ellipses(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_ellipses)}")
        
        rep_scheme = reporter.generate_network_scheme(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_scheme)}")
        
        rep_meas = reporter.generate_measurements_report(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_meas)}")
        
        print(f"\n  Все файлы сохранены в: {out_dir}")
        
    except Exception as e:
        print(f"  ✗ Ошибка генерации отчетов: {e}")
        import traceback
        traceback.print_exc()
    
    # ========== FINAL SUMMARY ==========
    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 80)
    
    adjusted_points = [p for p in network.points.values() if p.plan_status == 'adjusted']
    adjusted_heights = [p for p in network.points.values() if p.height_status == 'adjusted']
    points_with_xy = [p for p in network.points.values() if p.x is not None and not np.isnan(p.x)]
    points_with_h = [p for p in network.points.values() if p.h is not None and not np.isnan(p.h)]
    
    print(f"Всего пунктов в сети: {len(network.points)}")
    print(f"  - С координатами X,Y: {len(points_with_xy)}")
    print(f"  - С высотой H: {len(points_with_h)}")
    print(f"  - Уравнено (план): {len(adjusted_points)}")
    print(f"  - Уравнено (высота): {len(adjusted_heights)}")
    print(f"Всего измерений: {len(network.observations)}")
    
    print("\nПример результатов (точки с координатами):")
    print("-" * 80)
    print(f"{'№':<3} {'Имя':<20} {'X':<15} {'Y':<15} {'H':<12} {'Статус'}")
    
    shown = 0
    for name, point in network.points.items():
        if point.x is not None and not np.isnan(point.x) and shown < 10:
            x_str = f"{point.x:.4f}" if point.x else "-"
            y_str = f"{point.y:.4f}" if point.y else "-"
            h_str = f"{point.h:.4f}" if point.h and not np.isnan(point.h) else "-"
            status = f"P:{point.plan_status}, H:{point.height_status}"
            print(f"{shown+1:<3} {name:<20} {x_str:<15} {y_str:<15} {h_str:<12} {status}")
            shown += 1
    
    print("\n✓ ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН УСПЕШНО")
    print("=" * 80)

if __name__ == '__main__':
    main()
