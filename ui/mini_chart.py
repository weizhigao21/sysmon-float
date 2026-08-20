"""迷你折线图组件"""

from typing import Optional, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from config import CONFIG


class MiniChart(QWidget):
    """用于展示最近历史数据的迷你折线图"""

    def __init__(self, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._data: list[float] = []
        self.setMinimumHeight(24)
        self.setMaximumHeight(32)

    def set_data(self, data: Sequence[float]) -> None:
        """更新图表数据"""
        self._data = list(data)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 单点数据：绘制一个圆点
        if len(self._data) == 1:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._color)
            x = int(width / 2)
            y = height - 2 - int((max(0.0, min(100.0, self._data[0])) / 100.0) * (height - 4))
            radius = 2
            painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)
            painter.end()
            return

        if len(self._data) < 2:
            return

        pen = QPen(self._color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        step_x = width / (len(self._data) - 1)
        points = []
        for i, value in enumerate(self._data):
            x = int(i * step_x)
            # value 范围 0~100，映射到高度（留 2px 边距）
            y = height - 2 - int((max(0.0, min(100.0, value)) / 100.0) * (height - 4))
            points.append((x, y))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        painter.end()
