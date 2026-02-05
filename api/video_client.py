"""
视频生成 API 客户端
支持 Grok, Veo, Sora 等视频模型
"""
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
import requests
from dataclasses import dataclass


class VideoClient:
    """
    视频生成客户端

    支持：
    - Grok Video: grok-video-3, grok-video-3-10s
    - Veo: veo3.1, veo3.1-fast, veo3-fast-frames
    - Sora: sora-2, sora-2-pro
    - Kling, Luma, Runway 等
    """

    def __init__(self, api_key: str, base_url: str,
                 timeout: int = 180):
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

    def _get_model_type(self, model: str) -> str:
        """获取模型类型"""
        if model.startswith('grok'):
            return 'grok'
        elif model.startswith('veo'):
            return 'veo'
        elif model.startswith('sora'):
            return 'sora'
        else:
            return 'generic'

    # ==================== 任务提交 ====================

    def submit_task(self,
                   model: str,
                   prompt: str,
                   image_urls: List[str],
                   aspect_ratio: str = "3:2",
                   size: str = "720P",
                   duration: int = 5,
                   enhance_prompt: bool = False,
                   watermark: bool = False,
                   orientation: str = "landscape") -> Dict[str, Any]:
        """
        提交视频生成任务

        Args:
            model: 视频模型名称
            prompt: 视频提示词
            image_urls: 输入图像 URL 列表
            aspect_ratio: 宽高比 (2:3, 3:2, 1:1, 16:9, 9:16)
            size: 视频分辨率 (720P, 1080P)
            duration: 视频时长(秒)
            enhance_prompt: 是否增强提示词 (Veo)
            watermark: 是否添加水印 (Sora)
            orientation: 方向 (landscape, portrait) (Sora)

        Returns:
            任务响应 {"id": "task_id", "status": "pending", ...}
        """
        model_type = self._get_model_type(model)

        if model_type == 'grok':
            payload = self._build_grok_payload(
                model, prompt, image_urls, aspect_ratio, size
            )
        elif model_type == 'veo':
            payload = self._build_veo_payload(
                model, prompt, image_urls, aspect_ratio, enhance_prompt
            )
        elif model_type == 'sora':
            payload = self._build_sora_payload(
                model, prompt, image_urls, orientation, duration, watermark
            )
        else:
            # 通用格式
            payload = self._build_generic_payload(
                model, prompt, image_urls
            )

        response = self.session.post(
            f"{self.base_url}/v1/video/create",  # URL 不包含模型名
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        return response.json()

    def _build_grok_payload(self, model: str, prompt: str,
                           image_urls: List[str], aspect_ratio: str,
                           size: str) -> Dict[str, Any]:
        """构建 Grok 视频请求 - 支持 URL 和 base64"""
        # 检查是否为 base64 格式（以 data: 开头）
        images = []
        for img in image_urls[:1]:  # Grok 通常只支持单张图片
            if img.startswith('data:'):
                # base64 格式
                images.append(img)
            elif img.startswith('http://') or img.startswith('https://'):
                # URL 格式
                images.append(img)
            else:
                # 本地文件路径，转换为 base64
                images.append(self._file_to_base64(img))
        
        return {
            "model": model,
            "prompt": f"{prompt} --mode=custom",
            "aspect_ratio": aspect_ratio,
            "size": size,
            "images": images
        }
    
    def _file_to_base64(self, file_path: str) -> str:
        """将本地图片文件转换为 base64 data URI（优化大小）"""
        import base64
        from pathlib import Path
        from PIL import Image
        import io
        
        path = Path(file_path)
        img = Image.open(path)
        
        # 转换为 RGB（JPEG 不支持 RGBA）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        elif img.mode not in ('RGB',):
            img = img.convert('RGB')
        
        # 压缩大图片 - 降低分辨率以减小 base64 大小
        max_size = (1280, 1280)  # 降低到 1280px
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 使用 JPEG 格式压缩（比 PNG 小很多）
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        image_bytes = buffer.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"Image converted to base64: {len(image_base64)} chars ({len(image_bytes) / 1024:.1f} KB)")
        
        return f"data:image/jpeg;base64,{image_base64}"

    def _build_grok_payload(self,
                            model: str,
                            prompt: str,
                            image_urls: List[str],
                            aspect_ratio: str = "3:2",
                            size: str = "720P") -> Dict[str, Any]:
        """构建 Grok 视频 payload（符合官方 API 格式）"""
        return {
            "model": model,
            "prompt": prompt,
            "images": image_urls,  # 官方字段名是 images
            "aspect_ratio": aspect_ratio,
            "size": size
        }

    def _build_veo_payload(self, model: str, prompt: str,
                          image_urls: List[str], aspect_ratio: str,
                          enhance_prompt: bool) -> Dict[str, Any]:
        """构建 Veo 视频请求"""
        return {
            "model": model,
            "images": image_urls,
            "prompt": prompt,
            "enhance_prompt": enhance_prompt,
            "aspect_ratio": aspect_ratio
        }

    def _build_sora_payload(self, model: str, prompt: str,
                           image_urls: List[str], orientation: str,
                           duration: int, watermark: bool) -> Dict[str, Any]:
        """构建 Sora 视频请求"""
        return {
            "model": model,
            "images": image_urls[:1],
            "prompt": prompt,
            "orientation": orientation,
            "duration": duration,
            "watermark": watermark
        }

    def _build_generic_payload(self, model: str, prompt: str,
                              image_urls: List[str]) -> Dict[str, Any]:
        """构建通用视频请求"""
        return {
            "model": model,
            "images": image_urls,
            "prompt": prompt
        }

    # ==================== 任务查询 ====================

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        查询任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态响应 {\"id\": \"task_id\", \"status\": \"completed\", \"video_url\": \"...\", ...}
        """
        response = self.session.get(
            f"{self.base_url}/v1/video/query",
            params={"id": task_id},
            headers=self._get_headers(),
            timeout=self.timeout
        )
        response.raise_for_status()

        return response.json()

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
            callback: 状态更新回调函数

        Returns:
            最终任务状态
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_data = self.get_task_status(task_id)
            status = status_data.get("status", "unknown")

            if callback:
                callback(task_id, status, status_data)

            # 检查是否完成
            if status in ("completed", "failed", "cancelled"):
                return status_data

            # 等待后继续轮询
            time.sleep(interval)

        raise TimeoutError(f"任务轮询超时: {task_id}")

    # ==================== 批量操作 ====================

    def submit_batch(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量提交任务

        Args:
            tasks: 任务参数列表

        Returns:
            任务响应列表
        """
        results = []
        for task_params in tasks:
            try:
                result = self.submit_task(**task_params)
                results.append(result)
                # 添加延迟避免速率限制
                time.sleep(1)
            except Exception as e:
                print(f"提交任务失败: {e}")
                results.append({"error": str(e)})

        return results

    def poll_batch(self, task_ids: List[str],
                  interval: int = 5,
                  max_wait: int = 600,
                  callback=None) -> Dict[str, Dict[str, Any]]:
        """
        批量轮询任务

        Args:
            task_ids: 任务 ID 列表
            interval: 轮询间隔(秒)
            max_wait: 最大等待时间(秒)
            callback: 状态更新回调函数

        Returns:
            任务状态字典 {task_id: status_data}
        """
        results = {}
        pending_tasks = task_ids.copy()
        start_time = time.time()

        while pending_tasks and time.time() - start_time < max_wait:
            for task_id in pending_tasks.copy():
                try:
                    status_data = self.get_task_status(task_id)
                    status = status_data.get("status", "unknown")

                    if callback:
                        callback(task_id, status, status_data)

                    results[task_id] = status_data

                    # 移除已完成的任务
                    if status in ("completed", "failed", "cancelled"):
                        pending_tasks.remove(task_id)

                except Exception as e:
                    print(f"查询任务失败 {task_id}: {e}")
                    results[task_id] = {"error": str(e)}
                    pending_tasks.remove(task_id)

            # 等待后继续轮询
            if pending_tasks:
                time.sleep(interval)

        return results

    # ==================== 下载视频 ====================

    def download_video(self, video_url: str, save_path: Path) -> str:
        """
        下载生成的视频

        Args:
            video_url: 视频 URL
            save_path: 保存路径

        Returns:
            保存的文件路径
        """
        save_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return str(save_path)

    def close(self):
        """关闭会话"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


@dataclass
class VideoTaskInfo:
    """视频任务信息"""
    task_id: str
    status: str
    verse_index: int = 0
    prompt_index: int = 0
    source_image: str = ""
    video_url: str = ""
    duration: float = 0.0
    error: str = ""
