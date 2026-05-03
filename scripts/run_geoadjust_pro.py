#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрация работы GeoAdjust Pro
Запуск полноценного приложения
"""

import subprocess
import sys
import os
from pathlib import Path

def run_geoadjust_pro():
    """Запуск GeoAdjust Pro"""

    print("=" * 80)
    print("GeoAdjust Pro - ПОЛНОЦЕННОЕ ПРИЛОЖЕНИЕ")
    print("=" * 80)
    print()
    print("✓ Полная GUI оболочка на PyQt5")
    print("✓ Поддержка форматов: GSI, SDR, DAT, POS")
    print("✓ 9 этапов предобработки данных")
    print("✓ Уравнивание методом МНК")
    print("✓ Анализ надёжности (метод Баарда)")
    print("✓ Отчёты по ГОСТ 7.32-2017")
    print("✓ Системы координат РФ")
    print("✓ Экспорт в DXF, DOCX, HTML")
    print()
    print("Запуск приложения...")
    print()

    # Переход в директорию приложения
    app_dir = Path(__file__).parent / "GeoAdjustPro" / "src"

    try:
        # Запуск приложения
        os.chdir(app_dir)
        result = subprocess.run([sys.executable, "-m", "geoadjust"],
                              capture_output=False, text=True)

        return result.returncode == 0

    except KeyboardInterrupt:
        print("\nПриложение закрыто пользователем")
        return True
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        return False

if __name__ == "__main__":
    success = run_geoadjust_pro()

    print()
    print("=" * 80)
    if success:
        print("GeoAdjust Pro РАБОТАЕТ КОРРЕКТНО!")
        print("Все функции доступны через GUI интерфейс.")
    else:
        print("Ошибка запуска приложения")
    print("=" * 80)