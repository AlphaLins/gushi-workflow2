"""
诗词输入页面
用户输入诗词，解析诗句，选择风格
"""
import re
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QTextEdit, QPushButton, QLabel, QComboBox,
    QGroupBox, QScrollArea, QMessageBox
)
from PySide6.QtCore import Signal, Qt, QThread
from PySide6.QtGui import QFont

from core.app import get_app_state
from config.api_config import Models
from utils.style_anchor import StylePreset
from schemas.poetry import PoetryPromptsResponse, VersePrompts, ImagePrompt


class PoetryInputPage(QWidget):
    """
    诗词输入页面

    功能：
    1. 文本编辑器输入诗词
    2. 按钮解析诗句
    3. 风格选择
    4. 生成提示词
    """

    verses_parsed = Signal(list)  # 解析诗句信号
    prompts_generated = Signal(object)  # 生成提示词信号

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_state = get_app_state()
        self.verses: List[str] = []
        self.prompts: Optional[PoetryPromptsResponse] = None

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("输入诗词")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # 主内容区（左右布局）
        content_layout = QHBoxLayout()

        # 左侧：输入区域
        input_widget = self._create_input_widget()
        content_layout.addWidget(input_widget, 1)

        # 右侧：配置区域
        config_widget = self._create_config_widget()
        content_layout.addWidget(config_widget, 0)

        layout.addLayout(content_layout)

        # 底部：解析结果显示
        result_group = self._create_result_widget()
        layout.addWidget(result_group)

    def _create_input_widget(self) -> QWidget:
        """创建输入区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 说明文本
        hint = QLabel("请输入中国古典诗词，每句诗换行。系统将自动解析诗句并生成图像提示词。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        # 文本编辑器
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "床前明月光\n"
            "疑是地上霜\n"
            "举头望明月\n"
            "低头思故乡"
        )
        self.text_edit.setMinimumHeight(300)
        layout.addWidget(self.text_edit)

        # 示例按钮
        example_layout = QHBoxLayout()
        example_layout.addStretch()

        example_btn = QPushButton("加载示例")
        example_btn.clicked.connect(self._load_example)
        example_layout.addWidget(example_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_text)
        example_layout.addWidget(clear_btn)

        layout.addLayout(example_layout)

        return widget

    def _create_config_widget(self) -> QWidget:
        """创建配置区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 风格选择组
        style_group = QGroupBox("艺术风格")
        style_layout = QFormLayout()

        self.art_style_combo = QComboBox()
        self.art_style_combo.addItem("选择风格...", "")
        for style_id, name in Models.ART_STYLES.items():
            self.art_style_combo.addItem(name, style_id)
        style_layout.addRow("风格:", self.art_style_combo)

        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # 自定义风格
        custom_group = QGroupBox("自定义风格描述")
        custom_layout = QVBoxLayout()

        self.custom_style_edit = QTextEdit()
        self.custom_style_edit.setPlaceholderText(
            "例如：A traditional Chinese ink painting style, "
            "with soft brushstrokes and muted colors, "
            "emphasizing emptiness and contemplation..."
        )
        self.custom_style_edit.setMaximumHeight(100)
        custom_layout.addWidget(self.custom_style_edit)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # 生成选项
        options_group = QGroupBox("生成选项")
        options_layout = QFormLayout()

        self.example_count_spin = QComboBox()
        for i in range(1, 6):
            self.example_count_spin.addItem(f"{i} 个示例", i)
        self.example_count_spin.setCurrentIndex(2)  # 默认 3 个
        options_layout.addRow("每句诗生成:", self.example_count_spin)

        self.use_anchors_check = QPushButton("风格锚定: 开启")
        self.use_anchors_check.setCheckable(True)
        self.use_anchors_check.setChecked(True)
        self.use_anchors_check.clicked.connect(self._toggle_anchors)
        options_layout.addRow("", self.use_anchors_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 解析和生成按钮
        button_layout = QVBoxLayout()

        self.parse_btn = QPushButton("解析诗句")
        self.parse_btn.clicked.connect(self._parse_verses)
        button_layout.addWidget(self.parse_btn)

        self.generate_btn = QPushButton("生成提示词")
        self.generate_btn.clicked.connect(self._generate_prompts)
        self.generate_btn.setEnabled(False)
        button_layout.addWidget(self.generate_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        return widget

    def _create_result_widget(self) -> QGroupBox:
        """创建解析结果区域"""
        group = QGroupBox("解析结果")
        layout = QVBoxLayout(group)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)

        self.result_label = QLabel("等待解析诗句...")
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignTop)
        self.result_label.setMinimumHeight(150)

        scroll.setWidget(self.result_label)
        layout.addWidget(scroll)

        return group

    def _toggle_anchors(self):
        """切换风格锚定"""
        if self.use_anchors_check.isChecked():
            self.use_anchors_check.setText("风格锚定: 开启")
        else:
            self.use_anchors_check.setText("风格锚定: 关闭")

    def _load_example(self):
        """加载示例诗词"""
        examples = [
            """床前明月光
疑是地上霜
举头望明月
低头思故乡""",
            """春江花月夜
春江潮水连海平
海上明月共潮生
滟滟随波千万里
何处春江无月明""",
            """静夜思
李白
床前看月光
疑是地上霜
举头望山月
低头思故乡""",
        ]

        import random
        self.text_edit.setText(random.choice(examples))

    def _clear_text(self):
        """清空文本"""
        self.text_edit.clear()
        self.verses = []
        self.result_label.setText("等待解析诗句...")
        self.generate_btn.setEnabled(False)

    def _parse_verses(self):
        """解析诗句"""
        text = self.text_edit.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, "输入错误", "请输入诗词内容")
            return

        # 规则解析
        self.verses = self._parse_poetry_text(text)

        if not self.verses:
            QMessageBox.warning(self, "解析失败", "未能解析出有效的诗句")
            return

        # 显示结果
        result_text = f"共解析出 {len(self.verses)} 句诗：\n\n"
        for i, verse in enumerate(self.verses):
            result_text += f"{i + 1}. {verse}\n"

        self.result_label.setText(result_text)
        self.generate_btn.setEnabled(True)

        self.verses_parsed.emit(self.verses)

    def _parse_poetry_text(self, text: str) -> List[str]:
        """
        规则解析诗句

        规则：
        1. 按换行符分割
        2. 移除空行
        3. 按标点符号（。！？；，、）分割长行
        4. 过滤少于 2 个字符的行
        """
        lines = text.strip().split('\n')
        verses = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 按标点分割
            parts = re.split(r'[。！？；，、]', line)
            for part in parts:
                part = part.strip()
                if len(part) >= 2:
                    verses.append(part)

        return verses

    def _generate_prompts(self):
        """生成提示词（在后台线程中）"""
        if not self.verses:
            QMessageBox.warning(self, "生成错误", "请先解析诗句")
            return

        # 获取配置
        art_style = self.art_style_combo.currentData()
        custom_style = self.custom_style_edit.toPlainText().strip()
        example_count = self.example_count_spin.currentData()

        # 启动生成线程
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")

        self._generation_thread = PromptGenerationThread(
            self.app_state,
            self.verses,
            art_style,
            custom_style,
            example_count,
            self.use_anchors_check.isChecked()
        )
        self._generation_thread.finished.connect(self._on_generation_complete)
        self._generation_thread.error.connect(self._on_generation_error)
        self._generation_thread.start()

    def _on_generation_complete(self, prompts: PoetryPromptsResponse):
        """生成完成处理"""
        self.prompts = prompts
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("生成提示词")

        total = prompts.total_prompts()
        QMessageBox.information(
            self,
            "生成成功",
            f"共生成 {len(prompts.prompts)} 句诗的 {total} 个提示词"
        )

        self.prompts_generated.emit(prompts)

    def _on_generation_error(self, error: str):
        """生成错误处理"""
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("生成提示词")

        QMessageBox.critical(self, "生成失败", f"生成提示词失败：\n{error}")

    def get_verses(self) -> List[str]:
        """获取解析的诗句"""
        return self.verses

    def get_prompts(self) -> Optional[PoetryPromptsResponse]:
        """获取生成的提示词"""
        return self.prompts

    def set_prompts(self, prompts: PoetryPromptsResponse):
        """设置提示词（从外部加载）"""
        self.prompts = prompts
        self.verses = [v.verse for v in prompts.prompts]

        # 更新显示
        result_text = f"共 {len(prompts.prompts)} 句诗，{prompts.total_prompts()} 个提示词\n\n"
        for verse_prompt in prompts.prompts:
            result_text += f"{verse_prompt.verse}: {len(verse_prompt.descriptions)} 个提示词\n"

        self.result_label.setText(result_text)
        self.generate_btn.setEnabled(True)


