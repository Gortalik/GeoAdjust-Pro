#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoAdjust Pro - Рабочий прототип геодезической программы
Полностью функциональная версия для демонстрации
"""

import sys
import os

# GeoAdjustPro folder not available, using working prototype

def create_demo_project():
    """Создание демонстрационного проекта"""
    from geoadjust.io.project.project_manager import ProjectManager
    from pathlib import Path
    import tempfile

    pm = ProjectManager()

    # Создаем временную директорию для проекта
    temp_dir = Path(tempfile.mkdtemp())
    project = pm.create_project(temp_dir, "Демонстрационный проект GeoAdjust Pro")

    # Добавляем тестовые данные
    test_points = [
        {'name': 'P001', 'x': 1000.000, 'y': 2000.000, 'coord_type': 'FIXED'},
        {'name': 'P002', 'x': 1100.000, 'y': 2000.000, 'coord_type': 'FIXED'},
        {'name': 'P003', 'x': 1050.000, 'y': 2086.602, 'coord_type': 'FREE'},
        {'name': 'P004', 'x': 1150.000, 'y': 2086.602, 'coord_type': 'FREE'},
        {'name': 'P005', 'x': 1100.000, 'y': 2173.205, 'coord_type': 'APPROXIMATE'}
    ]

    test_observations = [
        # Направления
        {'from_point': 'P001', 'to_point': 'P003', 'type': 'direction', 'value': 45.0},
        {'from_point': 'P001', 'to_point': 'P002', 'type': 'direction', 'value': 0.0},
        {'from_point': 'P002', 'to_point': 'P004', 'type': 'direction', 'value': 45.0},

        # Расстояния
        {'from_point': 'P001', 'to_point': 'P002', 'type': 'slope_distance', 'value': 100.0},
        {'from_point': 'P002', 'to_point': 'P004', 'type': 'slope_distance', 'value': 86.602},
        {'from_point': 'P003', 'to_point': 'P004', 'type': 'slope_distance', 'value': 100.0},

        # Зенитные углы
        {'from_point': 'P001', 'to_point': 'P003', 'type': 'zenith_angle', 'value': 90.0},
        {'from_point': 'P002', 'to_point': 'P004', 'type': 'zenith_angle', 'value': 90.0},

        # Превышения
        {'from_point': 'P003', 'to_point': 'P004', 'type': 'height_diff', 'value': 0.0},
        {'from_point': 'P004', 'to_point': 'P005', 'type': 'height_diff', 'value': 2.5}
    ]

    if hasattr(project, 'data'):
        project.data['points'] = test_points
        project.data['observations'] = test_observations

    return project

def run_prototype():
    """Запуск рабочего прототипа"""
    print("=" * 80)
    print("GeoAdjust Pro - Рабочий прототип")
    print("=" * 80)
    print()
    print("Возможности прототипа:")
    print("[+] Создание и управление геодезическими проектами")
    print("[+] Импорт данных из SDR файлов")
    print("[+] Визуальное отображение сети на плане")
    print("[+] Таблицы пунктов и измерений с визуальными индикаторами")
    print("[+] Предобработка данных (9 этапов)")
    print("[+] Уравнивание сети методом МНК")
    print("[+] Создание ведомостей (координаты, топология, точность)")
    print("[+] Экспорт результатов")
    print()
    print("Управление:")
    print("• Файл -> Новый проект - создать проект")
    print("• Данные -> Импорт из файла - загрузить SDR данные")
    print("• Вид - переключение между таблицами и планом")
    print("• Обработка - предобработка и уравнивание")
    print("• Отчёты - создание ведомостей")
    print()

    try:
        # Импорт необходимых модулей
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.main_window import MainWindow

        # Создание приложения
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

        # Создание главного окна
        main_window = MainWindow()

        # Создание демонстрационного проекта
        print("Создание демонстрационного проекта...")
        demo_project = create_demo_project()
        main_window.current_project = demo_project

        # Отрисовка демонстрационной сети на плане
        if hasattr(main_window, 'plan_view') and main_window.plan_view:
            plan_view = main_window.plan_view
            plan_view.draw_network(demo_project)
            print("[+] Сеть нарисована на плане")

        # Обновление интерфейса
        main_window.setWindowTitle("GeoAdjust Pro - Рабочий прототип")
        main_window.show()

        print("\n" + "=" * 80)
        print("ПРОТОТИП ЗАПУЩЕН!")
        print("Закройте окно приложения для выхода.")
        print("=" * 80)

        # Запуск главного цикла
        sys.exit(app.exec_())

    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что все зависимости установлены.")
        return False

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_prototype()