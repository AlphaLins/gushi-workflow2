"""
API 配置模块
管理所有 API 相关的配置参数
"""
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json


@dataclass
class APIConfig:
    """API 配置类"""
    api_key: str = "sk-xxx..."
    base_url: str = "https://vipstar.vip"
    model: str = "gemini-2.5-flash"  # 默认文本模型
    image_model: str = "gemini-3-pro-image-preview"  # 默认图像模型
    use_native_google: bool = False  # 是否使用 Google 原生 SDK
    max_retries: int = 5  # 最大重试次数
    timeout: int = 120  # 超时时间(秒)
    temperature: float = 0.7  # 温度参数
    top_p: float = 0.9  # Top-p 参数

    # 视频配置
    video_model: str = "grok-video-3-10s"
    video_aspect_ratio: str = "3:2"  # 2:3, 3:2, 1:1, 16:9
    video_size: str = "720P"

    # 音乐配置
    music_model: str = "chirp-v4"  # Suno 模型版本
    music_tags: str = "chinese traditional,emotional"

    # 生成配置
    example_count: int = 3  # 每句诗生成几个示例
    style_anchors: bool = True  # 是否使用风格锚定

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'model': self.model,
            'image_model': self.image_model,
            'use_native_google': self.use_native_google,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'video_model': self.video_model,
            'video_aspect_ratio': self.video_aspect_ratio,
            'video_size': self.video_size,
            'music_model': self.music_model,
            'music_tags': self.music_tags,
            'example_count': self.example_count,
            'style_anchors': self.style_anchors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'APIConfig':
        """从字典创建配置"""
        return cls(**data)

    def save(self, path: Optional[Path] = None) -> None:
        """保存配置到文件"""
        if path is None:
            path = Path.home() / '.guui_config.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'APIConfig':
        """从文件加载配置"""
        if path is None:
            path = Path.home() / '.guui_config.json'
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        return cls()


# 模型配置常量
class Models:
    """可用模型列表"""

    # 文本模型
    TEXT_MODELS = {
        'gpt-5.2': 'GPT-5.2 (最新)',
        'gpt-4o': 'GPT-4o',
        'claude-opus-4-5-20251101': 'Claude Opus 4.5',
        'claude-sonnet-4-5-20250929': 'Claude Sonnet 4.5',
        'gemini-3-pro-preview': 'Gemini 3 Pro',
        'gemini-2.5-flash': 'Gemini 2.5 Flash',
        'deepseek-v3.2': 'DeepSeek V3.2',
        'deepseek-r1': 'DeepSeek R1',
        'qwen3-max': 'Qwen3 Max',
        'glm-4.7': 'GLM 4.7',
        'grok-4.1': 'Grok 4.1',
        'kimi-k2.5': 'Kimi K2.5',
    }

    # 图像模型
    IMAGE_MODELS = {
        'gemini-3-pro-image-preview': 'Gemini 3 Pro Image',
        'gemini-2.5-flash-image-preview': 'Gemini 2.5 Flash Image',
        'gpt-image-1.5': 'GPT Image 1.5',
        'flux-pro-1.1-ultra': 'Flux Pro 1.1 Ultra',
        'flux-kontext-max': 'Flux Kontext Max',
        'dall-e-3': 'DALL-E 3',
        'mj_imagine': 'Midjourney Imagine',
        'qwen-image-max': 'Qwen Image Max',
        'ideogram_generate_V_3_TURBO': 'Ideogram V3 Turbo',
    }

    # 视频模型
    VIDEO_MODELS = {
        'veo3.1': 'Veo 3.1',
        'veo3.1-fast': 'Veo 3.1 Fast',
        'veo3-fast-frames': 'Veo 3 Fast Frames',
        'sora-2': 'Sora 2',
        'sora-2-pro': 'Sora 2 Pro',
        'grok-video-3': 'Grok Video 3',
        'grok-video-3-10s': 'Grok Video 3 10s',
        'kling-video': 'Kling Video',
        'luma_video_api': 'Luma Video',
        'runwayml-gen4_turbo-10': 'Runway Gen4 Turbo',
        'doubao-seedance-1-0-pro-fast-251015': 'Doubao Seedance Pro',
        'minimax/video-01': 'MiniMax Video 01',
        'wan2.6-i2v': 'Wan 2.6 I2V',
    }

    # 音乐模型
    MUSIC_MODELS = {
        'chirp-v5': 'Suno V5.0 (最新)',
        'chirp-v4': 'Suno V4.0 (推荐)',
        'chirp-auk': 'Suno V4.5',
        'chirp-v3-5': 'Suno V3.5',
        'chirp-v3-0': 'Suno V3.0',
    }

    # 艺术风格
    ART_STYLES = {
        'ink': '传统水墨画',
        'gongbi': '工笔画',
        'watercolor': '水彩画',
        'oil': '油画',
        'anime': '动漫风格',
        'realistic': '写实风格',
        'abstract': '抽象风格',
        'minimalist': '极简风格',
    }

    # 视频宽高比
    ASPECT_RATIOS = {
        '16:9': '16:9 (横屏)',
        '9:16': '9:16 (竖屏)',
        '3:2': '3:2 (横版)',
        '2:3': '2:3 (竖版)',
        '1:1': '1:1 (正方形)',
    }

    # 音乐风格标签
    MUSIC_TAGS = [
        'chinese traditional',
        'guzheng',
        'pipa',
        'erhu',
        'pop',
        'emotional',
        'peaceful',
        'epic',
        'classical',
        'ambient',
        'folk',
    ]
