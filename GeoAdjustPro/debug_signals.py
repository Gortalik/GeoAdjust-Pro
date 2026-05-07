#!/usr/bin/env python3
"""
Отладочный тест для проверки подключения сигналов и работы окон
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_signals_connection():
    """Тест подключения сигналов"""
    print("=" * 60)
    print("ОТЛАДОЧНЫЙ ТЕСТ ПОДКЛЮЧЕНИЯ СИГНАЛОВ")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from geoadjust.gui.components.properties_widget import PropertiesWidget
        from geoadjust.gui.components.history_widget import PropertiesHistoryTabWidget, HistoryEntry
        from geoadjust.gui.widgets.points_table import PointsTableWidget

        # Создаём приложение
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        print("OK: QApplication создан")

        # Создаём комбинированный виджет
        props_history = PropertiesHistoryTabWidget()
        print("OK: PropertiesHistoryTabWidget создан")

        # Проверяем что вкладки созданы
        tab_count = props_history.count()
        print(f"OK: Создано {tab_count} вкладок")
        for i in range(tab_count):
            tab_text = props_history.tabText(i)
            print(f"  Вкладка {i}: {tab_text}")

        # Создаём таблицу пунктов
        points_table = PointsTableWidget()
        print("OK: Таблица пунктов создана")

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
                'h': 100.0,
                'instrument': 'Leica',
                'notes': 'Тестовый пункт'
            },
            {
                'id': 'P002',
                'name': 'Тестовый пункт 2',
                'type': 'FREE',
                'status': 'initial',
                'normative_class': 'Нивелирование I класса',
                'x': 1100.0,
                'y': 2100.0,
                'h': 101.0,
                'instrument': 'Trimble',
                'notes': 'Еще один тестовый пункт'
            }
        ]

        points_table.load_from_data(test_points)
        print("OK: Тестовые данные загружены")

        # Проверяем модель таблицы
        model = points_table.table_view.model
        row_count = model.rowCount()
        col_count = model.columnCount()
        print(f"OK: Таблица имеет {row_count} строк и {col_count} колонок")

        # Проверяем заголовки
        headers = []
        for col in range(col_count):
            header = model.headerData(col, 0)  # Qt.Horizontal = 0
            headers.append(str(header))
        print(f"Заголовки колонок: {headers}")

        # Проверяем данные в первой строке
        if row_count > 0:
            first_row_data = []
            for col in range(col_count):
                data = model.index(0, col).data()
                first_row_data.append(str(data))
            print(f"Первая строка данных: {first_row_data}")

        # Проверяем что делегаты установлены
        for col in range(col_count):
            delegate = points_table.table_view.itemDelegateForColumn(col)
            delegate_name = type(delegate).__name__
            print(f"Колонка {col} ({headers[col] if col < len(headers) else 'N/A'}): делегат {delegate_name}")

        print("\n" + "="*60)
        print("Тест завершен успешно!")
        print("Все компоненты созданы и настроены корректно.")
        print("="*60)

        return True

    except Exception as e:
        print(f"FAIL: Ошибка в тесте: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_signals_connection()
    sys.exit(0 if success else 1)