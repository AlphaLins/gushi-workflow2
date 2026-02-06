import sys
import os
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径
    适用于开发环境和 PyInstaller 打包后的环境
    
    Args:
        relative_path: 相对路径 (例如 'resources/styles/modern.qss')
        
    Returns:
        Path 对象
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = Path(sys._MEIPASS)
    else:
        # 开发环境：项目根目录
        # 假设此文件在 utils/resource_path.py，向上两级是根目录
        base_path = Path(__file__).resolve().parent.parent
    
    return base_path / relative_path
