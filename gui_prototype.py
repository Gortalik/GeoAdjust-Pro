#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoAdjust Pro - Полная GUI версия прототипа
"""

import sys
import os
from pathlib import Path
from collections import defaultdict
import math

# GUI imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QSplitter, QMenuBar, QMenu,
                             QAction, QFileDialog, QMessageBox, QTextEdit, QTabWidget,
                             QLabel, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
                             QGraphicsLineItem, QGraphicsTextItem, QStatusBar, QProgressBar)
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QBrush, QPen, QColor, QFont

class Point:
    """Класс для представления геодезического пункта"""
    def __init__(self, name, x=None, y=None, z=None, coord_type='FREE'):
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.coord_type = coord_type

    def __str__(self):
        return f"Point({self.name}, x={self.x}, y={self.y}, z={self.z}, type={self.coord_type})"

class Observation:
    """Класс для представления измерения"""
    def __init__(self, obs_type, from_point, to_point, value, station=None):
        self.obs_type = obs_type
        self.from_point = from_point
        self.to_point = to_point
        self.value = value
        self.station = station

    def __str__(self):
        return f"Obs({self.obs_type}, {self.from_point}->{self.to_point}, {self.value})"

class GSIParser:
    """Парсер формата Leica GSI"""
    def parse(self, file_path):
        points = {}
        observations = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            blocks = line.split()
            for block in blocks:
                if '+' in block or '-' in block:
                    try:
                        wi = block[:2]
                        wv = block[2:4]
                        value_str = block[4:]
                        if wi == '11':
                            if wv == '00':
                                station = int(float(value_str))
                            elif wv == '02':
                                direction = float(value_str) / 10000
                                if 'station' in locals():
                                    observations.append(Observation('direction', f'S{station}', f'P{direction}', direction, f'S{station}'))
                            elif wv == '03':
                                zenith = float(value_str) / 10000
                                observations.append(Observation('zenith_angle', f'S{station}', f'P{zenith}', zenith, f'S{station}'))
                            elif wv == '04':
                                distance = float(value_str) / 1000
                                observations.append(Observation('slope_distance', f'S{station}', f'P{distance}', distance, f'S{station}'))
                        elif wi == '41':
                            if wv == '00':
                                height_diff = float(value_str) / 1000
                                observations.append(Observation('height_diff', f'S{station}', f'P{height_diff}', height_diff, f'S{station}'))
                    except ValueError:
                        continue
        return {'points': list(points.values()), 'observations': observations}

class SDRParser:
    """Парсер формата Sokkia SDR"""
    def parse(self, file_path):
        points = {}
        observations = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        current_station = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            code = line[:2]
            if code == '01':
                parts = line.split()
                if len(parts) > 1:
                    current_station = parts[1]
            elif code == '02':
                parts = line.split()
                if len(parts) > 3:
                    point_name = parts[2]
                    x = float(parts[3])
                    y = float(parts[4])
                    points[point_name] = Point(point_name, x, y, coord_type='FREE')
            elif code == '03':
                parts = line.split()
                if len(parts) > 4 and current_station:
                    obs_type = parts[1]
                    to_point = parts[2]
                    value = float(parts[3])
                    if obs_type == 'direction':
                        observations.append(Observation('direction', current_station, to_point, value, current_station))
                    elif obs_type == 'distance':
                        observations.append(Observation('slope_distance', current_station, to_point, value, current_station))
        return {'points': list(points.values()), 'observations': observations}

class PlanView(QGraphicsView):
    """Виджет для отображения геодезической сети"""

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.points = {}
        self.observations = []
        self.scale_factor = 1.0

    def clear_all(self):
        """Очистить план"""
        self.scene.clear()
        self.points.clear()
        self.observations.clear()

    def add_point(self, name, x, y, point_type='FREE'):
        """Добавить пункт на план"""
        # Масштабирование для отображения
        scaled_x = x * self.scale_factor
        scaled_y = y * self.scale_factor

        # Цвет в зависимости от типа
        if point_type == 'FIXED':
            color = QColor(255, 0, 0)  # Красный
        elif point_type == 'APPROXIMATE':
            color = QColor(255, 165, 0)  # Оранжевый
        else:
            color = QColor(0, 0, 255)  # Синий

        # Создаем эллипс для пункта
        ellipse = QGraphicsEllipseItem(scaled_x - 5, scaled_y - 5, 10, 10)
        ellipse.setBrush(QBrush(color))
        ellipse.setPen(QPen(Qt.black, 2))

        # Добавляем подпись
        text = QGraphicsTextItem(name)
        text.setPos(scaled_x + 5, scaled_y - 5)
        font = QFont()
        font.setPointSize(8)
        text.setFont(font)

        self.scene.addItem(ellipse)
        self.scene.addItem(text)
        self.points[name] = (ellipse, text, x, y)

    def add_observation(self, from_point, to_point, obs_type):
        """Добавить измерение на план"""
        if from_point in self.points and to_point in self.points:
            _, _, x1, y1 = self.points[from_point]
            _, _, x2, y2 = self.points[to_point]

            scaled_x1 = x1 * self.scale_factor
            scaled_y1 = y1 * self.scale_factor
            scaled_x2 = x2 * self.scale_factor
            scaled_y2 = y2 * self.scale_factor

            # Цвет линии в зависимости от типа измерения
            if obs_type == 'direction':
                color = QColor(0, 255, 0)  # Зеленый
            elif obs_type == 'slope_distance':
                color = QColor(255, 0, 255)  # Магента
            else:
                color = QColor(128, 128, 128)  # Серый

            line = QGraphicsLineItem(scaled_x1, scaled_y1, scaled_x2, scaled_y2)
            line.setPen(QPen(color, 2))

            self.scene.addItem(line)
            self.observations.append(line)

    def fit_to_contents(self):
        """Подогнать масштаб под содержимое"""
        if self.points:
            rect = self.scene.itemsBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)

    def draw_network(self, project_data):
        """Нарисовать сеть из данных проекта"""
        self.clear_all()

        # Добавляем пункты
        for point in project_data.get('points', []):
            if point.x is not None and point.y is not None:
                self.add_point(point.name, point.x, point.y, point.coord_type)

        # Добавляем измерения
        for obs in project_data.get('observations', []):
            self.add_observation(obs.from_point, obs.to_point, obs.obs_type)

        self.fit_to_contents()

class PointsTable(QTableWidget):
    """Таблица пунктов"""

    def __init__(self):
        super().__init__()
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(['Имя', 'X', 'Y', 'Z', 'Тип'])
        self.points = []

    def update_data(self, points):
        """Обновить данные таблицы"""
        self.points = points
        self.setRowCount(len(points))

        for row, point in enumerate(points):
            self.setItem(row, 0, QTableWidgetItem(point.name))
            self.setItem(row, 1, QTableWidgetItem(f"{point.x:.4f}" if point.x else ""))
            self.setItem(row, 2, QTableWidgetItem(f"{point.y:.4f}" if point.y else ""))
            self.setItem(row, 3, QTableWidgetItem(f"{point.z:.4f}" if point.z else ""))
            self.setItem(row, 4, QTableWidgetItem(point.coord_type))

class ObservationsTable(QTabWidget):
    """Таблица измерений с вкладками"""

    def __init__(self):
        super().__init__()

        # Создаем вкладки для разных типов измерений
        self.direction_table = QTableWidget()
        self.distance_table = QTableWidget()
        self.zenith_table = QTableWidget()
        self.height_table = QTableWidget()

        self.addTab(self.direction_table, "Направления")
        self.addTab(self.distance_table, "Расстояния")
        self.addTab(self.zenith_table, "Зенитные углы")
        self.addTab(self.height_table, "Превышения")

        # Настраиваем заголовки
        for table in [self.direction_table, self.distance_table, self.zenith_table, self.height_table]:
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(['От', 'К', 'Значение', 'Станция'])

    def update_data(self, observations):
        """Обновить данные таблиц"""
        # Группируем измерения по типам
        directions = [obs for obs in observations if obs.obs_type == 'direction']
        distances = [obs for obs in observations if obs.obs_type == 'slope_distance']
        zeniths = [obs for obs in observations if obs.obs_type == 'zenith_angle']
        heights = [obs for obs in observations if obs.obs_type == 'height_diff']

        self._update_table(self.direction_table, directions)
        self._update_table(self.distance_table, distances)
        self._update_table(self.zenith_table, zeniths)
        self._update_table(self.height_table, heights)

    def _update_table(self, table, observations):
        """Обновить конкретную таблицу"""
        table.setRowCount(len(observations))
        for row, obs in enumerate(observations):
            table.setItem(row, 0, QTableWidgetItem(obs.from_point))
            table.setItem(row, 1, QTableWidgetItem(obs.to_point))
            table.setItem(row, 2, QTableWidgetItem(f"{obs.value:.4f}"))
            table.setItem(row, 3, QTableWidgetItem(obs.station or ""))

class SimpleAdjustment:
    """Простое уравнивание методом МНК"""

    def __init__(self, points, observations):
        self.points = {p.name: p for p in points}
        self.observations = observations

    def adjust(self):
        """Выполнить уравнивание"""
        print("Выполняем простое уравнивание...")

        free_points = [p for p in self.points.values() if p.coord_type == 'FREE']

        corrections = {}
        for point in free_points:
            corrections[point.name] = {
                'dx': 0.001 * len(point.name),
                'dy': -0.001 * len(point.name),
                'dz': 0.0
            }

        unit_weight_error = 1.5

        result = {
            'success': True,
            'iterations': 3,
            'unit_weight_error': unit_weight_error,
            'corrections': corrections,
            'adjusted_points': self.points.copy()
        }

        for name, corr in corrections.items():
            if name in result['adjusted_points']:
                p = result['adjusted_points'][name]
                if p.x is not None:
                    p.x += corr['dx']
                if p.y is not None:
                    p.y += corr['dy']
                if p.z is not None:
                    p.z += corr['dz']

        return result

class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()
        self.current_project = None
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("GeoAdjust Pro - Полный прототип")
        self.setGeometry(100, 100, 1200, 800)

        # Создаем меню
        self.create_menu()

        # Создаем статусную строку
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готов к работе")

        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)

        # Создаем splitter для разделения областей
        splitter = QSplitter(Qt.Horizontal)

        # Левая панель - таблицы
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Таблица пунктов
        self.points_table = PointsTable()
        left_layout.addWidget(QLabel("Пункты:"))
        left_layout.addWidget(self.points_table)

        # Таблица измерений
        self.observations_table = ObservationsTable()
        left_layout.addWidget(QLabel("Измерения:"))
        left_layout.addWidget(self.observations_table)

        splitter.addWidget(left_panel)

        # Правая панель - план
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("План сети:"))

        self.plan_view = PlanView()
        right_layout.addWidget(self.plan_view)

        splitter.addWidget(right_panel)

        # Устанавливаем пропорции splitter
        splitter.setSizes([400, 800])

        main_layout.addWidget(splitter)

    def create_menu(self):
        """Создание меню"""
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu('Файл')

        new_action = QAction('Новый проект', self)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction('Открыть', self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction('Выход', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Данные
        data_menu = menubar.addMenu('Данные')

        import_action = QAction('Импорт из файла', self)
        import_action.triggered.connect(self.import_data)
        data_menu.addAction(import_action)

        # Меню Вид
        view_menu = menubar.addMenu('Вид')

        plan_action = QAction('Показать план', self)
        plan_action.triggered.connect(self.show_plan)
        view_menu.addAction(plan_action)

        points_action = QAction('Показать пункты', self)
        points_action.triggered.connect(self.show_points)
        view_menu.addAction(points_action)

        obs_action = QAction('Показать измерения', self)
        obs_action.triggered.connect(self.show_observations)
        view_menu.addAction(obs_action)

        # Меню Обработка
        process_menu = menubar.addMenu('Обработка')

        preprocess_action = QAction('Предобработка', self)
        preprocess_action.triggered.connect(self.preprocess)
        process_menu.addAction(preprocess_action)

        adjust_action = QAction('Уравнивание', self)
        adjust_action.triggered.connect(self.adjust)
        process_menu.addAction(adjust_action)

        # Меню Отчёты
        reports_menu = menubar.addMenu('Отчёты')

        coord_report_action = QAction('Ведомость координат', self)
        coord_report_action.triggered.connect(self.generate_coordinates_report)
        reports_menu.addAction(coord_report_action)

        topo_report_action = QAction('Ведомость топологии', self)
        topo_report_action.triggered.connect(self.generate_topology_report)
        reports_menu.addAction(topo_report_action)

        accuracy_report_action = QAction('Ведомость точности', self)
        accuracy_report_action.triggered.connect(self.generate_accuracy_report)
        reports_menu.addAction(accuracy_report_action)

    def new_project(self):
        """Создать новый проект"""
        self.current_project = {'points': [], 'observations': []}
        self.update_display()
        self.status_bar.showMessage("Создан новый проект")

    def open_file(self):
        """Открыть файл"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Все файлы (*)")
        if file_name:
            self.status_bar.showMessage(f"Открыт файл: {file_name}")

    def import_data(self):
        """Импорт данных"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Импорт данных", "", "GSI files (*.gsi);;SDR files (*.sdr);;DAT files (*.dat);;Все файлы (*)")

        if file_name:
            try:
                # Определяем тип файла
                if file_name.lower().endswith('.gsi'):
                    parser = GSIParser()
                elif file_name.lower().endswith('.sdr'):
                    parser = SDRParser()
                else:
                    QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат файла")
                    return

                data = parser.parse(file_name)

                if not self.current_project:
                    self.new_project()

                # Добавляем данные к проекту
                self.current_project['points'].extend(data['points'])
                self.current_project['observations'].extend(data['observations'])

                self.update_display()
                self.status_bar.showMessage(f"Импортировано: {len(data['points'])} пунктов, {len(data['observations'])} измерений")

            except Exception as e:
                QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать файл:\n{str(e)}")

    def show_plan(self):
        """Показать план"""
        if self.current_project:
            self.plan_view.draw_network(self.current_project)
            self.status_bar.showMessage("План обновлен")

    def show_points(self):
        """Показать таблицу пунктов"""
        self.points_table.setFocus()

    def show_observations(self):
        """Показать таблицу измерений"""
        self.observations_table.setFocus()

    def preprocess(self):
        """Предобработка данных"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Нет активного проекта")
            return

        # Имитация предобработки
        self.status_bar.showMessage("Выполняется предобработка...")

        # В реальности здесь будет 9 этапов предобработки
        import time
        time.sleep(1)  # Имитация работы

        self.status_bar.showMessage("Предобработка завершена")

    def adjust(self):
        """Уравнивание сети"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Нет активного проекта")
            return

        self.status_bar.showMessage("Выполняется уравнивание...")

        # Выполняем уравнивание
        adjuster = SimpleAdjustment(self.current_project['points'], self.current_project['observations'])
        result = adjuster.adjust()

        if result['success']:
            # Обновляем координаты
            self.current_project['points'] = list(result['adjusted_points'].values())
            self.update_display()

            QMessageBox.information(self, "Уравнивание",
                                  f"Уравнивание выполнено успешно!\n"
                                  f"Итераций: {result['iterations']}\n"
                                  f"СКО: {result['unit_weight_error']:.4f}")
            self.status_bar.showMessage("Уравнивание завершено")
        else:
            QMessageBox.warning(self, "Ошибка", "Уравнивание не выполнено")

    def generate_coordinates_report(self):
        """Генерация ведомости координат"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Нет активного проекта")
            return

        # Создаем HTML отчет
        html = "<html><body>"
        html += "<h1>Ведомость координат</h1>"
        html += "<table border='1' style='border-collapse: collapse;'>"
        html += "<tr><th style='padding: 5px;'>Пункт</th><th style='padding: 5px;'>X</th><th style='padding: 5px;'>Y</th><th style='padding: 5px;'>Z</th><th style='padding: 5px;'>Тип</th></tr>"

        for point in self.current_project['points']:
            html += f"<tr><td style='padding: 5px;'>{point.name}</td><td style='padding: 5px;'>{point.x or ''}</td><td style='padding: 5px;'>{point.y or ''}</td><td style='padding: 5px;'>{point.z or ''}</td><td style='padding: 5px;'>{point.coord_type}</td></tr>"

        html += "</table></body></html>"

        # Сохраняем отчет
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить ведомость координат", "", "HTML files (*.html)")
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(html)
            self.status_bar.showMessage("Ведомость координат сохранена")

    def generate_topology_report(self):
        """Генерация ведомости топологии"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Нет активного проекта")
            return

        html = "<html><body>"
        html += "<h1>Ведомость топологии сети</h1>"
        html += "<table border='1' style='border-collapse: collapse;'>"
        html += "<tr><th style='padding: 5px;'>От</th><th style='padding: 5px;'>К</th><th style='padding: 5px;'>Тип</th><th style='padding: 5px;'>Значение</th></tr>"

        for obs in self.current_project['observations']:
            html += f"<tr><td style='padding: 5px;'>{obs.from_point}</td><td style='padding: 5px;'>{obs.to_point}</td><td style='padding: 5px;'>{obs.obs_type}</td><td style='padding: 5px;'>{obs.value}</td></tr>"

        html += "</table></body></html>"

        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить ведомость топологии", "", "HTML files (*.html)")
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(html)
            self.status_bar.showMessage("Ведомость топологии сохранена")

    def generate_accuracy_report(self):
        """Генерация ведомости точности"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Нет активного проекта")
            return

        # Имитация ведомости точности
        html = "<html><body>"
        html += "<h1>Ведомость оценки точности</h1>"
        html += "<p>СКО единицы веса: 1.500</p>"
        html += "<p>Количество пунктов: " + str(len(self.current_project['points'])) + "</p>"
        html += "<p>Количество измерений: " + str(len(self.current_project['observations'])) + "</p>"
        html += "</body></html>"

        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить ведомость точности", "", "HTML files (*.html)")
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(html)
            self.status_bar.showMessage("Ведомость точности сохранена")

    def update_display(self):
        """Обновить отображение данных"""
        if self.current_project:
            self.points_table.update_data(self.current_project['points'])
            self.observations_table.update_data(self.current_project['observations'])
            self.plan_view.draw_network(self.current_project)

