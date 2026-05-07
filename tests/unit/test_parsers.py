"""Тесты для парсеров GSI, SDR, Office"""
import pytest
from pathlib import Path
from geoadjust.io.gsi import GSIParser
from geoadjust.io.sdr import SDRParser
from geoadjust.io.office import OfficeParser
from geoadjust.io.validators import validate_and_clean

@pytest.fixture
def sample_gsi_file(tmp_path):
    """Создание тестового GSI файла"""
    content = """31..08  ST1
81..08  +0.1234
32..08  ST2
81..08  -0.5678
31..08  ST2
81..08  +0.9012
32..08  ST3
"""
    file_path = tmp_path / "test.GSI"
    file_path.write_text(content, encoding="utf-8")
    return file_path

@pytest.fixture
def sample_sdr_file(tmp_path):
    """Создание тестового SDR файла"""
    content = """InstrumentSetup: Setup1
Station: ST1
Target: ST2
HeightDiff: 0.1234
Distance: 50.0
Station: ST2
Target: ST3
HeightDiff: -0.5678
Distance: 75.5
"""
    file_path = tmp_path / "test.DAT"
    file_path.write_text(content, encoding="utf-8")
    return file_path

def test_gsi_parser(sample_gsi_file):
    """Парсинг GSI файла"""
    parser = GSIParser()
    obs = parser.parse(sample_gsi_file)
    
    assert len(obs) > 0
    assert all(o.station_id is not None for o in obs)
    assert all(o.type.value == "leveling" for o in obs)

def test_sdr_parser(sample_sdr_file):
    """Парсинг SDR файла"""
    parser = SDRParser()
    obs = parser.parse(sample_sdr_file)
    
    assert len(obs) > 0
    assert all(o.setup_id == "Setup1" for o in obs)

def test_validator_removes_duplicates():
    """Валидатор удаляет дубликаты"""
    from geoadjust.io.base import Observation, ObsType
    
    obs_list = [
        Observation("A", "B", 0.1, type=ObsType.LEVELING),
        Observation("A", "B", 0.2, type=ObsType.LEVELING),  # Дубликат
        Observation("B", "C", 0.3, type=ObsType.LEVELING),
    ]
    
    cleaned, report = validate_and_clean(obs_list)
    
    assert report["removed_duplicates"] == 1
    assert len(cleaned) == 2

def test_validator_removes_self_loops():
    """Валидатор удаляет самопетли"""
    from geoadjust.io.base import Observation, ObsType
    
    obs_list = [
        Observation("A", "A", 0.0, type=ObsType.LEVELING),  # Самопетля
        Observation("A", "B", 0.1, type=ObsType.LEVELING),
    ]
    
    cleaned, report = validate_and_clean(obs_list)
    
    assert report["removed_self_loops"] == 1
    assert len(cleaned) == 1
