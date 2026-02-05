"""
文件命名工具
为图片和视频提供规范化的命名
"""
from datetime import datetime
from pathlib import Path
from typing import Optional
import re


class FileNaming:
    """文件命名工具类"""
    
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """清理文件名，移除非法字符"""
        # 替换非法字符
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        # 替换多个下划线
        name = re.sub(r'_+', '_', name)
        # 移除首尾空格和下划线
        name = name.strip(' _')
        return name[:100]  # 限制长度
    
    @staticmethod
    def generate_image_filename(
        verse_index: int,
        prompt_index: int,
        verse_text: str = "",
        model: str = "",
        style: str = "",
        extension: str = "png"
    ) -> str:
        """
        生成规范的图片文件名
        
        格式: {诗句简写}_{序号}_{模型}_{时间戳}.{扩展名}
        示例: 床前明月光_v0p0_gemini_20260205_143000.png
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 诗句简写（取前4个字）
        verse_short = FileNaming.sanitize_filename(verse_text[:4]) if verse_text else ""
        
        # 模型简写
        model_short = FileNaming._shorten_model_name(model)
        
        # 构建文件名
        parts = []
        if verse_short:
            parts.append(verse_short)
        parts.append(f"v{verse_index}p{prompt_index}")
        if model_short:
            parts.append(model_short)
        if style:
            parts.append(FileNaming.sanitize_filename(style[:10]))
        parts.append(timestamp)
        
        filename = "_".join(parts)
        return f"{filename}.{extension}"
    
    @staticmethod
    def generate_video_filename(
        verse_index: int = 0,
        prompt_index: int = 0,
        verse_text: str = "",
        model: str = "",
        task_id: str = "",
        extension: str = "mp4"
    ) -> str:
        """
        生成规范的视频文件名
        
        格式: {诗句简写}_{序号}_{模型}_{任务ID简写}_{时间戳}.{扩展名}
        示例: 床前明月光_v0p0_sora2_abc123_20260205_143000.mp4
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 诗句简写
        verse_short = FileNaming.sanitize_filename(verse_text[:4]) if verse_text else ""
        
        # 模型简写
        model_short = FileNaming._shorten_model_name(model)
        
        # 任务ID简写（取后6位）
        task_short = task_id[-6:] if task_id else ""
        
        # 构建文件名
        parts = []
        if verse_short:
            parts.append(verse_short)
        parts.append(f"v{verse_index}p{prompt_index}")
        if model_short:
            parts.append(model_short)
        if task_short:
            parts.append(task_short)
        parts.append(timestamp)
        
        filename = "_".join(parts)
        return f"{filename}.{extension}"
    
    @staticmethod
    def generate_music_filename(
        title: str = "",
        style: str = "",
        extension: str = "mp3"
    ) -> str:
        """
        生成规范的音乐文件名
        
        格式: {标题}_{风格简写}_{时间戳}.{扩展名}
        示例: 静夜思_古风_20260205_143000.mp3
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 标题
        title_clean = FileNaming.sanitize_filename(title) if title else "music"
        
        # 风格简写（取第一个标签）
        style_short = ""
        if style:
            first_tag = style.split(",")[0].strip()[:15]
            style_short = FileNaming.sanitize_filename(first_tag)
        
        # 构建文件名
        parts = [title_clean]
        if style_short:
            parts.append(style_short)
        parts.append(timestamp)
        
        filename = "_".join(parts)
        return f"{filename}.{extension}"
    
    @staticmethod
    def _shorten_model_name(model: str) -> str:
        """简化模型名称"""
        if not model:
            return ""
        
        # 模型名称映射
        short_names = {
            'gemini': 'gem',
            'gpt': 'gpt',
            'flux': 'flux',
            'dall-e': 'dalle',
            'midjourney': 'mj',
            'sora-2-all': 'sora2a',
            'sora-2-pro': 'sora2p',
            'sora-2': 'sora2',
            'grok-video-3-10s': 'grok10s',
            'grok-video-3': 'grok3',
            'veo3.1': 'veo31',
            'kling': 'kling',
            'luma': 'luma',
            'runway': 'runway',
            'minimax': 'mmax',
            'wan': 'wan',
            'doubao': 'doubao'
        }
        
        model_lower = model.lower()
        for key, short in short_names.items():
            if key in model_lower:
                return short
        
        # 默认取前5个字符
        return FileNaming.sanitize_filename(model[:5])
    
    @staticmethod
    def generate_export_folder_name(poetry_title: str = "") -> str:
        """生成导出文件夹名称"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = FileNaming.sanitize_filename(poetry_title[:20]) if poetry_title else "export"
        return f"{title}_{timestamp}"


# 便捷函数
def image_filename(**kwargs) -> str:
    return FileNaming.generate_image_filename(**kwargs)

def video_filename(**kwargs) -> str:
    return FileNaming.generate_video_filename(**kwargs)

def music_filename(**kwargs) -> str:
    return FileNaming.generate_music_filename(**kwargs)
