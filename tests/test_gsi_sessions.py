#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
from geoadjust.io.formats.gsi import GSIParser
from pathlib import Path
parser = GSIParser()
result = parser.parse(Path('../test_real_mes/b_g/niv/GRO2209.GSI'))
print('Success:', result['success'])
print('Observations:', len(result['observations']))
print('Sessions:', len(result['station_sessions']))
for session in result['station_sessions'][:5]:
    print(f'  Session {session.session_id}: "{session.station_name}", obs: {len(session.observations)}, IH: {session.instrument_height}')