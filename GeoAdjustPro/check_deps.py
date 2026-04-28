#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка установки критических зависимостей для GeoAdjust Pro

Запустите этот скрипт перед сборкой приложения, чтобы убедиться,
что все необходимые зависимости установлены корректно.
"""

import sys
import importlib

CRITICAL_DEPS = [
    ('numpy', 'numpy'),
    ('scipy', 'scipy'),
    ('PyQt5', 'PyQt5.QtWidgets'),
    ('networkx', 'networkx'),
    ('matplotlib', 'matplotlib'),
    ('pandas', 'pandas'),
    ('python-docx', 'docx'),
    ('openpyxl', 'openpyxl'),
    ('Pillow', 'PIL'),
    ('chardet', 'chardet'),
    ('PyYAML', 'yaml'),
    ('ezdxf', 'ezdxf'),
]

print("=" * 80)
print("ПРОВЕРКА УСТАНОВКИ КРИТИЧЕСКИХ ЗАВИСИМОСТЕЙ")
print("=" * 80)
print()

all_ok = True
critical_missing = []

for package_name, module_name in CRITICAL_DEPS:
    try:
        importlib.import_module(module_name)
        print(f"[OK] {package_name:25s} - УСТАНОВЛЕН")
    except ImportError as e:
        print(f"[NO] {package_name:25s} - ОТСУТСТВУЕТ ({e})")
        all_ok = False
        critical_missing.append(package_name)

print()
print("=" * 80)

if all_ok:
    print("[OK] ВСЕ КРИТИЧЕСКИЕ ЗАВИСИМОСТИ УСТАНОВЛЕНЫ")
    print()
    print("Можно запускать сборку:")
    print("  cd GeoAdjustPro")
    print("  pyinstaller P-of-Geo-Meas.spec --clean --noconfirm")
else:
    print("[!!] НЕКОТОРЫЕ КРИТИЧЕСКИЕ ЗАВИСИМОСТИ ОТСУТСТВУЮТ")
    print()
    print("Отсутствующие пакеты:")
    for pkg in critical_missing:
        print(f"  - {pkg}")
    print()
    print("Рекомендуемые действия:")
    print()
    print("[PKG] Пакеты можно установить через pip:")
    print(f"   pip install {' '.join(critical_missing)}")
    print()
    print("   С использованием китайского зеркала (если проблемы с сетью):")
    print(f"   pip install {' '.join(critical_missing)} --index-url https://pypi.tuna.tsinghua.edu.cn/simple")
    print()

print("=" * 80)

sys.exit(0 if all_ok else 1)
