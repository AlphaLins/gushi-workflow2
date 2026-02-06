"""
设置面板
API 配置、模型选择等设置界面
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QPushButton, QLabel,
    QTabWidget, QScrollArea, QMessageBox
)
from PySide6.QtCore import Signal, Qt, QThread
from pathlib import Path

from core.app import get_app_state
from config.api_config import Models


class SettingsPanel(QWidget):
    """设置面板 - API 配置和模型选择"""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_state = get_app_state()
        self.config = self.app_state.config

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 创建内容部件
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # API 配置组
        api_group = self._create_api_group()
        content_layout.addWidget(api_group)

        # 模型配置组
        model_group = self._create_model_group()
        content_layout.addWidget(model_group)

        # 视频配置组
        video_group = self._create_video_group()
        content_layout.addWidget(video_group)

        # 音乐配置组
        music_group = self._create_music_group()
        content_layout.addWidget(music_group)

        # 生成配置组
        generation_group = self._create_generation_group()
        content_layout.addWidget(generation_group)

        content_layout.addStretch()

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self._reset_to_default)
        button_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(save_btn)

        content_layout.addLayout(button_layout)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_api_group(self) -> QGroupBox:
        """创建 API 配置组"""
        group = QGroupBox("API 配置")
        layout = QVBoxLayout()

        # 表单布局
        form_layout = QFormLayout()

        # API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-xxx...")
        form_layout.addRow("API Key:", self.api_key_edit)

        # Base URL
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://vipstar.vip")
        form_layout.addRow("Base URL:", self.base_url_edit)

        # 超时时间
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)
        self.timeout_spin.setValue(120)
        self.timeout_spin.setSuffix(" 秒")
        form_layout.addRow("超时时间:", self.timeout_spin)

        # 最大重试次数
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.max_retries_spin.setValue(5)
        form_layout.addRow("最大重试次数:", self.max_retries_spin)

        # 使用 Google 原生 SDK
        self.native_google_check = QCheckBox("使用 Google 原生 SDK（仅 Gemini）")
        form_layout.addRow("", self.native_google_check)

        layout.addLayout(form_layout)

        # 测试连接按钮和状态
        test_layout = QHBoxLayout()

        self.test_connection_btn = QPushButton("测试连接")
        self.test_connection_btn.clicked.connect(self._test_connection)
        test_layout.addWidget(self.test_connection_btn)

        self.connection_status_label = QLabel("未测试")
        self.connection_status_label.setStyleSheet("color: #999; padding: 5px;")
        test_layout.addWidget(self.connection_status_label)

        test_layout.addStretch()

        layout.addLayout(test_layout)

        group.setLayout(layout)
        return group

    def _create_combo_row(self, combo: QComboBox, model_type: str) -> QHBoxLayout:
        """创建带有保存按钮的下拉框行"""
        row = QHBoxLayout()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)  # 手动处理插入
        row.addWidget(combo, stretch=1)
        
        save_btn = QPushButton("💾")
        save_btn.setToolTip("保存当前填写的模型为自定义模型")
        save_btn.setFixedWidth(30)
        save_btn.clicked.connect(lambda: self._save_custom_model(combo, model_type))
        row.addWidget(save_btn)
        
        return row

    def _save_custom_model(self, combo: QComboBox, model_type: str):
        """保存自定义模型"""
        model_name = combo.currentText().strip()
        if not model_name:
            return
            
        # 检查是否已存在
        for i in range(combo.count()):
            if combo.itemText(i) == model_name:
                return

        # 添加到配置
        if model_type not in self.config.custom_models:
            self.config.custom_models[model_type] = []
        
        if model_name not in self.config.custom_models[model_type]:
            self.config.custom_models[model_type].append(model_name)
            self.app_state.update_config(custom_models=self.config.custom_models)
            
            # 添加到下拉框
            combo.addItem(model_name, model_name)
            combo.setCurrentIndex(combo.count() - 1)
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "成功", f"模 '{model_name}' 已保存到自定义列表")

    def _create_model_group(self) -> QGroupBox:
        """创建模型配置组"""
        group = QGroupBox("文本和图像模型")
        layout = QFormLayout()

        # 文本模型
        self.text_model_combo = QComboBox()
        for model_id, name in Models.TEXT_MODELS.items():
            self.text_model_combo.addItem(name, model_id)
        layout.addRow("文本模型:", self._create_combo_row(self.text_model_combo, 'text'))

        # 图像模型
        self.image_model_combo = QComboBox()
        for model_id, name in Models.IMAGE_MODELS.items():
            self.image_model_combo.addItem(name, model_id)
        layout.addRow("图像模型:", self._create_combo_row(self.image_model_combo, 'image'))

        # 温度参数
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        layout.addRow("温度:", self.temperature_spin)

        # Top-p 参数
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.9)
        layout.addRow("Top-p:", self.top_p_spin)

        group.setLayout(layout)
        return group

    def _create_video_group(self) -> QGroupBox:
        """创建视频配置组"""
        group = QGroupBox("视频生成配置")
        layout = QFormLayout()

        # 视频模型
        self.video_model_combo = QComboBox()
        for model_id, name in Models.VIDEO_MODELS.items():
            self.video_model_combo.addItem(name, model_id)
        layout.addRow("视频模型:", self._create_combo_row(self.video_model_combo, 'video'))

        # 宽高比
        self.aspect_ratio_combo = QComboBox()
        for ratio, name in Models.ASPECT_RATIOS.items():
            self.aspect_ratio_combo.addItem(name, ratio)
        layout.addRow("宽高比:", self.aspect_ratio_combo)

        # 分辨率
        self.size_combo = QComboBox()
        self.size_combo.addItem("720P", "720P")
        self.size_combo.addItem("1080P", "1080P")
        layout.addRow("分辨率:", self.size_combo)

        group.setLayout(layout)
        return group

    def _create_music_group(self) -> QGroupBox:
        """创建音乐配置组"""
        group = QGroupBox("音乐生成配置")
        layout = QFormLayout()

        # 音乐模型
        self.music_model_combo = QComboBox()
        for model_id, name in Models.MUSIC_MODELS.items():
            self.music_model_combo.addItem(name, model_id)
        layout.addRow("音乐模型:", self._create_combo_row(self.music_model_combo, 'music'))

        # 风格标签
        self.music_tags_edit = QLineEdit()
        self.music_tags_edit.setPlaceholderText("chinese traditional,emotional")
        layout.addRow("默认风格:", self.music_tags_edit)

        group.setLayout(layout)
        return group

    def _create_generation_group(self) -> QGroupBox:
        """创建生成配置组"""
        group = QGroupBox("生成配置")
        layout = QFormLayout()

        # 每句诗生成示例数
        self.example_count_spin = QSpinBox()
        self.example_count_spin.setRange(1, 10)
        self.example_count_spin.setValue(3)
        layout.addRow("每句诗生成示例数:", self.example_count_spin)

        # 使用风格锚定
        self.style_anchors_check = QCheckBox("使用风格锚定（保持多图风格一致）")
        self.style_anchors_check.setChecked(True)
        layout.addRow("", self.style_anchors_check)

        group.setLayout(layout)
        return group

    def _load_custom_models(self, combo: QComboBox, model_type: str):
        """加载自定义模型到下拉框"""
        if not hasattr(self.config, 'custom_models'):
            return
            
        custom_models = self.config.custom_models.get(model_type, [])
        for model_name in custom_models:
            # 检查是否已存在
            exists = False
            for i in range(combo.count()):
                if combo.itemText(i) == model_name:
                    exists = True
                    break
            
            if not exists:
                combo.addItem(model_name, model_name)

    def _load_config(self):
        """加载配置"""
        config = self.config

        # API 配置
        self.api_key_edit.setText(config.api_key)
        self.base_url_edit.setText(config.base_url)
        self.timeout_spin.setValue(config.timeout)
        self.max_retries_spin.setValue(config.max_retries)
        self.native_google_check.setChecked(config.use_native_google)

        # 加载自定义模型
        self._load_custom_models(self.text_model_combo, 'text')
        self._load_custom_models(self.image_model_combo, 'image')
        self._load_custom_models(self.video_model_combo, 'video')
        self._load_custom_models(self.music_model_combo, 'music')

        # 文本模型
        for i in range(self.text_model_combo.count()):
            if self.text_model_combo.itemData(i) == config.model or self.text_model_combo.itemText(i) == config.model:
                self.text_model_combo.setCurrentIndex(i)
                break
        else:
             self.text_model_combo.setCurrentText(config.model)

        # 图像模型
        for i in range(self.image_model_combo.count()):
            if self.image_model_combo.itemData(i) == config.image_model or self.image_model_combo.itemText(i) == config.image_model:
                self.image_model_combo.setCurrentIndex(i)
                break
        else:
             self.image_model_combo.setCurrentText(config.image_model)

        # 生成参数
        self.temperature_spin.setValue(config.temperature)
        self.top_p_spin.setValue(config.top_p)

        # 视频配置
        for i in range(self.video_model_combo.count()):
            if self.video_model_combo.itemData(i) == config.video_model or self.video_model_combo.itemText(i) == config.video_model:
                self.video_model_combo.setCurrentIndex(i)
                break
        else:
             self.video_model_combo.setCurrentText(config.video_model)

        for i in range(self.aspect_ratio_combo.count()):
            if self.aspect_ratio_combo.itemData(i) == config.video_aspect_ratio:
                self.aspect_ratio_combo.setCurrentIndex(i)
                break

        for i in range(self.size_combo.count()):
            if self.size_combo.itemData(i) == config.video_size:
                self.size_combo.setCurrentIndex(i)
                break

        # 音乐配置
        for i in range(self.music_model_combo.count()):
            if self.music_model_combo.itemData(i) == config.music_model or self.music_model_combo.itemText(i) == config.music_model:
                self.music_model_combo.setCurrentIndex(i)
                break
        else:
             self.music_model_combo.setCurrentText(config.music_model)

        self.music_tags_edit.setText(config.music_tags)

        # 生成配置
        self.example_count_spin.setValue(config.example_count)
        self.style_anchors_check.setChecked(config.style_anchors)

    def _save_config(self):
        """保存配置"""
        # 收集配置
        config_updates = {
            'api_key': self.api_key_edit.text(),
            'base_url': self.base_url_edit.text(),
            'timeout': self.timeout_spin.value(),
            'max_retries': self.max_retries_spin.value(),
            'use_native_google': self.native_google_check.isChecked(),
            'model': self.text_model_combo.currentData() or self.text_model_combo.currentText(),
            'image_model': self.image_model_combo.currentData() or self.image_model_combo.currentText(),
            'temperature': self.temperature_spin.value(),
            'top_p': self.top_p_spin.value(),
            'video_model': self.video_model_combo.currentData() or self.video_model_combo.currentText(),
            'video_aspect_ratio': self.aspect_ratio_combo.currentData(),
            'video_size': self.size_combo.currentData(),
            'music_model': self.music_model_combo.currentData() or self.music_model_combo.currentText(),
            'music_tags': self.music_tags_edit.text(),
            'example_count': self.example_count_spin.value(),
            'style_anchors': self.style_anchors_check.isChecked(),
        }

        # 验证 API Key
        if not config_updates['api_key'] or config_updates['api_key'] == "sk-xxx...":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "配置错误", "请输入有效的 API Key")
            return

        # 更新配置
        self.app_state.update_config(**config_updates)

        self.settings_changed.emit()

        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "保存成功", "配置已保存")

    def _reset_to_default(self):
        """重置为默认配置"""
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "重置配置",
            "确定要重置为默认配置吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.api_key_edit.setText("sk-xxx...")
            self.base_url_edit.setText("https://vipstar.vip")
            self.timeout_spin.setValue(120)
            self.max_retries_spin.setValue(5)
            self.native_google_check.setChecked(False)
            self.temperature_spin.setValue(0.7)
            self.top_p_spin.setValue(0.9)
            self.example_count_spin.setValue(3)
            self.style_anchors_check.setChecked(True)
            self.music_tags_edit.setText("chinese traditional,emotional")

    def _test_connection(self):
        """测试 API 连接"""
        api_key = self.api_key_edit.text().strip()
        base_url = self.base_url_edit.text().strip()

        # 验证输入
        if not api_key or api_key == "sk-xxx...":
            self._update_connection_status("error", "请输入有效的 API Key")
            return

        if not base_url:
            self._update_connection_status("error", "请输入 Base URL")
            return

        # 禁用按钮并更新状态
        self.test_connection_btn.setEnabled(False)
        self.test_connection_btn.setText("测试中...")
        self._update_connection_status("testing", "正在连接...")

        # 启动测试线程
        self._test_thread = ConnectionTestThread(api_key, base_url)
        self._test_thread.finished.connect(self._on_test_finished)
        self._test_thread.start()

    def _on_test_finished(self, success: bool, message: str, latency: float = None):
        """测试完成处理"""
        self.test_connection_btn.setEnabled(True)
        self.test_connection_btn.setText("测试连接")

        if success:
            if latency is not None:
                status_msg = f"连接成功 ({latency*1000:.0f}ms)"
            else:
                status_msg = "连接成功"
            self._update_connection_status("success", status_msg)
        else:
            self._update_connection_status("error", f"连接失败: {message}")

    def _update_connection_status(self, status: str, message: str):
        """更新连接状态显示"""
        colors = {
            "testing": "#FF9800",   # 橙色
            "success": "#4CAF50",    # 绿色
            "error": "#F44336",      # 红色
        }

        color = colors.get(status, "#999")
        self.connection_status_label.setText(message)
        self.connection_status_label.setStyleSheet(
            f"color: {color}; padding: 5px; background-color: #f5f5f5; border-radius: 4px;"
        )


class ConnectionTestThread(QThread):
    """API 连接测试线程"""

    finished = Signal(bool, str, float)  # success, message, latency

    def __init__(self, api_key: str, base_url: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = 30

    def run(self):
        """运行测试"""
        import time
        import requests

        try:
            # 准备测试请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gemini-2.5-flash",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10
            }

            # 发送测试请求
            start_time = time.time()

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            latency = time.time() - start_time

            # 检查响应
            if response.status_code == 200:
                self.finished.emit(True, "API 连接正常", latency)
            elif response.status_code == 401:
                self.finished.emit(False, "API Key 无效或已过期")
            elif response.status_code == 429:
                self.finished.emit(False, "请求过于频繁，请稍后再试")
            elif response.status_code == 500:
                self.finished.emit(False, "服务器内部错误")
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}"
                self.finished.emit(False, error_msg)

        except requests.exceptions.Timeout:
            self.finished.emit(False, "连接超时，请检查网络或 Base URL")
        except requests.exceptions.ConnectionError:
            self.finished.emit(False, "无法连接到服务器，请检查 Base URL")
        except Exception as e:
            self.finished.emit(False, f"未知错误: {str(e)}")
