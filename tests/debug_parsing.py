#!/usr/bin/env python3
import sys
from pathlib import Path

# Add the GeoAdjustPro src to path
sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser

def debug_gsi_parsing(file_path):
    print(f"Parsing {file_path}")
    parser = GSIParser()
    result = parser.parse(Path(file_path))
    
    print(f"Success: {result['success']}")
    print(f"Format: {result['format']} version {result['version']}")
    print(f"Total observations: {result['num_observations']}")
    print(f"Total points: {result['num_points']}")
    print(f"Total station sessions: {result['num_station_sessions']}")
    
    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result['errors'][:5]:
            print(f"  Line {error['line']}: {error['message']}")
    
    if result['warnings']:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for warning in result['warnings'][:5]:
            print(f"  Line {warning['line']}: {warning['message']}")
    
    # Show observation types breakdown
    stats = parser.get_statistics()
    print(f"\nObservation types breakdown:")
    for obs_type, count in stats['by_type'].items():
        print(f"  {obs_type}: {count}")
    
    # Show first few observations
    print(f"\nFirst 10 observations:")
    for i, obs in enumerate(result['observations'][:10]):
        print(f"  {i+1}: {obs.obs_type} from {obs.from_point} to {obs.to_point} = {obs.value}")
        if hasattr(obs, 'face_position'):
            print(f"       Face position: {obs.face_position}")
        if hasattr(obs, 'station_session_id'):
            print(f"       Station session: {obs.station_session_id}")

if __name__ == "__main__":
    # Test with one of the GSI files
    test_file = "test_real_mes/s5/niv/MIR0212.GSI"
    debug_gsi_parsing(test_file)