#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа в приложение P-of-Geo-Meas

Запуск приложения:
    python -m geoadjust
    или
    geoadjust (после установки)
"""

import sys
import os
import logging
import traceback
from pathlib import Path

# Проверка версии Python
if sys.version_info < (3, 8):
    print("- ТРЕБУЕТСЯ PYTHON 3.8 ИЛИ ВЫШЕ")
    print(f"   Установлена версия: {sys.version}")
    sys.exit(1)


# Проверка зависимостей при запуске
REQUIRED_PACKAGES = {
    'numpy': 'numpy',
    'scipy': 'scipy',
    'PyQt5': 'PyQt5',
    'chardet': 'chardet',
    'networkx': 'networkx',
    'pandas': 'pandas'
}


def check_dependencies():
    """Проверка наличия всех зависимостей"""
    missing = []
    for package_name, import_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print("- ОТСУТСТВУЮТ НЕОБХОДИМЫЕ ЗАВИСИМОСТИ:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nУстановите зависимости командой:")
        print("   pip install -r requirements.txt")
        sys.exit(1)


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Глобальный обработчик исключений для защиты от вылетов"""
    # Игнорируем KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Формируем сообщение об ошибке
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Выводим в консоль
    print("\n" + "=" * 60)
    print("КРИТИЧЕСКАЯ ОШИБКА ПРИЛОЖЕНИЯ")
    print("=" * 60)
    print(error_msg)
    print("=" * 60)
    print("Приложение завершилось с ошибкой.")
    print("Нажмите Enter для выхода...")
    print("=" * 60)
    
    # Логируем ошибку
    try:
        logger = logging.getLogger(__name__)
        logger.critical(f"Необработанное исключение: {error_msg}")
    except:
        pass
    
    # Ждем нажатия Enter перед выходом
    try:
        input()
    except:
        pass
    
    sys.exit(1)


