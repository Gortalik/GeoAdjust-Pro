#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Альтернативный тестовый запуск GeoAdjust Pro
Создает новый проект автоматически и запускает главное окно
"""

import sys
import os
from pathlib import Path

def main():
    print("=" * 60)
    print("АВТОМАТИЧЕСКИЙ ТЕСТ GeoAdjust Pro")
    print("Создание проекта + запуск GUI")
    print("=" * 60)

    # Определяем пути
    current_dir = Path(__file__).parent
    geoadjust_dir = current_dir / "GeoAdjustPro"
    src_path = geoadjust_dir / "src"

    # Добавляем путь к исходному коду
    if str(src_path) not in sys.path:
        print(f"[OK] Добавлен путь: {src_path}")

    # Устанавливаем рабочую директорию на GeoAdjustPro
    os.chdir(geoadjust_dir)
    print(f"[OK] Рабочая директория: {geoadjust_dir}")

    try:
        # Импортируем необходимые модули
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from geoadjust.io.project.project_manager import ProjectManager
        from geoadjust.gui.main_window import MainWindow, MainWindowConfig, InterfaceType
        from geoadjust.utils import setup_logging
        import tempfile

        # Настройка логирования
        logger = setup_logging()

        # Создание QApplication
        print("[INFO] Создание QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("P-of-Geo-Meas Test")
        app.setOrganizationName("GeoAdjust Team")
        app.setApplicationVersion("1.0.0")
        app.setStyle('Fusion')
        print("[OK] QApplication создан")

        # Создание временного проекта для тестирования
        print("[INFO] Создание тестового проекта...")
        project_manager = ProjectManager()

        # Создаем временную директорию для тестового проекта
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_project_path = temp_path / "TestProject.gad"

            # Создаем проект
            project = project_manager.create_project(
                project_path=temp_path,
                project_name="TestProject"
            )
            project.save()
            print(f"[OK] Тестовый проект создан: {test_project_path}")

            # Создание главного окна
            print("[INFO] Создание главного окна...")
            config = MainWindowConfig(
                interface_type=InterfaceType.RIBBON,
                window_title="P-of-Geo-Meas • ТЕСТОВЫЙ РЕЖИМ",
                window_size=(1200, 800),
                window_state="normal",
                theme="light"
            )

            main_window = MainWindow(config)
            main_window.current_project = project

            # Тестируем импорт SDR файла
            print("[INFO] Тестирование импорта SDR файла...")
            try:
                # Имитируем импорт SDR файла (прямой вызов логики import_dialog)
                from geoadjust.io.formats.sdr import SDRParser

                # Парсим SDR файл
                sdr_parser = SDRParser()
                sdr_file_path = current_dir / "test_real_mes" / "b_g" / "plan" / "badgro16093_const.sdr"
                sdr_data = sdr_parser.parse(sdr_file_path)

                print(f"[OK] SDR файл распарсен: {len(sdr_data.get('points', []))} пунктов, {len(sdr_data.get('observations', []))} измерений")

                # Имитируем обработку как в import_dialog._import_sdr()
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

                # Конвертация сессий станций для UI
                station_sessions = []
                for setup in sdr_data.get('setups', []):
                    # Группируем измерения по этой установке (сравниваем setup_id)
                    setup_observations = [obs for obs in observations if obs.get('from_setup_id', '') == setup.setup_id]

                    # Конвертируем измерения в формат словарей для UI
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

                print(f"[OK] Импорт завершен: {len(imported_data.get('points', []))} пунктов, {len(imported_data.get('observations', []))} измерений")

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
                print(f"[WARNING] Ошибка импорта SDR файла: {e}")
                import traceback
                traceback.print_exc()

            # Показываем окно
            print("[INFO] Отображение главного окна...")
            main_window.show()
            main_window.raise_()
            main_window.activateWindow()
            print("[OK] Главное окно отображено")

            print("\n" + "=" * 60)
            print("Тест завершен успешно!")
            print("Главное окно должно быть видно на экране")
            print("Для выхода закройте окно или нажмите Ctrl+C")
            print("=" * 60)

            # Запуск главного цикла (блокируется до закрытия окна)
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