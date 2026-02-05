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


def _set_app_style(app: QApplication):
    """设置应用样式"""
    app.setStyleSheet("""
        /* 全局样式 */
        * {
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
            font-size: 10pt;
        }

        /* 主窗口 */
        QMainWindow {
            background-color: #f5f5f5;
        }

        /* 标签页 */
        QTabWidget::pane {
            border: 1px solid #e0e0e0;
            background-color: #ffffff;
            border-radius: 4px;
        }

        QTabBar::tab {
            background-color: #f0f0f0;
            color: #333;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }

        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #2196F3;
            font-weight: bold;
        }

        QTabBar::tab:hover:!selected {
            background-color: #e8e8e8;
        }

        /* 按钮样式 */
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            min-width: 80px;
        }

        QPushButton:hover {
            background-color: #1976D2;
        }

        QPushButton:pressed {
            background-color: #0D47A1;
        }

        QPushButton:disabled {
            background-color: #e0e0e0;
            color: #999;
        }

        QPushButton:text {
            background-color: #f5f5f5;
            color: #333;
            border: 1px solid #e0e0e0;
        }

        QPushButton:text:hover {
            background-color: #e8e8e8;
        }

        /* 输入框样式 */
        QLineEdit, QTextEdit {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 6px;
            background-color: white;
        }

        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #2196F3;
        }

        /* 下拉框样式 */
        QComboBox {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 6px;
            background-color: white;
            min-width: 120px;
        }

        QComboBox::drop-down {
            border: none;
        }

        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }

        /* 分组框样式 */
        QGroupBox {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
            color: #666;
        }

        /* 表格样式 */
        QTableWidget {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background-color: white;
            gridline-color: #f0f0f0;
        }

        QTableWidget::item {
            padding: 6px;
        }

        QTableWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976D2;
        }

        QHeaderView::section {
            background-color: #f5f5f5;
            color: #333;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #e0e0e0;
            border-right: 1px solid #f0f0f0;
            font-weight: bold;
        }

        /* 进度条样式 */
        QProgressBar {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background-color: #f5f5f5;
            text-align: center;
        }

        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 3px;
        }

        /* 滚动条样式 */
        QScrollBar:vertical {
            border: none;
            background-color: #f5f5f5;
            width: 12px;
            margin: 0;
        }

        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            min-height: 30px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }

        QScrollBar:horizontal {
            border: none;
            background-color: #f5f5f5;
            height: 12px;
            margin: 0;
        }

        QScrollBar::handle:horizontal {
            background-color: #c0c0c0;
            min-width: 30px;
            border-radius: 6px;
        }

        QScrollBar::handle:horizontal:hover {
            background-color: #a0a0a0;
        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }

        /* 列表样式 */
        QListWidget {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background-color: white;
        }

        QListWidget::item {
            padding: 6px;
        }

        QListWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976D2;
        }

        /* 滑块样式 */
        QSlider::groove:horizontal {
            height: 6px;
            background-color: #e0e0e0;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            width: 16px;
            height: 16px;
            background-color: #2196F3;
            border-radius: 8px;
            margin: -5px 0;
        }

        QSlider::handle:horizontal:hover {
            background-color: #1976D2;
        }

        /* 菜单样式 */
        QMenuBar {
            background-color: #f5f5f5;
            border-bottom: 1px solid #e0e0e0;
        }

        QMenuBar::item {
            padding: 6px 12px;
        }

        QMenuBar::item:selected {
            background-color: #e8e8e8;
        }

        QMenu {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }

        QMenu::item {
            padding: 6px 24px;
        }

        QMenu::item:selected {
            background-color: #e3f2fd;
        }

        /* 状态栏样式 */
        QStatusBar {
            background-color: #f5f5f5;
            border-top: 1px solid #e0e0e0;
        }

        /* 工具栏样式 */
        QToolBar {
            background-color: #f5f5f5;
            border: 1px solid #e0e0e0;
            spacing: 4px;
            padding: 4px;
        }

        QToolBar::separator {
            width: 1px;
            background-color: #e0e0e0;
            margin: 4px 8px;
        }

        /* 消息框样式 */
        QMessageBox {
            background-color: white;
        }

        QMessageBox QPushButton {
            min-width: 80px;
            padding: 6px 16px;
        }
    """)


if __name__ == "__main__":
    main()
