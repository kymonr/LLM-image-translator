### [中文][zh] | [English][en]

# 大语言模型图片翻译器


本项目结合光学字符识别（OCR）与翻译技术，实现图片内文本的跨语言翻译。主要流程如下：

1. **OCR处理**：通过EasyOCR库从输入图片中提取文本及其定位框
2. **文本翻译**：调用LLM API对提取的文本进行翻译
3. **文本替换**：将翻译后的文本按原位置和样式覆盖到图片上
4. **输出结果**：最终生成带翻译文本的图片并保存至输出文件夹

## 环境配置

#### 安装步骤

1. 将代码仓库克隆到本地
2. 执行`pip install easyocr PIL`安装Python依赖包

## 使用说明

1. 将待翻译图片放入`input`文件夹
2. 将`main.py`脚本这一行`translator = Translator(source="英文", target="中文", apikey=yourapi_key, api_base=yourapi_url, model=your_model)`中的openai兼容api的api_key和api_url填写好。
3. 确保你的字体文件路径为：font/font.ttf
4. 运行`main.py`脚本
5. 翻译结果将保存至`output`文件夹

## 注意事项

- 支持的OCR语言列表参见[此链接](https://www.jaided.ai/easyocr/)
- 可在脚本中调整文本语种、识别阈值、翻译服务或图像处理参数
- 为了使用大语言模型联系全文翻译，文字无法一一对应，可能导致文字被压缩的很小。目前我无法解决。

## 致谢

- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - OCR处理核心库
- [Pillow (PIL Fork)](https://python-pillow.org/) - 图像处理工具库
- [原仓库python-image-translator](https://github.com/boysugi20/python-image-translator) 和 [原作者boysugi20](https://github.com/boysugi20)

[en]: https://github.com/jedzqer/LLM-image-translator/blob/master/README_en.md "This README is translated by AI"

[zh]: https://github.com/jedzqer/LLM-image-translator/blob/master/README.md
