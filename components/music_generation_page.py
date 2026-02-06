"""
音乐生成页面
风格标签、歌词生成、音频播放
"""
from typing import List, Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QGroupBox, QTextEdit,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QListWidget,
    QProgressBar, QSlider
)
from PySide6.QtCore import Signal, Qt, QThread, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QDesktopServices

from core.app import get_app_state
from schemas.music import MusicTask, MusicTaskStatus, MusicClip


class MusicGenerationPage(QWidget):
    """
    音乐生成页面

    功能：
    1. 选择风格标签
    2. 生成歌词
    3. 提交音乐生成任务
    4. 播放音频
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_state = get_app_state()
        self.music_tasks: List[MusicTask] = []
        self.current_playing_url: Optional[str] = None

        # 媒体播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # 监听配置变更
        self.app_state.config_changed.connect(self.update_models)

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("音乐生成")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 主内容区（左右布局）
        content_layout = QHBoxLayout()

        # 左侧：生成控制
        control_widget = self._create_control_widget()
        content_layout.addWidget(control_widget, 1)

        # 右侧：任务列表
        task_widget = self._create_task_widget()
        content_layout.addWidget(task_widget, 1)

        layout.addLayout(content_layout)

        # 底部：播放控制
        player_widget = self._create_player_widget()
        layout.addWidget(player_widget)

    def _create_control_widget(self) -> QGroupBox:
        """创建生成控制区域"""
        group = QGroupBox("音乐生成")
        layout = QVBoxLayout(group)

        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("灵感模式", "inspiration")
        self.mode_combo.addItem("自定义模式", "custom")
        self.mode_combo.addItem("续写模式", "extend")
        self.mode_combo.addItem("翻唱模式", "cover")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)

        layout.addLayout(mode_layout)

        # 模型选择
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        from api.suno_client import SunoClient
        # 1. 预定义模型
        for model_id, model_name in SunoClient.get_available_models().items():
            self.model_combo.addItem(model_name, model_id)
            
        # 2. 自定义模型
        if hasattr(self.app_state.config, 'custom_models'):
            custom_music = self.app_state.config.custom_models.get('music', [])
            for model_name in custom_music:
                # 避免重复
                exists = False
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemText(i) == model_name:
                        exists = True
                        break
                if not exists:
                    self.model_combo.addItem(model_name, model_name)
        # 默认选择 chirp-v4
        self.model_combo.setCurrentIndex(2)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)

        # 人声性别选择
        gender_layout = QHBoxLayout()
        gender_layout.addWidget(QLabel("人声:"))
        self.gender_combo = QComboBox()
        for gender_id, gender_name in SunoClient.get_vocal_genders().items():
            self.gender_combo.addItem(gender_name, gender_id)
        gender_layout.addWidget(self.gender_combo)
        layout.addLayout(gender_layout)

        # 风格标签
        tags_layout = QVBoxLayout()
        tags_layout.addWidget(QLabel("风格标签 (可多选):"))

        self.tags_list = QListWidget()
        self.tags_list.setMaximumHeight(100)
        self.tags_list.setSelectionMode(QListWidget.MultiSelection)

        for tag in SunoClient.get_style_tags():
            self.tags_list.addItem(tag)

        # 默认选中一些
        for i in [0, 1, 2]:
            if i < self.tags_list.count():
                self.tags_list.item(i).setSelected(True)

        tags_layout.addWidget(self.tags_list)
        layout.addLayout(tags_layout)

        # 排除风格
        neg_layout = QHBoxLayout()
        neg_layout.addWidget(QLabel("排除风格:"))
        self.negative_tags_edit = QLineEdit()
        self.negative_tags_edit.setPlaceholderText("不需要的风格,用逗号分隔")
        neg_layout.addWidget(self.negative_tags_edit)
        layout.addLayout(neg_layout)

        # 歌曲标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("例如: 春江花月夜")
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        # 歌词/描述
        layout.addWidget(QLabel("歌词或描述:"))
        self.lyrics_edit = QTextEdit()
        self.lyrics_edit.setPlaceholderText(
            "灵感模式: 输入音乐主题描述\n"
            "自定义模式: 输入完整歌词 (支持 [Verse], [Chorus] 等标签)\n"
            "例如: [Verse]\n月光如水照花间\n春风轻拂柳丝寒..."
        )
        self.lyrics_edit.setMaximumHeight(120)
        layout.addWidget(self.lyrics_edit)

        # 续写模式设置
        self.extend_group = QGroupBox("续写设置")
        extend_layout = QFormLayout_()
        self.extend_id_edit = QLineEdit()
        self.extend_id_edit.setPlaceholderText("从任务列表点击'续写'按钮自动填充")
        self.extend_time_edit = QLineEdit("30")
        self.extend_time_edit.setPlaceholderText("从第几秒开始续写")
        extend_layout.addRow("续写歌曲 ID:", self.extend_id_edit)
        extend_layout.addRow("起始时间(秒):", self.extend_time_edit)
        self.extend_group.setLayout(extend_layout)
        self.extend_group.setVisible(False)
        layout.addWidget(self.extend_group)

        # 翻唱模式设置
        self.cover_group = QGroupBox("翻唱设置")
        cover_layout = QFormLayout_()
        self.cover_clip_id_edit = QLineEdit()
        self.cover_clip_id_edit.setPlaceholderText("原曲ID或上传的音频ID")
        cover_layout.addRow("翻唱原曲 ID:", self.cover_clip_id_edit)
        self.cover_group.setLayout(cover_layout)
        self.cover_group.setVisible(False)
        layout.addWidget(self.cover_group)

        # 按钮区域
        btn_layout = QHBoxLayout()
        
        # 生成歌词按钮
        self.gen_lyrics_btn = QPushButton("生成歌词")
        self.gen_lyrics_btn.clicked.connect(self._generate_lyrics)
        btn_layout.addWidget(self.gen_lyrics_btn)

        # 生成音乐按钮
        self.generate_btn = QPushButton("🎵 生成音乐")
        self.generate_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.generate_btn.clicked.connect(self._generate_music)
        btn_layout.addWidget(self.generate_btn)

        layout.addLayout(btn_layout)

        layout.addStretch()

        return group

    def _create_task_widget(self) -> QGroupBox:
        """创建任务列表区域"""
        group = QGroupBox("生成任务")
        layout = QVBoxLayout(group)

        # 任务表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels(["标题", "状态", "时长", "Clip ID", "操作", ""])

        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setAlternatingRowColors(True)

        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.task_table.setColumnWidth(5, 0)  # 隐藏任务ID列

        layout.addWidget(self.task_table)

        # 刷新按钮
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()

        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.clicked.connect(self._refresh_tasks)
        refresh_layout.addWidget(self.refresh_btn)

        layout.addLayout(refresh_layout)

        return group

    def _create_player_widget(self) -> QGroupBox:
        """创建播放控制区域"""
        group = QGroupBox("播放控制")
        layout = QHBoxLayout(group)

        # 当前播放
        self.now_playing_label = QLabel("未播放")
        self.now_playing_label.setStyleSheet("color: #666;")
        layout.addWidget(self.now_playing_label)

        layout.addStretch()

        # 控制按钮
        self.play_btn = QPushButton("播放")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._play_audio)
        layout.addWidget(self.play_btn)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._pause_audio)
        layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_audio)
        layout.addWidget(self.stop_btn)

        # 音量
        layout.addWidget(QLabel("音量:"))
        from PySide6.QtWidgets import QSlider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self.volume_slider)

        # 进度条
        layout.addWidget(QLabel("进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        layout.addWidget(self.progress_bar)

        return group

    def _on_mode_changed(self):
        """模式变化"""
        mode = self.mode_combo.currentData()

        # 显示/隐藏续写设置
        self.extend_group.setVisible(mode == "extend")
        
        # 显示/隐藏翻唱设置
        self.cover_group.setVisible(mode == "cover")
        
        # 翻唱模式自动切换到专用模型
        if mode == "cover":
            for i in range(self.model_combo.count()):
                if "tau" in self.model_combo.itemData(i):
                    self.model_combo.setCurrentIndex(i)
                    break
            self.gen_lyrics_btn.setEnabled(False)
        else:
            self.gen_lyrics_btn.setEnabled(True)

    def _generate_lyrics(self):
        """生成歌词"""
        prompt = self.lyrics_edit.toPlainText().strip()

        if not prompt:
            QMessageBox.warning(self, "输入错误", "请输入主题或关键词")
            return

        # 启动生成线程
        self.gen_lyrics_btn.setEnabled(False)
        self.gen_lyrics_btn.setText("生成中...")

        self._lyrics_thread = LyricsGenerationThread(
            self.app_state,
            prompt
        )
        self._lyrics_thread.finished.connect(self._on_lyrics_finished)
        self._lyrics_thread.error.connect(self._on_lyrics_error)
        self._lyrics_thread.start()

    def _on_lyrics_finished(self, lyrics: str):
        """歌词生成完成"""
        self.gen_lyrics_btn.setEnabled(True)
        self.gen_lyrics_btn.setText("生成歌词")
        self.lyrics_edit.setPlainText(lyrics)

        # 自动填充标题（如果为空）
        if not self.title_edit.text():
            import re
            # 尝试提取第一行作为标题
            lines = lyrics.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('['):
                    self.title_edit.setText(line[:20])
                    break

    def _on_lyrics_error(self, error: str):
        """歌词生成错误"""
        self.gen_lyrics_btn.setEnabled(True)
        self.gen_lyrics_btn.setText("生成歌词")
        QMessageBox.critical(self, "生成失败", f"生成歌词失败：\n{error}")

    def _generate_music(self):
        """生成音乐"""
        # 获取选中的标签
        selected_tags = [self.tags_list.item(i).text()
                        for i in range(self.tags_list.count())
                        if self.tags_list.item(i).isSelected()]

        if not selected_tags:
            QMessageBox.warning(self, "选择错误", "请至少选择一个风格标签")
            return

        tags = ",".join(selected_tags)
        title = self.title_edit.text().strip() or "未命名"
        prompt = self.lyrics_edit.toPlainText().strip()
        mode = self.mode_combo.currentData()
        model = self.model_combo.currentData()
        gender = self.gender_combo.currentData() or None
        negative_tags = self.negative_tags_edit.text().strip()

        if not prompt and mode not in ["extend", "cover"]:
            QMessageBox.warning(self, "输入错误", "请输入歌词或描述")
            return

        # 续写模式参数
        continue_clip_id = None
        continue_at = None
        cover_clip_id = None

        if mode == "extend":
            continue_clip_id = self.extend_id_edit.text().strip()
            if not continue_clip_id:
                QMessageBox.warning(self, "输入错误", "请输入续写歌曲 ID")
                return
            try:
                continue_at = float(self.extend_time_edit.text())
            except ValueError:
                QMessageBox.warning(self, "输入错误", "续写起始时间必须是数字")
                return
        
        if mode == "cover":
            cover_clip_id = self.cover_clip_id_edit.text().strip()
            if not cover_clip_id:
                QMessageBox.warning(self, "输入错误", "请输入翻唱原曲 ID")
                return

        # 启动生成线程
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")

        self._music_thread = MusicGenerationThread(
            self.app_state,
            title=title,
            tags=tags,
            prompt=prompt,
            mode=mode,
            model=model,
            gender=gender,
            negative_tags=negative_tags,
            continue_clip_id=continue_clip_id,
            continue_at=continue_at,
            cover_clip_id=cover_clip_id
        )
        self._music_thread.task_submitted.connect(self._on_task_submitted)
        self._music_thread.finished.connect(self._on_music_generation_finished)
        self._music_thread.start()

    def _on_task_submitted(self, task: MusicTask):
        """任务提交完成"""
        self.music_tasks.append(task)
        self._add_task_to_table(task)

    def _on_music_generation_finished(self):
        """音乐生成完成"""
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("生成音乐")

    def _add_task_to_table(self, task: MusicTask):
        """添加任务到表格"""
        row = self.task_table.rowCount()
        self.task_table.insertRow(row)

        # 标题
        self.task_table.setItem(row, 0, QTableWidgetItem(task.title))

        # 状态
        status_item = QTableWidgetItem(task.status.value)
        self._set_status_color(status_item, task.status)
        self.task_table.setItem(row, 1, status_item)

        # 时长
        duration_text = f"{task.clips[0].duration:.0f}s" if task.clips and task.clips[0].duration else "-"
        self.task_table.setItem(row, 2, QTableWidgetItem(duration_text))

        # Clip ID (用于续写)
        clip_id = task.clips[0].id if task.clips else "-"
        clip_id_item = QTableWidgetItem(clip_id[:12] + "..." if len(clip_id) > 12 else clip_id)
        clip_id_item.setToolTip(clip_id)  # 完整ID显示在tooltip
        self.task_table.setItem(row, 3, clip_id_item)

        # 操作按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setSpacing(2)

        play_btn = QPushButton("▶")
        play_btn.setMaximumWidth(30)
        play_btn.setToolTip("播放")
        play_btn.clicked.connect(lambda checked, r=row: self._play_task(r))
        btn_layout.addWidget(play_btn)

        download_btn = QPushButton("⬇")
        download_btn.setMaximumWidth(30)
        download_btn.setToolTip("下载")
        download_btn.clicked.connect(lambda checked, r=row: self._download_task(r))
        btn_layout.addWidget(download_btn)

        extend_btn = QPushButton("↻")
        extend_btn.setMaximumWidth(30)
        extend_btn.setToolTip("续写此歌曲")
        extend_btn.clicked.connect(lambda checked, r=row: self._extend_task(r))
        btn_layout.addWidget(extend_btn)

        self.task_table.setCellWidget(row, 4, btn_widget)

        # 任务ID（隐藏）
        id_item = QTableWidgetItem(task.task_id)
        self.task_table.setItem(row, 5, id_item)

    def _extend_task(self, row: int):
        """续写指定任务的音乐"""
        task_id = self.task_table.item(row, 5).text()
        task = next((t for t in self.music_tasks if t.task_id == task_id), None)

        if task and task.clips:
            clip = task.get_primary_clip()
            if clip and clip.id:
                # 切换到续写模式
                self.mode_combo.setCurrentIndex(2)  # 续写模式
                # 填充clip_id
                self.extend_id_edit.setText(clip.id)
                # 设置起始时间为歌曲时长（续写从结尾开始）
                if clip.duration:
                    self.extend_time_edit.setText(str(int(clip.duration)))
                QMessageBox.information(
                    self, 
                    "续写模式已启动", 
                    f"已选择歌曲:\n• 标题: {clip.title}\n• Clip ID: {clip.id[:20]}...\n• 时长: {clip.duration:.0f}秒\n\n"
                    f"请输入续写歌词，然后点击'生成音乐'！"
                )
            else:
                QMessageBox.warning(self, "无法续写", "此任务尚未生成完成或没有有效的Clip ID")
        else:
            QMessageBox.warning(self, "无法续写", "请等待音乐生成完成后再续写")

    def _set_status_color(self, item: QTableWidgetItem, status: MusicTaskStatus):
        """设置状态颜色"""
        colors = {
            MusicTaskStatus.NOT_START: "#999",
            MusicTaskStatus.SUBMITTED: "#2196F3",
            MusicTaskStatus.QUEUED: "#FF9800",
            MusicTaskStatus.IN_PROGRESS: "#9C27B0",
            MusicTaskStatus.SUCCESS: "#4CAF50",
            MusicTaskStatus.FAILURE: "#F44336",
        }
        color = colors.get(status, "#000")
        item.setForeground(Qt.black)

    def _refresh_tasks(self):
        """刷新任务状态"""
        client = self.app_state.music_client

        for task in self.music_tasks:
            if task.is_processing():
                try:
                    status_data = client.get_task_status(task.task_id)
                    task_info = status_data.get("data", {})

                    if isinstance(task_info, list):
                        task_info = task_info[0] if task_info else {}

                    new_status = MusicTaskStatus(task_info.get("status", "NOT_START"))
                    task.update_status(new_status)

                    # 如果成功，更新片段
                    if new_status == MusicTaskStatus.SUCCESS:
                        clips_data = task_info.get("data", [])
                        clips = [
                            MusicClip(
                                id=c.get("id", ""),
                                video_url=c.get("video_url"),
                                audio_url=c.get("audio_url"),
                                image_large_url=c.get("image_large_url"),
                                title=c.get("title", ""),
                                duration=c.get("duration")
                            )
                            for c in clips_data
                        ]
                        task.set_clips(clips)

                    # 更新表格
                    self._update_task_in_table(task)

                except Exception as e:
                    self.app_state.logger.error(f"刷新任务失败 {task.task_id}: {e}")

    def _update_task_in_table(self, task: MusicTask):
        """更新表格中的任务"""
        for row in range(self.task_table.rowCount()):
            if self.task_table.item(row, 5).text() == task.task_id:
                # 更新状态
                status_item = self.task_table.item(row, 1)
                status_item.setText(task.status.value)
                self._set_status_color(status_item, task.status)

                # 更新时长
                if task.clips and task.clips[0].duration:
                    duration_item = self.task_table.item(row, 2)
                    duration_item.setText(f"{task.clips[0].duration:.0f}s")

                # 更新Clip ID
                if task.clips and task.clips[0].id:
                    clip_id = task.clips[0].id
                    clip_id_item = self.task_table.item(row, 3)
                    clip_id_item.setText(clip_id[:12] + "..." if len(clip_id) > 12 else clip_id)
                    clip_id_item.setToolTip(clip_id)

                break

    def _play_task(self, row: int):
        """播放任务的音乐"""
        task_id = self.task_table.item(row, 5).text()
        task = next((t for t in self.music_tasks if t.task_id == task_id), None)

        if task and task.clips:
            clip = task.get_primary_clip()
            if clip and clip.audio_url:
                self._play_url(clip.audio_url, f"{clip.title}")
            else:
                QMessageBox.information(self, "提示", "音乐尚未生成完成")
        else:
            QMessageBox.information(self, "提示", "音乐尚未生成完成")

    def _play_audio(self):
        """播放当前音频"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.media_player.play()
        else:
            QMessageBox.information(self, "提示", "请先选择要播放的音乐")

    def _pause_audio(self):
        """暂停播放"""
        self.media_player.pause()

    def _stop_audio(self):
        """停止播放"""
        self.media_player.stop()
        self.now_playing_label.setText("未播放")

    def _play_url(self, url: str, title: str = ""):
        """播放指定 URL 的音频"""
        self.media_player.setSource(QUrl(url))
        self.media_player.play()
        self.now_playing_label.setText(f"正在播放: {title}")
        self.current_playing_url = url

        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

    def _on_volume_changed(self, value: int):
        """音量变化"""
        self.audio_output.setVolume(value / 100)

    def _download_task(self, row: int):
        """下载任务的音乐"""
        task_id = self.task_table.item(row, 5).text()
        task = next((t for t in self.music_tasks if t.task_id == task_id), None)

        if task and task.clips:
            clip = task.get_primary_clip()
            if clip and clip.audio_url:
                directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
                if directory:
                    try:
                        from utils.file_naming import FileNaming
                        client = self.app_state.music_client
                        
                        # 使用规范化文件名
                        filename = FileNaming.generate_music_filename(
                            title=task.title,
                            style=task.tags
                        )
                        save_path = Path(directory) / filename
                        client.download_audio(clip.audio_url, save_path)
                        QMessageBox.information(self, "下载成功", f"音乐已保存到:\n{save_path}")
                    except Exception as e:
                        QMessageBox.critical(self, "下载失败", f"下载失败: {str(e)}")
            else:
                QMessageBox.information(self, "提示", "音乐尚未生成完成")
        else:
            QMessageBox.information(self, "提示", "音乐尚未生成完成")
    
    def set_music_prompt(self, music_prompt):
        """接收并填充音乐提示词
        
        Args:
            music_prompt: MusicPrompt 对象，包含 style_prompt, title, lyrics_cn, lyrics_en
        """
        if not music_prompt:
            return
        
        # 填充标题
        if music_prompt.title:
            self.title_edit.setText(music_prompt.title)
        
        # 解析风格标签并选中
        if music_prompt.style_prompt:
            # 取消所有选择
            for i in range(self.tags_list.count()):
                self.tags_list.item(i).setSelected(False)
            
            # 匹配并选中标签
            style_tags = [t.strip().lower() for t in music_prompt.style_prompt.split(',')]
            for i in range(self.tags_list.count()):
                item = self.tags_list.item(i)
                item_text = item.text().lower()
                # 检查是否有任何风格标签匹配
                for tag in style_tags:
                    if tag in item_text or item_text in tag:
                        item.setSelected(True)
                        break
        
        # 填充歌词 - 中英双语格式
        lyrics_text = ""
        if music_prompt.lyrics_cn:
            lyrics_text += music_prompt.lyrics_cn
        if music_prompt.lyrics_en:
            if lyrics_text:
                lyrics_text += "\n\n--- English Version ---\n\n"
            lyrics_text += music_prompt.lyrics_en
        
        if lyrics_text:
            self.lyrics_edit.setPlainText(lyrics_text)
        
        # 显示提示
        QMessageBox.information(
            self,
            "音乐提示词已导入",
            f"已导入音乐提示词:\n"
            f"• 标题: {music_prompt.title or '未设置'}\n"
            f"• 风格: {music_prompt.style_prompt[:50] + '...' if len(music_prompt.style_prompt) > 50 else music_prompt.style_prompt}\n"
            f"• 歌词已填充\n\n"
            f"请根据需要调整后点击'生成音乐'！"
        )



    def update_models(self):
        """更新模型列表（响应配置变更）"""
        current_model = self.model_combo.currentData()
        self.model_combo.clear()
        
        from api.suno_client import SunoClient
        # 1. 预定义模型
        for model_id, model_name in SunoClient.get_available_models().items():
            self.model_combo.addItem(model_name, model_id)
            
        # 2. 自定义模型
        if hasattr(self.app_state.config, 'custom_models'):
            custom_music = self.app_state.config.custom_models.get('music', [])
            for model_name in custom_music:
                # 避免重复
                exists = False
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemText(i) == model_name:
                        exists = True
                        break
                if not exists:
                    self.model_combo.addItem(model_name, model_name)
                    
        # 尝试恢复之前的选择
        index = self.model_combo.findData(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
             # 默认选择 chirp-v4 (如果存在)
             default_index = self.model_combo.findData("chirp-v4")
             if default_index >= 0:
                 self.model_combo.setCurrentIndex(default_index)


class QFormLayout_(QVBoxLayout):
    """简化的表单布局"""
    def __init__(self):
        super().__init__()
        self.row_layout = None

    def addRow(self, label, widget):
        if self.row_layout is None:
            self.row_layout = QHBoxLayout()
            self.addLayout(self.row_layout)

        self.row_layout.addWidget(QLabel(label))
        self.row_layout.addWidget(widget)


class LyricsGenerationThread(QThread):
    """歌词生成线程"""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, app_state, prompt: str):
        super().__init__()
        self.app_state = app_state
        self.prompt = prompt

    def run(self):
        """运行生成任务"""
        try:
            client = self.app_state.music_client
            lyrics = client.generate_lyrics(self.prompt)
            self.finished.emit(lyrics)
        except Exception as e:
            self.error.emit(str(e))


