# 系统性能监控-win-悬浮窗 - 项目笔记

## 项目概况
- Windows 桌面悬浮窗性能监控（PyQt6 + psutil + pynvml + pythonnet/LibreHardwareMonitor），版本 v1.0.0。
- 监控项：CPU（利用率/核心数/温度）、内存、GPU（NVIDIA 优先，WMI 回退）、网络（速度/利用率基准 400Mbps）。
- 运行数据目录：`~/.sysmon_float/`（app.log + window_position.json + settings.json）。

## 关键约定
- **打包**：`PYTHONPATH= python -m PyInstaller 系统性能监控.spec --noconfirm --clean`（WorkBuddy CLI 注入 sitecustomize 会阻断打包，必须置空 PYTHONPATH）。
- **图标**：`3.ico` 同时用于 exe 图标（spec EXE 段 `icon=`）与运行时窗口图标（`_resource_path()` 兼容 `_MEIPASS`）。
- **采集线程退出**：必须用 `QMetaObject.invokeMethod(collector, "shutdown", BlockingQueuedConnection)`，shutdown 是 `@pyqtSlot()`（释放 QTimer/LHM/NVML），直接跨线程调用 stop 不安全。
- **日志**：INFO + RotatingFileHandler(1MB×3)，勿改回 DEBUG（每秒多条 DEBUG 会膨胀日志）。
- **CPU 温度**：LibreHardwareMonitor 遍历开销大，已做 5s 缓存（`TEMP_CACHE_SECONDS`）。
- **网络利用率基准**：`NETWORK_REFERENCE_MBPS`（默认 400），改带宽时同步 config。

## git
- 本地已 init（原无仓库），项目级身份 weizhigao21 / weizhigao21@users.noreply.github.com。
- 首次 commit c7ec5b6（v1.0.0）。远程仓库待建（推荐名 `sysmon-float`），push 用 wincred + 代理 127.0.0.1:7897。
- `.dbg/`、`build/`、`dist/`、`*.log` 已 gitignore。

## 已知注意
- 排查 app.log 时注意：旧版打包 exe 与新实例可能混写同一日志文件（无文件锁）。
- WMI 回退时 AdapterRAM 对 >4GB 显存溢出（uint32 限制），显存仅供参考。
