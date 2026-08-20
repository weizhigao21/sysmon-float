"""全局配置"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    """应用配置"""

    # 窗口默认尺寸（位置由 ~/.sysmon_float/window_position.json 记忆恢复）
    WINDOW_WIDTH: int = 320
    WINDOW_HEIGHT: int = 300

    # 刷新间隔（毫秒）
    UPDATE_INTERVAL_MS: int = 1000

    # 图表历史数据点数量
    CHART_HISTORY_SIZE: int = 60

    # 网络利用率参考基准带宽（Mbps），达到该带宽视为 100% 利用率
    NETWORK_REFERENCE_MBPS: int = 400

    # 透明度 0.0 ~ 1.0
    WINDOW_OPACITY: float = 0.88

    # 圆角半径
    WINDOW_RADIUS: int = 10

    # 默认字体
    FONT_FAMILY: str = "Consolas"
    FONT_FAMILY_FALLBACK: str = "Microsoft YaHei"

    # 字体大小
    FONT_SIZE_VALUE: int = 18      # 百分比数值
    FONT_SIZE_NAME: int = 12       # 指标名称
    FONT_SIZE_DETAIL: int = 11     # 辅助信息
    FONT_SIZE_NET_SENT: int = 14   # 网络上行字号（与下行主值 18px 差距适中）

    # 配色方案（深色科技风）
    COLORS = {
        "background": "rgba(30, 30, 30, 0.88)",
        "border": "#333333",
        "border_hover": "#555555",
        "text_primary": "#e0e0e0",
        "text_secondary": "#888888",
        "cpu": "#4fc3f7",
        "memory": "#ba68c8",
        "gpu": "#ffb74d",
        "network": "#81c784",
        "net_sent": "#ef5350",       # 网络上行（红色，文字与迷你图线统一）
        "warning": "#ffca28",
        "critical": "#ef5350",
    }

    # 阈值配置
    THRESHOLDS = {
        "warning": 80,
        "critical": 95,
    }

    # 数据保存目录
    @property
    def config_dir(self) -> Path:
        path = Path.home() / ".sysmon_float"
        path.mkdir(parents=True, exist_ok=True)
        return path


CONFIG = AppConfig()
