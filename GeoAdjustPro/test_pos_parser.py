#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование POS парсера на реальных GNSS данных
"""

import sys
from pathlib import Path


from geoadjust.io.formats.pos import POSParser

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

TEST_DATA_DIR = Path(__file__).parent.parent / 'test_real_mes' / 'gnss'


def test_pos_parser():
    """Тестирование POS парсера"""
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ POS ПАРСЕРА (GNSS векторы)")
    print("=" * 70)
    
    pos_files = list(TEST_DATA_DIR.glob('*.pos'))
    
    if not pos_files:
        print("  Файлы POS не найдены!")
        return []
    
    results = []
    
    for pos_file in pos_files:
        print(f"\n--- Файл: {pos_file.name} ---")
        print(f"  Размер: {pos_file.stat().st_size / 1024:.1f} КБ")
        
        parser = POSParser()
        try:
            result = parser.parse(pos_file)
            
            print(f"\n  Результаты парсинга:")
            print(f"    Формат: {result['format']}")
            print(f"    Кодировка: {result['encoding']}")
            print(f"    Всего строк: {result['total_lines']}")
            print(f"    Эпох: {result['num_epochs']}")
            print(f"    Базовая станция: {result['from_station']}")
            print(f"    Подвижная станция: {result['to_station']}")
            print(f"    Опорная позиция: {result['ref_position']}")
            print(f"    Ошибок: {len(result['errors'])}")
            
            # Информация из заголовка
            header = result['header_info']
            print(f"\n  Параметры обработки:")
            print(f"    Программа: {header.get('program', 'N/A')}")
            print(f"    Режим: {header.get('pos_mode', 'N/A')}")
            print(f"    Частоты: {header.get('freqs', 'N/A')}")
            print(f"    Решение: {header.get('solution', 'N/A')}")
            print(f"    Маска угла: {header.get('elev_mask', 'N/A')}°")
            print(f"    Нав. системы: {header.get('navi_sys', 'N/A')}")
            print(f"    Начало: {header.get('obs_start', 'N/A')}")
            print(f"    Конец: {header.get('obs_end', 'N/A')}")
            
            # Статистика
            stats = parser.get_statistics()
            print(f"\n  Статистика:")
            print(f"    Среднее число спутников: {stats['avg_satellites']:.1f}")
            print(f"    Средний СКО X: {stats['avg_sdx']*1000:.2f} мм")
            print(f"    Средний СКО Y: {stats['avg_sdy']*1000:.2f} мм")
            print(f"    Средний СКО Z: {stats['avg_sdz']*1000:.2f} мм")
            print(f"    Качество решений: {stats['quality_counts']}")
            
            # GNSS вектор
            vector = parser.get_gnss_vector()
            if vector:
                print(f"\n  GNSS вектор {vector.from_station} -> {vector.to_station}:")
                print(f"    dX = {vector.dx:.4f} m (std={vector.sigma_dx*1000:.2f} mm)")
                print(f"    dY = {vector.dy:.4f} m (std={vector.sigma_dy*1000:.2f} mm)")
                print(f"    dZ = {vector.dz:.4f} m (std={vector.sigma_dz*1000:.2f} mm)")
                print(f"    Quality: {vector.quality}, Satellites: {vector.n_satellites}")
            
            if result['epochs']:
                print(f"\n  Первые 3 эпохи:")
                for i, epoch in enumerate(result['epochs'][:3], 1):
                    print(f"    {i}. {epoch.gpst_time}: X={epoch.x_ecef:.4f}, Y={epoch.y_ecef:.4f}, Z={epoch.z_ecef:.4f}, Q={epoch.quality}, ns={epoch.n_satellites}")
            
            results.append({
                'file': str(pos_file),
                'success': result['success'],
                'num_epochs': result['num_epochs'],
                'from_station': result['from_station'],
                'to_station': result['to_station'],
                'vector': vector
            })
            
        except Exception as e:
            print(f"  ОШИБКА при парсинге: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'file': str(pos_file),
                'success': False,
                'error': str(e)
            })
    
    return results


def print_summary(results):
    """Вывод сводной информации"""
    print("\n" + "=" * 70)
    print("СВОДНАЯ ИНФОРМАЦИЯ ПО GNSS ВЕКТОРАМ")
    print("=" * 70)
    
    for r in results:
        status = "OK" if r.get('success', False) else "FAIL"
        file_name = Path(r['file']).name
        
        if r.get('success', False):
            vector = r.get('vector')
            if vector:
                print(f"\n  [{status}] {file_name}")
                print(f"       {vector.from_station} -> {vector.to_station}")
                print(f"       dX = {vector.dx:.4f} m (std={vector.sigma_dx*1000:.2f} mm)")
                print(f"       dY = {vector.dy:.4f} m (std={vector.sigma_dy*1000:.2f} mm)")
                print(f"       dZ = {vector.dz:.4f} m (std={vector.sigma_dz*1000:.2f} mm)")
                print(f"       Epochs: {r['num_epochs']}, Quality: {vector.quality}")
            else:
                print(f"\n  [{status}] {file_name}: No vector")
        else:
            print(f"\n  [{status}] {file_name}: {r.get('error', 'Неизвестная ошибка')}")


if __name__ == '__main__':
    print("Тестирование POS парсера на реальных GNSS данных")
    print(f"Директория с данными: {TEST_DATA_DIR}")
    
    if not TEST_DATA_DIR.exists():
        print(f"ОШИБКА: Директория {TEST_DATA_DIR} не существует!")
        sys.exit(1)
    
    results = test_pos_parser()
    print_summary(results)
    
    print(f"\n{'=' * 70}")
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print(f"{'=' * 70}")
