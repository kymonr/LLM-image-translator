# LLM-V-Trans | 基于视觉语言模型（VLM）的图像翻译器

[简体中文](./README.md) | [English](./README_en.md)

一个功能强大的本地图像翻译工具，利用先进的视觉语言模型（VLM）实现对图片内文字的精准识别、翻译和无缝替换。告别传统OCR+翻译的繁琐流程，VLM一步到位，效果更佳。

<div style="display: flex; justify-content: space-around;">
  <div>
    <p>原图</p>
    <img src="https://github.com/jedzqer/LLM-image-translator/blob/master/input/test.jpeg" width="300">
  </div>
  <div>
    <p>翻译结果</p>
    <img src="https://github.com/jedzqer/LLM-image-translator/blob/master/output/test.jpeg" width="300">
  </div>
</div>


## ✨ 特性

- **🚀 一步到位**: 直接调用视觉语言模型（如 Qwen-VL），在一个步骤内完成OCR识别和文本翻译，上下文理解更准。
- **🎨 智能美化**: 自动在原文位置上生成与周围背景色融为一体的半透明图层，覆盖原文，观感自然。
- **✍️ 动态字体**: 根据原文区域大小，自动计算最合适的字体大小并进行换行，确保译文完整且美观地展示。
- **🌗 自动配色**: 智能判断背景亮度，为译文选择高对比度的颜色（黑或白），保证可读性。
- **⚙️ 高度可配置**: 所有关键参数（API密钥、模型、Prompt、字体、样式等）均可通过 `config.ini` 文件轻松配置，无需修改代码。
- **🗣️ 清晰日志**: 使用彩色日志输出，清晰展示程序运行的每一个步骤，便于调试和追踪。

## 📖 工作流程

1.  **加载配置**: 程序启动，读取 `config.ini` 中的设置。
2.  **API请求**: 遍历 `input` 文件夹中的图片，将其编码后连同指定的 Prompt 发送给 VLM API。
3.  **解析响应**: VLM 返回包含译文和对应原文坐标的 JSON 数据。
4.  **图像绘制**:
    - 在原图上创建一个新的绘制层。
    - 根据坐标，在每个文本区域绘制一个与背景色相似的半透明矩形，以遮盖原文。
    - 动态计算最佳字体大小和换行方式，将译文居中绘制在矩形上。
5.  **保存结果**: 将绘制层与原图合并，生成最终的翻译图片，并保存到 `output` 文件夹。

## 🛠️ 安装与使用

### 1. 准备环境

- **克隆仓库**:
  ```bash
  git clone https://github.com/your-username/your-repo-name.git
  cd your-repo-name
  ```
- **安装依赖**:
  为了方便，建议你创建一个 `requirements.txt` 文件，内容如下：
  ```txt
  Pillow
  requests
  colorama
  ```
  然后运行以下命令安装：
  ```bash
  pip install -r requirements.txt
  ```

### 2. 进行配置

项目根目录下应该有一个 `config.ini` 文件。如果没有，请根据下面的模板创建一个，或者将代码中的 `config_file = 'config.ini'` 改为您自己的配置文件名。

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
```

**重要**:
- 打开 `config.ini` 文件。
- 在 `[Translator]` 部分填入你的 `api_key`。脚本默认使用 SiliconFlow，你也可以更换为其他兼容 OpenAI API 格式的 VLM 服务商，并相应修改 `api_base` 和 `model_name`。
- 确保 `[Image]` 部分的 `font_path` 指向一个有效的中文字体文件。程序会自动创建 `font` 文件夹，你需要将字体文件（如 `font.ttf`）放入其中。

### 3. 开始翻译

1.  将需要翻译的图片（如 `.jpg`, `.png`）放入 `input` 文件夹。
2.  运行主程序：
    ```bash
    python main.py
    ```
3.  等待程序执行完毕，翻译好的图片将会出现在 `output` 文件夹中，文件名格式为 `原文件名-translated.后缀`。
4.  或者运行app.py， 打开网页localhost:7860使用。

## ⚠️ 注意事项与局限性

- **API 依赖**: 本工具的性能和效果强依赖于你所选择的 VLM 模型。模型的识别精度、翻译质量和响应速度会直接影响最终结果。
- **坐标精度**: VLM 返回的坐标可能不是 100% 精确，有时会导致译文覆盖位置有轻微偏差。
- **空间限制**: 如果原文区域过小，而译文过长，即使经过自动缩放和换行，文本也可能显得拥挤或超出边界。代码中的 `get_wrapped_text_and_font` 函数已尽力优化此问题。
- **费用**: 使用商业 VLM API 可能会产生费用，请注意你的 API 服务商的计费规则。

## 🙏 致谢

- **Pillow (PIL Fork)**: 强大的图像处理库。
- 本项目的设计和部分实现受到了 [python-image-translator](https://github.com/boysugi20/python-image-translator) by [boysugi20](https://github.com/boysugi20) 的启发，在此表示感谢。
