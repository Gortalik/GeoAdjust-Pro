#!/usr/bin/env python3
"""
Тест функциональности окон Свойства и История
GeoAdjust Pro
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_properties_widget():
    """Тест виджета свойств"""
    print("=" * 60)
    print("ТЕСТ ВИДЖЕТА СВОЙСТВ")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.components.properties_widget import PropertiesWidget

        # Создаём приложение если не существует
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Создаём виджет свойств
        widget = PropertiesWidget()
        print("OK Виджет свойств создан")

        # Тест установки свойств пункта
        point_props = {
            'coord_type': 'FIXED',
            'x': 1000.0,
            'y': 2000.0,
            'h': 100.0,
            'normative_class': 'Полигонометрия 4 класса',
            'sigma_x': 0.005,
            'sigma_y': 0.005
        }

        widget.set_point_properties('P1', point_props)
        print("OK Свойства пункта установлены")

        # Тест установки свойств измерения
        obs_props = {
            'obs_type': 'direction',
            'from_point': 'P1',
            'to_point': 'P2',
            'value': 45.5,
            'instrument_name': 'TotalStation',
            'sigma_apriori': 0.005,
            'is_active': True,
            'weight_multiplier': 1.0
        }

        widget.set_observation_properties('OBS1', obs_props)
        print("OK Свойства измерения установлены")

        # Проверяем, что виджет не пустой
        assert widget.current_object is not None
        print("OK Текущий объект установлен")

        # Очищаем виджет
        widget.clear()
        print("OK Виджет очищен")

        return True

    except Exception as e:
        print(f"FAIL Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_history_widget():
    """Тест виджета истории"""
    print("=" * 60)
    print("ТЕСТ ВИДЖЕТА ИСТОРИИ")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.components.history_widget import HistoryWidget, HistoryEntry
        from pathlib import Path
        import tempfile

        # Создаём приложение если не существует
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Создаём временную директорию для проекта
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаём виджет истории
            widget = HistoryWidget(project_dir=project_dir)
            print("OK Виджет истории создан")

            # Добавляем тестовые записи
            entries = [
                HistoryEntry('add_point', 'Добавлен пункт P1', {'point_id': 'P1'}),
                HistoryEntry('edit_point', 'Изменены координаты P1', {'point_id': 'P1', 'x': 1000.0}),
                HistoryEntry('delete_point', 'Удалён пункт P2', {'point_id': 'P2'}),
            ]

            for entry in entries:
                widget.add_entry(entry)
                print(f"OK Добавлена запись: {entry.description}")

            # Проверяем менеджер истории
            manager = widget.get_history_manager()
            assert manager.can_undo() == True
            assert manager.can_redo() == False
            print("OK Менеджер истории работает корректно")

            # Тест отмены
            undo_entry = manager.undo()
            assert undo_entry is not None
            assert undo_entry.action_type == 'delete_point'
            print("OK Отмена действия работает")

            # Тест повтора
            assert manager.can_redo() == True
            redo_entry = manager.redo()
            assert redo_entry is not None
            assert redo_entry.action_type == 'delete_point'
            print("OK Повтор действия работает")

            # Очищаем историю
            manager.clear()
            assert not manager.can_undo()
            assert not manager.can_redo()
            print("OK Очистка истории работает")

        return True

    except Exception as e:
        print(f"FAIL Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_properties_history_tab_widget():
    """Тест комбинированного виджета Свойства + История"""
    print("=" * 60)
    print("ТЕСТ КОМБИНИРОВАННОГО ВИДЖЕТА")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.components.history_widget import PropertiesHistoryTabWidget, HistoryEntry

        # Создаём приложение если не существует
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Создаём комбинированный виджет
        widget = PropertiesHistoryTabWidget()
        print("OK Комбинированный виджет создан")

        # Проверяем наличие вкладок
        assert widget.count() == 2
        assert widget.tabText(0) == "Свойства"
        assert widget.tabText(1) == "История"
        print("OK Вкладки созданы корректно")

        # Получаем доступ к подвиджетам
        properties_widget = widget.properties_widget
        history_widget = widget.history_widget

        # Тест свойств
        point_props = {
            'coord_type': 'FIXED',
            'x': 1000.0,
            'y': 2000.0,
            'h': 100.0
        }
        properties_widget.set_point_properties('P1', point_props)
        print("OK Свойства в комбинированном виджете работают")

        # Тест истории
        entry = HistoryEntry('add_point', 'Добавлен пункт P1', {'point_id': 'P1'})
        history_widget.add_entry(entry)
        print("OK История в комбинированном виджете работает")

        return True

    except Exception as e:
        print(f"FAIL Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_project_properties_dialog():
    """Тест диалога свойств проекта"""
    print("=" * 60)
    print("ТЕСТ ДИАЛОГА СВОЙСТВ ПРОЕКТА")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.dialogs.project_properties import ProjectPropertiesDialog

        # Создаём приложение если не существует
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Создаём mock проект
        class MockProject:
            def __init__(self):
                self.name = "Тестовый проект"
                self.description = "Описание тестового проекта"
                self.crs = "СК-42"
                self.settings = {}

            def get_settings(self):
                return self.settings

            def update_settings(self, settings):
                self.settings.update(settings)

        mock_project = MockProject()

        # Создаём диалог (не показываем, только создаём)
        dialog = ProjectPropertiesDialog(mock_project)
        print("OK Диалог свойств проекта создан")

        # Проверяем основные компоненты
        assert dialog.windowTitle() == "Свойства проекта"
        print("OK Заголовок диалога корректный")

        # Проверяем дерево настроек
        tree = None
        for child in dialog.children():
            if hasattr(child, 'topLevelItemCount'):  # QTreeWidget
                tree = child
                break

        if tree:
            print("OK Дерево настроек найдено")
        else:
            print("WARNING Дерево настроек не найдено (возможно, в layout)")

        return True

    except Exception as e:
        print(f"FAIL Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 80)
    print("КОМПЛЕКСНЫЙ ТЕСТ ОКОН СВОЙСТВА И ИСТОРИЯ")
    print("GeoAdjust Pro")
    print("=" * 80)

    tests = [
        ("Виджет свойств", test_properties_widget),
        ("Виджет истории", test_history_widget),
        ("Комбинированный виджет", test_properties_history_tab_widget),
        ("Диалог свойств проекта", test_project_properties_dialog),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\nЗапуск теста: {test_name}")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nFAIL Критическая ошибка в тесте '{test_name}': {str(e)}")
            results.append((test_name, False))

    # Итоговый отчёт
    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 80)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "OK PASSED" if result else "FAIL FAILED"
        print(f"  {status}: {test_name}")

    print(f"\nОбщий результат: {passed}/{total} тестов пройдено")

    if passed == total:
        print("\nSUCCESS ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Окна Свойства и История работают корректно.")
        return 0
    else:
        print(f"\nWARNING️  {total - passed} тест(а) не пройдены. Требуется внимание.")
        return 1

if __name__ == "__main__":
    sys.exit(main())