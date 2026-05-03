# src/geoadjust/io/formats/sdr_parser.py
"""
Замена самописного SDR парсера на улучшенную версию
Использует проверенные алгоритмы парсинга Trimble SDR
"""

import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Literal
from dataclasses import dataclass, field
from geoadjust.core.network.models import InstrumentSetup
import logging

logger = logging.getLogger(__name__)

@dataclass
class SDRStation:
    """Станция в формате SDR"""
    point_id: str
    x: Optional[float] = None
    y: Optional[float] = None
    h: Optional[float] = None
    instrument_height: Optional[float] = None
    backsight_point: Optional[str] = None
    backsight_angle: Optional[float] = None
    face_position: str = "NONE"

@dataclass
class SDRCombinedMeasurement:
    """Объединенное измерение для всей SDR строки 09F1/F2"""
    station_id: str
    target_id: str
    face_position: Optional[Literal['CL', 'CP']] = None
    horizontal_angle: Optional[float] = None
    zenith_angle: Optional[float] = None
    slope_distance: Optional[float] = None
    raw_line: Optional[str] = None


@dataclass
class SDRObservation:
    """Измерение в формате SDR"""
    obs_type: str
    from_point: str
    to_point: str
    value: Optional[float] = None
    setup_id: Optional[str] = None  # ID установки станции
    face_position: Optional[Literal['CL', 'CP']] = None  # CL - круг лево, CP - круг право
    horizontal_angle: Optional[float] = None
    vertical_angle: Optional[float] = None
    distance: Optional[float] = None
    raw_line: Optional[str] = None