class MusicGenerationThread(QThread):
    """音乐生成线程 - 支持所有模式"""

    task_submitted = Signal(object)
    finished = Signal()

    def __init__(self, app_state, title: str, tags: str, prompt: str,
                 mode: str, model: str = "chirp-v4",
                 gender: Optional[str] = None,
                 negative_tags: str = "",
                 continue_clip_id: Optional[str] = None,
                 continue_at: Optional[float] = None,
                 cover_clip_id: Optional[str] = None):
        super().__init__()
        self.app_state = app_state
        self.title = title
        self.tags = tags
        self.prompt = prompt
        self.mode = mode
        self.model = model
        self.gender = gender
        self.negative_tags = negative_tags
        self.continue_clip_id = continue_clip_id
        self.continue_at = continue_at
        self.cover_clip_id = cover_clip_id

    def run(self):
        """运行生成任务"""
        try:
            from datetime import datetime

            client = self.app_state.music_client
            task_id = None

            if self.mode == "cover" and self.cover_clip_id:
                # 翻唱模式
                task_id = client.generate_cover(
                    cover_clip_id=self.cover_clip_id,
                    prompt=self.prompt,
                    tags=self.tags,
                    title=self.title,
                    model=self.model
                )
            elif self.mode == "extend" and self.continue_clip_id:
                # 续写模式
                task_id = client.generate_extend(
                    clip_id=self.continue_clip_id,
                    continue_at=self.continue_at,
                    prompt=self.prompt,
                    tags=self.tags,
                    title=self.title,
                    model=self.model
                )
            else:
                # 自定义/灵感模式
                task_id = client.generate_custom(
                    title=self.title,
                    lyrics=self.prompt,
                    tags=self.tags,
                    model=self.model,
                    vocal_gender=self.gender,
                    negative_tags=self.negative_tags
                )

            if task_id:
                task = MusicTask(
                    task_id=task_id,
                    title=self.title,
                    tags=self.tags,
                    prompt=self.prompt,
                    model=self.model,
                    created_at=datetime.now()
                )
                task.update_status(MusicTaskStatus.SUBMITTED)

                self.task_submitted.emit(task)

        except Exception as e:
            self.app_state.logger.error(f"提交音乐任务失败: {e}")

        self.finished.emit()

