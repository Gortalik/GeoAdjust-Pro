"""
GeoAdjustPro - Reports Module
Generates GOST-compliant reports, schemes, and error ellipses
"""
import os
import math

class GOSTReportGenerator:
    """Generator for survey reports in Russian GOST format"""
    
    def generate_coordinates_report(self, network, output_dir):
        """Generate coordinates ведомость"""
        filepath = os.path.join(output_dir, 'ведомость_координат.txt')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("ВЕДОМОСТЬ КООРДИНАТ ПУНКТОВ\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"{'№':<5} {'Наименование':<20} {'X (м)':<15} {'Y (м)':<15} {'Статус плана':<15}\n")
            f.write("-" * 80 + "\n")
            
            for i, (name, point) in enumerate(network.points.items(), 1):
                x_str = f"{point.x:.4f}" if point.x is not None else "-"
                y_str = f"{point.y:.4f}" if point.y is not None else "-"
                f.write(f"{i:<5} {name:<20} {x_str:<15} {y_str:<15} {point.plan_status:<15}\n")
        
        return filepath
    
    def generate_heights_report(self, network, output_dir):
        """Generate heights ведомость"""
        filepath = os.path.join(output_dir, 'ведомость_высот.txt')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("ВЕДОМОСТЬ ВЫСОТ ПУНКТОВ\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"{'№':<5} {'Наименование':<20} {'Высота (м)':<15} {'СКП (мм)':<15} {'Статус высоты':<15}\n")
            f.write("-" * 80 + "\n")
            
            for i, (name, point) in enumerate(network.points.items(), 1):
                h_str = f"{point.h:.4f}" if point.h is not None else "-"
                h_std = getattr(point, 'h_std', None)
                h_std_str = f"{h_std:.2f}" if h_std is not None else "-"
                f.write(f"{i:<5} {name:<20} {h_str:<15} {h_std_str:<15} {point.height_status:<15}\n")
        
        return filepath
    
    def generate_error_ellipses(self, network, output_dir):
        """Generate error ellipses report"""
        filepath = os.path.join(output_dir, 'эллипсы_ошибок.txt')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("ЭЛЛИПСЫ ОШИБОК ПУНКТОВ\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"{'№':<5} {'Наименование':<20} {'A (мм)':<12} {'B (мм)':<12} {'Ориент. (°)':<12} {'Статус':<15}\n")
            f.write("-" * 80 + "\n")
            
            for i, (name, point) in enumerate(network.points.items(), 1):
                # Расчет параметров эллипса из ковариационной матрицы
                std_x = getattr(point, 'x_std', None)
                std_y = getattr(point, 'y_std', None)
                cov_xy = getattr(point, 'xy_cov', 0)
                
                if std_x is not None and std_y is not None:
                    # Вычисление полуосей эллипса
                    # Упрощенная формула для демонстрации
                    a = max(std_x, std_y) * 2.0  # Большая полуось (95% доверительный)
                    b = min(std_x, std_y) * 2.0  # Малая полуось
                    
                    # Ориентация
                    if abs(std_x - std_y) > 0.001:
                        orientation = 45.0 if cov_xy > 0 else -45.0
                    else:
                        orientation = 0.0
                    
                    f.write(f"{i:<5} {name:<20} {a*1000:.2f}{'':<8} {b*1000:.2f}{'':<8} {orientation:<12.1f} {point.plan_status:<15}\n")
                else:
                    f.write(f"{i:<5} {name:<20} {'-':<12} {'-':<12} {'-':<12} {point.plan_status:<15}\n")
        
        return filepath
    
    def generate_network_scheme(self, network, output_dir):
        """Generate network scheme text representation"""
        filepath = os.path.join(output_dir, 'схема_сети.txt')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("СХЕМА ГЕОДЕЗИЧЕСКОЙ СЕТИ\n")
            f.write("=" * 80 + "\n\n")
            
            # Список точек
            f.write("ПУНКТЫ СЕТИ:\n")
            f.write("-" * 40 + "\n")
            fixed_plan = [p for p in network.points.values() if p.plan_status == 'fixed']
            fixed_height = [p for p in network.points.values() if p.height_status == 'fixed']
            adjusted = [p for p in network.points.values() if p.plan_status == 'adjusted']
            
            f.write(f"  Исходные (план): {len(fixed_plan)}\n")
            f.write(f"  Исходные (высота): {len(fixed_height)}\n")
            f.write(f"  Уравненные: {len(adjusted)}\n")
            f.write(f"  Всего точек: {len(network.points)}\n\n")
            
            # Измерения
            f.write("ИЗМЕРЕНИЯ В СЕТИ:\n")
            f.write("-" * 40 + "\n")
            obs_types = {}
            for obs in network.observations:
                obs_types[obs.obs_type] = obs_types.get(obs.obs_type, 0) + 1
            
            for otype, count in obs_types.items():
                f.write(f"  {otype}: {count}\n")
            
            f.write(f"  Всего измерений: {len(network.observations)}\n\n")
            
            # Топология (упрощенно)
            f.write("ТОПОЛОГИЯ (пример связей):\n")
            f.write("-" * 40 + "\n")
            connections = {}
            for obs in network.observations[:20]:  # Первые 20 для примера
                key = (obs.from_point, obs.to_point)
                if key not in connections:
                    connections[key] = []
                connections[key].append(obs.obs_type)
            
            for (p1, p2), types in list(connections.items())[:10]:
                f.write(f"  {p1} --[{', '.join(types)}]--> {p2}\n")
            
            if len(connections) > 10:
                f.write(f"  ... и еще {len(connections) - 10} связей\n")
        
        return filepath
    
    def generate_measurements_report(self, network, output_dir):
        """Generate measurements ведомость with residuals"""
        filepath = os.path.join(output_dir, 'ведомость_измерений.txt')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("ВЕДОМОСТЬ ИЗМЕРЕНИЙ И ПОПРАВОК\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"{'№':<5} {'Тип':<20} {'От':<15} {'До':<15} {'Значение':<12} {'Поправка':<12}\n")
            f.write("-" * 80 + "\n")
            
            for i, obs in enumerate(network.observations[:100], 1):  # Первые 100
                v = getattr(obs, 'residual', 0.0)  # Поправка (если есть)
                f.write(f"{i:<5} {obs.obs_type:<20} {obs.from_point:<15} {obs.to_point:<15} {obs.value:<12.4f} {v:<12.4f}\n")
            
            if len(network.observations) > 100:
                f.write(f"\n... и еще {len(network.observations) - 100} измерений\n")
        
        return filepath
