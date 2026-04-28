#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование парсеров на реальных данных из папки test_real_mes
Проверка корректности парсинга GSI, SDR, DAT форматов
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.sdr import SDRParser
from geoadjust.io.formats.dat import DATParser

import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Базовый путь к тестовым данным
TEST_DATA_DIR = Path(__file__).parent.parent / 'test_real_mes'


def test_gsi_parser():
    """Тестирование парсера GSI на реальных файлах"""
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ GSI ПАРСЕРА")
    print("=" * 70)
    
    gsi_files = list(TEST_DATA_DIR.glob('**/*.GSI'))
    
    if not gsi_files:
        print("  Файлы GSI не найдены!")
        return []
    
    results = []
    
    for gsi_file in gsi_files:
        print(f"\n--- Файл: {gsi_file.name} ---")
        print(f"  Путь: {gsi_file}")
        
        # Показываем первые 5 строк для анализа
        with open(gsi_file, 'r', encoding='cp1251', errors='ignore') as f:
            first_lines = f.readlines()[:5]
            print(f"  Первые строки:")
            for i, line in enumerate(first_lines, 1):
                print(f"    {i}: {line.strip()[:80]}")
        
        parser = GSIParser()
        try:
            result = parser.parse(gsi_file)
            
            print(f"\n  Результаты парсинга:")
            print(f"    Формат: {result['format']} версия {result['version']}")
            print(f"    Кодировка: {result['encoding']}")
            print(f"    Всего строк: {result['total_lines']}")
            print(f"    Измерений: {result['num_observations']}")
            print(f"    Пунктов: {result['num_points']}")
            print(f"    Ошибок: {len(result['errors'])}")
            
            if result['observations']:
                print(f"\n  Первые 5 измерений:")
                for i, obs in enumerate(result['observations'][:5], 1):
                    print(f"    {i}. Тип: {obs.obs_type:15} | От: {obs.from_point:15} | К: {obs.to_point:15} | Значение: {obs.value:.6f}")
            
            if result['errors']:
                print(f"\n  Первые 5 ошибок:")
                for error in result['errors'][:5]:
                    print(f"    Строка {error.get('line', '?')}: {error.get('message', 'Неизвестная ошибка')}")
            
            stats = parser.get_statistics()
            print(f"\n  Статистика по типам:")
            for obs_type, count in stats['by_type'].items():
                print(f"    {obs_type}: {count}")
            
            results.append({
                'file': str(gsi_file),
                'success': result['success'],
                'num_observations': result['num_observations'],
                'num_points': result['num_points'],
                'num_errors': len(result['errors'])
            })
            
        except Exception as e:
            print(f"  ОШИБКА при парсинге: {e}")
            results.append({
                'file': str(gsi_file),
                'success': False,
                'error': str(e)
            })
    
    return results


def test_sdr_parser():
    """Тестирование парсера SDR на реальных файлах"""
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ SDR ПАРСЕРА")
    print("=" * 70)
    
    sdr_files = list(TEST_DATA_DIR.glob('**/*.sdr'))
    
    if not sdr_files:
        print("  Файлы SDR не найдены!")
        return []
    
    results = []
    
    for sdr_file in sdr_files:
        print(f"\n--- Файл: {sdr_file.name} ---")
        print(f"  Путь: {sdr_file}")
        
        # Показываем первые 10 строк для анализа
        with open(sdr_file, 'r', encoding='cp1251', errors='ignore') as f:
            first_lines = f.readlines()[:10]
            print(f"  Первые строки:")
            for i, line in enumerate(first_lines, 1):
                print(f"    {i}: {line.strip()[:100]}")
        
        parser = SDRParser()
        try:
            result = parser.parse(sdr_file)

            print(f"\n  Результаты парсинга:")
            print(f"    Формат: {result['format']}")
            print(f"    Имя работы: {result.get('job_name', 'N/A')}")
            print(f"    Кодировка: {result.get('encoding', 'N/A')}")
            print(f"    Всего строк: {result.get('total_lines', 0)}")
            print(f"    Измерений: {result.get('num_observations', 0)}")
            print(f"    Пунктов: {result.get('num_points', len(result.get('points', [])))}")
            print(f"    Ошибок: {len(result.get('errors', []))}")
            
            if result['observations']:
                print(f"\n  Первые 5 измерений:")
                try:
                    for i, obs in enumerate(result['observations'][:5], 1):
                        # Для SDR CombinedObservation используем from_point_id и to_point_id
                        from_point = getattr(obs, 'from_point_id', getattr(obs, 'from_point', 'UNKNOWN'))
                        to_point = getattr(obs, 'to_point_id', getattr(obs, 'to_point', 'UNKNOWN'))
                        print(f"    {i}. Тип: {obs.obs_type:20} | От: {from_point:15} | К: {to_point:15} | Значение: {obs.value:.6f}")
                except Exception as e:
                    print(f"    Ошибка при отображении измерений: {e}")
            
            if result['errors']:
                print(f"\n  Первые 5 ошибок:")
                for error in result['errors'][:5]:
                    print(f"    Строка {error.get('line', '?')}: {error.get('message', 'Неизвестная ошибка')}")
            
            stats = parser.get_statistics()
            print(f"\n  Статистика по типам:")
            for obs_type, count in stats['by_type'].items():
                print(f"    {obs_type}: {count}")
            
            results.append({
                'file': str(sdr_file),
                'success': result['success'],
                'num_observations': result.get('num_observations', 0),
                'num_points': len(result.get('points', [])),
                'num_errors': len(result.get('errors', []))
            })

        except Exception as e:
            print(f"  ОШИБКА при парсинге: {e}")
            results.append({
                'file': str(sdr_file),
                'success': False,
                'error': str(e)
            })
    
    return results


