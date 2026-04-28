#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the import dialog preview fix
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

def test_preview_update():
    """Test the preview update with CombinedObservation objects"""
    print("Testing preview update with CombinedObservation objects...")

    from geoadjust.io.formats.sdr import SDRParser
    from geoadjust.core.network.models import CombinedObservation

    # Parse SDR data
    parser = SDRParser()
    data = parser.parse(Path("test_real_mes/b_g/plan/badgro16093_const.sdr"))

    # Simulate the new import result (dictionaries)
    points = []
    for p in data.get('points', []):
        points.append({
            'name': p.get('point_id', ''),
            'x': p.get('x', 0) or 0,
            'y': p.get('y', 0) or 0,
            'h': p.get('h', 0) or 0,
            'type': p.get('point_type', 'free')
        })

    observations = []
    for obs in data.get('observations', []):
        # Convert to dictionary format like the new import method
        obs_dict = {
            'obs_id': getattr(obs, 'obs_id', ''),
            'from_setup_id': getattr(obs, 'from_setup_id', ''),
            'from_point_id': getattr(obs, 'from_point_id', ''),
            'to_point_id': getattr(obs, 'to_point_id', ''),
            'obs_type': getattr(obs, 'obs_type', 'combined'),
            'face_position': getattr(obs, 'face_position', None),
            'horizontal_angle': getattr(obs, 'horizontal_angle', None),
            'zenith_angle': getattr(obs, 'zenith_angle', None),
            'slope_distance': getattr(obs, 'slope_distance', None),
            'raw_line': getattr(obs, 'raw_line', None)
        }
        observations.append(obs_dict)

    imported_data = {
        'points': points[:5],  # Just first 5 for testing
        'observations': observations[:5],  # Just first 5 for testing
    }

    print(f"Testing with {len(imported_data['points'])} points and {len(imported_data['observations'])} observations")

    # Simulate the _update_preview method logic
    print("Simulating preview table update...")
    for obs in imported_data.get('observations', []):
        print(f"    Obs keys: {list(obs.keys()) if isinstance(obs, dict) else 'not dict'}")
        # All observations are now dictionaries
        obs_type = obs.get('type', obs.get('obs_type', ''))
        from_point = obs.get('from_point', obs.get('from_point_id', ''))
        to_point = obs.get('to_point', obs.get('to_point_id', ''))
        value = obs.get('horizontal_angle', obs.get('value', 0))

        print(f"  Obs: type={obs_type}, from={from_point}, to={to_point}, value={value}, h_angle={obs.get('horizontal_angle')}")

    print("Preview update simulation completed successfully!")

if __name__ == "__main__":
    print("Testing import dialog preview fix...")

    try:
        test_preview_update()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

    print("Testing completed.")