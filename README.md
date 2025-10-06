# LLM-V-Trans | 基于视觉语言模型（VLM）的图像翻译器

[简体中文](./README.md) | [English](./README_en.md)

一个功能强大的本地图像翻译工具，提供**命令行**和**网页界面**两种使用方式。利用先进的视觉语言模型（VLM）实现对图片内文字的精准识别、翻译和无缝替换。告别传统OCR+翻译的繁琐流程，VLM一步到位，效果更佳。

| 原图 | 翻译结果 |
|------|----------|
| ![原图](https://github.com/jedzqer/LLM-image-translator/blob/master/input/test.jpeg) | ![翻译结果](https://github.com/jedzqer/LLM-image-translator/blob/master/output/test.jpeg) |

## ✨ 特性

## ✨ 核心特性

- **🚀 一步到位**: 直接调用视觉语言模型（如 Qwen-VL），在一个步骤内完成OCR识别和文本翻译，上下文理解更准。
- **🎨 智能美化**: 自动在原文位置上生成与周围背景色融为一体的半透明图层，覆盖原文，观感自然。
- **✍️ 动态字体**: 根据原文区域大小，自动计算最合适的字体大小并进行换行，确保译文完整且美观地展示。
- **🌗 自动配色**: 智能判断背景亮度，为译文选择高对比度的颜色（黑或白），保证可读性。
- **⚙️ 高度可配置**: 所有关键参数（API密钥、模型、Prompt、字体、样式等）均可通过 `config.ini` 文件轻松配置，无需修改代码。
- **🗣️ 清晰日志**: 使用彩色日志输出，清晰展示程序运行的每一个步骤，便于调试和追踪。
- **🖥️ 双模使用**: 支持命令行批量处理和网页界面单张处理两种使用方式。

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
git clone https://github.com/your-username/LLM-V-Trans.git
cd LLM-V-Trans

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

编辑 `config.ini` 文件，主要配置项：

```ini
[Translator]
api_key = your_api_key_here  # 必须设置
api_base = https://api.siliconflow.cn
model_name = Qwen/Qwen2.5-VL-32B-Instruct

[Image]
font_path = font/font.ttf  # 确保字体文件存在
```

### 3. 使用方式

#### 方式一：网页界面（推荐用于单张图片处理）

```bash
python app.py
```

访问 `http://localhost:7860` 即可使用网页界面。

#### 方式二：命令行批量处理

```bash
# 将图片放入 input 文件夹后运行
python LLMtranslator.py
```

处理后的图片将保存在 `output` 文件夹中。

## 📁 项目结构

```
LLM-V-Trans/
├── app.py                 # Gradio网页界面
├── LLMtranslator.py       # 核心翻译模块
├── config.ini            # 配置文件
├── requirements.txt      # 依赖列表
├── input/               # 输入图片目录（命令行模式）
├── output/              # 输出图片目录（命令行模式）
├── font/                # 字体文件目录
└── README.md           # 说明文档
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

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- **Pillow (PIL Fork)**: 强大的图像处理库
- **Gradio**: 快速构建机器学习演示界面
- 本项目的设计受到了 [python-image-translator](https://github.com/boysugi20/python-image-translator) 的启发

---

如有问题或建议，欢迎提交 Issue 或 Pull Request！
