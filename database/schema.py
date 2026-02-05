"""
数据库表结构定义
用于存储会话、提示词和生成结果的历史记录
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Session(Base):
    """会话表 - 存储每次创作会话"""
    __tablename__ = 'sessions'
    
    id = Column(String(64), primary_key=True)
    name = Column(String(256))
    poetry_text = Column(Text)  # 原始诗词
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    prompts = relationship("Prompt", back_populates="session", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")


class Prompt(Base):
    """提示词表 - 存储图像和视频提示词"""
    __tablename__ = 'prompts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey('sessions.id'))
    verse_index = Column(Integer)  # 诗句索引
    prompt_index = Column(Integer)  # 提示词索引
    image_prompt = Column(Text)  # 图像提示词
    video_prompt = Column(Text)  # 视频提示词
    
    # 关联
    session = relationship("Session", back_populates="prompts")


class Artifact(Base):
    """生成物表 - 存储图片和视频路径"""
    __tablename__ = 'artifacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey('sessions.id'))
    type = Column(String(16))  # 'image' 或 'video'
    file_path = Column(Text)  # 本地文件路径
    url = Column(Text, nullable=True)  # 在线URL（可选）
    verse_index = Column(Integer)
    prompt_index = Column(Integer)
    model = Column(String(64), nullable=True)  # 使用的模型
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联
    session = relationship("Session", back_populates="artifacts")


def init_database(db_path: str = "guui_history.db"):
    """初始化数据库"""
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine


def get_session_maker(engine):
    """获取 Session Maker"""
    return sessionmaker(bind=engine)
