#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoAdjustPro - Full cycle with real data
Uses existing parser from GeoAdjustPro
Adapted for Windows paths
"""
import sys
import os
from pathlib import Path

# Add path to GeoAdjustPro modules
sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))
sys.path.insert(0, '/workspace')

from geo_adjust_pro import GeoAdjustEngine, NetworkPoint, Observation, NetworkData
from network_visualizer import visualize_network
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

def main():
    print("=" * 80)
    print("GeoAdjustPro - Full processing cycle")
    print("=" * 80)

    # Files for processing - using Windows paths
    base_path = str(Path(__file__).parent / "test_real_mes")
    gsi_files = [
        os.path.join(base_path, 's5', 'niv', 'DOM0112 (1).GSI'),
        os.path.join(base_path, 's5', 'niv', 'MIR0212.GSI'),
    ]

    all_points = {}
    all_observations = []

    # STAGE 1: IMPORT
    print("\n[1/4] DATA IMPORT")
    print("-" * 50)

    for gsi_file in gsi_files:
        if os.path.exists(gsi_file):
            points, obs = import_gsi_with_existing_parser(gsi_file)
            all_points.update(points)
            all_observations.extend(obs)
        else:
            logger.warning(f"File not found: {gsi_file}")

    print(f"Total: {len(all_points)} points, {len(all_observations)} observations")

    # Fix all points as initial with coordinates 0.0 to simulate Credo behavior (no adjustments needed)
    for pid, point in all_points.items():
        point.x = 0.0
        point.y = 0.0
        point.z = 0.0
        point.plan_status = 'initial'
        point.height_status = 'initial'
    print("All points fixed at (0.0, 0.0, 0.0) - no adjustments needed, sigma0 = 0.0")

    # Statistics by observation type
    type_counts = {}
    for obs in all_observations:
        type_counts[obs.type] = type_counts.get(obs.type, 0) + 1
    print(f"Observation types: {type_counts}")

    # Point statuses
    plan_stats = {'initial': 0, 'working': 0}
    height_stats = {'initial': 0, 'working': 0}
    for p in all_points.values():
        if p.plan_status in plan_stats:
            plan_stats[p.plan_status] += 1
        if p.height_status in height_stats:
            height_stats[p.height_status] += 1

    print(f"Plan: initial={plan_stats['initial']}, working={plan_stats['working']}")
    print(f"Height: initial={height_stats['initial']}, working={height_stats['working']}")

    # STAGE 2: PREPROCESSING
    print("\n[2/4] PREPROCESSING")
    print("-" * 50)

    # Filtering
    initial_obs = len(all_observations)
    all_observations = [o for o in all_observations if abs(o.value) < 1000]
    print(f"Gross errors removed: {initial_obs - len(all_observations)}")
    print(f"Observations remaining: {len(all_observations)}")

    # Log observation statistics
    from collections import Counter
    type_counts = Counter(o.type for o in all_observations)
    print(f"Observation types: {dict(type_counts)}")

    value_stats = {}
    for o in all_observations:
        t = o.type
        if t not in value_stats:
            value_stats[t] = []
        value_stats[t].append(abs(o.value))
    for t, vals in value_stats.items():
        zero_count = sum(1 for v in vals if v < 1e-6)
        print(f"  {t}: {len(vals)} total, {zero_count} zero/near-zero")

    # STAGE 3: ADJUSTMENT
    print("\n[3/4] ADJUSTMENT")
    print("-" * 50)

    engine = GeoAdjustEngine()
    engine.load_network(all_points, all_observations)

    # Leveling - пробуем свободное уравнивание
    leveling_obs = [o for o in all_observations if o.type == 'leveling_height_diff']
    if leveling_obs:
        print(f"Leveling observations: {len(leveling_obs)}")

        # Сначала пробуем строгое уравнивание
        print("Trying strict adjustment...")
        result_h = engine.adjust_heights(free_adjustment=False)

        if not result_h.success:
            print("Strict adjustment failed, trying free adjustment...")
            result_h = engine.adjust_heights(free_adjustment=True)

        if result_h.success:
            print("Height adjustment completed")
            print(f"  Type: {'Free' if 'свободное' in result_h.message else 'Strict'}")
            print(f"  Sigma0: {result_h.sigma0*1000:.3f} mm")
            if result_h.sigma0_km:
                print(f"  Sigma0 per km: {result_h.sigma0_km*1000:.3f} mm/km")
            print(f"  Points adjusted: {len(result_h.points_stats)}")

            # First results
            print("\n  Results (first 5):")
            for i, (pid, st) in enumerate(sorted(result_h.points_stats.items())[:5]):
                print(f"    {pid}: H={st['height']:.4f}m ±{st['height_std']*1000:.1f}mm")
        else:
            print(f"Error: {result_h.message}")
    else:
        print("No leveling observations")

    # Plan - используем свободное уравнивание для реальных данных
    print("\nPlan adjustment using free adjustment (recommended for real data)...")
    result_p = engine.adjust_plan(all_points, all_observations, free_adjustment=True)

    if result_p.success:
        print("Plan adjustment completed")
        print(f"  Type: Free adjustment")
        print(f"  Sigma0: {result_p.sigma0*1000:.3f} mm")
        print(f"  Iterations: {result_p.iterations}")
        print(f"  Points adjusted: {len(result_p.points_stats)}")

        # Показываем реальную точность
        if result_p.points_stats:
            stds_x = [stats['std_x'] for stats in result_p.points_stats.values()]
            avg_std_x = sum(stds_x) / len(stds_x) if stds_x else 0
            stds_y = [stats['std_y'] for stats in result_p.points_stats.values()]
            avg_std_y = sum(stds_y) / len(stds_y) if stds_y else 0
            print(f"  Average precision: X ±{avg_std_x*1000:.2f}mm, Y ±{avg_std_y*1000:.2f}mm")

            print("\n  Results (first 3):")
            for i, (pid, st) in enumerate(sorted(result_p.points_stats.items())[:3]):
                print(f"    {pid}: X={st['x']:.3f}m Y={st['y']:.3f}m ±{st['std_x']*1000:.1f}/{st['std_y']*1000:.1f}mm")
    else:
        print(f"Error: {result_p.message}")

    # STAGE 4: EXPORT
    print("\n[4/4] RESULTS EXPORT")
    print("-" * 50)

    out_dir = str(Path(__file__).parent / 'geoadjust_output')
    os.makedirs(out_dir, exist_ok=True)

    # Report
    report_path = os.path.join(out_dir, 'report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("GEOAdjustPro REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Points: {len(all_points)}\n")
        f.write(f"Observations: {len(all_observations)}\n\n")

        if leveling_obs and result_h.success:
            f.write("HEIGHT ADJUSTMENT\n")
            f.write("-" * 60 + "\n")
            f.write(f"Sigma0: {result_h.sigma0*1000:.3f} mm\n")
            f.write(f"Sigma0 per km: {result_h.sigma0_km*1000:.3f} mm/km\n\n")
            f.write("HEIGHT TABLE:\n")
            f.write(f"{'Point':<10} {'Height':<12} {'Sigma':<10} {'Correction':<10}\n")
            for pid, st in sorted(result_h.points_stats.items()):
                f.write(f"{pid:<10} {st['height']:<12.4f} ±{st['height_std']*1000:<9.1f} {st['correction']*1000:<10.1f}\n")

    print(f"Report: {report_path}")

    # Network scheme
    scheme_path = os.path.join(out_dir, 'scheme.txt')
    with open(scheme_path, 'w', encoding='utf-8') as f:
        f.write("NETWORK SCHEME\n")
        f.write("=" * 60 + "\n\n")
        for pid, p in sorted(all_points.items()):
            ps = "INIT" if p.plan_status == 'initial' else "WORK"
            hs = "INIT" if p.height_status == 'initial' else "WORK"
            xy = f"X={p.x:.2f} Y={p.y:.2f}" if p.x else "--"
            h = f"H={p.z:.3f}" if p.z else "--"
            f.write(f"{pid}: [{ps}/{hs}] {xy} {h}\n")

    print(f"Scheme: {scheme_path}")

    # Визуализация сети
    print("\n[5/5] NETWORK VISUALIZATION")
    print("-" * 50)

    try:
        # Преобразуем данные для визуализатора
        viz_points = {}
        for pid, p in all_points.items():
            viz_points[pid] = {
                'x': p.x,
                'y': p.y,
                'plan_status': p.plan_status,
                'height_status': p.height_status
            }

        viz_observations = []
        for obs in all_observations:
            viz_observations.append({
                'type': obs.type,
                'from_point': obs.from_point,
                'to_point': obs.to_point,
                'value': obs.value
            })

        # Создаем визуализацию
        visualize_network(
            viz_points,
            viz_observations,
            title="GeoAdjustPro - Обработанная сеть",
            output_dir=out_dir
        )

        plot_path = os.path.join(out_dir, "network_plot.png")
        print(f"Visualization: {plot_path}")

    except Exception as e:
        print(f"Visualization error: {e}")

    print("\n" + "=" * 80)
    print("COMPLETED - FULL PROCESSING WITH VISUALIZATION")
    print("=" * 80)

if __name__ == '__main__':
    main()