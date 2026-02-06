"""
数据库管理器 - 提供CRUD操作
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session as DBSession

from .schema import Session, Prompt, Artifact, init_database, get_session_maker


class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self, db_path: str = "guui_history.db"):
        """
        初始化历史记录管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.engine = init_database(db_path)
        self.SessionMaker = get_session_maker(self.engine)
    
    def create_session(self, session_id: str, name: str, poetry_text: str) -> Session:
        """
        创建新会话
        
        Args:
            session_id: 会话ID
            name: 会话名称
            poetry_text: 诗词文本
            
        Returns:
            Session 对象
        """
        db_session = self.SessionMaker()
        try:
            session = Session(
                id=session_id,
                name=name,
                poetry_text=poetry_text
            )
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)
            return session
        finally:
            db_session.close()

    def update_session(self, session_id: str, name: str = None, poetry_text: str = None) -> bool:
        """
        更新会话
        
        Args:
            session_id: 会话ID
            name: 会话名称 (可选)
            poetry_text: 诗词文本 (可选)
            
        Returns:
            是否更新成功
        """
        db_session = self.SessionMaker()
        try:
            session = db_session.query(Session).filter(Session.id == session_id).first()
            if not session:
                return False
                
            if name is not None:
                session.name = name
            if poetry_text is not None:
                session.poetry_text = poetry_text
            
            session.updated_at = datetime.now()
            db_session.commit()
            return True
        finally:
            db_session.close()
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        db_session = self.SessionMaker()
        try:
            return db_session.query(Session).filter(Session.id == session_id).first()
        finally:
            db_session.close()
    
    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Session]:
        """
        获取会话列表（按更新时间倒序）
        
        Args:
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            Session 列表
        """
        db_session = self.SessionMaker()
        try:
            return db_session.query(Session)\
                .order_by(Session.updated_at.desc())\
                .limit(limit)\
                .offset(offset)\
                .all()
        finally:
            db_session.close()
    
    def search_sessions(self, keyword: str) -> List[Session]:
        """
        搜索会话（按诗词内容或名称）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的Session列表
        """
        db_session = self.SessionMaker()
        try:
            return db_session.query(Session)\
                .filter(
                    (Session.name.like(f'%{keyword}%')) |
                    (Session.poetry_text.like(f'%{keyword}%'))
                )\
                .order_by(Session.updated_at.desc())\
                .all()
        finally:
            db_session.close()
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话（级联删除相关数据）
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否删除成功
        """
        db_session = self.SessionMaker()
        try:
            session = db_session.query(Session).filter(Session.id == session_id).first()
            if session:
                db_session.delete(session)
                db_session.commit()
                return True
            return False
        finally:
            db_session.close()
    
    def save_prompts(self, session_id: str, prompts_data: List[Dict[str, Any]]):
        """
        保存提示词
        
        Args:
            session_id: 会话ID
            prompts_data: 提示词数据列表 [{'verse_index': 0, 'prompt_index': 0, 'image_prompt': '...', 'video_prompt': '...'}, ...]
        """
        db_session = self.SessionMaker()
        try:
            # 先删除旧的提示词
            db_session.query(Prompt).filter(Prompt.session_id == session_id).delete()
            
            # 保存新的
            for data in prompts_data:
                prompt = Prompt(
                    session_id=session_id,
                    verse_index=data['verse_index'],
                    prompt_index=data['prompt_index'],
                    image_prompt=data.get('image_prompt', ''),
                    video_prompt=data.get('video_prompt', '')
                )
                db_session.add(prompt)
            
            db_session.commit()
            
            # 更新会话的 updated_at
            session = db_session.query(Session).filter(Session.id == session_id).first()
            if session:
                session.updated_at = datetime.now()
                db_session.commit()
        finally:
            db_session.close()
    
    def save_artifact(self, session_id: str, artifact_type: str, file_path: str,
                     verse_index: int, prompt_index: int, url: Optional[str] = None,
                     model: Optional[str] = None):
        """
        保存生成物（图片或视频）
        
        Args:
            session_id: 会话ID
            artifact_type: 类型 'image' 或 'video'
            file_path: 文件路径
            verse_index: 诗句索引
            prompt_index: 提示词索引
            url: 在线URL（可选）
            model: 使用的模型（可选）
        """
        db_session = self.SessionMaker()
        try:
            artifact = Artifact(
                session_id=session_id,
                type=artifact_type,
                file_path=file_path,
                url=url,
                verse_index=verse_index,
                prompt_index=prompt_index,
                model=model
            )
            db_session.add(artifact)
            db_session.commit()
            
            # 更新会话的 updated_at
            session = db_session.query(Session).filter(Session.id == session_id).first()
            if session:
                session.updated_at = datetime.now()
                db_session.commit()
        finally:
            db_session.close()
    
    def get_session_artifacts(self, session_id: str, artifact_type: Optional[str] = None) -> List[Artifact]:
        """
        获取会话的所有生成物
        
        Args:
            session_id: 会话ID
            artifact_type: 类型过滤（可选）
            
        Returns:
            Artifact 列表
        """
        db_session = self.SessionMaker()
        try:
            query = db_session.query(Artifact).filter(Artifact.session_id == session_id)
            if artifact_type:
                query = query.filter(Artifact.type == artifact_type)
            return query.order_by(Artifact.verse_index, Artifact.prompt_index).all()
        finally:
            db_session.close()
    
    def get_session_prompts(self, session_id: str) -> List[Prompt]:
        """获取会话的所有提示词"""
        db_session = self.SessionMaker()
        try:
            return db_session.query(Prompt)\
                .filter(Prompt.session_id == session_id)\
                .order_by(Prompt.verse_index, Prompt.prompt_index)\
                .all()
        finally:
            db_session.close()
