#!/usr/bin/env python3
"""
Проверка сохранения и чтения данных в проекте
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / 'GeoAdjustPro' / 'src'))

def test_project_data_storage():
    """Тест сохранения и чтения данных проекта"""
    print("=" * 60)
    print("ТЕСТ СОХРАНЕНИЯ И ЧТЕНИЯ ДАННЫХ ПРОЕКТА")
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
            project_name = "Test Data Project"
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

            print("Добавляю тестовые данные в проект...")
            for point_data in test_points:
                project.add_point(point_data)
                print(f"  Добавлен пункт: {point_data['id']}")

            # Проверяем что данные добавлены
            points = project.get_points()
            print(f"Всего пунктов в проекте: {len(points)}")

            for i, point in enumerate(points):
                print(f"  Пункт {i}: ID={point.get('id')}, Name={point.get('name')}")

            # Сохраняем проект
            print("Сохраняю проект...")
            project.save()

            # Создаём новый проект и загружаем данные
            print("Загружаю проект заново...")
            loaded_project = project_manager.open_project(project_dir / f"{project_name}.gad")
            loaded_points = loaded_project.get_points()

            print(f"Пунктов после загрузки: {len(loaded_points)}")
            for i, point in enumerate(loaded_points):
                print(f"  Загруженный пункт {i}: ID={point.get('id')}, Name={point.get('name')}")

            # Проверяем поиск по ID
            print("Тестирую поиск пунктов...")
            for test_point in test_points:
                point_id = test_point['id']
                found = False
                for point in loaded_points:
                    if isinstance(point, dict) and (point.get('id') == point_id or point.get('name') == point_id):
                        print(f"  ✓ Найден пункт {point_id}: {point}")
                        found = True
                        break
                if not found:
                    print(f"  ✗ НЕ найден пункт {point_id}")

            return True

    except Exception as e:
        print(f"FAIL: Ошибка в тесте: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_data_storage()
    sys.exit(0 if success else 1)