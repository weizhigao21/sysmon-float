"""系统性能监控悬浮窗 - 入口"""

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt6.QtCore import QMetaObject, Qt, QThread
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from config import CONFIG
from core.collector import Collector
from ui.float_window import FloatWindow


def _resource_path(relative: str) -> Path:
    """获取资源路径，兼容开发环境与 PyInstaller 打包环境"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).parent / relative


def _setup_logging() -> None:
    """初始化日志：默认 INFO 级别 + 轮转（1MB × 3），避免长时间运行日志膨胀"""
    log_path = CONFIG.config_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                log_path, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8"
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info(f"日志文件: {log_path}")


def main() -> int:
    _setup_logging()
    logging.info("程序启动...")
    try:
        app = QApplication(sys.argv)
        logging.info("QApplication 创建完成")

        # 设置窗口图标（任务栏 / Alt-Tab / 系统菜单）
        icon_path = _resource_path("3.ico")
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            logging.info(f"窗口图标已设置: {icon_path}")
        else:
            logging.warning(f"图标文件不存在: {icon_path}")

        # 设置全局字体
        from PyQt6.QtGui import QFont

        font = QFont(CONFIG.FONT_FAMILY)
        font.setStyleHint(QFont.StyleHint.Monospace)
        app.setFont(font)

        collector = Collector()
        logging.info(f"Collector 创建完成，GPU 可用: {collector.get_gpu_availability()}")

        # 将 Collector 移到独立工作线程，避免 WMI/psutil 查询阻塞 UI
        collector_thread = QThread()
        collector.moveToThread(collector_thread)
        collector_thread.started.connect(collector.start)

        window = FloatWindow(collector)
        logging.info("FloatWindow 创建完成")
        window.show()
        logging.info("FloatWindow 已显示")
        logging.info(
            f"窗口可见性: {window.isVisible()}, "
            f"几何: {window.geometry()}, "
            f"透明度: {window.windowOpacity()}"
        )

        collector_thread.start()
        logging.info("采集器工作线程已启动")

        exit_code = app.exec()
        # 通过 BlockingQueuedConnection 在 collector 线程内安全停止并释放资源，
        # 确保 QTimer.deleteLater / NVML / LHM 在事件循环退出前完成
        QMetaObject.invokeMethod(
            collector, "shutdown", Qt.ConnectionType.BlockingQueuedConnection
        )
        collector_thread.quit()
        collector_thread.wait()
        logging.info("程序退出")
        return exit_code
    except Exception:
        logging.exception("程序运行异常")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    sys.exit(main())
