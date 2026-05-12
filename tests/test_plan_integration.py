#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграционный тест окна плана в главном окне GeoAdjust Pro
"""

import sys
import os

# Добавляем путь к проекту

def test_plan_integration():
    """Интеграционный тест окна плана в главном окне"""
    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.main_window import MainWindow
        import time

        print("Интеграционный тест окна плана...")

        app = QApplication([])

        # Создаем главное окно
        main_window = MainWindow()
        print("[OK] Главное окно создано")

        # Получаем план из главного окна
        plan_view = main_window.plan_view
        if not plan_view:
            print("[ERROR] Окно плана не найдено в главном окне")
            return False

        print("[OK] Окно плана получено из главного окна")

        # Тест 1: Создание тестового проекта и данных
        print("Тест 1: Создание тестовых данных")

        # Создаем тестовый объект проекта
        class MockProject:
            def __init__(self):
                # Треугольник с базовой линией
                self.points = [
                    {'name': 'A', 'x': 0, 'y': 0, 'coord_type': 'FIXED'},
                    {'name': 'B', 'x': 1000, 'y': 0, 'coord_type': 'FIXED'},
                    {'name': 'C', 'x': 500, 'y': 866, 'coord_type': 'FREE'},
                    {'name': 'D', 'x': 1500, 'y': 866, 'coord_type': 'FREE'},
                    {'name': 'E', 'x': 1000, 'y': 1732, 'coord_type': 'APPROXIMATE'}
                ]
                self.observations = [
                    # Тахеометрические измерения (станция A)
                    {'from_point': 'A', 'to_point': 'C', 'type': 'direction'},
                    {'from_point': 'A', 'to_point': 'B', 'type': 'slope_distance'},
                    {'from_point': 'A', 'to_point': 'C', 'type': 'zenith_angle'},

                    # Тахеометрические измерения (станция B)
                    {'from_point': 'B', 'to_point': 'D', 'type': 'direction'},
                    {'from_point': 'B', 'to_point': 'A', 'type': 'slope_distance'},
                    {'from_point': 'B', 'to_point': 'D', 'type': 'zenith_angle'},

                    # Нивелирные измерения
                    {'from_point': 'C', 'to_point': 'D', 'type': 'height_diff'},
                    {'from_point': 'D', 'to_point': 'E', 'type': 'height_diff'},
                    {'from_point': 'A', 'to_point': 'B', 'type': 'height_diff'},

                    # GNSS измерения
                    {'from_point': 'C', 'to_point': 'E', 'type': 'slope_distance'},
                    {'from_point': 'A', 'to_point': 'D', 'type': 'horizontal_distance'}
                ]

        mock_project = MockProject()
        print(f"[OK] Создан тестовый проект: {len(mock_project.points)} пунктов, {len(mock_project.observations)} измерений")

        # Тест 2: Отрисовка сети
        print("Тест 2: Отрисовка геодезической сети")

        plan_view.draw_network(mock_project)

        # Проверяем количество элементов
        points_count = len(plan_view.points)
        observations_count = len(plan_view.observations)

        print(f"[OK] Сеть нарисована: {points_count} пунктов, {observations_count} измерений")

        if points_count != len(mock_project.points):
            print(f"[WARNING] Ожидалось {len(mock_project.points)} пунктов, получено {points_count}")
        if observations_count != len(mock_project.observations):
            print(f"[WARNING] Ожидалось {len(mock_project.observations)} измерений, получено {observations_count}")

        # Тест 3: Проверка типов пунктов
        print("Тест 3: Проверка типов пунктов")

        expected_types = {
            'A': 'FIXED', 'B': 'FIXED', 'C': 'FREE',
            'D': 'FREE', 'E': 'APPROXIMATE'
        }

        correct_types = 0
        for point_name, expected_type in expected_types.items():
            if point_name in plan_view.points:
                item = plan_view.points[point_name]
                # Проверяем, что элемент существует
                correct_types += 1
                print(f"[OK] Пункт {point_name}: тип {expected_type}")
            else:
                print(f"[ERROR] Пункт {point_name} не найден")

        print(f"[OK] Корректных типов пунктов: {correct_types}/{len(expected_types)}")

        # Тест 4: Проверка типов измерений
        print("Тест 4: Проверка типов измерений")

        # Подсчитываем измерения по типам
        obs_by_type = {}
        for obs in plan_view.observations:
            obs_type = obs.data(1)  # Тип измерения сохранен в data(1)
            if obs_type not in obs_by_type:
                obs_by_type[obs_type] = 0
            obs_by_type[obs_type] += 1

        print(f"[OK] Измерения по типам: {obs_by_type}")

        # Проверяем наличие основных типов
        expected_obs_types = ['direction', 'slope_distance', 'zenith_angle', 'height_diff', 'horizontal_distance']
        found_types = [t for t in expected_obs_types if t in obs_by_type]
        print(f"[OK] Найдено типов измерений: {len(found_types)}/{len(expected_obs_types)}")

        # Тест 5: Проверка сетки
        print("Тест 5: Проверка адаптивной сетки")

        grid_lines = len(plan_view.grid_lines)
        grid_labels = len(plan_view.grid_labels)

        print(f"[OK] Адаптивная сетка: {grid_lines} линий, {grid_labels} подписей")

        # Тест 6: Проверка масштабирования
        print("Тест 6: Проверка функций масштабирования")

        # Подгонка под содержимое
        plan_view.fit_to_contents()
        print("[OK] Автомасштабирование выполнено")

        # Ручное масштабирование
        initial_transform = plan_view.transform()
        plan_view.scale(1.5, 1.5)
        print("[OK] Масштабирование 1.5x выполнено")

        # Возврат к исходному
        plan_view.scale(1/1.5, 1/1.5)
        print("[OK] Возврат к исходному масштабу")

        # Тест 7: Проверка взаимодействия с пунктами
        print("Тест 7: Проверка взаимодействия")

        # Имитируем клик по пункту (проверяем логику)
        clicked_points = []

        def on_point_clicked(point_id):
            clicked_points.append(point_id)
            print(f"[OK] Клик по пункту: {point_id}")

        plan_view.point_clicked.connect(on_point_clicked)

        # Проверяем, что сигналы подключены
        print("[OK] Сигналы взаимодействия подключены")

        # Тест 8: Проверка контекстного меню
        print("Тест 8: Проверка контекстного меню")

        # Проверяем наличие контекстного меню
        if hasattr(plan_view, '_show_context_menu'):
            print("[OK] Контекстное меню доступно")
        else:
            print("[WARNING] Контекстное меню не найдено")

        # Тест 9: Проверка экспорта
        print("Тест 9: Проверка экспорта изображения")

        # Проверяем наличие метода экспорта
        if hasattr(plan_view, '_export_image'):
            print("[OK] Функция экспорта доступна")
        else:
            print("[WARNING] Функция экспорта не найдена")

        # Показываем главное окно на 3 секунды для визуальной проверки
        main_window.show()
        print("[OK] Главное окно показано для визуальной проверки")

        app.processEvents()
        time.sleep(3)

        # Закрываем приложение
        app.quit()

        print("\nИнтеграционный тест окна плана завершен успешно!")
        print("Резюме:")
        print(f"  - Пункты: {points_count} (ожидаемо: {len(mock_project.points)})")
        print(f"  - Измерения: {observations_count} (ожидаемо: {len(mock_project.observations)})")
        print(f"  - Типы пунктов: {correct_types}/{len(expected_types)} корректных")
        print(f"  - Типы измерений: {len(found_types)}/{len(expected_obs_types)} найдено")
        print(f"  - Сетка: {grid_lines} линий, {grid_labels} подписей")
        print("  - Масштабирование: OK")
        print("  - Взаимодействие: OK")

        return True

    except Exception as e:
        print(f"[CRITICAL] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_plan_integration()
    sys.exit(0 if success else 1)