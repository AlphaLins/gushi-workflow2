"""
主窗口
包含所有页面组件的主界面
"""
from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QToolBar, QMenuBar,
    QMenu, QMessageBox, QFileDialog, QStyle
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QKeySequence

from core.app import get_app_state, AppState
from components.settings_panel import SettingsPanel
from components.poetry_input_page import PoetryInputPage
from components.prompt_editor_page import PromptEditorPage
from components.image_gallery_page import ImageGalleryPage
from components.video_queue_page import VideoQueuePage
from components.music_generation_page import MusicGenerationPage


class MainWindow(QMainWindow):
    """
    主窗口类

    功能：
    1. 多标签页管理
    2. 菜单栏和工具栏
    3. 状态栏
    4. 页面间通信
    """

    def __init__(self):
        super().__init__()

        self.app_state = get_app_state()

        # 连接信号
        self._connect_signals()

        # 初始化 UI
        self._init_ui()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()

        # 创建初始会话
        self.app_state.create_session()

    def _connect_signals(self):
        """连接应用状态信号"""
        self.app_state.config_changed.connect(self._on_config_changed)
        self.app_state.session_changed.connect(self._on_session_changed)

    def _connect_page_signals(self):
        """连接页面间信号，实现数据流转"""
        # 诗词输入 -> 提示词编辑 + 图像生成
        self.poetry_page.prompts_generated.connect(self._on_prompts_generated)

        # 提示词编辑 -> 图像生成
        self.prompt_page.prompts_changed.connect(self.image_page.set_prompts)
        
        # 提示词编辑 -> 音乐生成（传递音乐提示词）
        self.prompt_page.music_transfer_requested.connect(self._on_music_transfer)

        # 图像生成 -> 视频队列
        self.image_page.images_generated.connect(self._on_images_generated)

        # 图像画廊 -> 视频队列（用户主动选择生成视频）
        self.image_page.generate_video_requested.connect(self._on_generate_video_requested)

    @Slot(object)
    def _on_prompts_generated(self, prompts):
        """提示词生成完成"""
        self.prompt_page.set_prompts(prompts)
        self.tab_widget.setCurrentIndex(1)  # 切换到提示词编辑页
        self.statusBar().showMessage("提示词已生成，请编辑确认", 3000)

    @Slot(object)
    def _on_prompts_changed(self, prompts):
        """提示词更新，同步到图像生成页面"""
        self.image_page.set_prompts(prompts)

    @Slot(list)
    def _on_images_generated(self, image_data):
        """图像生成完成，传递到视频队列 - image_data 为 [(path, video_prompt), ...]"""
        self.video_page.set_images_with_prompts(image_data)
        self.statusBar().showMessage(f"已生成 {len(image_data)} 张图片，可进入视频队列", 3000)

    @Slot(list)
    def _on_generate_video_requested(self, image_data):
        """从图像画廊发起的视频生成请求 - image_data 为 [(path, video_prompt), ...]"""
        self.video_page.set_images_with_prompts(image_data)
        self.tab_widget.setCurrentIndex(3)  # 切换到视频队列页面
        self.statusBar().showMessage(f"已加载 {len(image_data)} 张图片到视频队列", 3000)

    @Slot(object)
    def _on_music_transfer(self, music_prompt):
        """从提示词编辑页面发起的音乐提示词传递"""
        self.music_page.set_music_prompt(music_prompt)
        self.tab_widget.setCurrentIndex(4)  # 切换到音乐生成页面
        self.statusBar().showMessage("音乐提示词已传递到音乐生成页面", 3000)

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("诗韵画境 - Poetry to Image")
        self.setMinimumSize(1200, 800)

        # 创建主容器（水平布局：侧边栏 + 标签页）
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 历史记录侧边栏
        from components.history_sidebar import HistorySidebar
        self.history_sidebar = HistorySidebar()
        self.history_sidebar.setMaximumWidth(300)
        self.history_sidebar.setMinimumWidth(250)
        self.history_sidebar.session_selected.connect(self._on_session_restored)
        main_layout.addWidget(self.history_sidebar)

        # 标签页容器
        tab_container = QWidget()
        tab_layout = QVBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # 添加各个页面（不传参数，页面内部会调用 get_app_state()）
        self.poetry_page = PoetryInputPage()
        self.tab_widget.addTab(self.poetry_page, "诗词输入")

        self.prompt_page = PromptEditorPage()
        self.tab_widget.addTab(self.prompt_page, "提示词编辑")

        self.image_page = ImageGalleryPage()
        self.tab_widget.addTab(self.image_page, "图像生成")

        self.video_page = VideoQueuePage()
        self.tab_widget.addTab(self.video_page, "视频队列")

        self.music_page = MusicGenerationPage()
        self.tab_widget.addTab(self.music_page, "音乐生成")

        self.settings_panel = SettingsPanel()
        self.tab_widget.addTab(self.settings_panel, "设置")

        # 连接页面信号
        self._connect_page_signals()

        tab_layout.addWidget(self.tab_widget)
        main_layout.addWidget(tab_container, stretch=1)
        
        # 设置中心部件
        self.setCentralWidget(main_container)

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        # 新建会话
        new_session_action = QAction("新建会话(&N)", self)
        new_session_action.setShortcut(QKeySequence.New)
        new_session_action.triggered.connect(self._new_session)
        file_menu.addAction(new_session_action)

        # 打开会话
        open_session_action = QAction("打开会话(&O)...", self)
        open_session_action.setShortcut(QKeySequence.Open)
        open_session_action.triggered.connect(self._open_session)
        file_menu.addAction(open_session_action)
        
        # 保存项目
        save_action = QAction("保存项目(&S)", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # 导出
        export_action = QAction("导出(&E)...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_session)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        # 主题切换（添加快捷键 Ctrl+T）
        self.theme_action = QAction("🌙 切换到暗黑模式", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+T"))
        self.theme_action.setStatusTip("切换应用主题 (明亮/暗黑/黏土)")
        self.theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.theme_action)
        
        view_menu.addSeparator()

        # 跳转到各个页面
        goto_poetry_action = QAction("诗词输入(&P)", self)
        goto_poetry_action.setShortcut(QKeySequence("Ctrl+1"))
        goto_poetry_action.triggered.connect(lambda: self._go_to_tab(0))
        view_menu.addAction(goto_poetry_action)

        goto_prompt_action = QAction("提示词编辑(&R)", self)
        goto_prompt_action.setShortcut(QKeySequence("Ctrl+2"))
        goto_prompt_action.triggered.connect(lambda: self._go_to_tab(1))
        view_menu.addAction(goto_prompt_action)

        goto_image_action = QAction("图像生成(&I)", self)
        goto_image_action.setShortcut(QKeySequence("Ctrl+3"))
        goto_image_action.triggered.connect(lambda: self._go_to_tab(2))
        view_menu.addAction(goto_image_action)

        goto_video_action = QAction("视频队列(&V)", self)
        goto_video_action.setShortcut(QKeySequence("Ctrl+4"))
        goto_video_action.triggered.connect(lambda: self._go_to_tab(3))
        view_menu.addAction(goto_video_action)

        goto_music_action = QAction("音乐生成(&M)", self)
        goto_music_action.setShortcut(QKeySequence("Ctrl+5"))
        goto_music_action.triggered.connect(lambda: self._go_to_tab(4))
        view_menu.addAction(goto_music_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 新建会话
        new_action = QAction("新建会话", self)
        new_action.triggered.connect(self._new_session)
        toolbar.addAction(new_action)
        
        # 保存项目
        save_action = QAction("保存项目", self)
        save_action.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        save_action.triggered.connect(self._save_project)
        toolbar.addAction(save_action)

        # 导出
        export_action = QAction("导出", self)
        export_action.triggered.connect(self._export_session)
        toolbar.addAction(export_action)

        toolbar.addSeparator()

        # 主题切换按钮
        self.theme_toolbar_action = QAction("🎨 主题", self)
        self.theme_toolbar_action.setStatusTip("切换应用主题 (Ctrl+T)")
        self.theme_toolbar_action.triggered.connect(self._toggle_theme)
        toolbar.addAction(self.theme_toolbar_action)

        toolbar.addSeparator()

        # 设置
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(lambda: self._go_to_tab(5))
        toolbar.addAction(settings_action)

    def _create_status_bar(self):
        """创建状态栏"""
        # 创建状态栏
        self.setStatusBar(QStatusBar()) # Ensure a status bar is set
        statusBar = self.statusBar()
        statusBar.showMessage("就绪", 3000)

    # ==================== 信号处理 ====================

    @Slot()
    def _on_config_changed(self):
        """配置变更处理"""
        if self.statusBar():
            self.statusBar().showMessage("配置已更新", 3000)

    @Slot()
    def _on_session_changed(self):
        """会话变更处理"""
        session_id = self.app_state.current_session_id
        self.statusBar().showMessage(f"当前会话: {session_id}", 3000)

    @Slot(int)
    def _on_tab_changed(self, index: int):
        """标签页切换处理"""
        tab_name = self.tab_widget.tabText(index)
        self.statusBar().showMessage(f"切换到: {tab_name}", 2000)

        # 切换到图像生成页面时，传递提示词数据
        if index == 2:  # 图像生成页面
            prompts = self.prompt_page.get_prompts()
            if prompts:
                self.image_page.set_prompts(prompts)
                self.statusBar().showMessage(f"已加载 {prompts.total_prompts()} 个提示词", 2000)

        # 切换到视频队列页面时，传递图像数据
        if index == 3:  # 视频队列页面
            images = list(self.image_page.generated_images.values())
            images = [img for img in images if img]  # 过滤 None 值
            if images:
                # 转换为 (path, video_prompt) 格式
                image_data = [(img.get('path', ''), img.get('video_prompt', '')) for img in images]
                self.video_page.set_images_with_prompts(image_data)
                self.statusBar().showMessage(f"已加载 {len(images)} 张图片", 2000)

    # ==================== 菜单操作 ====================

    def _new_session(self):
        """创建新会话"""
        session_id = self.app_state.create_session()
        QMessageBox.information(self, "新会话", f"已创建新会话: {session_id}")
    
    def _open_session(self):
        """打开会话（通过历史侧边栏）"""
        QMessageBox.information(
            self, 
            "提示", 
            "请在左侧历史记录面板中选择要打开的会话"
        )
    
    def _on_session_restored(self, session_id: str):
        """恢复历史会话"""
        from database.manager import HistoryManager
        
        try:
            history_manager = HistoryManager()
            session = history_manager.get_session(session_id)
            
            if not session:
                QMessageBox.warning(self, "错误", "会话不存在")
                return
            
            # 显示会话信息（完整恢复功能需要更多开发）
            reply = QMessageBox.question(
                self,
                "恢复会话",
                f"会话: {session.name or session_id[:8]}\n"
                f"创建时间: {session.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"诗词内容: {session.poetry_text[:100]}...\n\n"
                f"是否打开此会话？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # TODO: 完整恢复逻辑
                # 1. 设置当前会话ID
                self.app_state._current_session_id = session_id
                
                # 2. 在诗词页面恢复文本
                # self.poetry_page.set_poetry_text(session.poetry_text)
                
                self.statusBar().showMessage(f"已打开会话: {session.name or session_id[:8]}", 5000)
            
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", f"错误: {str(e)}")

        except Exception as e:
            QMessageBox.warning(self, "恢复失败", f"错误: {str(e)}")

    def _save_project(self):
        """保存当前项目"""
        if not self.app_state.current_session_id:
            # 如果没有会话，先创建
            self.app_state.create_session()
            
        try:
            from database.manager import HistoryManager
            history_manager = HistoryManager()
            
            # 1. 保存诗词文本
            poetry_text = self.poetry_page.get_poetry_text()
            # 尝试从诗词中提取标题作为名称
            name = None
            if poetry_text:
                lines = poetry_text.strip().split('\n')
                if lines:
                    name = lines[0][:20]  # 取第一行前20字
            
            history_manager.update_session(
                self.app_state.current_session_id,
                name=name,
                poetry_text=poetry_text
            )
            
            # 2. 保存提示词
            prompts = self.prompt_page.get_prompts()
            if prompts:
                prompt_data = []
                for verse in prompts.verses:
                    for i, p in enumerate(verse.prompts):
                        prompt_data.append({
                            'verse_index': verse.index,
                            'prompt_index': i,
                            'image_prompt': p.image_prompt,
                            'video_prompt': p.video_prompt
                        })
                history_manager.save_prompts(self.app_state.current_session_id, prompt_data)
            
            self.statusBar().showMessage(f"项目已保存: {self.app_state.current_session_id}", 3000)
            
            # 简短提示
            # QMessageBox.information(self, "保存成功", "项目已保存到数据库")
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存项目: {str(e)}")

    def _export_session(self):
        """导出当前会话"""
        from utils.project_exporter import ProjectExporter
        from database.manager import HistoryManager
        from PySide6.QtWidgets import QFileDialog
        from pathlib import Path
        
        if not self.app_state.current_session_id:
            QMessageBox.warning(self, "提示", "请先创建会话")
            return
        
        # 获取保存路径
        default_name = f"poetry_project_{self.app_state.current_session_id[:8]}.zip"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出项目",
            default_name,
            "ZIP 文件 (*.zip)"
        )
        
        if file_path:
            try:
                history_manager = HistoryManager()
                exporter = ProjectExporter(history_manager)
                
                # 导出为 ZIP
                output_path = exporter.export_as_zip(
                    self.app_state.current_session_id,
                    Path(file_path)
                )
                
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"项目已导出到:\n{output_path}\n\n包含诗词、提示词、图片和视频"
                )
                self.statusBar().showMessage(f"项目已导出: {output_path.name}", 5000)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "导出失败",
                    f"导出失败: {str(e)}"
                )

    def _go_to_tab(self, index: int):
        """跳转到指定标签页"""
        self.tab_widget.setCurrentIndex(index)
    
    def _toggle_theme(self):
        """切换主题 (modern -> dark -> clay -> modern)"""
        from pathlib import Path
        import sys

        # 获取当前主题
        current_theme = getattr(self, '_current_theme', 'modern')

        # 循环切换主题: modern -> dark -> clay -> modern
        theme_order = ['modern', 'dark', 'clay']
        try:
            current_index = theme_order.index(current_theme)
            new_theme = theme_order[(current_index + 1) % len(theme_order)]
        except ValueError:
            new_theme = 'clay'

        # 加载新主题
        root_dir = Path(sys.argv[0]).parent if hasattr(sys, 'argv') else Path.cwd()
        style_path = root_dir / "resources" / "styles" / f"{new_theme}.qss"

        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                qss = f.read()
                self.app_state.app.setStyleSheet(qss)
                self._current_theme = new_theme

                # 更新菜单文本
                theme_names = {
                    'modern': "🌙 切换到暗黑模式",
                    'dark': "🎨 切换到黏土风格",
                    'clay': "☀️ 切换到明亮模式"
                }
                self.theme_action.setText(theme_names.get(new_theme, "切换主题"))

                # 显示状态消息
                display_names = {
                    'modern': "明亮",
                    'dark': "暗黑",
                    'clay': "黏土"
                }
                self.statusBar().showMessage(f"已切换到{display_names.get(new_theme, new_theme)}模式", 3000)
        else:
            QMessageBox.warning(self, "错误", f"主题文件不存在: {style_path}")

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于诗韵画境",
            "<h3>诗韵画境 (Poetry to Image)</h3>"
            "<p>将中国古典诗词转化为图像、视频和音乐的 AI 创作平台</p>"
            "<p>版本: 1.0.0</p>"
            "<p>使用 PySide6 构建</p>"
        )

    # ==================== 公共接口 ====================

    def get_poetry_page(self) -> PoetryInputPage:
        """获取诗词输入页面"""
        return self.poetry_page

    def get_prompt_page(self) -> PromptEditorPage:
        """获取提示词编辑页面"""
        return self.prompt_page

    def get_image_page(self) -> ImageGalleryPage:
        """获取图像生成页面"""
        return self.image_page

    def get_video_page(self) -> VideoQueuePage:
        """获取视频队列页面"""
        return self.video_page

    def get_music_page(self) -> MusicGenerationPage:
        """获取音乐生成页面"""
        return self.music_page

    def show_status_message(self, message: str, timeout: int = 3000):
        """显示状态栏消息"""
        self.status_bar.showMessage(message, timeout)

    def closeEvent(self, event):
        """关闭事件处理"""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 停止页面线程
            if hasattr(self.image_page, 'cleanup'):
                self.image_page.cleanup()
            if hasattr(self.video_page, 'cleanup'):
                self.video_page.cleanup()

            # 清理资源
            if self.app_state._llm_client:
                self.app_state._llm_client.close()
            if self.app_state._video_client:
                self.app_state._video_client.close()
            if self.app_state._music_client:
                self.app_state._music_client.close()

            event.accept()
        else:
            event.ignore()
