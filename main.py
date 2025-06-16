from PIL import Image, ImageDraw, ImageFont
import os, easyocr
import requests

class Translator:
    def __init__(self, source: str, target: str, api_key: str, api_base: str):
        self.source = source
        self.target = target
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")  # 防止末尾斜杠造成拼接错误
        self.model = your_model

    def translate(self, text: str) -> str:
        prompt = f"请将以下内容从{self.source}翻译为{self.target}，你的输出内容将直接作为译文，所以不要回复任何无关内容：\n\n{text}。\n/nothink"
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
            return result["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"请求失败啦 (╥﹏╥)，状态码: {response.status_code}, 响应: {response.text}")

def perform_ocr(image_path, reader):
    # Perform OCR on the image
    result = reader.readtext(image_path, width_ths = 0.8,  decoder = 'wordbeamsearch')

    # Extract text and bounding boxes from the OCR result
    extracted_text_boxes = [(entry[0], entry[1]) for entry in result if entry[2] > 0.4]

    return extracted_text_boxes


def get_font(image, text, width, height, font_path="font/font.ttf"):
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
            raise ValueError(f"字体加载失败，请检查路径是否正确：{font_path}")

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
    # Adjust RGB values to add discoloration
    # Only take the first three channels: R, G, B, ignore A (transparency)
    r, g, b = color[:3]
    r = max(0, min(255, r + strength))  # Ensure RGB values are within valid range
    g = max(0, min(255, g + strength))
    b = max(0, min(255, b + strength))
    
    if r == 255 and g == 255 and b == 255:
        r, g, b = 245, 245, 245

    return (r, g, b)


def get_background_color(image, x_min, y_min, x_max, y_max):
    # Define the margin for the edges
    margin = 10

    # Crop a small region around the edges of the bounding box
    edge_region = image.crop(
        (
            max(x_min - margin, 0),
            max(y_min - margin, 0),
            min(x_max + margin, image.width),
            min(y_max + margin, image.height),
        )
    )

    # Find the most common color in the cropped region
    edge_colors = edge_region.getcolors(edge_region.size[0] * edge_region.size[1])
    background_color = max(edge_colors, key=lambda x: x[0])[1]

    # Add a bit of discoloration to the background color
    background_color = add_discoloration(background_color, 40)

    return background_color


def get_text_fill_color(background_color):
    # Calculate the luminance of the background color
    luminance = (
        0.299 * background_color[0]
        + 0.587 * background_color[1]
        + 0.114 * background_color[2]
    ) / 255

    # Determine the text color based on the background luminance
    if luminance > 0.5:
        return "black"  # Use black text for light backgrounds
    else:
        return "white"  # Use white text for dark backgrounds


def replace_text_with_translation(image_path, translated_texts, text_boxes):
    # Open the image
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # Load a font
    font = ImageFont.load_default()

    # Replace each text box with translated text
    for text_box, translated in zip(text_boxes, translated_texts):

        if translated is None:
            continue

        # Set initial values
        x_min, y_min = text_box[0][0][0], text_box[0][0][1]
        x_max, y_max = text_box[0][0][0], text_box[0][0][1]

        for coordinate in text_box[0]:

            x, y = coordinate

            if x < x_min:
                x_min = x
            elif x > x_max:
                x_max = x
            if y < y_min:
                y_min = y
            elif y > y_max:
                y_max = y

        # Find the most common color in the text region
        background_color = get_background_color(image, x_min, y_min, x_max, y_max)

        # Draw a rectangle to cover the text region with the original background color
        draw.rectangle(((x_min, y_min), (x_max, y_max)), fill=background_color)

        # Calculate font size, box
        font, x, y = get_font(image, translated, x_max - x_min, y_max - y_min)

        # Draw the translated text within the box
        draw.text(
            (x_min + x, y_min + y),
            translated,
            fill=get_text_fill_color(background_color),
            font=font,
        )

    return image


# Initialize the OCR reader
reader = easyocr.Reader(["en"], model_storage_directory = 'model')

# Initialize the Translator
translator = Translator(source="英文", target="中文", apikey=yourapi_key, api_base=yourapi_url)

# Define input and output location
input_folder = "input"
output_folder = "output"

# Process each image file from input
files = os.listdir(input_folder)
image_files = [file for file in files if file.endswith((".jpg", ".jpeg", ".png"))]
for filename in image_files:
    
    print(f'[INFO] Processing {filename}...')

    image_path = os.path.join(input_folder, filename)

    # Extract text and location
    extracted_text_boxes = perform_ocr(image_path, reader)

    # Translate texts
    translated_texts = []
    all_original_texts = []
    all_translated_text = ""

    for text_box, text in extracted_text_boxes:
        all_original_texts.append(text)
        
    # Merge all original texts, connect them with <ng>
    all_translated_input = '<ng>'.join(all_original_texts)

    # perform translation
    all_translated_text = translator.translate(all_translated_input)

    # split the translated results according to the number of original texts
    translated_segments = all_translated_text.split('<ng>', len(all_original_texts)-1)

    # If the number of paragraphs in the translation result is less than the original text, merge the remaining parts into the last paragraph.
    if len(translated_segments) < len(all_original_texts):
        remaining_text = '<ng>'.join(translated_segments[len(all_original_texts)-1:])
        remaining_text = remaining_text.replace("<ng>", "")
        translated_segments = translated_segments[:len(all_original_texts)-1] + [remaining_text]

    translated_texts = translated_segments

    # Replace text with translated text
    image = replace_text_with_translation(image_path, translated_texts, extracted_text_boxes)

    # Save modified image
    base_filename, extension = os.path.splitext(filename)
    output_filename = f"{base_filename}-translated{extension}"
    output_path = os.path.join(output_folder, output_filename)
    image.save(output_path)

    print(f'[INFO] Saved as {output_filename}...')
