"""
应用程序核心类
全局状态管理和应用程序入口
"""
from typing import Optional
from pathlib import Path
from PySide6.QtCore import QObject, Signal

from config.api_config import APIConfig
from api.client import UnifiedClient
from api.video_client import VideoClient
from api.suno_client import SunoClient
from api.image_uploader import ImageUploader
from utils.file_manager import FileManager
from utils.logger import get_logger


class AppState(QObject):
    """
    应用程序全局状态

    遵循单一职责原则：仅管理状态，不处理 UI 逻辑
    """

    # 信号定义
    config_changed = Signal()
    client_changed = Signal()
    session_changed = Signal()

    def __init__(self):
        super().__init__()

        # API 配置
        # 优先查找程序目录下的 config.json
        local_config = Path.cwd() / 'config.json'
        if local_config.exists():
            self._config_path = local_config
        else:
            self._config_path = Path.home() / '.guui_config.json'

        self._config: APIConfig = APIConfig.load(self._config_path)

        # API 客户端（延迟初始化）
        self._llm_client: Optional[UnifiedClient] = None
        self._video_client: Optional[VideoClient] = None
        self._music_client: Optional[SunoClient] = None
        self._image_uploader: Optional[ImageUploader] = None

        # 文件管理器
        self._file_manager = FileManager(Path.cwd())

        # 当前会话
        self._current_session_id: Optional[str] = None

        # 日志器
        self._logger = get_logger()
        
        # QApplication 实例
        self._app: Optional['QApplication'] = None

    # ==================== 配置管理 ====================

    @property
    def config(self) -> APIConfig:
        """获取配置"""
        return self._config

    def update_config(self, **kwargs) -> None:
        """
        更新配置

        Args:
            **kwargs: 配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

        # 保存配置
        self._config.save(self._config_path)

        # 重置客户端（下次使用时重新创建）
        self._reset_clients()

        self.config_changed.emit()
        self._logger.info(f"配置已更新: {', '.join(kwargs.keys())}")

    def _reset_clients(self) -> None:
        """重置所有客户端"""
        self._llm_client = None
        self._video_client = None
        self._music_client = None
        self._image_uploader = None
        self.client_changed.emit()

    # ==================== API 客户端 ====================

    @property
    def llm_client(self) -> UnifiedClient:
        """获取 LLM 客户端（延迟初始化）"""
        if self._llm_client is None:
            self._llm_client = UnifiedClient(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                model=self._config.model,
                image_model=self._config.image_model,
                use_native_google=self._config.use_native_google,
                max_retries=self._config.max_retries,
                timeout=self._config.timeout,
                temperature=self._config.temperature,
                top_p=self._config.top_p,
            )
        return self._llm_client

    @property
    def video_client(self) -> VideoClient:
        """获取视频客户端（延迟初始化）"""
        if self._video_client is None:
            self._video_client = VideoClient(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=self._config.timeout,
            )
        return self._video_client

    @property
    def music_client(self) -> SunoClient:
        """获取音乐客户端（延迟初始化）"""
        if self._music_client is None:
            self._music_client = SunoClient(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=self._config.timeout,
            )
        return self._music_client

    @property
    def image_uploader(self) -> ImageUploader:
        """获取图片上传器（延迟初始化）"""
        if self._image_uploader is None:
            self._image_uploader = ImageUploader(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
            )
        return self._image_uploader

    # ==================== 文件管理 ====================

    @property
    def file_manager(self) -> FileManager:
        """获取文件管理器"""
        return self._file_manager

    # ==================== 会话管理 ====================

    @property
    def current_session_id(self) -> Optional[str]:
        """获取当前会话 ID"""
        return self._current_session_id

    def create_session(self) -> str:
        """创建新会话"""
        self._current_session_id = self._file_manager.create_session()
        self.session_changed.emit()
        self._logger.info(f"创建新会话: {self._current_session_id}")
        return self._current_session_id

    def set_session(self, session_id: str) -> None:
        """设置当前会话"""
        self._current_session_id = session_id
        self.session_changed.emit()
        self._logger.info(f"切换会话: {self._current_session_id}")

    # ==================== 日志 ====================

    @property
    def logger(self):
        """获取日志器"""
        return self._logger


    @property
    def app(self) -> 'QApplication':
        """获取 QApplication 实例"""
        return self._app

    def set_app(self, app: 'QApplication'):
        """设置 QApplication 实例"""
        self._app = app


# 全局应用状态实例
_app_state: Optional[AppState] = None


def get_app_state() -> AppState:
    """
    获取全局应用状态实例（单例模式）

    Returns:
        AppState 实例
    """
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state
