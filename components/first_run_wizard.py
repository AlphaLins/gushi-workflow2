"""
首次运行向导
引导用户完成初始配置
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QWizard,
    QWizardPage, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from config.api_config import APIConfig, Models


class FirstRunWizard(QWizard):
    """首次运行向导"""

    config_saved = Signal(object)  # 配置保存信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("诗韵画境 - 初始配置向导")
        self.setMinimumSize(600, 500)
        self.setWindowTitle("诗韵画境 - 欢迎使用")
        self.setWizardStyle(QWizard.ModernStyle)

        # 添加页面
        self.addPage(WelcomePage(self))
        self.addPage(APIConfigPage(self))
        self.addPage(ModelConfigPage(self))
        self.addPage(FinishPage(self))

        # 存储配置
        self._config = APIConfig()

    def get_config(self):
        """获取配置"""
        return self._config

    def set_config(self, config: APIConfig):
        """设置配置"""
        self._config = config


class WelcomePage(QWizardPage):
    """欢迎页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("欢迎使用诗韵画境")
        self.setSubTitle("将中国古典诗词转化为图像、视频和音乐的 AI 创作平台")

        layout = QVBoxLayout(self)

        # 欢迎文字
        welcome_label = QLabel(
            "<h2>欢迎使用诗韵画境！</h2>"
            "<p>这是您第一次运行诗韵画境，让我们来完成一些基本配置。</p>"
            "<p>您需要：</p>"
            "<ul>"
            "<li>配置 API 密钥（用于调用 AI 服务）</li>"
            "<li>选择默认的 AI 模型</li>"
            "<li>设置生成参数</li>"
            "</ul>"
            "<p>配置可以随时在设置页面中修改。</p>"
        )
        welcome_label.setWordWrap(True)
        welcome_label.setTextFormat(Qt.RichText)
        layout.addWidget(welcome_label)

        layout.addStretch()

        # 提示
        tip_label = QLabel(
            "<p><b>提示：</b>如果您还没有 API 密钥，可以在设置页面中选择使用本地上传图片的方式生成视频。</p>"
        )
        tip_label.setWordWrap(True)
        tip_label.setTextFormat(Qt.RichText)
        tip_label.setStyleSheet("color: #666; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        layout.addWidget(tip_label)


class APIConfigPage(QWizardPage):
    """API 配置页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("配置 API")
        self.setSubTitle("请输入您的 API 密钥和服务器地址")

        layout = QVBoxLayout(self)

        # API 密钥
        key_group = QGroupBox("API 密钥（必填）")
        key_layout = QGridLayout(key_group)

        key_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("sk-xxxxxxxxxxxxxxxxxxxxxxx")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        key_layout.addWidget(self.api_key_edit, 0, 1)

        layout.addWidget(key_group)

        # 服务器配置
        server_group = QGroupBox("服务器配置（可选）")
        server_layout = QGridLayout(server_group)

        server_layout.addWidget(QLabel("Base URL:"), 0, 0)
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.example.com")
        self.base_url_edit.setText("https://vipstar.vip")
        server_layout.addWidget(self.base_url_edit, 0, 1)

        layout.addWidget(server_group)

        # 注册字段
        self.registerField("apiKey*", self.api_key_edit)
        self.registerField("baseUrl", self.base_url_edit)

    def initializePage(self):
        """初始化页面"""
        wizard = self.wizard()
        if isinstance(wizard, FirstRunWizard):
            config = wizard.get_config()
            if config.api_key:
                self.api_key_edit.setText(config.api_key)
            if config.base_url:
                self.base_url_edit.setText(config.base_url)


class ModelConfigPage(QWizardPage):
    """模型配置页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("选择模型")
        self.setSubTitle("选择您想使用的 AI 模型")

        layout = QVBoxLayout(self)

        # 文本模型
        text_group = QGroupBox("文本模型（诗词生成）")
        text_layout = QGridLayout(text_group)

        text_layout.addWidget(QLabel("模型:"), 0, 0)
        self.text_model_combo = QComboBox()
        for model_id, name in Models.TEXT_MODELS.items():
            self.text_model_combo.addItem(name, model_id)
        self.text_model_combo.setCurrentIndex(0)
        text_layout.addWidget(self.text_model_combo, 0, 1)

        layout.addWidget(text_group)

        # 图像模型
        image_group = QGroupBox("图像模型")
        image_layout = QGridLayout(image_group)

        image_layout.addWidget(QLabel("模型:"), 0, 0)
        self.image_model_combo = QComboBox()
        for model_id, name in Models.IMAGE_MODELS.items():
            self.image_model_combo.addItem(name, model_id)
        self.image_model_combo.setCurrentIndex(0)
        image_layout.addWidget(self.image_model_combo, 0, 1)

        layout.addWidget(image_group)

        # 视频模型
        video_group = QGroupBox("视频模型")
        video_layout = QGridLayout(video_group)

        video_layout.addWidget(QLabel("模型:"), 0, 0)
        self.video_model_combo = QComboBox()
        for model_id, name in Models.VIDEO_MODELS.items():
            self.video_model_combo.addItem(name, model_id)
        # 默认选择 grok-video-3-10s
        for i in range(self.video_model_combo.count()):
            if self.video_model_combo.itemData(i) == "grok-video-3-10s":
                self.video_model_combo.setCurrentIndex(i)
                break
        video_layout.addWidget(self.video_model_combo, 0, 1)

        layout.addWidget(video_group)

        layout.addStretch()

    def initializePage(self):
        """初始化页面"""
        wizard = self.wizard()
        if isinstance(wizard, FirstRunWizard):
            config = wizard.get_config()
            # 设置文本模型
            for i in range(self.text_model_combo.count()):
                if self.text_model_combo.itemData(i) == config.model:
                    self.text_model_combo.setCurrentIndex(i)
                    break
            # 设置图像模型
            for i in range(self.image_model_combo.count()):
                if self.image_model_combo.itemData(i) == config.image_model:
                    self.image_model_combo.setCurrentIndex(i)
                    break
            # 设置视频模型
            for i in range(self.video_model_combo.count()):
                if self.video_model_combo.itemData(i) == config.video_model:
                    self.video_model_combo.setCurrentIndex(i)
                    break


class FinishPage(QWizardPage):
    """完成页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("配置完成")
        self.setSubTitle("您的配置已准备就绪")

        layout = QVBoxLayout(self)

        # 摘要
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.RichText)
        layout.addWidget(self.summary_label)

        layout.addStretch()

        # 完成提示
        finish_label = QLabel(
            "<p><b>配置完成！</b></p>"
            "<p>点击「完成」开始使用诗韵画境。</p>"
            "<p>您随时可以在设置页面中修改这些配置。</p>"
        )
        finish_label.setWordWrap(True)
        finish_label.setTextFormat(Qt.RichText)
        layout.addWidget(finish_label)

    def initializePage(self):
        """初始化页面"""
        wizard = self.wizard()
        if isinstance(wizard, FirstRunWizard):
            # 收集所有配置
            api_page = wizard.page(1)
            model_page = wizard.page(2)

            # 更新配置
            config = wizard.get_config()
            config.api_key = api_page.api_key_edit.text()
            config.base_url = api_page.base_url_edit.text()
            config.model = model_page.text_model_combo.currentData()
            config.image_model = model_page.image_model_combo.currentData()
            config.video_model = model_page.video_model_combo.currentData()

            # 显示摘要
            self.summary_label.setText(
                "<h3>配置摘要</h3>"
                f"<p><b>API Key:</b> {'*' * 20}</p>"
                f"<p><b>服务器:</b> {config.base_url}</p>"
                f"<p><b>文本模型:</b> {model_page.text_model_combo.currentText()}</p>"
                f"<p><b>图像模型:</b> {model_page.image_model_combo.currentText()}</p>"
                f"<p><b>视频模型:</b> {model_page.video_model_combo.currentText()}</p>"
            )

    def validatePage(self):
        """验证页面"""
        wizard = self.wizard()
        if isinstance(wizard, FirstRunWizard):
            config = wizard.get_config()
            # 保存配置
            config.save()
            wizard.config_saved.emit(config)
        return True
