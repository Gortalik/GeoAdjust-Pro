#!/usr/bin/env python3
import sys
from geoadjust.io.formats.sdr import SDRParser
from pathlib import Path

parser = SDRParser()
result = parser.parse(Path('../test_real_mes/b_g/plan/badgro16093_const.sdr'))
print('Success:', result['success'])
print('Observations:', len(result['observations']))
print('Setups:', len(result['setups']))
print('Station sessions:', len(result['station_sessions']))