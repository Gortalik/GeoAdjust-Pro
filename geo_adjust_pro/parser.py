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
    """Parser for Sokkia SDR format files (плановая сеть)
    
    Формат SDR33 использует фиксированные поля:
    - 01NM: Заголовок файла
    - 02NM: Координаты станции (X, Y, H)
    - 05NM: Высота инструмента/цели
    - 07NM: Станция + направление
    - 09F1/F2: Наблюдения (горизонтальный угол, зенитное расстояние, расстояние)
    - 13TS: Метка времени
    """
    
    def parse_file(self, filepath):
        network = NetworkData()
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        points_data = {}
        observations = []
        current_station = None
        inst_height = 1.5  # По умолчанию
        target_height = 1.5
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Определяем тип записи по первым символам
            rec_code = line[:4] if len(line) >= 4 else line[:2]
            
            # 02NM - координаты станции: 02NM[имя][X][Y][H]
            if rec_code == '02NM':
                rest = line[4:].strip()
                parts = rest.split()
                if len(parts) >= 4:
                    name = parts[0]
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        h = float(parts[3]) if len(parts) > 3 else None
                        points_data[name] = {'x': x, 'y': y, 'h': h}
                        current_station = name
                    except ValueError:
                        pass
            
            # 05NM - высота инструмента и цели: 05NM[inst_h][target_h]
            elif rec_code == '05NM':
                rest = line[4:].strip()
                parts = rest.split()
                if len(parts) >= 2:
                    try:
                        inst_height = float(parts[0])
                        target_height = float(parts[1])
                    except ValueError:
                        pass
            
            # 07NM - установка на станцию с начальным направлением: 07NM[станция][target][angle]
            elif rec_code == '07NM':
                rest = line[4:].strip()
                parts = rest.split()
                if len(parts) >= 1:
                    current_station = parts[0]
                    if current_station not in points_data:
                        points_data[current_station] = {'x': None, 'y': None, 'h': None}
            
            # 09F1 / 09F2 - наблюдения: 09F[номер][станция(12)][target(12)][Hz(16)][V(16)][Dist(16)]
            elif rec_code in ['09F1', '09F2']:
                if current_station:
                    rest = line[4:].strip()
                    # Формат SDR33: фиксированная ширина полей
                    # station(12) target(12) Hz(16) V(16) Dist(16)
                    if len(rest) >= 24:
                        station = rest[:12].strip()
                        target = rest[12:24].strip()
                        nums = rest[24:].strip()
                        
                        # Разделяем числа по 16 символов каждое
                        hz_angle = None
                        v_angle = None
                        dist = None
                        
                        if len(nums) >= 16:
                            try:
                                hz_angle = float(nums[:16])
                            except ValueError:
                                pass
                        if len(nums) >= 32:
                            try:
                                v_angle = float(nums[16:32])
                            except ValueError:
                                pass
                        if len(nums) >= 48:
                            try:
                                dist = float(nums[32:48])
                            except ValueError:
                                pass
                        
                        if hz_angle is not None and target:
                            # Добавляем точку цели если нет
                            if target not in points_data:
                                points_data[target] = {'x': None, 'y': None, 'h': None}
                            
                            # Создаем наблюдение направления
                            obs_dir = Observation(
                                id=f"obs_dir_{len(observations)}",
                                type='direction',
                                from_point=current_station,
                                to_point=target,
                                value=hz_angle,
                                instrument_height=inst_height,
                                target_height=target_height
                            )
                            observations.append(obs_dir)
                            
                            # Создаем наблюдение расстояния если есть
                            if dist is not None and dist > 0:
                                obs_dist = Observation(
                                    id=f"obs_dist_{len(observations)}",
                                    type='slope_distance',
                                    from_point=current_station,
                                    to_point=target,
                                    value=dist,
                                    instrument_height=inst_height,
                                    target_height=target_height
                                )
                                observations.append(obs_dist)
            
            i += 1
        
        # Создание точек сети
        for name, data in points_data.items():
            p = NetworkPoint(id=name)
            p.x = data.get('x')
            p.y = data.get('y')
            p.h = data.get('h')
            p.plan_status = 'initial' if (p.x is not None and p.y is not None) else 'working'
            p.height_status = 'initial' if p.h is not None else 'working'
            network.add_point(p)
        
        network.observations = observations
        
        return network
