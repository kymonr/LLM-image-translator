from PIL import Image, ImageDraw, ImageFont
import os
import requests
import json
import base64
import re
from io import BytesIO
import configparser
from colorama import Fore, Style, init

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
    def __init__(self, config: configparser.ConfigParser):
        """
        初始化VLTranslator实例。

        Args:
            config (configparser.ConfigParser): 配置对象，用于读取API设置。
        """
        self.api_key = config.get('Translator', 'api_key')
        self.api_base = config.get('Translator', 'api_base', fallback='https://api.siliconflow.cn').rstrip("/")
        self.model = config.get('Translator', 'model_name', fallback='Qwen/Qwen2.5-VL-32B-Instruct')
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
        log_debug(f"API Base: {self.api_base}, Model: {self.model}")

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
            if response is not None:
                log_error(f"HTTP状态码: {response.status_code}, 响应: {response.text}")
            raise
        except json.JSONDecodeError as e:
            log_error(f"解析API响应JSON失败: {e}, 响应内容: {response.text if response else '无'}")
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

def get_wrapped_text_and_font(text: str, width: int, height: int, font_path: str = "font/font.ttf") -> tuple:
    """
    根据给定的文本区域大小，计算并返回最适合绘制文本的字体大小，
    并进行自动换行。

    Args:
        text (str): 需要计算字体大小和换行的文本字符串。
        width (int): 文本框的宽度。
        height (int): 文本框的高度。
        font_path (str): 字体文件的路径。

    Returns:
        tuple: 包含以下元素的元组：
               - font (PIL.ImageFont.FreeTypeFont): 最佳字体对象。
               - wrapped_lines (list[str]): 包含分行后文本的列表。
               - text_height (int): 文本绘制后的总高度。
               - x_offset (int): 文本在x轴上的居中偏移量。
               - y_offset (int): 文本在y轴上的居中偏移量。
    """
    if not text:
        return None, [], 0, 0, 0

    font_path = os.path.abspath(font_path) # 确保字体路径是绝对路径
    try:
        ImageFont.truetype(font_path, size=10) # 预检查字体文件是否存在
    except OSError:
        log_warning(f"字体文件 '{font_path}' 未找到或损坏，使用PIL默认字体。")
        font_path = None # 使用None表示后续用默认字体

    best_font = None
    best_wrapped_lines = []
    best_text_height = 0
    best_x_offset = 0
    best_y_offset = 0

    # 创建一个临时的、不关联任何实际图像的 ImageDraw 对象，仅用于测量文本尺寸。
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    for size in range(1, 500): # 尝试从小到大的字体尺寸
        try:
            if font_path:
                current_font = ImageFont.truetype(font_path, size=size)
            else:
                current_font = ImageFont.load_default()
        except OSError:
            # 如果加载失败，继续尝试下一个大小，或者直接跳出
            break 
        
        # 尝试按单词边界或字符进行换行
        lines = []
        current_line = []
        words = text.split(' ') # 先按空格分割
        if not words: # 如果是中文等没有空格的文本
             words = list(text) # 按字符分割

        for word in words:
            # 尝试将单词添加到当前行
            test_line_text = ' '.join(current_line + [word])
            bbox = dummy_draw.textbbox((0, 0), test_line_text, font=current_font)
            text_w = bbox[2] - bbox[0]
            
            if text_w <= width: # 如果当前行加上新单词没有超出宽度
                current_line.append(word)
            else: # 超出宽度，进行换行
                if current_line: # 如果当前行有内容，先保存这行
                    lines.append(' '.join(current_line))
                current_line = [word] # 新行从当前单词开始
                # 检查单个单词是否就超出了宽度（对于很长的单词或无空格的中文）
                single_word_bbox = dummy_draw.textbbox((0, 0), word, font=current_font)
                if single_word_bbox[2] - single_word_bbox[0] > width:
                    # 如果单个单词就超出宽度，强制按字符切分
                    temp_word_line = ''
                    for char in word:
                        test_char_line_text = temp_word_line + char
                        char_bbox = dummy_draw.textbbox((0, 0), test_char_line_text, font=current_font)
                        if char_bbox[2] - char_bbox[0] <= width:
                            temp_word_line += char
                        else:
                            if temp_word_line:
                                lines.append(temp_word_line)
                            temp_word_line = char
                    if temp_word_line:
                        lines.append(temp_word_line)
                    current_line = [] # 强制切分后，当前行清空
        
        if current_line: # 添加最后一行
            lines.append(' '.join(current_line))

        # 计算总高度
        line_height = current_font.getmask("A").getbbox()[3] if current_font.getmask("A").getbbox() else size # 获取单行高度
        
        # 对于多行文本，增加行间距或简单乘行数
        total_text_height = line_height * len(lines)
        if len(lines) > 1 : # 针对多行文本做微调
             total_text_height += (len(lines) -1) * (current_font.size // 5) # 简单增加行间距

        # 检查是否超出文本框总高度
        if total_text_height > height:
            break # 超出高度，停止增大字体

        # 找到最长行的宽度用于居中计算
        max_line_width = 0
        for line in lines:
            line_bbox = dummy_draw.textbbox((0, 0), line, font=current_font)
            max_line_width = max(max_line_width, line_bbox[2] - line_bbox[0])

        # 如果最长行宽度超出区域，则也停止增大字体
        if max_line_width > width:
            break

        # 更新最佳字体和相关尺寸信息
        best_font = current_font
        best_wrapped_lines = lines
        best_text_height = total_text_height
        
        # 计算文本在给定区域内的居中偏移量 (基于最长行宽度和总高度)
        best_x_offset = (width - max_line_width) // 2 
        best_y_offset = (height - best_text_height) // 2
        
    # 如果循环结束后best_font仍然为None（意味着文本过大，即使最小字体也超出），
    # 则返回一个默认字体并尽可能多的文本
    if best_font is None:
        try:
            if font_path:
                best_font = ImageFont.truetype(font_path, size=1)
            else:
                best_font = ImageFont.load_default()
        except OSError:
            best_font = ImageFont.load_default() # 最终兜底

        # 重新计算一次，用最小字体尝试分行，避免完全空行
        lines = []
        current_line = []
        words = text.split(' ')
        if not words:
             words = list(text)

        for word in words:
            test_line_text = ' '.join(current_line + [word])
            bbox = dummy_draw.textbbox((0, 0), test_line_text, font=best_font)
            text_w = bbox[2] - bbox[0]
            
            if text_w <= width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                single_word_bbox = dummy_draw.textbbox((0, 0), word, font=best_font)
                if single_word_bbox[2] - single_word_bbox[0] > width:
                    temp_word_line = ''
                    for char in word:
                        test_char_line_text = temp_word_line + char
                        char_bbox = dummy_draw.textbbox((0, 0), test_char_line_text, font=best_font)
                        if char_bbox[2] - char_bbox[0] <= width:
                            temp_word_line += char
                        else:
                            if temp_word_line:
                                lines.append(temp_word_line)
                            temp_word_line = char
                    if temp_word_line:
                        lines.append(temp_word_line)
                    current_line = []
        if current_line:
            lines.append(' '.join(current_line))
        
        best_wrapped_lines = lines
        line_height = best_font.getmask("A").getbbox()[3] if best_font.getmask("A").getbbox() else 1
        best_text_height = line_height * len(lines)
        if len(lines) > 1 : 
             best_text_height += (len(lines) -1) * (best_font.size // 5)
        
        max_line_width = 0
        for line in lines:
            line_bbox = dummy_draw.textbbox((0, 0), line, font=best_font)
            max_line_width = max(max_line_width, line_bbox[2] - line_bbox[0])

        best_x_offset = max(0, (width - max_line_width) // 2)
        best_y_offset = (height - best_text_height) // 2

        log_warning(f"文本 '{text}' 无法完全适应给定区域 [{width}x{height}]。将使用最小字体和强制换行。")


    return best_font, best_wrapped_lines, best_text_height, best_x_offset, best_y_offset

def add_discoloration(color: tuple, strength: int) -> tuple:
    """
    调整RGB颜色值以增加一些“褪色”效果，使其不那么鲜艳或与背景有一定区分度。
    """
    r, g, b = color
    r = max(0, min(255, r + strength))
    g = max(0, min(255, g + strength))
    b = max(0, min(255, b + strength))
    
    if r == 255 and g == 255 and b == 255:
        r, g, b = 245, 245, 245

    return (r, g, b)

def get_background_color(image: Image.Image, x_min: int, y_min: int, x_max: int, y_max: int, margin: int) -> tuple:
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
    return background_color

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

def replace_text_with_translation(image: Image.Image, translated_data: list, config: configparser.ConfigParser) -> Image.Image:
    """
    在原始图片上绘制翻译后的中文文本，并为文本创建半透明背景。
    """
    img_width, img_height = image.size
    
    base_image = image.convert("RGBA")
    txt_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    transparency_alpha = config.getint('Image', 'text_box_transparency', fallback=180)
    discoloration_strength = config.getint('Image', 'background_discoloration_strength', fallback=40)
    background_margin = config.getint('Image', 'background_sample_margin', fallback=10)
    font_path = config.get('Image', 'font_path', fallback='font/font.ttf')

    for item in translated_data:
        translated_text = item.get('text')
        if not translated_text:
            continue
            
        box = item.get('box')
        if not box or len(box) != 4:
            log_warning(f"跳过无效边界框的条目: {item}")
            continue

        if all(0 <= coord <= 1 for coord in box):
            x_min = int(box[0] * img_width)
            y_min = int(box[1] * img_height)
            x_max = int(box[2] * img_width)
            y_max = int(box[3] * img_height)
        else:
            x_min = int(box[0])
            y_min = int(box[1])
            x_max = int(box[2])
            y_max = int(box[3])

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

        # 获取字体和分行文本
        font, wrapped_lines, text_total_height, x_offset, y_offset = \
            get_wrapped_text_and_font(translated_text, box_width, box_height, font_path)
        
        if not font or not wrapped_lines:
            log_warning(f"无法为文本 '{translated_text}' 计算字体或分行，跳过绘制。")
            continue

        text_color_rgba = get_text_fill_color(background_color_rgb)

        # 逐行绘制文本
        current_y = y_min + y_offset
        # 估算行高 (假设行高接近字体大小，更精确的计算需要getfontbbox或getmask)
        # PIL的getbbox在textbbox之后已经包含descender，但这里我们还需要line-to-line的步进
        # 这里用font.size估算，或者更精确的用font.getmask('A').getbbox()[3] if available
        line_height_base = font.getmask("M").getbbox()[3] if font.getmask("M").getbbox() else font.size
        line_spacing = font.size // 5 # 行间距
        
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
            current_y += (line_height_base + line_spacing) # 移动到下一行的Y坐标
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
    
    translator = VLTranslator(config)

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

if __name__ == "__main__":
    main()
