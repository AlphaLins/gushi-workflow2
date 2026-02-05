# 诗韵画境 (Poetry to Image)

将中国古典诗词转化为图像、视频和音乐的 AI 创作平台。

## 功能特性

- **诗词输入**: 输入中国古典诗词，自动解析诗句
- **提示词生成**: 基于 AI 为每句诗生成多个图像提示词
- **提示词编辑**: 表格形式编辑、查看、修改提示词
- **图像生成**: 批量生成高质量图像，支持失败重试
- **视频生成**: 从图像生成动画视频，支持多种模型
- **音乐生成**: 生成与诗词氛围匹配的背景音乐

## 技术栈

- **Python**: 3.11+
- **GUI**: PySide6 (Qt 6)
- **数据验证**: Pydantic
- **HTTP 客户端**: Requests
- **图像处理**: Pillow

## 目录结构

```
Guui_software/
├── main.py                 # 主入口文件
├── requirements.txt        # 依赖配置
├── api/                    # API 客户端模块
│   ├── client.py          # 统一 LLM/图像客户端
│   ├── video_client.py    # 视频生成客户端
│   ├── suno_client.py     # 音乐生成客户端
│   └── image_uploader.py  # 图片上传工具
├── schemas/               # 数据模型
│   ├── poetry.py          # 诗词提示词模型
│   ├── video_task.py      # 视频任务模型
│   └── music.py           # 音乐任务模型
├── utils/                 # 工具模块
│   ├── file_manager.py    # 文件管理
│   ├── style_anchor.py    # 风格锚定系统
│   └── logger.py          # 日志工具
├── components/            # GUI 组件
│   ├── settings_panel.py      # 设置面板
│   ├── poetry_input_page.py   # 诗词输入页面
│   ├── prompt_editor_page.py  # 提示词编辑页面
│   ├── image_gallery_page.py  # 图像生成页面
│   ├── video_queue_page.py    # 视频队列页面
│   └── music_generation_page.py # 音乐生成页面
├── core/                  # 核心模块
│   ├── app.py             # 应用程序核心类
│   └── main_window.py     # 主窗口
└── config/                # 配置模块
    └── api_config.py      # API 配置和模型列表
```

## 安装

1. 克隆项目：
```bash
git clone <repository-url>
cd Guui_software
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用

1. 运行应用：
```bash
python main.py
```

2. 在设置面板中配置 API Key

3. 输入诗词，解析诗句，生成提示词

4. 生成图像，然后可以进一步生成视频和音乐

## 配置

API 配置文件位于 `~/.guui_config.json`，首次运行后会自动创建。

可配置项：
- API Key
- Base URL
- 模型选择（文本、图像、视频、音乐）
- 生成参数（温度、重试次数等）

## 设计原则

本项目遵循以下软件工程原则：

- **SOLID**: 单一职责、开放封闭、里氏替换、接口隔离、依赖倒置
- **KISS**: 保持简单，避免不必要的复杂性
- **DRY**: 避免代码重复
- **YAGNI**: 只实现当前需要的功能

## 许可证

MIT License
