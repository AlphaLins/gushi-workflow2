"""
主窗口
包含所有页面组件的主界面
"""
from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QToolBar, QMenuBar,
    QMenu, QMessageBox, QFileDialog
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

        # 图像生成 -> 视频队列
        self.image_page.images_generated.connect(self._on_images_generated)

        # 图像画廊 -> 视频队列（用户主动选择生成视频）
        self.image_page.generate_video_requested.connect(self._on_generate_video_requested)

    @Slot(object)
    def _on_prompts_generated(self, prompts):
        """提示词生成完成，传递到编辑页面和图像页面"""
        self.prompt_page.set_prompts(prompts)
        self.image_page.set_prompts(prompts)
        self.tab_widget.setCurrentIndex(1)  # 切换到提示词编辑
        self.status_bar.showMessage("提示词已生成，请编辑确认", 3000)

    @Slot(object)
    def _on_prompts_changed(self, prompts):
        """提示词更新，同步到图像生成页面"""
        self.image_page.set_prompts(prompts)

    @Slot(list)
    def _on_images_generated(self, image_data):
        """图像生成完成，传递到视频队列 - image_data 为 [(path, video_prompt), ...]"""
        self.video_page.set_images_with_prompts(image_data)
        self.status_bar.showMessage(f"已生成 {len(image_data)} 张图片，可进入视频队列", 3000)

    @Slot(list)
    def _on_generate_video_requested(self, image_data):
        """从图像画廊发起的视频生成请求 - image_data 为 [(path, video_prompt), ...]"""
        self.video_page.set_images_with_prompts(image_data)
        self.tab_widget.setCurrentIndex(3)  # 切换到视频队列页面
        self.status_bar.showMessage(f"已加载 {len(image_data)} 张图片到视频队列", 3000)

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("诗韵画境 - Poetry to Image")
        self.setMinimumSize(1200, 800)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)

        # 创建各个页面
        self.poetry_page = PoetryInputPage()
        self.prompt_page = PromptEditorPage()
        self.image_page = ImageGalleryPage()
        self.video_page = VideoQueuePage()
        self.music_page = MusicGenerationPage()
        self.settings_page = SettingsPanel()

        # 添加页面到标签页
        self.tab_widget.addTab(self.poetry_page, "诗词输入")
        self.tab_widget.addTab(self.prompt_page, "提示词编辑")
        self.tab_widget.addTab(self.image_page, "图像生成")
        self.tab_widget.addTab(self.video_page, "视频队列")
        self.tab_widget.addTab(self.music_page, "音乐生成")
        self.tab_widget.addTab(self.settings_page, "设置")

        # 连接页面切换信号
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # 连接页面间信号，实现数据流转
        self._connect_page_signals()

        main_layout.addWidget(self.tab_widget)

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

        # 导出
        export_action = QAction("导出", self)
        export_action.triggered.connect(self._export_session)
        toolbar.addAction(export_action)

        toolbar.addSeparator()

        # 设置
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(lambda: self._go_to_tab(5))
        toolbar.addAction(settings_action)

    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    # ==================== 信号处理 ====================

    @Slot()
    def _on_config_changed(self):
        """配置变更处理"""
        self.status_bar.showMessage("配置已更新", 3000)

    @Slot()
    def _on_session_changed(self):
        """会话变更处理"""
        session_id = self.app_state.current_session_id
        self.status_bar.showMessage(f"当前会话: {session_id}", 3000)

    @Slot(int)
    def _on_tab_changed(self, index: int):
        """标签页切换处理"""
        tab_name = self.tab_widget.tabText(index)
        self.status_bar.showMessage(f"切换到: {tab_name}", 2000)

        # 切换到图像生成页面时，传递提示词数据
        if index == 2:  # 图像生成页面
            prompts = self.prompt_page.get_prompts()
            if prompts:
                self.image_page.set_prompts(prompts)
                self.status_bar.showMessage(f"已加载 {prompts.total_prompts()} 个提示词", 2000)

        # 切换到视频队列页面时，传递图像数据
        if index == 3:  # 视频队列页面
            images = list(self.image_page.generated_images.values())
            images = [img for img in images if img]  # 过滤 None 值
            if images:
                # 转换为 (path, video_prompt) 格式
                image_data = [(img.get('path', ''), img.get('video_prompt', '')) for img in images]
                self.video_page.set_images_with_prompts(image_data)
                self.status_bar.showMessage(f"已加载 {len(images)} 张图片", 2000)

    # ==================== 菜单操作 ====================

    def _new_session(self):
        """新建会话"""
        session_id = self.app_state.create_session()
        QMessageBox.information(self, "新会话", f"已创建新会话: {session_id}")

    def _open_session(self):
        """打开会话"""
        # TODO: 实现会话选择对话框
        QMessageBox.information(self, "打开会话", "此功能将在后续版本实现")

    def _export_session(self):
        """导出会话"""
        session_id = self.app_state.current_session_id
        if not session_id:
            QMessageBox.warning(self, "导出失败", "没有活动会话")
            return

        # 选择导出位置
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出会话",
            f"{session_id}.zip",
            "ZIP 文件 (*.zip)"
        )

        if file_path:
            try:
                export_path = self.app_state.file_manager.export_session(
                    session_id,
                    Path(file_path)
                )
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"会话已导出到: {export_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "导出失败",
                    f"导出失败: {str(e)}"
                )

    def _go_to_tab(self, index: int):
        """跳转到指定标签页"""
        self.tab_widget.setCurrentIndex(index)

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
