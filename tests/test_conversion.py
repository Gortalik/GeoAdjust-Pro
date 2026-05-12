#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the main window processing
"""

import sys
from pathlib import Path

# Add the src directory to the path

def test_main_window_conversion():
    """Test the main window observation conversion with new dict format"""
    print("Testing main window observation conversion...")

    from geoadjust.io.formats.sdr import SDRParser

    # Parse SDR data
    parser = SDRParser()
    data = parser.parse(Path("test_real_mes/b_g/plan/badgro16093_const.sdr"))

    # Get first few observations and convert to dict format like new import
    observations = data.get('observations', [])[:3]

    dict_observations = []
    for obs in observations:
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
        dict_observations.append(obs_dict)

    print(f"Testing with {len(dict_observations)} dict observations")

    # Test the reverse conversion (from dict back to CombinedObservation) - like _convert_observations_to_objects
    print("Testing reverse conversion...")
    from geoadjust.core.network.models import CombinedObservation

    for obs_dict in dict_observations:
        print(f"Converting dict with keys: {list(obs_dict.keys())}")
        print(f"  horizontal_angle present: {'horizontal_angle' in obs_dict and obs_dict['horizontal_angle'] is not None}")

        # Check if it should be converted (has combined fields)
        has_combined_fields = ('horizontal_angle' in obs_dict and obs_dict['horizontal_angle'] is not None and
                              'zenith_angle' in obs_dict and obs_dict['zenith_angle'] is not None and
                              'slope_distance' in obs_dict and obs_dict['slope_distance'] is not None)

        print(f"  Has combined fields: {has_combined_fields}")

        if has_combined_fields:
            try:
                combined_obs = CombinedObservation(
                    obs_id=obs_dict.get('obs_id', ''),
                    from_setup_id=obs_dict.get('from_setup_id', ''),
                    from_point_id=obs_dict.get('from_point_id', ''),
                    to_point_id=obs_dict.get('to_point_id', ''),
                    face_position=obs_dict.get('face_position'),
                    horizontal_angle=obs_dict.get('horizontal_angle'),
                    zenith_angle=obs_dict.get('zenith_angle'),
                    slope_distance=obs_dict.get('slope_distance'),
                    raw_line=obs_dict.get('raw_line')
                )
                print(f"  Successfully converted back to CombinedObservation: {combined_obs.from_point_id} -> {combined_obs.to_point_id}, h_angle={combined_obs.horizontal_angle}")
            except Exception as e:
                print(f"  Error converting back: {e}")
        else:
            print("  Keeping as dict")

if __name__ == "__main__":
    print("Testing main window processing...")

    try:
        test_main_window_conversion()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

    print("Testing completed.")