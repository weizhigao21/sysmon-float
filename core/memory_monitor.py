"""内存监控"""

import psutil


class MemoryMonitor:
    """采集内存使用情况"""

    def __init__(self) -> None:
        self.name = "内存"

    def get_usage(self) -> float:
        """获取内存使用率，返回 0~100"""
        return psutil.virtual_memory().percent

    def get_details(self) -> dict:
        """获取内存详细信息"""
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "used_gb": mem.used / (1024**3),
            "total_gb": mem.total / (1024**3),
            "available_gb": mem.available / (1024**3),
        }
