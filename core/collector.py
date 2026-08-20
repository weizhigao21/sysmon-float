"""数据采集调度器"""

import logging
from collections import deque
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from config import CONFIG
from .cpu_monitor import CpuMonitor
from .gpu_monitor import GpuMonitor
from .memory_monitor import MemoryMonitor
from .network_monitor import NetworkMonitor


class Collector(QObject):
    """定时采集各硬件指标并通过信号发出

    设计为在独立 QThread 中运行，避免 WMI/psutil 查询阻塞主线程 UI。
    """

    # 信号参数: {metric_name: {"value": float, "details": dict}}
    data_updated = pyqtSignal(dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._timer: Optional[QTimer] = None

        self._cpu = CpuMonitor()
        self._memory = MemoryMonitor()
        self._gpu = GpuMonitor()
        self._network = NetworkMonitor()

        # 历史数据队列
        self._history: dict[str, deque[float]] = {
            "CPU": deque(maxlen=CONFIG.CHART_HISTORY_SIZE),
            "内存": deque(maxlen=CONFIG.CHART_HISTORY_SIZE),
            "GPU": deque(maxlen=CONFIG.CHART_HISTORY_SIZE),
        }
        # 网络上下行各自的历史（利用率 0~100，相对基准带宽），用于双线交叉图
        self._net_recv_history: deque[float] = deque(maxlen=CONFIG.CHART_HISTORY_SIZE)
        self._net_sent_history: deque[float] = deque(maxlen=CONFIG.CHART_HISTORY_SIZE)

    def start(self) -> None:
        """开始定时采集（应在所在线程中调用）"""
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._collect)

        self._collect()  # 立即采集一次
        self._timer.start(CONFIG.UPDATE_INTERVAL_MS)
        logging.info("Collector 定时器已启动")

    @pyqtSlot()
    def shutdown(self) -> None:
        """停止采集并释放资源（应在 collector 所在线程中调用）

        通过信号槽/BlockingQueuedConnection 调用，保证 QTimer.deleteLater
        在事件循环退出前执行，并释放 LHM/NVML 等系统资源。
        """
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._cpu.close()
        self._gpu.close()
        logging.info("Collector 已停止并释放资源")

    def _collect(self) -> None:
        try:
            cpu_value = self._cpu.get_usage()
            mem_details = self._memory.get_details()
            net_details = self._network.get_speed()
            gpu_details = self._gpu.get_details()
        except Exception as exc:  # noqa: BLE001
            logging.warning(f"数据采集异常: {exc}")
            return

        self._history["CPU"].append(cpu_value)
        self._history["内存"].append(mem_details["percent"])

        # 网络：上下行各自利用率（相对基准带宽），供双线交叉图
        net_reference = (CONFIG.NETWORK_REFERENCE_MBPS * 1_000_000) / 8
        self._net_recv_history.append(
            min(100.0, net_details["speed_recv_bps"] / net_reference * 100.0)
        )
        self._net_sent_history.append(
            min(100.0, net_details["speed_sent_bps"] / net_reference * 100.0)
        )

        # CPU 温度
        cpu_temp = self._cpu.get_temperature()

        payload: dict[str, dict] = {
            "CPU": {
                "value": cpu_value,
                "details": {
                    "per_cpu": self._cpu.get_per_cpu_usage(),
                    "temperature": cpu_temp,
                },
                "history": list(self._history["CPU"]),
            },
            "内存": {
                "value": mem_details["percent"],
                "details": mem_details,
                "history": list(self._history["内存"]),
            },
        }

        # 网络数据（history 为上下行两条线）
        payload["网络"] = {
            "value": None,  # 网络没有百分比主值，使用 value_text 显示速度
            "details": net_details,
            "history": {
                "recv": list(self._net_recv_history),
                "sent": list(self._net_sent_history),
            },
        }

        if gpu_details is not None:
            gpu_percent = gpu_details.get("percent")
            # 图表历史使用 0 代替 None，避免绘制异常
            self._history["GPU"].append(gpu_percent if gpu_percent is not None else 0.0)
            payload["GPU"] = {
                "value": gpu_percent,
                "details": gpu_details,
                "history": list(self._history["GPU"]),
            }
        else:
            # GPU 查询瞬时失败时补 0，避免图表断裂
            self._history["GPU"].append(0.0)

        self.data_updated.emit(payload)

        gpu_value = payload.get("GPU", {}).get("value")
        logging.debug(f"数据采集完成: CPU={payload['CPU']['value']:.1f}%, "
                      f"内存={payload['内存']['value']:.1f}%, "
                      f"GPU={gpu_value if gpu_value is None else f'{gpu_value:.1f}%'}, "
                      f"网络↑={net_details['speed_sent']}↓={net_details['speed_recv']}")

    def get_gpu_availability(self) -> bool:
        return self._gpu.available

    def get_gpu_error(self) -> str:
        return self._gpu.error_message

    def get_gpu_name(self) -> str:
        return self._gpu.gpu_name
