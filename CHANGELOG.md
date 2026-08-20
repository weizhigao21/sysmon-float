# 更新日志

本项目所有重要变更记录在此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
