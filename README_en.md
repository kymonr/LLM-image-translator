# LLM-V-Trans | Image Translator Powered by Vision Language Models (VLM)

[简体中文](../README.md) | [English](./README_en.md)

A powerful, local image translation tool that leverages advanced Vision Language Models (VLMs) to accurately recognize, translate, and seamlessly replace text within images. Say goodbye to the cumbersome traditional OCR + Translation pipeline; VLM gets it done in a single, more effective step.

| before | Done |
|------|----------|
| ![before](https://github.com/jedzqer/LLM-image-translator/blob/master/input/test.jpeg) | ![done](https://github.com/jedzqer/LLM-image-translator/blob/master/output/test.jpeg) |


## ✨ Features

- **🚀 One-Step Process**: Directly utilizes a Vision Language Model (e.g., Qwen-VL) to perform both OCR and translation in a single step, leading to better contextual understanding.
- **🎨 Smart Inpainting**: Automatically generates a semi-transparent layer that blends with the surrounding background to cover the original text, resulting in a natural look.
- **✍️ Dynamic Font Sizing**: Intelligently calculates the optimal font size and wraps text to fit perfectly within the original text's bounding box, ensuring the translation is complete and aesthetically pleasing.
- **🌗 Auto Color Scheme**: Smartly determines the background luminance and selects a high-contrast text color (black or white) to guarantee readability.
- **⚙️ Highly Configurable**: All key parameters (API key, model, prompt, font, styles, etc.) are easily configurable through a `config.ini` file without needing to modify the source code.
- **🗣️ Verbose Logging**: Features colored console output to clearly display each step of the process, making debugging and tracking easy.

## 📖 How It Works

1.  **Load Configuration**: The script starts by reading settings from `config.ini`.
2.  **API Request**: It iterates through images in the `input` folder, encodes them, and sends them along with a specified prompt to the VLM API.
3.  **Parse Response**: The VLM returns JSON data containing the translated text and the coordinates of the original text.
4.  **Image Rendering**:
    - A new drawing layer is created on top of the original image.
    - For each text block, a semi-transparent rectangle, colored to match the local background, is drawn to hide the original text.
    - The optimal font size and line breaks are dynamically calculated, and the translated text is drawn and centered within this rectangle.
5.  **Save Result**: The drawing layer is composited with the original image, and the final translated image is saved to the `output` folder.

## 🛠️ Installation and Usage

### 1. Setup Environment

- **Clone the repository**:
  ```bash
  git clone https://github.com/your-username/your-repo-name.git
  cd your-repo-name
  ```
- **Install dependencies**:
  For convenience, it's recommended to create a `requirements.txt` file with the following content:
  ```txt
  Pillow
  requests
  colorama
  ```
  Then, run the following command to install them:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Configure the Script

There should be a `config.ini` file in the project root. If not, create one based on the template below or adjust the filename in the `main.py` script.

```ini
# config.ini
[Translator]
# Your API key from services like SiliconFlow, OpenAI, or other compatible providers
api_key = None
# The API base endpoint URL
api_base = https://api.siliconflow.cn
# The name of the Vision Language Model to use
model_name = Qwen/Qwen2.5-VL-32B-Instruct
# The prompt sent to the model. You can modify it, but ensure the JSON format requirement is kept.
model_prompt = """You are a professional OCR engine. Strictly follow these instructions to process the image:
1. Identify all English text in the image and translate it into Chinese.
2. Output the bounding box coordinates for each text area.
3. The output format must be one JSON object per line.
{
  "text": "Translated Text", 
  "box": [x_min, y_min, x_max, y_max]
}

Please carefully identify the foreign language in the image, translate it accurately, and provide precise pixel coordinates for the bounding boxes. Only reply with JSON objects, no comments."""

[Image]
# Transparency of the translated text background (0-255, 0=fully transparent, 255=opaque)
text_box_transparency = 180
# Strength of color adjustment applied to the sampled background color (higher value = more difference)
background_discoloration_strength = 40
# How many pixels to extend outward from the text box to sample the background color
background_sample_margin = 10
# Path to the font file used for rendering translated text
font_path = font/font.ttf
```

**IMPORTANT**:
- Open the `config.ini` file.
- Fill in your `api_key` under the `[Translator]` section. By default, the script is configured for SiliconFlow, but you can switch to any OpenAI-compatible VLM provider by changing `api_base` and `model_name`.
- Ensure the `font_path` under `[Image]` points to a valid font file that supports your target language (e.g., Chinese). The script will create the `font` directory, and you'll need to place your font file (e.g., `font.ttf`) inside it.

### 3. Start Translating

1.  Place the images you want to translate (e.g., `.jpg`, `.png`) into the `input` folder.
2.  Run the main script:
    ```bash
    python main.py
    ```
3.  Wait for the process to complete. The translated images will appear in the `output` folder, named `original-filename-translated.ext`.

## ⚠️ Notes and Limitations

- **API Dependency**: The performance and quality of this tool are heavily dependent on the chosen VLM. The model's recognition accuracy, translation quality, and response time will directly impact the final result.
- **Coordinate Precision**: The bounding box coordinates returned by the VLM may not be 100% accurate, which can sometimes lead to slight misalignments of the translated text.
- **Space Constraints**: If the original text area is too small and the translation is too long, the text may appear cramped or overflow the box, even with automatic resizing and wrapping. The `get_wrapped_text_and_font` function in the code does its best to mitigate this.
- **Costs**: Using commercial VLM APIs may incur costs. Please be aware of the pricing policies of your API provider.


## 🙏 Acknowledgements

- **Pillow (PIL Fork)**: For being a powerful image processing library.
- The design and parts of the implementation were inspired by [python-image-translator](https://github.com/boysugi20/python-image-translator) by [boysugi20](https://github.com/boysugi20). Thank you!
