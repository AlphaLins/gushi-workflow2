"""
============================================
诗韵画境 - 黏土风格主题配置
Claymorphism Theme Configuration
============================================
版本: 1.0.0
创建日期: 2026-02-06

这个模块提供了完整的颜色常量和主题配置，
可以在 Python 代码中直接使用。
============================================
"""

from dataclasses import dataclass
from typing import Dict, Tuple
from PySide6.QtGui import QColor, QPalette, QBrush
from PySide6.QtCore import QObject


@dataclass
class ColorPalette:
    """颜色调色板 - 蓝色系"""
    primary: str = "#5392CE"
    secondary: str = "#94B3DF"
    accent: str = "#D4DFF1"
    dark: str = "#3A6A9E"
    light: str = "#E8F0F8"


@dataclass
class GreenPalette:
    """颜色调色板 - 绿色系（成功状态）"""
    deep: str = "#75B956"
    med: str = "#B3D49B"
    light: str = "#E0EFDC"
    dark: str = "#5A9A3D"


@dataclass
class PurplePalette:
    """颜色调色板 - 紫色系（品牌色）"""
    deep: str = "#B266A5"
    med: str = "#CDA3CB"
    light: str = "#E8DAEB"
    dark: str = "#8B4A7F"


@dataclass
class NeutralColors:
    """中性色"""
    text_primary: str = "#2C3E50"
    text_secondary: str = "#5A6C7D"
    text_disabled: str = "#9CAAB8"
    bg_primary: str = "#FFFFFF"
    bg_secondary: str = "#F8FAFB"
    bg_overlay: str = "rgba(255, 255, 255, 0.85)"


@dataclass
class FunctionalColors:
    """功能色"""
    error: str = "#E57373"
    warning: str = "#FFB74D"
    info: str = "#64B5F6"
    success: str = "#75B956"


@dataclass
class ShadowColors:
    """阴影颜色"""
    light: str = "rgba(83, 146, 206, 0.15)"
    medium: str = "rgba(83, 146, 206, 0.25)"
    dark: str = "rgba(44, 62, 80, 0.1)"


@dataclass
class BorderRadius:
    """圆角半径"""
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 20


@dataclass
class Spacing:
    """间距系统"""
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass
class Shadows:
    """阴影样式"""
    sm: str = "0 2px 4px rgba(83, 146, 206, 0.15)"
    md: str = "0 4px 12px rgba(83, 146, 206, 0.15), 0 2px 6px rgba(44, 62, 80, 0.1)"
    lg: str = "0 8px 24px rgba(83, 146, 206, 0.25), 0 4px 12px rgba(44, 62, 80, 0.1)"
    xl: str = "0 12px 32px rgba(83, 146, 206, 0.25), 0 6px 16px rgba(44, 62, 80, 0.1)"

    clay_elevated: str = (
        "0 8px 16px rgba(83, 146, 206, 0.15), "
        "0 4px 8px rgba(255, 255, 255, 0.8) inset, "
        "0 -2px 4px rgba(0, 0, 0, 0.05) inset"
    )
    clay_inset: str = (
        "0 2px 4px rgba(44, 62, 80, 0.1) inset, "
        "0 1px 2px rgba(255, 255, 255, 0.5) inset"
    )


