#!/usr/bin/env python3
"""
Полный тест уравнивания на реальных данных
"""
from pathlib import Path
from geoadjust.io.formats.dat import DATParser
from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.sdr import SDRParser
from geoadjust.processing_pipeline import ProcessingPipeline
from geoadjust.core.processing_context import ProcessingContext

def test_network(network_path: Path, network_name: str):
    """Тестирование одной сети"""
    print(f"\n{'='*60}")
    print(f"ТЕСТИРОВАНИЕ СЕТИ: {network_name}")
    print(f"{'='*60}")

    # Находим файлы данных
    dat_files = list(network_path.rglob('*.DAT')) + list(network_path.rglob('*.dat'))
    gsi_files = list(network_path.rglob('*.GSI')) + list(network_path.rglob('*.gsi'))
    sdr_files = list(network_path.rglob('*.sdr')) + list(network_path.rglob('*.SDR'))

    observations = []

    # Парсим DAT файлы
    if dat_files:
        parser = DATParser()
        for f in dat_files:
            obs = parser.parse(f)
            observations.extend(obs)
            print(f"  DAT: {f.name} -> {len(obs)} наблюдений")

    # Парсим GSI файлы
    if gsi_files:
        parser = GSIParser()
        for f in gsi_files:
            obs = parser.parse(f)
            observations.extend(obs)
            print(f"  GSI: {f.name} -> {len(obs)} наблюдений")

    # Парсим SDR файлы
    if sdr_files:
        parser = SDRParser()
        for f in sdr_files:
            obs = parser.parse(f)
            observations.extend(obs)
            print(f"  SDR: {f.name} -> {len(obs)} наблюдений")

    print(f"\n  Всего наблюдений: {len(observations)}")

    if not observations:
        print("  ⚠️ Нет данных для уравнивания")
        return None

    # Находим фиксированные точки - используем известные точки из данных
    # Для нивелирных сетей обычно есть опорные точки с известными высотами
    all_points = set()
    for obs in observations:
        all_points.add(obs.station_id)
        all_points.add(obs.target_id)

    sorted_points = sorted(all_points)

    # Выбираем фиксированные точки - используем точки, которые появляются чаще всего
    # как станции (предполагаем, что они опорные)
    station_counts = {}
    for obs in observations:
        station_counts[obs.station_id] = station_counts.get(obs.station_id, 0) + 1

    # Берем 2 точки с наибольшим количеством измерений
    sorted_stations = sorted(station_counts.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_stations) >= 2:
        fixed_points = {
            sorted_stations[0][0]: 100.0,
            sorted_stations[1][0]: 101.5
        }
    else:
        fixed_points = {sorted_points[0]: 100.0}

    print(f"  Фиксированные точки: {fixed_points}")

    # Создаем контекст
    ctx = ProcessingContext(
        observations=observations,
        fixed_points=fixed_points,
        config={}
    )

    # Запускаем конвейер
    pipeline = ProcessingPipeline()
    result = pipeline.run(ctx)

    print(f"\n  Статус: {result.status}")

    # Получаем результаты из engine
    if hasattr(result, 'engine') and result.engine and result.engine._last_result:
        adj_result = result.engine._last_result
        print(f"  СКП (sigma_0): {adj_result.sigma_0:.6f} м")
        print(f"  Итераций: {adj_result.iterations}")
        print(f"  Статус сходимости: {adj_result.status}")

        print(f"\n  Уравненные высоты (первые 10):")
        sorted_heights = sorted(adj_result.adjusted_heights.items())
        for pid, h in sorted_heights[:10]:
            print(f"    {pid}: {h:.3f} м")

        return {
            'network': network_name,
            'observations': len(observations),
            'sigma_0': adj_result.sigma_0,
            'iterations': adj_result.iterations,
            'status': adj_result.status,
            'heights': adj_result.adjusted_heights
        }
    else:
        print(f"  Валидация: {result.validation_report}")
        return {
            'network': network_name,
            'observations': len(observations),
            'status': result.status,
            'validation': result.validation_report
        }

def main():
    test_dir = Path('test_real_mes')
    networks = ['l', 'b_g', 'd_d_k', 's_b', 'n_g', 'p_l_g']

    results = []
    for network in networks:
        net_path = test_dir / network
        if net_path.exists():
            res = test_network(net_path, network)
            if res:
                results.append(res)

    # Итоговый отчет
    print(f"\n{'='*60}")
    print("ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*60}")

    for res in results:
        print(f"\n{res['network']}:")
        print(f"  Наблюдений: {res['observations']}")
        if 'sigma_0' in res:
            print(f"  СКП: {res['sigma_0']:.6f} м")
            print(f"  Итераций: {res['iterations']}")
        print(f"  Статус: {res['status']}")

if __name__ == "__main__":
    main()