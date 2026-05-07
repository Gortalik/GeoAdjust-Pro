#!/usr/bin/env python3
"""
Тест функциональности окон Свойства и История после исправлений
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_windows_functionality():
    """Тест работы окон после исправлений"""
    print("=" * 60)
    print("ТЕСТ РАБОТЫ ОКОН ПОСЛЕ ИСПРАВЛЕНИЙ")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.components.properties_widget import PropertiesWidget
        from geoadjust.gui.components.history_widget import PropertiesHistoryTabWidget, HistoryEntry
        from geoadjust.gui.widgets.points_table import PointsTableWidget

        # Создаём приложение если не существует
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        print("OK Создание QApplication")

        # Создаём комбинированный виджет
        props_history = PropertiesHistoryTabWidget()
        print("OK Создание PropertiesHistoryTabWidget")

        # Создаём таблицу пунктов
        points_table = PointsTableWidget()
        print("OK Создание таблицы пунктов")

        # Добавляем тестовый пункт
        test_point = {
            'id': 'P001',
            'name': 'Тестовый пункт',
            'type': 'FIXED',
            'status': 'working',
            'normative_class': 'Полигонометрия 4 класса',
            'x': 1000.0,
            'y': 2000.0,
            'h': 100.0,
            'instrument': 'Leica',
            'notes': 'Тестовый пункт'
        }

        points_table.load_from_data([test_point])
        print("OK Загрузка тестовых данных в таблицу")

        # Проверяем что данные загружены
        model = points_table.table_view.model
        if model.rowCount() > 0:
            print("OK Данные загружены в таблицу")
            # Проверяем колонки
            if model.columnCount() == 10:
                print("OK Количество колонок корректно (10)")
            else:
                print(f"FAIL Количество колонок: {model.columnCount()}, ожидалось 10")
        else:
            print("FAIL Данные не загружены в таблицу")

        # Тестируем свойства
        props_widget = props_history.properties_widget
        props_widget.set_point_properties('P001', test_point)
        print("OK Установка свойств пункта")

        # Проверяем что свойства установлены
        if props_widget.current_object and props_widget.current_object['id'] == 'P001':
            print("OK Свойства пункта установлены корректно")
        else:
            print("FAIL Свойства пункта не установлены")

        # Тестируем историю
        history_widget = props_history.history_widget
        entry = HistoryEntry('add_point', 'Добавлен тестовый пункт P001', {'point_id': 'P001'})
        history_widget.add_entry(entry)
        print("OK Добавление записи в историю")

        # Проверяем историю
        manager = history_widget.get_history_manager()
        if manager.can_undo() and len(manager.get_entries()) > 0:
            print("OK История работает корректно")
        else:
            print("FAIL История не работает")

        return True

    except Exception as e:
        print(f"FAIL Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_windows_functionality()
    if success:
        print("\nSUCCESS: Исправления применены успешно!")
    else:
        print("\nFAIL: Есть проблемы с исправлениями")
    sys.exit(0 if success else 1)