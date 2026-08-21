"""网络监控"""

import ctypes
import ctypes.wintypes as wt
import logging
import sys
import time
from typing import Optional

import psutil

from config import CONFIG

# ---- Windows 物理网卡识别（ctypes GetAdaptersAddresses） ----

# RFC 2863 ifType 常量
_IF_TYPE_ETHERNET = 6        # 以太网 (ethernetCsmacd)
_IF_TYPE_IEEE80211 = 71      # WiFi
_IF_OPER_STATUS_UP = 1       # ifOperStatusUp

# 虚拟网卡描述关键词（命中即排除，描述统一小写匹配）
_VIRTUAL_DESC_KEYWORDS = (
    "tunnel", "virtual", "vmware", "virtualbox", "bluetooth", "蓝牙",
    "loopback", "hyper-v", "hyperv", "vethernet", "wsl", "tailscale",
    "zerotier", "wireguard", "tap", "ppp",
)


class _IP_ADAPTER_ADDRESSES(ctypes.Structure):
    """IP_ADAPTER_ADDRESSES 结构（仅声明到 OperStatus，后续字段不访问）

    前半部分布局在 Vista+ 所有 Windows 版本中一致，保证读取可靠。
    """


_IP_ADAPTER_ADDRESSES._fields_ = [
    ("Length", wt.ULONG),
    ("IfIndex", wt.DWORD),
    ("Next", ctypes.POINTER(_IP_ADAPTER_ADDRESSES)),
    ("AdapterName", ctypes.c_char_p),
    ("FirstUnicastAddress", ctypes.c_void_p),
    ("FirstAnycastAddress", ctypes.c_void_p),
    ("FirstMulticastAddress", ctypes.c_void_p),
    ("FirstDnsServerAddress", ctypes.c_void_p),
    ("DnsSuffix", ctypes.c_wchar_p),
    ("Description", ctypes.c_wchar_p),
    ("FriendlyName", ctypes.c_wchar_p),
    ("PhysicalAddress", ctypes.c_ubyte * 8),
    ("PhysicalAddressLength", wt.ULONG),
    ("Flags", wt.ULONG),
    ("Mtu", wt.ULONG),
    ("IfType", wt.DWORD),
    ("OperStatus", ctypes.c_int),
]

_IP_ADAPTER_ADDRESSES_P = ctypes.POINTER(_IP_ADAPTER_ADDRESSES)

# GAA_FLAG_SKIP_UNICAST | SKIP_ANYCAST | SKIP_MULTICAST | SKIP_DNSSERVER
_GAA_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0008
_ERROR_BUFFER_OVERFLOW = 111

# 物理网卡集合缓存（接口增删频率低，120s 刷新一次即可）
_physical_cache: Optional[tuple[float, frozenset]] = None
_PHYSICAL_CACHE_TTL = 120.0


def _query_physical_interfaces() -> frozenset:
    """调用 GetAdaptersAddresses 识别物理网卡（以太网/WiFi）接口名集合"""
    if sys.platform != "win32":
        return frozenset()

    get_adapters = ctypes.windll.iphlpapi.GetAdaptersAddresses
    get_adapters.argtypes = [
        wt.ULONG, wt.ULONG, ctypes.c_void_p,
        _IP_ADAPTER_ADDRESSES_P, ctypes.POINTER(wt.ULONG),
    ]
    get_adapters.restype = wt.ULONG

    size = wt.ULONG(0)
    ret = get_adapters(0, _GAA_FLAGS, None, None, ctypes.byref(size))
    if ret != _ERROR_BUFFER_OVERFLOW:
        return frozenset()

    buf = ctypes.create_string_buffer(size.value)
    ret = get_adapters(
        0, _GAA_FLAGS, None,
        ctypes.cast(buf, _IP_ADAPTER_ADDRESSES_P),
        ctypes.byref(size),
    )
    if ret != 0:
        return frozenset()

    physical: set = set()
    excluded: list = []
    p = ctypes.cast(buf, _IP_ADAPTER_ADDRESSES_P)
    while p:
        a = p.contents
        name = a.FriendlyName or ""
        desc = (a.Description or "").lower()
        is_physical = (
            a.IfType in (_IF_TYPE_ETHERNET, _IF_TYPE_IEEE80211)
            and a.OperStatus == _IF_OPER_STATUS_UP
            and not any(kw in desc for kw in _VIRTUAL_DESC_KEYWORDS)
        )
        if is_physical:
            physical.add(name)
        else:
            excluded.append(name or "(unnamed)")
        p = a.Next

    logging.info(
        f"网络统计网卡: {sorted(physical) or '无（将回退为聚合计数）'}，"
        f"已排除: {excluded}"
    )
    return frozenset(physical)


def _physical_interface_names() -> frozenset:
    """带缓存的物理网卡接口名集合"""
    global _physical_cache
    now = time.monotonic()
    if _physical_cache is None or now - _physical_cache[0] > _PHYSICAL_CACHE_TTL:
        try:
            names = _query_physical_interfaces()
        except Exception as exc:  # noqa: BLE001
            logging.warning(f"物理网卡识别失败，回退聚合计数: {exc}")
            names = frozenset()
        _physical_cache = (now, names)
    return _physical_cache[1]


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

    def _get_io_bytes(self) -> tuple:
        """按配置统计口径返回 (bytes_sent, bytes_recv)

        统计口径优先级：
        1. CONFIG.NETWORK_INCLUDE_ONLY 非空 → 只统计白名单网卡
        2. CONFIG.NETWORK_PHYSICAL_ONLY → 只统计物理网卡（默认，排除 TUN/虚拟机等）
        3. 均不满足/识别为空 → 全部网卡聚合（原行为）

        背景：Clash/V2Ray 开启 TUN 模式时，同一份流量会在物理网卡与
        虚拟隧道网卡（如 "Meta Tunnel"）各计数一次，聚合值约为实际值的 2 倍。
        """
        pernic = psutil.net_io_counters(pernic=True)

        if CONFIG.NETWORK_INCLUDE_ONLY:
            names = [n for n in CONFIG.NETWORK_INCLUDE_ONLY if n in pernic]
        elif CONFIG.NETWORK_PHYSICAL_ONLY:
            names = [n for n in _physical_interface_names() if n in pernic]
        else:
            names = list(pernic.keys())

        if not names:  # 兜底：识别失败或全部被排除时回退聚合
            names = list(pernic.keys())

        sent = sum(pernic[n].bytes_sent for n in names)
        recv = sum(pernic[n].bytes_recv for n in names)
        return sent, recv

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
        bytes_sent, bytes_recv = self._get_io_bytes()
        now = time.time()

        if not self._initialized:
            self._last_bytes_sent = bytes_sent
            self._last_bytes_recv = bytes_recv
            self._last_time = now
            self._initialized = True
            self.speed_sent = 0.0
            self.speed_recv = 0.0
        else:
            elapsed = now - self._last_time
            if elapsed > 0:
                self.speed_sent = max(0.0, (bytes_sent - self._last_bytes_sent) / elapsed)
                self.speed_recv = max(0.0, (bytes_recv - self._last_bytes_recv) / elapsed)

            self._last_bytes_sent = bytes_sent
            self._last_bytes_recv = bytes_recv
            self._last_time = now

        # 累计流量（转换为 GB）
        self.total_sent_gb = bytes_sent / (1024**3)
        self.total_recv_gb = bytes_recv / (1024**3)

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