def test_dat_parser():
    """Тестирование парсера DAT на реальных файлах"""
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ DAT ПАРСЕРА")
    print("=" * 70)
    
    dat_files = list(TEST_DATA_DIR.glob('**/*.DAT'))
    
    if not dat_files:
        print("  Файлы DAT не найдены!")
        return []
    
    results = []
    
    for dat_file in dat_files:
        print(f"\n--- Файл: {dat_file.name} ---")
        print(f"  Путь: {dat_file}")
        
        # Показываем первые 10 строк для анализа
        with open(dat_file, 'r', encoding='cp1251', errors='ignore') as f:
            first_lines = f.readlines()[:10]
            print(f"  Первые строки:")
            for i, line in enumerate(first_lines, 1):
                print(f"    {i}: {line.strip()[:100]}")
        
        parser = DATParser()
        try:
            result = parser.parse(dat_file)
            
            print(f"\n  Результаты парсинга:")
            print(f"    Формат: {result['format']} версия {result['version']}")
            print(f"    Кодировка: {result['encoding']}")
            print(f"    Всего строк: {result['total_lines']}")
            print(f"    Измерений: {result['num_observations']}")
            print(f"    Пунктов: {result['num_points']}")
            print(f"    Ошибок: {len(result['errors'])}")
            
            if result['observations']:
                print(f"\n  Первые 5 измерений:")
                for i, obs in enumerate(result['observations'][:5], 1):
                    print(f"    {i}. Тип: {obs.obs_type:15} | От: {obs.from_point:15} | К: {obs.to_point:15} | Значение: {obs.value:.6f}")
            
            if result['errors']:
                print(f"\n  Первые 5 ошибок:")
                for error in result['errors'][:5]:
                    print(f"    Строка {error.get('line', '?')}: {error.get('message', 'Неизвестная ошибка')}")
            
            stats = parser.get_statistics()
            print(f"\n  Статистика по типам:")
            for obs_type, count in stats['by_type'].items():
                print(f"    {obs_type}: {count}")
            
            results.append({
                'file': str(dat_file),
                'success': result['success'],
                'num_observations': result['num_observations'],
                'num_points': result['num_points'],
                'num_errors': len(result['errors'])
            })
            
        except Exception as e:
            print(f"  ОШИБКА при парсинге: {e}")
            results.append({
                'file': str(dat_file),
                'success': False,
                'error': str(e)
            })
    
    return results


def print_summary(gsi_results, sdr_results, dat_results):
    """Вывод сводной информации по всем тестам"""
    print("\n" + "=" * 70)
    print("СВОДНАЯ ИНФОРМАЦИЯ ПО ТЕСТИРОВАНИЮ ПАРСЕРОВ")
    print("=" * 70)
    
    all_results = [
        ('GSI', gsi_results),
        ('SDR', sdr_results),
        ('DAT', dat_results)
    ]
    
    total_files = 0
    total_success = 0
    total_observations = 0
    total_points = 0
    total_errors = 0
    
    for format_name, results in all_results:
        print(f"\n--- {format_name} ---")
        if not results:
            print("  Нет результатов")
            continue

        for r in results:
            total_files += 1
            success = r.get('success', False)
            status = "OK" if success else "FAIL"
            if success:
                total_success += 1
                total_observations += r.get('num_observations', 0)
                total_points += r.get('num_points', 0)
            total_errors += r.get('num_errors', 0)

            print(f"  [{status}] {Path(r['file']).name}: "
                  f"измерений={r.get('num_observations', 0)}, "
                  f"пунктов={r.get('num_points', 0)}, "
                  f"ошибок={r.get('num_errors', 0)}")
    
    print(f"\n{'=' * 70}")
    print(f"ИТОГО:")
    print(f"  Файлов обработано: {total_files}")
    print(f"  Успешно: {total_success}")
    print(f"  С ошибками: {total_files - total_success}")
    print(f"  Всего измерений: {total_observations}")
    print(f"  Всего пунктов: {total_points}")
    print(f"  Всего ошибок: {total_errors}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    print("Тестирование парсеров на реальных данных")
    print(f"Директория с данными: {TEST_DATA_DIR}")
    
    if not TEST_DATA_DIR.exists():
        print(f"ОШИБКА: Директория {TEST_DATA_DIR} не существует!")
        sys.exit(1)
    
    gsi_results = test_gsi_parser()
    sdr_results = test_sdr_parser()
    dat_results = test_dat_parser()
    
    print_summary(gsi_results, sdr_results, dat_results)
