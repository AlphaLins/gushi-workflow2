#!/usr/bin/env python3
"""
诗韵画境 - Poetry to Image
主入口文件

将中国古典诗词转化为图像、视频和音乐的 AI 创作平台
"""
import sys
import os

# 添加项目根目录到 Python 路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.main_window import MainWindow
from core.app import get_app_state
from utils.logger import setup_logging


def main():
    """主函数"""
    # 设置高 DPI 缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("诗韵画境")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Guui")

    # 设置应用样式
    app.setStyle("Fusion")

    # 设置全局样式表
    _set_app_style(app)

    # 设置日志
    log_dir = Path(ROOT_DIR) / "logs"
    logger = setup_logging(log_dir)
    logger.info("应用启动")

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 退出处理
    def handle_exit():
        logger.info("应用退出")

    app.aboutToQuit.connect(handle_exit)

    # 运行应用
    sys.exit(app.exec())


def _set_app_style(app: QApplication, theme: str = "modern"):
    """
    设置应用样式
    
    Args:
        app: QApplication 实例
        theme: 主题名称 ('modern' 或 'dark')
    """
    # 加载 QSS 样式表
    style_path = Path(ROOT_DIR) / "resources" / "styles" / f"{theme}.qss"
    
    if style_path.exists():
        with open(style_path, "r", encoding="utf-8") as f:
            qss = f.read()
            app.setStyleSheet(qss)
            print(f"✓ 已加载 {theme} 主题")
    else:
        print(f"⚠️  主题文件不存在: {style_path}")
        # 使用默认简单样式
        app.setStyleSheet("""
            * {
                font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
                font-size: 10pt;
            }
            
            QMainWindow {
                background-color: #f5f5f5;
            }
            
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
        """)


if __name__ == "__main__":
    main()
