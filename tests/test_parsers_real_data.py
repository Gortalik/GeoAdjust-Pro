#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование всех парсеров на реальных данных из test_real_mes
"""

import sys
import os
from pathlib import Path
from collections import defaultdict
from pathlib import Path as PathLibPath

def main():
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ПАРСЕРОВ НА РЕАЛЬНЫХ ДАННЫХ")
    print("Директория: test_real_mes")
    print("=" * 80)

    # Определяем пути
    current_dir = Path(__file__).parent
    test_dir = current_dir.parent / "test_real_mes"

    try:
        # Импортируем парсеры
        from geoadjust.io.formats.gsi import GSIParser
        from geoadjust.io.formats.sdr import SDRParser
        from geoadjust.io.formats.dat import DATParser

        # Создаем парсеры
        parsers = {
            'GSI': GSIParser(),
            'SDR': SDRParser(),
            'DAT': DATParser(),
        }

        # Расширения файлов для каждого парсера
        extensions = {
            'GSI': ['.gsi', '.GSI'],
            'SDR': ['.sdr', '.SDR'],
            'DAT': ['.dat', '.DAT'],
        }

        # Находим все файлы данных
        data_files = []
        for ext_list in extensions.values():
            for ext in ext_list:
                data_files.extend(list(test_dir.rglob(f"*{ext}")))

        print(f"Найдено файлов данных: {len(data_files)}")
        print()

        # Группируем файлы по парсерам
        files_by_parser = defaultdict(list)
        for file_path in data_files:
            for parser_name, ext_list in extensions.items():
                if file_path.suffix.upper() in [ext.upper() for ext in ext_list]:
                    files_by_parser[parser_name].append(file_path)
                    break

        # Тестируем каждый парсер
        results = {}
        debug_keys = set()

        for parser_name, files in files_by_parser.items():
            print(f"{'='*20} ТЕСТИРОВАНИЕ {parser_name} ПАРСЕРА {'='*20}")
            print(f"Файлов для тестирования: {len(files)}")
            print()

            parser = parsers[parser_name]
            parser_results = []

            for i, file_path in enumerate(files, 1):
                print(f"[{i}/{len(files)}] Тестирование: {file_path.name}")
                print(f"    Путь: {file_path}")

                try:
                    # Парсим файл
                    data = parser.parse(PathLibPath(file_path))

                    # Подсчитываем результаты
                    points_count = len(data.get('points', []))
                    observations_count = len(data.get('observations', []))

                    print(f"    Результат: {points_count} пунктов, {observations_count} измерений")

                    # Выводим ключи для отладки (только для первого файла каждого типа)
                    if 'debug_keys' not in locals():
                        debug_keys = set()
                    if str(file_path) not in debug_keys:
                        print(f"    Ключи в результате: {list(data.keys())}")
                        debug_keys.add(str(file_path))

                    parser_results.append({
                        'file': file_path,
                        'success': True,
                        'points': points_count,
                        'observations': observations_count,
                        'error': None
                    })

                except Exception as e:
                    print(f"    ОШИБКА: {str(e)}")
                    parser_results.append({
                        'file': file_path,
                        'success': False,
                        'points': 0,
                        'observations': 0,
                        'error': str(e)
                    })

                print()

            results[parser_name] = parser_results

        # Выводим сводку результатов
        print("=" * 80)
        print("СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        print("=" * 80)

        total_files = 0
        total_success = 0
        total_points = 0
        total_observations = 0

        for parser_name, parser_results in results.items():
            success_count = sum(1 for r in parser_results if r['success'])
            total_files += len(parser_results)
            total_success += success_count
            total_points += sum(r['points'] for r in parser_results)
            total_observations += sum(r['observations'] for r in parser_results)

            print(f"{parser_name} парсер:")
            print(f"  Файлов: {len(parser_results)}")
            print(f"  Успешно: {success_count}")
            print(f"  Ошибок: {len(parser_results) - success_count}")
            print(f"  Всего пунктов: {sum(r['points'] for r in parser_results)}")
            print(f"  Всего измерений: {sum(r['observations'] for r in parser_results)}")
            print()

        print(f"ОБЩИЙ ИТОГ:")
        print(f"  Всего файлов: {total_files}")
        print(f"  Успешно обработано: {total_success}")
        print(f"  Ошибок: {total_files - total_success}")
        print(f"  Процент успеха: {(total_success/total_files*100):.1f}%" if total_files > 0 else "0%")
        print(f"  Всего извлечено пунктов: {total_points}")
        print(f"  Всего извлечено измерений: {total_observations}")

        # Детальный отчет об ошибках
        if total_files > total_success:
            print("\n" + "=" * 80)
            print("ОТЧЕТ ОБ ОШИБКАХ")
            print("=" * 80)

            for parser_name, parser_results in results.items():
                errors = [r for r in parser_results if not r['success']]
                if errors:
                    print(f"\n{parser_name} парсер - ошибки:")
                    for error in errors:
                        print(f"  {error['file'].name}: {error['error']}")

    except ImportError as e:
        print(f"[ERROR] Ошибка импорта: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()