class ClayTheme:
    """
    黏土风格主题配置类

    使用示例:
        >>> theme = ClayTheme()
        >>> print(theme.colors.blue.primary)
        #5392CE
        >>> color = QColor(theme.colors.blue.primary)
    """

    def __init__(self):
        self.colors = type('Colors', (), {
            'blue': ColorPalette(),
            'green': GreenPalette(),
            'purple': PurplePalette(),
            'neutral': NeutralColors(),
            'functional': FunctionalColors(),
            'shadow': ShadowColors()
        })()

        self.radius = BorderRadius()
        self.spacing = Spacing()
        self.shadows = Shadows()

        # 背景图片路径
        self.background_image = "C:/Users/Lin/Pictures/wallhaven-qzwde7.png"

    def get_qcolor(self, hex_color: str) -> QColor:
        """
        将十六进制颜色转换为 QColor

        Args:
            hex_color: 十六进制颜色字符串 (例如: "#5392CE")

        Returns:
            QColor 对象
        """
        return QColor(hex_color)

    def get_palette(self) -> QPalette:
        """
        创建 QPalette 对象用于应用程序

        Returns:
            配置好的 QPalette 对象
        """
        palette = QPalette()

        # 设置窗口颜色
        palette.setColor(QPalette.ColorRole.Window, QColor(self.colors.neutral.bg_secondary))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self.colors.neutral.text_primary))

        # 设置基础颜色
        palette.setColor(QPalette.ColorRole.Base, QColor(self.colors.neutral.bg_primary))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.colors.neutral.bg_secondary))

        # 设置文本颜色
        palette.setColor(QPalette.ColorRole.Text, QColor(self.colors.neutral.text_primary))
        palette.setColor(QPalette.ColorRole.Button, QColor(self.colors.neutral.bg_primary))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.colors.blue.primary))

        # 设置高亮颜色
        palette.setColor(QPalette.ColorRole.Highlight, QColor(self.colors.blue.primary))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

        return palette

    def get_style_sheet(self) -> str:
        """
        获取完整的 QSS 样式表

        Returns:
            QSS 样式字符串
        """
        try:
            with open("resources/styles/clay.qss", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def apply_to_widget(self, widget, style_type: str = ""):
        """
        将样式应用到部件

        Args:
            widget: QWidget 或其子类实例
            style_type: 样式类型标识符 (例如: "primary", "success", "elevated")
        """
        if style_type:
            widget.setProperty(style_type, True)

    def create_gradient(self, color_start: str, color_end: str) -> str:
        """
        创建 QSS 渐变字符串

        Args:
            color_start: 起始颜色
            color_end: 结束颜色

        Returns:
            QSS 渐变样式字符串
        """
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color_start}, stop:1 {color_end})"


class StyleHelper:
    """
    样式助手类 - 提供便捷的样式设置方法

    使用示例:
        >>> helper = StyleHelper()
        >>> btn = helper.primary_button("确定")
        >>> card = helper.card_widget()
    """

    def __init__(self):
        self.theme = ClayTheme()

    def primary_button(self, text: str = ""):
        """创建主按钮"""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setProperty("primary", True)
        return btn

    def secondary_button(self, text: str = ""):
        """创建次要按钮"""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setProperty("secondary", True)
        return btn

    def success_button(self, text: str = ""):
        """创建成功按钮"""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setProperty("success", True)
        return btn

    def brand_button(self, text: str = ""):
        """创建品牌按钮（紫色）"""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setProperty("brand", True)
        return btn

    def danger_button(self, text: str = ""):
        """创建危险按钮"""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setProperty("danger", True)
        return btn

    def icon_button(self, icon=None):
        """创建图标按钮"""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton()
        btn.setProperty("icon", True)
        if icon:
            btn.setIcon(icon)
        return btn

    def circle_button(self, icon=None):
        """创建圆形按钮"""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton()
        btn.setProperty("circle", True)
        if icon:
            btn.setIcon(icon)
        return btn

    def card_frame(self, elevated: bool = True) -> 'QFrame':
        """创建卡片容器"""
        from PySide6.QtWidgets import QFrame
        frame = QFrame()
        if elevated:
            frame.setProperty("elevated", True)
        else:
            frame.setProperty("card", True)
        return frame

    def heading_label(self, text: str = ""):
        """创建标题标签"""
        from PySide6.QtWidgets import QLabel
        label = QLabel(text)
        label.setProperty("heading", True)
        return label

    def subheading_label(self, text: str = ""):
        """创建副标题标签"""
        from PySide6.QtWidgets import QLabel
        label = QLabel(text)
        label.setProperty("subheading", True)
        return label

    def caption_label(self, text: str = ""):
        """创建说明文本标签"""
        from PySide6.QtWidgets import QLabel
        label = QLabel(text)
        label.setProperty("caption", True)
        return label

    def glass_widget(self) -> 'QWidget':
        """创建玻璃态效果部件"""
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        widget.setProperty("glass", True)
        return widget


# 预定义主题实例
THEME = ClayTheme()
HELPER = StyleHelper()


# 便捷导出
__all__ = [
    'ClayTheme',
    'StyleHelper',
    'ColorPalette',
    'GreenPalette',
    'PurplePalette',
    'NeutralColors',
    'FunctionalColors',
    'ShadowColors',
    'BorderRadius',
    'Spacing',
    'Shadows',
    'THEME',
    'HELPER'
]


if __name__ == "__main__":
    # 测试代码
    theme = ClayTheme()
    print(f"主色调: {theme.colors.blue.primary}")
    print(f"成功色: {theme.colors.green.deep}")
    print(f"品牌色: {theme.colors.purple.deep}")
    print(f"圆角 (中): {theme.radius.md}px")
    print(f"间距 (大): {theme.spacing.lg}px")

    helper = StyleHelper()
    print(f"\n样式助手已创建")
    print(f"背景图片路径: {theme.background_image}")
