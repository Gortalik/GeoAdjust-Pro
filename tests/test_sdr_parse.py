import sys
import os

# Add src to path

print("Python path:", sys.path[:3])

try:
    from geoadjust.io.formats.sdr import SDRParser
    print("Import successful")
    
    # Parse the SDR file
    parser = SDRParser()
    result = parser.parse_file('test_real_mes/b_g/plan/badgro16093_const.sdr')
    
    print('Parse result:')
    print('  Success:', result.get('success', False))
    print('  Number of setups:', result.get('num_setups', 0))
    print('  Number of observations:', result.get('num_observations', 0))
    print('  Number of points:', len(result.get('points', [])))
    print('  Errors:', len(result.get('errors', [])))
    
    if result.get('points'):
        print('')
        print('First few points:')
        for i, point in enumerate(result['points'][:3]):
            print('  {}: {}'.format(i, point))
    
    if result.get('observations'):
        print('')
        print('First few observations:')
        for i, obs in enumerate(result['observations'][:3]):
            print('  {}: from_point_id={}, to_point_id={}, obs_type={}, value={}'.format(
                i, obs.from_point_id, obs.to_point_id, obs.obs_type, obs.value
            ))
            
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()