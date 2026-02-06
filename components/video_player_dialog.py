"""
视频播放器对话框
内置视频播放功能，支持播放控制、进度条、音量调节
"""
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QStyle, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QUrl, Signal, Slot, QThread, QStandardPaths
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
import tempfile
import requests
from pathlib import Path


class VideoDownloadThread(QThread):
    """视频下载线程"""
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._stopped = False
        
    def stop(self):
        self._stopped = True
        
    def run(self):
        try:
            # 创建临时文件
            temp_dir = Path(tempfile.gettempdir()) / "guui_video_cache"
            temp_dir.mkdir(exist_ok=True)
            
            filename = self.url.split('/')[-1].split('?')[0]
            if not filename.endswith('.mp4'):
                filename += '.mp4'
                
            save_path = temp_dir / filename
            
            # 如果文件已存在且大小正常，直接使用
            if save_path.exists() and save_path.stat().st_size > 0:
                self.finished.emit(str(save_path))
                return
            
            # 下载
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._stopped:
                        return
                        
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress.emit(int(downloaded / total_size * 100))
                            
            self.finished.emit(str(save_path))
            
        except Exception as e:
            self.error.emit(str(e))



class VideoPlayerDialog(QDialog):
    """视频播放器对话框"""
    
    # 信号
    regenerate_requested = Signal(str)  # 重新生成请求（提示词）
    
    def __init__(self, video_url: str, metadata: dict = None, parent=None):
        """
        初始化视频播放器
        
        Args:
            video_url: 视频 URL 或本地路径
            metadata: 视频元数据 {'prompt': str, 'model': str, 'duration': float, ...}
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.video_url = video_url
        self.metadata = metadata or {}
        
        self._init_ui()
        self._init_player()
        
    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("视频预览")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # 视频显示区域
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_widget)
        
        # 加载进度条 (默认隐藏)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 100)
        self.loading_bar.setValue(0)
        self.loading_bar.setTextVisible(True)
        self.loading_bar.setFormat("正在缓冲视频... %p%")
        self.loading_bar.hide()
        layout.addWidget(self.loading_bar)
        
        # 播放控制区域
        
        # 播放控制区域
        controls_layout = self._create_controls()
        layout.addLayout(controls_layout)
        
        # 元数据显示区域
        if self.metadata:
            metadata_layout = self._create_metadata_panel()
            layout.addLayout(metadata_layout)
        
        # 操作按钮区域
        actions_layout = self._create_action_buttons()
        layout.addLayout(actions_layout)
        
    def _create_controls(self) -> QHBoxLayout:
        """创建播放控制区"""
        layout = QHBoxLayout()
        
        # 播放/暂停按钮
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setToolTip("播放/暂停 (空格)")
        self.play_button.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_button)
        
        # 停止按钮
        stop_button = QPushButton()
        stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        stop_button.setToolTip("停止")
        stop_button.clicked.connect(self._stop_video)
        layout.addWidget(stop_button)
        
        # 当前时间标签
        self.time_label = QLabel("00:00")
        layout.addWidget(self.time_label)
        
        # 进度条
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setToolTip("拖动跳转")
        self.position_slider.sliderMoved.connect(self._set_position)
        layout.addWidget(self.position_slider, stretch=1)
        
        # 总时长标签
        self.duration_label = QLabel("00:00")
        layout.addWidget(self.duration_label)
        
        # 音量按钮
        volume_button = QPushButton()
        volume_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        volume_button.setToolTip("音量")
        layout.addWidget(volume_button)
        
        # 音量滑块
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.setToolTip("音量调节")
        self.volume_slider.valueChanged.connect(self._set_volume)
        layout.addWidget(self.volume_slider)
        
        # 循环播放按钮
        self.loop_button = QPushButton("🔁")
        self.loop_button.setCheckable(True)
        self.loop_button.setToolTip("循环播放")
        self.loop_button.setMaximumWidth(40)
        layout.addWidget(self.loop_button)
        
        # 全屏按钮
        fullscreen_button = QPushButton()
        fullscreen_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        fullscreen_button.setToolTip("全屏 (F11)")
        fullscreen_button.clicked.connect(self._toggle_fullscreen)
        layout.addWidget(fullscreen_button)
        
        return layout
    
    def _create_metadata_panel(self) -> QHBoxLayout:
        """创建元数据显示面板"""
        layout = QHBoxLayout()
        
        # 提示词
        prompt = self.metadata.get('prompt')
        if prompt:
            prompt_label = QLabel(f"📝 提示词: {str(prompt)[:100]}...")
            prompt_label.setWordWrap(True)
            prompt_label.setStyleSheet("color: #666; padding: 5px;")
            layout.addWidget(prompt_label)
        
        # 模型
        if 'model' in self.metadata:
            model_label = QLabel(f"🤖 {self.metadata['model']}")
            model_label.setStyleSheet("color: #888; padding: 5px;")
            layout.addWidget(model_label)
        
        # 分辨率
        if 'resolution' in self.metadata:
            res_label = QLabel(f"📐 {self.metadata['resolution']}")
            res_label.setStyleSheet("color: #888; padding: 5px;")
            layout.addWidget(res_label)
        
        layout.addStretch()
        return layout
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """创建操作按钮"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # 重新生成按钮
        regenerate_btn = QPushButton("🔄 重新生成")
        regenerate_btn.clicked.connect(self._on_regenerate)
        layout.addWidget(regenerate_btn)
        
        # 下载按钮
        download_btn = QPushButton("📥 下载视频")
        download_btn.clicked.connect(self._download_video)
        layout.addWidget(download_btn)
        
        # 关闭按钮
        close_btn = QPushButton("❌ 关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return layout
    
    def _init_player(self):
        """初始化媒体播放器"""
        # 创建播放器
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        # 连接信号
        self.player.positionChanged.connect(self._update_position)
        self.player.durationChanged.connect(self._update_duration)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        
        # 设置音量
        self.audio_output.setVolume(0.7)
        
        # 加载视频
        self._load_video()
    
    def _load_video(self):
        """加载视频"""
        if self.video_url.startswith(('http://', 'https://')):
            # 显示加载状态
            self.loading_bar.show()
            self.loading_bar.setValue(0)
            self.play_button.setEnabled(False)
            
            # 启动下载线程
            self.download_thread = VideoDownloadThread(self.video_url)
            self.download_thread.progress.connect(self.loading_bar.setValue)
            self.download_thread.finished.connect(self._on_video_ready)
            self.download_thread.error.connect(self._on_video_error)
            self.download_thread.start()
        else:
            # 本地文件直接播放
            url = QUrl.fromLocalFile(self.video_url)
            self.player.setSource(url)
            self.player.play()
            
    def _on_video_ready(self, local_path: str):
        """视频下载完成"""
        self.loading_bar.hide()
        self.play_button.setEnabled(True)
        self.video_url = local_path  # 更新为本地路径
        
        url = QUrl.fromLocalFile(local_path)
        self.player.setSource(url)
        self.player.play()
        
    def _on_video_error(self, error_msg: str):
        """视频下载失败"""
        self.loading_bar.hide()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "加载失败", f"无法加载视频: {error_msg}\n\n将尝试流式播放...")
        
        # 降级由于流式播放
        url = QUrl(self.video_url)
        self.player.setSource(url)
        self.player.play()
        self.play_button.setEnabled(True)
    
    @Slot()
    def _toggle_play(self):
        """切换播放/暂停"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    @Slot()
    def _stop_video(self):
        """停止播放"""
        self.player.stop()
    
    @Slot(int)
    def _set_position(self, position: int):
        """设置播放位置"""
        self.player.setPosition(position)
    
    @Slot(int)
    def _set_volume(self, volume: int):
        """设置音量"""
        self.audio_output.setVolume(volume / 100.0)
    
    @Slot(int)
    def _update_position(self, position: int):
        """更新播放位置"""
        # 更新进度条（避免循环触发）
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)
        
        # 更新时间标签
        self.time_label.setText(self._format_time(position))
    
    @Slot(int)
    def _update_duration(self, duration: int):
        """更新视频时长"""
        self.position_slider.setMaximum(duration)
        self.duration_label.setText(self._format_time(duration))
    
    @Slot()
    def _on_state_changed(self):
        """播放状态变化"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
    
    @Slot()
    def _on_media_status_changed(self):
        """媒体状态变化"""
        status = self.player.mediaStatus()
        
        # 视频播放结束
        if status == QMediaPlayer.EndOfMedia:
            if self.loop_button.isChecked():
                # 循环播放
                self.player.setPosition(0)
                self.player.play()
            else:
                # 回到开始位置
                self.player.stop()
    
    @Slot()
    def _toggle_fullscreen(self):
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    @Slot()
    def _on_regenerate(self):
        """发起重新生成请求"""
        from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox
        
        current_prompt = self.metadata.get('prompt') or ''
        
        # 创建自定义编辑对话框
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle("修改视频提示词")
        edit_dialog.setMinimumSize(600, 350)
        
        layout = QVBoxLayout(edit_dialog)
        
        # 说明
        hint_label = QLabel("请编辑视频提示词（英文），包含运镜、动画风格等描述：")
        layout.addWidget(hint_label)
        
        # 显示原提示词
        if current_prompt:
            original_label = QLabel(f"原提示词: {current_prompt[:80]}...")
            original_label.setStyleSheet("color: #666; font-size: 10px;")
            original_label.setWordWrap(True)
            layout.addWidget(original_label)
        
        # 多行文本编辑器
        text_edit = QTextEdit()
        text_edit.setPlainText(current_prompt)
        text_edit.setPlaceholderText("Slow camera pan across traditional Chinese landscape, gentle ink flow animation, serene atmosphere...")
        layout.addWidget(text_edit)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(edit_dialog.accept)
        buttons.rejected.connect(edit_dialog.reject)
        layout.addWidget(buttons)
        
        if edit_dialog.exec() == QDialog.Accepted:
            new_prompt = text_edit.toPlainText().strip()
            if new_prompt:
                self.regenerate_requested.emit(new_prompt)
                QMessageBox.information(self, "提示", "已提交重新生成任务，请在视频队列中查看")

    
    @Slot()
    def _download_video(self):
        """下载视频"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import requests
        from pathlib import Path
        
        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存视频",
            f"video_{self.metadata.get('model', 'unknown')}.mp4",
            "视频文件 (*.mp4 *.mov *.avi)"
        )
        
        if file_path:
            try:
                if self.video_url.startswith(('http://', 'https://')):
                    # 下载在线视频
                    response = requests.get(self.video_url, stream=True)
                    response.raise_for_status()
                    
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    # 复制本地文件
                    import shutil
                    shutil.copy(self.video_url, file_path)
                
                QMessageBox.information(self, "成功", f"视频已保存到:\n{file_path}")
                
            except Exception as e:
                QMessageBox.warning(self, "下载失败", f"错误: {str(e)}")
    
    def _format_time(self, ms: int) -> str:
        """格式化时间（毫秒 -> MM:SS）"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_Space:
            self._toggle_play()
        elif event.key() == Qt.Key_F11:
            self._toggle_fullscreen()
        elif event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.player.stop()
        if hasattr(self, 'download_thread') and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait()
        super().closeEvent(event)
