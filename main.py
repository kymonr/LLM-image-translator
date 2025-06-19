from PIL import Image, ImageDraw, ImageFont
import os, easyocr
import requests


class Translator:
    def __init__(self, source: str, target: str, api_key: str, api_base: str, model: str):
        self.source = source
        self.target = target
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")  # Prevent concatenation errors caused by trailing slashes
        self.model = model

    def translate(self, text: str) -> str:
        prompt = f"将给出内容从{self.source}翻译为{self.target}，翻译过程中必须保留我的标记符“<ng>”，禁止自主添加、减少和移动标记符“<ng>”，你的输出内容将直接作为译文，所以不要回复任何无关内容。原文：{text}/nothink"
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
            raise Exception(f"The request failed (╥﹏╥)，Status code: {response.status_code}, response: {response.text}")

def perform_ocr(image_path, reader):
    # Perform OCR recognition on the image
    result = reader.readtext(image_path, width_ths = 0.8,  decoder = 'wordbeamsearch')

    # Extract text and bounding boxes from OCR results
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
            raise ValueError(f"Failed to load font, please check the path: {font_path}")

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
    # Adjust RGB values to add a discoloration effect
    r, g, b = color
    r = max(0, min(255, r + strength))  # Ensure RGB values are within valid range
    g = max(0, min(255, g + strength))
    b = max(0, min(255, b + strength))
    
    if r == 255 and g == 255 and b == 255:
        r, g, b = 245, 245, 245

    return (r, g, b)


def get_background_color(image, x_min, y_min, x_max, y_max):
    # Define margin for edge region
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
    
    # Convert the cropped region to RGB mode
    edge_region = edge_region.convert("RGB")

    # Find the most common color in the cropped region
    edge_colors = edge_region.getcolors(edge_region.size[0] * edge_region.size[1])
    
    # When the region has uniform color, getcolors might return None
    if not edge_colors:
        # If no colors are retrieved (e.g., region is completely transparent or special case), return a default color
        # Here we take the color of the top-left pixel of the region as a fallback
        return add_discoloration(edge_region.getpixel((0, 0)), 40)

    background_color = max(edge_colors, key=lambda x: x[0])[1]

    # Add a slight discoloration effect to the background color
    background_color = add_discoloration(background_color, 40)

    return background_color


def get_text_fill_color(background_color):
    # Calculate luminance of the background color
    luminance = (
        0.299 * background_color[0]
        + 0.587 * background_color[1]
        + 0.114 * background_color[2]
    ) / 255

    # Determine text color based on background luminance
    if luminance > 0.5:
        return "black"  # Use black text for light backgrounds
    else:
        return "white"  # Use white text for dark backgrounds


def replace_text_with_translation(image_path, translated_texts, text_boxes):
    # Open the image
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # Load font
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

        # Calculate font size and position
        font, x, y = get_font(image, translated, x_max - x_min, y_max - y_min)

        # Draw translated text inside the box
        draw.text(
            (x_min + x, y_min + y),
            translated,
            fill=get_text_fill_color(background_color),
            font=font,
        )

    return image


def group_boxes_by_line(box_text_list, y_tolerance_ratio=0.5):
    """
    Group OCR results into lines, sort them correctly, and flatten the results.
    
    This function first groups bounding boxes into lines based on vertical proximity,
    then sorts the boxes within each line by horizontal position (left to right).
    
    Parameters:
        box_text_list: List of tuples, each in the format (bounding_box, text).
        y_tolerance_ratio: Ratio of bounding box height used as tolerance to determine if two boxes are on the same line.

    Returns:
        List of (bounding_box, text) tuples sorted in reading order.
    """
    if not box_text_list:
        return []

    # Sort primarily by the top y-coordinate of the bounding boxes
    boxes_sorted = sorted(box_text_list, key=lambda item: item[0][0][1])

    lines = []
    current_line = []
    
    if boxes_sorted:
        current_line.append(boxes_sorted[0])
        for i in range(1, len(boxes_sorted)):
            prev_box = current_line[-1][0]
            current_box = boxes_sorted[i][0]

            # Calculate the vertical center of the last bounding box in the current line
            prev_box_center_y = (prev_box[0][1] + prev_box[2][1]) / 2
            
            # Calculate the vertical center of the current bounding box being checked
            current_box_center_y = (current_box[0][1] + current_box[2][1]) / 2

            # Calculate the height of the last bounding box in the line
            prev_box_height = abs(prev_box[0][1] - prev_box[2][1])

            # If the vertical distance is within tolerance, they are on the same line
            if abs(prev_box_center_y - current_box_center_y) <= prev_box_height * y_tolerance_ratio:
                current_line.append(boxes_sorted[i])
            else:
                # Finalize the previous line and start a new one
                lines.append(current_line)
                current_line = [boxes_sorted[i]]
    
    # Append the last line
    if current_line:
        lines.append(current_line)

    # Sort each line by x-coordinate and flatten the list of lines
    sorted_and_flattened = []
    for line in lines:
        # Sort the line by the minimum x-coordinate (left edge)
        line_sorted_by_x = sorted(line, key=lambda item: item[0][0][0])
        sorted_and_flattened.extend(line_sorted_by_x)

    return sorted_and_flattened


# Initialize OCR reader
reader = easyocr.Reader(["en"], model_storage_directory = 'model')

# Initialize translator
translator = Translator(source="English",
    target="Chinese",
    api_key=yourapi_key, 
    api_base=yourapi_url, 
    model=your_model
    )

# Define input and output locations
input_folder = "input"
output_folder = "output"

# Process each image file in the input folder
files = os.listdir(input_folder)
image_files = [file for file in files if file.endswith((".jpg", ".jpeg", ".png"))]
for filename in image_files:
    
    print(f'[INFO] Processing {filename}...')

    image_path = os.path.join(input_folder, filename)

    # Extract text and positions
    extracted_text_boxes = group_boxes_by_line(perform_ocr(image_path, reader))

    # Translate text
    translated_texts = []
    all_original_texts = []
    all_translated_text = ""

    for text_box, text in extracted_text_boxes:
        all_original_texts.append(text)
        
    # Combine all original texts with <ng> separator
    all_translated_input = '<ng>'.join(all_original_texts)

    # Perform translation
    all_translated_text = translator.translate(all_translated_input)

    # Split translated result into segments based on original text count
    translated_segments = all_translated_text.split('<ng>', len(all_original_texts)-1)

    # If there are fewer translated segments than original texts, merge remaining parts into the last segment
    if len(translated_segments) < len(all_original_texts):
        remaining_text = '<ng>'.join(translated_segments[len(all_original_texts)-1:])
        remaining_text = remaining_text.replace("<ng>", "")
        translated_segments = translated_segments[:len(all_original_texts)-1] + [remaining_text]

    translated_texts = translated_segments

    print("\nTranslated: ", translated_texts)
    print("\nOriginal: ", all_original_texts)

    # Replace original text with translated text
    image = replace_text_with_translation(image_path, translated_texts, extracted_text_boxes)

    # Save modified image
    base_filename, extension = os.path.splitext(filename)
    output_filename = f"{base_filename}-translated{extension}"
    output_path = os.path.join(output_folder, output_filename)
    image.save(output_path)

    print(f'[INFO] Saved as {output_filename}...')
