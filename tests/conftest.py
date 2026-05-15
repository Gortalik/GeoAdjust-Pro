import os
import sys
from pathlib import Path
import pytest

# Добавляем src в PYTHON_PATH
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Headless Qt для CI и фоновых прогонов
os.environ["QT_QPA_PLATFORM"] = "offscreen"

@pytest.fixture
def mock_ctx():
    """Фикстура валидного контекста"""
    from geoadjust.core.processing_context import ProcessingContext
    return ProcessingContext(
        observations=[],
        points={"P1": type("Pt", (), {"x":100.0, "y":200.0, "coord_type":"FIXED"})()},
        fixed_points=["P1"],
        config={"default_sigma": 0.005}
    )
