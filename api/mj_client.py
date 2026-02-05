"""
Midjourney API 客户端
支持图片上传、Imagine、Action 操作
"""
import base64
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
import requests


@dataclass
class MJButton:
    """MJ 操作按钮"""
    custom_id: str      # 如 "MJ::JOB::upsample::1::xxxxx"
    label: str          # 如 "U1", "V1"
    emoji: str = ""     # 如 "🔄"
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.label:
            return self.label
        return self.emoji or self.custom_id[:20]
    
    @property
    def action_type(self) -> str:
        """操作类型"""
        if "upsample" in self.custom_id.lower():
            return "upscale"
        elif "variation" in self.custom_id.lower():
            return "variation"
        elif "reroll" in self.custom_id.lower():
            return "reroll"
        elif "pan" in self.custom_id.lower():
            return "pan"
        elif "zoom" in self.custom_id.lower():
            return "zoom"
        return "unknown"


@dataclass
class MJTaskResult:
    """MJ 任务结果"""
    task_id: str
    action: str = ""
    status: str = ""        # IN_PROGRESS, SUCCESS, FAILURE, NOT_START
    progress: str = "0%"
    image_url: str = ""
    prompt: str = ""
    fail_reason: str = ""
    buttons: List[MJButton] = field(default_factory=list)
    
    @property
    def is_completed(self) -> bool:
        return self.status == "SUCCESS"
    
    @property
    def is_failed(self) -> bool:
        return self.status == "FAILURE"
    
    @property
    def is_running(self) -> bool:
        return self.status in ("IN_PROGRESS", "SUBMITTED", "NOT_START")


class MidjourneyClient:
    """
    Midjourney API 客户端
    
    支持功能：
    - 上传图片到 Discord
    - 提交 Imagine 任务（带垫图）
    - 执行 Action（U/V/重绘等）
    - 查询任务状态
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.ephone.ai",
        timeout: int = 120
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.timeout
        
        response = self.session.request(
            method=method,
            url=url,
            headers=self._get_headers(),
            json=json_data,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    
    def upload_image(self, image_path: Path) -> str:
        """
        上传图片到 Midjourney Discord
        
        Args:
            image_path: 图片路径
            
        Returns:
            上传后的图片 URL
        """
        # 读取图片并转换为 base64
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 检测图片类型
        suffix = image_path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            mime_type = "image/jpeg"
        elif suffix == ".png":
            mime_type = "image/png"
        elif suffix == ".webp":
            mime_type = "image/webp"
        elif suffix == ".gif":
            mime_type = "image/gif"
        else:
            mime_type = "image/png"
        
        base64_str = f"data:{mime_type};base64,{base64.b64encode(image_data).decode()}"
        
        data = {
            "base64Array": [base64_str]
        }
        
        result = self._make_request("POST", "/mj/submit/upload-discord-images", data)
        
        # 返回第一个上传的图片 URL
        # API 返回格式: {'code': 1, 'description': 'success', 'result': [url]}
        if isinstance(result, dict):
            if "result" in result:
                res = result["result"]
                if isinstance(res, list) and len(res) > 0:
                    return res[0]
                elif isinstance(res, str):
                    return res
            elif "url" in result:
                return result["url"]
        elif isinstance(result, list) and len(result) > 0:
            return result[0]
        elif isinstance(result, str):
            return result
        
        raise ValueError(f"上传图片失败: {result}")
    
    def submit_imagine(
        self,
        prompt: str,
        ref_images: Optional[List[str]] = None,
        bot_type: str = "MID_JOURNEY"
    ) -> str:
        """
        提交 Imagine 任务
        
        Args:
            prompt: 提示词
            ref_images: 垫图 URL 或 base64 列表
            bot_type: MID_JOURNEY 或 NIJI_JOURNEY
            
        Returns:
            任务 ID
        """
        data = {
            "prompt": prompt,
            "botType": bot_type
        }
        
        if ref_images:
            data["base64Array"] = ref_images
        
        result = self._make_request("POST", "/mj/submit/imagine", data)
        
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        elif isinstance(result, str):
            return result
        
        raise ValueError(f"提交 Imagine 任务失败: {result}")
    
    def submit_action(
        self,
        task_id: str,
        custom_id: str
    ) -> str:
        """
        执行 Action 操作
        
        Args:
            task_id: 原任务 ID
            custom_id: 按钮的 customId
            
        Returns:
            新任务 ID
        """
        data = {
            "taskId": task_id,
            "customId": custom_id
        }
        
        result = self._make_request("POST", "/mj/submit/action", data)
        
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        elif isinstance(result, str):
            return result
        
        raise ValueError(f"执行 Action 失败: {result}")
    
    def fetch_task(self, task_id: str) -> MJTaskResult:
        """
        查询任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务结果
        """
        result = self._make_request("GET", f"/mj/task/{task_id}/fetch")
        
        # 解析按钮
        buttons = []
        if "buttons" in result and result["buttons"]:
            for btn in result["buttons"]:
                buttons.append(MJButton(
                    custom_id=btn.get("customId", ""),
                    label=btn.get("label", ""),
                    emoji=btn.get("emoji", "")
                ))
        
        return MJTaskResult(
            task_id=result.get("id", task_id),
            action=result.get("action", ""),
            status=result.get("status", ""),
            progress=result.get("progress", "0%"),
            image_url=result.get("imageUrl", ""),
            prompt=result.get("prompt", ""),
            fail_reason=result.get("failReason", ""),
            buttons=buttons
        )
    
    def wait_for_completion(
        self,
        task_id: str,
        timeout: int = 600,
        poll_interval: int = 5,
        progress_callback=None
    ) -> MJTaskResult:
        """
        轮询等待任务完成
        
        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
            progress_callback: 进度回调 callback(progress: str, status: str)
            
        Returns:
            任务结果
        """
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"任务超时: {task_id}")
            
            result = self.fetch_task(task_id)
            
            if progress_callback:
                progress_callback(result.progress, result.status)
            
            if result.is_completed:
                return result
            
            if result.is_failed:
                raise RuntimeError(f"任务失败: {result.fail_reason}")
            
            time.sleep(poll_interval)
    
    def submit_blend(
        self,
        images: List[str],
        dimensions: str = "SQUARE"
    ) -> str:
        """
        提交 Blend 融合任务
        
        Args:
            images: 2-5 张图片的 base64 或 URL
            dimensions: PORTRAIT(2:3), SQUARE(1:1), LANDSCAPE(3:2)
            
        Returns:
            任务 ID
        """
        if len(images) < 2 or len(images) > 5:
            raise ValueError("Blend 需要 2-5 张图片")
        
        data = {
            "base64Array": images,
            "dimensions": dimensions
        }
        
        result = self._make_request("POST", "/mj/submit/blend", data)
        
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        
        raise ValueError(f"提交 Blend 任务失败: {result}")
    
    def submit_describe(self, image: str) -> str:
        """
        提交 Describe 任务（图转文）
        
        Args:
            image: 图片 base64 或 URL
            
        Returns:
            任务 ID
        """
        data = {
            "base64": image
        }
        
        result = self._make_request("POST", "/mj/submit/describe", data)
        
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        
        raise ValueError(f"提交 Describe 任务失败: {result}")
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
