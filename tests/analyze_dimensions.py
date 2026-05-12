#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ размерности и уравнивание для всех SDR файлов в test_real_mes
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoAdjust-Pro: Анализ и уравнивание геодезических сетей
CLI интерфейс для обработки SDR файлов с учётом RTF ведомостей

Использование:
python analyze_dimensions.py --input-dir test_real_mes --output-dir output --rtf-parsing --adjustment-type strict
"""

import sys
import os
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Literal, Dict
import scipy.sparse as sparse
import re

from geoadjust.io.formats.sdr import SDRParser
from geoadjust.io.formats.gsi import GSIParser
from geoadjust.crs import CoordinateTransformer, GeoidModel
from geoadjust.core import NetworkPoint, Observation
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder

try:
    from striprtf.striprtf import rtf_to_text
except ImportError:
    rtf_to_text = None

@dataclass
class ComponentStatus:
    id: int
    points: List[str]
    observations: List[Observation]
    status: Literal['solvable', 'free_only', 'underdetermined', 'isolated']
    reason: str
    can_adjust_strict: bool
    can_adjust_free: bool

def build_observation_graph(network_points: dict, observations: list) -> dict:
    """Строит граф наблюдений для всех типов измерений"""
    graph = {}
    for point_id in network_points:
        graph[point_id] = {'edges': [], 'type': network_points[point_id].plan_status}

    for obs in observations:
        obs_type = obs.obs_type
        from_id = obs.from_point_id
        to_id = obs.to_point_id

        # Добавляем рёбра в зависимости от типа наблюдения
        if obs_type == 'distance':
            # Расстояние: прямая связь from -> to
            if from_id in graph and to_id in graph:
                graph[from_id]['edges'].append(to_id)
                graph[to_id]['edges'].append(from_id)

        elif obs_type == 'direction':
            # Направление: от станции к цели
            if from_id in graph and to_id in graph:
                graph[from_id]['edges'].append(to_id)

        elif obs_type == 'height_diff':
            # Превышение: связь from -> to
            if from_id in graph and to_id in graph:
                graph[from_id]['edges'].append(to_id)
                graph[to_id]['edges'].append(from_id)

        elif obs_type == 'azimuth':
            # Азимут: от станции к цели
            if from_id in graph and to_id in graph:
                graph[from_id]['edges'].append(to_id)

        elif obs_type == 'zenith_angle':
            # Зенитный угол: от станции к цели
            if from_id in graph and to_id in graph:
                graph[from_id]['edges'].append(to_id)

        elif obs_type == 'gnss_vector':
            # GNSS вектор: прямая связь from -> to
            if from_id in graph and to_id in graph:
                graph[from_id]['edges'].append(to_id)
                graph[to_id]['edges'].append(from_id)

        # Для углов: если есть дополнительные точки (target1, target2), добавить связи
        # Предполагаем, что obs может иметь target_ids
        if hasattr(obs, 'target_ids') and obs.target_ids:
            for target_id in obs.target_ids:
                if from_id in graph and target_id in graph:
                    graph[from_id]['edges'].append(target_id)

    # Убираем дубликаты в edges
    for point_id in graph:
        graph[point_id]['edges'] = list(set(graph[point_id]['edges']))

    return graph

def find_connected_components(graph: dict) -> List[List[str]]:
    """Находит связные компоненты графа (BFS)"""
    visited = set()
    components = []
    for point in graph:
        if point not in visited:
            component = []
            queue = [point]
            while queue:
                current = queue.pop(0)
                if current not in visited:
                    visited.add(current)
                    component.append(current)
                    queue.extend(graph[current]['edges'])
            if len(component) >= 2:  # Минимум 2 точки для сети
                components.append(component)
    return components

def parse_coordinate_report(rtf_file: Path) -> Dict[str, Dict]:
    """Парсит RTF ведомость координат, возвращает dict точка: {'x':, 'y':, 'h':, 'sigma_x':, 'sigma_y':, 'sigma_h':}"""
    if rtf_to_text is None:
        print("striprtf не установлен, пропуск парсинга RTF")
        return {}

    with open(rtf_file, 'r', encoding='cp1251', errors='ignore') as f:
        rtf_content = f.read()

    text = rtf_to_text(rtf_content)

    points = {}
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Ищем строки с | разделителями (таблица RTF)
        parts = re.split(r'\|', line.strip())
        if len(parts) >= 6 and parts[0].isdigit():  # Начинается с номера строки
            try:
                point_id = parts[1]  # Название точки
                x = float(parts[2].replace(',', '.')) if parts[2] not in ['-', ''] else None
                y = float(parts[3].replace(',', '.')) if parts[3] not in ['-', ''] else None
                mxy = float(parts[4].replace(',', '.')) if len(parts) > 4 and parts[4] not in ['-', ''] else 0.0
                h = float(parts[5].replace(',', '.')) if len(parts) > 5 and parts[5] not in ['-', ''] else None
                mh = float(parts[6].replace(',', '.')) if len(parts) > 6 and parts[6] not in ['-', ''] else 0.0
                if point_id and not point_id.isdigit():  # Не чистый номер
                    points[point_id] = {
                        'x': x, 'y': y, 'h': h,
                        'sigma_x': mxy, 'sigma_y': mxy, 'sigma_h': mh
                    }
            except (ValueError, IndexError):
                continue
    return points

def preprocess_gnss_data(points_dict: dict, anomaly_path: str):
    """Предобработка GNSS данных: трансформация в плоские координаты и нормальные высоты"""
    transformer = CoordinateTransformer()
    geoid = GeoidModel(data_dir=Path(anomaly_path))

    for point_id, point in points_dict.items():
        if point.coord_type == 'FIXED' and point.x and point.y:  # GNSS точки
            # Предполагаем WGS84 геоцентрические, трансформация в плоские (UTM зона)
            # Для простоты: если координаты > 180, это долгота/широта, трансформировать
            if abs(point.x) > 180 or abs(point.y) > 90:  # Геодезические
                # Преобразование WGS84 -> UTM (упрощённо)
                flat_x, flat_y = transformer.wgs84_to_utm(point.y, point.x)  # lat, lon
                point.x, point.y = flat_x, flat_y

            # Геодезическая высота к нормальной через геоид
            if point.h is not None:
                try:
                    anomaly = geoid.get_height_anomaly(point.x, point.y)  # Аномалия геоида
                    point.h = point.h - anomaly  # Нормальная высота
                except:
                    pass  # Если не удалось, оставить

    return points_dict

def classify_component(component_points: List[str], network_points: dict, observations: list, graph: dict) -> ComponentStatus:
    """Классифицирует компоненту по разрешимости с учётом типов измерений"""
    comp_id = hash(tuple(sorted(component_points))) % 10000  # Простой ID

    # Фильтр наблюдений для компоненты
    comp_obs = [obs for obs in observations if obs.from_point_id in component_points and (obs.to_point_id in component_points or (hasattr(obs, 'target_ids') and any(t in component_points for t in obs.target_ids)))]

    # Подсчёт типов измерений
    obs_types = {}
    for obs in comp_obs:
        obs_types[obs.obs_type] = obs_types.get(obs.obs_type, 0) + 1

    # Подсчёт неизвестных (предполагаем 2D-план)
    fixed_points = [p for p in component_points if network_points[p].coord_type == 'FIXED']
    working_points = [p for p in component_points if network_points[p].coord_type != 'FIXED']
    unknowns = len(working_points) * 2  # X, Y (упрощённо)

    obs_count = len(comp_obs)

    # Критерии с учётом типов
    min_points_ok = len(component_points) >= 2
    if 'angle' in obs_types or 'direction' in obs_types:
        min_points_ok = len(component_points) >= 3  # Для углов/направлений минимум 3 точки

    datum_ok = len(fixed_points) >= 1
    if 'gnss_vector' in obs_types:
        datum_ok = len(fixed_points) >= 1  # GNSS требует datum

    # Оценка redundancy (упрощённо)
    redundancy = obs_count - unknowns

    reason = f"Наблюдения: {obs_types}, redundancy={redundancy}"

    if not min_points_ok:
        return ComponentStatus(
            id=comp_id, points=component_points, observations=comp_obs,
            status='isolated', reason=f'недостаточно точек ({len(component_points)}), {reason}', can_adjust_strict=False, can_adjust_free=False
        )
    if redundancy < 0:
        return ComponentStatus(
            id=comp_id, points=component_points, observations=comp_obs,
            status='underdetermined', reason=f'недостаточно наблюдений, {reason}', can_adjust_strict=False, can_adjust_free=False
        )
    if datum_ok:
        return ComponentStatus(
            id=comp_id, points=component_points, observations=comp_obs,
            status='solvable', reason=reason, can_adjust_strict=True, can_adjust_free=True
        )
    else:
        return ComponentStatus(
            id=comp_id, points=component_points, observations=comp_obs,
            status='free_only', reason=f'нет datum, {reason}', can_adjust_strict=False, can_adjust_free=True
        )

def main():
    parser = argparse.ArgumentParser(description="GeoAdjust-Pro: Анализ и уравнивание геодезических сетей")
    parser.add_argument('--input-dir', type=str, default='test_real_mes', help='Директория с входными файлами')
    parser.add_argument('--output-dir', type=str, default='output', help='Директория для результатов')
    parser.add_argument('--rtf-parsing', action='store_true', help='Включить парсинг RTF ведомостей для fixed точек')
    parser.add_argument('--adjustment-type', choices=['strict', 'free', 'auto'], default='auto', help='Тип уравнивания: strict (только solvable), free (включая free_only), auto (по классификации)')
    parser.add_argument('--verbose', action='store_true', help='Подробный вывод')
    parser.add_argument('--files', nargs='*', help='Список конкретных файлов для обработки')
    parser.add_argument('--anomaly-path', type=str, default='C:\\Users\\gorta.DUDOSG\\Downloads\\P-of-Geo-Meas\\anomaly eight', help='Путь к картам аномалий геоида')

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"GeoAdjust-Pro: Анализ сетей в {input_dir}")

    # Найти файлы
    if args.files:
        files = [Path(f) for f in args.files if Path(f).suffix.lower() in ['.sdr', '.gsi']]
    else:
        sdr_files = list(input_dir.glob('**/*.sdr'))
        gsi_files = list(input_dir.glob('**/*.GSI'))
        files = sdr_files + gsi_files

    if not files:
        print("Файлы не найдены")
        return

    # Обработка файлов
    process_files(files, args.rtf_parsing, args.adjustment_type, args.verbose, output_dir, args.anomaly_path)

def process_files(files, rtf_parsing, adjustment_type, verbose, output_dir, anomaly_path):
    print(f"Найдено {len(files)} файлов")
    for file_path in files:
        print(f"\n=== Обработка файла: {file_path} ===")
        suffix = file_path.suffix.lower()
        if suffix == '.sdr':
            parser = SDRParser()
        elif suffix == '.gsi':
            parser = GSIParser()
        else:
            print(f"Неподдерживаемый формат: {suffix}")
            continue

        try:
            result = parser.parse(str(file_path))
        except Exception as e:
            print(f"Ошибка парсинга {file_path}: {e}")
            continue

    # Найти RTF
    reference_points = {}
    if rtf_parsing:
        rtf_file = find_rtf_file(file_path)
        if rtf_file:
            print(f"Найден RTF: {rtf_file}")
            reference_points = parse_coordinate_report(rtf_file)
            print(f"Из RTF извлечено {len(reference_points)} точек")
        else:
            print("RTF не найден")

        try:
            points = result.get('points', [])
            observations = result.get('observations', [])

            if verbose:
                print(f"Парсер вернул {len(points)} точек и {len(observations)} наблюдений")
                for i, p in enumerate(points[:3]):
                    print(f"Точка {i}: {p['point_id']}, type={p.get('point_type')}, x={p.get('x')}")
                for i, obs in enumerate(observations[:3]):
                    print(f"Наблюдение {i}: from={obs.from_point_id}, to={obs.to_point_id}, dist={getattr(obs, 'slope_distance', 'N/A')}")

            # Преобразование точек
            points_dict = {}
            working_points = 0
            for p in points:
                coord_type = 'FREE'
                x = p.get('x')
                y = p.get('y')
                h = p.get('h')
                plan_status = 'working'

                # Если в reference и sigma=0, FIXED
                point_id = p['point_id']
                if point_id in reference_points and reference_points[point_id]['sigma_x'] == 0.0:
                    coord_type = 'FIXED'
                    x = reference_points[point_id]['x']
                    y = reference_points[point_id]['y']
                    h = reference_points[point_id]['h']
                    plan_status = 'initial'

                points_dict[point_id] = NetworkPoint(
                    point_id=point_id,
                    coord_type=coord_type,
                    x=x, y=y, h=h,
                    plan_status=plan_status,
                    height_status=plan_status
                )
                if plan_status == 'working':
                    working_points += 1

            # Добавление недостающих точек
            all_point_ids = set()
            for obs in observations:
                all_point_ids.add(obs.from_point_id)
                all_point_ids.add(obs.to_point_id)
            for point_id in all_point_ids:
                if point_id not in points_dict:
                    points_dict[point_id] = NetworkPoint(
                        point_id=point_id,
                        coord_type='FREE',
                        x=None, y=None, h=None,
                        plan_status='working',
                        height_status='working'
                    )
                    working_points += 1

        # Предобработка GNSS данных
        points_dict = preprocess_gnss_data(points_dict, anomaly_path)

        print(f"Всего точек: {len(points)}")
        print(f"Рабочих точек: {working_points}")
            unknowns = working_points * 2
            observations_count = len([obs for obs in observations if hasattr(obs, 'slope_distance') and obs.slope_distance])
            degrees_of_freedom = observations_count - unknowns
            print(f"Неизвестных: {unknowns}, Наблюдений: {observations_count}, Степени свободы: {degrees_of_freedom}")

            if degrees_of_freedom < 0:
                print("Система недоопределена")
                continue
            elif degrees_of_freedom == 0:
                print("Система определена")
            else:
                print("Система переопределена")

            # Граф и компоненты
            graph = build_observation_graph(points_dict, observations)
            components_points = find_connected_components(graph)
            print(f"Компонент: {len(components_points)}")

            # Уравнивание
            equations_builder = EquationsBuilder()
            weight_builder = WeightBuilder()
            engine = AdjustmentEngine()

            for comp in components_points:
                status = classify_component(comp, points_dict, observations)
                comp_points = {pid: points_dict[pid] for pid in comp}
                comp_obs = [obs for obs in observations if obs.from_point_id in comp and obs.to_point_id in comp]

                can_adjust = (adjustment_type == 'auto' and status.can_adjust_free) or \
                            (adjustment_type == 'strict' and status.can_adjust_strict) or \
                            (adjustment_type == 'free' and status.can_adjust_free)

                if can_adjust:
                    fixed_points = [p for p in comp if points_dict[p].coord_type == 'FIXED']
                    A, L = equations_builder.build_adjustment_matrix(comp_obs, comp_points, fixed_points)
                    P = sparse.eye(A.shape[0])
                    result_adj = engine.adjust(A, L, P)
                    print(f"Уравнено: {status.status}, СКП={result_adj['sigma0']*1000:.3f}мм")

                    # Сравнение
                    if reference_points:
                        dx = result_adj['coordinate_corrections']
                        param_index = 0
                        for pid in sorted(comp):
                            if points_dict[pid].coord_type != 'FIXED':
                                x_adj = points_dict[pid].x + dx[param_index] if points_dict[pid].x else None
                                y_adj = points_dict[pid].y + dx[param_index + 1] if points_dict[pid].y else None
                                if pid in reference_points and x_adj and y_adj:
                                    ref = reference_points[pid]
                                    diff_x = (x_adj - ref['x']) * 1000
                                    diff_y = (y_adj - ref['y']) * 1000
                                    print(f"  {pid}: dx={diff_x:.1f}мм, dy={diff_y:.1f}мм")
                                param_index += 2
                else:
                    print(f"Пропущено: {status.reason}")

        except Exception as e:
            print(f"Ошибка анализа {sdr_file}: {e}")

def find_rtf_file(sdr_file):
    """Найти соответствующий RTF файл"""
    for rtf in sdr_file.parent.glob('**/*Ведомость*координат*.rtf'):
        if sdr_file.parent == rtf.parent or str(rtf).find(sdr_file.stem) != -1:
            return rtf
    return None

if __name__ == "__main__":
    main()

print(f"Найдено {len(sdr_files)} SDR файлов")

for sdr_file in sdr_files:
    print(f"\n=== Обработка файла: {sdr_file} ===")
    parser = SDRParser()
    try:
        result = parser.parse(str(sdr_file))
    except Exception as e:
        print(f"Ошибка парсинга {sdr_file}: {e}")
        continue

    # Найти соответствующий RTF с ведомостью координат
    rtf_file = None
    for rtf in test_dir.glob('**/*Ведомость*координат*.rtf'):
        if sdr_file.parent == rtf.parent or (sdr_file.parent.name in str(rtf) and 'plan' in str(rtf)):
            rtf_file = rtf
            break
    if rtf_file:
        print(f"Найден RTF: {rtf_file}")
        reference_points = parse_coordinate_report(rtf_file)
        print(f"Из RTF извлечено {len(reference_points)} точек")
    else:
        reference_points = {}
        print("RTF не найден")

    try:
        points = result.get('points', [])
        observations = result.get('observations', [])

        print(f"Парсер вернул {len(points)} точек и {len(observations)} наблюдений")
        for i, p in enumerate(points[:3]):  # Первые 3 точки
            print(f"Точка {i}: {p['point_id']}, type={p.get('point_type')}, x={p.get('x')}")
        for i, obs in enumerate(observations[:3]):  # Первые 3 наблюдения
            print(f"Наблюдение {i}: from={obs.from_point_id}, to={obs.to_point_id}, dist={getattr(obs, 'slope_distance', 'N/A')}")

        # Преобразуем точки
        points_dict = {}
        working_points = 0
        for p in points:
            point_id = p['point_id']
            # Если в reference и sigma=0, задать как FIXED с координатами из reference
            if point_id in reference_points and reference_points[point_id]['sigma_x'] == 0.0 and reference_points[point_id]['sigma_y'] == 0.0:
                coord_type = 'FIXED'
                x = reference_points[point_id]['x']
                y = reference_points[point_id]['y']
                h = reference_points[point_id]['h']
                plan_status = 'initial'
            else:
                coord_type = 'FREE'
                x = p.get('x')
                y = p.get('y')
                h = p.get('h')
                plan_status = 'working'
            points_dict[point_id] = NetworkPoint(
                point_id=point_id,
                coord_type=coord_type,
                x=x,
                y=y,
                h=h,
                plan_status=plan_status,
                height_status=plan_status
            )
            if plan_status == 'working':
                working_points += 1

        # Добавим точки из наблюдений, которых нет в points
        all_point_ids = set()
        for obs in observations:
            from_id = getattr(obs, 'from_point_id', getattr(obs, 'from_point', None))
            to_id = getattr(obs, 'to_point_id', getattr(obs, 'to_point', None))
            if from_id:
                all_point_ids.add(from_id)
            if to_id:
                all_point_ids.add(to_id)

        for point_id in all_point_ids:
            if point_id not in points_dict:
                points_dict[point_id] = NetworkPoint(
                    point_id=point_id,
                    coord_type='FREE',
                    x=None,
                    y=None,
                    h=None,
                    plan_status='working',
                    height_status='working'
                )
                working_points += 1

        print(f"Всего точек: {len(points)}")
        print(f"Рабочих точек: {working_points}")
        print(f"Неизвестных параметров плана: {working_points * 2}")  # X и Y для каждой точки

        # Создаем все наблюдения
        all_observations = []
        for obs in observations:
            obs_type = getattr(obs, 'obs_type', 'height_diff')  # Для GSI по умолчанию height_diff
            from_id = getattr(obs, 'from_point_id', getattr(obs, 'from_point', None))
            to_id = getattr(obs, 'to_point_id', getattr(obs, 'to_point', None))
            value = getattr(obs, 'value', getattr(obs, 'height_difference', None))

            if value is not None and from_id and to_id:
                simple_obs = Observation(
                    obs_id=f"obs_{len(all_observations)}",
                    obs_type=obs_type,
                    from_setup_id='setup_0',  # Заглушка
                    from_point_id=from_id,
                    to_point_id=to_id,
                    value=value
                )
                # Для углов добавить target_ids если есть
                if hasattr(obs, 'target_ids'):
                    simple_obs.target_ids = obs.target_ids
                all_observations.append(simple_obs)

        print(f"Всего наблюдений: {len(all_observations)}")

        # Расчет степеней свободы (упрощённо)
        unknowns = working_points * 2  # X и Y координаты
        observations_count = len(all_observations)
        degrees_of_freedom = observations_count - unknowns

        print("\nАнализ размерности:")
        print(f"Неизвестные параметры: {unknowns}")
        print(f"Наблюдения: {observations_count}")
        print(f"Степени свободы: {degrees_of_freedom}")

        if degrees_of_freedom < 0:
            print("СИСТЕМА НЕДООПРЕДЕЛЕНА!")
            print(f"Нужно еще {-degrees_of_freedom} наблюдений")
        elif degrees_of_freedom == 0:
            print("СИСТЕМА ОПРЕДЕЛЕНА (нулевые степени свободы)")
        else:
            print("СИСТЕМА ПЕРЕОПРЕДЕЛЕНА")
            print(f"Избыточность: {degrees_of_freedom} наблюдений")

        # Построение графа
        graph = build_observation_graph(points_dict, all_observations)

        # Компоненты
        components_points = find_connected_components(graph)
        print(f"\nНайдено {len(components_points)} связных компонент")
        for i, comp in enumerate(components_points[:2]):  # Первые 2 компоненты
            print(f"Компонента {i}: {len(comp)} точек")

        # Классификация
        component_statuses = []
        for comp in components_points:
            status = classify_component(comp, points_dict, all_observations, graph)
            component_statuses.append(status)
            print(f"Компонента {status.id}: статус {status.status}, точки {len(status.points)}, наблюдения {len(status.observations)}, причина: {status.reason}")

        print(f"Итого компонент: solvable={sum(1 for s in component_statuses if s.can_adjust_strict)}, free_only={sum(1 for s in component_statuses if s.can_adjust_free and not s.can_adjust_strict)}, excluded={sum(1 for s in component_statuses if not s.can_adjust_free)}")

        # Уравнивание для всех уравниваемых компонент
        equations_builder = EquationsBuilder()
        weight_builder = WeightBuilder()
        engine = AdjustmentEngine()

        for status in component_statuses:
            if status.can_adjust_free:
                print(f"\nУравнивание компоненты {status.id} ({status.status})...")
                try:
                    # Фильтр точек и наблюдений для компоненты
                    comp_points = {pid: points_dict[pid] for pid in status.points}
                    fixed_points = [p for p in status.points if points_dict[p].coord_type == 'FIXED']
                    # Построение уравнений
                    A, L = equations_builder.build_adjustment_matrix(status.observations, comp_points, fixed_points)
                    P = sparse.eye(A.shape[0])  # Единичная весовая матрица
                    print(f"Матрицы: A {A.shape}, L {L.shape}, P {P.shape}, fixed_points: {len(fixed_points)}")

                    # Уравнивание
                    result = engine.adjust(A, L, P)
                    print(f"СКП = {result['sigma0']*1000:.3f} мм, итераций = {result['iterations']}")
                except Exception as e:
                    print(f"Ошибка уравнивания: {e}")
            else:
                print(f"Компонента {status.id} пропущена: {status.reason}")

        except Exception as e:
            print(f"Ошибка анализа файла {file_path}: {e}")

print("\nОбработка завершена.")