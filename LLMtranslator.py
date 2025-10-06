from PIL import Image, ImageDraw, ImageFont
import os
import requests
import json
import base64
import re
from io import BytesIO
import configparser
from colorama import Fore, Style, init
import math

# 初始化colorama，使其在Windows等平台上也能正常显示颜色
init(autoreset=True)

# 定义颜色常量
INFO = Fore.GREEN
WARNING = Fore.YELLOW
ERROR = Fore.RED
DEBUG = Fore.LIGHTBLACK_EX # 或者 Fore.CYAN, Fore.MAGENTA
RESET = Style.RESET_ALL

def log_info(message):
    print(f"{INFO}[INFO]{RESET} {message}")

def log_warning(message):
    print(f"{WARNING}[WARNING]{RESET} {message}")

def log_error(message):
    print(f"{ERROR}[ERROR]{RESET} {message}")

def log_debug(message):
    print(f"{DEBUG}[DEBUG]{RESET} {message}")

class VLTranslator:
    """
    视觉语言翻译器类，封装了与SiliconFlow VL模型交互的逻辑。
    """
    def __init__(self, config: configparser.ConfigParser, normalize_coordinates: bool = False):
        """
        初始化VLTranslator实例。

        Args:
            config (configparser.ConfigParser): 配置对象，用于读取API设置。
            normalize_coordinates (bool): 是否使用归一化坐标模式
        """
        self.api_key = config.get('Translator', 'api_key')
        self.api_base = config.get('Translator', 'api_base').rstrip("/")
        self.model = config.get('Translator', 'model_name', fallback='Qwen/Qwen2.5-VL-32B-Instruct')
        self.normalize_coordinates = normalize_coordinates
        
        # 根据坐标模式选择不同的提示词
        if normalize_coordinates:
            self.model_prompt = config.get('Translator', 'model_prompt_normalized', fallback="""你是一个专业OCR引擎。严格按以下要求处理图像：
1. 识别图中所有英文文字并翻译成中文输出
2. 为每个文字区域输出检测框坐标（使用归一化坐标，范围0-1）
3. 输出格式：每行一个JSON对象
{
  "text": "译文",
  "box": [x_min, y_min, x_max, y_max]
}

请仔细识别图片中的外语，准确翻译并提供归一化坐标（0-1范围）。只许回复json对象，不要注释""")
        else:
            self.model_prompt = config.get('Translator', 'model_prompt', fallback="""你是一个专业OCR引擎。严格按以下要求处理图像：
1. 识别图中所有英文文字并翻译成中文输出
2. 为每个文字区域输出检测框坐标
3. 输出格式：每行一个JSON对象
{
  "text": "译文",
  "box": [x_min, y_min, x_max, y_max]
}

请仔细识别图片中的外语，准确翻译并提供精确的边界框像素化坐标。只许回复json对象，不要注释""")
        
        log_info("VLTranslator初始化完成。")
        log_debug(f"API Base: {self.api_base}, Model: {self.model}, 坐标模式: {'归一化' if normalize_coordinates else '像素'}")

    def image_to_base64(self, image_path: str) -> str:
        """
        将本地图片文件读取并转换为Base64编码字符串。
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def ocr_and_translate(self, image_path: str) -> list:
        """
        使用VL模型进行OCR识别和文本翻译。
        """
        base64_image = self.image_to_base64(image_path)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.model_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }

        try:
            response = requests.post(
                f"{self.api_base}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60 # 设置超时时间，防止请求无限等待
            )
            response.raise_for_status() # 检查HTTP响应状态码，如果不是200范围则抛出HTTPError
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            return self.parse_response(content)
        except requests.exceptions.Timeout as e:
            log_error(f"API请求超时: {e}")
            raise
        except requests.exceptions.RequestException as e:
            log_error(f"API请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                log_error(f"HTTP状态码: {e.response.status_code}, 响应: {e.response.text}")
            raise
        except json.JSONDecodeError as e:
            log_error(f"解析API响应JSON失败: {e}")
            raise
        except Exception as e:
            log_error(f"OCR和翻译过程中发生未知错误: {e}")
            raise

    def parse_response(self, content: str) -> list:
        """
        将VL模型返回的包含多个JSON对象的字符串解析成Python字典列表。
        """
        results = []
        log_debug("模型返回原始内容:")
        log_debug(content)
        
        json_objects_str = re.findall(r'\{.*?\}', content, re.DOTALL)
        
        for obj_str in json_objects_str:
            try:
                data = json.loads(obj_str)
                if isinstance(data, dict) and 'text' in data and 'box' in data:
                    results.append(data)
                else:
                    log_debug(f"发现无效或不完整的JSON对象，已跳过: {obj_str}")
            except json.JSONDecodeError:
                log_debug(f"无法解析以下片段为有效JSON，已跳过: {obj_str}")
                continue
        
        return results

def calculate_font_size_by_area(text: str, total_area: int, area_ratio: float = 0.8) -> int:
    """
    根据文本背景总面积和文字数量计算合适的字体大小。
    
    Args:
        text (str): 需要渲染的文本
        total_area (int): 文本背景的总面积（像素）
        area_ratio (float): 面积缩放比例，用于给文字留出边距
    
    Returns:
        int: 计算出的字体大小
    """
    if not text:
        return 12  # 默认字体大小
    
    # 计算文字数量（中文字符和英文字符都算作1个字符）
    char_count = len(text)
    
    # 计算每个字符的平均面积
    char_area = (total_area * area_ratio) / char_count
    
    # 假设字符是正方形，计算字体大小
    # 字体大小大约等于字符高度，而字符宽度通常略小于高度
    font_size = int(math.sqrt(char_area))
    
    # 限制字体大小在合理范围内
    font_size = max(8, min(font_size, 200))
    
    log_debug(f"文本 '{text}' 字符数: {char_count}, 总面积: {total_area}, 单字符面积: {char_area:.2f}, 计算字体大小: {font_size}")
    
    return font_size

def get_wrapped_text_and_font_by_area(text: str, width: int, height: int, font_path: str = "font/font.ttf") -> tuple:
    """
    基于文本背景面积计算字体大小，然后进行文本换行。

    Args:
        text (str): 需要计算字体大小和换行的文本字符串。
        width (int): 文本框的宽度。
        height (int): 文本框的高度。
        font_path (str): 字体文件的路径。

    Returns:
        tuple: 包含以下元素的元组：
               - font (PIL.ImageFont.FreeTypeFont): 字体对象。
               - wrapped_lines (list[str]): 包含分行后文本的列表。
               - text_height (int): 文本绘制后的总高度。
               - x_offset (int): 文本在x轴上的居中偏移量。
               - y_offset (int): 文本在y轴上的居中偏移量。
    """
    if not text:
        return None, [], 0, 0, 0

    font_path = os.path.abspath(font_path)
    try:
        ImageFont.truetype(font_path, size=10)
    except OSError:
        log_warning(f"字体文件 '{font_path}' 未找到或损坏，使用PIL默认字体。")
        font_path = ""

    # 计算文本背景总面积
    total_area = width * height
    
    # 根据面积计算字体大小
    calculated_font_size = calculate_font_size_by_area(text, total_area)
    
    # 创建字体对象
    try:
        if font_path:
            font = ImageFont.truetype(font_path, size=calculated_font_size)
        else:
            font = ImageFont.load_default()
    except OSError:
        font = ImageFont.load_default()
        log_warning(f"无法加载字体文件，使用默认字体")

    # 创建临时绘图对象用于测量文本尺寸
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    # 进行文本换行
    lines = []
    current_line = []
    words = text.split(' ')
    if not words or len(words) == 1:  # 对于中文或单个长单词
        words = list(text)  # 按字符分割

    for word in words:
        # 尝试将单词添加到当前行
        test_line_text = ''.join(current_line + [word]) if len(words) == len(text) else ' '.join(current_line + [word])
        bbox = dummy_draw.textbbox((0, 0), test_line_text, font=font)
        text_w = bbox[2] - bbox[0]
        
        if text_w <= width:  # 如果当前行加上新单词没有超出宽度
            current_line.append(word)
        else:  # 超出宽度，进行换行
            if current_line:  # 如果当前行有内容，先保存这行
                lines.append(''.join(current_line) if len(words) == len(text) else ' '.join(current_line))
            current_line = [word]  # 新行从当前单词开始
            
            # 检查单个单词是否就超出了宽度
            single_word_bbox = dummy_draw.textbbox((0, 0), word, font=font)
            if single_word_bbox[2] - single_word_bbox[0] > width:
                # 如果单个单词就超出宽度，强制按字符切分
                if current_line:
                    lines.append(''.join(current_line) if len(words) == len(text) else ' '.join(current_line))
                current_line = []
                temp_word_line = ''
                for char in word:
                    test_char_line_text = temp_word_line + char
                    char_bbox = dummy_draw.textbbox((0, 0), test_char_line_text, font=font)
                    if char_bbox[2] - char_bbox[0] <= width:
                        temp_word_line += char
                    else:
                        if temp_word_line:
                            lines.append(temp_word_line)
                        temp_word_line = char
                if temp_word_line:
                    lines.append(temp_word_line)
    
    if current_line:  # 添加最后一行
        lines.append(''.join(current_line) if len(words) == len(text) else ' '.join(current_line))

    # 计算文本总高度
    line_height = font.getmask("M").getbbox()[3] if font.getmask("M").getbbox() else calculated_font_size
    line_spacing = max(2, calculated_font_size // 8)  # 行间距
    total_text_height = line_height * len(lines)
    if len(lines) > 1:
        total_text_height += (len(lines) - 1) * line_spacing

    # 如果文本高度超出区域，尝试减小字体大小
    if total_text_height > height and calculated_font_size > 8:
        # 递归调用，使用更小的字体
        smaller_font_size = int(calculated_font_size * 0.8)
        try:
            if font_path:
                smaller_font = ImageFont.truetype(font_path, size=smaller_font_size)
            else:
                smaller_font = ImageFont.load_default()
        except OSError:
            smaller_font = ImageFont.load_default()
        
        # 重新计算换行和高度
        return get_wrapped_text_and_font_by_area_recursive(text, width, height, font_path, smaller_font_size)

    # 计算最长行的宽度用于居中
    max_line_width = 0
    for line in lines:
        line_bbox = dummy_draw.textbbox((0, 0), line, font=font)
        max_line_width = max(max_line_width, line_bbox[2] - line_bbox[0])

    # 计算居中偏移量
    x_offset = max(0, (width - max_line_width) // 2)
    y_offset = max(0, (height - total_text_height) // 2)

    return font, lines, total_text_height, x_offset, y_offset

def get_wrapped_text_and_font_by_area_recursive(text: str, width: int, height: int, font_path: str, font_size: int) -> tuple:
    """
    递归辅助函数，用于在字体大小需要调整时重新计算文本换行。
    """
    if font_size < 8:
        font_size = 8
    
    try:
        if font_path:
            font = ImageFont.truetype(font_path, size=font_size)
        else:
            font = ImageFont.load_default()
    except OSError:
        font = ImageFont.load_default()

    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    # 重新进行文本换行
    lines = []
    current_line = []
    words = text.split(' ')
    if not words or len(words) == 1:
        words = list(text)

    for word in words:
        test_line_text = ''.join(current_line + [word]) if len(words) == len(text) else ' '.join(current_line + [word])
        bbox = dummy_draw.textbbox((0, 0), test_line_text, font=font)
        text_w = bbox[2] - bbox[0]
        
        if text_w <= width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(''.join(current_line) if len(words) == len(text) else ' '.join(current_line))
            current_line = [word]
            
            single_word_bbox = dummy_draw.textbbox((0, 0), word, font=font)
            if single_word_bbox[2] - single_word_bbox[0] > width:
                if current_line:
                    lines.append(''.join(current_line) if len(words) == len(text) else ' '.join(current_line))
                current_line = []
                temp_word_line = ''
                for char in word:
                    test_char_line_text = temp_word_line + char
                    char_bbox = dummy_draw.textbbox((0, 0), test_char_line_text, font=font)
                    if char_bbox[2] - char_bbox[0] <= width:
                        temp_word_line += char
                    else:
                        if temp_word_line:
                            lines.append(temp_word_line)
                        temp_word_line = char
                if temp_word_line:
                    lines.append(temp_word_line)
    
    if current_line:
        lines.append(''.join(current_line) if len(words) == len(text) else ' '.join(current_line))

    # 计算文本总高度
    line_height = font.getmask("M").getbbox()[3] if font.getmask("M").getbbox() else font_size
    line_spacing = max(2, font_size // 8)
    total_text_height = line_height * len(lines)
    if len(lines) > 1:
        total_text_height += (len(lines) - 1) * line_spacing

    # 如果仍然超出高度，继续递归减小字体
    if total_text_height > height and font_size > 8:
        return get_wrapped_text_and_font_by_area_recursive(text, width, height, font_path, int(font_size * 0.9))

    # 计算居中偏移量
    max_line_width = 0
    for line in lines:
        line_bbox = dummy_draw.textbbox((0, 0), line, font=font)
        max_line_width = max(max_line_width, line_bbox[2] - line_bbox[0])

    x_offset = max(0, (width - max_line_width) // 2)
    y_offset = max(0, (height - total_text_height) // 2)

    return font, lines, total_text_height, x_offset, y_offset

def add_discoloration(color: tuple, strength: int) -> tuple:
    """
    调整RGB颜色值以增加一些"褪色"效果，使其不那么鲜艳或与背景有一定区分度。
    """
    r, g, b = color
    r = max(0, min(255, r + strength))
    g = max(0, min(255, g + strength))
    b = max(0, min(255, b + strength))
    
    if r == 255 and g == 255 and b == 255:
        r, g, b = 245, 245, 245

    return (r, g, b)

def get_background_color(image: Image.Image, x_min: int, y_min: int, x_max: int, y_max: int, margin: int) -> tuple[int, int, int]:
    """
    从图片指定区域的边缘获取背景颜色。
    """
    
    edge_region = image.crop(
        (
            max(x_min - margin, 0),
            max(y_min - margin, 0),
            min(x_max + margin, image.width),
            min(y_max + margin, image.height),
        )
    )
    
    edge_region = edge_region.convert("RGB")
    edge_colors = edge_region.getcolors(edge_region.size[0] * edge_region.size[1])
    
    if not edge_colors:
        return (128, 128, 128) # 默认返回一个中性灰色

    background_color = max(edge_colors, key=lambda x: x[0])[1]
    # 确保返回的是三元组
    if isinstance(background_color, tuple) and len(background_color) == 3:
        return background_color
    else:
        return (128, 128, 128) # 如果颜色格式异常，返回默认灰色

def get_text_fill_color(background_color: tuple) -> tuple:
    """
    根据给定的背景色确定最佳的文本填充颜色（黑色或白色）。
    """
    luminance = (
        0.299 * background_color[0]
        + 0.587 * background_color[1]
        + 0.114 * background_color[2]
    ) / 255

    if luminance > 0.5:
        return (0, 0, 0, 255)
    else:
        return (255, 255, 255, 255)

def replace_text_with_translation(image: Image.Image, translated_data: list, config: configparser.ConfigParser, normalize_coordinates: bool | None = None) -> Image.Image:
    """
    在原始图片上绘制翻译后的文本，并为文本创建半透明背景。
    
    Args:
        image: 原始图片
        translated_data: 翻译数据列表
        config: 配置对象
        normalize_coordinates: 是否强制使用归一化坐标，None时从配置文件读取
    """
    img_width, img_height = image.size
    
    base_image = image.convert("RGBA")
    txt_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    transparency_alpha = config.getint('Image', 'text_box_transparency', fallback=180)
    discoloration_strength = config.getint('Image', 'background_discoloration_strength', fallback=40)
    background_margin = config.getint('Image', 'background_sample_margin', fallback=10)
    font_path = config.get('Image', 'font_path', fallback='font/font.ttf')
    
    # 读取归一化坐标配置
    if normalize_coordinates is None:
        normalize_coordinates = config.getboolean('Image', 'normalize_coordinates', fallback=False)
    
    log_debug(f"坐标模式: {'归一化坐标' if normalize_coordinates else '像素坐标'}")

    for item in translated_data:
        translated_text = item.get('text')
        if not translated_text:
            continue
            
        box = item.get('box')
        if not box or len(box) != 4:
            log_warning(f"跳过无效边界框的条目: {item}")
            continue

        # 根据归一化模式设置处理坐标
        if normalize_coordinates:
            # 归一化模式下，坐标应该在0-1范围内
            if all(0 <= coord <= 1 for coord in box):
                x_min = int(box[0] * img_width)
                y_min = int(box[1] * img_height)
                x_max = int(box[2] * img_width)
                y_max = int(box[3] * img_height)
                log_debug(f"归一化坐标转换: {box} -> 像素坐标: [{x_min}, {y_min}, {x_max}, {y_max}]")
            else:
                # 如果坐标不在0-1范围内，可能是像素坐标，直接使用
                log_warning(f"归一化模式下检测到非归一化坐标: {box}，尝试直接使用")
                x_min = int(box[0])
                y_min = int(box[1])
                x_max = int(box[2])
                y_max = int(box[3])
        else:
            # 像素坐标模式
            if all(0 <= coord <= 1 for coord in box):
                # 自动检测到归一化坐标，转换为像素坐标
                x_min = int(box[0] * img_width)
                y_min = int(box[1] * img_height)
                x_max = int(box[2] * img_width)
                y_max = int(box[3] * img_height)
                log_debug(f"自动检测归一化坐标: {box} -> 像素坐标: [{x_min}, {y_min}, {x_max}, {y_max}]")
            else:
                # 使用像素坐标
                x_min = int(box[0])
                y_min = int(box[1])
                x_max = int(box[2])
                y_max = int(box[3])
                log_debug(f"使用像素坐标: {box}")

        x_min = max(0, min(x_min, img_width))
        y_min = max(0, min(y_min, img_height))
        x_max = max(0, min(x_max, img_width))
        y_max = max(0, min(y_max, img_height))

        # 检查文本框是否有效
        box_width = x_max - x_min
        box_height = y_max - y_min
        if box_width <= 0 or box_height <= 0:
            log_warning(f"无效的文本框尺寸 ({box_width}x{box_height}) for {item.get('text', '')}, 跳过绘制。")
            continue

        background_color_rgb = get_background_color(image, x_min, y_min, x_max, y_max, background_margin)
        background_color_rgb = add_discoloration(background_color_rgb, discoloration_strength)
        background_color_rgba = background_color_rgb + (transparency_alpha,)

        draw.rectangle(((x_min, y_min), (x_max, y_max)), fill=background_color_rgba)

        # 使用新的基于面积的字体计算方法
        font, wrapped_lines, text_total_height, x_offset, y_offset = \
            get_wrapped_text_and_font_by_area(translated_text, box_width, box_height, font_path)
        
        if not font or not wrapped_lines:
            log_warning(f"无法为文本 '{translated_text}' 计算字体或分行，跳过绘制。")
            continue

        text_color_rgba = get_text_fill_color(background_color_rgb)

        # 逐行绘制文本
        current_y = y_min + y_offset
        line_height_base = font.getmask("M").getbbox()[3] if font.getmask("M").getbbox() else font.size
        line_spacing = max(2, font.size // 8)
        
        for line in wrapped_lines:
            # 重新计算本行的X偏移，使其居中
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            current_x_offset = (box_width - line_width) // 2
            
            draw.text(
                (x_min + current_x_offset, current_y),
                line,
                fill=text_color_rgba,
                font=font,
            )
            current_y += (line_height_base + line_spacing)
            
            # 如果当前行的底部超出了原始文本框的底部，停止绘制
            if current_y > y_max:
                log_debug(f"文本 '{line}' ( part of '{translated_text}') 超出界限，停止绘制。")
                break

    final_image = Image.alpha_composite(base_image, txt_layer)
    return final_image

# --- 主程序执行部分 ---
def main():
    """
    主执行函数，负责初始化翻译器、遍历输入文件夹、处理图片、
    以及保存翻译后的图片。
    """
    # 加载配置文件
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    if not os.path.exists(config_file):
        raise ValueError("配置文件无法读取")

    config.read(config_file, encoding='utf-8')
    log_info(f"已加载配置文件: {config_file}")
    if config.get('Translator', 'api_key') == 'None':
        raise ValueError("请填写好你的api密钥")
    
    # 读取归一化坐标配置
    normalize_coordinates = config.getboolean('Image', 'normalize_coordinates', fallback=False)
    translator = VLTranslator(config, normalize_coordinates)

    input_folder = "input"
    output_folder = "output"

    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(os.path.dirname(config.get('Image', 'font_path', fallback='font/font.ttf')), exist_ok=True)

    log_info(f"输入文件夹: {input_folder}")
    log_info(f"输出文件夹: {output_folder}")

    files_to_process = [f for f in os.listdir(input_folder) if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff"))]
    if not files_to_process:
        log_warning(f"输入文件夹 '{input_folder}' 中未找到支持的图片文件。请放入图片。")
        return

    for filename in files_to_process:
        log_info(f'\n正在处理图片: {filename}...')
        image_path = os.path.join(input_folder, filename)
        
        try:
            log_info('正在调用VL模型进行OCR识别和翻译...')
            translated_data = translator.ocr_and_translate(image_path)
            
            if not translated_data:
                log_warning(f'未在图片中检测到任何可翻译文本: {filename}。将跳过此图片。')
                continue
            
            log_info(f'成功检测到 {len(translated_data)} 个文字区域。')
            
            log_info('正在将翻译结果绘制到图片上...')
            original_image = Image.open(image_path)
            processed_image = replace_text_with_translation(original_image, translated_data, config)
            
            base_name, ext = os.path.splitext(filename)
            output_path = os.path.join(output_folder, f"{base_name}-translated{ext}")
            
            if output_path.lower().endswith((".jpg", ".jpeg")):
                log_info("检测到输出格式为JPEG，将图片转换为RGB模式以保存...")
                processed_image = processed_image.convert("RGB")

            processed_image.save(output_path)
            log_info(f'已保存翻译后的图片到: {os.path.basename(output_path)}')
            
        except Exception as e:
            log_error(f'处理文件 {filename} 时发生错误: {e}')
            continue
    
    log_info("\n所有图片处理完成。")


def process_image_translation(image_input, config_path='config.ini', normalize_coordinates=None):
    """
    图片翻译处理对外接口函数
    
    外部模块调用方法：
    1. 导入模块：from LLMtranslator import process_image_translation
    2. 准备配置文件：确保config.ini存在且包含必要的API配置
    3. 调用函数：
       - 传入图片路径：result = process_image_translation('path/to/image.jpg')
       - 传入PIL图片对象：result = process_image_translation(pil_image)
       - 指定配置文件：result = process_image_translation('image.jpg', 'custom_config.ini')
       - 强制使用归一化坐标：result = process_image_translation('image.jpg', normalize_coordinates=True)
    
    Args:
        image_input (str | PIL.Image.Image): 图片输入，可以是：
            - 图片文件路径字符串 (如: 'image.jpg')
            - PIL.Image.Image对象
        config_path (str, optional): 配置文件路径，默认为 'config.ini'
        normalize_coordinates (bool, optional): 是否强制使用归一化坐标模式，None时从配置文件读取
    
    Returns:
        dict: 处理结果字典，包含以下键值：
            - 'success' (bool): 处理是否成功
            - 'message' (str): 处理结果消息
            - 'translated_image' (PIL.Image.Image | None): 翻译后的图片对象，失败时为None
            - 'detected_texts' (list | None): 检测到的文字区域信息列表，失败时为None
            - 'error' (str | None): 错误信息，成功时为None
    
    示例：
        # 方式1：使用图片路径
        result = process_image_translation('input/test.jpg')
        if result['success']:
            result['translated_image'].save('output/translated.jpg')
            print(f"检测到{len(result['detected_texts'])}个文字区域")
        else:
            print(f"处理失败: {result['error']}")
        
        # 方式2：使用PIL图片对象
        from PIL import Image
        img = Image.open('test.jpg')
        result = process_image_translation(img)
        
        # 方式3：自定义配置文件
        result = process_image_translation('test.jpg', 'my_config.ini')
        
        # 方式4：强制使用归一化坐标
        result = process_image_translation('test.jpg', normalize_coordinates=True)
    """
    
    # 初始化返回结果
    result = {
        'success': False,
        'message': '',
        'translated_image': None,
        'detected_texts': None,
        'error': None
    }
    
    try:
        # 检查并加载配置文件
        if not os.path.exists(config_path):
            result['error'] = f"配置文件 '{config_path}' 不存在"
            result['message'] = "配置文件读取失败"
            return result
        
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # 检查API密钥
        if config.get('Translator', 'api_key', fallback='None') == 'None':
            result['error'] = "请在配置文件中设置有效的API密钥"
            result['message'] = "API密钥未配置"
            return result
        
        # 处理输入图片
        if isinstance(image_input, str):
            # 输入是文件路径
            if not os.path.exists(image_input):
                result['error'] = f"图片文件 '{image_input}' 不存在"
                result['message'] = "图片文件不存在"
                return result
            
            original_image = Image.open(image_input)
            image_path_for_api = image_input
        elif hasattr(image_input, 'mode') and hasattr(image_input, 'size'):
            # 输入是PIL Image对象
            original_image = image_input
            # 为API调用创建临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                original_image.save(tmp_file.name, 'PNG')
                image_path_for_api = tmp_file.name
        else:
            result['error'] = "输入必须是图片文件路径或PIL.Image对象"
            result['message'] = "输入类型错误"
            return result
        
        # 读取归一化坐标配置
        if normalize_coordinates is None:
            normalize_coordinates = config.getboolean('Image', 'normalize_coordinates', fallback=False)
        
        # 初始化翻译器
        translator = VLTranslator(config, normalize_coordinates)
        
        # 进行OCR识别和翻译
        translated_data = translator.ocr_and_translate(image_path_for_api)
        
        # 如果输入是PIL对象，清理临时文件
        if not isinstance(image_input, str):
            try:
                os.unlink(image_path_for_api)
            except:
                pass  # 忽略删除临时文件的错误
        
        if not translated_data:
            result['success'] = True
            result['message'] = "未检测到任何可翻译文本"
            result['translated_image'] = original_image.copy()
            result['detected_texts'] = []
            return result
        
        # 在图片上绘制翻译结果
        processed_image = replace_text_with_translation(original_image, translated_data, config, normalize_coordinates)
        
        # 成功处理
        result['success'] = True
        result['message'] = f"成功处理图片，检测到{len(translated_data)}个文字区域"
        result['translated_image'] = processed_image
        result['detected_texts'] = translated_data
        
        return result
        
    except Exception as e:
        result['error'] = str(e)
        result['message'] = "处理过程中发生错误"
        return result

if __name__ == "__main__":
    main()