class PromptGenerationThread(QThread):
    """提示词生成线程"""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, app_state, verses: List[str],
                 art_style: str, custom_style: str,
                 example_count: int, use_anchors: bool):
        super().__init__()
        self.app_state = app_state
        self.verses = verses
        self.art_style = art_style
        self.custom_style = custom_style
        self.example_count = example_count
        self.use_anchors = use_anchors

    def run(self):
        """运行生成任务"""
        try:
            # 构建提示词模板
            style_preset = StylePreset()
            style_desc = ""

            if self.art_style:
                preset_map = {
                    'ink': style_preset.CHINESE_INK,
                    'watercolor': style_preset.CHINESE_WATERCOLOR,
                    'gongbi': style_preset.GONGBI,
                }
                if self.art_style in preset_map:
                    style_desc = preset_map[self.art_style]['description']

            if self.custom_style:
                if style_desc:
                    style_desc += f". {self.custom_style}"
                else:
                    style_desc = self.custom_style

            verses_text = "\n".join(f"{i + 1}. {v}" for i, v in enumerate(self.verses))

            system_prompt = """你是一个专业的中国古典诗词视觉艺术家和视频导演。请根据以下诗句同时生成高质量的图像提示词和专业的视频提示词。

## 图像提示词要求
每个图像描述必须包含：
1. 艺术风格（如 traditional Chinese ink painting, watercolor）
2. 构图说明（如 wide shot, close-up, bird's eye view）
3. 光影氛围（如 soft morning light, moonlit, golden hour）
4. 文化元素（如 red lanterns, calligraphy, bamboo, plum blossoms）
5. 色彩方案（如 muted earth tones, vibrant reds and golds）

## 视频提示词要求
每个视频描述必须是专业的动画制作提示词，包含：
1. **运镜方式** (Camera Movement):
   - 缓慢推拉 (slow push in/pull out)
   - 横移/跟随 (pan/track)
   - 摇摄 (tilt)
   - 环绕 (orbit)
   - 升降 (crane/bird's eye)

2. **动画风格** (Animation Style):
   - 水墨流动效果 (ink flow animation)
   - 水彩晕染扩散 (watercolor spread)
   - 传统动画帧 (traditional frame-by-frame)
   - 3D 粒子效果 (3D particle effects)

3. **转场效果** (Transition):
   - 淡入淡出 (fade)
   - 墨色散开 (ink dissolve)
   - 云雾缭绕 (mist transition)
   - 花瓣飘落 (petal cascade)

4. **节奏与时长** (Pace & Duration):
   - 缓慢宁静 (slow and serene)
   - 流畅连贯 (smooth flow)
   - 建议秒数 (5-10 seconds)

5. **动态元素** (Motion Elements):
   - 风吹柳枝 (willow swaying)
   - 水波荡漾 (water rippling)
   - 云卷云舒 (clouds drifting)
   - 落花纷飞 (falling petals)

请以 JSON 格式返回：
{
  "prompts": [
    {
      "verse": "诗句原文",
      "index": 0,
      "descriptions": [
        {
          "image": "图像生成提示词 (英文)",
          "video": "专业视频生成提示词 (英文，包含运镜、动画风格、转场、节奏)"
        }
      ]
    }
  ]
}"""

            user_prompt = f"""## 诗句
{verses_text}

## 风格要求
{style_desc or 'traditional Chinese art style with ink painting aesthetic'}

## 输出要求
为每句诗生成 {self.example_count} 组不同的图像+视频提示词对。
图像提示词要注重画面构图和色彩美感。
视频提示词要注重动画制作的可执行性，包含具体的运镜、动画风格、转场和节奏描述。

请严格按照上述 JSON 格式返回，不要添加任何其他文字。"""

            # 调用 LLM
            client = self.app_state.llm_client
            response = client.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                temperature=0.8
            )

            # 解析 JSON 响应
            import json
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                response = json_match.group(0)

            data = json.loads(response)

            # 构建响应对象
            prompts = PoetryPromptsResponse()
            for item in data.get("prompts", []):
                verse_prompts = []
                for desc in item.get("descriptions", []):
                    # 兼容两种格式：
                    # 1. 新格式: {"image": "...", "video": "..."}
                    # 2. 旧格式: "纯字符串"
                    if isinstance(desc, dict):
                        image_desc = desc.get("image", desc.get("description", ""))
                        video_desc = desc.get("video", "")
                    else:
                        image_desc = str(desc)
                        video_desc = ""

                    verse_prompts.append(
                        ImagePrompt(description=image_desc, video_prompt=video_desc)
                    )

                verse = VersePrompts(
                    verse=item["verse"],
                    index=item["index"],
                    descriptions=verse_prompts
                )
                prompts.prompts.append(verse)

            self.finished.emit(prompts)

        except Exception as e:
            self.error.emit(str(e))
