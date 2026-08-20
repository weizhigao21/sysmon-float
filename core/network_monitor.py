"""网络监控"""

import time

import psutil

from config import CONFIG


class NetworkMonitor:
    """采集网络上传/下载速度"""

    def __init__(self) -> None:
        self.name = "网络"
        self._last_bytes_sent: int = 0
        self._last_bytes_recv: int = 0
        self._last_time: float = 0.0
        self._initialized: bool = False

        # 当前速度（字节/秒）
        self.speed_sent: float = 0.0
        self.speed_recv: float = 0.0

        # 累计流量（GB）
        self.total_sent_gb: float = 0.0
        self.total_recv_gb: float = 0.0

    def get_speed(self) -> dict:
        """获取网络速度

        Returns:
            dict: {
                "speed_sent_bps": 上传速度 (bytes/s),
                "speed_recv_bps": 下载速度 (bytes/s),
                "speed_sent": 上传速度 (格式化为 KB/s 或 MB/s),
                "speed_recv": 下载速度 (格式化为 KB/s 或 MB/s),
                "total_sent_gb": 累计上传 (GB),
                "total_recv_gb": 累计下载 (GB),
            }
        """
        counters = psutil.net_io_counters()
        now = time.time()

        if not self._initialized:
            self._last_bytes_sent = counters.bytes_sent
            self._last_bytes_recv = counters.bytes_recv
            self._last_time = now
            self._initialized = True
            self.speed_sent = 0.0
            self.speed_recv = 0.0
        else:
            elapsed = now - self._last_time
            if elapsed > 0:
                self.speed_sent = max(0.0, (counters.bytes_sent - self._last_bytes_sent) / elapsed)
                self.speed_recv = max(0.0, (counters.bytes_recv - self._last_bytes_recv) / elapsed)

            self._last_bytes_sent = counters.bytes_sent
            self._last_bytes_recv = counters.bytes_recv
            self._last_time = now

        # 累计流量（转换为 GB）
        self.total_sent_gb = counters.bytes_sent / (1024**3)
        self.total_recv_gb = counters.bytes_recv / (1024**3)

        return {
            "speed_sent_bps": self.speed_sent,
            "speed_recv_bps": self.speed_recv,
            "speed_sent": self._format_speed(self.speed_sent),
            "speed_recv": self._format_speed(self.speed_recv),
            "total_sent_gb": self.total_sent_gb,
            "total_recv_gb": self.total_recv_gb,
        }

    def get_utilization(self) -> float:
        """获取网络利用率（基于当前速度映射到 0~100）

        以 CONFIG.NETWORK_REFERENCE_MBPS（默认 400Mbps ≈ 50 MB/s）为参考基准，
        达到基准带宽视为 100% 利用率。
        """
        total_bps = self.speed_sent + self.speed_recv
        # 基准带宽：Mbps → bytes/s（1 Mbps = 1_000_000 bit/s ÷ 8）
        reference = (CONFIG.NETWORK_REFERENCE_MBPS * 1_000_000) / 8
        util = min(100.0, (total_bps / reference) * 100.0)
        return util

    @staticmethod
    def _format_speed(bps: float) -> str:
        """格式化速度显示"""
        if bps >= 1024 * 1024:
            return f"{bps / (1024 * 1024):.1f} MB/s"
        if bps >= 1024:
            return f"{bps / 1024:.1f} KB/s"
        return f"{bps:.0f} B/s"