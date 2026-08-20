"""单个指标展示卡片"""

from typing import Optional

from PyQt6 import sip
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from config import CONFIG
from ui.mini_chart import MiniChart


class MetricWidget(QWidget):
    """展示单个指标的名称、数值和迷你图"""

    def __init__(
        self,
        name: str,
        color_key: str,
        parent: Optional[QWidget] = None,
        auto_layout: bool = True,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._color = CONFIG.COLORS[color_key]
        self._warning = CONFIG.THRESHOLDS["warning"]
        self._critical = CONFIG.THRESHOLDS["critical"]
        # 自动横/竖切换：数值文本长度波动大（如网络速度）时固定布局，避免跳动
        self._auto_layout = auto_layout

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        # 第一行：名称 + 数值（自动换行切换）
        self._top_widget = QWidget()
        # auto_layout=False 时固定垂直布局（名称在上、数值在下），
        # 防止数值长度波动导致布局反复切换
        self._use_horizontal_top = self._auto_layout

        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet(
            f"color: {CONFIG.COLORS['text_secondary']}; font-size: {CONFIG.FONT_SIZE_NAME}px; font-weight: bold; font-family: '{CONFIG.FONT_FAMILY_FALLBACK}', '{CONFIG.FONT_FAMILY}';"
        )

        self._value_label = QLabel("--%")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        font = QFont(CONFIG.FONT_FAMILY, CONFIG.FONT_SIZE_VALUE)
        self._value_label.setFont(font)

        self._build_top_layout(horizontal=True)

        layout.addWidget(self._top_widget)

        # 第二行：迷你图
        self._chart = MiniChart(self._color)

        # 第三行：辅助信息（如 GPU 名称、显存/网络速度）
        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet(
            f"color: {CONFIG.COLORS['text_secondary']}; font-size: {CONFIG.FONT_SIZE_DETAIL}px; font-weight: bold; font-family: '{CONFIG.FONT_FAMILY_FALLBACK}', '{CONFIG.FONT_FAMILY}';"
        )
        self._detail_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(self._chart)
        layout.addWidget(self._detail_label)

    def _build_top_layout(self, horizontal: bool) -> None:
        """构建顶部布局（水平或垂直）"""
        # 从旧布局中剥离控件
        self._name_label.setParent(None)
        self._value_label.setParent(None)

        # 销毁旧布局
        old_layout = self._top_widget.layout()
        if old_layout is not None:
            sip.delete(old_layout)

        if horizontal:
            layout = QHBoxLayout(self._top_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)
            layout.addWidget(self._name_label)
            layout.addStretch()
            layout.addWidget(self._value_label)
        else:
            layout = QVBoxLayout(self._top_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            layout.addWidget(self._name_label)
            layout.addWidget(self._value_label)

        self._use_horizontal_top = horizontal

    def update_value(
        self,
        value: Optional[float],
        history: list[float],
        detail_text: Optional[str] = None,
        value_text: Optional[str] = None,
    ) -> None:
        """更新显示

        Args:
            value: 百分比数值，用于阈值颜色判断；None 时显示 N/A
            history: 历史数据列表（0~100 范围）
            detail_text: 辅助信息文本
            value_text: 自定义主值文本，不为 None 时替代百分比显示
        """
        if value_text is not None:
            self._value_label.setText(value_text)
            color = self._color
        elif value is None:
            self._value_label.setText("N/A")
            color = self._color
        else:
            self._value_label.setText(f"{value:.1f}%")
            # 根据阈值调整颜色
            if value >= self._critical:
                color = CONFIG.COLORS["critical"]
            elif value >= self._warning:
                color = CONFIG.COLORS["warning"]
            else:
                color = self._color

        self._value_label.setStyleSheet(
            f"color: {color}; font-size: {CONFIG.FONT_SIZE_VALUE}px;"
        )

        # 自动换行：数值文本较长（>10字符）时切换为垂直布局，短于 6 字符恢复水平
        # 中间区间保持当前状态（滞回），避免速度文本在边界抖动时反复重建布局
        if self._auto_layout:
            current_text = self._value_label.text()
            length = len(current_text)
            if length > 10:
                needs_vertical = True
            elif length < 6:
                needs_vertical = False
            else:
                needs_vertical = self._use_horizontal_top
            if needs_vertical == self._use_horizontal_top:
                self._build_top_layout(horizontal=not needs_vertical)

        self._chart.set_data(history)

        if detail_text:
            self._detail_label.setText(detail_text)
            self._detail_label.show()
        else:
            self._detail_label.hide()
