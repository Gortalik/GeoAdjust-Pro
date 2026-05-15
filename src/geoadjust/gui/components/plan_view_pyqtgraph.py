# src/geoadjust/gui/components/plan_view_pyqtgraph.py
"""Быстрый визуализатор геодезической сети на базе PyQtGraph."""
from typing import Any, Dict, List

import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication


class PlanViewPyQtGraph(pg.GraphicsLayoutWidget):
    """GPU-ускоренный виджет для отрисовки плана геодезической сети."""
    point_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot = self.addPlot(row=0, col=0)
        self.plot.setAspectLocked()
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.getViewBox().invertY(True)  # Геодезическая ориентация (Y вверх)

        self.points_item = pg.ScatterPlotItem(size=8, pen=pg.mkPen('w', width=0.8))
        self.lines_item = pg.PlotCurveItem(pen=pg.mkPen('b', width=1.2))

        self.plot.addItem(self.points_item)
        self.plot.addItem(self.lines_item)

        self._id_map = {}
        self._setup_interactions()

    def _setup_interactions(self):
        def on_click(plot, points):
            for pt in points:
                pid = self._id_map.get(pt.data())
                if pid:
                    self.point_clicked.emit(pid)
        self.points_item.sigClicked.connect(on_click)
        self.points_item.sigHovered.connect(self._on_point_hover)

    def _on_point_hover(self, points):
        from PyQt5.QtGui import QCursor
        if points:
            QApplication.setOverrideCursor(QCursor(13))  # PointingHandCursor
        else:
            QApplication.restoreOverrideCursor()

    def update_network(self, points: Dict[str, Any], observations: List[Any]):
        """Обновление данных сети. Вызывается из главного потока."""
        x_pts, y_pts, ids, colors = [], [], [], []
        self._id_map.clear()

        for i, (pid, pt) in enumerate(points.items()):
            if hasattr(pt, 'x') and hasattr(pt, 'y') and pt.x is not None and pt.y is not None:
                x_pts.append(pt.x)
                y_pts.append(pt.y)
                ids.append(pid)
                self._id_map[i] = pid
                coord_type = getattr(pt, 'coord_type', '')
                colors.append("r" if coord_type == "FIXED" else "g")

        if x_pts:
            self.points_item.setData(
                x=x_pts, y=y_pts, size=8,
                pen=pg.mkPen('w', width=0.8),
                brush=colors,
                data=range(len(x_pts))
            )
        else:
            self.points_item.setData(x=[], y=[])

        # Линии наблюдений
        x_obs, y_obs = [], []
        for obs in observations:
            from_id = getattr(obs, 'from_point_id', None)
            to_id = getattr(obs, 'to_point_id', None)
            if from_id and to_id:
                p1 = points.get(from_id)
                p2 = points.get(to_id)
                if p1 and p2 and hasattr(p1, 'x') and hasattr(p2, 'x') and p1.x is not None:
                    x_obs.extend([p1.x, p2.x, None])  # None разрывает линию
                    y_obs.extend([p1.y, p2.y, None])

        if x_obs:
            self.lines_item.setData(x=x_obs, y=y_obs)
        else:
            self.lines_item.setData(x=[], y=[])

        self.plot.autoRange(padding=0.1)
