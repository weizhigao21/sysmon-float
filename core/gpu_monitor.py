"""GPU 监控"""

import logging
from typing import Optional


class GpuMonitor:
    """采集 GPU 使用情况，优先 NVIDIA，其次 Windows WMI"""

    def __init__(self) -> None:
        self.name = "GPU"
        self._nvml = None
        self._handle = None
        self._wmi = None
        self._wmi_gpu = None
        self._available = False
        self._error_message = ""
        self._gpu_name = ""

        self._init_nvml()
        if not self._available:
            self._init_wmi()

    def _init_nvml(self) -> None:
        try:
            import pynvml

            logging.info("开始初始化 pynvml...")
            pynvml.nvmlInit()
            self._nvml = pynvml
            version = None
            try:
                version = pynvml.nvmlSystemGetDriverVersion()
            except Exception as exc:  # noqa: BLE001
                logging.debug(f"读取 NVIDIA 驱动版本失败: {exc}")

            device_count = pynvml.nvmlDeviceGetCount()
            logging.info(f"pynvml 驱动版本: {version}, 设备数量: {device_count}")
            if device_count == 0:
                self._error_message = "未检测到 NVIDIA GPU"
                logging.info("pynvml 未检测到 NVIDIA GPU")
                return

            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            raw_name = pynvml.nvmlDeviceGetName(self._handle)
            # 新版 pynvml 可能返回 bytes
            if isinstance(raw_name, bytes):
                self._gpu_name = raw_name.decode("utf-8", errors="ignore")
            else:
                self._gpu_name = str(raw_name)
            self._available = True
            logging.info(f"NVIDIA GPU 初始化成功: {self._gpu_name}")
        except ImportError:
            self._error_message = "未安装 nvidia-ml-py，无法监控 NVIDIA GPU"
            logging.info("未安装 nvidia-ml-py")
        except Exception as exc:  # noqa: BLE001
            self._error_message = f"NVIDIA GPU 监控初始化失败: {exc}"
            logging.warning(f"NVIDIA GPU 初始化失败: {exc}")

    def _init_wmi(self) -> None:
        """通过 Windows WMI 获取 GPU 基本信息"""
        try:
            import wmi

            self._wmi = wmi.WMI()
            controllers = self._wmi.Win32_VideoController()
            if not controllers:
                self._error_message = "未通过 WMI 检测到 GPU"
                logging.info("WMI 未检测到 GPU")
                return

            # 优先选择真实 GPU，过滤虚拟/基本显示适配器
            skip_keywords = (
                "Microsoft",
                "Virtual",
                "Display",
                "Basic",
                "Adapter",
                "VMware",
                "Citrix",
                "Indirect",
            )
            real_gpus = [
                c
                for c in controllers
                if not any(
                    kw.lower() in getattr(c, "Name", "").lower() for kw in skip_keywords
                )
            ]

            if real_gpus:
                self._wmi_gpu = real_gpus[0]
                self._gpu_name = getattr(real_gpus[0], "Name", "Unknown GPU")
            elif controllers:
                self._wmi_gpu = controllers[0]
                self._gpu_name = getattr(controllers[0], "Name", "Unknown GPU")
            else:
                self._error_message = "未通过 WMI 检测到 GPU"
                logging.info("WMI 未检测到 GPU")
                return

            self._available = True
            logging.info(f"WMI GPU 初始化成功: {self._gpu_name}")
        except ImportError:
            self._error_message = "未安装 WMI，无法通过 WMI 监控 GPU"
            logging.info("未安装 WMI 包")
        except Exception as exc:  # noqa: BLE001
            self._error_message = f"WMI GPU 监控初始化失败: {exc}"
            logging.warning(f"WMI GPU 初始化失败: {exc}")

    @property
    def available(self) -> bool:
        return self._available

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def gpu_name(self) -> str:
        return self._gpu_name

    def get_usage(self) -> Optional[float]:
        """获取 GPU 利用率，返回 0~100 或 None"""
        details = self.get_details()
        if details is None:
            return None
        return details.get("percent")

    def _get_nvidia_details(self) -> Optional[dict]:
        if self._nvml is None or self._handle is None:
            logging.debug("_get_nvidia_details: nvml 或 handle 为空")
            return None
        try:
            util = self._nvml.nvmlDeviceGetUtilizationRates(self._handle)
            mem_info = self._nvml.nvmlDeviceGetMemoryInfo(self._handle)
            temperature = None
            try:
                temperature = self._nvml.nvmlDeviceGetTemperature(
                    self._handle, self._nvml.NVML_TEMPERATURE_GPU
                )
            except Exception:  # noqa: BLE001
                pass

            result = {
                "name": self._gpu_name,
                "percent": float(util.gpu),
                "memory_used_gb": mem_info.used / (1024**3),
                "memory_total_gb": mem_info.total / (1024**3),
                "memory_percent": (mem_info.used / mem_info.total) * 100,
                "temperature": temperature,
            }
            logging.debug(f"NVIDIA GPU 详情: {result}")
            return result
        except Exception as exc:  # noqa: BLE001
            logging.warning(f"读取 NVIDIA GPU 详情失败: {exc}")
            return None

    def _get_wmi_details(self) -> Optional[dict]:
        """读取 WMI GPU 静态信息（不查询性能计数器，避免卡顿）"""
        if self._wmi is None or self._wmi_gpu is None:
            return None
        try:
            # 使用初始化时缓存的 controller，避免每 tick 查询 WMI
            controller = self._wmi_gpu

            # 显存信息（WMI 提供的是字节）
            # 注意：AdapterRAM 是 uint32，>4GB 显存会溢出回绕（如 11GB 会显示 ~3GB）。
            # NVIDIA 后端不受影响；WMI 仅为回退方案，此处结果仅供参考。
            adapter_ram = getattr(controller, "AdapterRAM", None)
            total_gb = None
            if adapter_ram and adapter_ram > 0:
                total_gb = adapter_ram / (1024**3)

            return {
                "name": self._gpu_name,
                "percent": None,  # WMI 无法稳定获取利用率，由 nvidia-ml-py 提供
                "memory_total_gb": total_gb,
                "temperature": None,
            }
        except Exception as exc:  # noqa: BLE001
            logging.warning(f"读取 WMI GPU 详情失败: {exc}")
            return None

    def close(self) -> None:
        """释放 NVML 资源"""
        if self._nvml is not None:
            try:
                self._nvml.nvmlShutdown()
            except Exception as exc:  # noqa: BLE001
                logging.debug(f"关闭 NVML 失败: {exc}")
            self._nvml = None
        self._handle = None
        self._available = False

    def get_details(self) -> Optional[dict]:
        """获取 GPU 详细信息"""
        if not self._available:
            logging.debug("get_details: GPU 不可用")
            return None

        if self._nvml is not None:
            logging.debug("get_details: 使用 NVIDIA 后端")
            return self._get_nvidia_details()
        if self._wmi is not None:
            logging.debug("get_details: 使用 WMI 后端")
            return self._get_wmi_details()
        logging.debug("get_details: 无可用后端")
        return None
