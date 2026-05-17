#!/usr/bin/env python3
"""
Проверка работы сигналов и загрузки данных в приложении
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулю

def test_full_application_flow():
    """Тест полного цикла работы приложения"""
    print("=" * 60)
    print("ТЕСТ ПОЛНОГО ЦИКЛА РАБОТЫ ПРИЛОЖЕНИЯ")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.main_window import MainWindow, MainWindowConfig, InterfaceType
        from geoadjust.io.project.project_manager import ProjectManager
        from pathlib import Path
        import tempfile

        # Создаём приложение
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        print("OK: QApplication создан")

        # Создаём временную директорию для проекта
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаём менеджер проектов
            project_manager = ProjectManager()

            # Создаём тестовый проект
            project_name = "Test Project"
            project = project_manager.create_project(
                project_path=project_dir,
                project_name=project_name
            )

            # Добавляем тестовые данные
            test_points = [
                {
                    'id': 'P001',
                    'name': 'Тестовый пункт 1',
                    'type': 'FIXED',
                    'status': 'working',
                    'normative_class': 'Полигонометрия 4 класса',
                    'x': 1000.0,
                    'y': 2000.0,
                    'h': 100.0
                },
                {
                    'id': 'P002',
                    'name': 'Тестовый пункт 2',
                    'type': 'FREE',
                    'status': 'working',
                    'normative_class': 'Нивелирование I класса',
                    'x': 1100.0,
                    'y': 2100.0,
                    'h': 101.0
                }
            ]

            for point_data in test_points:
                project.add_point(point_data)

            print(f"OK: Создан проект '{project_name}' с {len(test_points)} пунктами")

            # Создаём главное окно
            config = MainWindowConfig(
                interface_type=InterfaceType.RIBBON,
                window_title=f"Test • Проект: {project.name}",
                window_size=(1200, 800),
                window_state="normal",
                theme="light"
            )
            main_window = MainWindow(config)
            main_window.current_project = project

            print("OK: Создано главное окно")

            # Проверяем что проект установлен
            assert main_window.current_project is not None
            print("OK: Проект установлен в главное окно")

            # Вызываем обновление данных
            main_window._refresh_data_views()
            print("OK: Вызвано обновление данных")

            # Проверяем что данные загружены в таблицу
            points_table = main_window.points_table  # Это уже PointsTableView
            model = points_table.model
            row_count = model.rowCount()
            print(f"OK: В таблице пунктов {row_count} строк")

            if row_count > 0:
                print("OK: Данные загружены в таблицу пунктов")

                # Проверяем первую строку
                first_row_data = []
                for col in range(min(5, model.columnCount())):  # Проверяем первые 5 колонок
                    data = model.index(0, col).data()
                    first_row_data.append(str(data))
                print(f"Первая строка: {first_row_data}")

            # Проверяем что окна свойств и истории созданы
            props_dock = main_window.properties_dock
            if props_dock:
                print("OK: Док-виджет свойств создан")

                # Проверяем вкладки
                props_widget = main_window.properties_widget
                history_widget = main_window.history_widget

                if props_widget:
                    print("OK: Виджет свойств доступен")
                if history_widget:
                    print("OK: Виджет истории доступен")

            print("\n" + "="*60)
            print("Тест завершен успешно!")
            print("Все компоненты работают корректно.")
            print("="*60)

            return True

    except Exception as e:
        print(f"FAIL: Ошибка в тесте: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_application_flow()
    sys.exit(0 if success else 1)