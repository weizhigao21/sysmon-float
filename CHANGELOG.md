# 更新日志

本项目所有重要变更记录在此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [v1.0.4] - 2026-08-21

### 修复

- 修复网络下载/上传速度显示约为实际 **2 倍**的问题：Clash/V2Ray 等代理开启 TUN 模式时，同一份流量会被物理网卡与虚拟隧道网卡（如 `Meta Tunnel`）各计数一次，`psutil.net_io_counters()` 聚合值虚高
- 网络速度统计改为**只统计物理网卡**（以太网/WiFi）：通过 `GetAdaptersAddresses` 识别接口类型（IfType 6/71）并排除 TUN/VMware/蓝牙/回环等虚拟网卡，识别结果缓存 120s；识别失败自动回退为全部网卡聚合

### 新增

- 配置项 `NETWORK_PHYSICAL_ONLY`（默认 `True`，只统计物理网卡；`False` 恢复旧行为统计全部网卡）
- 配置项 `NETWORK_INCLUDE_ONLY`（网卡名白名单，非空时优先于自动检测，如 `["以太网"]`）

## [v1.0.3] - 2026-08-20

### 新增

- 网络迷你图支持**上下行双线显示**：下行绿线 + 上行红线
- 双线**上下分区**：下行固定在上半区、上行固定在下半区，各自独立缩放，小波动也清晰可见
- 迷你图 y 轴自适应缩放（`MiniChart` 新增 `set_series(series, split=True)` 接口）
- 上行文字颜色改为红色（`COLORS.net_sent`，与上行线统一）

### 变更

- `COLORS.net_sent` 由 `#b8b8b8` 改为 `#ef5350`；删除冗余的 `net_sent_line` 配置

## [v1.0.2] - 2026-08-20

### 优化

- 网络上行/下行改为**同一行并排显示**（富文本）：下行 18px 亮绿主值 + 上行 14px 亮灰辅助，充分利用卡片横向空间，视觉更紧凑
- 上行颜色 `#888888` → `#b8b8b8`（深色背景下更清晰），字号 11px → 14px（与下行差距收窄，主次仍分明）
- 新增配置项：`COLORS.net_sent`（上行颜色）、`FONT_SIZE_NET_SENT`（上行字号）

## [v1.0.1] - 2026-08-20

### 修复

- 修复网络卡片上下行速度显示反复跳动的问题：数值文本长度波动（如 `↓ 0 B/s` ↔ `↓ 123.4 MB/s`）导致名称/数值布局在横竖之间反复切换
- 网络卡片改为固定垂直布局（`MetricWidget` 新增 `auto_layout` 参数），不再随数值长度切换

### 优化

- 网络上行/下行分开显示：下行作主值（大字号）、上行放辅助行（小字号），互不干扰

## [v1.0.0] - 2026-08-20

### 新增

- 应用图标：接入 `3.ico`，同时生效于 exe 文件图标与运行时窗口图标
- `.gitignore`（忽略 `__pycache__/`、`build/`、`dist/`、`*.log` 等）

### 修复

- 修复采集日志中网络上传/下载箭头方向写反的问题（上传应配 `↑`，下载应配 `↓`）
- 修复 GPU 查询瞬时失败时历史数据不追加、图表断裂的问题（失败时补 0）
- 修复 GPU 不可用时右键菜单「显示/隐藏 GPU」仍可点击、显示 N/A 卡片的问题
- 修复 WMI 回退场景下 `AdapterRAM` 对 >4GB 显存溢出回绕的问题（补充注释说明）

### 优化

- 采集线程停止改为 `BlockingQueuedConnection` 在线程内安全停止，确保 `QTimer.deleteLater` 执行并释放 LibreHardwareMonitor / NVML 资源
- 日志改为 INFO 级别 + 轮转（1MB × 3），避免长时间运行日志文件无限膨胀
- CPU 温度采集增加 5 秒缓存，降低 LibreHardwareMonitor 传感器遍历开销
- 网络利用率参考基准带宽可配置（`NETWORK_REFERENCE_MBPS`，默认 400Mbps）
- 迷你折线图支持单数据点绘制（圆点），不再空白
- 指标数值横/竖布局切换增加滞回区间，避免文本长度在阈值边界抖动时反复重建布局
- 悬浮窗背景色只解析一次并缓存，减少每帧 `paintEvent` 开销

### 清理

- 删除未使用的回调注册机制（`register_callback` / `unregister_callback`）
- 删除未使用的 `WINDOW_X` / `WINDOW_Y` 配置项（窗口位置由记忆文件恢复）
- 清理根目录残留的 `run.log`、`test_redirect.log`
