"""
图片上传工具
用于将本地图片上传到 CDN，获取 HTTP URL 供视频 API 使用
"""
import base64
import time
from typing import List, Optional
from pathlib import Path
import requests
from PIL import Image
import io


class ImageUploader:
    """
    图片上传工具

    视频 API 需要使用 HTTP URL，不支持 base64，
    因此需要先上传图片到 CDN。
    """

    def __init__(self, api_key: str, base_url: str,
                 timeout: int = 60):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _image_to_base64(self, image_path: Path) -> tuple:
        """
        将图片转换为 base64 格式

        Args:
            image_path: 图片路径

        Returns:
            (纯 base64 字符串, 带前缀的 base64 字符串)
        """
        # 读取图片
        img = Image.open(image_path)

        # 保持原始格式或转换为 PNG（避免 JPEG 有损压缩）
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        # 压缩图片以减少上传大小
        max_size = (1920, 1920)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 编码为 base64 - 使用 PNG 保持质量
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # 返回两种格式
        base64_only = image_base64
        base64_with_prefix = f"data:image/png;base64,{image_base64}"

        return base64_only, base64_with_prefix

    def upload_single(self, image_path: Path) -> str:
        """
        上传单张图片到免费图床获取 URL

        Args:
            image_path: 图片路径

        Returns:
            图片 HTTP URL
        """
        errors = []

        # 1. 尝试 imgbb（国内可访问，速度快）
        try:
            url = self._upload_to_imgbb(image_path)
            if url:
                print(f"✓ Upload success (imgbb): {url}")
                return url
        except Exception as e:
            errors.append(f"imgbb: {e}")
            print(f"✗ Imgbb upload failed: {e}")

        # 2. 备选：使用 sm.ms（中国图床）
        try:
            url = self._upload_to_smms(image_path)
            if url:
                print(f"✓ Upload success (sm.ms): {url}")
                return url
        except Exception as e:
            errors.append(f"sm.ms: {e}")
            print(f"✗ SM.MS upload failed: {e}")

        # 3. 备选：freeimage.host（国外图床，速度快）
        try:
            url = self._upload_to_freeimage(image_path)
            if url:
                print(f"✓ Upload success (freeimage): {url}")
                return url
        except Exception as e:
            errors.append(f"freeimage: {e}")
            print(f"✗ Freeimage upload failed: {e}")

        # 4. 最后尝试：catbox（可能国内慢）
        try:
            url = self._upload_to_catbox(image_path)
            if url:
                print(f"✓ Upload success (catbox): {url}")
                return url
        except Exception as e:
            errors.append(f"catbox: {e}")
            print(f"✗ Catbox upload failed: {e}")

        # 汇总所有错误
        error_summary = "\n".join(f"  - {err}" for err in errors)
        raise ValueError(
            f"所有图床均上传失败，请检查网络连接或手动输入图片 URL\n"
            f"尝试的服务:\n{error_summary}\n"
            f"建议：\n"
            f"  1. 检查网络连接\n"
            f"  2. 使用 VPN 或代理\n"
            f"  3. 在对话框中选择「手动输入图片 URL」选项"
        )
    
    def _upload_to_imgbb(self, image_path: Path) -> str:
        """上传到 imgbb.com（国内可访问）"""
        # 转换为 base64
        base64_only, _ = self._image_to_base64(image_path)

        # 使用免费 API（无需 API Key）
        response = requests.post(
            'https://api.imgbb.com/1/upload',
            data={
                'key': 'da2f59b83a95e6e0f57c4a5a2c4f3b0e',  # 公共 API Key
                'image': base64_only,
                'name': image_path.stem
            },
            timeout=60  # 增加超时时间到 60 秒
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data', {}).get('url'):
                return data['data']['url']
        return None
    
    def _upload_to_smms(self, image_path: Path) -> str:
        """上传到 sm.ms（中国图床）"""
        with open(image_path, 'rb') as f:
            files = {'smfile': (image_path.name, f)}
            headers = {'Authorization': ''}  # 匿名上传
            response = requests.post(
                'https://sm.ms/api/v2/upload',
                files=files,
                headers=headers,
                timeout=60  # 增加超时时间到 60 秒
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('url'):
                    return data['data']['url']
                # 如果图片已存在，返回已有的 URL
                if data.get('code') == 'image_repeated':
                    return data.get('images')
        return None
    
    def _upload_to_catbox(self, image_path: Path) -> str:
        """上传到 catbox.moe"""
        with open(image_path, 'rb') as f:
            files = {'fileToUpload': (image_path.name, f)}
            data = {'reqtype': 'fileupload'}
            response = requests.post(
                'https://catbox.moe/user/api.php',
                files=files,
                data=data,
                timeout=90  # catbox 可能很慢，增加到 90 秒
            )
            if response.status_code == 200 and response.text.startswith('https://'):
                return response.text.strip()
        return None

    def _upload_to_freeimage(self, image_path: Path) -> str:
        """上传到 freeimage.host（国外图床，速度快）"""
        # 转换为 base64
        base64_only, _ = self._image_to_base64(image_path)

        response = requests.post(
            'https://freeimage.host/api/1/upload',
            data={
                'key': '6d207e02198a847aa98d0a2a901485a5',  # 免费公共 API Key
                'source': base64_only,
                'format': 'json'
            },
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status_code') == 200 and data.get('image', {}).get('url'):
                return data['image']['url']
        return None

    def upload_batch(self, image_paths: List[Path],
                    delay: float = 0.5) -> List[str]:
        """
        批量上传图片

        Args:
            image_paths: 图片路径列表
            delay: 上传间隔(秒)

        Returns:
            图片 HTTP URL 列表
        """
        results = []

        for image_path in image_paths:
            try:
                url = self.upload_single(image_path)
                results.append(url)

                # 添加延迟避免速率限制
                if delay > 0 and len(results) < len(image_paths):
                    time.sleep(delay)

            except Exception as e:
                print(f"上传图片失败 {image_path}: {e}")
                results.append("")

        return results

    def upload_from_directory(self, directory: Path,
                             pattern: str = "*.png",
                             delay: float = 0.5) -> dict:
        """
        上传目录中的所有图片

        Args:
            directory: 图片目录
            pattern: 文件匹配模式
            delay: 上传间隔(秒)

        Returns:
            {文件名: URL} 字典
        """
        image_files = sorted(directory.glob(pattern))

        if not image_files:
            # 尝试其他格式
            for ext in ['*.jpg', '*.jpeg', '*.webp']:
                image_files = sorted(directory.glob(ext))
                if image_files:
                    break

        urls = self.upload_batch(image_files, delay)

        return {str(f): url for f, url in zip(image_files, urls)}

    def close(self):
        """关闭会话"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_image_url(image_path: Path,
                 api_key: str,
                 base_url: str) -> str:
    """
    便捷函数：获取图片的 HTTP URL

    Args:
        image_path: 图片路径
        api_key: API 密钥
        base_url: API 基础 URL

    Returns:
        图片 HTTP URL
    """
    with ImageUploader(api_key, base_url) as uploader:
        return uploader.upload_single(image_path)
