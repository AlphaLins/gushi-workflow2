"""
音乐生成数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MusicTaskStatus(str, Enum):
    """音乐任务状态枚举"""
    NOT_START = "NOT_START"
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"


class MusicClip(BaseModel):
    """单个音乐片段"""
    id: str = Field(..., description="片段 ID")
    video_url: Optional[str] = Field(default=None, description="视频 URL（带封面）")
    audio_url: Optional[str] = Field(default=None, description="纯音频 URL")
    image_large_url: Optional[str] = Field(default=None, description="封面图片 URL")
    title: str = Field(..., description="歌曲标题")
    duration: Optional[float] = Field(default=None, description="时长(秒)")


class MusicTask(BaseModel):
    """音乐生成任务"""
    task_id: str = Field(..., description="任务 ID")
    status: MusicTaskStatus = Field(default=MusicTaskStatus.NOT_START, description="任务状态")
    title: str = Field(..., description="歌曲标题")
    tags: str = Field(default="", description="风格标签")
    prompt: str = Field(default="", description="歌词或描述")
    negative_tags: str = Field(default="", description="排除风格")
    model: str = Field(default="chirp-v4", description="模型版本")
    generation_type: str = Field(default="TEXT", description="生成类型")
    continue_clip_id: Optional[str] = Field(default=None, description="续写片段 ID")
    continue_at: Optional[float] = Field(default=None, description="续写起始时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    submit_time: Optional[datetime] = Field(default=None, description="提交时间")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    finish_time: Optional[datetime] = Field(default=None, description="完成时间")
    clips: List[MusicClip] = Field(default_factory=list, description="生成的音乐片段")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    def update_status(self, status: MusicTaskStatus, error: Optional[str] = None) -> None:
        """更新任务状态"""
        self.status = status
        if error:
            self.error_message = error

        if status == MusicTaskStatus.SUBMITTED and not self.submit_time:
            self.submit_time = datetime.now()
        elif status == MusicTaskStatus.IN_PROGRESS and not self.start_time:
            self.start_time = datetime.now()
        elif status == MusicTaskStatus.SUCCESS and not self.finish_time:
            self.finish_time = datetime.now()
        elif status == MusicTaskStatus.FAILURE and not self.finish_time:
            self.finish_time = datetime.now()

    def set_clips(self, clips: List[MusicClip]) -> None:
        """设置生成的音乐片段"""
        self.clips = clips
        if clips:
            self.update_status(MusicTaskStatus.SUCCESS)
        else:
            self.update_status(MusicTaskStatus.FAILURE, "未生成任何音乐片段")

    def get_elapsed_time(self) -> Optional[float]:
        """获取已用时间(秒)"""
        if not self.submit_time:
            return None

        end_time = self.finish_time or datetime.now()
        return (end_time - self.submit_time).total_seconds()

    def is_finished(self) -> bool:
        """是否已完成（成功或失败）"""
        return self.status in (MusicTaskStatus.SUCCESS, MusicTaskStatus.FAILURE)

    def is_processing(self) -> bool:
        """是否正在处理中"""
        return self.status in (MusicTaskStatus.SUBMITTED, MusicTaskStatus.QUEUED,
                               MusicTaskStatus.IN_PROGRESS)

    def get_primary_clip(self) -> Optional[MusicClip]:
        """获取主要音乐片段（第一个）"""
        return self.clips[0] if self.clips else None


class LyricsRequest(BaseModel):
    """歌词生成请求"""
    prompt: str = Field(..., description="歌词主题或关键词")
    style: Optional[str] = Field(default="chinese traditional", description="风格")
