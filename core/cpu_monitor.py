"""CPU 监控"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import psutil


class CpuMonitor:
    """采集 CPU 使用率和温度"""

    # 温度缓存有效期（秒）：LHM 遍历传感器开销较大，无需每秒刷新
    TEMP_CACHE_SECONDS = 5.0

    def __init__(self) -> None:
        self.name = "CPU"
        # 首次调用通常返回 0，先预热一次
        psutil.cpu_percent(interval=None)
        self._lhm_computer = None
        self._lhm_available = False
        self._temp_cache: Optional[float] = None
        self._temp_cache_time: float = 0.0
        self._init_lhm()

    def _init_lhm(self) -> None:
        """初始化 LibreHardwareMonitor 以读取 CPU 温度"""
        try:
            import clr

            dll_dir = Path(__file__).resolve().parent.parent / "LibreHardwareMonitor"
            if dll_dir.exists():
                sys.path.append(str(dll_dir))
            clr.AddReference("LibreHardwareMonitorLib")
            from LibreHardwareMonitor.Hardware import Computer

            self._lhm_computer = Computer()
            self._lhm_computer.IsCpuEnabled = True
            self._lhm_computer.Open()
            self._lhm_available = True
            logging.info("LibreHardwareMonitor 初始化成功")
        except Exception as exc:  # noqa: BLE001
            logging.debug(f"LibreHardwareMonitor 初始化失败（CPU 温度不可用）: {exc}")
            self._lhm_computer = None
            self._lhm_available = False

    def get_usage(self) -> float:
        """获取整体 CPU 使用率，返回 0~100"""
        return psutil.cpu_percent(interval=None)

    def get_per_cpu_usage(self) -> list[float]:
        """获取每个核心使用率"""
        return psutil.cpu_percent(interval=None, percpu=True)

    def get_temperature(self) -> Optional[float]:
        """获取 CPU 温度（摄氏度）

        通过 LibreHardwareMonitor 采集，适用于 AMD/Intel。
        返回 None 表示不可用。
        结果缓存 TEMP_CACHE_SECONDS 秒，避免高频遍历 LHM 传感器。
        """
        if not self._lhm_available or self._lhm_computer is None:
            return None

        now = time.monotonic()
        if self._temp_cache is not None and (now - self._temp_cache_time) < self.TEMP_CACHE_SECONDS:
            return self._temp_cache

        try:
            from LibreHardwareMonitor.Hardware import SensorType

            temps: list[float] = []
            for hardware in self._lhm_computer.Hardware:
                if str(hardware.HardwareType) != "Cpu":
                    continue
                hardware.Update()
                for sensor in hardware.Sensors:
                    if sensor.SensorType == SensorType.Temperature and sensor.Value is not None:
                        value = float(sensor.Value)
                        if value > 0:
                            temps.append(value)

            if not temps:
                return None
            result = round(max(temps), 1)
            self._temp_cache = result
            self._temp_cache_time = now
            return result
        except Exception as exc:  # noqa: BLE001
            logging.debug(f"读取 CPU 温度失败: {exc}")
            return None

    def close(self) -> None:
        """释放 LibreHardwareMonitor 资源"""
        if self._lhm_computer is not None:
            try:
                self._lhm_computer.Close()
            except Exception as exc:  # noqa: BLE001
                logging.debug(f"关闭 LibreHardwareMonitor 失败: {exc}")
            self._lhm_computer = None
            self._lhm_available = False
