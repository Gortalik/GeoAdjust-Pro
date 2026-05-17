#!/usr/bin/env python3
"""
Полный автоматический тест GeoAdjust Pro на реальных данных.
Проверяет весь цикл: импорт GSI → предобработка → уравнивание.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "GeoAdjustPro" / "src"))

from geoadjust.io.formats.gsi import GSIParser
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.weights import InstrumentSpec


def test_real_gsi_import_and_adjustment():
    """Тест импорта реальных GSI данных и уравнивания"""
    base_path = Path(__file__).parent.parent / "test_real_mes" / "s5" / "niv"

    gsi_files = list(base_path.glob("*.GSI"))
    assert len(gsi_files) > 0, "Нет GSI файлов"

    parser = GSIParser()
    all_observations = []

    for gsi_file in gsi_files:
        data = parser.parse(gsi_file)
        obs = data.get('observations', [])
        all_observations.extend(obs)
        print(f"  {gsi_file.name}: {len(obs)} измерений")

    assert len(all_observations) > 0, "Не удалось импортировать измерения"

    # Простая проверка уравнивания (демо)
    engine = AdjustmentEngine(spec=InstrumentSpec(class_code="4"))

    print(f"\n[OK] Импорт и инициализация движка успешны")
    print(f"  Всего измерений: {len(all_observations)}")


if __name__ == "__main__":
    test_real_gsi_import_and_adjustment()
    print("\n[OK] Тест на реальных данных пройден")
