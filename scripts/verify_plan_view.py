#!/usr/bin/env python3
"""Проверяет корректность замены QGraphicsView на PyQtGraph"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from geoadjust.gui.components.plan_view_pyqtgraph import PlanViewPyQtGraph

app = QApplication(sys.argv)
win = QMainWindow()
view = PlanViewPyQtGraph()
win.setCentralWidget(view)

# Имитация данных
pts = {
    "P1": type("Pt", (), {"x": 0.0, "y": 0.0, "coord_type": "FIXED"})(),
    "P2": type("Pt", (), {"x": 100.0, "y": 50.0, "coord_type": "ADJUSTED"})(),
}
obs = [
    type("Obs", (), {"from_point_id": "P1", "to_point_id": "P2", "obs_type": "distance"})()
]

view.update_network(pts, obs)
win.resize(800, 600)
win.show()

print("✅ План отрисован на PyQtGraph. Проверьте зум, пан и клик по точкам.")
sys.exit(app.exec_())
