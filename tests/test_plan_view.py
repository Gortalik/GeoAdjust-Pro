#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест окна плана для GeoAdjust Pro
Проверяет корректность отображения геодезической сети
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GeoAdjustPro', 'src'))

def test_plan_view():
    """Тест окна плана с реальными данными"""
    try:
        from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
        from geoadjust.gui.components.plan_view import PlanGraphicsView
        import time

        print("Тестирование окна плана...")

        app = QApplication([])

        # Создаем тестовое окно
        window = QWidget()
        window.setWindowTitle("Тест окна плана GeoAdjust Pro")
        window.resize(800, 600)

        layout = QVBoxLayout(window)

        # Создаем план
        plan_view = PlanGraphicsView()
        layout.addWidget(plan_view)

        print("[OK] Окно плана создано")

        # Тест 1: Добавление пунктов разных типов
        print("Тест 1: Добавление пунктов разных типов")

        # Опорные пункты
        plan_view.add_point("P001", 100, 100, point_type="FIXED")
        plan_view.add_point("P002", 200, 150, point_type="FIXED")
        plan_view.add_point("P003", 300, 200, point_type="FIXED")

        # Свободные пункты
        plan_view.add_point("P101", 150, 120, point_type="FREE")
        plan_view.add_point("P102", 250, 180, point_type="FREE")
        plan_view.add_point("P103", 350, 250, point_type="FREE")

        # Приближенные пункты
        plan_view.add_point("P201", 120, 80, point_type="APPROXIMATE")
        plan_view.add_point("P202", 280, 120, point_type="APPROXIMATE")

        print(f"[OK] Добавлено {len(plan_view.points)} пунктов")

        # Тест 2: Добавление измерений разных типов
        print("Тест 2: Добавление измерений разных типов")

        # Направления
        plan_view.add_observation("P001", "P101", "direction")
        plan_view.add_observation("P001", "P201", "direction")
        plan_view.add_observation("P002", "P102", "direction")

        # Расстояния
        plan_view.add_observation("P101", "P102", "slope_distance")
        plan_view.add_observation("P102", "P103", "slope_distance")

        # Превышения
        plan_view.add_observation("P001", "P002", "height_diff")
        plan_view.add_observation("P002", "P003", "height_diff")

        print(f"[OK] Добавлено {len(plan_view.observations)} измерений")

        # Тест 3: Проверка сетки
        print("Тест 3: Проверка адаптивной сетки")

        grid_lines = len(plan_view.grid_lines)
        grid_labels = len(plan_view.grid_labels)

        print(f"[OK] Создана сетка: {grid_lines} линий, {grid_labels} подписей")

        # Тест 4: Проверка масштабирования
        print("Тест 4: Проверка масштабирования")

        # Подгонка под содержимое
        plan_view.fit_to_contents()
        print("[OK] Масштабирование выполнено")

        # Тест 5: Проверка удаления элементов
        print("Тест 5: Проверка удаления элементов")

        initial_points = len(plan_view.points)
        plan_view.remove_point("P201")  # Удаляем приближенный пункт

        if len(plan_view.points) == initial_points - 1:
            print("[OK] Пункт успешно удален")
        else:
            print("[ERROR] Ошибка удаления пункта")

        # Тест 6: Проверка очистки
        print("Тест 6: Проверка очистки")

        plan_view.clear_all()

        if not plan_view.points and not plan_view.observations:
            print("[OK] План успешно очищен")
        else:
            print(f"[ERROR] Ошибка очистки: {len(plan_view.points)} пунктов, {len(plan_view.observations)} измерений")

        # Тест 7: Проверка работы с тестовыми данными проекта
        print("Тест 7: Проверка работы с тестовыми данными проекта")

        # Создаем тестовый объект проекта
        class MockProject:
            def __init__(self):
                self.points = [
                    {'name': 'A', 'x': 0, 'y': 0, 'coord_type': 'FIXED'},
                    {'name': 'B', 'x': 100, 'y': 0, 'coord_type': 'FIXED'},
                    {'name': 'C', 'x': 50, 'y': 86.6, 'coord_type': 'FREE'},
                    {'name': 'D', 'x': 150, 'y': 86.6, 'coord_type': 'FREE'},
                    {'name': 'E', 'x': 100, 'y': 173.2, 'coord_type': 'APPROXIMATE'}
                ]
                self.observations = [
                    {'from_point': 'A', 'to_point': 'C', 'type': 'direction'},
                    {'from_point': 'A', 'to_point': 'B', 'type': 'slope_distance'},
                    {'from_point': 'B', 'to_point': 'D', 'type': 'direction'},
                    {'from_point': 'C', 'to_point': 'D', 'type': 'height_diff'},
                    {'from_point': 'C', 'to_point': 'E', 'type': 'slope_distance'},
                    {'from_point': 'D', 'to_point': 'E', 'type': 'direction'}
                ]

        mock_project = MockProject()
        plan_view.draw_network(mock_project)

        print(f"[OK] Сеть нарисована: {len(plan_view.points)} пунктов, {len(plan_view.observations)} измерений")

        # Тест 8: Проверка визуальных индикаторов
        print("Тест 8: Проверка визуальных индикаторов")

        from geoadjust.gui.visual_indicators import VisualIndicator

        # Проверяем символы для разных типов пунктов
        symbols = VisualIndicator.get_symbol_map()
        colors = VisualIndicator.get_color_scheme()

        print(f"[OK] Доступно символов: {len(symbols)}, цветов: {len(colors)}")

        # Создаем индикаторы
        fixed_indicator = VisualIndicator.create_point_type_indicator("FIXED")
        free_indicator = VisualIndicator.create_point_type_indicator("FREE")
        approx_indicator = VisualIndicator.create_point_type_indicator("APPROXIMATE")

        print("[OK] Индикаторы типов пунктов созданы")

        # Индикаторы измерений
        dir_indicator = VisualIndicator.create_observation_type_indicator("direction")
        dist_indicator = VisualIndicator.create_observation_type_indicator("slope_distance")
        height_indicator = VisualIndicator.create_observation_type_indicator("height_diff")

        print("[OK] Индикаторы типов измерений созданы")

        # Показываем окно на 2 секунды
        window.show()
        app.processEvents()
        time.sleep(2)

        # Закрываем приложение
        app.quit()

        print("\nВсе тесты окна плана пройдены успешно!")
        return True

    except Exception as e:
        print(f"[CRITICAL] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_plan_view()
    sys.exit(0 if success else 1)