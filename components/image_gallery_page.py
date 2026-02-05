"""
图像生成页面
生成图像、画廊展示、图片预览、重新生成、选择生成视频
"""
from typing import List, Optional, Dict
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QProgressBar, QGroupBox,
    QScrollArea, QFrame, QMessageBox, QFileDialog,
    QDialog, QTabWidget, QCheckBox, QInputDialog
)
from PySide6.QtCore import Signal, Qt, QThread
from PySide6.QtGui import QPixmap, QCursor

from core.app import get_app_state
from schemas.poetry import PoetryPromptsResponse


class ImageGalleryPage(QWidget):
    """
    图像生成页面

    功能：
    1. 显示待生成的提示词列表
    2. 进度条显示生成进度
    3. 画廊展示生成的图片
    4. 图片放大预览
    5. 单张图片重新生成
    6. 选择图片生成视频
    7. 视频预览
    8. 失败重试
    """

    images_generated = Signal(list)  # 图像生成完成信号 [(path, video_prompt), ...]
    generate_video_requested = Signal(list)  # 生成视频请求信号 [(path, video_prompt), ...]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_state = get_app_state()
        self.prompts: Optional[PoetryPromptsResponse] = None
        self.generated_images: Dict[tuple, dict] = {}  # (verse_index, prompt_index) -> {path, video_prompt, description}
        self.selected_images: set = set()  # 选中的图片索引

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("图像生成与管理")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 控制面板
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("等待生成...")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        # 创建标签页（待生成、图像画廊、视频队列）
        self.tab_widget = QTabWidget()

        # 待生成列表
        self.pending_widget = self._create_pending_widget()
        self.tab_widget.addTab(self.pending_widget, "待生成")

        # 图像画廊（增强版）
        self.gallery_widget = self._create_gallery_widget()
        self.tab_widget.addTab(self.gallery_widget, "图像画廊")

        layout.addWidget(self.tab_widget)

    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # 生成按钮
        self.generate_btn = QPushButton("🎨 生成图像")
        self.generate_btn.clicked.connect(self._start_generation)
        layout.addWidget(self.generate_btn)

        # 停止按钮
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.clicked.connect(self._stop_generation)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        # 重试失败
        self.retry_btn = QPushButton("🔄 重试失败")
        self.retry_btn.clicked.connect(self._retry_failed)
        layout.addWidget(self.retry_btn)

        layout.addStretch()

        # 选择操作区
        self.select_all_btn = QPushButton("☑️ 全选")
        self.select_all_btn.clicked.connect(self._select_all_images)
        layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("◻️ 反选")
        self.deselect_all_btn.clicked.connect(self._deselect_all_images)
        layout.addWidget(self.deselect_all_btn)

        # 批量操作
        self.regenerate_selected_btn = QPushButton("🔄 重新生成选中")
        self.regenerate_selected_btn.clicked.connect(self._regenerate_selected_images)
        layout.addWidget(self.regenerate_selected_btn)
        
        # 编辑提示词按钮
        self.edit_prompt_btn = QPushButton("✏️ 编辑提示词")
        self.edit_prompt_btn.clicked.connect(self._edit_selected_prompts)
        self.edit_prompt_btn.setToolTip("编辑选中图片的提示词并重新生成")
        layout.addWidget(self.edit_prompt_btn)

        self.generate_video_btn = QPushButton("🎬 生成视频")
        self.generate_video_btn.clicked.connect(self._generate_video_from_selected)
        layout.addWidget(self.generate_video_btn)

        self.export_btn = QPushButton("📥 导出选中")
        self.export_btn.clicked.connect(self._export_images)
        layout.addWidget(self.export_btn)

        return widget

    def _create_pending_widget(self) -> QWidget:
        """创建待生成列表"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.pending_list = QLabel("暂无待生成的提示词\n\n请先在「诗词输入」页面生成提示词")
        self.pending_list.setAlignment(Qt.AlignCenter)
        self.pending_list.setStyleSheet("color: #999;")
        layout.addWidget(self.pending_list)

        return widget

    def _create_gallery_widget(self) -> QWidget:
        """创建增强的图像画廊"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 工具栏
        toolbar = QHBoxLayout()

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self._select_all_images)
        toolbar.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self._deselect_all_images)
        toolbar.addWidget(self.deselect_all_btn)

        self.regenerate_selected_btn = QPushButton("重新生成选中的")
        self.regenerate_selected_btn.clicked.connect(self._regenerate_selected_images)
        self.regenerate_selected_btn.setEnabled(False)
        toolbar.addWidget(self.regenerate_selected_btn)

        self.generate_video_btn = QPushButton("生成视频 (选中)")
        self.generate_video_btn.clicked.connect(self._generate_video_from_selected)
        self.generate_video_btn.setEnabled(False)
        toolbar.addWidget(self.generate_video_btn)

        toolbar.addStretch()

        self.selected_count_label = QLabel("已选: 0 张")
        toolbar.addWidget(self.selected_count_label)

        layout.addLayout(toolbar)

        # 画廊网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.gallery_container = QWidget()
        self.gallery_layout = QGridLayout(self.gallery_container)
        self.gallery_layout.setSpacing(15)
        scroll.setWidget(self.gallery_container)

        layout.addWidget(scroll)

        return widget

    def set_prompts(self, prompts: PoetryPromptsResponse):
        """设置提示词数据"""
        self.prompts = prompts
        self.generate_btn.setEnabled(True)
        self._update_pending_list()

    def _update_pending_list(self):
        """更新待生成列表"""
        if self.prompts is None:
            return

        total = self.prompts.total_prompts()
        generated = len([v for v in self.generated_images.values() if v and v.get('path')])
        pending = total - generated

        if pending > 0:
            text = f"待生成: {pending} 张图片\n已生成: {generated} 张\n总计: {total} 张"
        else:
            text = f"全部生成完成！\n总计: {total} 张图片"

        self.pending_list.setText(text)

    def _start_generation(self):
        """开始生成图像"""
        if self.prompts is None:
            return

        # 收集待生成的提示词
        to_generate = []
        for verse_index, prompt_index, description, video_prompt in self.prompts.all_descriptions():
            key = (verse_index, prompt_index)
            if key not in self.generated_images or not self.generated_images[key].get('path'):
                to_generate.append((verse_index, prompt_index, description, video_prompt))

        if not to_generate:
            QMessageBox.information(self, "生成完成", "所有提示词均已生成图像")
            return

        # 启动生成线程
        self.generate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(to_generate))
        self.progress_bar.setValue(0)

        self._generation_thread = ImageGenerationThread(
            self.app_state,
            to_generate,
            self.prompts,
            self.app_state.current_session_id or "default"
        )
        self._generation_thread.progress.connect(self._on_generation_progress)
        self._generation_thread.image_ready.connect(self._on_image_ready)
        self._generation_thread.finished.connect(self._on_generation_finished)
        self._generation_thread.failed.connect(self._on_generation_failed)
        self._generation_thread.start()

    def _stop_generation(self):
        """停止生成"""
        if hasattr(self, '_generation_thread') and self._generation_thread.isRunning():
            self._generation_thread.stop()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("正在停止...")

    def _retry_failed(self):
        """重试失败的图片"""
        # 清除失败的图片记录
        failed_keys = [k for k, v in self.generated_images.items() if not v or not v.get('path')]
        for key in failed_keys:
            del self.generated_images[key]

        self._update_pending_list()
        self.retry_btn.setEnabled(False)

        if self.prompts:
            self._start_generation()

    def _on_generation_progress(self, current: int, total: int):
        """生成进度更新"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"生成中... {current}/{total}")

    def _on_image_ready(self, verse_index: int, prompt_index: int, path: Optional[str], video_prompt: str = "", description: str = ""):
        """图片生成完成"""
        key = (verse_index, prompt_index)
        self.generated_images[key] = {'path': path, 'video_prompt': video_prompt, 'description': description}
        self._add_to_gallery(verse_index, prompt_index, path, video_prompt, description)
        self._update_pending_list()

    def _on_generation_finished(self):
        """生成完成"""
        self.generate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 获取成功生成的图片路径和视频提示词（过滤 None 值）
        successful_images = []
        for v in self.generated_images.values():
            if v and v.get('path'):
                successful_images.append((v['path'], v.get('video_prompt', '')))

        generated = len(successful_images)
        total = len(self.generated_images)

        self.status_label.setText(f"生成完成: {generated}/{total}")

        # 发出信号，传递成功的图片路径和视频提示词
        if successful_images:
            self.images_generated.emit(successful_images)

        # 检查是否有失败
        failed = total - generated
        if failed > 0:
            self.retry_btn.setEnabled(True)
            QMessageBox.warning(
                self,
                "生成部分完成",
                f"成功生成 {generated} 张，失败 {failed} 张。\n可以点击「重试失败」重新生成失败的图片。"
            )

    def _on_generation_failed(self, verse_index: int, prompt_index: int, error: str):
        """图片生成失败"""
        key = (verse_index, prompt_index)
        self.generated_images[key] = {'path': None, 'video_prompt': '', 'description': '', 'error': error}
        self.app_state.logger.error(f"图像生成失败 ({verse_index}, {prompt_index}): {error}")

    def _add_to_gallery(self, verse_index: int, prompt_index: int, path: Optional[str], video_prompt: str = "", description: str = ""):
        """添加图片到画廊"""
        if path is None or not Path(path).exists():
            return

        # 创建可交互的图片卡片
        card = self._create_image_card(verse_index, prompt_index, path, video_prompt, description)

        # 添加到网格
        current_count = self.gallery_layout.count()
        row = current_count // 3
        col = current_count % 3
        self.gallery_layout.addWidget(card, row, col)

    def _create_image_card(self, verse_index: int, prompt_index: int, path: str, video_prompt: str, description: str = "") -> QFrame:
        """创建图片卡片"""
        from PySide6.QtWidgets import QCheckBox

        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setFixedSize(280, 320)
        card.setStyleSheet("""
            QFrame {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QFrame:hover {
                border-color: #2196F3;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)

        # 顶部：复选框
        checkbox = QCheckBox()
        checkbox.setChecked(False)
        checkbox.stateChanged.connect(lambda state, k=(verse_index, prompt_index): self._on_image_selected(k, state))
        layout.addWidget(checkbox)

        # 图片（可点击放大）
        image_label = ClickableLabel(path, verse_index, prompt_index, self)
        pixmap = QPixmap(path)
        scaled_pixmap = pixmap.scaled(250, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(image_label)

        # 信息标签
        verse = self.prompts.get_verse(verse_index) if self.prompts else None
        if verse:
            label_text = f"{verse.verse[:15]}... #{prompt_index + 1}"
        else:
            label_text = f"诗句 {verse_index} #{prompt_index + 1}"

        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")
        layout.addWidget(label)

        # 视频提示词预览
        if video_prompt:
            video_label = QLabel(f"🎬 {video_prompt[:30]}...")
            video_label.setStyleSheet("font-size: 9px; color: #2196F3;")
            video_label.setToolTip(video_prompt)
            video_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(video_label)

        # 操作按钮
        btn_layout = QHBoxLayout()

        regenerate_btn = QPushButton("重新生成")
        regenerate_btn.setMaximumWidth(80)
        regenerate_btn.clicked.connect(lambda: self._regenerate_single_image(verse_index, prompt_index))
        btn_layout.addWidget(regenerate_btn)

        video_btn = QPushButton("生成视频")
        video_btn.setMaximumWidth(80)
        video_btn.clicked.connect(lambda: self._generate_video_from_single(verse_index, prompt_index))
        btn_layout.addWidget(video_btn)

        layout.addLayout(btn_layout)

        return card

    def _on_image_selected(self, key: tuple, state: int):
        """图片选中状态变化"""
        if state == Qt.Checked.value:
            self.selected_images.add(key)
        else:
            self.selected_images.discard(key)

        self.selected_count_label.setText(f"已选: {len(self.selected_images)} 张")
        self.regenerate_selected_btn.setEnabled(len(self.selected_images) > 0)
        self.generate_video_btn.setEnabled(len(self.selected_images) > 0)

    def _select_all_images(self):
        """全选图片"""
        self.selected_images.clear()
        for key in self.generated_images.keys():
            if self.generated_images[key].get('path'):
                self.selected_images.add(key)
        self.selected_count_label.setText(f"已选: {len(self.selected_images)} 张")
        self.regenerate_selected_btn.setEnabled(len(self.selected_images) > 0)
        self.generate_video_btn.setEnabled(len(self.selected_images) > 0)
        # 更新所有复选框状态
        self._update_all_checkboxes(True)

    def _deselect_all_images(self):
        """取消全选"""
        self.selected_images.clear()
        self.selected_count_label.setText("已选: 0 张")
        self.regenerate_selected_btn.setEnabled(False)
        self.generate_video_btn.setEnabled(False)
        self._update_all_checkboxes(False)

    def _update_all_checkboxes(self, _checked: bool):
        """更新所有复选框状态"""
        # 重新创建画廊以更新复选框状态
        self._refresh_gallery()

    def _refresh_gallery(self):
        """刷新画廊显示"""
        # 清空现有画廊
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新添加所有图片
        for (verse_index, prompt_index), data in self.generated_images.items():
            if data and data.get('path'):
                self._add_to_gallery(
                    verse_index,
                    prompt_index,
                    data['path'],
                    data.get('video_prompt', ''),
                    data.get('description', '')
                )

    def _regenerate_single_image(self, verse_index: int, prompt_index: int):
        """重新生成单张图片"""
        key = (verse_index, prompt_index)
        if key not in self.generated_images:
            return

        # 获取原始描述
        descriptions = self.prompts.all_descriptions()
        for vi, pi, desc, video_prompt in descriptions:
            if vi == verse_index and pi == prompt_index:
                # 删除旧图片
                old_path = self.generated_images[key].get('path')
                if old_path and Path(old_path).exists():
                    try:
                        Path(old_path).unlink()
                    except:
                        pass

                # 重新生成
                self._regenerate_images([(verse_index, prompt_index, desc, video_prompt)])
                return

    def _regenerate_selected_images(self):
        """重新生成选中的图片"""
        if not self.selected_images:
            return

        to_regenerate = []
        for verse_index, prompt_index in self.selected_images:
            # 获取原始描述
            descriptions = self.prompts.all_descriptions()
            for vi, pi, desc, video_prompt in descriptions:
                if vi == verse_index and pi == prompt_index:
                    # 删除旧图片
                    key = (vi, pi)
                    old_path = self.generated_images[key].get('path')
                    if old_path and Path(old_path).exists():
                        try:
                            Path(old_path).unlink()
                        except:
                            pass

                    to_regenerate.append((verse_index, prompt_index, desc, video_prompt))
                    break

        if to_regenerate:
            self._regenerate_images(to_regenerate)

    def _regenerate_images(self, tasks: List[tuple]):
        """重新生成指定图片"""
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(tasks))
        self.progress_bar.setValue(0)

        # 清空画廊重新生成
        self.selected_images.clear()

        self._generation_thread = ImageGenerationThread(
            self.app_state,
            tasks,
            self.prompts,
            self.app_state.current_session_id or "default"
        )
        self._generation_thread.progress.connect(self._on_generation_progress)
        self._generation_thread.image_ready.connect(self._on_image_ready)
        self._generation_thread.finished.connect(self._on_regeneration_finished)
        self._generation_thread.failed.connect(self._on_generation_failed)
        self._generation_thread.start()

    def _on_regeneration_finished(self):
        """重新生成完成"""
        self._on_generation_finished()
        # 刷新画廊显示
        self._refresh_gallery()

    def _generate_video_from_single(self, verse_index: int, prompt_index: int):
        """从单张图片生成视频"""
        key = (verse_index, prompt_index)
        if key not in self.generated_images:
            return

        data = self.generated_images[key]
        if not data or not data.get('path'):
            QMessageBox.warning(self, "无法生成视频", "图片未生成或已失败")
            return

        # 发送生成视频请求信号
        self.generate_video_requested.emit([(data['path'], data.get('video_prompt', ''))])

    def _generate_video_from_selected(self):
        """从选中的图片生成视频"""
        if not self.selected_images:
            return

        images_data = []
        for verse_index, prompt_index in self.selected_images:
            key = (verse_index, prompt_index)
            if key in self.generated_images:
                data = self.generated_images[key]
                if data and data.get('path'):
                    images_data.append((data['path'], data.get('video_prompt', '')))

        if images_data:
            # 发送生成视频请求信号
            self.generate_video_requested.emit(images_data)

    def show_image_preview(self, path: str, verse_index: int, prompt_index: int):
        """显示图片预览对话框"""
        dialog = ImagePreviewDialog(path, verse_index, prompt_index, self.prompts, self.generated_images, self)
        dialog.preview_regenerated.connect(self._on_preview_regenerate)
        dialog.exec()

    def _on_preview_regenerate(self, verse_index: int, prompt_index: int, new_prompt: str):
        """预览对话框中重新生成"""
        # 获取视频提示词
        key = (verse_index, prompt_index)
        video_prompt = ""
        if key in self.generated_images:
            video_prompt = self.generated_images[key].get('video_prompt', '')

        # 删除旧图片
        old_path = self.generated_images[key].get('path')
        if old_path and Path(old_path).exists():
            try:
                Path(old_path).unlink()
            except:
                pass

        # 重新生成
        self._regenerate_images([(verse_index, prompt_index, new_prompt, video_prompt)])

    def _export_images(self):
        """导出选中的图片"""
        if not self.selected_images:
            QMessageBox.information(self, "提示", "请先选择要导出的图片")
            return

        # 选择导出格式
        from PySide6.QtWidgets import QDialog, QRadioButton, QDialogButtonBox, QVBoxLayout
        
        format_dialog = QDialog(self)
        format_dialog.setWindowTitle("选择导出格式")
        layout = QVBoxLayout(format_dialog)
        
        folder_radio = QRadioButton("📁 复制到文件夹")
        folder_radio.setChecked(True)
        zip_radio = QRadioButton("📦 打包为 ZIP（包含元数据）")
        
        layout.addWidget(folder_radio)
        layout.addWidget(zip_radio)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(format_dialog.accept)
        buttons.rejected.connect(format_dialog.reject)
        layout.addWidget(buttons)
        
        if format_dialog.exec() != QDialog.Accepted:
            return
        
        # 执行导出
        if zip_radio.isChecked():
            self._export_as_zip()
        else:
            self._export_to_folder()
    
    def _export_to_folder(self):
        """导出到文件夹"""
        directory = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not directory:
            return
            
        import shutil
        export_count = 0

        for verse_index, prompt_index in self.selected_images:
            key = (verse_index, prompt_index)
            if key in self.generated_images:
                path = self.generated_images[key].get('path')
                if path and Path(path).exists():
                    dest = Path(directory) / Path(path).name
                    shutil.copy(path, dest)
                    export_count += 1

        QMessageBox.information(
            self,
            "导出完成",
            f"已导出 {export_count} 张图片到 {directory}"
        )
    
    def _export_as_zip(self):
        """导出为 ZIP 文件（包含元数据）"""
        import zipfile
        import json
        from datetime import datetime
        
        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 ZIP",
            f"images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            "ZIP 文件 (*.zip)"
        )
        
        if not file_path:
            return
        
        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                metadata_list = []
                
                for verse_index, prompt_index in self.selected_images:
                    key = (verse_index, prompt_index)
                    if key in self.generated_images:
                        img_data = self.generated_images[key]
                        path = img_data.get('path')
                        
                        if path and Path(path).exists():
                            # 添加图片到 ZIP
                            arcname = f"verse_{verse_index}_prompt_{prompt_index}_{Path(path).name}"
                            zipf.write(path, arcname)
                            
                            # 收集元数据
                            metadata_list.append({
                                'filename': arcname,
                                'verse_index': verse_index,
                                'prompt_index': prompt_index,
                                'image_prompt': img_data.get('description', ''),
                                'video_prompt': img_data.get('video_prompt', ''),
                                'generated_at': datetime.now().isoformat()
                            })
                
                # 添加元数据文件
                metadata_json = json.dumps(metadata_list, ensure_ascii=False, indent=2)
                zipf.writestr('metadata.json', metadata_json)
                
                # 添加 README
                readme_content = f"""# 图像导出包

导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
图片数量: {len(metadata_list)}

## 文件说明
- metadata.json: 图片元数据（提示词、索引等）
- verse_*_prompt_*.png: 生成的图片

## 元数据格式
每张图片包含：
- filename: 文件名
- verse_index: 诗句索引
- prompt_index: 提示词索引
- image_prompt: 图像提示词
- video_prompt: 视频提示词
- generated_at: 生成时间
"""
                zipf.writestr('README.txt', readme_content)
            
            QMessageBox.information(
                self,
                "导出成功",
                f"已导出 {len(metadata_list)} 张图片到:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"错误: {str(e)}")

    def _edit_selected_prompts(self):
        """编辑选中图片的提示词并重新生成"""
        if not self.selected_images:
            QMessageBox.information(self, "提示", "请先选择要编辑的图片")
            return
        
        from PySide6.QtWidgets import QInputDialog
        
        # 如果只选了一张图，显示当前提示词
        if len(self.selected_images) == 1:
            verse_index, prompt_index = list(self.selected_images)[0]
            key = (verse_index, prompt_index)
            current_prompt = ""
            
            if key in self.generated_images:
                current_prompt = self.generated_images[key].get('description', '')
            
            # 编辑提示词
            new_prompt, ok = QInputDialog.getMultiLineText(
                self,
                "编辑图像提示词",
                f"诗句 {verse_index + 1} - 提示词 {prompt_index + 1}:",
                current_prompt
            )
            
            if ok and new_prompt.strip():
                # 重新生成这一张
                self._regenerate_with_new_prompt(verse_index, prompt_index, new_prompt.strip())
        else:
            # 多张图片，使用统一提示词
            new_prompt, ok = QInputDialog.getMultiLineText(
                self,
                "批量编辑提示词",
                f"将为选中的 {len(self.selected_images)} 张图片使用新提示词:",
                "A beautiful scene in traditional Chinese art style..."
            )
            
            if ok and new_prompt.strip():
                for verse_index, prompt_index in self.selected_images:
                    self._regenerate_with_new_prompt(verse_index, prompt_index, new_prompt.strip())
    
    def _regenerate_with_new_prompt(self, verse_index: int, prompt_index: int, new_prompt: str):
        """使用新提示词重新生成单张图片"""
        key = (verse_index, prompt_index)
        
        # 更新提示词数据
        if self.prompts and verse_index < len(self.prompts.prompts):
            verse_prompts = self.prompts.prompts[verse_index]
            if prompt_index < len(verse_prompts.descriptions):
                verse_prompts.descriptions[prompt_index].description = new_prompt
        
        # 触发重新生成
        self._regenerate_images([(verse_index, prompt_index, new_prompt, self.generated_images[key].get('video_prompt', ''))])


class ClickableLabel(QLabel):
    """可点击的图片标签"""

    def __init__(self, path: str, verse_index: int, prompt_index: int, gallery_page: ImageGalleryPage):
        super().__init__()
        self.path = path
        self.verse_index = verse_index
        self.prompt_index = prompt_index
        self.gallery_page = gallery_page

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.gallery_page.show_image_preview(self.path, self.verse_index, self.prompt_index)
        super().mousePressEvent(event)


class ImagePreviewDialog(QDialog):
    """图片预览对话框"""

    preview_regenerated = Signal(int, int, str)  # 重新生成信号

    def __init__(self, path: str, verse_index: int, prompt_index: int,
                 prompts: Optional[PoetryPromptsResponse],
                 generated_images: Dict,
                 parent=None):
        super().__init__(parent)
        self.path = path
        self.verse_index = verse_index
        self.prompt_index = prompt_index
        self.prompts = prompts
        self.generated_images = generated_images
        
        # MJ 相关状态
        self.mj_task_id = None
        self.mj_buttons = []
        self.mj_worker = None

        self.setWindowTitle("图片预览")
        self.setMinimumSize(900, 700)
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 图片显示
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.image_label = QLabel()
        pixmap = QPixmap(self.path)
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll.setWidget(self.image_label)

        layout.addWidget(scroll)

        # 信息区域
        info_group = QGroupBox("图片信息")
        info_layout = QGridLayout()

        # 诗句
        verse = self.prompts.get_verse(self.verse_index) if self.prompts else None
        if verse:
            info_layout.addWidget(QLabel("诗句:"), 0, 0)
            info_layout.addWidget(QLabel(verse.verse), 0, 1)

        # 图像提示词
        key = (self.verse_index, self.prompt_index)
        if key in self.generated_images:
            data = self.generated_images[key]
            description = data.get('description', '')
            if description:
                info_layout.addWidget(QLabel("图像提示词:"), 1, 0)
                desc_label = QLabel(description[:100] + "..." if len(description) > 100 else description)
                desc_label.setWordWrap(True)
                info_layout.addWidget(desc_label, 1, 1)

            # 视频提示词
            video_prompt = data.get('video_prompt', '')
            if video_prompt:
                info_layout.addWidget(QLabel("视频提示词:"), 2, 0)
                video_label = QLabel(video_prompt[:100] + "..." if len(video_prompt) > 100 else video_prompt)
                video_label.setWordWrap(True)
                info_layout.addWidget(video_label, 2, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # MJ 处理面板
        self._create_mj_panel(layout)

        # 按钮区域
        btn_layout = QHBoxLayout()

        edit_prompt_btn = QPushButton("修改提示词并重新生成")
        edit_prompt_btn.clicked.connect(self._edit_and_regenerate)
        btn_layout.addWidget(edit_prompt_btn)

        generate_video_btn = QPushButton("生成视频")
        generate_video_btn.clicked.connect(self._generate_video)
        btn_layout.addWidget(generate_video_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _create_mj_panel(self, parent_layout):
        """创建 Midjourney 处理面板"""
        mj_group = QGroupBox("Midjourney 处理")
        mj_layout = QVBoxLayout()

        # 说明
        hint = QLabel("上传图片到 Midjourney 进行以图生图、放大、变换等操作")
        hint.setStyleSheet("color: #888;")
        mj_layout.addWidget(hint)

        # 进度条
        self.mj_progress = QProgressBar()
        self.mj_progress.setTextVisible(True)
        self.mj_progress.setFormat("就绪")
        self.mj_progress.setValue(0)
        mj_layout.addWidget(self.mj_progress)

        # 状态标签
        self.mj_status_label = QLabel("")
        mj_layout.addWidget(self.mj_status_label)

        # 启动按钮
        start_layout = QHBoxLayout()
        
        self.mj_start_btn = QPushButton("🎨 开始 MJ 处理")
        self.mj_start_btn.setStyleSheet("padding: 8px 16px; font-weight: bold;")
        self.mj_start_btn.clicked.connect(self._start_mj_processing)
        start_layout.addWidget(self.mj_start_btn)
        
        start_layout.addStretch()
        mj_layout.addLayout(start_layout)

        # 操作按钮区域（初始隐藏）
        self.mj_actions_widget = QWidget()
        actions_layout = QVBoxLayout(self.mj_actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        # 放大按钮行
        upscale_layout = QHBoxLayout()
        upscale_layout.addWidget(QLabel("放大:"))
        self.mj_u_btns = []
        for i in range(1, 5):
            btn = QPushButton(f"U{i}")
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked, idx=i: self._on_mj_action_clicked(f"U{idx}"))
            upscale_layout.addWidget(btn)
            self.mj_u_btns.append(btn)
        upscale_layout.addStretch()
        actions_layout.addLayout(upscale_layout)

        # 变换按钮行
        variation_layout = QHBoxLayout()
        variation_layout.addWidget(QLabel("变换:"))
        self.mj_v_btns = []
        for i in range(1, 5):
            btn = QPushButton(f"V{i}")
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked, idx=i: self._on_mj_action_clicked(f"V{idx}"))
            variation_layout.addWidget(btn)
            self.mj_v_btns.append(btn)
        variation_layout.addStretch()
        actions_layout.addLayout(variation_layout)

        # 重绘按钮
        other_layout = QHBoxLayout()
        other_layout.addWidget(QLabel("其他:"))
        self.mj_reroll_btn = QPushButton("🔄 重绘")
        self.mj_reroll_btn.setEnabled(False)
        self.mj_reroll_btn.clicked.connect(lambda: self._on_mj_action_clicked("reroll"))
        other_layout.addWidget(self.mj_reroll_btn)
        other_layout.addStretch()
        actions_layout.addLayout(other_layout)

        self.mj_actions_widget.setVisible(False)
        mj_layout.addWidget(self.mj_actions_widget)

        mj_group.setLayout(mj_layout)
        parent_layout.addWidget(mj_group)

    def _start_mj_processing(self):
        """开始 MJ 处理"""
        from core.app import get_app_state
        
        app_state = get_app_state()
        api_key = app_state.config.api_key
        base_url = app_state.config.base_url
        
        if not api_key:
            QMessageBox.warning(self, "错误", "请先设置 API Key")
            return
        
        self.mj_start_btn.setEnabled(False)
        self.mj_progress.setFormat("正在处理...")
        self.mj_progress.setValue(10)
        self.mj_status_label.setText("正在上传图片并提交 Imagine 任务...")
        
        # 启动工作线程
        self.mj_worker = MJProcessingThread(
            api_key=api_key,
            base_url=base_url,
            image_path=self.path
        )
        self.mj_worker.progress.connect(self._on_mj_progress)
        self.mj_worker.task_ready.connect(self._on_mj_task_ready)
        self.mj_worker.error.connect(self._on_mj_error)
        self.mj_worker.start()

    def _on_mj_progress(self, progress: str, status: str):
        """MJ 进度更新"""
        try:
            pct = int(progress.replace("%", ""))
            self.mj_progress.setValue(pct)
        except:
            pass
        self.mj_progress.setFormat(f"{status}: {progress}")
        self.mj_status_label.setText(f"状态: {status}")

    def _on_mj_task_ready(self, task_id: str, image_url: str, buttons: list):
        """MJ 任务完成"""
        self.mj_task_id = task_id
        self.mj_buttons = buttons
        
        self.mj_progress.setValue(100)
        self.mj_progress.setFormat("完成")
        self.mj_status_label.setText(f"任务 ID: {task_id[:20]}...")
        
        # 更新预览图片
        self._load_image_from_url(image_url)
        
        # 显示操作按钮
        self.mj_actions_widget.setVisible(True)
        self._update_mj_buttons(buttons)
        
        self.mj_start_btn.setText("🔄 重新处理")
        self.mj_start_btn.setEnabled(True)

    def _on_mj_error(self, error: str):
        """MJ 错误"""
        self.mj_progress.setValue(0)
        self.mj_progress.setFormat("失败")
        self.mj_status_label.setText(f"错误: {error}")
        self.mj_start_btn.setEnabled(True)
        QMessageBox.warning(self, "MJ 处理失败", error)

    def _update_mj_buttons(self, buttons: list):
        """更新 MJ 操作按钮状态"""
        # 禁用所有按钮
        for btn in self.mj_u_btns + self.mj_v_btns:
            btn.setEnabled(False)
        self.mj_reroll_btn.setEnabled(False)
        
        # 根据返回的按钮启用对应的 UI
        for mj_btn in buttons:
            label = mj_btn.get("label", "") if isinstance(mj_btn, dict) else mj_btn.label
            emoji = mj_btn.get("emoji", "") if isinstance(mj_btn, dict) else mj_btn.emoji
            
            if label.startswith("U") and len(label) == 2:
                idx = int(label[1]) - 1
                if 0 <= idx < 4:
                    self.mj_u_btns[idx].setEnabled(True)
            elif label.startswith("V") and len(label) == 2:
                idx = int(label[1]) - 1
                if 0 <= idx < 4:
                    self.mj_v_btns[idx].setEnabled(True)
            elif emoji == "🔄" or "reroll" in (mj_btn.get("customId", "") if isinstance(mj_btn, dict) else mj_btn.custom_id).lower():
                self.mj_reroll_btn.setEnabled(True)

    def _on_mj_action_clicked(self, action_label: str):
        """点击 MJ 操作按钮"""
        if not self.mj_task_id or not self.mj_buttons:
            return
        
        # 找到对应的 custom_id
        custom_id = None
        for mj_btn in self.mj_buttons:
            label = mj_btn.get("label", "") if isinstance(mj_btn, dict) else mj_btn.label
            emoji = mj_btn.get("emoji", "") if isinstance(mj_btn, dict) else mj_btn.emoji
            btn_custom_id = mj_btn.get("customId", "") if isinstance(mj_btn, dict) else mj_btn.custom_id
            
            if action_label == "reroll" and (emoji == "🔄" or "reroll" in btn_custom_id.lower()):
                custom_id = btn_custom_id
                break
            elif label == action_label:
                custom_id = btn_custom_id
                break
        
        if not custom_id:
            QMessageBox.warning(self, "错误", f"找不到操作: {action_label}")
            return
        
        # 执行 Action
        from core.app import get_app_state
        app_state = get_app_state()
        api_key = app_state.config.api_key
        base_url = app_state.config.base_url
        
        self.mj_progress.setValue(10)
        self.mj_progress.setFormat(f"执行 {action_label}...")
        self.mj_status_label.setText(f"正在执行 {action_label} 操作...")
        
        # 禁用按钮
        for btn in self.mj_u_btns + self.mj_v_btns:
            btn.setEnabled(False)
        self.mj_reroll_btn.setEnabled(False)
        
        # 启动 Action 线程
        self.mj_worker = MJActionThread(
            api_key=api_key,
            base_url=base_url,
            task_id=self.mj_task_id,
            custom_id=custom_id
        )
        self.mj_worker.progress.connect(self._on_mj_progress)
        self.mj_worker.task_ready.connect(self._on_mj_task_ready)
        self.mj_worker.error.connect(self._on_mj_error)
        self.mj_worker.start()

    def _load_image_from_url(self, url: str):
        """从 URL 加载图片"""
        try:
            import requests
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            from PySide6.QtGui import QImage
            image = QImage()
            image.loadFromData(response.content)
            pixmap = QPixmap.fromImage(image)
            self.image_label.setPixmap(pixmap)
        except Exception as e:
            print(f"加载图片失败: {e}")

    def _edit_and_regenerate(self):
        """修改提示词并重新生成"""
        key = (self.verse_index, self.prompt_index)
        current_prompt = ""
        if key in self.generated_images:
            current_prompt = self.generated_images[key].get('description', '')

        # 使用自定义对话框（支持多行编辑）
        from PySide6.QtWidgets import QTextEdit, QDialogButtonBox, QVBoxLayout, QLabel, QDialog
        
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle("修改图像提示词")
        edit_dialog.setMinimumSize(600, 300)
        
        layout = QVBoxLayout(edit_dialog)
        
        # 说明
        hint_label = QLabel("请编辑图像提示词（英文），详细描述画面元素：")
        layout.addWidget(hint_label)
        
        # 多行文本编辑器
        text_edit = QTextEdit()
        text_edit.setPlainText(current_prompt)
        text_edit.setPlaceholderText("A traditional Chinese ink painting depicting...")
        layout.addWidget(text_edit)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(edit_dialog.accept)
        buttons.rejected.connect(edit_dialog.reject)
        layout.addWidget(buttons)
        
        if edit_dialog.exec() == QDialog.Accepted:
            new_prompt = text_edit.toPlainText().strip()
            if new_prompt:
                # 更新提示词
                if self.prompts:
                    verse = self.prompts.get_verse(self.verse_index)
                    if verse and 0 <= self.prompt_index < len(verse.descriptions):
                        verse.descriptions[self.prompt_index].description = new_prompt

                self.preview_regenerated.emit(self.verse_index, self.prompt_index, new_prompt)
                self.accept()

    def _generate_video(self):
        """生成视频"""
        self.accept()
        # 切换到视频队列页面
        main_window = self.parent().parent().parent().parent()
        if hasattr(main_window, 'video_page'):
            key = (self.verse_index, self.prompt_index)
            video_prompt = ""
            if key in self.generated_images:
                video_prompt = self.generated_images[key].get('video_prompt', '')

            main_window.video_page.set_images_with_prompts([(self.path, video_prompt)])
            main_window.tab_widget.setCurrentIndex(3)


class MJProcessingThread(QThread):
    """MJ 处理线程（上传 + Imagine + 等待）"""
    progress = Signal(str, str)  # progress, status
    task_ready = Signal(str, str, list)  # task_id, image_url, buttons
    error = Signal(str)
    
    def __init__(self, api_key: str, base_url: str, image_path: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.image_path = image_path
    
    def run(self):
        try:
            from api.mj_client import MidjourneyClient
            
            with MidjourneyClient(self.api_key, self.base_url) as client:
                # 上传图片
                self.progress.emit("10%", "上传图片")
                image_url = client.upload_image(Path(self.image_path))
                
                # 提交 Imagine（使用图片作为垫图）
                self.progress.emit("20%", "提交任务")
                task_id = client.submit_imagine(
                    prompt=image_url,  # 以图片 URL 作为垫图
                    ref_images=None
                )
                
                # 等待完成
                def on_progress(progress, status):
                    self.progress.emit(progress, status)
                
                result = client.wait_for_completion(
                    task_id,
                    timeout=600,
                    poll_interval=5,
                    progress_callback=on_progress
                )
                
                # 转换 buttons 为 dict 列表
                buttons = []
                for btn in result.buttons:
                    buttons.append({
                        "customId": btn.custom_id,
                        "label": btn.label,
                        "emoji": btn.emoji
                    })
                
                self.task_ready.emit(result.task_id, result.image_url, buttons)
                
        except Exception as e:
            self.error.emit(str(e))


class MJActionThread(QThread):
    """MJ Action 执行线程"""
    progress = Signal(str, str)  # progress, status
    task_ready = Signal(str, str, list)  # task_id, image_url, buttons
    error = Signal(str)
    
    def __init__(self, api_key: str, base_url: str, task_id: str, custom_id: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.task_id = task_id
        self.custom_id = custom_id
    
    def run(self):
        try:
            from api.mj_client import MidjourneyClient
            
            with MidjourneyClient(self.api_key, self.base_url) as client:
                # 提交 Action
                self.progress.emit("10%", "提交操作")
                new_task_id = client.submit_action(self.task_id, self.custom_id)
                
                # 等待完成
                def on_progress(progress, status):
                    self.progress.emit(progress, status)
                
                result = client.wait_for_completion(
                    new_task_id,
                    timeout=600,
                    poll_interval=5,
                    progress_callback=on_progress
                )
                
                # 转换 buttons 为 dict 列表
                buttons = []
                for btn in result.buttons:
                    buttons.append({
                        "customId": btn.custom_id,
                        "label": btn.label,
                        "emoji": btn.emoji
                    })
                
                self.task_ready.emit(result.task_id, result.image_url, buttons)
                
        except Exception as e:
            self.error.emit(str(e))




class ImageGenerationThread(QThread):
    """图像生成线程"""

    progress = Signal(int, int)
    image_ready = Signal(int, int, object, str, str)  # verse_index, prompt_index, path, video_prompt, description
    finished = Signal()
    failed = Signal(int, int, str)  # verse_index, prompt_index, error

    def __init__(self, app_state, tasks: List[tuple], prompts: Optional[PoetryPromptsResponse], session_id: str):
        super().__init__()
        self.app_state = app_state
        self.tasks = tasks  # [(verse_index, prompt_index, description, video_prompt), ...]
        self.prompts = prompts
        self.session_id = session_id
        self._stopped = False

    def stop(self):
        """停止生成"""
        self._stopped = True

    def run(self):
        """运行生成任务"""
        total = len(self.tasks)
        client = self.app_state.llm_client
        import time

        for i, task in enumerate(self.tasks):
            if self._stopped:
                break

            # 兼容旧格式（3项）和新格式（4项）
            if len(task) >= 4:
                verse_index, prompt_index, description, video_prompt = task[0], task[1], task[2], task[3]
            else:
                verse_index, prompt_index, description = task
                video_prompt = ""

            try:
                # 创建文件名
                timestamp = __import__('time').strftime("%Y%m%d_%H%M%S")
                filename = f"verse_{verse_index}_prompt_{prompt_index}_{timestamp}.png"
                save_path = Path(self.app_state.file_manager.get_session_dir(self.session_id)) / "images" / filename

                # 生成图像
                result_path = client.generate_image(
                    description,
                    save_path=save_path
                )

                self.image_ready.emit(verse_index, prompt_index, result_path, video_prompt, description)

            except Exception as e:
                self.failed.emit(verse_index, prompt_index, str(e))

            self.progress.emit(i + 1, total)

            # 添加延迟避免速率限制
            if i < total - 1:
                time.sleep(3)

        self.finished.emit()
