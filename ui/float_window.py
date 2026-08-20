"""悬浮窗主窗口"""

import json
import logging
import re
from typing import Optional

from PyQt6 import sip
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QBrush,
    QColor,
    QContextMenuEvent,
    QCursor,
    QMouseEvent,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import QApplication, QGridLayout, QMenu, QVBoxLayout, QWidget

from config import CONFIG
from core.collector import Collector
from ui.metric_widget import MetricWidget


class FloatWindow(QWidget):
    """置顶无边框可拖拽悬浮窗"""

    def __init__(self, collector: Collector, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._collector = collector
        self._drag_position: Optional[QPoint] = None
        self._border_color = CONFIG.COLORS["border"]
        # 背景色只解析一次，避免每帧 paintEvent 重复解析 rgba 字符串
        r, g, b, a = self._parse_rgba(CONFIG.COLORS["background"])
        self._bg_color = QColor(r, g, b, a)
        self._settings = self._load_settings()

        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        logging.info("FloatWindow 初始化完成")

    def _setup_window(self) -> None:
        self.setWindowTitle("系统性能监控")
        self.resize(CONFIG.WINDOW_WIDTH, CONFIG.WINDOW_HEIGHT)

        # 窗口标志：无边框、置顶、不在任务栏显示
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # 透明背景，由 paintEvent 自行绘制背景和边框
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(self._settings.get("opacity", CONFIG.WINDOW_OPACITY))

        self._restore_or_center()

        # 子控件样式
        self.setStyleSheet(f"""
            QWidget#FloatWindow {{
                color: {CONFIG.COLORS['text_primary']};
            }}
        """)
        self.setObjectName("FloatWindow")

    def _restore_or_center(self) -> None:
        """恢复上次位置，无记录时居中到主屏幕"""
        pos = self._load_position()
        if pos is not None:
            self.move(pos.x(), pos.y())
            logging.info(f"窗口位置已恢复: ({pos.x()}, {pos.y()})")
            return
        self._center_on_primary_screen()

    def _center_on_primary_screen(self) -> None:
        """将窗口居中到主屏幕"""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        logging.info(f"窗口居中到: ({x}, {y}), 屏幕尺寸: {screen_geometry.size()}")

    @property
    def _config_dir(self) -> str:
        return str(CONFIG.config_dir)

    @property
    def _position_file(self) -> str:
        return f"{self._config_dir}/window_position.json"

    @property
    def _settings_file(self) -> str:
        return f"{self._config_dir}/settings.json"

    def _save_position(self) -> None:
        """保存当前窗口位置到文件"""
        pos = self.pos()
        try:
            with open(self._position_file, "w", encoding="utf-8") as f:
                json.dump({"x": pos.x(), "y": pos.y()}, f)
        except OSError as exc:
            logging.warning(f"保存窗口位置失败: {exc}")

    def _load_position(self) -> Optional[QPoint]:
        """从文件恢复窗口位置"""
        try:
            with open(self._position_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return QPoint(data["x"], data["y"])
        except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError):
            return None

    def _save_settings(self) -> None:
        """保存设置到文件"""
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f)
        except OSError as exc:
            logging.warning(f"保存设置失败: {exc}")

    def _load_settings(self) -> dict:
        """从文件加载设置"""
        try:
            with open(self._settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {
                "layout": "grid",
                "opacity": CONFIG.WINDOW_OPACITY,
            }

    def closeEvent(self, event) -> None:  # noqa: ARG002
        self._save_position()
        self._save_settings()

    def _setup_ui(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(0)

        self._content_widget = QWidget(self)
        self._content_layout: Optional[QGridLayout | QVBoxLayout] = None
        self._main_layout.addWidget(self._content_widget)

        self._cpu_widget = MetricWidget("CPU", "cpu")
        self._memory_widget = MetricWidget("内存", "memory")
        self._gpu_widget = MetricWidget("GPU", "gpu")
        # 网络速度文本长度波动大，固定垂直布局 + 上下行分行显示，避免布局跳动
        self._network_widget = MetricWidget("网络", "network", auto_layout=False)

        self._apply_layout(self._settings.get("layout", "grid"))

        # 如果 GPU 不可用则隐藏
        if not self._collector.get_gpu_availability():
            self._gpu_widget.hide()

    def _apply_layout(self, layout_name: str) -> None:
        """应用指定布局"""
        self._settings["layout"] = layout_name

        # 强制销毁旧布局（setLayout 不能替换已有布局，必须先删除）
        if self._content_layout is not None:
            while self._content_layout.count():
                self._content_layout.takeAt(0)
            old_layout = self._content_layout
            self._content_layout = None
            sip.delete(old_layout)

        # 创建新布局并添加子控件
        if layout_name == "vertical":
            self._content_layout = QVBoxLayout(self._content_widget)
            self._content_layout.setContentsMargins(0, 0, 0, 0)
            self._content_layout.setSpacing(6)
            self._content_layout.addWidget(self._cpu_widget)
            self._content_layout.addWidget(self._memory_widget)
            self._content_layout.addWidget(self._gpu_widget)
            self._content_layout.addWidget(self._network_widget)
        else:
            self._content_layout = QGridLayout(self._content_widget)
            self._content_layout.setContentsMargins(0, 0, 0, 0)
            self._content_layout.setSpacing(8)
            self._content_layout.addWidget(self._cpu_widget, 0, 0)
            self._content_layout.addWidget(self._memory_widget, 0, 1)
            self._content_layout.addWidget(self._gpu_widget, 1, 0)
            self._content_layout.addWidget(self._network_widget, 1, 1)

        # 重新调整窗口大小
        if layout_name == "vertical":
            self.resize(CONFIG.WINDOW_WIDTH, CONFIG.WINDOW_HEIGHT + 160)
        else:
            self.resize(CONFIG.WINDOW_WIDTH, CONFIG.WINDOW_HEIGHT)

    def _connect_signals(self) -> None:
        self._collector.data_updated.connect(self._on_data_updated)

    def _on_data_updated(self, data: dict) -> None:
        if "CPU" in data:
            cpu_details = data["CPU"]["details"]
            per_cpu = cpu_details.get("per_cpu", [])
            detail_parts = []
            if per_cpu:
                detail_parts.append(f"{len(per_cpu)} 核")
            cpu_temp = cpu_details.get("temperature")
            if cpu_temp is not None:
                detail_parts.append(f"{cpu_temp:.0f}°C")
            self._cpu_widget.update_value(
                data["CPU"]["value"],
                data["CPU"]["history"],
                detail_text=" | ".join(detail_parts) if detail_parts else None,
            )

        if "内存" in data:
            mem_details = data["内存"]["details"]
            total_gb = mem_details.get("total_gb", 0)
            used_gb = mem_details.get("used_gb", 0)
            mem_detail = f"{total_gb:.0f}G / {used_gb:.1f}G"
            self._memory_widget.update_value(
                data["内存"]["value"],
                data["内存"]["history"],
                detail_text=mem_detail,
            )

        if "GPU" in data:
            gpu_details = data["GPU"]["details"]
            detail_parts = []

            # 显存：总量 / 已用
            memory_total_gb = gpu_details.get("memory_total_gb")
            memory_used_gb = gpu_details.get("memory_used_gb")
            if memory_total_gb is not None and memory_used_gb is not None:
                detail_parts.append(f"显存 {memory_total_gb:.0f}G / {memory_used_gb:.1f}G")
            elif memory_total_gb is not None:
                detail_parts.append(f"显存 {memory_total_gb:.0f}G")

            if gpu_details.get("temperature"):
                detail_parts.append(f"{gpu_details['temperature']}°C")

            self._gpu_widget.update_value(
                data["GPU"]["value"],
                data["GPU"]["history"],
                detail_text=" | ".join(detail_parts) if detail_parts else None,
            )
            self._gpu_widget.show()

        if "网络" in data:
            net_details = data["网络"]["details"]
            speed_recv = net_details.get("speed_recv", "--")
            speed_sent = net_details.get("speed_sent", "--")
            self._network_widget.update_value(
                value=None,
                history=data["网络"]["history"],
                # 上行单独放在辅助行，下行是主值（value_text），两者分开显示
                detail_text=f"↑ {speed_sent}",
                value_text=f"↓ {speed_recv}",
            )

    # ---------- 鼠标拖拽 ----------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and self._drag_position is not None
        ):
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_position is not None:
            self._save_position()
        self._drag_position = None

    # ---------- 右键菜单 ----------
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)

        toggle_gpu_action = QAction("显示/隐藏 GPU", self)
        toggle_gpu_action.setCheckable(True)
        toggle_gpu_action.setChecked(self._gpu_widget.isVisible())
        toggle_gpu_action.triggered.connect(self._toggle_gpu)
        # GPU 硬件不可用时禁用菜单项，避免显示 N/A 卡片
        if not self._collector.get_gpu_availability():
            toggle_gpu_action.setEnabled(False)

        layout_menu = QMenu("布局", self)
        layout_group = QActionGroup(layout_menu)

        grid_action = QAction("2x2 网格", layout_group)
        grid_action.setCheckable(True)
        grid_action.setChecked(self._settings.get("layout") == "grid")
        grid_action.triggered.connect(lambda: self._apply_layout("grid"))

        vertical_action = QAction("竖向排列", layout_group)
        vertical_action.setCheckable(True)
        vertical_action.setChecked(self._settings.get("layout") == "vertical")
        vertical_action.triggered.connect(lambda: self._apply_layout("vertical"))

        layout_menu.addAction(grid_action)
        layout_menu.addAction(vertical_action)

        opacity_menu = QMenu("透明度", self)
        opacity_group = QActionGroup(opacity_menu)

        opacity_high_action = QAction("正常", opacity_group)
        opacity_high_action.setCheckable(True)
        opacity_high_action.setChecked(self._settings.get("opacity") >= 0.7)
        opacity_high_action.triggered.connect(lambda: self._set_opacity(0.88))

        opacity_mid_action = QAction("半透明", opacity_group)
        opacity_mid_action.setCheckable(True)
        opacity_mid_action.setChecked(0.4 <= self._settings.get("opacity", 1.0) < 0.7)
        opacity_mid_action.triggered.connect(lambda: self._set_opacity(0.5))

        opacity_low_action = QAction("高透明", opacity_group)
        opacity_low_action.setCheckable(True)
        opacity_low_action.setChecked(self._settings.get("opacity") < 0.4)
        opacity_low_action.triggered.connect(lambda: self._set_opacity(0.25))

        opacity_menu.addAction(opacity_high_action)
        opacity_menu.addAction(opacity_mid_action)
        opacity_menu.addAction(opacity_low_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        menu.addAction(toggle_gpu_action)
        menu.addMenu(layout_menu)
        menu.addMenu(opacity_menu)
        menu.addSeparator()
        menu.addAction(quit_action)

        menu.exec(QCursor.pos())

    def _toggle_gpu(self) -> None:
        if self._gpu_widget.isVisible():
            self._gpu_widget.hide()
        else:
            self._gpu_widget.show()

    def _set_opacity(self, opacity: float) -> None:
        self._settings["opacity"] = opacity
        self.setWindowOpacity(opacity)

    @staticmethod
    def _parse_rgba(rgba_str: str) -> tuple[int, int, int, int]:
        """解析 rgba(r, g, b, a) 字符串为 (r, g, b, alpha_0_255)"""
        match = re.match(
            r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)",
            rgba_str,
        )
        if match:
            return (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(float(match.group(4)) * 255),
            )
        # 默认颜色
        return 30, 30, 30, 224

    def paintEvent(self, event) -> None:  # noqa: ARG002
        """自定义绘制圆角背景和边框"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        border_color = QColor(self._border_color)

        painter.setBrush(QBrush(self._bg_color))
        pen = QPen(border_color)
        pen.setWidth(1)
        painter.setPen(pen)

        # 留出 1px 给边框
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(
            rect, CONFIG.WINDOW_RADIUS, CONFIG.WINDOW_RADIUS
        )
        painter.end()
        logging.debug("paintEvent 已执行")

    def enterEvent(self, event) -> None:  # noqa: ARG002
        self._border_color = CONFIG.COLORS["border_hover"]
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: ARG002
        self._border_color = CONFIG.COLORS["border"]
        self.update()
