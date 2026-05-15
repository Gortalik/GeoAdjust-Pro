"""Парсер Leica GSI (Geodetic Standard Interface) строго по спецификации"""
import re
from pathlib import Path
from typing import Optional
from ..base import BaseParser, Observation, ObsType


class GSIParser(BaseParser):
    """
    Парсер файлов Leica GSI согласно документации GRO2209/KOL0708
    
    Поддерживаемые коды измерений:
    - 32: Горизонтальный угол (градусы)
    - 331/335: Прямое проложение (метры)
    - 332/336: Обратное проложение (метры)
    - 333: Боковое/промежуточное проложение (метры)
    - 571/573: Превышение прямой ход (метры)
    - 572/574: Превышение обратный ход (метры)
    - 83: Отметка/высота/отсчёт по рейке (метры)
    
    Формат блока: [Код][.Знаки][±][Значение]
    Пример: 331.08+00156217 → 0.0156217 м
    """

    # Регулярное выражение для парсинга блоков измерений
    # Формат: КК[К].+[ДД][±]ЗЗЗЗ где К=код (2-3 цифры), Д=десятичные знаки (1-2 цифры), З=значение
    # Примеры: 32...8+00491132, 331.28+00142332, 573..8+00005298, 83..58+00000000
    BLOCK_PATTERN = re.compile(r'(\d{2,3})[.]+(\d+)([+-])(\d+)')

    def __init__(self):
        self.current_station: Optional[str] = None
        self.current_target: Optional[str] = None
        self.current_distance: float = 1.0
        self.setup_counter: int = 0
        self.points_data: dict[str, dict] = {}  # Данные по точкам
        self.current_point_id: Optional[str] = None

    def parse(self, file_path: Path) -> list[Observation]:
        """Парсинг GSI файла в список наблюдений"""
        text = self.read_with_fallback(file_path)
        observations: list[Observation] = []

        # Сброс состояния
        self.current_station = None
        self.current_target = None
        self.current_distance = 1.0
        self.setup_counter = 0
        self.points_data = {}
        self.current_point_id = None

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Первая проходка: собираем данные по точкам
        for line in lines:
            # Пропускаем маркеры секций (41...) и заголовки
            if line.startswith('41'):
                continue

            # Строка должна начинаться с типа записи (11, 41 и т.д.)
            if not line or not line[0].isdigit():
                continue

            # Извлекаем ID точки из атрибута (позиции 7-13 после '+')
            point_info = self._extract_point_info(line)
            if not point_info:
                continue

            station_code, point_id = point_info
            measurements = self._parse_measurements(line)

            if point_id:
                self.current_point_id = point_id

                # Сохраняем данные точки
                if point_id not in self.points_data:
                    self.points_data[point_id] = {
                        'station_code': station_code,
                        'measurements': {},
                        'codes': set()
                    }

                # Обновляем измерения
                for code, value in measurements.items():
                    self.points_data[point_id]['measurements'][code] = value
                    self.points_data[point_id]['codes'].add(code.split('.')[0])

        # Вторая проходка: формируем наблюдения
        observations = self._build_observations()

        return observations

    def _extract_point_info(self, line: str) -> Optional[tuple[str, str]]:
        """
        Извлечение информации о точке из строки GSI
        Возвращает (код_станции, ID_точки) или None
        
        Формат: 110002+000000J1 83..58+00000000
        Позиции:
          0-5: тип записи (11) + номер (0002)
          6: разделитель '+'
          7-12: код станции (6 символов) - может быть '000000' или '00R522'
          13+: ID точки и измерения
        
        Примеры из реальных файлов:
          110002+000000J1 ... → station='000000', point='J1' ✓
          110004+0000V500 ... → station='0000', point='V500'
          110007+0000J501 ... → station='0000', point='J501'
        
        Логика: если атрибут начинается с '0000' и содержит буквы после,
        то это часть ID точки, а не код станции.
        """
        if len(line) < 13 or line[6] != '+':
            return None

        # Первые 6 символов после '+' - атрибут
        attr = line[7:13]

        # Остальная часть строки после атрибута
        rest = line[13:].lstrip()

        # Если атрибут типа '0000XX' где XX буквы, это частично ID точки
        # Пример: '0000V5' + rest='00' → полный ID 'V500'
        if attr.startswith('0000') and len(attr) == 6:
            suffix = attr[4:]  # 'V5' из '0000V5'
            if suffix.isalnum() and not suffix.isdigit():
                # suffix содержит буквы - это начало ID
                # Проверяем rest на продолжение (цифры)
                if rest:
                    # Пытаемся взять цифры из начала rest
                    rest_match = re.match(r'^(\d+)', rest)
                    if rest_match:
                        full_id = suffix + rest_match.group(1)
                        return ('0000', full_id)
                # Если нет продолжения, suffix это весь ID
                return ('0000', suffix)

        # Стандартный случай: attr='000000', rest начинается с ID
        if rest:
            # ID точки - первый алфавитно-цифровой токен
            match = re.match(r'^([A-Za-z][A-Za-z0-9_.]*|[0-9]+(?:\.[0-9]+)?)', rest)
            if match:
                return (attr, match.group(1))

        return (attr, None)

    def _parse_measurements(self, line: str) -> dict[str, float]:
        """
        Парсинг блоков измерений из строки GSI
        
        Формат блока: КК[К].+ДД[±]ЗЗЗЗ
        где КК[К] - код измерения (2-3 цифры), ДД - количество десятичных знаков,
        ± - знак, ЗЗЗЗ - целочисленное значение
        
        Возвращает словарь {код: реальное_значение}
        """
        measurements = {}

        for match in self.BLOCK_PATTERN.finditer(line):
            code = match.group(1)
            decimals_str = match.group(2)
            sign = match.group(3)
            value_str = match.group(4)

            # Определяем количество десятичных знаков
            try:
                decimals = int(decimals_str)
            except ValueError:
                decimals = 8  # по умолчанию

            # Конвертируем значение
            try:
                int_value = int(value_str)
                real_value = float(sign + str(int_value)) / (10 ** decimals)
                measurements[code] = real_value
            except (ValueError, OverflowError):
                continue

        return measurements

    def _build_observations(self) -> list[Observation]:
        """
        Построение списка наблюдений на основе собранных данных точек
        
        Логика согласно документации:
        - Точки хода: имеют коды 331/332/335/336 и 573/574
        - Боковые точки: имеют код 333 без 573/574
        - Тип отсчёта определяется по наличию кодов
        """
        observations = []
        sorted_points = sorted(self.points_data.keys(),
                              key=lambda x: int(''.join(filter(str.isdigit, x)) or '0'))

        prev_point = None
        self.setup_counter = 0

        for _, point_id in enumerate(sorted_points):
            data = self.points_data[point_id]
            codes = data['codes']
            meas = data['measurements']

            # Определяем тип точки
            is_side_shot = '333' in codes and not any(
                c in codes for c in ['573', '574', '571', '572']
            )
            is_traverse_point = any(c in codes for c in ['573', '574', '571', '572'])

            if is_side_shot:
                # Боковая точка - не участвует в уравнивании, но сохраняем для информации
                self.setup_counter += 1
                continue

            if is_traverse_point:
                # Точка хода
                self.setup_counter += 1

                # Получаем превышения
                dh_forward = meas.get('573') or meas.get('571')
                dh_backward = meas.get('574') or meas.get('572')

                # Получаем расстояния
                dist_forward = meas.get('331') or meas.get('335')
                dist_backward = meas.get('332') or meas.get('336')

                # Если есть предыдущая точка, создаём наблюдение
                if prev_point:
                    # Используем среднее превышение если есть оба
                    if dh_forward is not None and dh_backward is not None:
                        avg_dh = (dh_forward - dh_backward) / 2  # Знак зависит от направления
                    elif dh_forward is not None:
                        avg_dh = dh_forward
                    elif dh_backward is not None:
                        avg_dh = -dh_backward  # Инвертируем для обратного хода
                    else:
                        prev_point = point_id
                        continue

                    # Расстояние
                    distance = dist_forward or dist_backward or 1.0
                    if distance <= 0.01:
                        distance = 1.0

                    observations.append(Observation(
                        station_id=prev_point,
                        target_id=point_id,
                        value=avg_dh,
                        distance=distance,
                        type=ObsType.LEVELING,
                        setup_id=f"setup_{self.setup_counter}"
                    ))

                prev_point = point_id

        return observations
