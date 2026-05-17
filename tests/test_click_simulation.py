#!/usr/bin/env python3
"""
Тест симуляции клика по пункту в запущенном приложении
"""

import sys
import os
from pathlib import Path
import time

# Добавляем путь к модулю

def simulate_click_test():
    """Тест симуляции клика по пункту"""
    print("=" * 60)
    print("ТЕСТ СИМУЛЯЦИИ КЛИКА ПО ПУНКТУ")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.main_window import MainWindow, MainWindowConfig, InterfaceType
        from geoadjust.io.project.project_manager import ProjectManager
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
            project_name = "Test Click Simulation"
            project = project_manager.create_project(
                project_path=project_dir,
                project_name=project_name
            )

            # Добавляем тестовый пункт
            test_point = {
                'id': 'P001',
                'name': 'Тестовый пункт 1',
                'type': 'FIXED',
                'status': 'working',
                'normative_class': 'Полигонометрия 4 класса',
                'x': 1000.0,
                'y': 2000.0,
                'h': 100.0
            }
            project.add_point(test_point)
            project.save()

            print("OK: Проект создан с тестовым пунктом")

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

            # Загружаем данные
            main_window._refresh_data_views()
            print("OK: Данные загружены")

            # Проверяем что пункт есть в таблице
            points_table = main_window.points_table
            model = points_table.model
            row_count = model.rowCount()
            print(f"OK: В таблице {row_count} строк")

            if row_count > 0:
                # Имитируем сигнал выбора пункта
                point_id = model.index(0, 0).data()
                print(f"Имитирую выбор пункта: {point_id}")

                # Отправляем сигнал напрямую
                points_table.point_selected.emit(point_id)
                print("OK: Сигнал отправлен")

                # Даем время на обработку
                app.processEvents()

                # Проверяем что свойства установлены
                props_widget = main_window.properties_widget
                if hasattr(props_widget, 'current_object') and props_widget.current_object:
                    print(f"OK: Свойства установлены для: {props_widget.current_object}")
                else:
                    print("FAIL: Свойства не установлены")

                # Проверяем заголовок
                title = props_widget.title_label.text()
                print(f"Заголовок окна свойств: '{title}'")

                if point_id in title:
                    print("SUCCESS: Окно свойств корректно отображает выбранный пункт!")
                    return True
                else:
                    print("FAIL: Окно свойств не обновилось")
                    return False
            else:
                print("FAIL: Нет данных в таблице")
                return False

    except Exception as e:
        print(f"FAIL: Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simulate_click_test()
    if success:
        print("\n🎉 ТЕСТ ПРОЙДЕН: Механизм выбора пунктов работает!")
    else:
        print("\n❌ ТЕСТ НЕ ПРОЙДЕН: Проблемы с механизмом выбора пунктов")
    sys.exit(0 if success else 1)