#!/usr/bin/env python3
"""
Проверка создания и открытия проекта с данными
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / 'GeoAdjustPro' / 'src'))

def test_project_save_load():
    """Тест сохранения и загрузки проекта с данными"""
    print("=" * 60)
    print("ТЕСТ СОХРАНЕНИЯ И ЗАГРУЗКИ ПРОЕКТА С ДАННЫМИ")
    print("=" * 60)

    try:
        from geoadjust.io.project.project_manager import ProjectManager
        import tempfile

        # Создаём менеджер проектов
        project_manager = ProjectManager()

        # Создаём временную директорию для проекта
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаём тестовый проект
            project_name = "Test Save Load"
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

            print("Добавляю тестовые данные...")
            for point_data in test_points:
                project.add_point(point_data)
                print(f"  Добавлен: {point_data['id']}")

            # Проверяем данные в памяти
            points_in_memory = project.get_points()
            print(f"Пунктов в памяти: {len(points_in_memory)}")

            # Сохраняем проект
            print("Сохраняю проект...")
            project.save()

            # Проверяем что файл создан
            project_file = project_dir / f"{project_name}.gad" / "project.json"
            if project_file.exists():
                print(f"Файл проекта создан: {project_file}")
            else:
                print("FAIL: Файл проекта НЕ создан")

            # Создаём новый менеджер проектов и открываем проект
            print("Открываю проект заново...")
            new_project_manager = ProjectManager()
            loaded_project = new_project_manager.open_project(project_dir / f"{project_name}.gad")

            # Проверяем данные после загрузки
            loaded_points = loaded_project.get_points()
            print(f"Пунктов после загрузки: {len(loaded_points)}")

            if len(loaded_points) > 0:
                print("SUCCESS: Данные загружены из файла!")
                for i, point in enumerate(loaded_points):
                    print(f"  {i}: ID={point.get('id')}, Name={point.get('name')}")
                return True
            else:
                print("FAIL: Данные НЕ загружены из файла")
                return False

    except Exception as e:
        print(f"FAIL: Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_save_load()
    sys.exit(0 if success else 1)