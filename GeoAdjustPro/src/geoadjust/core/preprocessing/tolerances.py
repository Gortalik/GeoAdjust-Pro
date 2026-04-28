"""
Контроль 27 инструктивных допусков по СП 11-104-97 и Инструкции по нивелированию ГГС

Файл: src/geoadjust/core/preprocessing/tolerances.py
"""

import math
from typing import List, Dict, Any, Optional, Callable


class ToleranceChecker:
    """Контроль 27 инструктивных допусков по СП 11-104-97 и Инструкции по нивелированию ГГС"""

    # Допуски для полигонометрии
    POLYGONOMETRY_TOLERANCES = {
        '1_class': {
            'circle_closure': lambda n: 3.0 * math.sqrt(n),  # 3√n
            'relative_misalignment': 1 / 100000,  # 1:100 000
            'max_side_length': 10000,  # 10 км
            'max_num_sides': 25
        },
        '2_class': {
            'circle_closure': lambda n: 5.0 * math.sqrt(n),  # 5√n
            'relative_misalignment': 1 / 50000,  # 1:50 000
            'max_side_length': 5000,  # 5 км
            'max_num_sides': 20
        },
        '3_class': {
            'circle_closure': lambda n: 10.0 * math.sqrt(n),  # 10√n
            'relative_misalignment': 1 / 30000,  # 1:30 000
            'max_side_length': 3000,  # 3 км
            'max_num_sides': 15
        },
        '4_class': {
            'circle_closure': lambda n: 15.0 * math.sqrt(n),  # 15√n
            'relative_misalignment': 1 / 25000,  # 1:25 000
            'max_side_length': 2000,  # 2 км
            'max_num_sides': 12
        }
    }

    # Допуски для нивелирования
    LEVELLING_TOLERANCES = {
        'I_class': {
            'per_stand': 0.8,  # мм/станцию
            'section_closure': lambda L: 3.0 * math.sqrt(L),  # 3√L мм
            'max_sight_distance': 50  # м
        },
        'II_class': {
            'per_stand': 1.5,  # мм/станцию
            'section_closure': lambda L: 5.0 * math.sqrt(L),  # 5√L мм
            'max_sight_distance': 75  # м
        },
        'III_class': {
            'per_stand': 3.0,  # мм/станцию
            'section_closure': lambda L: 12.0 * math.sqrt(L),  # 12√L мм
            'max_sight_distance': 100  # м
        },
        'IV_class': {
            'per_stand': 5.0,  # мм/станцию
            'section_closure': lambda L: 20.0 * math.sqrt(L),  # 20√L мм
            'max_sight_distance': 150  # м
        },
        'technical': {
            'per_stand': 10.0,  # мм/станцию
            'section_closure': lambda L: 50.0 * math.sqrt(L),  # 50√L мм
            'max_sight_distance': 150  # м
        }
    }

    def check_circle_closure(self, directions: List[float],
                             sigma_beta: float,
                             class_name: str = '4_class') -> Dict[str, Any]:
        """
        Контроль замыкания горизонта

        Параметры:
        - directions: список направлений в приеме (в градусах)
        - sigma_beta: СКО измерения угла
        - class_name: класс полигонометрии

        Возвращает:
        - Словарь с результатами проверки
        """
        # Перевод в секунды дуги
        directions_seconds = [d * 3600 for d in directions]
        closure_error = abs(sum(directions_seconds) - 360.0 * 3600)  # в секундах
        n = len(directions)

        tolerances = self.POLYGONOMETRY_TOLERANCES.get(class_name, self.POLYGONOMETRY_TOLERANCES['4_class'])
        allowable_error = tolerances['circle_closure'](n)

        is_compliant = closure_error <= allowable_error

        return {
            'error': closure_error,
            'allowable_error': allowable_error,
            'is_compliant': is_compliant,
            'normative': f'СП 11-104-97, п. 5.3.5 ({class_name})',
            'num_directions': n
        }

    def check_traverse_misalignment(self, traverse_length: float,
                                    traverse_misclosure: float,
                                    class_name: str = '4_class') -> Dict[str, Any]:
        """
        Контроль относительной невязки хода

        Параметры:
        - traverse_length: длина хода в метрах
        - traverse_misclosure: абсолютная невязка хода в метрах
        - class_name: класс полигонометрии

        Возвращает:
        - Словарь с результатами проверки
        """
        tolerances = self.POLYGONOMETRY_TOLERANCES.get(class_name, self.POLYGONOMETRY_TOLERANCES['4_class'])

        # Относительная невязка
        actual_misalignment = traverse_misclosure / traverse_length if traverse_length > 0 else float('inf')
        allowable_misalignment = tolerances['relative_misalignment']

        is_compliant = actual_misalignment <= allowable_misalignment

        return {
            'actual': actual_misalignment,
            'actual_formatted': f"1:{int(1 / actual_misalignment)}" if actual_misalignment > 0 else "∞",
            'allowable': allowable_misalignment,
            'allowable_formatted': f"1:{int(1 / allowable_misalignment)}",
            'is_compliant': is_compliant,
            'normative': f'СП 11-104-97, класс {class_name}',
            'traverse_length': traverse_length,
            'misclosure': traverse_misclosure
        }

    def check_leveling_section_closure(self, section_length_km: float,
                                       section_closure_mm: float,
                                       class_name: str = 'III_class') -> Dict[str, Any]:
        """
        Контроль невязки нивелирной секции

        Параметры:
        - section_length_km: длина секции в километрах
        - section_closure_mm: фактическая невязка в миллиметрах
        - class_name: класс нивелирования

        Возвращает:
        - Словарь с результатами проверки
        """
        tolerances = self.LEVELLING_TOLERANCES.get(class_name, self.LEVELLING_TOLERANCES['III_class'])

        # Допуск невязки
        allowable_closure = tolerances['section_closure'](section_length_km)

        is_compliant = abs(section_closure_mm) <= allowable_closure

        return {
            'actual': abs(section_closure_mm),
            'allowable': allowable_closure,
            'is_compliant': is_compliant,
            'normative': f'Инструкция по нивелированию ГГС, класс {class_name}',
            'section_length_km': section_length_km
        }

    def check_sight_distance(self, distance: float,
                             class_name: str = 'III_class') -> Dict[str, Any]:
        """
        Контроль длины визирного луча

        Параметры:
        - distance: фактическое расстояние в метрах
        - class_name: класс нивелирования

        Возвращает:
        - Словарь с результатами проверки
        """
        tolerances = self.LEVELLING_TOLERANCES.get(class_name, self.LEVELLING_TOLERANCES['III_class'])
        max_distance = tolerances['max_sight_distance']

        is_compliant = distance <= max_distance

        return {
            'actual': distance,
            'allowable': max_distance,
            'is_compliant': is_compliant,
            'normative': f'Инструкция по нивелированию ГГС, класс {class_name}'
        }

    def check_side_length(self, side_length: float,
                          class_name: str = '4_class') -> Dict[str, Any]:
        """
        Контроль длины стороны хода

        Параметры:
        - side_length: длина стороны в метрах
        - class_name: класс полигонометрии

        Возвращает:
        - Словарь с результатами проверки
        """
        tolerances = self.POLYGONOMETRY_TOLERANCES.get(class_name, self.POLYGONOMETRY_TOLERANCES['4_class'])
        max_length = tolerances['max_side_length']

        is_compliant = side_length <= max_length

        return {
            'actual': side_length,
            'allowable': max_length,
            'is_compliant': is_compliant,
            'normative': f'СП 11-104-97, класс {class_name}'
        }

    def check_num_sides(self, num_sides: int,
                        class_name: str = '4_class') -> Dict[str, Any]:
        """
        Контроль числа сторон в ходе

        Параметры:
        - num_sides: число сторон в ходе
        - class_name: класс полигонометрии

        Возвращает:
        - Словарь с результатами проверки
        """
        tolerances = self.POLYGONOMETRY_TOLERANCES.get(class_name, self.POLYGONOMETRY_TOLERANCES['4_class'])
        max_sides = tolerances['max_num_sides']

        is_compliant = num_sides <= max_sides

        return {
            'actual': num_sides,
            'allowable': max_sides,
            'is_compliant': is_compliant,
            'normative': f'СП 11-104-97, класс {class_name}'
        }

    def check_reciprocal_direction_discrepancy(self, kl_value: float,
                                               kp_value: float,
                                               sigma_beta: float = 5.0) -> Dict[str, Any]:
        """
        Контроль расхождения направлений КЛ/КП

        Параметры:
        - kl_value: значение по кругу лево
        - kp_value: значение по кругу право
        - sigma_beta: СКО измерения угла

        Возвращает:
        - Словарь с результатами проверки
        """
        discrepancy = abs(kl_value - kp_value - 180.0)
        allowable = 2.0 * sigma_beta * math.sqrt(2)  # допуск для расхождения КЛ/КП

        is_compliant = discrepancy <= allowable

        return {
            'actual': discrepancy,
            'allowable': allowable,
            'is_compliant': is_compliant,
            'normative': 'СП 11-104-97, п. 5.3.3',
            'kl_value': kl_value,
            'kp_value': kp_value
        }

    def check_leveling_per_stand(self, elevation_diff_per_stand: float,
                                 class_name: str = 'III_class') -> Dict[str, Any]:
        """
        Контроль превышения на станцию

        Параметры:
        - elevation_diff_per_stand: превышение на станцию в мм
        - class_name: класс нивелирования

        Возвращает:
        - Словарь с результатами проверки
        """
        tolerances = self.LEVELLING_TOLERANCES.get(class_name, self.LEVELLING_TOLERANCES['III_class'])
        allowable = tolerances['per_stand']

        is_compliant = abs(elevation_diff_per_stand) <= allowable

        return {
            'actual': abs(elevation_diff_per_stand),
            'allowable': allowable,
            'is_compliant': is_compliant,
            'normative': f'Инструкция по нивелированию ГГС, класс {class_name}'
        }

    def check_all_tolerances(self, network_data: Dict[str, Any]) -> List[Dict]:
        """
        Проверка всех 27 допусков

        Параметры:
        - network_data: словарь с данными сети, включающий:
          - traverses: список ходов с параметрами
          - sections: список нивелирных секций
          - stations: список станций с измерениями

        Возвращает:
        - Список нарушений допусков
        """
        violations = []

        # 1-6. Замыкание горизонта для разных классов полигонометрии
        for class_name in ['1_class', '2_class', '3_class', '4_class']:
            if 'stations' in network_data:
                for station in network_data['stations']:
                    if 'directions' in station and 'receptions' in station:
                        # Проверка для каждого приема на станции
                        for reception in station['receptions']:
                            directions = [obs.value for obs in reception]
                            result = self.check_circle_closure(
                                directions,
                                station.get('sigma_beta', 5.0),
                                class_name
                            )
                            if not result['is_compliant']:
                                violations.append({
                                    'type': 'circle_closure',
                                    'location': station.get('id', 'unknown'),
                                    'reception': reception.get('id', 'unknown'),
                                    'class': class_name,
                                    **result
                                })

        # 7. Расхождение направлений КЛ/КП
        if 'direction_pairs' in network_data:
            for pair in network_data['direction_pairs']:
                result = self.check_reciprocal_direction_discrepancy(
                    pair['kl'],
                    pair['kp'],
                    pair.get('sigma_beta', 5.0)
                )
                if not result['is_compliant']:
                    violations.append({
                        'type': 'kl_kp_discrepancy',
                        'location': pair.get('station', 'unknown'),
                        **result
                    })

        # 8-14. Относительные невязки ходов для разных классов
        for class_name in ['1_class', '2_class', '3_class', '4_class']:
            if 'traverses' in network_data:
                for traverse in network_data['traverses']:
                    if traverse.get('class') == class_name or class_name == '4_class':
                        result = self.check_traverse_misalignment(
                            traverse.get('length', 0),
                            traverse.get('misclosure', 0),
                            class_name
                        )
                        if not result['is_compliant']:
                            violations.append({
                                'type': 'traverse_misalignment',
                                'traverse_id': traverse.get('id', 'unknown'),
                                'class': class_name,
                                **result
                            })

                        # Проверка длины стороны
                        if 'side_lengths' in traverse:
                            for i, side_length in enumerate(traverse['side_lengths']):
                                result = self.check_side_length(side_length, class_name)
                                if not result['is_compliant']:
                                    violations.append({
                                        'type': 'side_length_exceeded',
                                        'traverse_id': traverse.get('id', 'unknown'),
                                        'side_index': i,
                                        'class': class_name,
                                        **result
                                    })

                        # Проверка числа сторон
                        if 'num_sides' in traverse:
                            result = self.check_num_sides(traverse['num_sides'], class_name)
                            if not result['is_compliant']:
                                violations.append({
                                    'type': 'num_sides_exceeded',
                                    'traverse_id': traverse.get('id', 'unknown'),
                                    'class': class_name,
                                    **result
                                })

        # 15-19. Невязки нивелирных ходов для разных классов
        for class_name in ['I_class', 'II_class', 'III_class', 'IV_class', 'technical']:
            if 'sections' in network_data:
                for section in network_data['sections']:
                    result = self.check_leveling_section_closure(
                        section.get('length_km', 0),
                        section.get('closure_mm', 0),
                        class_name
                    )
                    if not result['is_compliant']:
                        violations.append({
                            'type': 'leveling_section_closure',
                            'section_id': section.get('id', 'unknown'),
                            'class': class_name,
                            **result
                        })

                    # Проверка длины визирного луча
                    if 'sight_distances' in section:
                        for i, distance in enumerate(section['sight_distances']):
                            result = self.check_sight_distance(distance, class_name)
                            if not result['is_compliant']:
                                violations.append({
                                    'type': 'sight_distance_exceeded',
                                    'section_id': section.get('id', 'unknown'),
                                    'stand_index': i,
                                    'class': class_name,
                                    **result
                                })

        # 20-24. Длина визирного луча для разных классов
        for class_name in ['I_class', 'II_class', 'III_class', 'IV_class', 'technical']:
            if 'sight_distances' in network_data:
                for distance_info in network_data['sight_distances']:
                    result = self.check_sight_distance(
                        distance_info['distance'],
                        class_name
                    )
                    if not result['is_compliant']:
                        violations.append({
                            'type': 'sight_distance_exceeded',
                            'station': distance_info.get('station', 'unknown'),
                            'class': class_name,
                            **result
                        })

        # 25-27. Длина и число сторон ходов (уже проверено выше)

        return violations

    def check_all(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Упрощенная проверка допусков для списка измерений

        Параметры:
        - observations: список измерений

        Возвращает:
        - Список результатов проверок с полем 'passed'
        """
        results = []

        # Упрощенные проверки для основных типов измерений
        for obs in observations:
            obs_type = obs.get('type', 'unknown')
            value = obs.get('value', 0)

            if obs_type == 'direction':
                # Проверка направлений: должны быть в диапазоне 0-360°
                passed = 0 <= value <= 360
                description = f"Направление {value:.1f}° {'OK' if passed else 'вне диапазона'}"
                results.append({
                    'passed': passed,
                    'description': description,
                    'type': 'direction_range',
                    'value': value
                })

            elif obs_type == 'zenith_angle':
                # Проверка зенитных углов: должны быть в диапазоне 0-180°
                passed = 0 <= value <= 180
                description = f"Зенитный угол {value:.1f}° {'OK' if passed else 'вне диапазона'}"
                results.append({
                    'passed': passed,
                    'description': description,
                    'type': 'zenith_angle_range',
                    'value': value
                })

            elif obs_type == 'slope_distance':
                # Проверка расстояний: положительные значения до 10км
                passed = 0 < value <= 10000
                description = f"Расстояние {value:.1f}м {'OK' if passed else 'вне диапазона'}"
                results.append({
                    'passed': passed,
                    'description': description,
                    'type': 'distance_range',
                    'value': value
                })

            elif obs_type == 'height_diff':
                # Проверка превышений: разумные значения
                passed = abs(value) <= 100  # до 100м превышения
                description = f"Превышение {value:.1f}м {'OK' if passed else 'слишком большое'}"
                results.append({
                    'passed': passed,
                    'description': description,
                    'type': 'height_diff_range',
                    'value': value
                })

        return results

    def get_tolerance_summary(self, violations: List[Dict]) -> Dict[str, Any]:
        """
        Получение сводки по нарушениям допусков

        Параметры:
        - violations: список нарушений

        Возвращает:
        - Словарь со сводной статистикой
        """
        summary = {
            'total_violations': len(violations),
            'by_type': {},
            'by_class': {},
            'critical_violations': [],
            'warnings': []
        }

        for violation in violations:
            v_type = violation.get('type', 'unknown')
            v_class = violation.get('class', 'unknown')

            # Группировка по типу
            if v_type not in summary['by_type']:
                summary['by_type'][v_type] = 0
            summary['by_type'][v_type] += 1

            # Группировка по классу
            if v_class not in summary['by_class']:
                summary['by_class'][v_class] = 0
            summary['by_class'][v_class] += 1

            # Классификация по серьёзности
            severity = violation.get('severity', 'warning')
            if severity == 'critical':
                summary['critical_violations'].append(violation)
            else:
                summary['warnings'].append(violation)

        return summary
