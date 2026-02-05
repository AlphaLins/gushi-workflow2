"""
视频任务数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class VideoTaskStatus(str, Enum):
    """视频任务状态枚举（兼容 Grok/Veo API）"""
    # 通用状态
    PENDING = "pending"
    SUBMITTED = "submitted"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"

    # Veo 特定状态（映射到通用状态）
    IMAGE_DOWNLOADING = "image_downloading"  # → PROCESSING
    VIDEO_GENERATING = "video_generating"  # → PROCESSING
    VIDEO_GENERATION_COMPLETED = "video_generation_completed"  # → COMPLETED
    VIDEO_GENERATION_FAILED = "video_generation_failed"  # → FAILED
    VIDEO_UPSAMPLING = "video_upsampling"  # → PROCESSING
    VIDEO_UPSAMPLING_COMPLETED = "video_upsampling_completed"  # → COMPLETED
    VIDEO_UPSAMPLING_FAILED = "video_upsampling_failed"  # → FAILED

    @classmethod
    def from_api_status(cls, status: str) -> "VideoTaskStatus":
        """
        从 API 状态转换为内部状态

        Args:
            status: API 返回的状态字符串

        Returns:
            对应的 VideoTaskStatus
        """
        # 标准化状态字符串
        status_lower = status.lower().replace("-", "_")

        # 直接匹配
        for member in cls:
            if member.value == status or member.name.lower() == status_lower:
                return member

        # 映射特定状态到通用状态
        status_mapping = {
            "image_downloading": cls.PROCESSING,
            "video_generating": cls.PROCESSING,
            "video_upsampling": cls.PROCESSING,
            "video_generation_completed": cls.COMPLETED,
            "video_upsampling_completed": cls.COMPLETED,
            "video_generation_failed": cls.FAILED,
            "video_upsampling_failed": cls.FAILED,
        }

        return status_mapping.get(status, cls.PENDING)

    def is_processing_state(self) -> bool:
        """是否为处理中状态（包括子状态）"""
        processing_states = {
            self.PENDING,
            self.SUBMITTED,
            self.QUEUED,
            self.PROCESSING,
            self.IMAGE_DOWNLOADING,
            self.VIDEO_GENERATING,
            self.VIDEO_UPSAMPLING,
        }
        return self in processing_states


class VideoTask(BaseModel):
    """视频生成任务"""
    task_id: str = Field(..., description="任务 ID")
    status: VideoTaskStatus = Field(default=VideoTaskStatus.PENDING, description="任务状态")
    verse_index: int = Field(..., ge=0, description="诗句索引")
    prompt_index: int = Field(..., ge=0, description="提示词索引")
    source_image_path: str = Field(..., description="源图片路径")
    video_prompt: Any = Field(default=None, description="视频提示词")
    model: str = Field(default="grok-video-3-10s", description="视频模型")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    submit_time: Optional[datetime] = Field(default=None, description="提交时间")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    finish_time: Optional[datetime] = Field(default=None, description="完成时间")
    video_path: Optional[str] = Field(default=None, description="本地视频路径")
    video_url: Optional[str] = Field(default=None, description="视频 URL")
    duration: Optional[float] = Field(default=None, description="视频时长(秒)")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    def update_status(self, status: VideoTaskStatus, error: Optional[str] = None) -> None:
        """更新任务状态"""
        self.status = status
        if error:
            self.error_message = error

        if status == VideoTaskStatus.SUBMITTED and not self.submit_time:
            self.submit_time = datetime.now()
        elif status == VideoTaskStatus.PROCESSING and not self.start_time:
            self.start_time = datetime.now()
        elif status == VideoTaskStatus.COMPLETED and not self.finish_time:
            self.finish_time = datetime.now()
        elif status == VideoTaskStatus.FAILED and not self.finish_time:
            self.finish_time = datetime.now()

    def set_result(self, video_url: str, duration: Optional[float] = None) -> None:
        """设置视频结果"""
        self.video_url = video_url
        if duration:
            self.duration = duration
        self.update_status(VideoTaskStatus.COMPLETED)

    def get_elapsed_time(self) -> Optional[float]:
        """获取已用时间(秒)"""
        if not self.submit_time:
            return None

        end_time = self.finish_time or datetime.now()
        return (end_time - self.submit_time).total_seconds()

    def is_finished(self) -> bool:
        """是否已完成（成功或失败）"""
        return self.status in (VideoTaskStatus.COMPLETED, VideoTaskStatus.FAILED, VideoTaskStatus.CANCELLED)

    def is_processing(self) -> bool:
        """是否正在处理中（包括所有子状态）"""
        return self.status.is_processing_state()


class VideoPrompt(BaseModel):
    """视频提示词"""
    prompt: str = Field(..., description="视频描述")
    style: Optional[str] = Field(default=None, description="风格")
    camera_motion: Optional[str] = Field(default=None, description="运镜方式")
    duration: int = Field(default=5, ge=1, le=60, description="时长(秒)")

    def to_video_api_prompt(self) -> str:
        """转换为视频 API 提示词格式"""
        parts = [self.prompt]

        if self.style:
            parts.append(f"style: {self.style}")

        if self.camera_motion:
            parts.append(f"camera: {self.camera_motion}")

        # 对于 Grok 模型，需要添加模式标志
        return " --mode=custom ".join(parts) if self.camera_motion else " ".join(parts)
