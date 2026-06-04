#!/usr/bin/env python3
"""
Генерация схемы сети в виде изображения
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("terrain_plotter")

def read_coordinates(file_path):
    """Чтение координат из ведомости"""
    points = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line and ':' in line and 'H = ' in line:
                try:
                    # Пример: GR4: H = 100.123 м, sigma = 0.001000 м
                    parts = line.split(':')
                    if len(parts) >= 2:
                        point_id = parts[0].strip()
                        if 'H = ' in parts[1]:
                            h_part = parts[1].split('H = ')[1]
                            h_value = float(h_part.split(' м')[0].strip())
                            points[point_id] = h_value
                except Exception as e:
                    continue
    except Exception as e:
        logger.error(f"Ошибка чтения файла: {e}")
    
    return points

def generate_terrain_map(points, output_path):
    """Генерация карты местности с высотами"""
    if not points:
        logger.error("Нет данных для построения")
        return
    
    plt.figure(figsize=(15, 10))
    
    # Генерируем случайные планы координаты для наглядности
    # В реальном проекте здесь должны быть реальные X,Y координаты
    x_coords = np.random.uniform(0, 1000, len(points))
    y_coords = np.random.uniform(0, 1000, len(points))
    
    # Сортируем по высоте для цветовой шкалы
    sorted_points = sorted(points.items(), key=lambda x: x[1])
    point_ids = [p[0] for p in sorted_points]
    heights = [p[1] for p in sorted_points]
    
    # Цветовая палитра
    colors = plt.cm.terrain(np.linspace(0, 1, len(heights)))
    
    # Построение точек
    for i, (x, y, h, color, point_id) in enumerate(zip(x_coords, y_coords, heights, colors, point_ids)):
        plt.scatter(x, y, c=[color], s=200, alpha=0.8, edgecolors='black', linewidth=1)
        plt.annotate(f'{point_id}\n{h:.2f}', (x, y), xytext=(5, 5), 
                    textcoords='offset points', fontsize=8, ha='left')
    
    # Добавление цветовой шкалы
    sm = plt.cm.ScalarMappable(cmap=plt.cm.terrain, norm=plt.Normalize(vmin=min(heights), vmax=max(heights)))
    sm.set_array([])
    cbar = plt.colorbar(sm, shrink=0.8)
    cbar.set_label('Высота, м', rotation=270, labelpad=20)
    
    # Сетка с шагом 10м по высоте
    plt.grid(True, alpha=0.3)
    
    # Заголовок
    plt.title('Геодезическая сеть - Схема высот', fontsize=16, fontweight='bold')
    plt.xlabel('X (метры)', fontsize=12)
    plt.ylabel('Y (метры)', fontsize=12)
    
    # Легенда
    plt.figtext(0.02, 0.02, f'Дата: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                             f'Пунктов: {len(points)}\n'
                             f'Диапазон высот: {min(heights):.2f} - {max(heights):.2f} м',
                fontsize=10, ha='left')
    
    # Сохранение
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"Схема сети сохранена: {output_path}")

def main():
    # Путь к ведомости координат
    coords_file = Path("test_real_mes/b_g/ведомость_координат.txt")
    output_path = Path("test_real_mes/b_g/схема_сети.png")
    
    logger.info(f"Чтение данных из: {coords_file}")
    points = read_coordinates(coords_file)
    
    if points:
        logger.info(f"Загружено {len(points)} пунктов")
        generate_terrain_map(points, output_path)
        logger.info("Готово!")
    else:
        logger.error("Не удалось загрузить данные для построения схемы")

if __name__ == "__main__":
    main()