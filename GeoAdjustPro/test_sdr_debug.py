#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from geoadjust.io.formats.sdr import SDRParser
from pathlib import Path

# Тестируем тот же файл, что и в test_real_data_parsers.py
parser = SDRParser()
result = parser.parse(Path('../test_real_mes/b_g/plan/badgro16093_const.sdr'))
print('Success:', result['success'])
print('Format:', result.get('format'))
print('Num observations:', result.get('num_observations'))
print('Len observations:', len(result.get('observations', [])))
print('Len setups:', len(result.get('setups', [])))
print('Len station_sessions:', len(result.get('station_sessions', [])))