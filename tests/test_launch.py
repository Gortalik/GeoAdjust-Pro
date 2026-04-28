#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый запуск GeoAdjust Pro без сборки exe
Запускает приложение в режиме разработки для тестирования
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Тестирование импортов без запуска GUI"""
    print("=" * 60)
    print("1. ТЕСТИРОВАНИЕ ИМПОРТОВ")
    print("=" * 60)

    test_modules = [
        "geoadjust.utils",
        "geoadjust.core.network.models",
        "geoadjust.core.adjustment.engine",
        "geoadjust.gui.main_window",
        "geoadjust.io.formats.gsi",
        "geoadjust.io.formats.sdr"
    ]

    success_count = 0
    for module in test_modules:
        try:
            __import__(module)
            print(f"[OK] {module}")
            success_count += 1
        except ImportError as e:
            print(f"[ERROR] {module}: {e}")

    print(f"\nРезультат: {success_count}/{len(test_modules)} модулей импортировано")
    return success_count == len(test_modules)

def run_gui_test():
    """Запуск GUI в тестовом режиме"""
    print("\n" + "=" * 60)
    print("2. ЗАПУСК GUI ПРИЛОЖЕНИЯ")
    print("=" * 60)

    # Проверяем наличие дисплея
    try:
        from PyQt5.QtWidgets import QApplication
        import os
        if os.name == 'nt':  # Windows
            # На Windows проверяем переменную DISPLAY или просто пытаемся создать QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            print("[OK] QApplication создан успешно")
            app.quit()
            return True
        else:
            # На Linux/Unix проверяем DISPLAY
            display = os.environ.get('DISPLAY')
            if not display:
                print("[WARNING] Переменная DISPLAY не установлена")
                print("[INFO] На Linux установите DISPLAY или используйте X11 forwarding")
                return False
            print(f"[OK] DISPLAY: {display}")
            return True
    except Exception as e:
        print(f"[ERROR] Ошибка создания QApplication: {e}")
        return False

def main():
    print("=" * 60)
    print("ТЕСТОВЫЙ ЗАПУСК GeoAdjust Pro")
    print("Режим разработки - без сборки exe")
    print("=" * 60)

    # Определяем пути
    current_dir = Path(__file__).parent
    geoadjust_dir = current_dir / "GeoAdjustPro"
    src_path = geoadjust_dir / "src"

    # Добавляем путь к исходному коду
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        print(f"[OK] Добавлен путь: {src_path}")

    # Устанавливаем рабочую директорию на GeoAdjustPro
    os.chdir(geoadjust_dir)
    print(f"[OK] Рабочая директория: {geoadjust_dir}")

    try:
        # Тестируем импорты
        if not test_imports():
            print("\n[ERROR] Не все модули удалось импортировать")
            sys.exit(1)

        # Тестируем GUI
        if not run_gui_test():
            print("\n[WARNING] GUI тест не пройден - возможно нет дисплея")
            print("[INFO] Но программа готова к запуску на системе с GUI")

        # Запуск полного приложения
        print("\n" + "=" * 60)
        print("3. ЗАПУСК ПОЛНОГО ПРИЛОЖЕНИЯ")
        print("=" * 60)
        print("[INFO] Запуск GeoAdjust Pro...")
        print("[INFO] Если GUI не отображается, приложение работает в фоне")
        print("[INFO] Для выхода нажмите Ctrl+C")

        # Импортируем и запускаем главное приложение
        import geoadjust.__main__

    except ImportError as e:
        print(f"[ERROR] Ошибка импорта: {e}")
        print("[INFO] Попробуйте установить зависимости:")
        print("  pip install -r GeoAdjustPro/requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Приложение остановлено пользователем")
    except Exception as e:
        print(f"[ERROR] Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()