"""迷你折线图组件（支持多条数据线交叉显示）"""

from typing import Optional, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class MiniChart(QWidget):
    """用于展示最近历史数据的迷你折线图，可同时绘制多条线"""

    def __init__(self, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        # 每条线: (数据列表, 颜色)
        self._series: list[tuple[list[float], QColor]] = []
        # y 轴自适应：True 时按数据最大值动态缩放（网络双线用），
        # False 时固定 0~100（CPU/内存/GPU 用）
        self._auto_scale = False
        # 上下分区：True 时多条线纵向各占一段（第 0 条最上），各自独立缩放
        self._split = False
        self.setMinimumHeight(24)
        self.setMaximumHeight(32)

    def set_data(self, data: Sequence[float]) -> None:
        """设置单条数据线（兼容旧接口），固定 0~100 轴"""
        self._series = [(list(data), self._color)]
        self._auto_scale = False
        self._split = False
        self.update()

    def set_series(self, series: Sequence[tuple[Sequence[float], str]], split: bool = False) -> None:
        """设置多条数据线，y 轴自适应缩放

        Args:
            series: [(数据, 颜色hex), ...]，如 [([1,2,3], '#81c784'), ([4,5,6], '#ef5350')]
            split: True 时上下分区显示（第 0 条在上半区、第 1 条在下半区，各自独立缩放）
        """
        self._series = [(list(data), QColor(color)) for data, color in series]
        self._auto_scale = True
        self._split = split
        self.update()

    def _series_y_max(self, data: Sequence[float]) -> float:
        """计算单条线的 y 轴最大值（自适应）：该线峰值 × 1.15，至少 1.0"""
        peak = 1.0
        if data:
            peak = max(peak, max(data))
        return peak * 1.15

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        line_count = len(self._series)

        for idx, (data, color) in enumerate(self._series):
            # 上下分区：每条线占 height/n 的纵向区域（第 0 条最上）
            if self._split and line_count > 0:
                region_top = idx * (height / line_count)
                region_h = height / line_count
            else:
                region_top = 0.0
                region_h = float(height)
            # y 轴范围：分区模式各线独立缩放；非分区按 auto_scale 决定
            # （自适应取全局峰值 ×1.15，否则固定 0~100）
            if self._split:
                y_max = self._series_y_max(data)
            elif self._auto_scale:
                y_max = self._series_y_max(self._all_peaks())
            else:
                y_max = 100.0
            if y_max <= 0:
                y_max = 1.0

            # 单点数据：绘制一个圆点
            if len(data) == 1:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                x = int(width / 2)
                y = int(region_top + region_h - 2 - (max(0.0, min(y_max, data[0])) / y_max) * (region_h - 4))
                radius = 2
                painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)
                continue

            if len(data) < 2:
                continue

            pen = QPen(color)
            pen.setWidth(2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            step_x = width / (len(data) - 1)
            points = []
            for i, value in enumerate(data):
                x = int(i * step_x)
                # 值映射到该线所在区域高度（留 2px 边距）
                y = int(region_top + region_h - 2 - (max(0.0, min(y_max, value)) / y_max) * (region_h - 4))
                points.append((x, y))

            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        painter.end()

    def _all_peaks(self) -> list[float]:
        """汇总所有线的数据，供非分区模式计算全局 y 轴"""
        merged: list[float] = []
        for data, _ in self._series:
            merged.extend(data)
        return merged
