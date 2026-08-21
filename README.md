# 系统性能监控悬浮窗

> 版本 **v1.0.4** · [更新日志](CHANGELOG.md)

一个 Windows 桌面悬浮窗程序，实时显示 CPU、内存、GPU 和网络的使用情况。

## 功能

- **CPU** — 总体利用率 + 核心数 + 温度 + 迷你折线图
- **内存** — 利用率 + 总量/已用（如 `32G / 8.3G`）+ 迷你折线图
- **GPU** — 利用率 + 显存总量/已用（如 `显存 11G / 3.1G`）+ 温度 + 迷你折线图（NVIDIA）
- **网络** — 下行/上行并排显示（下行大字号亮绿主值 + 上行小字号红色辅助，如 `↓ 3.5 MB/s ↑ 1.2 MB/s`）+ 迷你图上下分区双线（绿=下行在上、红=上行在下，各自独立缩放），布局固定不跳动；**只统计物理网卡流量**（排除 TUN/VPN/虚拟机等虚拟网卡，避免 Clash/V2Ray TUN 模式下速度翻倍）
- **深色科技风 UI**，半透明背景
- **窗口置顶**、无边框、可拖拽
- **窗口位置自动记忆**，重启恢复
- **高负载颜色提醒**（>=80% 黄，>=95% 红）
- **应用图标**（`3.ico`，exe 文件图标 + 运行时窗口图标）
- **右键菜单**：
  - 显示/隐藏 GPU
  - 布局切换（竖向排列 / 2×2 网格）
  - 透明度切换（正常 88% / 半透明 50% / 高透明 25%）
  - 退出程序

## 项目结构

```
├── main.py              # 程序入口（图标、日志轮转、采集线程安全停止）
├── config.py            # 全局配置（配色、字体大小、刷新间隔、网络基准带宽等）
├── requirements.txt     # Python 依赖
├── 3.ico                # 应用图标（exe + 窗口）
├── 打包.bat             # 一键打包脚本（PyInstaller 单文件，含依赖检查）
├── core/
│   ├── collector.py     # 数据采集调度器（独立线程）
│   ├── cpu_monitor.py   # CPU 监控（psutil + LibreHardwareMonitor 温度）
│   ├── memory_monitor.py# 内存监控（psutil）
│   ├── gpu_monitor.py   # GPU 监控（nvidia-ml-py + WMI 回退）
│   └── network_monitor.py# 网络监控（psutil）
└── ui/
    ├── version.py       # 应用版本号（与 README / CHANGELOG 同步）
    ├── float_window.py  # 悬浮窗主窗口
    ├── metric_widget.py # 单指标卡片组件
    └── mini_chart.py    # 迷你折线图组件
```

## 运行

### 开发者运行

```bash
pip install -r requirements.txt
python main.py
```

### 打包为 exe

```bash
cd g:\code\系统性能监控-win-悬浮窗
打包.bat                # 推荐：自动检查依赖并打包为单文件 exe
```

或直接使用 PyInstaller：

```bash
pyinstaller 系统性能监控.spec --noconfirm --clean
```

## 技术栈

| 技术 | 用途 |
|---|---|
| Python 3.10+ | 开发语言 |
| PyQt6 | GUI 框架 |
| psutil | CPU / 内存 / 网络数据采集 |
| nvidia-ml-py | NVIDIA GPU 数据采集 |
| WMI | GPU 名称回退（非 NVIDIA） |
| pythonnet | 调用 LibreHardwareMonitor 读取 CPU 温度 |
| LibreHardwareMonitorLib | 硬件传感器库（已含在项目中） |
| PyInstaller | 打包为单文件 exe |

## 配置

编辑 [config.py](config.py) 可自定义：

- 窗口尺寸
- 字体大小（数值 / 指标名称 / 辅助信息）
- 刷新间隔（默认 1000ms）
- 配色方案（深色科技风，支持自定义）
- 阈值（高负载颜色切换阈值）
- 默认透明度
- 圆角半径
- 网络利用率参考基准带宽（`NETWORK_REFERENCE_MBPS`，默认 400Mbps）
- 网络统计口径：`NETWORK_PHYSICAL_ONLY`（默认 `True` 只统计物理网卡，`False` 统计全部网卡）、`NETWORK_INCLUDE_ONLY`（网卡名白名单，非空时优先）

配置和窗口位置自动保存到 `~/.sysmon_float/` 目录。

## 更新日志

版本历史见 [CHANGELOG.md](CHANGELOG.md)。

## 注意事项

- **CPU 温度需要以管理员身份运行**，否则 LibreHardwareMonitor 可能读取不到温度传感器
- GPU 利用率需要 NVIDIA 显卡并安装 `nvidia-ml-py`
- 非 NVIDIA 显卡可通过 WMI 显示 GPU 名称，但无法获取利用率
- 打包时需将 `LibreHardwareMonitor` 目录一并包含，否则 CPU 温度功能失效（`打包.bat` 已处理）
- 打包后约 **46MB**（单文件，主要为 Qt6 DLL）

## 许可证

MIT