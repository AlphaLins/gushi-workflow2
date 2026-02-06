"""
诗词提示词数据模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any


class ImagePrompt(BaseModel):
    """单个图像提示词"""
    description: str = Field(..., min_length=20, description="英文图像提示词")
    video_prompt: str = Field(default="", description="视频提示词（可选）")

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """验证描述长度"""
        if len(v.strip()) < 20:
            raise ValueError("图像描述必须至少包含 20 个字符")
        return v.strip()


class MusicPrompt(BaseModel):
    """Suno AI 音乐提示词"""
    style_prompt: str = Field(default="", description="音乐风格提示词 (Genre, Vocals, Mood, Instruments)")
    title: str = Field(default="", description="歌曲标题")
    lyrics_cn: str = Field(default="", description="中文歌词（古诗原文 + 结构标签）")
    lyrics_en: str = Field(default="", description="英文歌词（翻译版 + 结构标签）")
    instrumental: bool = Field(default=False, description="是否是纯音乐（无人声）")
    
    def get_full_lyrics(self) -> str:
        """获取完整歌词（中英双语）"""
        return f"{self.lyrics_cn}\n\n--- English Version ---\n\n{self.lyrics_en}"


class VersePrompts(BaseModel):
    """单个诗句的提示词集合"""
    verse: str = Field(..., description="诗句原文")
    index: int = Field(..., ge=0, description="诗句索引")
    descriptions: List[ImagePrompt] = Field(default_factory=list, description="多个图像提示词")

    def add_description(self, description: str) -> None:
        """添加图像描述"""
        self.descriptions.append(ImagePrompt(description=description))

    def remove_description(self, index: int) -> None:
        """移除指定索引的描述"""
        if 0 <= index < len(self.descriptions):
            self.descriptions.pop(index)

    def update_description(self, index: int, description: str) -> None:
        """更新指定索引的描述"""
        if 0 <= index < len(self.descriptions):
            self.descriptions[index] = ImagePrompt(description=description)


class PoetryPromptsResponse(BaseModel):
    """诗词提示词响应"""
    prompts: List[VersePrompts] = Field(default_factory=list, description="所有诗句的提示词")
    music_prompt: Optional[MusicPrompt] = Field(default=None, description="整首诗的音乐提示词")
    grid_prompt: Optional[str] = Field(default=None, description="九宫格网格生图提示词")

    def add_verse(self, verse: str, index: int) -> None:
        """添加诗句"""
        verse_prompt = VersePrompts(verse=verse, index=index)
        self.prompts.append(verse_prompt)
        return verse_prompt

    def get_verse(self, index: int) -> Optional[VersePrompts]:
        """获取指定索引的诗句"""
        for verse in self.prompts:
            if verse.index == index:
                return verse
        return None

    def remove_verse(self, index: int) -> bool:
        """移除指定索引的诗句"""
        for i, verse in enumerate(self.prompts):
            if verse.index == index:
                self.prompts.pop(i)
                return True
        return False

    def total_prompts(self) -> int:
        """获取总提示词数量"""
        return sum(len(v.descriptions) for v in self.prompts)

    def all_descriptions(self) -> List[tuple]:
        """获取所有描述 (verse_index, prompt_index, description, video_prompt)"""
        result = []
        for verse in self.prompts:
            for i, desc in enumerate(verse.descriptions):
                video_prompt = getattr(desc, 'video_prompt', '') or ''
                result.append((verse.index, i, desc.description, video_prompt))
        return result
    
    def get_all_verses_text(self) -> str:
        """获取所有诗句原文"""
        return "\n".join(v.verse for v in self.prompts)

