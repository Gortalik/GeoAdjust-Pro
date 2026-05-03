#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoAdjustPro - Визуализация сети (подобно DynAdjust)
Создает карты сети с цветовой индикацией точек и измерений
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import os

class NetworkVisualizer:
    """Визуализатор геодезической сети"""

    def __init__(self):
        self.colors = {
            'fixed': 'red',
            'initial': 'blue',
            'working': 'green',
            'adjusted': 'purple'
        }

        self.markers = {
            'fixed': 's',      # square
            'initial': 'o',    # circle
            'working': '^',    # triangle
            'adjusted': 'D'    # diamond
        }

    def plot_network(self, points, observations, title="Геодезическая сеть", save_path=None):
        """
        Создает карту сети с точками и измерениями

        Параметры:
        - points: словарь точек {id: point_data}
        - observations: список наблюдений
        - title: заголовок графика
        - save_path: путь для сохранения (опционально)
        """
        fig, ax = plt.subplots(figsize=(12, 8))

        # Определяем границы
        x_coords = []
        y_coords = []

        for pid, p in points.items():
            if p.get('x') is not None and p.get('y') is not None:
                x_coords.append(p['x'])
                y_coords.append(p['y'])

        if not x_coords:
            # Если нет координат, создаем сетку на основе связей
            self._plot_topology_only(ax, points, observations)
        else:
            # Отрисовка измерений
            self._plot_observations(ax, observations, points)

            # Отрисовка точек
            self._plot_points(ax, points)

            # Настройка осей
            if x_coords and y_coords:
                margin = 0.1 * max(max(x_coords) - min(x_coords), max(y_coords) - min(y_coords))
                ax.set_xlim(min(x_coords) - margin, max(x_coords) + margin)
                ax.set_ylim(min(y_coords) - margin, max(y_coords) + margin)

        # Настройки графика
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('X координата (м)', fontsize=12)
        ax.set_ylabel('Y координата (м)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        # Легенда
        self._add_legend(ax, points)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Карта сохранена: {save_path}")
        else:
            plt.show()

    def _plot_points(self, ax, points):
        """Отрисовка точек с цветовой индикацией"""
        for pid, p in points.items():
            x = p.get('x', 0)
            y = p.get('y', 0)
            status = p.get('plan_status', 'working')

            color = self.colors.get(status, 'gray')
            marker = self.markers.get(status, 'o')

            # Размер маркера зависит от типа точки
            size = 100 if status == 'fixed' else 80

            ax.scatter(x, y, c=color, marker=marker, s=size, alpha=0.8, edgecolors='black', linewidth=1)

            # Подпись точки
            ax.annotate(pid, (x, y), xytext=(3, 3), textcoords='offset points',
                       fontsize=8, bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

    def _plot_observations(self, ax, observations, points):
        """Отрисовка измерений линиями"""
        # Группировка по типам
        directions = [obs for obs in observations if obs.get('type') == 'direction']
        distances = [obs for obs in observations if obs.get('type') == 'distance']

        # Отрисовка направлений (красные линии)
        for obs in directions[:50]:  # Ограничиваем для читаемости
            from_pt = obs.get('from_point')
            to_pt = obs.get('to_point')

            if from_pt in points and to_pt in points:
                p1 = points[from_pt]
                p2 = points[to_pt]

                x1 = p1.get('x', 0)
                y1 = p1.get('y', 0)
                x2 = p2.get('x', 0)
                y2 = p2.get('y', 0)

                ax.plot([x1, x2], [y1, y2], 'r-', alpha=0.3, linewidth=1)

        # Отрисовка расстояний (синие линии)
        for obs in distances[:50]:  # Ограничиваем для читаемости
            from_pt = obs.get('from_point')
            to_pt = obs.get('to_point')

            if from_pt in points and to_pt in points:
                p1 = points[from_pt]
                p2 = points[to_pt]

                x1 = p1.get('x', 0)
                y1 = p1.get('y', 0)
                x2 = p2.get('x', 0)
                y2 = p2.get('y', 0)

                ax.plot([x1, x2], [y1, y2], 'b-', alpha=0.5, linewidth=2)

    def _plot_topology_only(self, ax, points, observations):
        """Отрисовка топологии сети без координат"""
        # Создаем фиктивные координаты на основе связей
        positions = self._compute_positions_from_topology(points, observations)

        # Отрисовка измерений
        for obs in observations:
            from_pt = obs.get('from_point')
            to_pt = obs.get('to_point')

            if from_pt in positions and to_pt in positions:
                x1, y1 = positions[from_pt]
                x2, y2 = positions[to_pt]

                color = 'red' if obs.get('type') == 'direction' else 'blue'
                alpha = 0.3 if obs.get('type') == 'direction' else 0.5
                linewidth = 1 if obs.get('type') == 'direction' else 2

                ax.plot([x1, x2], [y1, y2], color=color, alpha=alpha, linewidth=linewidth)

        # Отрисовка точек
        for pid, (x, y) in positions.items():
            p = points[pid]
            status = p.get('plan_status', 'working')

            color = self.colors.get(status, 'gray')
            marker = self.markers.get(status, 'o')
            size = 100 if status == 'fixed' else 80

            ax.scatter(x, y, c=color, marker=marker, s=size, alpha=0.8,
                      edgecolors='black', linewidth=1)

            ax.annotate(pid, (x, y), xytext=(3, 3), textcoords='offset points',
                       fontsize=8, bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

    def _compute_positions_from_topology(self, points, observations):
        """Вычисление позиций точек на основе топологии (алгоритм размещения графа)"""
        # Простой алгоритм размещения: случайные позиции с оптимизацией
        n_points = len(points)
        positions = {}

        # Инициализация случайными позициями
        np.random.seed(42)  # Для воспроизводимости
        for i, pid in enumerate(points.keys()):
            angle = 2 * np.pi * i / n_points
            radius = 10
            positions[pid] = (radius * np.cos(angle), radius * np.sin(angle))

        # Простая оптимизация (итеративное улучшение)
        for _ in range(10):
            forces = {pid: np.array([0.0, 0.0]) for pid in points.keys()}

            # Силы отталкивания
            for pid1 in points.keys():
                for pid2 in points.keys():
                    if pid1 != pid2:
                        dx = positions[pid1][0] - positions[pid2][0]
                        dy = positions[pid1][1] - positions[pid2][1]
                        dist = np.sqrt(dx**2 + dy**2)
                        if dist > 0:
                            force = 50 / (dist**2)  # Отталкивание
                            forces[pid1][0] += force * dx / dist
                            forces[pid1][1] += force * dy / dist

            # Силы притяжения от связей
            for obs in observations:
                from_pt = obs.get('from_point')
                to_pt = obs.get('to_point')

                if from_pt in positions and to_pt in positions:
                    dx = positions[to_pt][0] - positions[from_pt][0]
                    dy = positions[to_pt][1] - positions[from_pt][1]
                    dist = np.sqrt(dx**2 + dy**2)

                    if dist > 0:
                        force = dist * 0.1  # Притяжение
                        forces[from_pt][0] += force * dx / dist
                        forces[from_pt][1] += force * dy / dist
                        forces[to_pt][0] -= force * dx / dist
                        forces[to_pt][1] -= force * dy / dist

            # Применение сил
            for pid in points.keys():
                positions[pid] = (
                    positions[pid][0] + forces[pid][0] * 0.01,
                    positions[pid][1] + forces[pid][1] * 0.01
                )

        return positions

    def _add_legend(self, ax, points):
        """Добавление легенды"""
        legend_elements = []

        # Собираем уникальные статусы
        statuses = set()
        for p in points.values():
            statuses.add(p.get('plan_status', 'working'))

        for status in sorted(statuses):
            color = self.colors.get(status, 'gray')
            marker = self.markers.get(status, 'o')
            label = f"{status.capitalize()} points"
            legend_elements.append(
                plt.Line2D([0], [0], marker=marker, color='w', markerfacecolor=color,
                          markersize=10, label=label)
            )

        # Линии измерений
        legend_elements.extend([
            plt.Line2D([0], [0], color='red', alpha=0.5, linewidth=1, label='Directions'),
            plt.Line2D([0], [0], color='blue', alpha=0.7, linewidth=2, label='Distances')
        ])

        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

def visualize_network(points, observations, title="Геодезическая сеть", output_dir=None):
    """
    Создает визуализацию геодезической сети

    Параметры:
    - points: словарь точек
    - observations: список наблюдений
    - title: заголовок
    - output_dir: директория для сохранения (опционально)
    """
    visualizer = NetworkVisualizer()

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "network_plot.png")
    else:
        save_path = None

    visualizer.plot_network(points, observations, title=title, save_path=save_path)

    return visualizer

if __name__ == "__main__":
    print("GeoAdjustPro Network Visualizer loaded.")
    print("Ready to create network plots like DynAdjust.")