#!/usr/bin/env python3
"""
Скрипт для выполнения уравнивания всех сетей в проекте
Упрощенная версия без предобработки - используем координаты из файла
"""
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, '/workspace/GeoAdjustPro/src')

from geoadjust.io.formats.sdr import SDRParser
from geoadjust.core.network.models import NetworkPoint, CombinedObservation
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder

def process_network(sdr_file: str):
    """Обработка одной сети"""
    print(f"\n{'='*60}")
    print(f"ОБРАБОТКА СЕТИ: {os.path.basename(sdr_file)}")
    print('='*60)
    
    try:
        # 1. Парсинг SDR файла
        print("\n[1/4] Парсинг SDR файла...")
        parser = SDRParser()
        parsed_data = parser.parse(sdr_file)
        
        if not parsed_data.get('success', False):
            raise ValueError("Не удалось распарсить файл")
        
        # Преобразуем точки в NetworkPoint
        points_dict = {}
        for p in parsed_data.get('points', []):
            coord_type = 'FREE'
            if p.get('plan_status') == 'initial':
                coord_type = 'FIXED'
            elif (p.get('x', 0) and p.get('y', 0)) and (p.get('x', 0) != 0 or p.get('y', 0) != 0):
                coord_type = 'APPROXIMATE'
            
            points_dict[p['point_id']] = NetworkPoint(
                point_id=p['point_id'],
                coord_type=coord_type,
                x=p.get('x', 0.0) or 0.0,
                y=p.get('y', 0.0) or 0.0,
                h=p.get('h', 0.0) or 0.0,
                plan_status=p.get('plan_status', 'working'),
                height_status=p.get('height_status', 'working')
            )
        
        # Получаем измерения (CombinedObservation)
        observations = parsed_data.get('observations', [])
        
        print(f"  - Найдено пунктов: {len(points_dict)}")
        print(f"  - Найдено измерений: {len(observations)}")
        
        # Статистика по пунктам
        points_with_coords = sum(1 for p in points_dict.values() if p.has_plan_coords())
        points_without_coords = len(points_dict) - points_with_coords
        fixed_points = sum(1 for p in points_dict.values() if p.coord_type == 'FIXED')
        approx_points = sum(1 for p in points_dict.values() if p.coord_type == 'APPROXIMATE')
        free_points = sum(1 for p in points_dict.values() if p.coord_type == 'FREE')
        
        print(f"  - Пунктов с координатами: {points_with_coords}")
        print(f"    - FIXED (исходные): {fixed_points}")
        print(f"    - APPROXIMATE (приближенные): {approx_points}")
        print(f"    - FREE (свободные): {free_points}")
        print(f"  - Пунктов без координат: {points_without_coords}")
        
        # Если нет точек с координатами, пропускаем сеть
        if fixed_points == 0 and approx_points == 0:
            print("\n  ⚠️ ПРЕДУПРЕЖДЕНИЕ: Нет точек с координатами - уравнивание невозможно")
            return {
                'file': sdr_file,
                'status': 'SKIP',
                'reason': 'Нет точек с координатами',
                'points_count': len(points_dict),
                'measurements_count': len(observations)
            }
        
        # 2. Построение матрицы уравнений
        print("\n[2/4] Построение матрицы уравнений...")
        
        # Определяем список закрепленных пунктов (только FIXED)
        fixed_point_ids = [pid for pid, p in points_dict.items() if p.coord_type == 'FIXED']
        
        builder = EquationsBuilder()
        A, L = builder.build_adjustment_matrix(
            observations=observations,
            points=points_dict,
            fixed_points=fixed_point_ids if fixed_point_ids else None
        )
        print(f"  - Размер матрицы A: {A.shape}")
        print(f"  - Размер вектора L: {L.shape}")
        
        # 3. Уравнивание
        print("\n[3/4] Уравнивание методом МНК...")
        
        # Строим весовую матрицу
        weight_builder = WeightBuilder()
        P = weight_builder.build_weight_matrix(observations, points_dict)
        
        engine = AdjustmentEngine()
        result = engine.adjust(A, L, P)  # Передаем P как третий аргумент
        
        redundancy = A.shape[0] - A.shape[1] if len(A.shape) > 1 else 0
        sigma0 = result.get('sigma0', float('inf'))
        
        print(f"  - Количество избыточных измерений: {redundancy}")
        print(f"  - СКП единицы веса: {sigma0:.6f}")
        
        # 4. Отчет
        print("\n[4/4] Формирование отчета...")
        
        # Координаты после уравнивания
        adjusted_points = result.get('adjusted_points', {})
        print("\n  КООРДИНАТЫ ПОСЛЕ УРАВНИВАНИЯ:")
        print("  " + "-"*50)
        for pt_name, coords in sorted(adjusted_points.items()):
            if isinstance(coords, dict):
                x = coords.get('x', 0)
                y = coords.get('y', 0)
                mx = coords.get('mx', 0) * 1000  # перевод в мм
                my = coords.get('my', 0) * 1000  # перевод в мм
                print(f"  {pt_name:15} X={x:12.4f} Y={y:12.4f}  Mx={mx:7.2f}мм My={my:7.2f}мм")
        
        # Высоты после уравнивания
        adjusted_heights = result.get('adjusted_heights', {})
        if adjusted_heights:
            print("\n  ВЫСОТЫ ПОСЛЕ УРАВНИВАНИЯ:")
            print("  " + "-"*50)
            for pt_name, h_data in sorted(adjusted_heights.items()):
                if isinstance(h_data, dict):
                    h = h_data.get('h', 0)
                    mh = h_data.get('mh', 0) * 1000  # перевод в мм
                    print(f"  {pt_name:15} H={h:12.4f}  Mh={mh:7.2f}мм")
        
        # Эллипсы ошибок
        ellipses = result.get('ellipses', {})
        if ellipses:
            print("\n  ЭЛЛИПСЫ ОШИБОК:")
            print("  " + "-"*50)
            for pt_name, ellipse in sorted(ellipses.items()):
                if isinstance(ellipse, dict):
                    a = ellipse.get('a', 0) * 1000  # перевод в мм
                    b = ellipse.get('b', 0) * 1000  # перевод в мм
                    angle = ellipse.get('angle', 0)  # угол ориентации
                    print(f"  {pt_name:15} a={a:7.2f}мм b={b:7.2f}мм α={angle:6.1f}°")
        
        return {
            'file': sdr_file,
            'status': 'OK',
            'points_count': len(points_dict),
            'measurements_count': len(observations),
            'sigma0': sigma0,
            'redundancy': redundancy,
            'adjusted_points': adjusted_points,
            'adjusted_heights': adjusted_heights,
            'ellipses': ellipses
        }
        
    except Exception as e:
        print(f"\n  ❌ ОШИБКА: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'file': sdr_file,
            'status': 'ERROR',
            'error': str(e)
        }


