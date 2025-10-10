# LLM-V-Trans | Image Translator Based on Visual Language Model (VLM)

[简体中文](./README.md) | [English](./README_en.md)

A powerful local image translation tool offering **standalone window application** and **command-line batch processing** usage modes. Leverages advanced Visual Language Models (VLM) to achieve precise text recognition, translation, and seamless in-place replacement within images. Streamlines the process by eliminating the traditional OCR + translation workflow — VLM handles it all in one step for superior results.

| Original Image | Translated Result |
|----------------|-------------------|
| ![Original](https://github.com/jedzqer/LLM-image-translator/blob/master/input/test.jpeg) | ![Result](https://github.com/jedzqer/LLM-image-translator/blob/master/output/test.jpeg) |

## ✨ Core Features

- **🚀 All-in-One Process**: Directly utilizes Visual Language Models (e.g., Qwen-VL) to perform OCR and text translation in a single step, ensuring better contextual understanding.
- **🎨 Intelligent Beautification**: Automatically generates semi-transparent overlays that blend with the surrounding background color to cover the original text, resulting in a natural appearance.
- **✍️ Dynamic Font Sizing**: Automatically calculates the optimal font size based on the original text region and handles text wrapping to ensure the translation is displayed completely and aesthetically.
- **🌗 Automatic Color Matching**: Intelligently assesses background brightness and selects a high-contrast color (black or white) for the translated text to ensure readability.
- **📐 Normalized Coordinates**: Supports normalized coordinate mode to solve coordinate mismatch issues caused by some API providers compressing image resolution.
- **⚙️ Highly Configurable**: All key parameters (API key, model, prompt, font, styles, etc.) are easily adjustable via the `config.ini` file without modifying the source code.
- **🗣️ Clear Logging**: Uses colored log output to clearly display each step of the process, facilitating debugging and tracking.
- **🖥️ Dual Usage Modes**: Supports standalone window application for single image processing and command-line batch processing.
- **🎯 Modern Interface**: NiceGUI version provides native window experience with real-time preview, keyboard shortcuts, and responsive design.
- **⚡ Asynchronous Processing**: Non-blocking translation task processing keeps the interface responsive and smooth.

## 📖 Workflow

1.  **Load Configuration**: The program starts and reads settings from `config.ini`.
2.  **API Request**: Encodes the image and sends it along with the specified prompt to the VLM API.
3.  **Parse Response**: The VLM returns JSON data containing the translations and their corresponding bounding box coordinates for the original text.
4.  **Image Rendering**:
    - Creates a new drawing layer on the original image.
    - For each text region, draws a semi-transparent rectangle matching the background color to cover the original text.
    - Dynamically calculates the optimal font size and wrapping, then centers and draws the translated text on the rectangle.
5.  **Save Result**: Merges the drawing layer with the original image to produce the final translated image.

## 🛠️ Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/jedzqer/LLM-image-translator.git
cd LLM-image-translator

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

There is a `config.ini.example` file in the project root directory. You can copy it to `config.ini` and configure:

```bash
# Copy configuration template
cp config.ini.example config.ini
```

Edit the `config.ini` file. Key configuration items:

```ini
# config.ini
[Translator]
api_key = your_api_key_here  # REQUIRED
api_base = https://api.siliconflow.cn
model_name = Qwen/Qwen2.5-VL-32B-Instruct

[Image]
font_path = font/font.ttf  # Ensure the font file exists
```

### 3. Usage

#### Option 1: Standalone Window Application (Recommended for single images)

```bash
# Run the application
python run_nicegui_app.py
```

**Features**:
- Standalone window application with native window experience
- Modern layout with left control panel and right image preview
- Real-time preview of original and translated images with tab switching
- Keyboard shortcuts: Ctrl+T (Translate), Ctrl+R (Reset), Ctrl+S (Save)
- Asynchronous processing keeps the interface responsive
- Batch processing functionality supports folder-based batch translation

#### Option 2: Command Line Batch Processing

```bash
# Place images in the 'input' folder, then run
python LLMtranslator.py
```

Processed images will be saved in the `output` folder.

## 📁 Project Structure

```
LLM-image-translator/
├── nicegui_app.py         # NiceGUI main application file
├── run_nicegui_app.py     # NiceGUI startup script (recommended)
├── LLMtranslator.py       # Core translation module
├── config.ini.example     # Configuration file template
├── requirements.txt       # Dependencies list
├── input/                # Input image directory (CLI mode)
├── output/               # Output image directory
└── font/                 # Font directory
```

## ⚙️ Detailed Configuration

### API Configuration (Translator Section)

- `api_key`: **Required**. Supports services compatible with the OpenAI API, such as SiliconFlow.
- `api_base`: API service address, defaults to SiliconFlow.
- `model_name`: Recommended to use models capable of visual tasks, like the Qwen-VL series.
- `model_prompt`: Custom instructions can be defined, but must adhere to the required JSON output format.

### Image Style Configuration (Image Section)

- `text_box_transparency`: Transparency of the translation background overlay (0-255).
- `background_discoloration_strength`: Strength of the background color adjustment.
- `background_sample_margin`: Margin for sampling the background color.
- `font_path`: Path to the Chinese font file.
- `normalize_coordinates`: Normalized coordinate mode switch.

## ⚠️ Important Notes

1.  **API Key**: You must configure a valid API key in `config.ini` before use.
2.  **Font File**: Ensure the `font/font.ttf` file exists; otherwise, the system default font will be used.
3.  **Image Formats**: Supports common formats like JPG, PNG, JPEG, BMP, GIF.
4.  **Internet Connection**: A stable internet connection is required to call the VLM API.
5.  **Configuration File**: For first-time use, copy `config.ini.example` to `config.ini`.

## 🔧 Troubleshooting

### Common Issues

**Q: Error "Configuration file cannot be read" on startup.**
A: Ensure the `config.ini` file exists in the project root directory, or copy from `config.ini.example`.

**Q: Translation fails with an API key error.**
A: Check if the `api_key` in `config.ini` is correctly set.

**Q: Standalone window application cannot start.**
A: Check if dependencies are installed completely, run `pip install -r requirements.txt`.

**Q: Translated text displays incorrectly.**
A: Check if the font file exists, or adjust the font-size related parameters in `config.ini`.

**Q: Translation position is inaccurate.**
A: Try enabling the normalized coordinate mode.

**Q: Keyboard shortcuts don't work (NiceGUI version).**
A: Ensure the application window is active; shortcuts only work within the application window.

## 🛠️ Development Notes

### Tech Stack

- **Frontend Framework**: NiceGUI (based on Vue.js)
- **Backend Language**: Python 3.9+
- **Image Processing**: Pillow (PIL)
- **API Calls**: requests
- **Configuration Management**: configparser
- **Async Processing**: asyncio

### Core Modules

The application is based on the [`LLMtranslator.py`](LLMtranslator.py) module, integrated through the [`process_image_translation`](LLMtranslator.py:652) function. The standalone window application uses [`nicegui_app.py`](nicegui_app.py) to build a modern interface.

### Extension Development

The core translation module [`LLMtranslator.py`](LLMtranslator.py) provides a complete API interface that can be easily integrated into other applications:

```python
from LLMtranslator import process_image_translation
from PIL import Image

# Using image path
result = process_image_translation('path/to/image.jpg')
if result['success']:
    result['translated_image'].save('output/translated.jpg')

# Using PIL image object
img = Image.open('test.jpg')
result = process_image_translation(img)
```

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Pillow (PIL Fork)**: Powerful image processing library.
- **NiceGUI**: For enabling modern Python GUI applications.
- **SiliconFlow**: For providing stable VLM API services.
- This project's design was inspired by [python-image-translator](https://github.com/boysugi20/python-image-translator).

---

For questions or suggestions, please submit an Issue or Pull Request!
