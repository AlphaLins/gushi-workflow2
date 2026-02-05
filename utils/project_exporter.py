"""
项目导出工具
将整个会话导出为完整项目包（诗词、提示词、图片、视频）
"""
import json
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
import zipfile

from database.manager import HistoryManager


class ProjectExporter:
    """项目导出器"""
    
    def __init__(self, history_manager: HistoryManager):
        self.history_manager = history_manager
    
    def export_session(self, session_id: str, output_dir: Path) -> Path:
        """
        导出会话为完整项目
        
        Args:
            session_id: 会话ID
            output_dir: 输出目录
            
        Returns:
            导出的文件夹路径
        """
        # 获取会话数据
        session = self.history_manager.get_session(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 创建导出文件夹
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"poetry_project_{session_id[:8]}_{timestamp}"
        export_path = output_dir / export_name
        export_path.mkdir(parents=True, exist_ok=True)
        
        # 1. 保存诗词原文
        poetry_file = export_path / "poetry.txt"
        poetry_file.write_text(session.poetry_text, encoding="utf-8")
        
        # 2. 保存提示词
        prompts = self.history_manager.get_session_prompts(session_id)
        prompts_data = []
        for p in prompts:
            prompts_data.append({
                "verse_index": p.verse_index,
                "prompt_index": p.prompt_index,
                "image_prompt": p.image_prompt,
                "video_prompt": p.video_prompt
            })
        
        prompts_file = export_path / "prompts.json"
        prompts_file.write_text(json.dumps(prompts_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # 3. 复制图片和视频
        artifacts = self.history_manager.get_session_artifacts(session_id)
        
        images_dir = export_path / "images"
        videos_dir = export_path / "videos"
        images_dir.mkdir(exist_ok=True)
        videos_dir.mkdir(exist_ok=True)
        
        metadata = {
            "session_id": session_id,
            "session_name": session.name,
            "created_at": session.created_at.isoformat(),
            "export_time": datetime.now().isoformat(),
            "images": [],
            "videos": []
        }
        
        for artifact in artifacts:
            src_path = Path(artifact.file_path)
            if not src_path.exists():
                continue
            
            if artifact.type == "image":
                dest_path = images_dir / src_path.name
                shutil.copy2(src_path, dest_path)
                metadata["images"].append({
                    "filename": src_path.name,
                    "verse_index": artifact.verse_index,
                    "prompt_index": artifact.prompt_index,
                    "model": artifact.model,
                    "url": artifact.url
                })
            elif artifact.type == "video":
                dest_path = videos_dir / src_path.name
                shutil.copy2(src_path, dest_path)
                metadata["videos"].append({
                    "filename": src_path.name,
                    "verse_index": artifact.verse_index,
                    "prompt_index": artifact.prompt_index,
                    "model": artifact.model,
                    "url": artifact.url
                })
        
        # 4. 保存元数据
        metadata_file = export_path / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # 5. 生成 README
        readme = f"""# {session.name or '诗韵画境项目'}

## 项目信息

- 会话ID: {session_id}
- 创建时间: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- 导出时间: {metadata['export_time']}

## 目录结构

```
{export_name}/
├── poetry.txt          # 原始诗词
├── prompts.json        # 所有提示词
├── images/             # 生成的图片
├── videos/             # 生成的视频
├── metadata.json       # 元数据
└── README.md           # 本文件
```

## 诗词内容

{session.poetry_text}

## 统计信息

- 图片数量: {len(metadata['images'])}
- 视频数量: {len(metadata['videos'])}
- 提示词数量: {len(prompts_data)}

---

导出自「诗韵画境」应用
"""
        
        readme_file = export_path / "README.md"
        readme_file.write_text(readme, encoding="utf-8")
        
        return export_path
    
    def export_as_zip(self, session_id: str, output_path: Path) -> Path:
        """
        导出为 ZIP 文件
        
        Args:
            session_id: 会话ID
            output_path: ZIP文件输出路径
            
        Returns:
            ZIP文件路径
        """
        import tempfile
        
        # 先导出到临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = self.export_session(session_id, Path(temp_dir))
            
            # 打包为 ZIP
            zip_path = output_path.with_suffix('.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in export_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(export_path.parent)
                        zipf.write(file_path, arcname)
            
            return zip_path
