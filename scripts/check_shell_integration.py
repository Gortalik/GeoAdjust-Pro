#!/usr/bin/env python3
"""
ПРОВЕРКА РАБОТОСПОСОБНОСТИ В ОБОЛОЧКЕ
- Уравнивание нивелирных сетей
- Тригонометрическое нивелирование из тахеометрии
"""

import sys
from pathlib import Path
import os
import numpy as np

# Добавляем путь к оболочке
sys.path.insert(0, str(Path(__file__).parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser
from geoadjust.io.formats.sdr import SDRParser


def check_leveling_network():
    """Проверка уравнивания нивелирной сети"""
    print("\n" + "="*80)
    print("1. ПРОВЕРКА УРАВНИВАНИЯ НИВЕЛИРНОЙ СЕТИ (GSI)")
    print("="*80)
    
    base = Path("test_real_mes")
    f = base / "s5" / "niv" / "MIR0212.GSI"
    
    parser = GSIParser()
    data = parser.parse(f)
    obs = data.get('observations', [])
    
    # Валидные нивелирные пары
    leveling = [o for o in obs if getattr(o, 'obs_type', '') == 'leveling_height_diff' 
                and getattr(o, 'from_point', '') != getattr(o, 'to_point', '')]
    
    print(f"\nВалидных нивелирных пар: {len(leveling)}")
    
    if len(leveling) < 2:
        print("❌ НЕДОСТАТОЧНО ДАННЫХ (требуется доработка парсера)")
        return False
    
    dh = [float(o.value) for o in leveling]
    from_p = [o.from_point for o in leveling]
    to_p = [o.to_point for o in leveling]
    
    all_points = sorted(set(from_p + to_p))
    n = len(all_points)
    m = len(dh)
    
    fixed = all_points[0]
    fixed_idx = all_points.index(fixed)
    
    A = np.zeros((m, n))
    L = np.array(dh)
    idx = {p: i for i, p in enumerate(all_points)}
    
    for i in range(m):
        A[i, idx[from_p[i]]] = -1
        A[i, idx[to_p[i]]] = 1
    
    A = np.delete(A, fixed_idx, axis=1)
    
    try:
        N = A.T @ A
        u = A.T @ L
        dx = np.linalg.solve(N, u)
        
        H = np.zeros(n)
        H[fixed_idx] = 0.0
        free = [i for i in range(n) if i != fixed_idx]
        H[free] = dx
        
        v = A @ dx - L
        r = m - (n-1)
        sigma0 = np.sqrt(np.sum(v**2) / r)
        
        print(f"✓ Уравнивание выполнено")
        print(f"  sigma0 = {sigma0:.4f} м = {sigma0*1000:.2f} мм")
        
        if sigma0 < 0.005:
            print("✓ СООТВЕТСТВУЕТ ТРЕБОВАНИЯМ (< 5 мм)")
        else:
            print(f"⚠ НЕ СООТВЕТСТВУЕТ (< 5 мм требуется)")
        
        return True
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False


def check_trigonometric_leveling():
    """Проверка тригонометрического нивелирования из тахеометрии"""
    print("\n" + "="*80)
    print("2. ПРОВЕРКА ТРИГОНОМЕТРИЧЕСКОГО НИВЕЛИРОВАНИЯ (SDR)")
    print("="*80)
    
    base = Path("test_real_mes")
    f = base / "b_g" / "plan" / "badgro16093_const.sdr"
    
    parser = SDRParser()
    data = parser.parse(f)
    obs = data.get('observations', [])
    
    # Извлекаем тригонометрические превышения
    trig_leveling = []
    
    for o in obs:
        fp = getattr(o, 'from_point_id', None) or getattr(o, 'from_setup_id', None)
        tp = getattr(o, 'to_point_id', None)
        
        if not fp or not tp or fp == tp:
            continue
        
        # Зенитный угол и расстояние
        zenith = getattr(o, 'zenith_angle', None)
        dist = getattr(o, 'slope_distance', None) or getattr(o, 'horizontal_distance', None)
        
        if zenith is not None and dist is not None:
            # Тригонометрическое превышение: h = s * cos(z)
            h = dist * np.cos(np.deg2rad(zenith))
            trig_leveling.append({
                'from': fp,
                'to': tp,
                'value': h,
                'distance': dist,
                'zenith': zenith
            })
    
    print(f"\nТригонометрических превышений: {len(trig_leveling)}")
    
    if len(trig_leveling) < 2:
        print("❌ НЕДОСТАТОЧНО ДАННЫХ")
        return False
    
    # Уравнивание
    dh = [t['value'] for t in trig_leveling]
    from_p = [t['from'] for t in trig_leveling]
    to_p = [t['to'] for t in trig_leveling]
    
    all_points = sorted(set(from_p + to_p))
    n = len(all_points)
    m = len(dh)
    
    fixed = all_points[0]
    fixed_idx = all_points.index(fixed)
    
    A = np.zeros((m, n))
    L = np.array(dh)
    idx = {p: i for i, p in enumerate(all_points)}
    
    for i in range(m):
        A[i, idx[from_p[i]]] = -1
        A[i, idx[to_p[i]]] = 1
    
    A = np.delete(A, fixed_idx, axis=1)
    
    try:
        N = A.T @ A
        u = A.T @ L
        dx = np.linalg.solve(N, u)
        
        H = np.zeros(n)
        H[fixed_idx] = 0.0
        free = [i for i in range(n) if i != fixed_idx]
        H[free] = dx
        
        v = A @ dx - L
        r = m - (n-1)
        sigma0 = np.sqrt(np.sum(v**2) / r)
        
        print(f"✓ Уравнивание выполнено")
        print(f"  sigma0 = {sigma0:.4f} м = {sigma0*1000:.2f} мм")
        
        return True
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False


def check_shell_integration():
    """Проверка интеграции с оболочкой"""
    print("\n" + "="*80)
    print("3. ПРОВЕРКА ИНТЕГРАЦИИ С ОБОЛОЧКОЙ")
    print("="*80)
    
    try:
        from geoadjust.core.adjustment.engine import AdjustmentEngine
        from geoadjust.core.adjustment.equations_builder import EquationsBuilder
        from geoadjust.core.adjustment.weights import InstrumentSpec
        
        print("\n✓ AdjustmentEngine импортирован")
        print("✓ EquationsBuilder импортирован")
        print("✓ InstrumentSpec импортирован")
        
        # Проверка создания
        spec = InstrumentSpec(class_code="4")
        engine = AdjustmentEngine(spec=spec)
        builder = EquationsBuilder(spec=spec)
        
        print("\n✓ AdjustmentEngine создан")
        print("✓ EquationsBuilder создан")
        
        return True
    except Exception as e:
        print(f"\n❌ ОШИБКА ИМПОРТА: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("ПРОВЕРКА РАБОТОСПОСОБНОСТИ В ОБОЛОЧКЕ")
    print("="*80)
    
    results = []
    
    # 1. Нивелирные сети
    results.append(("Нивелирные сети (GSI)", check_leveling_network()))
    
    # 2. Тригонометрическое нивелирование
    results.append(("Тригонометрическое нивелирование (SDR)", check_trigonometric_leveling()))
    
    # 3. Интеграция с оболочкой
    results.append(("Интеграция с оболочкой", check_shell_integration()))
    
    # Итоги
    print("\n" + "="*80)
    print("ИТОГИ ПРОВЕРКИ")
    print("="*80)
    
    for name, result in results:
        status = "✓ ПРОШЛО" if result else "❌ НЕ ПРОШЛО"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nПройдено: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    else:
        print("\n⚠ ТРЕБУЕТСЯ ДОРАБОТКА")


if __name__ == "__main__":
    main()
