#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for import functionality
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

# Test basic imports
try:
    from geoadjust.io.formats.sdr import SDRParser
    from geoadjust.io.formats.dat import DATParser
    print("Basic imports successful")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def test_sdr_import():
    """Test SDR file import"""
    print("Testing SDR import...")

    from geoadjust.io.formats.sdr import SDRParser

    sdr_file = Path("test_real_mes/b_g/plan/badgro16093_const.sdr")
    if not sdr_file.exists():
        print(f"SDR file not found: {sdr_file}")
        return

    parser = SDRParser()
    result = parser.parse(sdr_file)

    print(f"SDR Parse result: {result['success']}")
    print(f"Points: {len(result['points'])}")
    print(f"Observations: {len(result['observations'])}")
    print(f"Setups: {len(result['setups'])}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("Errors:")
        for error in result['errors'][:5]:
            print(f"  {error}")

    return result

def test_dat_import():
    """Test DAT file import"""
    print("Testing DAT import...")

    from geoadjust.io.formats.dat import DATParser

    dat_file = Path("test_real_mes/l/niv/LIH2103.DAT")
    if not dat_file.exists():
        print(f"DAT file not found: {dat_file}")
        return

    parser = DATParser()
    result = parser.parse(dat_file)

    print(f"DAT Parse result: {result['success']}")
    print(f"Points: {len(result['points'])}")
    print(f"Observations: {len(result['observations'])}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("Errors:")
        for error in result['errors'][:5]:
            print(f"  {error}")

    return result

def test_import_dialog_methods():
    """Test the import dialog methods logic"""
    print("Testing import dialog methods...")

    # Test SDR import logic (copied from ImportDialog)
    print("Testing SDR import logic...")
    from geoadjust.io.formats.sdr import SDRParser
    from pathlib import Path

    parser = SDRParser()
    data = parser.parse(Path("test_real_mes/b_g/plan/badgro16093_const.sdr"))

    # Convert to expected format (from ImportDialog._import_sdr)
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
        if hasattr(obs, 'horizontal_angle') or hasattr(obs, 'zenith_angle') or hasattr(obs, 'slope_distance'):
            observations.append(obs)
        else:
            observations.append({
                'from_point': getattr(obs, 'from_point_id', ''),
                'to_point': getattr(obs, 'to_point_id', ''),
                'type': getattr(obs, 'obs_type', 'direction'),
                'value': getattr(obs, 'value', 0),
                'from_setup_id': getattr(obs, 'from_setup_id', ''),
                'face_position': getattr(obs, 'face_position', None)
            })

    sdr_result = {
        'points': points,
        'observations': observations,
        'station_sessions': data.get('station_sessions', []),
        'metadata': {'format': 'SDR'}
    }
    print(f"Station sessions: {len(sdr_result['station_sessions'])}")

    print(f"SDR Dialog result: points={len(sdr_result['points'])}, obs={len(sdr_result['observations'])}")
    print(f"First observation type: {type(sdr_result['observations'][0])}")
    if hasattr(sdr_result['observations'][0], 'obs_type'):
        print(f"First obs type attr: {sdr_result['observations'][0].obs_type}")

    # Test DAT import logic (copied from ImportDialog)
    print("Testing DAT import logic...")
    from geoadjust.io.formats.dat import DATParser

    parser = DATParser()
    data = parser.parse(Path("test_real_mes/l/niv/LIH2103.DAT"))

    # Convert to expected format (from ImportDialog._import_dat)
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
        observations.append({
            'from_point': getattr(obs, 'from_point_id', ''),
            'to_point': getattr(obs, 'to_point_id', ''),
            'type': getattr(obs, 'obs_type', 'direction'),
            'value': getattr(obs, 'value', 0),
            'from_setup_id': getattr(obs, 'from_setup_id', ''),
            'face_position': getattr(obs, 'face_position', None)
        })

    dat_result = {
        'points': points,
        'observations': observations,
        'metadata': {'format': 'DAT'}
    }

    print(f"DAT Dialog result: points={len(dat_result['points'])}, obs={len(dat_result['observations'])}")
    print(f"First observation type: {type(dat_result['observations'][0])}")
    if hasattr(dat_result['observations'][0], 'obs_type'):
        print(f"First obs type attr: {dat_result['observations'][0].obs_type}")

def test_main_window_processing():
    """Test how main window processes imported data"""
    print("Testing main window processing...")

    # Simulate the import result for SDR
    from geoadjust.io.formats.sdr import SDRParser
    from pathlib import Path

    parser = SDRParser()
    data = parser.parse(Path("test_real_mes/b_g/plan/badgro16093_const.sdr"))

    # Simulate ImportDialog._import_sdr result
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
        if hasattr(obs, 'horizontal_angle') or hasattr(obs, 'zenith_angle') or hasattr(obs, 'slope_distance'):
            observations.append(obs)

    imported_data = {
        'points': points,
        'observations': observations,
        'station_sessions': data.get('station_sessions', []),
        'metadata': {'format': 'SDR'}
    }

    print(f"Simulated import: {len(imported_data['points'])} points, {len(imported_data['observations'])} observations, {len(imported_data['station_sessions'])} sessions")

    # Simulate MainWindow._process_imported_data
    print("Simulating main window processing...")

    # Add points to project (simulated)
    for point in imported_data.get('points', []):
        print(f"Adding point: {point['name']} at ({point['x']}, {point['y']}, {point['h']})")

    # Add observations to project (simulated)
    for obs in imported_data.get('observations', []):
        try:
            # Convert to dict like MainWindow does
            from dataclasses import asdict
            obs_dict = asdict(obs)
            print(f"Adding observation: {obs_dict.get('from_point_id', 'unknown')} -> {obs_dict.get('to_point_id', 'unknown')} (type: {obs_dict.get('obs_type', 'unknown')})")
        except Exception as e:
            print(f"Error converting observation: {e}")

    # Check station sessions
    station_sessions = imported_data.get('station_sessions', [])
    if station_sessions:
        print(f"Station sessions: {len(station_sessions)}")
        for session in station_sessions[:3]:  # First 3
            print(f"  Session {session['session_id']}: station {session['station_name']}, {len(session['observations'])} obs")

    print("Main window processing simulation completed.")

if __name__ == "__main__":
    print("Starting comprehensive import tests...")

    try:
        sdr_result = test_sdr_import()
        dat_result = test_dat_import()
        test_import_dialog_methods()
        test_main_window_processing()
    except Exception as e:
        print(f"Error during tests: {e}")
        import traceback
        traceback.print_exc()

    print("All tests completed.")