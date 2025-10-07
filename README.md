# LLM-V-Trans | 基于视觉语言模型（VLM）的图像翻译器

[简体中文](./README.md) | [English](./README_en.md)

一个功能强大的本地图像翻译工具，提供**命令行**、**网页界面**和**独立窗口应用**三种使用方式。利用先进的视觉语言模型（VLM）实现对图片内文字的精准识别、翻译和无缝替换。告别传统OCR+翻译的繁琐流程，VLM一步到位，效果更佳。

| 原图 | 翻译结果 |
|------|----------|
| ![原图](https://github.com/jedzqer/LLM-image-translator/blob/master/input/test.jpeg) | ![翻译结果](https://github.com/jedzqer/LLM-image-translator/blob/master/output/test.jpeg) |

## ✨ 核心特性

- **🚀 一步到位**: 直接调用视觉语言模型（如 Qwen-VL），在一个步骤内完成OCR识别和文本翻译，上下文理解更准。
- **🎨 智能美化**: 自动在原文位置上生成与周围背景色融为一体的半透明图层，覆盖原文，观感自然。
- **🌗 自动配色**: 智能判断背景亮度，为译文选择高对比度的颜色（黑或白），保证可读性。
- **📐 归一化坐标**: 支持归一化坐标模式，解决部分API供应商压缩图片分辨率导致坐标不匹配的问题。
- **⚙️ 高度可配置**: 所有关键参数（API密钥、模型、Prompt、字体、样式等）均可通过 `config.ini` 文件轻松配置，无需修改代码。
- **🗣️ 清晰日志**: 使用彩色日志输出，清晰展示程序运行的每一个步骤，便于调试和追踪。
- **🖥️ 三模使用**: 支持命令行批量处理、网页界面单张处理和独立窗口应用三种使用方式。
- **🎯 现代化界面**: NiceGUI版本提供原生窗口体验，支持实时预览、键盘快捷键和响应式设计。
- **⚡ 异步处理**: 非阻塞的翻译任务处理，保持界面响应流畅。

## 📖 工作流程

1.  **加载配置**: 程序启动，读取 `config.ini` 中的设置。
2.  **API请求**: 将图片编码后连同指定的 Prompt 发送给 VLM API。
3.  **解析响应**: VLM 返回包含译文和对应原文坐标的 JSON 数据。
4.  **图像绘制**:
    - 在原图上创建一个新的绘制层。
    - 根据坐标，在每个文本区域绘制一个与背景色相似的半透明矩形，以遮盖原文。
    - 动态计算最佳字体大小和换行方式，将译文居中绘制在矩形上。
5.  **保存结果**: 将绘制层与原图合并，生成最终的翻译图片。

## 🛠️ 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/jedzqer/LLM-image-translator.git
cd LLM-image-translator
```

### 2. 进行配置

项目根目录下应该有一个 `config.ini.example` 文件，你可以复制文件为config.ini并进行配置。如果没有，请根据下面的模板创建一个，或者将代码中的 `config_file = 'config.ini'` 改为您自己的配置文件名。

```ini
# config.ini
[Translator]
# 你的API密钥，例如 SiliconFlow, OpenAI, or other compatible services
api_key = None
# API的接入点地址
api_base = https://api.siliconflow.cn
# 使用的视觉语言模型名称
model_name = Qwen/Qwen2.5-VL-32B-Instruct
# 发送给模型的指令 (Prompt)。可以根据需求修改，但务必保留JSON格式的要求
model_prompt = """你是一个专业OCR引擎。严格按以下要求处理图像：
1. 识别图中所有英文文字并翻译成中文输出
2. 为每个文字区域输出检测框坐标
3. 输出格式：每行一个JSON对象
{
  "text": "译文", 
  "box": [x_min, y_min, x_max, y_max]
}

请仔细识别图片中的外语，准确翻译并提供精确的边界框像素化坐标。只许回复json对象，不要注释"""

[Image]
# 译文背景的透明度 (0-255, 0为全透明, 255为不透明)
text_box_transparency = 180
# 背景色取样后，对其进行的颜色调整强度（数值越大，与原背景色差异越大）
background_discoloration_strength = 40
# 从文本框边缘向外扩展多少像素来取样背景色
background_sample_margin = 10
# 绘制译文所用的字体文件路径
font_path = font/font.ttf
# 是否使用归一化坐标模式 (True/False)
# 启用后，将强制使用归一化坐标(0-1范围)处理文本位置
# 适用于某些压缩图片分辨率的API供应商
normalize_coordinates = False
```

**重要**:
- 打开 `config.ini` 文件。
- 在 `[Translator]` 部分填入你的 `api_key`。
- 确保 `[Image]` 部分的 `font_path` 指向一个有效的中文字体文件。程序会自动创建 `font` 文件夹，你需要将字体文件（如 `font.ttf`）放入其中。
- 如果发现翻译结果位置不正确，可以尝试将 `normalize_coordinates` 设置为 `True`。

### 3. 使用方式

#### 方式一：独立窗口应用（推荐用于单张图片处理）

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python run_nicegui_app.py
```

**特性**:
- 独立窗口应用，提供原生窗口体验
- 左侧控制面板 + 右侧图片预览的现代化布局
- 实时预览原图和翻译结果，支持标签切换
- 键盘快捷键支持：Ctrl+T翻译、Ctrl+R重置、Ctrl+S保存
- 异步处理，保持界面响应流畅

#### 方式二：网页界面

```bash
python app.py
```

访问 `http://localhost:7860` 即可使用网页界面。

#### 方式三：命令行批量处理

```bash
# 将图片放入 input 文件夹后运行
python LLMtranslator.py
```

处理后的图片将保存在 `output` 文件夹中。

## 📁 项目结构

```
LLM-image-translator/
├── app.py                 # Gradio网页界面
├── nicegui_app.py         # NiceGUI主应用文件
├── run_nicegui_app.py     # NiceGUI启动脚本
├── LLMtranslator.py       # 核心翻译模块
├── config.ini.example     # 配置文件模板
├── requirements.txt       # 依赖列表
├── README.md             # 说明文档
├── README_en.md          # 英文说明文档
├── input/                # 输入图片目录（命令行模式）
├── output/               # 输出图片目录
└── font/                 # 字体文件目录
```

## ⚙️ 详细配置说明

### API配置（Translator部分）

- `api_key`: 必须设置，支持 SiliconFlow 等兼容 OpenAI API 的服务
- `model_name`: 推荐使用支持视觉任务的模型，如 Qwen-VL 系列
- `model_prompt`: 可自定义指令，但需保持JSON输出格式要求

### 图像样式配置（Image部分）

- `text_box_transparency`: 译文背景透明度（0-255）
- `background_discoloration_strength`: 背景色调整强度
- `background_sample_margin`: 背景色取样边距
- `font_path`: 中文字体文件路径
- `normalize_coordinates`: 归一化坐标模式开关

## 🎯 使用指南

### 基本操作流程（NiceGUI版本）

1. **上传图片**: 点击"选择或拖拽图片文件"上传包含文字的图片
2. **检查配置**: 确认配置文件路径正确，API密钥已设置
3. **选择模式**: 根据需要选择是否启用归一化坐标模式
4. **开始翻译**: 点击"开始翻译"按钮或使用快捷键 Ctrl+T 启动翻译过程
5. **查看结果**: 在右侧标签页中切换查看原图和翻译结果
6. **保存结果**: 点击"保存结果"或使用快捷键 Ctrl+S 将翻译后的图片保存到output文件夹

### 键盘快捷键（NiceGUI版本）

- **Ctrl + T**: 开始翻译（需要已上传图片）
- **Ctrl + R**: 重置应用状态
- **Ctrl + S**: 保存翻译结果（需要翻译完成）

### 归一化坐标模式

- **启用时机**: 当翻译结果位置不正确时
- **适用场景**: 某些API供应商会压缩图片分辨率，导致坐标不匹配
- **效果**: 将坐标按比例缩放到正确位置

## ⚠️ 注意事项

1. **API密钥**: 使用前务必在 `config.ini` 中配置有效的 API 密钥
2. **字体文件**: 确保 `font/font.ttf` 文件存在，否则使用系统默认字体
3. **图片格式**: 支持 JPG、PNG、JPEG、BMP、GIF 等常见格式
4. **网络连接**: 需要稳定的网络连接以调用 VLM API

## 🔧 故障排除

### 常见问题

**Q: 运行时报错 "配置文件无法读取"**
A: 确保 `config.ini` 文件存在于项目根目录

**Q: 翻译失败，提示API密钥错误**
A: 检查 `config.ini` 中的 `api_key` 是否已正确设置

**Q: 网页界面无法访问**
A: 检查 7860 端口是否被占用，或尝试修改 `app.py` 中的端口设置

**Q: 译文显示异常**
A: 检查字体文件是否存在，或调整 `config.ini` 中的字体大小相关参数

**Q: 翻译位置不准确**
A: 启用归一化坐标模式

**Q: 快捷键不生效（NiceGUI版本）**
A: 确保应用窗口处于激活状态，快捷键仅在应用窗口内有效

**Q: 依赖安装失败**
A: 使用 `pip install -r requirements.txt` 安装所有依赖

### 日志查看

应用会在控制台输出详细的处理日志，包括:
- 配置加载状态
- 图片处理进度
- API调用结果
- 错误信息

## 🛠️ 开发说明

### 技术栈

- **前端框架**: NiceGUI (基于Vue.js) / Gradio
- **后端语言**: Python 3.8+
- **图片处理**: Pillow (PIL)
- **API调用**: requests
- **配置管理**: configparser
- **样式框架**: Tailwind CSS (通过NiceGUI集成)

### 核心模块

应用基于 `LLMtranslator.py` 模块，通过 `process_image_translation` 函数进行集成。

### 扩展开发

如需添加新功能，可以:
1. 在 `ImageTranslatorApp` 类中添加新方法
2. 在 `setup_ui` 方法中添加界面组件
3. 使用Tailwind CSS类优化样式设计
4. 添加新的键盘快捷键支持

## 更新计划

- 后续将加入对Qwen-MT-Image的支持。
- 将加入具有上下文感知的批量图片翻译，适用于翻译整本漫画等。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- **Pillow (PIL Fork)**: 强大的图像处理库
- **Gradio**: 快速构建机器学习演示界面
- **NiceGUI**: 现代化的Python GUI框架
- 本项目的设计受到了 [python-image-translator](https://github.com/boysugi20/python-image-translator) 的启发

---

如有问题或建议，欢迎提交 Issue 或 Pull Request！
