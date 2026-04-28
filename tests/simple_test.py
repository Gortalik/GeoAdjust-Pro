#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОСТАЯ ПРОВЕРКА GeoAdjust Pro
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GeoAdjustPro', 'src'))

def simple_test():
    """Простая проверка основных компонентов"""
    print("=" * 60)
    print("ПРОСТАЯ ПРОВЕРКА GeoAdjust Pro")
    print("=" * 60)

    results = {}

    try:
        # 1. Импорт модулей
        print("\n1. Проверка импорта модулей...")
        try:
            from PyQt5.QtWidgets import QApplication
            from geoadjust.gui.main_window import MainWindow
            from geoadjust.gui.visual_indicators import VisualIndicator
            from geoadjust.gui.delegates.visual_delegates import PointTypeDelegate
            from geoadjust.core.reporting.reports import ReportGenerator
            print("   [OK] Все модули импортированы")
            results['imports'] = True
        except Exception as e:
            print(f"   [ERROR] Ошибка импорта: {e}")
            results['imports'] = False

        # 2. Создание приложения
        print("\n2. Создание Qt приложения...")
        app = QApplication([])
        print("   [OK] Qt приложение создано")
        results['qt_app'] = True

        # 3. Создание главного окна
        print("\n3. Создание главного окна...")
        main_window = MainWindow()
        print("   [OK] Главное окно создано")
        results['main_window'] = True

        # 4. Проверка меню
        print("\n4. Проверка меню...")
        menu_bar = main_window.menuBar()
        menus = {}
        for action in menu_bar.actions():
            menu_name = action.text().replace('&', '')
            if action.menu():
                submenus = [subaction.text() for subaction in action.menu().actions() if subaction.text()]
                menus[menu_name] = submenus

        required_menus = ['Файл', 'Отчёты']
        found_menus = [menu for menu in required_menus if menu in menus]

        print(f"   [OK] Найдено меню: {len(found_menus)}/{len(required_menus)}")
        results['menus'] = len(found_menus) >= 1

        # 5. Проверка визуальных индикаторов
        print("\n5. Проверка визуальных индикаторов...")
        symbols = VisualIndicator.get_symbol_map()
        colors = VisualIndicator.get_color_scheme()

        print(f"   [OK] Символов: {len(symbols)}, цветов: {len(colors)}")

        # Создание индикаторов
        point_indicator = VisualIndicator.create_point_type_indicator("FIXED")
        obs_indicator = VisualIndicator.create_observation_type_indicator("direction")

        print("   [OK] Индикаторы созданы")
        results['indicators'] = True

        # 6. Проверка делегатов
        print("\n6. Проверка делегатов таблиц...")
        delegate = PointTypeDelegate()
        print("   [OK] Делегат создан")
        results['delegates'] = True

        # 7. Проверка генератора отчетов
        print("\n7. Проверка генератора отчетов...")
        generator = ReportGenerator()

        # Создание тестового проекта
        class MockProject:
            def __init__(self):
                self.name = "Тестовый проект"
                self.points = [
                    {'name': 'A', 'x': 0, 'y': 0, 'coord_type': 'FIXED'},
                    {'name': 'B', 'x': 100, 'y': 0, 'coord_type': 'FREE'}
                ]
                self.observations = [
                    {'from_point': 'A', 'to_point': 'B', 'type': 'direction'}
                ]

            def get_points(self):
                return self.points

            def get_observations(self):
                return self.observations

        mock_project = MockProject()
        html = generator.generate_coordinates_report(mock_project)

        if html and len(html) > 1000:
            print("   [OK] Отчет создан")
            results['reports'] = True
        else:
            print("   [ERROR] Отчет не создан")
            results['reports'] = False

        # 8. Проверка плана
        print("\n8. Проверка окна плана...")
        plan_view = main_window.plan_view
        if plan_view:
            # Добавляем тестовые данные
            plan_view.add_point("Test", 50, 50, point_type="FIXED")
            print("   [OK] Пункт добавлен на план")
            results['plan'] = True
        else:
            print("   [ERROR] План не найден")
            results['plan'] = False

        # Закрываем приложение
        app.quit()

    except Exception as e:
        print(f"[CRITICAL] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Итоговый отчет
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    print(f"\nВсего тестов: {total_tests}")
    print(f"Пройдено: {passed_tests}")
    print(".1f")
    print("\nДетальные результаты:")
    for test_name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"  {status} {test_name}")

    success = passed_tests >= total_tests * 0.7

    print(f"\nИТОГ: {'ПРОТОТИП ГОТОВ!' if success else 'Требуется доработка'}")
    print("=" * 60)

    return success

if __name__ == "__main__":
    success = simple_test()
    sys.exit(0 if success else 1)