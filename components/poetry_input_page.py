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
            "春苑月裴回\n"
            "竹堂侵夜开\n"
            "惊鸟排林度\n"
            "风花隔水来"
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

        # --- 九宫格模式设置 ---
        grid_group = QGroupBox("九宫格生图 (Nano Banana Pro)")
        grid_group.setCheckable(True)
        grid_group.setChecked(False)
        self.grid_mode_group = grid_group
        grid_layout = QFormLayout(grid_group)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["4k", "8k", "2k", "1080p"])
        grid_layout.addRow("分辨率:", self.resolution_combo)

        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(["16:9", "4:3", "1:1", "3:2", "21:9"])
        grid_layout.addRow("画幅:", self.aspect_ratio_combo)

        options_layout.addRow(grid_group)
        # ---------------------

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
            """春苑月裴回
竹堂侵夜开
惊鸟排林度
风花隔水来""",
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
        
        # Grid Mode params
        grid_mode = self.grid_mode_group.isChecked()
        resolution = self.resolution_combo.currentText()
        aspect_ratio = self.aspect_ratio_combo.currentText()

        # 启动生成线程
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")

        self._generation_thread = PromptGenerationThread(
            self.app_state,
            self.verses,
            art_style,
            custom_style,
            example_count,
            self.use_anchors_check.isChecked(),
            grid_mode=grid_mode,
            resolution=resolution,
            aspect_ratio=aspect_ratio
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

    def get_poetry_text(self) -> str:
        """获取当前输入的诗词文本"""
        return self.text_edit.toPlainText().strip()


class PromptGenerationThread(QThread):
    """提示词生成线程"""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, app_state, verses: List[str],
                 art_style: str, custom_style: str,
                 example_count: int, use_anchors: bool,
                 grid_mode: bool = False,
                 resolution: str = "4k",
                 aspect_ratio: str = "16:9"):
        super().__init__()
        self.app_state = app_state
        self.verses = verses
        self.art_style = art_style
        self.custom_style = custom_style
        self.example_count = example_count
        self.use_anchors = use_anchors
        self.grid_mode = grid_mode
        self.resolution = resolution
        self.aspect_ratio = aspect_ratio

    def run(self):
        """运行生成任务"""
        try:
            # 构建提示词模板
            style_preset = StylePreset()
            style_desc = ""

            if self.art_style:
                # 完整的风格映射（包含所有 ART_STYLES）
                preset_map = {
                    'ink': style_preset.CHINESE_INK,
                    'watercolor': style_preset.CHINESE_WATERCOLOR,
                    'gongbi': style_preset.GONGBI,
                    'oil': {
                        'description': 'Western oil painting style with rich textures, vivid colors, thick brush strokes, and dramatic lighting, reminiscent of classical European art'
                    },
                    'anime': {
                        'description': 'Japanese anime art style with vibrant colors, expressive characters, clean lines, cel-shaded rendering, and dramatic atmospheric effects'
                    },
                    'realistic': {
                        'description': 'Photo-realistic style with accurate details, natural lighting, realistic textures, true-to-life colors, and precise spatial depth'
                    },
                    'abstract': {
                        'description': 'Abstract art style with non-representational forms, bold color blocks, geometric shapes, emotional expression through color and composition'
                    },
                    'minimalist': {
                        'description': 'Minimalist design with clean composition, limited color palette, essential elements only, negative space emphasis, modern aesthetic'
                    }
                }
                if self.art_style in preset_map:
                    style_desc = preset_map[self.art_style]['description']

            if self.custom_style:
                if style_desc:
                    style_desc += f". {self.custom_style}"
                else:
                    style_desc = self.custom_style

            verses_text = "\n".join(f"{i + 1}. {v}" for i, v in enumerate(self.verses))


            # 动态生成 JSON 模板示例
            json_descriptions_template = """        {
          "image": "Image Prompt 1 (English)...",
          "video": "Video Prompt 1 (English)..."
        }"""
            
            # 如果需要多个示例，就在模板中展示多个
            if self.example_count > 1:
                for i in range(2, self.example_count + 1):
                    json_descriptions_template += f""",
        {{
          "image": "Image Prompt {i} (English)...",
          "video": "Video Prompt {i} (English)..."
        }}"""

            sys_prompt_content = f"""你是一个专业的中国古典诗词视觉艺术家和视频导演。请根据以下诗句同时生成高质量的图像提示词和专业的视频提示词。

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
{{
  "prompts": [
    {{
      "verse": "诗句原文",
      "index": 0,
      "descriptions": [
{json_descriptions_template}
      ]
    }}
  ]
}}"""

            user_prompt = f"""## 诗句
{verses_text}

## 视觉风格要求 (仅用于图像和视频，严禁用于音乐)
{style_desc or 'traditional Chinese art style with ink painting aesthetic'}
**注意：此风格描述仅适用于图像和视频画面的生成，绝不可用于音乐风格的生成。**

## 输出要求
为每句诗生成 {self.example_count} 组不同的图像+视频提示词对。
图像提示词要注重画面构图和色彩美感。
视频提示词要注重动画制作的可执行性，包含具体的运镜、动画风格、转场和节奏描述。

同时，为整首诗生成一个 Suno AI 音乐提示词。
**音乐生成特别说明：**
音乐风格 (style_prompt) 必须**完全独立于上述的"视觉风格"**，仅基于诗词本身的情感、意境和历史背景进行创作。
例如：如果诗词是悲伤的古诗，即使视觉风格选择了"赛博朋克"，音乐风格仍应是"Sad, Traditional Chinese Instruments, Guqin"等，而不是"Electronic"或"Cyberpunk"。

音乐提示词需包含：
1. style_prompt: 音乐风格标签（Genre, Vocals, Mood, Instruments），用逗号分隔。**请忽略视觉风格描述。**
2. title: 歌曲标题（基于诗词内容）
3. lyrics_cn: 中文歌词（使用诗词原文，添加 [Verse], [Chorus] 等结构标签）
4. lyrics_en: 英文歌词（诗词翻译版，添加结构标签）

请严格按照上述 JSON 格式返回，不要添加任何其他文字。"""

            # 更新系统提示词以包含音乐生成
            music_prompt_addition = """

## 音乐提示词 (Suno AI)
同时为整首诗生成一个专业的 Suno AI 音乐提示词。

### Style Prompt 格式
用逗号分隔的标签，按重要性排序：
[Genre] > [Vocal Style] > [Mood/Atmosphere] > [Tempo/Rhythm] > [Instrumentation]

示例风格：
- 古风：`Traditional Chinese, Guzheng, Erhu, Ethereal Female Vocals, Melancholic, Slow, Atmospheric`
- 现代融合：`Cinematic, Orchestral, Chinese Folk Elements, Female Choir, Epic, Emotional`

### 歌词结构
使用 Suno 标签：
- `[Intro]` - 开场引入
- `[Verse]` - 诗句段落
- `[Chorus]` - 副歌高潮
- `[Bridge]` - 过渡段
- `[Outro]` - 结尾

完整 JSON 格式：
{
  "prompts": [...图像视频提示词...],
  "music": {
    "style_prompt": "Traditional Chinese, Guzheng, Erhu, Ethereal Female Vocals, Melancholic, Slow tempo, Atmospheric, Lo-fi",
    "title": "基于诗词的歌曲标题",
    "lyrics_cn": "[Verse]\\n诗句1\\n诗句2\\n\\n[Chorus]\\n诗句3\\n诗句4",
    "lyrics_en": "[Verse]\\nEnglish translation line 1\\nEnglish translation line 2\\n\\n[Chorus]\\nEnglish translation line 3\\nEnglish translation line 4",
    "instrumental": false
  }
}"""

            # 将音乐提示词添加到系统提示词
            full_system_prompt = sys_prompt_content + music_prompt_addition

            # 调用 LLM
            client = self.app_state.llm_client
            response = client.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=full_system_prompt,
                temperature=0.8
            )

            # 解析 JSON 响应
            import json
            import logging
            
            # 记录原始响应以便调试
            print(f"LLM Response: {response}")
            
            # 尝试提取 JSON
            # 1. 尝试匹配 markdown 代码块 ```json ... ```
            json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 2. 尝试匹配最外层的 {}
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # 3. 都没有匹配到，尝试直接解析整个响应
                    json_str = response

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                # 如果解析失败，尝试修复常见的 JSON 格式错误 (如末尾逗号)
                try:
                    # 简单的修复尝试：移除末尾逗号
                    fixed_str = re.sub(r',\s*\}', '}', json_str)
                    fixed_str = re.sub(r',\s*\]', ']', fixed_str)
                    data = json.loads(fixed_str)
                except Exception:
                    raise ValueError(f"无法解析 JSON 响应: {e}\nRaw response: {response[:200]}...")

            # 构建响应对象
            from schemas.poetry import MusicPrompt
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

            # 解析音乐提示词
            music_data = data.get("music", {})
            if music_data:
                prompts.music_prompt = MusicPrompt(
                    style_prompt=music_data.get("style_prompt", ""),
                    title=music_data.get("title", ""),
                    lyrics_cn=music_data.get("lyrics_cn", ""),
                    lyrics_en=music_data.get("lyrics_en", ""),
                    instrumental=music_data.get("instrumental", False)
                )

            # --- 九宫格提示词生成逻辑 ---
            if self.grid_mode and prompts.prompts:
                # 获取所有提示词（包括多示例）
                image_prompts = []
                for v in prompts.prompts:
                    if v.descriptions:
                        for d in v.descriptions:
                            image_prompts.append(d.description)
                
                count = len(image_prompts)
                if count > 0:
                    n, m = self._calculate_grid_layout(count)
                    
                    # 诗词总意境 (如果有多示例，简单重复诗词可能会有点冗余，但这保持了上下文)
                    # 更好的做法可能只是列出诗句一次，但 prompt 数量匹配
                    poem_summary = " ".join([v.verse for v in prompts.prompts])
                    
                    grid_prompt = f"根据【{poem_summary}】，生成一张具有凝聚力的[{n}*{m}]的网格图像（包含{count}个镜头），"
                    grid_prompt += f"严格保持人物/物体服装光线的一致性，[{self.resolution}]分辨率，[{self.aspect_ratio}]画幅。"
                    grid_prompt += "生成的多宫格图每一个分镜头都需要按照序号编号。\n\n"
                    
                    for i, prompt in enumerate(image_prompts):
                        grid_prompt += f"镜头{i+1}: [{prompt}]\n"
                    
                    prompts.grid_prompt = grid_prompt
            # ---------------------------

            self.finished.emit(prompts)

        except Exception as e:
            self.error.emit(str(e))

    def _calculate_grid_layout(self, count: int) -> tuple:
        """计算网格布局 (n, m)"""
        if count <= 0:
            return 1, 1
        
        # 特殊规则
        if count == 3:
            return 1, 3  # 1x3 长条
        if count == 5:
            return 1, 5  # 1x5 长条
        
        # 默认尝试接近正方形的布局 (2x2, 2x3, 3x3)
        import math
        n = int(math.ceil(math.sqrt(count)))
        m = int(math.ceil(count / n))
        
        return m, n # 行, 列 (m*n) 或者 n*m，根据用户习惯通常是 行x列 或者 列x行。
                    # 用户描述: "1*3" usually means 1 row 3 cols or 1 col 3 rows?
                    # let's assume Row x Col. 
                    # Users said: "3 or 5 can be 1*3". This likely means 1 Row, 3 Cols (Horizontal Strip).
                    # I will return (1, count) for 3 and 5.


