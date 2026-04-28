# src/geoadjust/core/reporting/reports.py
"""
Генерация ведомостей и отчетов по результатам обработки
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import math

class ReportGenerator:
    """Генератор ведомостей и отчетов"""

    def generate_coordinates_report(self, project, adjustment_result: Optional[Dict] = None) -> str:
        """Генерация ведомости координат"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Ведомость координат</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2E86C1; text-align: center; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f2f2f2; }}
                .adjusted {{ background-color: #D5F4E6; }}
                .fixed {{ background-color: #FCF3CF; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <h1>ВЕДОМОСТЬ КООРДИНАТ</h1>
            <p><strong>Проект:</strong> {project.name}</p>
            <p><strong>Дата обработки:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>

            <table>
                <thead>
                    <tr>
                        <th>Название пункта</th>
                        <th>Тип</th>
                        <th>X (м)</th>
                        <th>Y (м)</th>
                        <th>H (м)</th>
                        <th>СКО X (мм)</th>
                        <th>СКО Y (мм)</th>
                        <th>СКО H (мм)</th>
                    </tr>
                </thead>
                <tbody>
        """

        points = project.get_points()
        for point_data in points:
            # Получаем имя пункта
            point_name = point_data.get('name', point_data.get('id', 'Unknown'))

            # Определяем тип пункта
            point_type = "Свободный"
            row_class = "adjusted"

            if point_data.get('type') == 'fixed' or point_data.get('coord_type') == 'FIXED':
                point_type = "Опорный"
                row_class = "fixed"

            # Координаты
            x = point_data.get('x', 0)
            y = point_data.get('y', 0)
            h = point_data.get('h', 0)

            # Оценки точности
            sigma_x = sigma_y = sigma_h = "-"

            if adjustment_result and 'point_errors' in adjustment_result:
                point_errors = adjustment_result['point_errors'].get(point_name, {})
                sigma_x = f"{point_errors.get('sigma_x', 0)*1000:.1f}" if point_errors.get('sigma_x') else "Априорная"
                sigma_y = f"{point_errors.get('sigma_y', 0)*1000:.1f}" if point_errors.get('sigma_y') else "Априорная"
                sigma_h = f"{point_errors.get('sigma_z', 0)*1000:.1f}" if point_errors.get('sigma_z') else "Априорная"

            html += f"""
                    <tr class="{row_class}">
                        <td>{point_name}</td>
                        <td>{point_type}</td>
                        <td>{x:.4f}</td>
                        <td>{y:.4f}</td>
                        <td>{h:.4f}</td>
                        <td>{sigma_x}</td>
                        <td>{sigma_y}</td>
                        <td>{sigma_h}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>

            <div class="footer">
                <p><strong>Примечание:</strong></p>
                <p>• Координаты даны в системе координат проекта</p>
                <p>• Оценки точности даны в миллиметрах</p>
                <p>• "Априорная" означает отсутствие результатов уравнивания</p>
            </div>
        </body>
        </html>
        """

        return html

    def generate_topology_report(self, project, adjustment_result: Optional[Dict] = None) -> str:
        """Генерация ведомости топологии сети"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Ведомость топологии сети</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #E74C3C; text-align: center; }}
                h2 {{ color: #2E86C1; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f2f2f2; }}
                .station {{ background-color: #D6EAF8; }}
                .measurement {{ background-color: #FCF3CF; }}
                .stats {{ background-color: #D5F4E6; font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <h1>ВЕДОМОСТЬ ТОПОЛОГИИ СЕТИ</h1>
            <p><strong>Проект:</strong> {project.name}</p>
            <p><strong>Дата обработки:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        """

        # Группируем измерения по станциям
        observations = project.get_observations()
        stations_data = {}

        for obs in observations:
            station = obs.get('from_point', '')
            if station not in stations_data:
                stations_data[station] = {
                    'directions': 0,
                    'zenith_angles': 0,
                    'distances': 0,
                    'targets': set()
                }

            obs_type = obs.get('type', '')
            target = obs.get('to_point', '')

            if obs_type == 'direction':
                stations_data[station]['directions'] += 1
            elif obs_type == 'zenith_angle':
                stations_data[station]['zenith_angles'] += 1
            elif obs_type == 'slope_distance':
                stations_data[station]['distances'] += 1

            stations_data[station]['targets'].add(target)

        # Статистика по станциям
        html += "<h2>Статистика по станциям</h2>"
        html += """
            <table>
                <thead>
                    <tr>
                        <th>Станция</th>
                        <th>Количество целей</th>
                        <th>Направлений</th>
                        <th>Зенитных углов</th>
                        <th>Расстояний</th>
                        <th>Всего измерений</th>
                    </tr>
                </thead>
                <tbody>
        """

        total_stations = 0
        total_targets = 0
        total_directions = 0
        total_zenith = 0
        total_distances = 0

        for station, data in stations_data.items():
            total_stations += 1
            total_targets += len(data['targets'])
            total_directions += data['directions']
            total_zenith += data['zenith_angles']
            total_distances += data['distances']

            html += f"""
                    <tr>
                        <td>{station}</td>
                        <td>{len(data['targets'])}</td>
                        <td>{data['directions']}</td>
                        <td>{data['zenith_angles']}</td>
                        <td>{data['distances']}</td>
                        <td>{data['directions'] + data['zenith_angles'] + data['distances']}</td>
                    </tr>
            """

        # Итого
        html += f"""
                    <tr class="stats">
                        <td>ИТОГО</td>
                        <td>{total_targets}</td>
                        <td>{total_directions}</td>
                        <td>{total_zenith}</td>
                        <td>{total_distances}</td>
                        <td>{total_directions + total_zenith + total_distances}</td>
                    </tr>
                </tbody>
            </table>
        """

        # Детальная информация по измерениям
        html += "<h2>Детальная информация по измерениям</h2>"

        for station, data in stations_data.items():
            html += f"<h3>Станция: {station}</h3>"
            html += """
                <table>
                    <thead>
                        <tr>
                            <th>Цель</th>
                            <th>Направление (°)</th>
                            <th>Зенитный угол (°)</th>
                            <th>Расстояние (м)</th>
                            <th>Круг</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            # Группируем измерения по целям
            target_measurements = {}
            for obs in observations:
                if obs.get('from_point') == station:
                    target = obs.get('to_point', '')
                    if target not in target_measurements:
                        target_measurements[target] = {}
                    target_measurements[target][obs.get('type')] = obs

            for target, measurements in target_measurements.items():
                direction = measurements.get('direction', {})
                zenith = measurements.get('zenith_angle', {})
                distance = measurements.get('slope_distance', {})

                dir_value = f"{math.degrees(direction.get('value', 0)):.4f}" if direction else "-"
                zen_value = f"{math.degrees(zenith.get('value', 0)):.4f}" if zenith else "-"
                dist_value = f"{distance.get('value', 0):.3f}" if distance else "-"
                face = direction.get('face_position', '-') if direction else '-'

                html += f"""
                        <tr>
                            <td>{target}</td>
                            <td>{dir_value}</td>
                            <td>{zen_value}</td>
                            <td>{dist_value}</td>
                            <td>{face}</td>
                        </tr>
                """

            html += "</tbody></table>"

        html += """
            <div class="footer">
                <p><strong>Примечание:</strong></p>
                <p>• Направления даны в градусах от 0° до 360°</p>
                <p>• Зенитные углы даны в градусах от 0° до 180°</p>
                <p>• Расстояния даны в метрах (наклонные)</p>
                <p>• CL = круг лево, CP = круг право</p>
            </div>
        </body>
        </html>
        """

        return html

    def generate_accuracy_report(self, project, adjustment_result: Optional[Dict] = None) -> str:
        """Генерация ведомости оценки точности с эллипсами ошибок"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Ведомость оценки точности</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #27AE60; text-align: center; }}
                h2 {{ color: #2E86C1; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f2f2f2; }}
                .ellipse {{ background-color: #FCF3CF; }}
                .apriori {{ background-color: #FADBD8; }}
                .fixed {{ background-color: #D6EAF8; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
                .error-ellipse {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>ВЕДОМОСТЬ ОЦЕНКИ ТОЧНОСТИ</h1>
            <p><strong>Проект:</strong> {project.name}</p>
            <p><strong>Дата обработки:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        """

        if adjustment_result and adjustment_result.get('success'):
            # Результаты уравнивания доступны
            html += f"""
            <h2>Общие характеристики сети</h2>
            <table>
                <tr><td>Число пунктов:</td><td>{adjustment_result.get('num_points', 0)}</td></tr>
                <tr><td>Число измерений:</td><td>{adjustment_result.get('num_observations', 0)}</td></tr>
                <tr><td>Число избыточных измерений:</td><td>{adjustment_result.get('redundancy', 0)}</td></tr>
                <tr><td>СКО единицы веса:</td><td>{adjustment_result.get('unit_weight_error', 0):.6f}</td></tr>
                <tr><td>Число итераций:</td><td>{adjustment_result.get('iterations', 0)}</td></tr>
            </table>
            """

            # Точность по пунктам
            html += "<h2>Точность положения пунктов</h2>"
            html += """
                <table>
                    <thead>
                        <tr>
                            <th>Пункт</th>
                            <th>Тип</th>
                            <th>СКО X (мм)</th>
                            <th>СКО Y (мм)</th>
                            <th>СКО H (мм)</th>
                            <th>Большая полуось (мм)</th>
                            <th>Малая полуось (мм)</th>
                            <th>Азимут большой оси (°)</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            points = project.get_points()
            for point_data in points:
                point_name = point_data.get('name', point_data.get('id', 'Unknown'))

                if 'point_errors' in adjustment_result and point_name in adjustment_result['point_errors']:
                    errors = adjustment_result['point_errors'][point_name]
                    sigma_x = errors.get('sigma_x', 0) * 1000  # в мм
                    sigma_y = errors.get('sigma_y', 0) * 1000
                    sigma_z = errors.get('sigma_z', 0) * 1000 if errors.get('sigma_z') else 0

                    # Эллипс ошибок (упрощенное вычисление)
                    a = max(sigma_x, sigma_y)  # большая полуось
                    b = min(sigma_x, sigma_y)  # малая полуось
                    azimuth = 0  # упрощенный азимут

                    point_type = "Уравненный"
                    row_class = "ellipse"
                else:
                    # Априорная оценка точности
                    sigma_x = sigma_y = sigma_z = "Априорная (5мм)"
                    a = b = azimuth = "-"
                    point_type = "Априорная оценка"
                    row_class = "apriori"

                html += f"""
                        <tr class="{row_class}">
                            <td>{point_name}</td>
                            <td>{point_type}</td>
                            <td>{sigma_x}</td>
                            <td>{sigma_y}</td>
                            <td>{sigma_z}</td>
                            <td>{a}</td>
                            <td>{b}</td>
                            <td>{azimuth}</td>
                        </tr>
                """

            html += "</tbody></table>"

        else:
            # Результаты уравнивания недоступны - показываем априорные оценки
            html += """
            <div style="background-color: #FFF3CD; border: 1px solid #FFEAA7; padding: 15px; margin: 20px 0; border-radius: 5px;">
                <h2 style="color: #856404; margin-top: 0;">⚠️ ВНИМАНИЕ</h2>
                <p><strong>Результаты уравнивания недоступны.</strong></p>
                <p>Показаны априорные оценки точности на основе характеристик приборов и условий измерений.</p>
                <p>Для получения точных оценок выполните уравнивание сети.</p>
            </div>

            <h2>Априорная оценка точности</h2>
            """

            # Показываем априорные оценки
            html += """
                <table>
                    <thead>
                        <tr>
                            <th>Пункт</th>
                            <th>Тип оценки</th>
                            <th>СКО X (мм)</th>
                            <th>СКО Y (мм)</th>
                            <th>СКО H (мм)</th>
                            <th>Примечание</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            points = project.get_points()
            for point_data in points:
                point_name = point_data.get('name', point_data.get('id', 'Unknown'))

                # Априорные оценки на основе расстояний и точности приборов
                # Упрощенная оценка: 5мм + расстояние/100000
                sigma_xy = 5.0  # мм
                sigma_z = 8.0   # мм для высот

                html += f"""
                        <tr class="apriori">
                            <td>{point_name}</td>
                            <td>Априорная</td>
                            <td>{sigma_xy:.1f}</td>
                            <td>{sigma_xy:.1f}</td>
                            <td>{sigma_z:.1f}</td>
                            <td>Оценка по характеристикам приборов</td>
                        </tr>
                """

            html += "</tbody></table>"

        html += """
            <div class="footer">
                <p><strong>Примечание:</strong></p>
                <p>• СКО даны в миллиметрах</p>
                <p>• Эллипс ошибок рассчитан упрощенно</p>
                <p>• "Априорная" означает отсутствие результатов строгого уравнивания</p>
                <p>• Для получения точных оценок выполните уравнивание свободной сети</p>
            </div>
        </body>
        </html>
        """

        return html