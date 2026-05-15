#!/usr/bin/env python3
"""Проверяет корректность замены QGraphicsView на PyQtGraph"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow

try:
    import pyqtgraph as pg
    from geoadjust.gui.components.plan_view_pyqtgraph import PlanViewPyQtGraph
except ImportError as e:
    print(f"⚠️ PyQtGraph не установлен: {e}")
    print("Установите: pip install pyqtgraph")
    sys.exit(1)

app = QApplication(sys.argv)
win = QMainWindow()
view = PlanViewPyQtGraph()
win.setCentralWidget(view)

# Имитация данных
pts = {
    "P1": type("Pt", (), {"x": 0.0, "y": 0.0, "coord_type": "FIXED"})(),
    "P2": type("Pt", (), {"x": 100.0, "y": 50.0, "coord_type": "ADJUSTED"})(),
    "P3": type("Pt", (), {"x": 50.0, "y": 80.0, "coord_type": "ADJUSTED"})(),
}
obs = [
    type("Obs", (), {"from_point_id": "P1", "to_point_id": "P2", "obs_type": "distance"})(),
    type("Obs", (), {"from_point_id": "P2", "to_point_id": "P3", "obs_type": "direction"})(),
    type("Obs", (), {"from_point_id": "P3", "to_point_id": "P1", "obs_type": "distance"})(),
]

view.update_network(pts, obs)
win.resize(800, 600)
win.show()

print("✅ План отрисован на PyQtGraph. Проверьте зум, пан и клик по точкам.")
print("Закройте окно для завершения теста.")
sys.exit(app.exec_())
