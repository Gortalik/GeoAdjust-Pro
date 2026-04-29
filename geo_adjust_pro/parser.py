"""
GeoAdjustPro - Parser Module
Supports GSI (Leica) and SDR (Sokkia) formats
"""
import re
from models import Network, NetworkPoint, Observation, NetworkData

class GSIParser:
    """Parser for Leica GSI format files (нивелирование)"""
    
    def parse_file(self, filepath):
        network = NetworkData()
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        points_data = {}
        observations = []
        current_station = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # GSI формат: каждая строка содержит несколько полей типа ..XX значение
            # Для нивелирования ключевые коды:
            # ..32 - задняя отсчет (back sight)
            # ..33 - передняя отсчет (fore sight)  
            # ..83 - превышение (height difference)
            # ..57 - расстояние
            
            # Извлекаем все поля из строки
            fields = re.findall(r'(\d{2,3})\.\.(\+|-)?(\d+)', line)
            
            if not fields:
                continue
            
            # Первый номер в строке может быть номером станции/точки
            first_code = fields[0][0]
            
            # Определяем тип записи и извлекаем данные
            dh = None
            dist = None
            back_sight = None
            fore_sight = None
            
            for code, sign, value in fields:
                val = float(value)
                if sign == '-':
                    val = -val
                
                # Масштабирование значений (GSI использует мм или 0.01мм)
                if code in ['32', '33']:  # Отсчеты по рейке (в 0.01 мм)
                    scaled_val = val / 100.0  # Перевод в мм
                    if code == '32':
                        back_sight = scaled_val
                    elif code == '33':
                        fore_sight = scaled_val
                
                elif code == '83':  # Превышение (в 0.1 мм)
                    dh = val / 10.0  # Перевод в мм
                
                elif code in ['573', '574']:  # Расстояние (в 0.1 мм)
                    dist = abs(val) / 10.0  # Перевод в мм
            
            # Если есть превышение - создаем наблюдение
            if dh is not None:
                # Генерируем имя точки на основе первого поля
                point_name = f"GSIP_{first_code}_{len(observations)}"
                
                if current_station is None:
                    current_station = f"GSIP_STATION_0"
                    if current_station not in points_data:
                        points_data[current_station] = {'x': None, 'y': None, 'h': None}
                
                # Создаем точку назначения если нет
                if point_name not in points_data:
                    points_data[point_name] = {'x': None, 'y': None, 'h': None}
                
                obs = Observation(
                    id=f"obs_{len(observations)}",
                    type='leveling_height_diff',
                    from_point=current_station,
                    to_point=point_name,
                    value=dh,  # в мм
                    distance=dist if dist else 1.0  # в мм, для веса
                )
                observations.append(obs)
                
                # Переходим к следующей станции
                current_station = point_name
        
        # Создание точек сети
        for name, data in points_data.items():
            p = NetworkPoint(id=name)
            p.x = data.get('x')
            p.y = data.get('y')
            p.h = data.get('h')
            p.plan_status = 'working' if p.x is None else 'initial'
            p.height_status = 'working' if p.h is None else 'initial'
            network.add_point(p)
        
        network.observations = observations
        
        return network


class SDRParser:
    """Parser for Sokkia SDR format files"""
    
    def parse_file(self, filepath):
        network = Network()
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        points_data = {}
        observations = []
        current_station = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Формат SDR обычно CSV-like или фиксированный
            # Пример: 1,STATION,NAME,X,Y,H
            # Или: 2,BS,TARGET,ANGLE,DIST
            
            parts = line.split(',')
            if len(parts) < 2:
                parts = line.split()
            
            if len(parts) >= 2:
                rec_type = parts[0].upper()
                
                # Точки с координатами
                if rec_type in ['1', 'POINT', 'COORD']:
                    try:
                        # Попытка распарсить координаты
                        if len(parts) >= 4:
                            name = parts[1] if len(parts) > 1 else f"SDR_{len(points_data)}"
                            x = float(parts[2]) if len(parts) > 2 else None
                            y = float(parts[3]) if len(parts) > 3 else None
                            h = float(parts[4]) if len(parts) > 4 else None
                            
                            points_data[name] = {'x': x, 'y': y, 'h': h}
                    except:
                        pass
                
                # Станция
                elif rec_type in ['STATION', 'SETUP']:
                    if len(parts) > 1:
                        current_station = parts[1]
                        if current_station not in points_data:
                            points_data[current_station] = {'x': None, 'y': None, 'h': None}
                
                # Направления/Углы
                elif rec_type in ['2', 'ANGLE', 'DIR', 'AZIMUTH']:
                    if current_station and len(parts) >= 3:
                        target = parts[2] if len(parts) > 2 else f"SDR_T{len(observations)}"
                        try:
                            angle = float(parts[3]) if len(parts) > 3 else 0.0
                            obs = Observation(
                                from_point=current_station,
                                to_point=target,
                                obs_type='direction',
                                value=angle
                            )
                            observations.append(obs)
                        except:
                            pass
                
                # Расстояния
                elif rec_type in ['3', 'DIST', 'SD']:
                    if current_station and len(parts) >= 3:
                        target = parts[2] if len(parts) > 2 else f"SDR_T{len(observations)}"
                        try:
                            dist = float(parts[3]) if len(parts) > 3 else 0.0
                            obs = Observation(
                                from_point=current_station,
                                to_point=target,
                                obs_type='slope_distance',
                                value=dist
                            )
                            observations.append(obs)
                        except:
                            pass
                
                # Комбинированные измерения
                elif rec_type in ['OBS', 'COMBINED']:
                    if current_station and len(parts) >= 4:
                        target = parts[2]
                        try:
                            angle = float(parts[3]) if len(parts) > 3 else 0.0
                            dist = float(parts[4]) if len(parts) > 4 else 0.0
                            
                            obs_angle = Observation(
                                from_point=current_station,
                                to_point=target,
                                obs_type='direction',
                                value=angle
                            )
                            obs_dist = Observation(
                                from_point=current_station,
                                to_point=target,
                                obs_type='slope_distance',
                                value=dist
                            )
                            observations.extend([obs_angle, obs_dist])
                        except:
                            pass
        
        # Создание точек
        for name, data in points_data.items():
            p = NetworkPoint(name=name)
            p.x = data.get('x')
            p.y = data.get('y')
            p.h = data.get('h')
            # Если есть координаты - initial, иначе working
            p.plan_status = 'initial' if (p.x is not None and p.y is not None) else 'working'
            p.height_status = 'initial' if p.h is not None else 'working'
            network.add_point(p)
        
        network.observations = observations
        
        return network