class SDRParser:
    """Улучшенный парсер Sokkia SDR с проверенными алгоритмами"""

    # SDR record types based on documented format
    RECORD_TYPES = {
        '00': 'file_header',
        '01': 'instrument_info',
        '02': 'station_setup',
        '03': 'target_height',
        '04': 'backsight_info',
        '05': 'orientation',
        '06': 'atmospheric_correction',
        '07': 'orientation_angle',
        '08': 'coordinates',
        '09': 'measurement',
        '10': 'job_name',
        '11': 'end_of_job'
    }

    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Парсинг SDR файла с улучшенной обработкой"""
        job_name = ""
        setups: List[InstrumentSetup] = []
        observations: List[Any] = []
        points: Dict[str, Any] = {}
        current_setup: Optional[InstrumentSetup] = None
        setup_counter = 0
        errors = []

        try:
            # Определяем кодировку файла
            encoding = self._detect_encoding(file_path)

            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Ошибка чтения файла: {e}")
            return {'error': str(e), 'setups': [], 'observations': [], 'points': {}}

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or len(line) < 4:
                continue

            try:
                # Определяем тип записи: 02, 03NM, 05NM, 07NM, 09F1, 09F2, etc.
                if line.startswith('09'):
                    record_type = line[:4]  # 09F1, 09F2
                elif 'NM' in line[:4]:
                    record_type = line[:4]  # 02NM, 03NM, 05NM, 07NM
                else:
                    record_type = line[:2]  # 02, 03, 05, 07



                if record_type == '02' or record_type.startswith('02'):  # Станция (новая установка)
                    # Сохраняем предыдущую установку
                    if current_setup:
                        setups.append(current_setup)
                        logger.debug(f"Сохранена установка {current_setup.setup_id} с {len(current_setup.observations)} измерениями")

                    # Парсим новую установку
                    setup_data = self._parse_station_record(line)
                    setup_counter += 1

                    point_id = setup_data.get('station_id', f"UNK_{setup_counter}")

                    current_setup = InstrumentSetup(
                        setup_id=f"{point_id}_SETUP_{setup_counter:03d}",
                        point_id=point_id,
                        instrument_name="SDR_Instrument",
                        instrument_height=setup_data.get('instrument_height', 0.0),
                        target_height=0.0,
                        timestamp=datetime.now()
                    )

                    logger.debug(f"Создана новая установка {current_setup.setup_id} для точки {point_id}")

                    # Добавляем точку в список
                    if point_id not in points:
                        # Определяем статус точки на основе наличия координат
                        has_coords = (setup_data.get('x') is not None and
                                    setup_data.get('y') is not None)

                        points[point_id] = {
                            'point_id': point_id,
                            'coord_type': 'FREE',  # Станции - свободные точки
                            'plan_status': 'working',   # Все точки - рабочие (определяемые)
                            'height_status': 'working', # Все точки - рабочие (определяемые)
                            'x': setup_data.get('x'),  # Начальные приближения из файла
                            'y': setup_data.get('y'),
                            'h': setup_data.get('h')
                        }

                elif record_type in ['03', '03NM'] and current_setup:  # Высота наведения
                    target_height = self._parse_target_height(line)
                    current_setup.target_height = target_height

                elif record_type in ['05', '05NM'] and current_setup:  # Давление и температура
                    pressure, temperature = self._parse_atmospheric_data(line)
                    current_setup.pressure = pressure
                    current_setup.temperature = temperature

                elif record_type in ['07', '07NM'] and current_setup:  # Ориентирное направление
                    orientation = self._parse_orientation(line)
                    current_setup.orientation_angle = orientation

                elif record_type.startswith('08'):  # Координаты станции (08, 08RS, 08KI, 08MA, etc.)
                    coord_data = self._parse_coordinates_record(line)
                    if coord_data:
                        point_id = coord_data.get('point_id', '').upper()  # Приводим к верхнему регистру
                        # Ищем точку без учета регистра
                        found_key = None
                        for existing_id in points.keys():
                            if existing_id.upper() == point_id:
                                found_key = existing_id
                                break

                        if found_key:
                            # Обновляем координаты существующей точки
                            points[found_key].update({
                                'x': coord_data.get('x'),
                                'y': coord_data.get('y'),
                                'h': coord_data.get('h'),
                                'coord_type': 'FIXED',  # Координаты из файла - опорные
                                'plan_status': 'initial',    # План исходный
                                'height_status': 'initial'   # Высота исходная
                            })
                            logger.debug(f"Обновлены координаты точки {found_key}: X={coord_data.get('x')}, Y={coord_data.get('y')}, H={coord_data.get('h')}")
                        else:
                            # Создаем новую точку с координатами (исходный пункт)
                            points[point_id] = {
                                'point_id': point_id,
                                'coord_type': 'FIXED',  # Координаты из файла - опорные
                                'plan_status': 'initial',   # План исходный
                                'height_status': 'initial', # Высота исходная
                                'x': coord_data.get('x'),
                                'y': coord_data.get('y'),
                                'h': coord_data.get('h')
                            }
                            logger.debug(f"Создана новая точка {point_id} с координатами: X={coord_data.get('x')}, Y={coord_data.get('y')}, H={coord_data.get('h')}")

                elif record_type.startswith('09'):  # Измерение (09F1, 09F2)
                    if not current_setup:
                        logger.debug(f"Измерение без активной установки на строке {line_num}")
                        continue

                    # Определяем позицию круга: F1 = CL (круг лево), F2 = CP (круг право)
                    face_position = 'CL' if 'F1' in record_type else 'CP' if 'F2' in record_type else None

                    measurements = self._parse_measurement(line)
                    for measurement in measurements:
                        # measurement уже является объектом SDRCombinedMeasurement
                        # Создаем SDRObservation для совместимости, но с объединенными данными
                        obs = SDRObservation(
                            obs_type='combined',  # Для UI
                            from_point=current_setup.point_id,
                            to_point=measurement.target_id,
                            value=None,
                            setup_id=current_setup.setup_id,
                            face_position=measurement.face_position,
                            horizontal_angle=measurement.horizontal_angle,
                            vertical_angle=measurement.zenith_angle,
                            distance=measurement.slope_distance,
                            raw_line=measurement.raw_line
                        )

                        logger.debug(f"Created SDRObservation: type={obs.obs_type}, h_angle={obs.horizontal_angle}, dist={obs.distance}")
                        # Добавляем измерение в общий список
                        observations.append(obs)
                        # Добавляем измерение в текущую установку станции
                        if current_setup:
                            current_setup.observations.append(obs)
                        logger.debug(f"Добавлено объединенное измерение от {obs.from_point} к {obs.to_point} (круг: {obs.face_position})")

            except Exception as e:
                errors.append({
                    'line': line_num,
                    'message': str(e),
                    'raw': line[:50]
                })
                logger.debug(f"Ошибка парсинга строки {line_num}: {e}")

        # Сохраняем последнюю установку
        if current_setup:
            setups.append(current_setup)

        # Конвертация в совместимый формат
        from geoadjust.core.network.models import Observation

        compatible_points = []
        for p in points.values():
            compatible_points.append({
                'point_id': p['point_id'],
                'x': p.get('x', 0.0) or 0.0,
                'y': p.get('y', 0.0) or 0.0,
                'h': p.get('h', 0.0) or 0.0,
                'point_type': p.get('coord_type', 'FREE'),
                'plan_status': p.get('plan_status', 'working'),
                'height_status': p.get('height_status', 'working')
            })

        # Конвертируем в объекты CombinedObservation
        from geoadjust.core.network.models import CombinedObservation

        compatible_observations = []
        for obs in observations:  # Берем из плоского списка SDRObservation
            # Создаем один CombinedObservation для всей SDR строки
            combined_obs = CombinedObservation(
                obs_id=f"OBS_{len(compatible_observations):06d}",
                obs_type=obs.obs_type,  # Копируем тип из SDRObservation
                from_setup_id=obs.setup_id or f"{obs.from_point}_SETUP",
                from_point_id=obs.from_point,
                to_point_id=obs.to_point,
                face_position=obs.face_position,
                horizontal_angle=obs.horizontal_angle,
                zenith_angle=obs.vertical_angle,
                slope_distance=obs.distance,
                raw_line=obs.raw_line
            )


            compatible_observations.append(combined_obs)

        # Формируем данные сессий станций для UI (формат, ожидаемый import_dialog)
        station_sessions = []
        for setup in setups:
            # Преобразуем измерения этой установки в формат для UI
            setup_observations_ui = []
            for obs in setup.observations:
                setup_observations_ui.append({
                    'obs_type': obs.obs_type,
                    'from_point': obs.from_point,
                    'to_point': obs.to_point,
                    'value': obs.value,
                    'setup_id': obs.setup_id,
                    'face_position': obs.face_position
                })

            session_data = {
                'session_id': setup.setup_id,
                'station_name': setup.point_id,
                'instrument_height': setup.instrument_height,
                'target_height': setup.target_height,
                'orientation_angle': setup.orientation_angle,
                'temperature': setup.temperature,
                'pressure': setup.pressure,
                'num_observations': len(setup.observations),
                'timestamp': setup.timestamp,
                'observations': setup_observations_ui
            }
            station_sessions.append(session_data)

        # Успех определяется наличием наблюдений, а не отсутствием ошибок
        # Ошибки парсинга координат не должны делать парсинг неудачным
        success = len(observations) > 0
        return {
            'format': 'SDR',
            'job_name': job_name,
            'encoding': 'cp1251',
            'total_lines': len(lines),
            'setups': setups,
            'observations': compatible_observations,
            'points': compatible_points,
            'station_sessions': station_sessions,
            'num_setups': len(setups),
            'num_observations': len(observations),
            'errors': errors,
            'success': success
        }

    def get_statistics(self):
        """Получение статистики по типам измерений"""
        # Для SDR файлов возвращаем простую статистику
        return {'by_type': {'combined': 0}}  # Заглушка

    def _detect_encoding(self, file_path: Path) -> str:
        """Определение кодировки файла"""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                encoding = result.get('encoding')
                return encoding if encoding else 'utf-8'
        except ImportError:
            return 'utf-8'

    def _parse_station_record(self, line: str) -> Dict[str, Any]:
        """Парсинг записи станции (02)"""
        # Форматы:
        # - 02NM        STATION_ID   X_COORD   Y_COORD   H_COORD  (разделено пробелами)
        # - 02NM        STATION_ID   XXXXXXXXXXXXXXYXXXXXXXXXXXXXZXXXXXXXXXXXXX  (упаковано)
        result = {}

        try:
            # Record type (позиции 0-1): "02"
            record_type = line[0:2]

            # Instrument designation (позиции 2-3): "NM"
            instrument = line[2:4]

            # Station ID (начинается после пробелов)
            station_start = 4
            while station_start < len(line) and line[station_start] == ' ':
                station_start += 1
            station_end = station_start
            while station_end < len(line) and line[station_end] != ' ':
                station_end += 1
            station_id = line[station_start:station_end].strip()
            if station_id:
                result['station_id'] = station_id.upper()

            # Координаты после station_id
            coord_start = station_end
            while coord_start < len(line) and line[coord_start] == ' ':
                coord_start += 1
            coord_str = line[coord_start:].strip()

            if coord_str:
                # Проверяем, разделены ли координаты пробелами (как в kotlntss06042026.sdr)
                coord_parts = coord_str.split()
                if len(coord_parts) >= 3:
                    # Разделенные пробелами координаты
                    try:
                        result['x'] = float(coord_parts[0])
                        result['y'] = float(coord_parts[1])
                        result['h'] = float(coord_parts[2]) if len(coord_parts) > 2 else 0.0
                    except (ValueError, IndexError):
                        pass
                elif len(coord_str) > 20:
                    # Упакованные координаты (как в badgro16093_const.sdr)
                    # Берем только первые 48 символов (как в записи 08RS)
                    coord_data = coord_str[:48] if len(coord_str) > 48 else coord_str

                    # Парсим как упакованные координаты
                    try:
                        coord_len = len(coord_data) // 3
                        x_str = coord_data[:coord_len]
                        y_str = coord_data[coord_len:2*coord_len]
                        h_str = coord_data[2*coord_len:]

                        result['x'] = self._clean_coordinate_string(x_str)
                        result['y'] = self._clean_coordinate_string(y_str)
                        result['h'] = self._clean_coordinate_string(h_str)
                    except Exception as e:
                        logger.warning(f"Ошибка парсинга упакованных координат станции: {line} - {e}")

        except Exception as e:
            logger.error(f"Критическая ошибка парсинга станции: {e}")

        return result

    def _clean_coordinate_string(self, coord_str: str) -> float:
        """Очистка строки координат от лишних символов и конвертация в float"""
        # Удаляем все кроме цифр, точки и минуса
        cleaned = ''.join(c for c in coord_str if c.isdigit() or c in '.-')
        # Удаляем повторяющиеся точки
        while '..' in cleaned:
            cleaned = cleaned.replace('..', '.')
        try:
            return float(cleaned)
        except ValueError:
            # Если не получается, пробуем найти первое валидное число
            import re
            match = re.search(r'-?\d+\.?\d*', cleaned)
            if match:
                return float(match.group())
            raise ValueError(f"Cannot parse coordinate: {coord_str}")

    def _parse_coordinates_record(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Парсинг записи координат станции (тип 08)

        Форматы:
        - 08KI        point_id   x_coord   y_coord   h_coord  (разделено пробелами)
        - 08RS        point_id   xxxxxxxxxxxxxxyyyyyyyyyyyyyzzzzzzzzzzzzz  (упаковано)
        """
        try:
            # Удаляем тип записи и разделяем по пробелам
            parts = line[4:].strip().split()

            if len(parts) < 2:
                logger.warning(f"Недостаточно данных в записи координат: {line}")
                return None

            point_id = parts[0].strip().upper()  # Приводим к верхнему регистру

            # Проверяем, разделены ли координаты пробелами (08KI формат)
            if len(parts) >= 4:
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    h = float(parts[3]) if len(parts) > 3 else 0.0

                    return {
                        'point_id': point_id,
                        'x': x,
                        'y': y,
                        'h': h
                    }
                except (ValueError, IndexError) as e:
                    logger.warning(f"Ошибка парсинга разделенных координат: {line} - {e}")

            # Проверяем упакованный формат (08RS)
            elif len(parts) == 2:
                coord_str = parts[1].strip()
                # Пробуем разобрать как упакованные координаты
                # В некоторых SDR форматах координаты идут подряд без разделителей
                try:
                    # Предполагаем, что координаты имеют одинаковую длину
                    # Для этого формата: каждая координата ~25 символов
                    coord_len = len(coord_str) // 3  # Делим на 3 координаты

                    x_str = coord_str[:coord_len].strip()
                    y_str = coord_str[coord_len:2*coord_len].strip()
                    h_str = coord_str[2*coord_len:].strip()

                    # Удаляем лишние символы и пробуем конвертировать
                    x = self._clean_coordinate_string(x_str)
                    y = self._clean_coordinate_string(y_str)
                    h = self._clean_coordinate_string(h_str)

                    return {
                        'point_id': point_id,
                        'x': x,
                        'y': y,
                        'h': h
                    }
                except (ValueError, IndexError) as e:
                    logger.warning(f"Ошибка парсинга упакованных координат: {line} - {e}")

            # Дополнительная попытка: ищем паттерн с несколькими точками
            if len(parts) == 2:
                coord_str = parts[1].strip()
                try:
                    # Ищем позиции точек
                    dot_positions = []
                    for i, char in enumerate(coord_str):
                        if char == '.':
                            dot_positions.append(i)

                    if len(dot_positions) >= 2:
                        # Разделяем по точкам: берем до второй точки + немного для X,
                        # от второй до третьей для Y, остальное для H
                        x_end = dot_positions[1] + 15  # Берем достаточно символов для X
                        y_end = dot_positions[1] + 15 + (dot_positions[-1] - dot_positions[1]) // 2

                        x_str = coord_str[:x_end]
                        y_str = coord_str[x_end:y_end]
                        h_str = coord_str[y_end:]

                        x = self._clean_coordinate_string(x_str)
                        y = self._clean_coordinate_string(y_str)
                        h = self._clean_coordinate_string(h_str)

                        return {
                            'point_id': point_id,
                            'x': x,
                            'y': y,
                            'h': h
                        }
                except Exception as e:
                    logger.warning(f"Ошибка парсинга по точкам: {line} - {e}")

            logger.warning(f"Не удалось разобрать координаты в строке: {line}")
            return None

        except Exception as e:
            logger.error(f"Критическая ошибка парсинга координат: {e}")
            return None

    def _parse_target_height(self, line: str) -> float:
        """Парсинг высоты наведения (03)"""
        parts = line.split()
        if len(parts) >= 2:
            try:
                return float(parts[1])
            except ValueError:
                pass
        return 0.0

    def _parse_orientation(self, line: str) -> Optional[float]:
        """Парсинг ориентирного направления (07)"""
        parts = line.split()
        if len(parts) >= 2:
            try:
                return float(parts[1])
            except ValueError:
                pass
        return None

    def _parse_atmospheric_data(self, line: str) -> Tuple[Optional[float], Optional[float]]:
        """Парсинг атмосферных данных (05NM) - давление и температура"""
        pressure = None
        temperature = None
        
        if len(line) >= 10:  # Минимум для данных
            try:
                # Давление: позиции 6-15 (9 символов с возможным знаком и десятичной точкой)
                pressure_str = line[6:15].strip()
                if pressure_str:
                    pressure = float(pressure_str)
                    
                # Температура: позиции 16-25 (10 символов)
                temp_str = line[16:25].strip()
                if temp_str:
                    temperature = float(temp_str)
            except (ValueError, IndexError):
                pass
                
        return pressure, temperature

    def _parse_measurement(self, line: str) -> List[Dict[str, Any]]:
        """Парсинг измерения (09) - возвращает список измерений"""
        try:
            # Разделяем строку по пробелам
            parts = line.strip().split()

            if len(parts) < 4 or not parts[0].startswith('09'):
                return []

            # Извлекаем компоненты
            record_type = parts[0]  # 09F1 или 09F2
            station_id = parts[1]   # станция
            target_id = parts[2]    # цель

            # Числа могут быть в одной строке или разделены
            measurements = []

            if len(parts) >= 4:
                numbers_str = parts[3]

                # Если чисел больше, объединяем их
                for i in range(4, len(parts)):
                    numbers_str += parts[i]

                # В SDR файлах числа могут идти подряд, нужно разделить их по фиксированной ширине
                # Обычно формат: 3 числа по 15 символов каждое (горизонтальный угол, зенитный угол, расстояние)
                # Попробуем разделить строку на числа фиксированной длины
                import re

                # Сначала попробуем найти числа с помощью регулярного выражения
                numbers = re.findall(r'\d+\.\d+', numbers_str)

                if len(numbers) >= 3:
                    # Если нашли 3 или больше чисел, используем первые 3
                    # Порядок в SDR: расстояние, вертикальный угол, горизонтальный угол
                    slope_distance = float(numbers[0])
                    zenith_angle = float(numbers[1])
                    horizontal_angle = float(numbers[2])
                else:
                    # Если не нашли числа, попробуем разделить строку на части фиксированной длины
                    # Предполагаем, что каждое число имеет около 15-16 символов
                    if len(numbers_str) >= 45:  # Минимум 3 числа по 15 символов
                        try:
                            # Разделяем на 3 части примерно равной длины
                            part_len = len(numbers_str) // 3
                            h_str = numbers_str[:part_len].strip()
                            z_str = numbers_str[part_len:2*part_len].strip()
                            d_str = numbers_str[2*part_len:].strip()

                            # Порядок в SDR: расстояние, вертикальный угол, горизонтальный угол
                            slope_distance = float(h_str)
                            zenith_angle = float(z_str)
                            horizontal_angle = float(d_str)
                        except (ValueError, IndexError):
                            horizontal_angle = None
                            zenith_angle = None
                            slope_distance = None
                    else:
                        horizontal_angle = None
                        zenith_angle = None
                        slope_distance = None

                measurement = SDRCombinedMeasurement(
                    station_id=station_id,
                    target_id=target_id,
                    face_position='CL' if 'F1' in record_type else 'CP',
                    horizontal_angle=horizontal_angle,
                    zenith_angle=zenith_angle,
                    slope_distance=slope_distance,
                    raw_line=line
                )

                measurements.append(measurement)

            return measurements

        except Exception as e:
            logger.debug(f"Ошибка парсинга измерения: {e}")
            return []