def main():
    # Поиск всех SDR файлов
    sdr_files = []
    for root, dirs, files in os.walk('/workspace/test_real_mes'):
        for file in files:
            if file.endswith('.sdr'):
                sdr_files.append(os.path.join(root, file))
    
    if not sdr_files:
        print("SDR файлы не найдены!")
        return
    
    print(f"Найдено сетей для обработки: {len(sdr_files)}")
    
    results = []
    for sdr_file in sorted(sdr_files):
        result = process_network(sdr_file)
        results.append(result)
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ ПО ВСЕМ СЕТЯМ")
    print("="*60)
    
    success_count = sum(1 for r in results if r['status'] == 'OK')
    error_count = sum(1 for r in results if r['status'] == 'ERROR')
    skip_count = sum(1 for r in results if r['status'] == 'SKIP')
    
    print(f"\nВсего сетей: {len(results)}")
    print(f"✅ Успешно обработано: {success_count}")
    print(f"⚠️  Пропущено: {skip_count}")
    print(f"❌ С ошибками: {error_count}")
    
    print("\n" + "-"*70)
    print(f"{'Файл':<35} {'Статус':<8} {'Точек':<6} {'Измер.':<8} {'Изб.':<6} {'СКП':<10}")
    print("-"*70)
    
    for r in results:
        if r['status'] == 'OK':
            status = '✅ OK'
            sigma = f"{r.get('sigma0', 0):.6f}"
            redundancy = str(r.get('redundancy', 'N/A'))
        elif r['status'] == 'SKIP':
            status = '⚠️ SKIP'
            sigma = 'N/A'
            redundancy = 'N/A'
        else:
            status = '❌ ERROR'
            sigma = 'N/A'
            redundancy = 'N/A'
        
        file_name = os.path.basename(r['file'])[:33]
        points = str(r.get('points_count', 'N/A'))
        meas = str(r.get('measurements_count', 'N/A'))
        print(f"{file_name:<35} {status:<8} {points:<6} {meas:<8} {redundancy:<6} {sigma:<10}")
    
    print("-"*70)
    
    # Подробные результаты для успешных сетей
    ok_results = [r for r in results if r['status'] == 'OK']
    if ok_results:
        print("\n\nПОДРОБНЫЕ РЕЗУЛЬТАТЫ УСПЕШНЫХ СЕТЕЙ:")
        for r in ok_results:
            print(f"\n{'='*60}")
            print(f"Сеть: {os.path.basename(r['file'])}")
            print('='*60)
            
            if r.get('adjusted_points'):
                print("\nКоординаты после уравнивания:")
                for pt_name, coords in sorted(r['adjusted_points'].items()):
                    if isinstance(coords, dict):
                        x = coords.get('x', 0)
                        y = coords.get('y', 0)
                        mx = coords.get('mx', 0) * 1000
                        my = coords.get('my', 0) * 1000
                        print(f"  {pt_name:15} X={x:12.4f} Y={y:12.4f}  Mx={mx:6.2f}мм My={my:6.2f}мм")
            
            if r.get('ellipses'):
                print("\nЭллипсы ошибок:")
                for pt_name, ellipse in sorted(r['ellipses'].items()):
                    if isinstance(ellipse, dict):
                        a = ellipse.get('a', 0) * 1000
                        b = ellipse.get('b', 0) * 1000
                        angle = ellipse.get('angle', 0)
                        print(f"  {pt_name:15} a={a:6.2f}мм b={b:6.2f}мм α={angle:5.1f}°")


if __name__ == '__main__':
    main()
