"""
统一 API 客户端 - 支持 LLM 聊天和图像生成
遵循 SOLID 原则：单一职责，通过依赖注入实现解耦
"""
import base64
import re
import time
import random
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import requests
from PIL import Image
import io


class UnifiedClient:
    """
    统一 API 客户端
    支持 OpenAI 兼容格式和 Gemini 原生格式
    """

    def __init__(self, api_key: str, base_url: str,
                 model: str = "gemini-2.5-flash",
                 image_model: str = "gemini-3-pro-image-preview",
                 use_native_google: bool = False,
                 max_retries: int = 5,
                 timeout: int = 120,
                 temperature: float = 0.7,
                 top_p: float = 0.9):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.image_model = image_model
        self.use_native_google = use_native_google
        self.max_retries = max_retries
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _is_gemini_model(self, model: Optional[str] = None) -> bool:
        """检查是否为 Gemini 模型"""
        model_name = model or self.model
        return model_name.startswith('gemini-')

    def _retry_with_backoff(self, func, max_retries: Optional[int] = None):
        """指数退避重试机制"""
        max_retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # 检查是否为可重试的错误
                is_rate_limit = "429" in error_str or "rate limit" in error_str
                is_server_error = any(code in error_str for code in ["500", "502", "503", "504"])
                is_timeout = "timeout" in error_str

                if is_rate_limit or is_server_error or is_timeout:
                    multiplier = 3 if is_rate_limit else 2
                    sleep_time = (3 * (multiplier ** attempt)) + random.uniform(0, 2)
                    print(f"请求失败，{sleep_time:.1f}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(sleep_time)
                else:
                    raise

        raise last_error

    # ==================== LLM 聊天接口 ====================

    def chat(self,
             messages: List[Dict[str, str]],
             system_prompt: Optional[str] = None,
             model: Optional[str] = None,
             temperature: Optional[float] = None,
             top_p: Optional[float] = None,
             stream: bool = False) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词
            model: 模型名称
            temperature: 温度参数
            top_p: Top-p 参数
            stream: 是否流式返回

        Returns:
            模型响应文本
        """

        def _do_request():
            model_name = model or self.model

            if self._is_gemini_model(model_name):
                return self._chat_gemini_native(messages, system_prompt, model_name,
                                               temperature, top_p)
            else:
                return self._chat_openai_compatible(messages, system_prompt, model_name,
                                                   temperature, top_p)

        return self._retry_with_backoff(_do_request)

    def _chat_openai_compatible(self,
                                messages: List[Dict[str, str]],
                                system_prompt: Optional[str],
                                model: str,
                                temperature: Optional[float],
                                top_p: Optional[float]) -> str:
        """OpenAI 兼容格式聊天"""
        # 如果有系统提示词，添加到消息开头
        request_messages = messages.copy()
        if system_prompt:
            request_messages.insert(0, {"role": "system", "content": system_prompt})

        payload = {
            "model": model,
            "messages": request_messages,
            "temperature": temperature or self.temperature,
            "top_p": top_p or self.top_p,
            "stream": False
        }

        response = self.session.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _chat_gemini_native(self,
                           messages: List[Dict[str, str]],
                           system_prompt: Optional[str],
                           model: str,
                           temperature: Optional[float],
                           top_p: Optional[float]) -> str:
        """Gemini 原生格式聊天"""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else msg["role"]
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {"contents": contents}

        if temperature or top_p:
            payload["generationConfig"] = {
                "temperature": temperature or self.temperature,
                "topP": top_p or self.top_p
            }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        response = self.session.post(
            f"{self.base_url}/v1beta/models/{model}:generateContent",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    # ==================== 图像生成接口 ====================

    def generate_image(self,
                      prompt: str,
                      model: Optional[str] = None,
                      save_path: Optional[Path] = None) -> str:
        """
        生成图像

        Args:
            prompt: 图像提示词
            model: 图像模型
            save_path: 保存路径

        Returns:
            图像保存路径或 URL
        """

        def _do_request():
            model_name = model or self.image_model

            if self._is_gemini_model(model_name):
                return self._generate_image_gemini(prompt, model_name, save_path)
            else:
                return self._generate_image_chat(prompt, model_name, save_path)

        return self._retry_with_backoff(_do_request)

    def _generate_image_gemini(self,
                              prompt: str,
                              model: str,
                              save_path: Optional[Path]) -> str:
        """Gemini 图像生成（返回 base64）"""
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        # 使用正确的端点格式
        endpoint = f"{self.base_url}/v1beta/models/{model}:generateContent"
        print(f"Image generation endpoint: {endpoint}")
        print(f"Model: {model}")

        response = self.session.post(
            endpoint,
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        print(f"Response keys: {list(data.keys())}")

        # 尝试多种响应格式解析
        image_base64 = None
        error_detail = None

        # 方式1: 标准 Gemini 格式
        try:
            inline_data = data["candidates"][0]["content"]["parts"][0]["inlineData"]
            image_base64 = inline_data["data"]
            print("Found image using standard format")
        except (KeyError, IndexError, TypeError) as e:
            error_detail = f"Standard format failed: {e}"
            # 不是错误，只是第一种格式不匹配，继续尝试其他格式

        # 方式2: 尝试从所有 parts 中查找
        if image_base64 is None:
            try:
                candidates = data.get("candidates", [])
                print(f"Searching in {len(candidates)} candidates")
                for idx, candidate in enumerate(candidates):
                    parts = candidate.get("content", {}).get("parts", [])
                    print(f"  Candidate {idx} has {len(parts)} parts")
                    for part_idx, part in enumerate(parts):
                        print(f"    Part {part_idx} keys: {list(part.keys())}")
                        if "inlineData" in part:
                            image_base64 = part["inlineData"]["data"]
                            print(f"    Found inlineData in part {part_idx}")
                            break
                    if image_base64:
                        break
            except Exception as e:
                error_detail = f"Parts search failed: {e}"
                print(f"Parts search error: {e}")

        # 方式3: 检查是否为错误响应
        if image_base64 is None:
            if "error" in data:
                error_msg = data.get("error", {})
                if isinstance(error_msg, dict):
                    error_detail = f"API Error: {error_msg.get('message', error_msg)}"
                else:
                    error_detail = f"API Error: {error_msg}"
            else:
                error_detail = f"Cannot parse image from response. Keys: {list(data.keys())}"

        # 如果仍然没有找到图像数据
        if image_base64 is None:
            raise ValueError(f"Gemini image generation failed: {error_detail}. Response: {str(data)[:500]}")

        # 解码并保存图像
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            raise ValueError(f"Failed to decode image data: {e}")

        if save_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = Path("generated_images") / f"image_{timestamp}.png"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(save_path)

        return str(save_path)

    def _generate_image_chat(self,
                            prompt: str,
                            model: str,
                            save_path: Optional[Path]) -> str:
        """其他模型图像生成（返回 Markdown URL）"""
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": f"Generate an image: {prompt}"}
            ],
            "temperature": 0.7
        }

        print(f"Chat image generation - Model: {model}")
        print(f"Endpoint: {self.base_url}/v1/chat/completions")

        response = self.session.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self._get_headers(),
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        print(f"Response content type: {type(content)}")
        print(f"Response content: {content[:200]}...")

        # 从 Markdown 中提取图像 URL
        url_pattern = r'!\[.*?\]\((https?://[^\)]+)\)'
        urls = re.findall(url_pattern, content)

        if not urls:
            # 尝试直接从内容中提取 URL
            url_pattern2 = r'(https?://[^\s]+\.(?:png|jpg|jpeg|webp)[^\s]*)'
            urls = re.findall(url_pattern2, content)

        if not urls:
            raise ValueError(f"无法从响应中提取图像 URL. 响应内容: {content[:500]}...")

        image_url = urls[0]
        print(f"Found image URL: {image_url}")

        # 下载并保存图像
        if save_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = Path("generated_images") / f"image_{timestamp}.png"

        save_path.parent.mkdir(parents=True, exist_ok=True)

        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(img_response.content)

        return str(save_path)

    def generate_images_batch(self,
                             prompts: List[str],
                             model: Optional[str] = None,
                             output_dir: Optional[Path] = None,
                             delay: float = 2.0) -> List[str]:
        """
        批量生成图像

        Args:
            prompts: 图像提示词列表
            model: 图像模型
            output_dir: 输出目录
            delay: 请求间隔（秒）

        Returns:
            图像保存路径列表
        """
        if output_dir is None:
            output_dir = Path("generated_images")
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for i, prompt in enumerate(prompts):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = output_dir / f"image_{timestamp}_{i}.png"

            try:
                result_path = self.generate_image(prompt, model, save_path)
                results.append(result_path)

                # 添加延迟避免速率限制
                if i < len(prompts) - 1:
                    time.sleep(delay)

            except Exception as e:
                print(f"生成图像失败 ({i+1}/{len(prompts)}): {e}")
                results.append(None)

        return results

    def close(self):
        """关闭会话"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
