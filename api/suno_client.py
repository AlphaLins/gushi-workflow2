"""
音乐生成 API 客户端 (Suno)
支持所有模式：灵感模式、自定义模式、续写模式、翻唱模式
基于 sunnyAPI 文档完整实现
"""
import time
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
import requests


class SunoClient:
    """
    Suno 音乐生成客户端 - 完整版

    支持模式：
    - 灵感模式 (Inspiration): 根据描述生成音乐
    - 自定义模式 (Custom): 自定义歌词和风格，支持性别选择
    - 续写模式 (Extend): 续写现有音乐
    - 翻唱模式 (Cover): 基于音频进行翻唱
    
    支持模型：
    - chirp-v5: Suno V5.0 (最新)
    - chirp-auk: Suno V4.5
    - chirp-v4: Suno V4.0 (推荐)
    - chirp-v3-5: Suno V3.5
    - chirp-v3-0: Suno V3.0
    - chirp-v3-5-upload: V3.5 上传音频版本
    - chirp-v3-5-tau: V3.5 翻唱专用
    """

    # 任务状态常量
    STATUS_NOT_START = "NOT_START"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_QUEUED = "QUEUED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILURE = "FAILURE"

    def __init__(self, api_key: str, base_url: str,
                 timeout: int = 120):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ==================== 音乐生成 ====================

    def generate_music(self,
                      prompt: str,
                      tags: str = "chinese traditional,emotional",
                      title: str = "",
                      negative_tags: str = "",
                      model: str = "chirp-v4",
                      generation_type: str = "TEXT",
                      vocal_gender: Optional[Literal["m", "f"]] = None,
                      create_mode: str = "custom",
                      continue_clip_id: Optional[str] = None,
                      continue_at: Optional[float] = None,
                      notify_hook: Optional[str] = None) -> str:
        """
        生成音乐 - 自定义创作模式

        Args:
            prompt: 歌词内容或描述
            tags: 风格标签 (逗号分隔)
            title: 歌曲标题
            negative_tags: 不希望出现的风格 (逗号分隔)
            model: 模型版本 (chirp-v5, chirp-v4, chirp-auk, chirp-v3-5, chirp-v3-0)
            generation_type: 生成类型 (TEXT)
            vocal_gender: 人声性别 ("m"=男声, "f"=女声, None=随机)
            create_mode: 创作模式 ("custom"=自定义)
            continue_clip_id: 续写模式下的原歌曲 ID
            continue_at: 续写起始时间(秒)
            notify_hook: 任务完成回调 URL

        Returns:
            任务 ID
        """
        payload = {
            "prompt": prompt,
            "tags": tags,
            "negative_tags": negative_tags,
            "mv": model,
            "generation_type": generation_type
        }

        if title:
            payload["title"] = title

        # 自定义参数 (性别选择等)
        metadata = {"create_mode": create_mode}
        if vocal_gender:
            metadata["vocal_gender"] = vocal_gender
        payload["metadata"] = metadata

        # 续写模式参数
        if continue_clip_id:
            payload["continue_clip_id"] = continue_clip_id
            payload["continue_at"] = continue_at
            payload["task"] = "extend"

        # 回调通知
        if notify_hook:
            payload["notify_hook"] = notify_hook

        response = self.session.post(
            f"{self.base_url}/suno/submit/music",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data.get("data", "")

    def generate_inspiration(self,
                            description: str,
                            tags: str = "chinese traditional,emotional",
                            model: str = "chirp-v4",
                            vocal_gender: Optional[Literal["m", "f"]] = None) -> str:
        """
        灵感模式生成音乐

        Args:
            description: 音乐描述
            tags: 风格标签
            model: 模型版本
            vocal_gender: 人声性别

        Returns:
            任务 ID
        """
        return self.generate_music(
            prompt=description,
            tags=tags,
            model=model,
            generation_type="TEXT",
            vocal_gender=vocal_gender,
            create_mode="custom"
        )

    def generate_custom(self,
                       title: str,
                       lyrics: str,
                       tags: str = "chinese traditional",
                       model: str = "chirp-v4",
                       vocal_gender: Optional[Literal["m", "f"]] = None,
                       negative_tags: str = "") -> str:
        """
        自定义模式生成音乐

        Args:
            title: 歌曲标题
            lyrics: 完整歌词 (支持 [Verse], [Chorus] 等标签)
            tags: 风格标签
            model: 模型版本
            vocal_gender: 人声性别 ("m"=男声, "f"=女声)
            negative_tags: 排除风格

        Returns:
            任务 ID
        """
        return self.generate_music(
            prompt=lyrics,
            tags=tags,
            title=title,
            model=model,
            generation_type="TEXT",
            vocal_gender=vocal_gender,
            negative_tags=negative_tags,
            create_mode="custom"
        )

    def generate_extend(self,
                       clip_id: str,
                       continue_at: float,
                       prompt: str = "",
                       tags: str = "",
                       title: str = "",
                       model: str = "chirp-v4") -> str:
        """
        续写模式生成音乐

        Args:
            clip_id: 原歌曲片段 ID
            continue_at: 续写起始时间(秒), 例如 120.00 或 61.59
            prompt: 续写歌词 (可选)
            tags: 风格标签 (可选，覆盖原风格)
            title: 新标题 (可选)
            model: 模型版本

        Returns:
            任务 ID
        """
        return self.generate_music(
            prompt=prompt,
            tags=tags,
            title=title,
            model=model,
            continue_clip_id=clip_id,
            continue_at=continue_at,
            generation_type="TEXT"
        )

    def generate_cover(self,
                      cover_clip_id: str,
                      prompt: str = "",
                      tags: str = "",
                      title: str = "",
                      model: str = "chirp-v3-5-tau",
                      infill_start_s: Optional[float] = None,
                      infill_end_s: Optional[float] = None) -> str:
        """
        翻唱模式生成音乐

        Args:
            cover_clip_id: 要翻唱的原曲ID或上传的音频clip id
            prompt: 音乐创作提示词 (可选)
            tags: 风格标签
            title: 歌曲标题
            model: 模型 (必须使用 chirp-v3-5-tau)
            infill_start_s: 填充开始时间(秒)
            infill_end_s: 填充结束时间(秒)

        Returns:
            任务 ID
        """
        payload = {
            "prompt": prompt,
            "tags": tags,
            "negative_tags": "",
            "mv": model,
            "generation_type": "TEXT",
            "title": title,
            "task": "cover",
            "cover_clip_id": cover_clip_id
        }

        if infill_start_s is not None:
            payload["infill_start_s"] = infill_start_s
        if infill_end_s is not None:
            payload["infill_end_s"] = infill_end_s

        response = self.session.post(
            f"{self.base_url}/suno/submit/music",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data.get("data", "")

    def upload_audio(self, audio_url: str) -> str:
        """
        上传音频用于翻唱

        Args:
            audio_url: 音频文件 URL

        Returns:
            上传后的 clip_id
        """
        payload = {
            "url": audio_url
        }

        response = self.session.post(
            f"{self.base_url}/suno/upload",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data.get("data", {}).get("clip_id", "")

    # ==================== 歌词生成 ====================

    def generate_lyrics(self, prompt: str) -> str:
        """
        生成歌词

        Args:
            prompt: 主题或关键词 (如 "爱情, 夏天, 思念")

        Returns:
            生成的歌词文本 (包含 [Verse], [Chorus] 等标签)
        """
        payload = {
            "prompt": prompt
        }

        response = self.session.post(
            f"{self.base_url}/suno/submit/lyrics",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        task_id = data.get("data", "")
        
        if not task_id:
            return ""
        
        # 等待歌词生成完成
        result = self.poll_task(task_id, interval=2, max_wait=60)
        lyrics_data = result.get("data", {})
        
        if isinstance(lyrics_data, dict):
            return lyrics_data.get("text", "")
        return str(lyrics_data)

    # ==================== 任务查询 ====================

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        查询单个任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态数据，包含:
            - task_id: 任务ID
            - action: 任务类型 (MUSIC/LYRICS)
            - status: 状态 (NOT_START/SUBMITTED/QUEUED/IN_PROGRESS/SUCCESS/FAILURE)
            - submitTime: 提交时间戳
            - startTime: 开始执行时间戳
            - finishTime: 完成时间戳
            - failReason: 失败原因
            - data: 音乐片段数据 (数组)
        """
        response = self.session.get(
            f"{self.base_url}/suno/fetch/{task_id}",
            headers=self._get_headers(),
            timeout=self.timeout
        )
        response.raise_for_status()

        return response.json()

    def get_task_status_batch(self, task_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量查询任务状态

        Args:
            task_ids: 任务 ID 列表

        Returns:
            任务状态字典 {task_id: status_data}
        """
        payload = {
            "ids": task_ids
        }

        response = self.session.post(
            f"{self.base_url}/suno/fetch",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        results = {}

        for item in data.get("data", []):
            task_id = item.get("task_id", "")
            if task_id:
                results[task_id] = item

        return results

    def poll_task(self, task_id: str,
                 interval: int = 5,
                 max_wait: int = 600,
                 callback=None) -> Dict[str, Any]:
        """
        轮询任务直到完成

        Args:
            task_id: 任务 ID
            interval: 轮询间隔(秒)
            max_wait: 最大等待时间(秒)
            callback: 状态更新回调函数 callback(task_id, status, task_info)

        Returns:
            最终任务状态
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_data = self.get_task_status(task_id)

            # 解析响应
            task_info = status_data.get("data", {})
            if isinstance(task_info, list) and task_info:
                task_info = task_info[0]

            status = task_info.get("status", self.STATUS_NOT_START)

            if callback:
                callback(task_id, status, task_info)

            # 检查是否完成
            if status in (self.STATUS_SUCCESS, self.STATUS_FAILURE):
                return task_info

            # 等待后继续轮询
            time.sleep(interval)

        raise TimeoutError(f"任务轮询超时: {task_id}")

    # ==================== 批量操作 ====================

    def generate_batch(self, prompts: List[Dict[str, Any]]) -> List[str]:
        """
        批量生成音乐

        Args:
            prompts: 生成参数列表

        Returns:
            任务 ID 列表
        """
        task_ids = []

        for params in prompts:
            try:
                task_id = self.generate_music(**params)
                task_ids.append(task_id)
                # 添加延迟避免速率限制
                time.sleep(2)
            except Exception as e:
                print(f"生成音乐失败: {e}")
                task_ids.append("")

        return task_ids

    # ==================== 下载音频 ====================

    def download_audio(self, audio_url: str, save_path: Path) -> str:
        """
        下载生成的音频

        Args:
            audio_url: 音频 URL
            save_path: 保存路径

        Returns:
            保存的文件路径
        """
        save_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(audio_url, stream=True, timeout=60)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return str(save_path)

    def download_video(self, video_url: str, save_path: Path) -> str:
        """
        下载带封面的音乐视频

        Args:
            video_url: 视频 URL
            save_path: 保存路径

        Returns:
            保存的文件路径
        """
        return self.download_audio(video_url, save_path)

    # ==================== 模型和风格信息 ====================

    @staticmethod
    def get_available_models() -> Dict[str, str]:
        """获取可用模型列表"""
        return {
            'chirp-v5': 'chirp-v5 (V5.0 最新)',
            'chirp-auk': 'chirp-auk (V4.5)',
            'chirp-v4': 'chirp-v4 (V4.0 推荐)',
            'chirp-v3-5': 'chirp-v3-5 (V3.5)',
            'chirp-v3-0': 'chirp-v3-0 (V3.0)',
            'chirp-v3-5-upload': 'chirp-v3-5-upload (V3.5 上传)',
            'chirp-v3-5-tau': 'chirp-v3-5-tau (翻唱专用)',
        }

    @staticmethod
    def get_style_tags() -> List[str]:
        """获取常用风格标签"""
        return [
            # 中国风
            'chinese traditional', 'guzheng', 'pipa', 'erhu', 'dizi',
            # 情感
            'emotional', 'melancholic', 'peaceful', 'uplifting', 'romantic',
            # 流派
            'pop', 'rock', 'jazz', 'electronic', 'classical', 'folk',
            'r&b', 'hip hop', 'indie', 'country', 'reggae',
            # 氛围
            'ambient', 'cinematic', 'epic', 'dreamy', 'dark',
            # 乐器
            'acoustic', 'piano', 'guitar', 'strings', 'synthesizer',
            # 人声
            'male vocal', 'female vocal', 'choir', 'vocal harmony',
            # 速度
            'slow tempo', 'mid tempo', 'fast tempo', 'ballad',
        ]

    @staticmethod
    def get_vocal_genders() -> Dict[str, str]:
        """获取人声性别选项"""
        return {
            '': '随机',
            'm': '男声',
            'f': '女声',
        }

    @staticmethod
    def get_generation_modes() -> Dict[str, str]:
        """获取生成模式"""
        return {
            'custom': '自定义模式',
            'inspiration': '灵感模式',
            'extend': '续写模式',
            'cover': '翻唱模式',
        }

    def close(self):
        """关闭会话"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

