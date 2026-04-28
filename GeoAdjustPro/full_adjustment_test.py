import sys
from pathlib import Path
sys.path.insert(0, 'C:/Users/gorta.DUDOSG/Downloads/P-of-Geo-Meas/GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser
from geoadjust.core.preprocessing.module import PreprocessingModule
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder
from geoadjust.core.adjustment.engine import AdjustmentEngine

print('=== ДИАГНОСТИКА ПРОБЛЕМЫ С УРАВНИВАНИЕМ ===')
print('Файл: badgro16093_const.sdr')
print()

# Шаг 1: Парсинг SDR файла
print('1. Парсинг SDR файла...')
parser = SDRParser()
result = parser.parse(Path('test_real_mes/b_g/plan/badgro16093_const.sdr'))

print('   Результат парсинга:')
print('   - Успех:', result.get('success', False))
print('   - Измерений:', result.get('num_observations', 0))
print('   - Точек:', len(result.get('points', [])))
print('   - Установок:', result.get('num_setups', 0))

# Анализ измерений
observations = result.get('observations', [])
points = result.get('points', [])

print()
print('2. Анализ измерений:')
obs_types = {}
for obs in observations:
    obs_type = getattr(obs, 'obs_type', 'unknown')
    obs_types[obs_type] = obs_types.get(obs_type, 0) + 1

print('   Типы измерений:')
for obs_type, count in sorted(obs_types.items()):
    print('     {}: {}'.format(obs_type, count))

# Анализ точек
print()
print('3. Анализ точек:')
fixed_points = [p for p in points if p.get('point_type') == 'FIXED']
free_points = [p for p in points if p.get('point_type') != 'FIXED']

print('   Фиксированных точек:', len(fixed_points))
print('   Свободных точек:', len(free_points))

for p in fixed_points[:3]:
    print('     FIXED: {} ({}, {})'.format(p['point_id'], p.get('x'), p.get('y')))

# Фильтрация валидных измерений
print()
print('4. Фильтрация валидных измерений:')
point_ids = set(p['point_id'] for p in points)
valid_observations = []
invalid_observations = []

for obs in observations:
    from_id = getattr(obs, 'from_point_id', None)
    to_id = getattr(obs, 'to_point_id', None)
    if from_id in point_ids and to_id in point_ids:
        valid_observations.append(obs)
    else:
        invalid_observations.append(obs)

print('   Валидных измерений:', len(valid_observations))
print('   Невалидных измерений:', len(invalid_observations))

# Шаг 2: Предобработка
print()
print('5. Предобработка...')
preprocessor = PreprocessingModule()
prep_result = preprocessor.run_preprocessing(valid_observations, points, {})

print('   Стадии обработки:', prep_result.get('stages_completed', 0))

# Обновление точек координатами из предобработки
prelim_coords = prep_result.get('preliminary_coordinates', {}).get('coordinates', {})
print('   Рассчитано предварительных координат:', len(prelim_coords))

points_dict = {p['point_id']: p for p in points}
for pid, coord in prelim_coords.items():
    if pid in points_dict:
        old_x = points_dict[pid].get('x')
        old_y = points_dict[pid].get('y')
        points_dict[pid]['x'] = coord.get('x', old_x)
        points_dict[pid]['y'] = coord.get('y', old_y)
        print('     Обновлена точка {}: x={}, y={}'.format(pid, coord.get('x'), coord.get('y')))

# Шаг 3: Подготовка к уравниванию
print()
print('6. Подготовка данных для уравнивания...')

# Конвертация в NetworkPoint
from geoadjust.core.network.models import NetworkPoint
network_points = {}
fixed_points_list = []

for p in points:
    point = NetworkPoint(
        point_id=p['point_id'],
        x=p.get('x'),
        y=p.get('y'),
        h=p.get('h'),
        coord_type=p.get('point_type', 'FREE')
    )
    network_points[p['point_id']] = point
    if p.get('point_type') == 'FIXED':
        fixed_points_list.append(p['point_id'])

    points_with_coords = sum(1 for p in network_points.values() if p.x is not None and p.y is not None)
    print('   Точек с координатами: {}/{}'.format(points_with_coords, len(network_points)))
    print('   Фиксированных точек:', len(fixed_points_list))

    print('   Совместимых измерений:', len(valid_observations))

    # Конвертация измерений в Observation объекты
    from geoadjust.core.network.models import Observation
    compatible_observations = []
    for obs in valid_observations:
        # Для CombinedObservation нужно определить value в зависимости от типа
        obs_type = getattr(obs, 'obs_type', 'unknown')
        value = 0.0
        if obs_type == 'direction' and obs.horizontal_angle is not None:
            value = obs.horizontal_angle
        elif obs_type == 'distance' and obs.slope_distance is not None:
            value = obs.slope_distance
        elif obs_type == 'zenith_angle' and obs.zenith_angle is not None:
            value = obs.zenith_angle
        elif obs_type == 'combined' and obs.horizontal_angle is not None:
            value = obs.horizontal_angle  # Для совместимости берем горизонтальный угол

        observation = Observation(
            obs_id=getattr(obs, 'obs_id', 'UNK'),
            obs_type=obs_type,
            from_setup_id=getattr(obs, 'from_setup_id', ''),
            from_point_id=getattr(obs, 'from_point_id', ''),
            to_point_id=getattr(obs, 'to_point_id', ''),
            value=value,
            sigma_apriori=0.001,  # Значение по умолчанию
            face_position=getattr(obs, 'face_position', None),
            raw_line=getattr(obs, 'raw_line', None)
        )
        compatible_observations.append(observation)

    print('   Observation объектов:', len(compatible_observations))

# Шаг 4: Построение уравнений
print()
print('7. Попытка построения уравнений...')
builder = EquationsBuilder()

try:
    A, L = builder.build_adjustment_matrix(compatible_observations, network_points, fixed_points_list)
    print('   ✅ УСПЕХ: Матрица построена {}x{} с {} уравнениями'.format(A.shape[0], A.shape[1], len(L)))

    if A.shape[0] > 0:
        print()
        print('8. Построение весовой матрицы...')
        weight_builder = WeightBuilder()
        P = weight_builder.build_weight_matrix(compatible_observations, network_points)
        print('   ✅ Весовая матрица: {}x{}'.format(P.shape[0], P.shape[1]))

        print()
        print('9. Запуск уравнивания...')
        engine = AdjustmentEngine()
        adjustment_result = engine.adjust(A, L, P)

        print('   ✅ УРАВНИВАНИЕ ЗАВЕРШЕНО!')
        print('   - СКО единицы веса: {:.6f}'.format(adjustment_result.get('sigma0', 0)))
        print('   - Количество итераций: {}'.format(adjustment_result.get('iterations', 0)))

        if adjustment_result.get('coordinates'):
            print('   - Уравненные координаты рассчитаны для {} точек'.format(len(adjustment_result['coordinates'])))

        print()
        print('🎉 ПОЛНОЕ УРАВНИВАНИЕ ПРОШЛО УСПЕШНО!')

    else:
        print('   ❌ Матрица построена, но нет уравнений')

except Exception as e:
    print('   ❌ ОШИБКА при построении уравнений:', e)
    import traceback
    traceback.print_exc()

    # Детальный анализ проблемы
    print()
    print('8. ДИАГНОСТИКА ПРОБЛЕМЫ:')
    print('   Анализ каждого измерения:')

    for i, obs in enumerate(compatible_observations[:10]):
        from_point = network_points.get(obs.from_point_id)
        to_point = network_points.get(obs.to_point_id)

        from_coords = (from_point.x, from_point.y) if from_point else (None, None)
        to_coords = (to_point.x, to_point.y) if to_point else (None, None)

        print('     {}. {}: тип={}, от {} {} к {} {}'.format(
            i+1, obs.obs_id, obs.obs_type,
            obs.from_point_id, from_coords,
            obs.to_point_id, to_coords
        ))