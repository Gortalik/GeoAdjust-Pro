#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест основных функций GUI (без отображения)
"""

import sys
import os
sys.path.insert(0, 'GeoAdjustPro/src')

# Устанавливаем виртуальный дисплей для тестирования GUI
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer
    import geoadjust.gui.main_window as mw

    print('Testing GUI functionality...')

    # Создаем QApplication
    app = QApplication([])

    # Создаем главное окно
    window = mw.MainWindow()
    print('Main window created successfully')

    # Проверяем основные компоненты
    if hasattr(window, 'project_manager'):
        print('OK project_manager')
    else:
        print('MISSING project_manager')

    if hasattr(window, 'data_processor'):
        print('OK data_processor')
    else:
        print('MISSING data_processor')

    if hasattr(window, 'plot_view'):
        print('OK plot_view')
    else:
        print('MISSING plot_view')

    # Проверяем меню
    if hasattr(window, 'menuBar'):
        menubar = window.menuBar()
        if menubar:
            print('OK menu bar')
            actions = menubar.actions()
            print(f'Menu has {len(actions)} top-level items')
        else:
            print('MISSING menu bar')

    # Завершаем приложение
    QTimer.singleShot(100, app.quit)
    app.exec_()

    print('GUI test completed successfully')

except ImportError as e:
    print(f'PyQt5 not available: {e}')
    print('GUI components cannot be tested without PyQt5')

except Exception as e:
    print(f'GUI test error: {e}')