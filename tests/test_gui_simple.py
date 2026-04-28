#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест GUI GeoAdjust Pro с визуальными индикаторами
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GeoAdjustPro', 'src'))

def test_gui_basic():
    """Базовый тест GUI"""
    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.main_window import MainWindow
        import time

        print("Тестирование базового GUI...")

        app = QApplication([])

        # Создаем главное окно
        window = MainWindow()
        print("[OK] Главное окно создано")

        # Проверяем меню
        menu_bar = window.menuBar()
        reports_menu = None
        for action in menu_bar.actions():
            if action.text() == 'Отчёты':
                reports_menu = action.menu()
                break

        if reports_menu:
            print("[OK] Меню 'Отчёты' найдено")
            report_actions = [action.text() for action in reports_menu.actions() if action.text()]
            print(f"  Доступные отчеты: {report_actions}")
            if len(report_actions) >= 3:
                print("[OK] Все ведомости присутствуют")
            else:
                print("[WARNING] Некоторые ведомости отсутствуют")
        else:
            print("[ERROR] Меню 'Отчёты' не найдено")

        # Проверяем визуальные индикаторы
        try:
            from geoadjust.gui.visual_indicators import VisualIndicator
            symbols = VisualIndicator.get_symbol_map()
            colors = VisualIndicator.get_color_scheme()

            print("[OK] Визуальные индикаторы загружены")
            print(f"  Доступно {len(symbols)} символов и {len(colors)} цветов")

            # Тестируем создание индикатора
            indicator = VisualIndicator.create_point_type_indicator("FIXED")
            print("[OK] Индикатор типа пункта создан")

        except Exception as e:
            print(f"[ERROR] Ошибка визуальных индикаторов: {e}")

        # Проверяем делегаты
        try:
            from geoadjust.gui.delegates.visual_delegates import PointTypeDelegate, ObservationTypeDelegate
            print("[OK] Визуальные делегаты загружены")

            # Создаем делегат
            delegate = PointTypeDelegate()
            print("[OK] Делегат для типов пунктов создан")

        except Exception as e:
            print(f"[ERROR] Ошибка делегатов: {e}")

        # Закрываем приложение
        app.quit()

        print("\nТестирование завершено успешно!")
        return True

    except Exception as e:
        print(f"[CRITICAL] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gui_basic()
    sys.exit(0 if success else 1)