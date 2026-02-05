"""
风格锚定系统
用于保持生成图像的风格一致性
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json


class StyleAnchor:
    """
    风格锚定：从参考图片或首张生成图片提取风格特征

    功能：
    1. 设置参考图片
    2. 提取风格特征（颜色、艺术风格、氛围等）
    3. 将风格特征应用到提示词
    """

    def __init__(self):
        self.reference_image: Optional[str] = None  # 参考图片路径
        self.style_features: Dict[str, Any] = {}    # 提取的风格特征
        self.style_description: str = ""             # 风格描述文本

    def set_reference(self, image_path: str, auto_extract: bool = True) -> None:
        """
        设置参考图片

        Args:
            image_path: 参考图片路径
            auto_extract: 是否自动提取风格特征
        """
        self.reference_image = image_path

        if auto_extract:
            self.style_features = self._extract_features(image_path)

    def set_style_description(self, description: str) -> None:
        """
        手动设置风格描述

        Args:
            description: 风格描述文本
        """
        self.style_description = description
        self.style_features['manual_description'] = description

    def _extract_features(self, image_path: str) -> Dict[str, Any]:
        """
        从图片提取风格特征

        注意：这是一个简化版本，实际应用中可以使用
        计算机视觉模型来提取更准确的特征。

        Args:
            image_path: 图片路径

        Returns:
            风格特征字典
        """
        # 简化版本：基于文件名和路径推断风格
        path = Path(image_path)
        name = path.stem.lower()

        features = {
            'color_palette': self._infer_color_palette(name),
            'art_style': self._infer_art_style(name),
            'mood': self._infer_mood(name),
            'lighting': self._infer_lighting(name),
        }

        return features

    def _infer_color_palette(self, name: str) -> str:
        """从文件名推断色调"""
        palettes = {
            'warm': ['warm', 'sunset', 'golden', 'autumn', 'fire', 'red'],
            'cool': ['cool', 'winter', 'night', 'blue', 'cold', 'ice'],
            'earthy': ['earth', 'brown', 'nature', 'forest', 'mountain'],
            'pastel': ['pastel', 'soft', 'light', 'dreamy'],
        }

        for palette, keywords in palettes.items():
            if any(kw in name for kw in keywords):
                return palette

        return "natural"

    def _infer_art_style(self, name: str) -> str:
        """从文件名推断艺术风格"""
        styles = {
            'ink': ['ink', 'shui-mo', 'sumi', 'calligraphy'],
            'watercolor': ['watercolor', 'aquarelle'],
            'oil': ['oil', 'painting'],
            'anime': ['anime', 'manga'],
            'realistic': ['realistic', 'photo', 'real'],
            'minimalist': ['minimal', 'simple', 'clean'],
        }

        for style, keywords in styles.items():
            if any(kw in name for kw in keywords):
                return style

        return "traditional chinese art"

    def _infer_mood(self, name: str) -> str:
        """从文件名推断氛围"""
        moods = {
            'peaceful': ['peaceful', 'calm', 'quiet', 'serene'],
            'melancholic': ['sad', 'melancholy', 'lonely', 'nostalgic'],
            'energetic': ['energetic', 'dynamic', 'powerful', 'strong'],
            'mysterious': ['mysterious', 'fog', 'mist', 'hidden'],
            'romantic': ['romantic', 'love', 'tender'],
        }

        for mood, keywords in moods.items():
            if any(kw in name for kw in keywords):
                return mood

        return "contemplative"

    def _infer_lighting(self, name: str) -> str:
        """从文件名推断光照"""
        lighting_keywords = {
            'morning light': ['morning', 'dawn', 'sunrise'],
            'golden hour': ['golden', 'sunset', 'dusk'],
            'moonlight': ['moon', 'night', 'evening'],
            'soft light': ['soft', 'diffused', 'gentle'],
            'dramatic': ['dramatic', 'contrast', 'shadow'],
        }

        for lighting, keywords in lighting_keywords.items():
            if any(kw in name for kw in keywords):
                return lighting

        return "natural lighting"

    def apply_to_prompt(self, prompt: str, strength: float = 1.0) -> str:
        """
        将风格特征应用到提示词

        Args:
            prompt: 原始提示词
            strength: 风格应用强度 (0.0 - 1.0)

        Returns:
            应用风格后的提示词
        """
        if not self.style_features and not self.style_description:
            return prompt

        # 构建风格后缀
        style_parts = []

        # 使用手动描述
        if self.style_description:
            style_parts.append(self.style_description)

        # 使用提取的特征
        for feature_type in ['art_style', 'color_palette', 'mood', 'lighting']:
            value = self.style_features.get(feature_type)
            if value:
                style_parts.append(value)

        if not style_parts:
            return prompt

        # 根据强度决定如何应用
        if strength < 0.3:
            style_suffix = ", influenced by: " + ", ".join(style_parts[:2])
        elif strength < 0.7:
            style_suffix = ", style: " + ", ".join(style_parts[:3])
        else:
            style_suffix = ", consistent style: " + ", ".join(style_parts)

        return f"{prompt}{style_suffix}"

    def get_style_prompt(self) -> str:
        """
        获取纯风格提示词（用于首张图片）

        Returns:
            风格提示词
        """
        if self.style_description:
            return self.style_description

        features = self.style_features
        return f"{features.get('art_style', 'traditional art')}, " \
               f"{features.get('color_palette', 'natural')}, " \
               f"{features.get('mood', 'peaceful')}, " \
               f"{features.get('lighting', 'natural')}"

    def save(self, path: Path) -> None:
        """
        保存风格配置

        Args:
            path: 保存路径
        """
        data = {
            'reference_image': self.reference_image,
            'style_features': self.style_features,
            'style_description': self.style_description,
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: Path) -> None:
        """
        加载风格配置

        Args:
            path: 配置文件路径
        """
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.reference_image = data.get('reference_image')
        self.style_features = data.get('style_features', {})
        self.style_description = data.get('style_description', '')

    def reset(self) -> None:
        """重置风格锚定"""
        self.reference_image = None
        self.style_features = {}
        self.style_description = ""


class StylePreset:
    """风格预设 - 常用艺术风格"""

    # 中国传统艺术风格
    CHINESE_INK = {
        'art_style': 'traditional Chinese ink painting',
        'color_palette': 'monochrome black and gray',
        'mood': 'contemplative',
        'lighting': 'soft diffused light',
        'description': 'A traditional Chinese ink painting style, characterized by bold brushstrokes, '
                       'monochrome palette with varying ink density, and emphasis on empty space (liubai).'
    }

    CHINESE_WATERCOLOR = {
        'art_style': 'Chinese watercolor painting',
        'color_palette': 'soft pastel colors',
        'mood': 'gentle',
        'lighting': 'soft natural light',
        'description': 'A delicate Chinese watercolor style with soft colors, gentle gradients, '
                       'and ethereal atmosphere.'
    }

    GONGBI = {
        'art_style': 'Chinese gongbi painting style',
        'color_palette': 'rich vibrant colors',
        'mood': 'refined',
        'lighting': 'even studio lighting',
        'description': 'A detailed Chinese gongbi style with precise brushwork, rich colors, '
                       'and meticulous detail.'
    }

    # 现代艺术风格
    ANIME = {
        'art_style': 'anime art style',
        'color_palette': 'vibrant saturated colors',
        'mood': 'dynamic',
        'lighting': 'dramatic lighting',
        'description': 'Japanese anime art style with clean lines, large expressive eyes, '
                       'and vibrant colors.'
    }

    REALISTIC = {
        'art_style': 'photorealistic',
        'color_palette': 'natural colors',
        'mood': 'authentic',
        'lighting': 'natural lighting',
        'description': 'Photorealistic style with accurate details, natural colors, '
                       'and realistic lighting.'
    }

    IMPRESSIONIST = {
        'art_style': 'impressionist painting',
        'color_palette': 'warm pastel tones',
        'mood': 'dreamy',
        'lighting': 'soft dappled light',
        'description': 'Impressionist style with visible brushstrokes, light colors, '
                       'and emphasis on light and atmosphere.'
    }

    @staticmethod
    def apply_preset(preset: dict, prompt: str) -> str:
        """
        应用风格预设到提示词

        Args:
            preset: 风格预设字典
            prompt: 原始提示词

        Returns:
            应用风格后的提示词
        """
        style_suffix = preset.get('description', '')
        return f"{prompt}. {style_suffix}"

    @staticmethod
    def get_all_presets() -> dict:
        """获取所有风格预设"""
        return {
            'Chinese Ink': StylePreset.CHINESE_INK,
            'Chinese Watercolor': StylePreset.CHINESE_WATERCOLOR,
            'Gongbi': StylePreset.GONGBI,
            'Anime': StylePreset.ANIME,
            'Realistic': StylePreset.REALISTIC,
            'Impressionist': StylePreset.IMPRESSIONIST,
        }
