#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test script for GSI parser
"""

import sys
import os

# Direct imports to avoid module issues
import pathlib
import re
import logging

logger = logging.getLogger(__name__)

class GSIWord:
    """Информационное слово GSI"""
    def __init__(self, number: int, sign: str, digits: str, decimal_places: int, identifier: str = None, value: float = 0.0, raw: str = ""):
        self.number = number
        self.sign = sign
        self.digits = digits
        self.decimal_places = decimal_places
        self.identifier = identifier
        self.value = value
        self.raw = raw

class GSIObservation:
    """Измерение в формате GSI"""
    def __init__(self, obs_type: str, from_point: str, to_point: str, value: float, station_session_id: str = "", instrument_height: float = None, target_height: float = None, line_number: int = 0, raw_words: list = None):
        self.obs_type = obs_type
        self.from_point = from_point
        self.to_point = to_point
        self.value = value
        self.station_session_id = station_session_id
        self.instrument_height = instrument_height
        self.target_height = target_height
        self.line_number = line_number
        self.raw_words = raw_words or []

class GSIStationSession:
    """Одна установка (сессия) станции."""
    def __init__(self, session_id: str, station_name: str, instrument_height: float = None, target_height: float = None):
        self.session_id = session_id
        self.station_name = station_name
        self.instrument_height = instrument_height
        self.target_height = target_height
        self.observations = []

class SimpleGSIParser:
    """Simplified GSI parser for testing"""

    WORD_TYPES = {
        '571': 'leveling_backsight_point',
        '572': 'leveling_foresight_point',
        '573': 'leveling_height_diff',
        '574': 'leveling_distance',
        '83': 'instrument_height',
        '87': 'instrument_height',
    }

    def parse(self, file_path: pathlib.Path):
        points = []
        observations = []
        station_sessions = []

        try:
            with open(file_path, 'r', encoding='cp1251', errors='ignore') as f:
                lines = f.readlines()

            station_counter = 0

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # Find all words in the line
                words = re.findall(r'(\d+(?:\.\.\d+|\.\d+)?[\+\-][\+\-\d]+[^\d]*)', line)

                # Parse words
                parsed_words = []
                for word in words:
                    match = re.match(r'(\d+(?:\.\.\d+|\.\d+)?)([\+\-])([\d\.]+)(.*)$', word)
                    if match:
                        word_code_str = match.group(1)
                        sign = match.group(2)
                        value_str = match.group(3).strip()
                        identifier = match.group(4).strip('.')

                        try:
                            # Parse word code and decimal places
                            if '..' in word_code_str:
                                parts = word_code_str.split('..')
                                word_code = int(parts[0])
                                decimal_digits = int(parts[1]) if parts[1] else 0
                            elif '.' in word_code_str:
                                parts = word_code_str.split('.')
                                word_code = int(parts[0])
                                decimal_digits = int(parts[1]) if parts[1].isdigit() else len(parts[1])
                            else:
                                word_code = int(word_code_str)
                                decimal_digits = 0

                            value = float(value_str)
                            if decimal_digits > 0:
                                value /= (10 ** decimal_digits)
                            if sign == '-':
                                value = -value

                            gsi_word = GSIWord(
                                number=word_code,
                                sign=sign,
                                digits=value_str,
                                decimal_places=decimal_digits,
                                identifier=identifier if identifier else None,
                                value=value
                            )
                            parsed_words.append(gsi_word)

                        except ValueError as e:
                            logger.debug(f"Error parsing value {value_str}: {e}")
                            continue

                # Process leveling measurements
                if parsed_words:
                    leveling_words = [w for w in parsed_words if w.number in [571, 572, 573, 574, 83, 87]]
                    if leveling_words:
                        self._process_leveling_simple(parsed_words, line_num, observations, station_sessions, station_counter, points)

        except Exception as e:
            logger.error(f"Error parsing GSI: {e}")

        return {
            'points': points,
            'observations': observations,
            'station_sessions': station_sessions,
            'format': 'GSI',
            'success': len(observations) > 0,
            'errors': [],
            'warnings': []
        }

    def _process_leveling_simple(self, words, line_num, observations, station_sessions, station_counter, points):
        """Process leveling measurements"""
        height_diff_word = None
        backsight_point = None
        foresight_point = None
        instrument_height = None
        distance = None

        for word in words:
            if word.number == 573:  # Height difference
                height_diff_word = word
            elif word.number == 571:  # Backsight point
                backsight_point = word.identifier.strip('.') if word.identifier else None
            elif word.number == 572:  # Foresight point
                foresight_point = word.identifier.strip('.') if word.identifier else None
            elif word.number == 574:  # Distance
                distance = word.value
            elif word.number in [83, 87]:  # Instrument height
                instrument_height = word.value

        if not height_diff_word:
            return

        from_point = backsight_point or "UNKNOWN"
        to_point = foresight_point or height_diff_word.identifier.strip('.') if height_diff_word.identifier else "UNKNOWN"

        # Create session
        session_id = f"SESSION_{station_counter:03d}"
        if not any(s.session_id == session_id for s in station_sessions):
            session = GSIStationSession(
                session_id=session_id,
                station_name=from_point,
                instrument_height=instrument_height
            )
            station_sessions.append(session)
            station_counter += 1

        # Add points
        for point_id in [from_point, to_point]:
            if point_id != "UNKNOWN" and point_id not in [p.get('point_id') for p in points]:
                points.append({
                    'point_id': point_id,
                    'point_type': 'target',
                    'x': None,
                    'y': None,
                    'h': None
                })

        # Create observation
        obs = GSIObservation(
            obs_type='leveling_height_diff',
            from_point=from_point,
            to_point=to_point,
            value=height_diff_word.value,
            station_session_id=session_id,
            instrument_height=instrument_height,
            line_number=line_num,
            raw_words=words
        )
        observations.append(obs)

if __name__ == "__main__":
    parser = SimpleGSIParser()
    result = parser.parse(pathlib.Path('C:/Users/gorta.DUDOSG/Downloads/P-of-Geo-Meas/test_real_mes/b_g/niv/GRO2209.GSI'))
    print('Success:', result['success'])
    print('Observations:', len(result['observations']))
    print('Points:', len(result['points']))
    print('Sessions:', len(result['station_sessions']))
    for obs in result['observations'][:10]:
        print(f'  {obs.obs_type}: {obs.from_point} -> {obs.to_point} = {obs.value:.5f} (IH: {obs.instrument_height})')