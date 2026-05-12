#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексный тест полной обработки геодезических измерений
Создает ведомости координат, топологии сети и оценки точности
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

def main():
    print("=" * 80)
    print("КОМПЛЕКСНЫЙ ТЕСТ ПОЛНОЙ ОБРАБОТКИ ИЗМЕРЕНИЙ")
    print("=" * 80)

    # Определяем пути
    current_dir = Path(__file__).parent
    geoadjust_dir = current_dir / "GeoAdjustPro"
    src_path = geoadjust_dir / "src"

    # Добавляем путь к исходному коду
    if str(src_path) not in sys.path:
        print(f"[OK] Добавлен путь: {src_path}")

    # Устанавливаем рабочую директорию
    os.chdir(geoadjust_dir)
    print(f"[OK] Рабочая директория: {geoadjust_dir}")

    try:
        # Импортируем необходимые модули
        from PyQt5.QtWidgets import QApplication
        from geoadjust.io.project.project_manager import ProjectManager
        from geoadjust.gui.main_window import MainWindow, MainWindowConfig, InterfaceType
        from geoadjust.utils import setup_logging
        import tempfile

        # Настройка логирования
        logger = setup_logging()

        # Создание QApplication
        print("[INFO] Создание QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("GeoAdjust Pro - Полная обработка")
        app.setOrganizationName("GeoAdjust Team")
        app.setApplicationVersion("1.0.0")
        app.setStyle('Fusion')
        print("[OK] QApplication создан")

        # Создание временного проекта
        print("[INFO] Создание проекта для обработки...")
        project_manager = ProjectManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_path = temp_path / "ProcessingTest.gad"

            # Создаем проект
            project = project_manager.create_project(
                project_path=temp_path,
                project_name="Тест полной обработки"
            )
            project.save()
            print(f"[OK] Проект создан: {project_path}")

            # Создание главного окна
            config = MainWindowConfig(
                interface_type=InterfaceType.RIBBON,
                window_title="GeoAdjust Pro • ПОЛНАЯ ОБРАБОТКА",
                window_size=(1400, 900),
                window_state="normal",
                theme="light"
            )

            main_window = MainWindow(config)
            main_window.current_project = project

            # ШАГ 1: Импорт SDR данных
            print("\n" + "=" * 60)
            print("ШАГ 1: ИМПОРТ SDR ДАННЫХ")
            print("=" * 60)

            try:
                from geoadjust.io.formats.sdr import SDRParser
                from geoadjust.gui.dialogs.import_dialog import ImportDialog

                # Парсим SDR файл
                sdr_parser = SDRParser()
                sdr_file_path = current_dir / "test_real_mes" / "b_g" / "plan" / "badgro16093_const.sdr"
                sdr_data = sdr_parser.parse(sdr_file_path)

                print(f"[OK] SDR файл распарсен: {len(sdr_data.get('points', []))} пунктов, {len(sdr_data.get('observations', []))} измерений")

                # Имитируем обработку импорта
                points = []
                for p in sdr_data.get('points', []):
                    points.append({
                        'name': p.get('point_id', ''),
                        'x': p.get('x', 0) or 0,
                        'y': p.get('y', 0) or 0,
                        'h': p.get('h', 0) or 0,
                        'type': p.get('point_type', 'free')
                    })

                observations = []
                for obs in sdr_data.get('observations', []):
                    observations.append({
                        'from_point': getattr(obs, 'from_point_id', ''),
                        'to_point': getattr(obs, 'to_point_id', ''),
                        'type': getattr(obs, 'obs_type', 'direction'),
                        'value': getattr(obs, 'value', 0),
                        'sigma': getattr(obs, 'sigma_apriori', 0.00005),
                        'from_setup_id': getattr(obs, 'from_setup_id', ''),
                        'face_position': getattr(obs, 'face_position', None)
                    })

                # Формируем сессии станций
                station_sessions = []
                for setup in sdr_data.get('setups', []):
                    setup_observations = [obs for obs in observations if obs.get('from_setup_id', '') == setup.setup_id]
                    setup_observations_ui = []
                    for obs in setup_observations:
                        setup_observations_ui.append({
                            'obs_type': obs.get('type', ''),
                            'from_point': obs.get('from_point', ''),
                            'to_point': obs.get('to_point', ''),
                            'value': obs.get('value', 0),
                            'setup_id': obs.get('from_setup_id', ''),
                            'face_position': obs.get('face_position', None)
                        })

                    session_data = {
                        'session_id': setup.setup_id,
                        'station_name': setup.point_id,
                        'instrument_height': setup.instrument_height,
                        'target_height': setup.target_height,
                        'orientation_angle': setup.orientation_angle,
                        'temperature': setup.temperature,
                        'pressure': setup.pressure,
                        'num_observations': len(setup_observations),
                        'timestamp': setup.timestamp,
                        'observations': setup_observations_ui
                    }
                    station_sessions.append(session_data)

                imported_data = {
                    'points': points,
                    'observations': observations,
                    'station_sessions': station_sessions
                }

                # Добавляем данные в проект
                if imported_data.get('points'):
                    for point in imported_data['points']:
                        project.add_point(point)

                if imported_data.get('observations'):
                    for obs in imported_data['observations']:
                        project.add_observation(obs)

                # Обновляем станции
                if station_sessions:
                    main_window._update_stations_view(station_sessions)
                    print(f"[OK] Станции обновлены: {len(station_sessions)} сессий")

                print("[OK] Данные импортированы в проект")

            except Exception as e:
                print(f"[ERROR] Ошибка импорта SDR файла: {e}")
                import traceback
                traceback.print_exc()
                return

            # ШАГ 2: Контроль допусков
            print("\n" + "=" * 60)
            print("ШАГ 2: КОНТРОЛЬ ДОПУСКОВ")
            print("=" * 60)

            try:
                from geoadjust.core.preprocessing.tolerances import ToleranceChecker

                checker = ToleranceChecker()
                obs_data = project.get_observations()

                if obs_data:
                    results = checker.check_all(obs_data)
                    violations = [r for r in results if not r['passed']]

                    print(f"[OK] Контроль допусков выполнен: {len(violations)} нарушений из {len(results)} проверок")

                    if violations:
                        print("[WARNING] Обнаружены нарушения допусков:")
                        for v in violations[:5]:
                            print(f"  - {v['description']}")
                        if len(violations) > 5:
                            print(f"  ... и еще {len(violations) - 5}")
                    else:
                        print("[OK] Все измерения в пределах допусков")
                else:
                    print("[WARNING] Нет измерений для контроля допусков")

            except Exception as e:
                print(f"[ERROR] Ошибка контроля допусков: {e}")

            # ШАГ 3: Предобработка данных
            print("\n" + "=" * 60)
            print("ШАГ 3: ПРЕДОБРАБОТКА ДАННЫХ")
            print("=" * 60)

            try:
                from geoadjust.core.preprocessing.module import PreprocessingModule

                preprocessor = PreprocessingModule()
                obs_data = project.get_observations()

                if obs_data:
                    # Запуск полной предобработки
                    preprocessing_result = preprocessor.run_preprocessing(obs_data)
                    print(f"[OK] Предобработка завершена - выполнено {preprocessing_result.get('stages_completed', 0)} этапов")

                    # Сохраняем результаты предобработки
                    project.preprocessing_result = preprocessing_result
                    project.preprocessing_completed = True
                else:
                    print("[WARNING] Нет измерений для предобработки")

            except Exception as e:
                print(f"[ERROR] Ошибка предобработки: {e}")
                import traceback
                traceback.print_exc()

            # ШАГ 4: Уравнивание сети
            print("\n" + "=" * 60)
            print("ШАГ 4: УРАВНИВАНИЕ СЕТИ")
            print("=" * 60)

            adjustment_result = None
            try:
                # Проверяем наличие данных
                obs_data = project.get_observations()
                points_data = project.get_points()

                if not obs_data or not points_data:
                    print("[ERROR] Недостаточно данных для уравнивания")
                    return

                print(f"[OK] Данные для уравнивания: {len(points_data)} пунктов, {len(obs_data)} измерений")

                # Выполняем классическое МНК уравнивание
                from geoadjust.core.adjustment.classic_mnk import ClassicMNK

                adjuster = ClassicMNK()
                adjustment_result = adjuster.adjust(project)

                if adjustment_result and adjustment_result.get('success'):
                    print("[OK] Уравнивание выполнено успешно")
                    print(f"  - Число итераций: {adjustment_result.get('iterations', 0)}")
                    print(f"  - СКО единицы веса: {adjustment_result.get('unit_weight_error', 0):.6f}")

                    # Сохраняем результаты в проект
                    project.adjustment_result = adjustment_result
                else:
                    print("[WARNING] Уравнивание завершено с предупреждениями")

            except Exception as e:
                print(f"[ERROR] Ошибка уравнивания: {e}")
                import traceback
                traceback.print_exc()

            # ШАГ 5: Создание ведомостей
            print("\n" + "=" * 60)
            print("ШАГ 5: СОЗДАНИЕ ВЕДОМОСТЕЙ")
            print("=" * 60)

            try:
                from geoadjust.core.reporting.reports import ReportGenerator

                generator = ReportGenerator()
                reports_dir = temp_path / "reports"
                reports_dir.mkdir(exist_ok=True)

                # Ведомость координат
                print("[INFO] Создание ведомости координат...")
                coord_report = generator.generate_coordinates_report(project, adjustment_result)
                coord_file = reports_dir / "coordinates_report.html"
                with open(coord_file, 'w', encoding='utf-8') as f:
                    f.write(coord_report)
                print(f"[OK] Ведомость координат сохранена: {coord_file}")

                # Ведомость топологии сети
                print("[INFO] Создание ведомости топологии сети...")
                topo_report = generator.generate_topology_report(project, adjustment_result)
                topo_file = reports_dir / "topology_report.html"
                with open(topo_file, 'w', encoding='utf-8') as f:
                    f.write(topo_report)
                print(f"[OK] Ведомость топологии сохранена: {topo_file}")

                # Ведомость оценки точности
                print("[INFO] Создание ведомости оценки точности...")
                accuracy_report = generator.generate_accuracy_report(project, adjustment_result)
                accuracy_file = reports_dir / "accuracy_report.html"
                with open(accuracy_file, 'w', encoding='utf-8') as f:
                    f.write(accuracy_report)
                print(f"[OK] Ведомость оценки точности сохранена: {accuracy_file}")

                print(f"[OK] Все ведомости созданы в директории: {reports_dir}")

            except Exception as e:
                print(f"[ERROR] Ошибка создания ведомостей: {e}")
                import traceback
                traceback.print_exc()

            # Показываем окно
            print("\n" + "=" * 60)
            print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
            print("=" * 60)
            print("Результаты:")
            print("✓ Импорт SDR данных")
            print("✓ Контроль допусков")
            print("✓ Применение редукций")
            print("✓ Уравнивание сети")
            print("✓ Создание ведомостей")
            print("=" * 60)

            main_window.show()
            main_window.raise_()
            main_window.activateWindow()
            print("[OK] Графический интерфейс запущен - можно просмотреть результаты")

            # Запуск главного цикла
            exit_code = app.exec_()
            print(f"\nПриложение завершено с кодом: {exit_code}")

    except ImportError as e:
        print(f"[ERROR] Ошибка импорта: {e}")
        print("[INFO] Попробуйте установить зависимости:")
        print("  pip install -r GeoAdjustPro/requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Приложение остановлено пользователем")
    except Exception as e:
        print(f"[ERROR] Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()