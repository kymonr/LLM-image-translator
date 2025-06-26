from PIL import Image, ImageDraw, ImageFont
import os, easyocr
import requests
import json


class Translator:
    def __init__(self, source: str, target: str, api_key: str, api_base: str, model: str):
        self.source = source
        self.target = target
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")  # Prevent concatenation errors caused by trailing slashes
        self.model = model

    def translate(self, data: list) -> list:
        """Process structured input and output"""
        input_json = json.dumps(data, ensure_ascii=False)
        prompt = f"""你是一个翻译助手，需要将输入的JSON格式数据中的每个文本字段从{self.source}翻译成{self.target}，并保持相同的结构。输入格式为列表，每个元素包含"text"和"text_box"。输出必须严格遵循输入结构，仅翻译"text"字段的值。例如：

输入：
[{{"text": "Hello", "text_box": [[1,2], [3,4]]}}, {{"text": "World", "text_box": [[5,6]]}}]

输出：
[{{"text": "你好", "text_box": [[1,2], [3,4]]}}, {{"text": "世界", "text_box": [[5,6]]}}]

请严格按照上述格式输出翻译结果，不要添加任何额外内容。尽量翻译全部可翻译内容。
这是由OCR输出的结果，存在随意拆分，你可以将一些可能为同一句的项合并在一起，新的项的text_box的每个值应为原来几个项目中最大的那几个。

原文：{input_json}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的翻译助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        response = requests.post(
            f"{self.api_base}/v1/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            result = response.json()
            translated_content = result["choices"][0]["message"]["content"].strip()
            try:
                return json.loads(translated_content)
            except json.JSONDecodeError:
                raise Exception("Translation result format error")
        else:
            raise Exception(f"Request failed: {response.status_code}")

def perform_ocr(image_path, reader):
    """Perform OCR on the input image and return text with confidence > 0.4"""
    result = reader.readtext(image_path, width_ths=0.8, decoder='wordbeamsearch')
    return [(entry[0], entry[1]) for entry in result if entry[2] > 0.4]

def get_font(image, text, width, height, font_path="font/font.ttf"):
    """Determine the largest font size that fits within the given dimensions"""
    font_size = None
    font = None
    box = None
    x = 0
    y = 0

    draw = ImageDraw.Draw(image)

    for size in range(1, 500):
        try:
            new_font = ImageFont.truetype(font_path, size=size)
        except OSError:
            raise ValueError(f"Failed to load font, please check path: {font_path}")

        new_box = draw.textbbox((0, 0), text, font=new_font)
        new_w = new_box[2] - new_box[0]
        new_h = new_box[3] - new_box[1]

        if new_w > width or new_h > height:
            break

        font_size = size
        font = new_font
        box = new_box
        w = new_w
        h = new_h
        x = (width - w) // 2 - box[0]
        y = (height - h) // 2 - box[1]

    return font, x, y


def add_discoloration(color, strength):
    """Adjust RGB values to create a discoloration effect"""
    r, g, b = color
    r = max(0, min(255, r + strength))  # Ensure RGB values are within valid range
    g = max(0, min(255, g + strength))
    b = max(0, min(255, b + strength))
    
    if r == 255 and g == 255 and b == 255:
        r, g, b = 245, 245, 245

    return (r, g, b)

def get_background_color(image, x_min, y_min, x_max, y_max):
    """Determine the background color around the text region"""
    # Define margin for edge region
    margin = 10

    # Crop a small region around the bounding box edges
    edge_region = image.crop(
        (
            max(x_min - margin, 0),
            max(y_min - margin, 0),
            min(x_max + margin, image.width),
            min(y_max + margin, image.height),
        )
    )
    
    # Convert the cropped region to RGB mode
    edge_region = edge_region.convert("RGB")

    # Find the most common color in the cropped region
    edge_colors = edge_region.getcolors(edge_region.size[0] * edge_region.size[1])
    
    # getcolors might return None if the region is monochromatic
    if not edge_colors:
        # Return the color of the top-left pixel as a fallback
        return add_discoloration(edge_region.getpixel((0, 0)), 40)

    background_color = max(edge_colors, key=lambda x: x[0])[1]

    # Add a slight discoloration effect to the background color
    background_color = add_discoloration(background_color, 40)

    return background_color


def get_text_fill_color(background_color):
    """Determine text color (black/white) based on background luminance"""
    # Calculate luminance of the background color
    luminance = (
        0.299 * background_color[0]
        + 0.587 * background_color[1]
        + 0.114 * background_color[2]
    ) / 255

    # Choose text color based on background luminance
    if luminance > 0.5:
        return "black"  # Use black text for light backgrounds
    else:
        return "white"  # Use white text for dark backgrounds

def replace_text_with_translation(image, translated_data):
    """Replace original text with translated text on the image"""
    draw = ImageDraw.Draw(image)
    
    for item in translated_data:
        translated_text = item.get('text')
        if not translated_text:
            continue
            
        text_box = item.get('text_box')
        if not text_box:
            continue

        # Calculate bounding box coordinates
        x_coords = [coord[0] for coord in text_box]
        y_coords = [coord[1] for coord in text_box]
        x_min, y_min = min(x_coords), min(y_coords)
        x_max, y_max = max(x_coords), max(y_coords)

        # Get background color
        background_color = get_background_color(image, x_min, y_min, x_max, y_max)

        # Draw background
        draw.rectangle(((x_min, y_min), (x_max, y_max)), fill=background_color)

        # Calculate font and position
        font, x, y = get_font(image, translated_text, x_max - x_min, y_max - y_min)

        # Draw text
        draw.text(
            (x_min + x, y_min + y),
            translated_text,
            fill=get_text_fill_color(background_color),
            font=font,
        )

    return image


# Initialize OCR reader
reader = easyocr.Reader(["en"], model_storage_directory = 'model')

# Initialize translator
translator = Translator(source="English",
    target="Chinese",
    api_key=yourapi_key, 
    api_base=yourapi_url, 
    model=your_model
    )

input_folder = "input"
output_folder = "output"

for filename in os.listdir(input_folder):
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        continue
        
    print(f'[INFO] Processing {filename}...')
    image_path = os.path.join(input_folder, filename)
    
    # OCR recognition
    try:
        extracted = perform_ocr(image_path, reader)
    except Exception as e:
        print(f'[ERROR] OCR recognition failed: {e}')
        continue
    
    # Construct structured input
    structured_input = [
        {
            'text': text, 
            'text_box': [[int(coord[0]), int(coord[1])] for coord in box]
        } 
        for box, text in extracted
    ]
    
    # Translation
    translated_data = translator.translate(structured_input)

    
    # Draw on image
    image = Image.open(image_path)
    image = replace_text_with_translation(image, translated_data)
    
    # Save
    base, ext = os.path.splitext(filename)
    output_path = os.path.join(output_folder, f"{base}-translated{ext}")
    image.save(output_path)
    print(f'[INFO] Saved as {os.path.basename(output_path)}...')
