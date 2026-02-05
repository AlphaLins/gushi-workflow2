"""
视频队列页面
视频任务列表、状态刷新、视频预览
"""
from typing import List, Optional, Dict
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel, QGroupBox, QProgressBar,
    QMessageBox, QFileDialog, QMenu
)
from PySide6.QtCore import Signal, Qt, QThread, QTimer
from PySide6.QtGui import QAction, QColor, QBrush

from core.app import get_app_state
from schemas.video_task import VideoTask, VideoTaskStatus


class VideoQueuePage(QWidget):
    """
    视频队列页面

    功能：
    1. 显示视频任务列表
    2. 提交视频生成任务
    3. 轮询刷新状态
    4. 预览和下载视频
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_state = get_app_state()
        self.video_tasks: List[VideoTask] = []
        self.polling_timer: Optional[QTimer] = None

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("视频生成队列")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 控制面板
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # 任务表格
        self.table = self._create_task_table()
        layout.addWidget(self.table)

        # 底部状态
        bottom_layout = QHBoxLayout()

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666;")
        bottom_layout.addWidget(self.status_label)

        bottom_layout.addStretch()

        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.clicked.connect(self._refresh_status)
        self.refresh_btn.setEnabled(False)
        bottom_layout.addWidget(self.refresh_btn)

        layout.addLayout(bottom_layout)

    def _create_control_panel(self) -> QGroupBox:
        """创建控制面板"""
        group = QGroupBox("批量生成视频")
        layout = QHBoxLayout(group)

        # 从图片生成
        self.generate_from_images_btn = QPushButton("从图片生成视频")
        self.generate_from_images_btn.clicked.connect(self._generate_from_images)
        layout.addWidget(self.generate_from_images_btn)

        # 停止轮询
        self.stop_polling_btn = QPushButton("停止轮询")
        self.stop_polling_btn.clicked.connect(self._stop_polling)
        self.stop_polling_btn.setEnabled(False)
        layout.addWidget(self.stop_polling_btn)

        # 下载完成的
        self.download_btn = QPushButton("下载完成的视频")
        self.download_btn.clicked.connect(self._download_completed)
        layout.addWidget(self.download_btn)

        # 浏览本地图片
        self.browse_btn = QPushButton("浏览本地图片")
        self.browse_btn.clicked.connect(self._browse_local_images)
        layout.addWidget(self.browse_btn)

        layout.addStretch()

        return group

    def _create_task_table(self) -> QTableWidget:
        """创建任务表格"""
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "任务 ID", "诗句", "提示词", "模型", "状态", "时长", "创建时间", "操作"
        ])

        # 设置表格属性
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)

        # 列宽设置
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        # 右键菜单
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)

        return table

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.table.itemAt(pos)
        if item is None:
            return

        row = item.row()
        task_id_item = self.table.item(row, 0)
        task_id = task_id_item.text()

        menu = QMenu(self)

        refresh_action = QAction("刷新状态", self)
        refresh_action.triggered.connect(lambda: self._refresh_single_task(task_id))
        menu.addAction(refresh_action)

        download_action = QAction("下载视频", self)
        download_action.triggered.connect(lambda: self._download_single_video(row))
        menu.addAction(download_action)

        preview_action = QAction("预览", self)
        preview_action.triggered.connect(lambda: self._preview_video(row))
        menu.addAction(preview_action)

        delete_action = QAction("删除任务", self)
        delete_action.triggered.connect(lambda: self._delete_task(row))
        menu.addAction(delete_action)

        menu.exec_(self.table.mapToGlobal(pos))

    def set_image_paths(self, paths: List[str]):
        """设置图片路径列表用于生成视频（无视频提示词）"""
        # 转换为带空视频提示词的格式
        self.image_data = [(p, "") for p in paths]
        self.generate_from_images_btn.setEnabled(len(paths) > 0)

    def set_images_with_prompts(self, image_data: List[tuple]):
        """设置图片路径和视频提示词列表 - [(path, video_prompt), ...]"""
        self.image_data = image_data  # [(path, video_prompt), ...]
        self.generate_from_images_btn.setEnabled(len(image_data) > 0)

    def _browse_local_images(self):
        """浏览并选择本地图片文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp);;所有文件 (*.*)"
        )
        if file_paths:
            # 合并已有图片和新选择的图片
            existing_data = getattr(self, 'image_data', []) or []
            existing_paths = [p for p, _ in existing_data]
            new_data = [(p, "") for p in file_paths if p not in existing_paths]
            all_data = existing_data + new_data
            self.image_data = all_data
            self.generate_from_images_btn.setEnabled(len(all_data) > 0)
            QMessageBox.information(self, "导入成功", f"已选择 {len(file_paths)} 张图片，共 {len(all_data)} 张")

    def _generate_from_images(self):
        """从图片生成视频"""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
            QDialogButtonBox, QRadioButton, QGroupBox, QLineEdit,
            QScrollArea, QGridLayout, QFrame, QCheckBox
        )
        from PySide6.QtGui import QPixmap

        dialog = QDialog(self)
        dialog.setWindowTitle("视频生成配置")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(dialog)

        # 选择图片来源
        source_group = QGroupBox("图片来源")
        source_layout = QVBoxLayout(source_group)

        self.use_local_radio = QRadioButton("使用本地生成的图片")
        self.use_local_radio.setChecked(True)
        source_layout.addWidget(self.use_local_radio)

        self.use_url_radio = QRadioButton("手动输入图片 URL")
        source_layout.addWidget(self.use_url_radio)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # 本地图片缩略图网格
        layout.addWidget(QLabel("本地图片 (点击选择/取消选择):"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(250)

        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QGridLayout(self.thumbnail_container)
        self.thumbnail_layout.setSpacing(8)

        # 存储缩略图复选框
        self.image_checkboxes = []

        if hasattr(self, 'image_data') and self.image_data:
            for i, (path, video_prompt) in enumerate(self.image_data):
                # 创建缩略图帧
                frame = QFrame()
                frame.setFrameStyle(QFrame.Box)
                frame.setFixedSize(120, 140)
                frame_layout = QVBoxLayout(frame)
                frame_layout.setContentsMargins(4, 4, 4, 4)

                # 缩略图
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label = QLabel()
                    img_label.setPixmap(scaled)
                    img_label.setAlignment(Qt.AlignCenter)
                    frame_layout.addWidget(img_label)

                # 复选框
                checkbox = QCheckBox()
                checkbox.setChecked(True)  # 默认全选
                checkbox.setProperty("image_path", path)
                checkbox.setProperty("video_prompt", video_prompt)
                # 确保 path 是字符串类型
                path_str = str(path) if not isinstance(path, str) else path
                path_name = Path(path_str).name
                tooltip_text = f"{path_name}\n视频提示词: {video_prompt[:50]}..." if video_prompt else path_name
                checkbox.setToolTip(tooltip_text)
                frame_layout.addWidget(checkbox, alignment=Qt.AlignCenter)

                self.image_checkboxes.append(checkbox)

                # 添加到网格
                row = i // 4
                col = i % 4
                self.thumbnail_layout.addWidget(frame, row, col)

        scroll.setWidget(self.thumbnail_container)
        layout.addWidget(scroll)

        # URL 输入（默认隐藏）
        self.url_group = QGroupBox("图片 URL")
        url_layout = QVBoxLayout(self.url_group)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("输入图片 URL，每行一个（http://... 或 https://...）")
        url_layout.addWidget(self.url_edit)
        self.url_group.setLayout(url_layout)
        self.url_group.setVisible(False)
        layout.addWidget(self.url_group)

        # 视频模型 - 默认选择 grok-video-3-10s
        layout.addWidget(QLabel("视频模型:"))
        from config.api_config import Models
        model_combo = QComboBox()
        default_model_index = 0
        for idx, (model_id, name) in enumerate(Models.VIDEO_MODELS.items()):
            model_combo.addItem(name, model_id)
            if model_id == "grok-video-3-10s":
                default_model_index = idx
        model_combo.setCurrentIndex(default_model_index)
        layout.addWidget(model_combo)

        # 宽高比
        layout.addWidget(QLabel("宽高比:"))
        aspect_combo = QComboBox()
        for ratio, name in Models.ASPECT_RATIOS.items():
            aspect_combo.addItem(name, ratio)
        layout.addWidget(aspect_combo)

        # 连接单选按钮
        self.use_local_radio.toggled.connect(lambda checked: self._toggle_image_source_dialog(scroll, checked))

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            # 收集图片路径
            image_paths = []

            if self.use_url_radio.isChecked():
                # 使用手动输入的 URL
                url_text = self.url_edit.text().strip()
                if not url_text:
                    QMessageBox.warning(self, "输入错误", "请输入至少一个图片 URL")
                    return

                # 按行分割 URL
                for line in url_text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('http://') or line.startswith('https://')):
                        image_paths.append(line)

                if not image_paths:
                    QMessageBox.warning(self, "输入错误", "请输入有效的图片 URL（以 http:// 或 https:// 开头）")
                    return

            else:
                # 使用本地图片 - 从复选框获取选中的（包含视频提示词）
                selected_data = []
                for checkbox in self.image_checkboxes:
                    if checkbox.isChecked():
                        path = checkbox.property("image_path")
                        video_prompt = checkbox.property("video_prompt") or ""
                        selected_data.append((path, video_prompt))

                if not selected_data:
                    QMessageBox.warning(self, "未选择", "请选择至少一张图片")
                    return

            # 启动生成线程
            if self.use_url_radio.isChecked():
                # URL 模式：转换为带空视频提示词的格式
                self._start_video_generation([(p, "") for p in image_paths], model_combo.currentData(), aspect_combo.currentData())
            else:
                self._start_video_generation(selected_data, model_combo.currentData(), aspect_combo.currentData())

    def _toggle_image_source_dialog(self, scroll_widget, use_local: bool):
        """切换图片来源（对话框内）"""
        scroll_widget.setVisible(use_local)
        self.url_group.setVisible(not use_local)

    def _start_video_generation(self, image_data: List[tuple], model: str, aspect_ratio: str):
        """启动视频生成线程 - image_data 为 [(path, video_prompt), ...]"""
        session_id = self.app_state.current_session_id or "default"

        self._video_thread = VideoGenerationThread(
            self.app_state,
            image_data,  # [(path, video_prompt), ...]
            model,
            aspect_ratio,
            session_id
        )
        self._video_thread.task_submitted.connect(self._on_task_submitted)
        self._video_thread.task_updated.connect(self._on_task_updated)
        self._video_thread.finished.connect(self._on_generation_finished)
        self._video_thread.start()

        # 启动轮询
        self._start_polling()

    def _on_task_submitted(self, task: VideoTask):
        """任务提交完成"""
        self.video_tasks.append(task)
        self._add_task_to_table(task)
        self.refresh_btn.setEnabled(True)

    def _on_task_updated(self, task_id: str, status: str):
        """任务状态更新"""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == task_id:
                # 更新状态
                status_item = self.table.item(row, 4)

                # 设置颜色映射（包含所有状态）
                status_colors = {
                    # 通用状态
                    VideoTaskStatus.PENDING: "#999999",
                    VideoTaskStatus.SUBMITTED: "#2196F3",
                    VideoTaskStatus.QUEUED: "#FF9800",
                    VideoTaskStatus.PROCESSING: "#9C27B0",
                    VideoTaskStatus.COMPLETED: "#4CAF50",
                    VideoTaskStatus.FAILED: "#F44336",
                    VideoTaskStatus.CANCELLED: "#757575",
                    VideoTaskStatus.ERROR: "#D32F2F",
                    # Veo 子状态
                    VideoTaskStatus.IMAGE_DOWNLOADING: "#7B1FA2",
                    VideoTaskStatus.VIDEO_GENERATING: "#8E24AA",
                    VideoTaskStatus.VIDEO_UPSAMPLING: "#AB47BC",
                }

                # 使用 from_api_status 获取枚举并映射颜色
                enum_status = VideoTaskStatus.from_api_status(status)
                color = status_colors.get(enum_status, "#000000")

                # 显示原始状态（更详细的 API 状态）
                display_status = status.replace("_", " ").title()

                status_item.setText(display_status)
                status_item.setForeground(QBrush(QColor(color)))
                status_item.setTextAlignment(Qt.AlignCenter)

                break

    def _on_generation_finished(self):
        """生成完成"""
        self.stop_polling_btn.setEnabled(False)

    def _add_task_to_table(self, task: VideoTask):
        """添加任务到表格"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 任务 ID
        self.table.setItem(row, 0, QTableWidgetItem(task.task_id))

        # 诗句
        self.table.setItem(row, 1, QTableWidgetItem(f"诗句 {task.verse_index}"))

        # 提示词
        prompt_text = str(task.video_prompt)[:50] + "..." if task.video_prompt else ""
        self.table.setItem(row, 2, QTableWidgetItem(prompt_text))

        # 模型
        self.table.setItem(row, 3, QTableWidgetItem(task.model))

        # 状态
        status_item = QTableWidgetItem(task.status.value)
        self._set_status_color(status_item, task.status)
        self.table.setItem(row, 4, status_item)

        # 时长
        duration_text = f"{task.duration:.1f}s" if task.duration else "-"
        self.table.setItem(row, 5, QTableWidgetItem(duration_text))

        # 创建时间
        time_text = task.created_at.strftime("%H:%M:%S")
        self.table.setItem(row, 6, QTableWidgetItem(time_text))

        # 操作按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(5, 2, 5, 2)

        preview_btn = QPushButton("预览")
        preview_btn.setMaximumWidth(50)
        preview_btn.clicked.connect(lambda: self._preview_video(row))
        btn_layout.addWidget(preview_btn)

        download_btn = QPushButton("下载")
        download_btn.setMaximumWidth(50)
        download_btn.clicked.connect(lambda: self._download_single_video(row))
        btn_layout.addWidget(download_btn)

        self.table.setCellWidget(row, 7, btn_widget)

    def _set_status_color(self, item: QTableWidgetItem, status: VideoTaskStatus):
        """设置状态颜色"""
        colors = {
            # 通用状态
            VideoTaskStatus.PENDING: "#999999",
            VideoTaskStatus.SUBMITTED: "#2196F3",
            VideoTaskStatus.QUEUED: "#FF9800",
            VideoTaskStatus.PROCESSING: "#9C27B0",
            VideoTaskStatus.COMPLETED: "#4CAF50",
            VideoTaskStatus.FAILED: "#F44336",
            VideoTaskStatus.CANCELLED: "#757575",
            VideoTaskStatus.ERROR: "#D32F2F",
            # Veo 子状态
            VideoTaskStatus.IMAGE_DOWNLOADING: "#7B1FA2",
            VideoTaskStatus.VIDEO_GENERATING: "#8E24AA",
            VideoTaskStatus.VIDEO_UPSAMPLING: "#AB47BC",
        }
        color = colors.get(status, "#000000")
        item.setForeground(QBrush(QColor(color)))
        item.setTextAlignment(Qt.AlignCenter)

    def _start_polling(self):
        """启动状态轮询"""
        if self.polling_timer is None:
            self.polling_timer = QTimer()
            self.polling_timer.timeout.connect(self._refresh_status)

        self.polling_timer.start(5000)  # 5秒间隔
        self.stop_polling_btn.setEnabled(True)
        self.status_label.setText("轮询中...")

    def _stop_polling(self):
        """停止状态轮询"""
        if self.polling_timer:
            self.polling_timer.stop()
        self.stop_polling_btn.setEnabled(False)
        self.status_label.setText("轮询已停止")

    def _refresh_status(self):
        """刷新所有任务状态"""
        if not self.video_tasks:
            return

        pending_tasks = [t for t in self.video_tasks if t.is_processing()]

        if not pending_tasks:
            self._stop_polling()
            return

        for task in pending_tasks:
            try:
                client = self.app_state.video_client
                status_data = client.get_task_status(task.task_id)

                # 使用 from_api_status 方法解析 API 状态
                api_status = status_data.get("status", "pending")
                new_status = VideoTaskStatus.from_api_status(api_status)
                task.update_status(new_status)

                # 如果完成，设置结果
                if new_status == VideoTaskStatus.COMPLETED:
                    task.video_url = status_data.get("video_url")
                    # 支持多种 duration 字段名
                    task.duration = (
                        status_data.get("duration") or
                        status_data.get("video_duration") or
                        (status_data.get("completed_at") - task.submit_time.timestamp() if task.submit_time else None)
                    )

                self._on_task_updated(task.task_id, api_status)

            except Exception as e:
                self.app_state.logger.error(f"刷新状态失败 {task.task_id}: {e}")

        completed = sum(1 for t in self.video_tasks if t.is_finished())
        self.status_label.setText(f"进度: {completed}/{len(self.video_tasks)}")

    def _refresh_single_task(self, task_id: str):
        """刷新单个任务状态"""
        for task in self.video_tasks:
            if task.task_id == task_id:
                try:
                    client = self.app_state.video_client
                    status_data = client.get_task_status(task_id)

                    # 使用 from_api_status 方法解析 API 状态
                    api_status = status_data.get("status", "pending")
                    new_status = VideoTaskStatus.from_api_status(api_status)
                    task.update_status(new_status)

                    if new_status == VideoTaskStatus.COMPLETED:
                        task.video_url = status_data.get("video_url")
                        # 支持多种 duration 字段名
                        task.duration = (
                            status_data.get("duration") or
                            status_data.get("video_duration") or
                            (status_data.get("completed_at") - task.submit_time.timestamp() if task.submit_time else None)
                        )

                    self._on_task_updated(task_id, api_status)

                except Exception as e:
                    QMessageBox.critical(self, "刷新失败", f"刷新失败: {str(e)}")

                break

    def _preview_video(self, row: int):
        """预览视频"""
        task_id = self.table.item(row, 0).text()
        task = next((t for t in self.video_tasks if t.task_id == task_id), None)

        if task and task.video_url:
            import webbrowser
            webbrowser.open(task.video_url)
        else:
            QMessageBox.information(self, "预览", "视频尚未生成完成")

    def _download_single_video(self, row: int):
        """下载单个视频"""
        task_id = self.table.item(row, 0).text()
        task = next((t for t in self.video_tasks if t.task_id == task_id), None)

        if task and task.video_url:
            directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if directory:
                try:
                    client = self.app_state.video_client
                    filename = f"{task_id}.mp4"
                    save_path = Path(directory) / filename
                    client.download_video(task.video_url, save_path)
                    QMessageBox.information(self, "下载成功", f"视频已保存到 {save_path}")
                except Exception as e:
                    QMessageBox.critical(self, "下载失败", f"下载失败: {str(e)}")
        else:
            QMessageBox.information(self, "下载", "视频尚未生成完成")

    def _download_completed(self):
        """批量下载完成的视频"""
        completed_tasks = [t for t in self.video_tasks if t.status == VideoTaskStatus.COMPLETED]

        if not completed_tasks:
            QMessageBox.information(self, "下载", "没有已完成的视频")
            return

        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if directory:
            import os
            client = self.app_state.video_client
            success_count = 0

            for task in completed_tasks:
                try:
                    filename = f"verse_{task.verse_index}_prompt_{task.prompt_index}.mp4"
                    save_path = Path(directory) / filename
                    client.download_video(task.video_url, save_path)
                    success_count += 1
                except Exception as e:
                    self.app_state.logger.error(f"下载失败 {task.task_id}: {e}")

            QMessageBox.information(
                self,
                "下载完成",
                f"成功下载 {success_count}/{len(completed_tasks)} 个视频"
            )

    def _delete_task(self, row: int):
        """删除任务"""
        task_id = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除任务 {task_id} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.table.removeRow(row)
            self.video_tasks = [t for t in self.video_tasks if t.task_id != task_id]


class VideoGenerationThread(QThread):
    """视频生成线程"""

    task_submitted = Signal(object)
    task_updated = Signal(str, str)
    finished = Signal()

    def __init__(self, app_state, image_data: List[tuple], model: str, aspect_ratio: str, session_id: str):
        super().__init__()
        self.app_state = app_state
        self.image_data = image_data  # [(path, video_prompt), ...]
        self.model = model
        self.aspect_ratio = aspect_ratio
        self.session_id = session_id

    def run(self):
        """运行生成任务"""
        uploader = self.app_state.image_uploader
        client = self.app_state.video_client

        for i, item in enumerate(self.image_data):
            try:
                # 兼容多种数据格式：
                # 1. 元组格式: (path, video_prompt)
                # 2. 字典格式: {'path': ..., 'video_prompt': ..., 'description': ...}
                if isinstance(item, tuple):
                    image_path, video_prompt = item[0], item[1]
                elif isinstance(item, dict):
                    image_path = item.get('path', '')
                    video_prompt = item.get('video_prompt', '')
                else:
                    # 如果是字符串，作为路径处理
                    image_path = str(item)
                    video_prompt = ""

                # 确保路径是字符串
                image_path = str(image_path) if not isinstance(image_path, str) else image_path

                # 判断是 URL 还是本地路径
                if image_path.startswith('http://') or image_path.startswith('https://'):
                    image_url = image_path  # 直接使用 URL
                else:
                    # 本地路径，需要先上传到图床获取 URL
                    from pathlib import Path
                    print(f"Uploading image: {image_path}")
                    image_url = uploader.upload_single(Path(image_path))

                # 使用视频提示词，如果为空则使用默认文本
                prompt = video_prompt if video_prompt else "Animated video based on the image"
                
                # 提交视频任务
                result = client.submit_task(
                    model=self.model,
                    prompt=prompt,
                    image_urls=[image_url],
                    aspect_ratio=self.aspect_ratio
                )

                # 创建任务对象
                from datetime import datetime
                task = VideoTask(
                    task_id=result.get("id", ""),
                    status=VideoTaskStatus.PENDING,
                    verse_index=i,
                    prompt_index=0,
                    source_image_path=image_path,
                    model=self.model,
                    created_at=datetime.now()
                )
                task.update_status(VideoTaskStatus.SUBMITTED)

                self.task_submitted.emit(task)

            except Exception as e:
                self.app_state.logger.error(f"提交视频任务失败 ({image_path}): {e}")

        self.finished.emit()
