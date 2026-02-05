"""
历史记录侧边栏组件
显示所有历史会话，支持搜索、恢复、删除
"""
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot
from datetime import datetime

from database.manager import HistoryManager


class HistorySidebar(QWidget):
    """历史记录侧边栏"""
    
    # 信号
    session_selected = Signal(str)  # 选中会话 (session_id)
    
    def __init__(self, db_path: str = "guui_history.db"):
        super().__init__()
        
        self.history_manager = HistoryManager(db_path)
        self._init_ui()
        self._load_sessions()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("📚 历史记录")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索诗词...")
        self.search_edit.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_edit)
        
        search_btn = QPushButton("🔍")
        search_btn.setFixedWidth(40)
        search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)
        
        # 会话列表
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self._on_session_clicked)
        layout.addWidget(self.session_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("📂 恢复")
        self.restore_btn.clicked.connect(self._restore_session)
        self.restore_btn.setEnabled(False)
        btn_layout.addWidget(self.restore_btn)
        
        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.clicked.connect(self._delete_session)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.clicked.connect(self._load_sessions)
        layout.addWidget(refresh_btn)
    
    def _load_sessions(self):
        """加载所有会话"""
        self.session_list.clear()
        sessions = self.history_manager.list_sessions(limit=50)
        
        for session in sessions:
            # 创建列表项
            item = QListWidgetItem()
            item.setData(Qt.UserRole, session.id)
            
            # 格式化显示文本
            poetry_preview = session.poetry_text[:30] + "..." if len(session.poetry_text) > 30 else session.poetry_text
            poetry_preview = poetry_preview.replace('\n', ' ')
            
            time_str = session.updated_at.strftime("%Y-%m-%d %H:%M")
            
            item_text = f"{session.name or session.id[:8]}\n{poetry_preview}\n{time_str}"
            item.setText(item_text)
            
            self.session_list.addItem(item)
    
    def _on_search(self):
        """搜索会话"""
        keyword = self.search_edit.text().strip()
        
        if not keyword:
            self._load_sessions()
            return
        
        self.session_list.clear()
        sessions = self.history_manager.search_sessions(keyword)
        
        for session in sessions:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, session.id)
            
            poetry_preview = session.poetry_text[:30] + "..." if len(session.poetry_text) > 30 else session.poetry_text
            poetry_preview = poetry_preview.replace('\n', ' ')
            
            time_str = session.updated_at.strftime("%Y-%m-%d %H:%M")
            item_text = f"{session.name or session.id[:8]}\n{poetry_preview}\n{time_str}"
            item.setText(item_text)
            
            self.session_list.addItem(item)
    
    def _on_session_clicked(self, item: QListWidgetItem):
        """会话被点击"""
        self.restore_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
    
    def _restore_session(self):
        """恢复选中会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            return
        
        session_id = current_item.data(Qt.UserRole)
        self.session_selected.emit(session_id)
    
    def _delete_session(self):
        """删除选中会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            return
        
        session_id = current_item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除此会话吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.history_manager.delete_session(session_id):
                QMessageBox.information(self, "成功", "会话已删除")
                self._load_sessions()
            else:
                QMessageBox.warning(self, "错误", "删除会话失败")
    
    def add_session(self, session_id: str, name: str, poetry_text: str):
        """添加新会话（用于自动保存）"""
        try:
            self.history_manager.create_session(session_id, name, poetry_text)
            self._load_sessions()
        except Exception as e:
            print(f"添加会话失败: {e}")