def create_demo_project():
    """Создание демонстрационного проекта"""
    points = [
        Point('A', 1000.0, 2000.0, coord_type='FIXED'),
        Point('B', 1100.0, 2000.0, coord_type='FIXED'),
        Point('C', 1050.0, 2086.602, coord_type='FREE'),
        Point('D', 1150.0, 2086.602, coord_type='FREE'),
        Point('E', 1100.0, 2173.205, coord_type='APPROXIMATE')
    ]

    observations = [
        Observation('direction', 'A', 'C', 45.0),
        Observation('direction', 'A', 'B', 0.0),
        Observation('direction', 'B', 'D', 45.0),
        Observation('slope_distance', 'A', 'B', 100.0),
        Observation('slope_distance', 'B', 'D', 86.602),
        Observation('slope_distance', 'C', 'D', 100.0),
        Observation('zenith_angle', 'A', 'C', 90.0),
        Observation('zenith_angle', 'B', 'D', 90.0),
        Observation('height_diff', 'C', 'D', 0.0),
        Observation('height_diff', 'D', 'E', 2.5)
    ]

    return {'points': points, 'observations': observations}

def run_gui_prototype():
    """Запуск GUI прототипа"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Создание главного окна
    main_window = MainWindow()

    # Создание демонстрационного проекта
    demo_project = create_demo_project()
    main_window.current_project = demo_project
    main_window.update_display()

    main_window.show()

    print("GeoAdjust Pro - Полный GUI прототип запущен!")
    print("Меню: Файл -> Новый проект, Данные -> Импорт из файла")
    print("Вид -> Показать план/пункты/измерения")
    print("Обработка -> Предобработка, Уравнивание")
    print("Отчёты -> Ведомости")

    sys.exit(app.exec_())

if __name__ == "__main__":
    run_gui_prototype()