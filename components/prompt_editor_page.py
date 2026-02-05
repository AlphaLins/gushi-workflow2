"""
提示词编辑页面
表格形式编辑、查看、修改图像提示词
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel, QGroupBox, QMenu,
    QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction

from schemas.poetry import PoetryPromptsResponse, VersePrompts, ImagePrompt


class PromptEditorPage(QWidget):
    """
    提示词编辑页面

    功能：
    1. 表格形式展示所有提示词
    2. 支持编辑、删除
    3. 支持添加新提示词
    4. 支持导入/导出
    """

    prompts_changed = Signal(object)  # 提示词变更信号

    def __init__(self, parent=None):
        super().__init__(parent)

        self.prompts: Optional[PoetryPromptsResponse] = None

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题和工具栏
        header_layout = QHBoxLayout()

        title = QLabel("提示词编辑")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 工具按钮
        self.add_btn = QPushButton("添加提示词")
        self.add_btn.clicked.connect(self._add_prompt)
        self.add_btn.setEnabled(False)
        header_layout.addWidget(self.add_btn)

        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        header_layout.addWidget(self.delete_btn)

        self.export_btn = QPushButton("导出 JSON")
        self.export_btn.clicked.connect(self._export_json)
        self.export_btn.setEnabled(False)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["诗句", "序号", "图像提示词", "视频提示词", "长度"])

        # 设置表格属性
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        # 列宽设置
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # 支持右键菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # 双击编辑
        self.table.itemDoubleClicked.connect(self._edit_item)

        # 选中变化
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.table)

        # 底部统计信息
        self.stats_label = QLabel("无数据")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        if self.prompts is None:
            return

        menu = QMenu(self)

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self._edit_selected)
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)

        copy_action = QAction("复制提示词", self)
        copy_action.triggered.connect(self._copy_prompt)
        menu.addAction(copy_action)

        menu.exec_(self.table.mapToGlobal(pos))

    def _on_selection_changed(self):
        """选中项变化"""
        has_selection = len(self.table.selectedItems()) > 0
        self.delete_btn.setEnabled(has_selection and self.prompts is not None)

    def _edit_item(self, item: QTableWidgetItem):
        """编辑项目"""
        column = item.column()
        # 只允许编辑第2列（图像提示词）和第3列（视频提示词）
        if column not in (2, 3):
            return

        from PySide6.QtWidgets import QInputDialog

        current_text = item.text()
        title = "编辑图像提示词" if column == 2 else "编辑视频提示词"
        label = "图像提示词:" if column == 2 else "视频提示词:"
        
        new_text, ok = QInputDialog.getText(
            self,
            title,
            label,
            text=current_text
        )

        if ok:
            # 更新数据
            row = item.row()
            verse_index = self.table.item(row, 0).data(Qt.UserRole)
            prompt_index = self.table.item(row, 1).data(Qt.UserRole)

            verse = self.prompts.get_verse(verse_index)
            if verse and 0 <= prompt_index < len(verse.descriptions):
                if column == 2:
                    verse.descriptions[prompt_index].description = new_text
                else:
                    verse.descriptions[prompt_index].video_prompt = new_text

                # 更新显示
                item.setText(new_text)
                if column == 2:
                    length_item = self.table.item(row, 4)
                    length_item.setText(str(len(new_text)))

                self.prompts_changed.emit(self.prompts)

    def _edit_selected(self):
        """编辑选中项"""
        selected = self.table.selectedItems()
        if not selected:
            return

        # 找到提示词列的项目
        for item in selected:
            if item.column() == 2:
                self._edit_item(item)
                break

    def _add_prompt(self):
        """添加新提示词"""
        if self.prompts is None or not self.prompts.prompts:
            QMessageBox.warning(self, "添加失败", "请先生成提示词")
            return

        from PySide6.QtWidgets import QInputDialog, QComboBox

        # 选择诗句
        dialog = QInputDialog(self)
        dialog.setWindowTitle("选择诗句")
        dialog.setLabelText("为哪句诗添加提示词？")

        combo = QComboBox()
        for verse in self.prompts.prompts:
            combo.addItem(f"{verse.verse}", verse.index)

        dialog.setComboBox(combo)

        if dialog.exec():
            verse_index = combo.currentData()

            # 输入提示词
            new_prompt, ok = QInputDialog.getText(
                self,
                "新提示词",
                "请输入新的图像提示词 (英文):",
                minimum=20
            )

            if ok and new_prompt:
                verse = self.prompts.get_verse(verse_index)
                if verse:
                    verse.add_description(new_prompt)
                    self._refresh_table()
                    self.prompts_changed.emit(self.prompts)

    def _delete_selected(self):
        """删除选中的提示词"""
        selected = self.table.selectedItems()
        if not selected:
            return

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton

        # 创建选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除")
        layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        rows_to_delete = set()

        for item in selected:
            row = item.row()
            if row not in rows_to_delete:
                verse_item = self.table.item(row, 0)
                prompt_item = self.table.item(row, 2)
                list_widget.addItem(f"{verse_item.text()} - {prompt_item.text()[:50]}...")
                rows_to_delete.add(row)

        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        if dialog.exec():
            # 执行删除
            for row in sorted(rows_to_delete, reverse=True):
                verse_index = self.table.item(row, 0).data(Qt.UserRole)
                prompt_index = self.table.item(row, 1).data(Qt.UserRole)

                verse = self.prompts.get_verse(verse_index)
                if verse:
                    verse.remove_description(prompt_index)

            self._refresh_table()
            self.prompts_changed.emit(self.prompts)

    def _copy_prompt(self):
        """复制提示词"""
        selected = self.table.selectedItems()
        if not selected:
            return

        for item in selected:
            if item.column() == 2:
                from PySide6.QtWidgets import QApplication
                QApplication.clipboard().setText(item.text())
                QMessageBox.information(self, "复制成功", "提示词已复制到剪贴板")
                break

    def _export_json(self):
        """导出为 JSON"""
        if self.prompts is None:
            return

        from PySide6.QtWidgets import QFileDialog
        import json

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出提示词",
            "prompts.json",
            "JSON 文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.prompts.model_dump(), f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "导出成功", f"提示词已导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出失败: {str(e)}")

    def _refresh_table(self):
        """刷新表格内容"""
        self.table.setRowCount(0)

        if self.prompts is None:
            return

        row = 0
        for verse in self.prompts.prompts:
            for i, desc in enumerate(verse.descriptions):
                self.table.insertRow(row)

                # 诗句
                verse_item = QTableWidgetItem(verse.verse)
                verse_item.setData(Qt.UserRole, verse.index)
                self.table.setItem(row, 0, verse_item)

                # 序号
                index_item = QTableWidgetItem(str(i + 1))
                index_item.setData(Qt.UserRole, i)
                index_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, index_item)

                # 图像提示词
                prompt_item = QTableWidgetItem(desc.description)
                prompt_item.setFlags(prompt_item.flags() | Qt.ItemIsEditable)
                self.table.setItem(row, 2, prompt_item)

                # 视频提示词
                video_prompt = getattr(desc, 'video_prompt', '') or ''
                video_item = QTableWidgetItem(video_prompt)
                video_item.setFlags(video_item.flags() | Qt.ItemIsEditable)
                self.table.setItem(row, 3, video_item)

                # 长度
                length_item = QTableWidgetItem(str(len(desc.description)))
                length_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, length_item)

                row += 1

        # 更新统计
        total = self.prompts.total_prompts()
        verses_count = len(self.prompts.prompts)
        self.stats_label.setText(f"共 {verses_count} 句诗，{total} 个提示词")

        # 启用/禁用按钮
        has_data = self.prompts is not None and total > 0
        self.add_btn.setEnabled(has_data)
        self.delete_btn.setEnabled(False)
        self.export_btn.setEnabled(has_data)

    def set_prompts(self, prompts: PoetryPromptsResponse):
        """设置提示词数据"""
        self.prompts = prompts
        self._refresh_table()

    def get_prompts(self) -> Optional[PoetryPromptsResponse]:
        """获取当前提示词数据"""
        return self.prompts

    def all_descriptions(self) -> list:
        """获取所有提示词描述"""
        if self.prompts is None:
            return []
        return self.prompts.all_descriptions()
