"""
文件管理工具
处理文件读写、目录管理、会话持久化
"""
import json
import shutil
from pathlib import Path
from typing import Any, Optional, List
from datetime import datetime
import hashlib


class FileManager:
    """文件管理器 - 遵循单一职责原则"""

    def __init__(self, base_dir: Path = None):
        """
        初始化文件管理器

        Args:
            base_dir: 基础目录，默认为当前目录
        """
        self.base_dir = base_dir or Path.cwd()
        self.sessions_dir = self.base_dir / "sessions"
        self.exports_dir = self.base_dir / "exports"
        self.images_dir = self.base_dir / "generated_images"
        self.videos_dir = self.base_dir / "generated_videos"
        self.music_dir = self.base_dir / "generated_music"

        # 创建必要的目录
        self._create_directories()

    def _create_directories(self) -> None:
        """创建必要的目录结构"""
        for directory in [self.sessions_dir, self.exports_dir,
                         self.images_dir, self.videos_dir, self.music_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    # ==================== 会话管理 ====================

    def create_session(self) -> str:
        """
        创建新会话

        Returns:
            会话 ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{timestamp}"
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(exist_ok=True)
        return session_id

    def get_session_dir(self, session_id: str) -> Path:
        """
        获取会话目录

        Args:
            session_id: 会话 ID

        Returns:
            会话目录路径
        """
        return self.sessions_dir / session_id

    def save_session_data(self, session_id: str, data: dict,
                         filename: str = "data.json") -> Path:
        """
        保存会话数据

        Args:
            session_id: 会话 ID
            data: 要保存的数据
            filename: 文件名

        Returns:
            保存的文件路径
        """
        session_dir = self.get_session_dir(session_id)
        file_path = session_dir / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return file_path

    def load_session_data(self, session_id: str,
                         filename: str = "data.json") -> Optional[dict]:
        """
        加载会话数据

        Args:
            session_id: 会话 ID
            filename: 文件名

        Returns:
            加载的数据，不存在则返回 None
        """
        file_path = self.get_session_dir(session_id) / filename

        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_sessions(self) -> List[dict]:
        """
        列出所有会话

        Returns:
            会话信息列表
        """
        sessions = []

        for session_dir in sorted(self.sessions_dir.iterdir(), reverse=True):
            if not session_dir.is_dir():
                continue

            metadata_file = session_dir / "metadata.json"
            metadata = {}

            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

            sessions.append({
                'id': session_dir.name,
                'path': str(session_dir),
                **metadata
            })

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功删除
        """
        session_dir = self.get_session_dir(session_id)

        if not session_dir.exists():
            return False

        shutil.rmtree(session_dir)
        return True

    # ==================== 文件保存 ====================

    def save_image(self, image_data: bytes, session_id: str,
                  filename: str) -> Path:
        """
        保存图片

        Args:
            image_data: 图片二进制数据
            session_id: 会话 ID
            filename: 文件名

        Returns:
            保存的文件路径
        """
        session_dir = self.get_session_dir(session_id)
        images_dir = session_dir / "images"
        images_dir.mkdir(exist_ok=True)

        file_path = images_dir / filename
        with open(file_path, 'wb') as f:
            f.write(image_data)

        return file_path

    def save_video(self, video_data: bytes, session_id: str,
                  filename: str) -> Path:
        """
        保存视频

        Args:
            video_data: 视频二进制数据
            session_id: 会话 ID
            filename: 文件名

        Returns:
            保存的文件路径
        """
        session_dir = self.get_session_dir(session_id)
        videos_dir = session_dir / "videos"
        videos_dir.mkdir(exist_ok=True)

        file_path = videos_dir / filename
        with open(file_path, 'wb') as f:
            f.write(video_data)

        return file_path

    def save_music(self, audio_data: bytes, session_id: str,
                  filename: str) -> Path:
        """
        保存音乐

        Args:
            audio_data: 音频二进制数据
            session_id: 会话 ID
            filename: 文件名

        Returns:
            保存的文件路径
        """
        session_dir = self.get_session_dir(session_id)
        music_dir = session_dir / "music"
        music_dir.mkdir(exist_ok=True)

        file_path = music_dir / filename
        with open(file_path, 'wb') as f:
            f.write(audio_data)

        return file_path

    # ==================== 导出功能 ====================

    def export_session(self, session_id: str, output_path: Path = None) -> Path:
        """
        导出会话为 ZIP 文件

        Args:
            session_id: 会话 ID
            output_path: 输出路径，默认为 exports 目录

        Returns:
            导出的 ZIP 文件路径
        """
        import zipfile

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.exports_dir / f"{session_id}_{timestamp}.zip"

        self.exports_dir.mkdir(exist_ok=True)

        session_dir = self.get_session_dir(session_id)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in session_dir.rglob('*'):
                if file.is_file():
                    arcname = file.relative_to(session_dir)
                    zipf.write(file, arcname)

        return output_path

    # ==================== 工具函数 ====================

    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """
        计算文件的 MD5 哈希

        Args:
            file_path: 文件路径

        Returns:
            MD5 哈希值
        """
        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)

        return md5.hexdigest()

    @staticmethod
    def get_unique_filename(directory: Path, base_name: str,
                           extension: str) -> str:
        """
        生成唯一的文件名

        Args:
            directory: 目录路径
            base_name: 基础文件名
            extension: 文件扩展名

        Returns:
            唯一的文件名
        """
        counter = 0
        filename = f"{base_name}.{extension}"

        while (directory / filename).exists():
            counter += 1
            filename = f"{base_name}_{counter}.{extension}"

        return filename

    def get_session_images(self, session_id: str) -> List[Path]:
        """
        获取会话中的所有图片

        Args:
            session_id: 会话 ID

        Returns:
            图片路径列表
        """
        images_dir = self.get_session_dir(session_id) / "images"

        if not images_dir.exists():
            return []

        return sorted(images_dir.glob('*.png')) + sorted(images_dir.glob('*.jpg'))

    def get_session_videos(self, session_id: str) -> List[Path]:
        """
        获取会话中的所有视频

        Args:
            session_id: 会话 ID

        Returns:
            视频路径列表
        """
        videos_dir = self.get_session_dir(session_id) / "videos"

        if not videos_dir.exists():
            return []

        return sorted(videos_dir.glob('*.mp4'))

    def get_session_music(self, session_id: str) -> List[Path]:
        """
        获取会话中的所有音乐

        Args:
            session_id: 会话 ID

        Returns:
            音乐路径列表
        """
        music_dir = self.get_session_dir(session_id) / "music"

        if not music_dir.exists():
            return []

        return sorted(music_dir.glob('*.mp3')) + sorted(music_dir.glob('*.mp4'))

    def clean_old_sessions(self, keep_count: int = 10) -> int:
        """
        清理旧会话，保留最近的 N 个

        Args:
            keep_count: 保留的会话数量

        Returns:
            删除的会话数量
        """
        sessions = self.list_sessions()

        if len(sessions) <= keep_count:
            return 0

        # 删除旧的会话
        deleted_count = 0
        for session in sessions[keep_count:]:
            if self.delete_session(session['id']):
                deleted_count += 1

        return deleted_count
