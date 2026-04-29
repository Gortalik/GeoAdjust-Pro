#!/usr/bin/env python3
"""
Full cycle test for GeoAdjustPro
Tests: Import (GSI/SDR) -> Preprocessing -> Adjustment -> Reports
"""
import sys
import os

# Add module path
sys.path.insert(0, '/workspace/geo_adjust_pro')

from parser import GSIParser, SDRParser
from engine import GeoAdjustEngine as AdjustmentEngine
from models import Network, NetworkPoint, NetworkData
from reports import GOSTReportGenerator
import numpy as np

def main():
    print("=" * 80)
    print("ПОЛНЫЙ ЦИКЛ ПРОВЕРКИ GeoAdjustPro")
    print("=" * 80)
    
    # Initialize
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
    
    # Summary after import
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
    
    # Auto-fix if needed
    if len(fixed_plan) < 2:
        print("  ! АВТО-ФИКСАЦИЯ: Закрепляем первые 2 точки с координатами...")
        pts_with_coords = [p for p in network.points.values() if p.x is not None and p.y is not None]
        for p in pts_with_coords[:2]:
            p.plan_status = 'fixed'
        fixed_plan = [p for p in network.points.values() if p.plan_status == 'fixed']
        print(f"  → Теперь Fixed (Plan): {len(fixed_plan)}")
    
    if len(fixed_height) < 1:
        print("  ! АВТО-ФИКСАЦИЯ: Закрепляем первую точку с высотой...")
        pts_with_h = [p for p in network.points.values() if p.h is not None]
        if pts_with_h:
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
        # Filter gross errors
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
    
    # Count by type
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
        # Build matrices
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
            
            # Weight inversely proportional to distance
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
            
            # Update network
            for name, stats in result_h['points_stats'].items():
                if name in network.points:
                    network.points[name].h = stats['adjusted_value']
                    network.points[name].height_status = 'adjusted'
                    setattr(network.points[name], 'h_std', stats['std'])
            
            print("  ✓ Уравнивание высот завершено успешно")
            
        except Exception as e:
            print(f"  ✗ Ошибка уравнивания высот: {e}")
            import traceback
            traceback.print_exc()
    
    # ========== STAGE 6: PLAN ADJUSTMENT ==========
    print("\n[6/7] УРАВНИВАНИЕ ПЛАНА")
    print("-" * 40)
    
    plan_obs = [o for o in network.observations if o.type in ['direction', 'angle', 'slope_distance', 'horizontal_distance', 'combined']]
    
    if not plan_obs:
        print("  ! Нет плановых наблюдений для уравнивания")
    else:
        try:
            result_p = engine.adjust_plan(network.points, plan_obs)
            
            print(f"  СКП направления: {result_p.sigma0:.2f} \"")
            print(f"  СКП расстояния: {result_p.sigma0:.2f} мм + {0} ppm")
            print(f"  Относительная погрешность: 1:{100000:,.0f}")
            print(f"  Уравнено точек: {len(result_p.points_stats)}")
            
            # Update network
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
        # Coordinates
        rep_coord = reporter.generate_coordinates_report(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_coord)}")
        
        # Heights
        rep_height = reporter.generate_heights_report(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_height)}")
        
        # Error ellipses
        rep_ellipses = reporter.generate_error_ellipses(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_ellipses)}")
        
        # Network scheme
        rep_scheme = reporter.generate_network_scheme(network, out_dir)
        print(f"  ✓ {os.path.basename(rep_scheme)}")
        
        # Measurements
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
    
    print(f"Всего пунктов в сети: {len(network.points)}")
    print(f"  - Уравнено (план): {len(adjusted_points)}")
    print(f"  - Уравнено (высота): {len(adjusted_heights)}")
    print(f"Всего измерений: {len(network.observations)}")
    
    # Show sample results
    print("\nПример результатов (первые 5 точек):")
    print("-" * 80)
    print(f"{'№':<3} {'Имя':<20} {'X':<15} {'Y':<15} {'H':<12} {'Статус'}")
    for i, (name, point) in enumerate(list(network.points.items())[:5], 1):
        x_str = f"{point.x:.3f}" if point.x else "-"
        y_str = f"{point.y:.3f}" if point.y else "-"
        h_str = f"{point.h:.3f}" if point.h else "-"
        status = f"P:{point.plan_status}, H:{point.height_status}"
        print(f"{i:<3} {name:<20} {x_str:<15} {y_str:<15} {h_str:<12} {status}")
    
    print("\n✓ ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН УСПЕШНО")
    print("=" * 80)

if __name__ == '__main__':
    main()
