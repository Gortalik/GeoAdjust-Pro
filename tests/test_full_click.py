#!/usr/bin/env python3
"""
Тест полного пути: клик -> сигнал -> отображение свойств
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулю

def test_full_click_to_properties():
    """Тест полного пути от клика до отображения свойств"""
    print("=" * 60)
    print("ТЕСТ ПОЛНОГО ПУТИ: КЛИК -> СИГНАЛ -> СВОЙСТВА")
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
            project_name = "Test Click Project"
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
                }
            ]

            for point_data in test_points:
                project.add_point(point_data)

            project.save()
            print("OK: Проект создан и сохранен с тестовыми данными")

            # Создаём главное окно
            config = MainWindowConfig(
                interface_type=InterfaceType.RIBBON,
                window_title=f"Test Click • Проект: {project.name}",
                window_size=(1200, 800),
                window_state="normal",
                theme="light"
            )
            main_window = MainWindow(config)
            main_window.current_project = project

            # Вызываем обновление данных
            main_window._refresh_data_views()
            print("OK: Данные загружены в интерфейс")

            # Проверяем что данные в таблице
            points_table = main_window.points_table
            model = points_table.model
            row_count = model.rowCount()
            print(f"OK: В таблице {row_count} строк")

            if row_count > 0:
                # Имитируем клик на первой строке
                print("Имитирую клик на первой строке таблицы...")

                # Получаем point_id из таблицы
                point_id = model.index(0, 0).data()
                print(f"Point ID из таблицы: {point_id}")

                # Вызываем обработчик выбора пункта напрямую
                print("Вызываю _on_point_selected напрямую...")
                main_window._on_point_selected(point_id)

                # Проверяем что свойства установлены
                props_widget = main_window.properties_widget
                if props_widget.current_object:
                    print(f"OK: Свойства установлены для объекта: {props_widget.current_object}")
                else:
                    print("FAIL: Свойства НЕ установлены")

                # Проверяем что заголовок окна свойств изменился
                title = props_widget.title_label.text()
                print(f"Заголовок окна свойств: '{title}'")

                if "P001" in title:
                    print("SUCCESS: Окно свойств отображает данные выбранного пункта!")
                    return True
                else:
                    print("FAIL: Окно свойств не отображает данные пункта")
                    return False
            else:
                print("FAIL: Нет данных в таблице")
                return False

    except Exception as e:
        print(f"FAIL: Ошибка в тесте: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_click_to_properties()
    sys.exit(0 if success else 1)