def main():
    """Основная функция запуска приложения"""
    # Установка глобального обработчика исключений
    sys.excepthook = global_exception_handler
    
    # Вывод информации о запуске в консоль
    print("=" * 60)
    print("P-of-Geo-Meas - Запуск приложения")
    print("=" * 60)
    print(f"Версия Python: {sys.version}")
    print(f"Платформа: {sys.platform}")
    print()
    
    try:
        # Проверка зависимостей
        print("Проверка зависимостей...")
        check_dependencies()
        print("+ Все зависимости найдены")
        print()
        
        # Импорт утилит из центрального модуля
        from geoadjust.utils import get_resource_path, setup_logging
        
        # Настройка логирования
        log_file = Path.cwd() / "geoadjust_debug.log"
        logger = setup_logging(log_file=str(log_file))
        logger.info("=" * 60)
        logger.info("ЗАПУСК P-OF-GEO-MEAS")
        logger.info("=" * 60)
        logger.info(f"Версия Python: {sys.version}")
        logger.info(f"Платформа: {sys.platform}")
        logger.info(f"Текущая директория: {Path.cwd()}")
        logger.info(f"Файл лога: {log_file}")
        logger.info("=" * 60)
        print(f"Настройка логирования завершена. Лог: {log_file}")
        print("=" * 60)
        print()
        
        try:
            from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QIcon
        except ImportError as e:
            print(f"- Ошибка импорта PyQt5: {e}")
            print("Установите PyQt5: pip install PyQt5")
            print("\nНажмите Enter для выхода...")
            try:
                input()
            except:
                pass
            sys.exit(1)
        
        # Создание приложения
        print("Создание QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("P-of-Geo-Meas")
        app.setOrganizationName("GeoAdjust Team")
        app.setApplicationVersion("1.0.0")
        # Установка кроссплатформенного стиля Fusion для надежности
        app.setStyle('Fusion')
        print("+ QApplication создан")
        print()
        
        # Настройка шрифтов
        font = app.font()
        font.setPointSize(10)
        app.setFont(font)
        
        # Импорт менеджера проектов и приветственного диалога
        try:
            from geoadjust.io.project.project_manager import ProjectManager
            from geoadjust.gui.welcome_dialog import WelcomeDialog
            from geoadjust.gui.main_window import MainWindow, MainWindowConfig, InterfaceType
        except ImportError as e:
            logger.error(f"Ошибка импорта компонентов: {e}")
            print(f"- Ошибка импорта: {e}")
            print("\nНажмите Enter для выхода...")
            try:
                input()
            except:
                pass
            sys.exit(1)
        
        # Создание менеджера проектов
        project_manager = ProjectManager()

        # Получение списка недавних проектов
        recent_projects = [p['path'] for p in project_manager.get_recent_projects()]

        # Создание менеджера проектов
        project_manager = ProjectManager()

        # Получение списка недавних проектов
        recent_projects = [p['path'] for p in project_manager.get_recent_projects()]

        # Создание и показ приветственного диалога
        print("Отображение приветственного диалога...")
        welcome_dialog = WelcomeDialog(recent_projects=recent_projects)

        # Переменная для хранения главного окна
        main_window = None

        # Обработчики сигналов приветственного диалога
        def create_new_project():
            """Создание нового проекта с настройками по умолчанию"""
            nonlocal main_window
            logger.info("Создание нового проекта с настройками по умолчанию")

            try:
                # Создание директории по умолчанию
                default_project_path = Path.home() / "P-of-Geo-Meas Projects"
                default_project_path.mkdir(parents=True, exist_ok=True)

                # Проверка существования проекта с именем по умолчанию и генерация уникального имени
                project_name = "Новый проект"
                project_dir = default_project_path / f"{project_name}.gad"
                counter = 1

                while project_dir.exists():
                    project_name = f"Новый проект {counter}"
                    project_dir = default_project_path / f"{project_name}.gad"
                    counter += 1

                # Создание проекта с уникальным именем
                project = project_manager.create_project(
                    project_path=default_project_path,
                    project_name=project_name
                )

                # Добавление тестовых данных для демонстрации
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
                    },
                    {
                        'id': 'P003',
                        'name': 'Тестовый пункт 3',
                        'type': 'APPROXIMATE',
                        'status': 'initial',
                        'normative_class': 'Нивелирование II класса',
                        'x': 1200.0,
                        'y': 2200.0,
                        'h': 102.0
                    }
                ]

                # Добавляем тестовые пункты в проект
                for point_data in test_points:
                    project.add_point(point_data)

                # Сохраняем проект с тестовыми данными
                print("DEBUG: Сохраняю проект с тестовыми данными")
                points_before_save = project.get_points()
                print(f"DEBUG: Пунктов перед сохранением: {len(points_before_save)}")
                for i, p in enumerate(points_before_save):
                    print(f"  {i}: {p.get('id')} - {p.get('name')}")

                project.save()

                points_after_save = project.get_points()
                print(f"DEBUG: Пунктов после сохранения: {len(points_after_save)}")
                print(f"DEBUG: Проект сохранен в: {project.project_dir / project.name}.gad")

                # Создание главного окна с проектом
                config = MainWindowConfig(
                    interface_type=InterfaceType.RIBBON,
                    window_title=f"P-of-Geo-Meas • Проект: {project.name}",
                    window_size=(1600, 900),
                    window_state="maximized",
                    theme="light"
                )
                main_window = MainWindow(config)
                main_window.current_project = project

                # Обновляем данные в интерфейсе
                main_window._refresh_data_views()

                # Закрываем приветственный диалог после успешного создания
                welcome_dialog.accept()

                logger.info("Новый проект создан и отображён в главном окне")

            except Exception as e:
                logger.error(f"Ошибка создания проекта: {e}", exc_info=True)
                QMessageBox.critical(
                    welcome_dialog,
                    "Ошибка создания проекта",
                    f"Не удалось создать проект:\n{str(e)}"
                )

        def open_existing_project():
            """Открытие существующего проекта"""
            nonlocal main_window
            logger.info("Открытие существующего проекта")

            try:
                file_path = QFileDialog.getOpenFileName(
                    welcome_dialog,
                    "Открыть проект",
                    str(Path.home()),
                    "Проекты GeoAdjust (*.gad);;Все файлы (*.*)"
                )[0]

                if file_path:
                    project = project_manager.open_project(Path(file_path))

                    # Создание главного окна с проектом
                    config = MainWindowConfig(
                        interface_type=InterfaceType.RIBBON,
                        window_title=f"P-of-Geo-Meas • Проект: {project.name}",
                        window_size=(1600, 900),
                        window_state="maximized",
                        theme="light"
                    )
                    main_window = MainWindow(config)
                    main_window.current_project = project

                    # Обновляем данные в интерфейсе
                    main_window._refresh_data_views()

                    # Закрываем приветственный диалог после успешного открытия
                    welcome_dialog.accept()

                    logger.info(f"Проект '{project.name}' открыт и отображён в главном окне")

            except Exception as e:
                logger.error(f"Ошибка открытия проекта: {e}", exc_info=True)
                QMessageBox.critical(
                    welcome_dialog,
                    "Ошибка открытия проекта",
                    f"Не удалось открыть проект:\n{str(e)}"
                )

        # Подключение обработчиков сигналов
        welcome_dialog.new_project_requested.connect(create_new_project)
        welcome_dialog.open_project_requested.connect(open_existing_project)

        # Показ приветственного диалога
        result = welcome_dialog.exec_()

        if result == QDialog.Accepted:
            # Диалог был принят - проект создан или открыт
            pass
        elif result == QDialog.Rejected:
            # Диалог был отклонен - выход из программы
            logger.info("Приветственный диалог отменен пользователем")
            sys.exit(0)
        else:
            # Неожиданный результат
            logger.warning(f"Неожиданный результат приветственного диалога: {result}")
            sys.exit(1)

        # Запуск главного цикла приложения
        if main_window:
            main_window.show()
            main_window.raise_()  # Поднимаем окно поверх других
            main_window.activateWindow()  # Активируем окно

        # Запуск главного цикла приложения
        logger.info("Запуск главного цикла приложения Qt")
        print("=" * 60)
        print("+ ПРИЛОЖЕНИЕ УСПЕШНО ЗАПУЩЕНО!")
        print("=" * 60)
        exit_code = app.exec_()

        # Если произошла ошибка, оставляем консоль открытой для просмотра ошибки
        if exit_code != 0:
            print(f"\n- Приложение завершилось с кодом ошибки: {exit_code}")
            print("Нажмите Enter для выхода...")
            try:
                input()
            except:
                pass

        sys.exit(exit_code)

    except Exception as e:
        print(f"\n- Критическая ошибка: {e}")
        traceback.print_exc()
        print("\nНажмите Enter для выхода...")
        try:
            input()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
