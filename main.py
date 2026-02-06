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
from utils.resource_path import resource_path


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

    # 注册 App 实例到全局状态
    get_app_state().set_app(app)

    # 设置应用样式
    app.setStyle("Fusion")

    # 设置全局样式表
    _set_app_style(app)

    # 设置日志
    # 使用当前运行目录作为日志目录，确保便携性
    log_dir = Path.cwd() / "logs"
    logger = setup_logging(log_dir)
    logger.info("应用启动")

    # 检查是否首次运行
    if not _check_first_run():
        logger.info("用户取消了首次运行配置，应用退出")
        sys.exit(0)

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 退出处理
    def handle_exit():
        logger.info("应用退出")

    app.aboutToQuit.connect(handle_exit)

    # 运行应用
    sys.exit(app.exec())


def _check_first_run() -> bool:
    """
    检查是否首次运行，如果首次运行则显示配置向导

    Returns:
        bool: 是否应该继续启动应用
    """
    from config.api_config import APIConfig
    from PySide6.QtWidgets import QDialog

    # 检查用户配置文件
    config_path = Path.home() / '.guui_config.json'

    # 如果配置文件不存在，显示首次运行向导
    if not config_path.exists():
        from components.first_run_wizard import FirstRunWizard

        logger = setup_logging(Path.cwd() / "logs")
        logger.info("首次运行，显示配置向导")

        wizard = FirstRunWizard()
        result = wizard.exec()

        if result == QDialog.Accepted:
            logger.info("首次运行配置完成")
            return True
        else:
            logger.info("用户取消了首次运行配置")
            return False

    return True


def _set_app_style(app: QApplication, theme: str = "modern"):
    """
    设置应用样式
    
    Args:
        app: QApplication 实例
        theme: 主题名称 ('modern' 或 'dark')
    """
    # 加载 QSS 样式表
    style_path = resource_path(f"resources/styles/{theme}.qss")
    
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
