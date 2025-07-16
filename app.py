import gradio as gr
from PIL import Image
import os
from LLMtranslator import process_image_translation

def translate_image(image_input, config_path="config.ini"):
    """
    Gradio界面的图片翻译函数
    
    Args:
        image_input: Gradio上传的图片文件
        config_path: 配置文件路径
    
    Returns:
        tuple: (翻译后的图片, 状态消息, 检测到的文字信息)
    """
    
    if image_input is None:
        return None, "❌ 请上传图片", ""
    
    try:
        # 将Gradio的图片输入转换为PIL图片对象
        if isinstance(image_input, str):
            # 如果是文件路径
            pil_image = Image.open(image_input)
        else:
            # 如果已经是PIL图片对象
            pil_image = image_input
        
        # 调用翻译函数
        result = process_image_translation(pil_image, config_path)
        
        if result['success']:
            # 成功处理
            translated_image = result['translated_image']
            detected_texts = result['detected_texts']
            
            # 构建检测信息
            if detected_texts:
                text_info = f"✅ 翻译成功！\n检测到 {len(detected_texts)} 个文字区域"
                # 可以添加更多详细信息
                for i, text_area in enumerate(detected_texts, 1):
                    if isinstance(text_area, dict) and 'text' in text_area:
                        text_info += f"\n区域{i}: {text_area['text']}"
            else:
                text_info = "✅ 翻译成功！\n未检测到文字区域"
            
            return translated_image, result['message'], text_info
        else:
            # 处理失败
            error_msg = f"❌ 翻译失败: {result['error']}"
            return None, error_msg, ""
            
    except Exception as e:
        return None, f"❌ 发生错误: {str(e)}", ""

def main():
    """主函数，创建Gradio界面"""
    
    # 创建Gradio界面
    with gr.Blocks(title="图片翻译工具", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🌍 图片翻译工具")
        gr.Markdown("上传图片，自动检测并翻译图片中的文字")
        
        with gr.Row():
            # 左侧输入区域
            with gr.Column(scale=1):
                gr.Markdown("## 📤 输入")
                image_input = gr.Image(
                    label="上传图片",
                    type="pil",
                    height=400
                )
                
                config_input = gr.Textbox(
                    label="配置文件路径",
                    value="config.ini",
                    placeholder="输入配置文件路径，默认为 config.ini"
                )
                
                translate_btn = gr.Button(
                    "🔄 开始翻译",
                    variant="primary",
                    size="lg"
                )
            
            # 右侧输出区域
            with gr.Column(scale=1):
                gr.Markdown("## 📥 输出")
                image_output = gr.Image(
                    label="翻译后的图片",
                    height=400
                )
                
                status_output = gr.Textbox(
                    label="处理状态",
                    lines=2,
                    interactive=False
                )
                
                text_info_output = gr.Textbox(
                    label="检测到的文字信息",
                    lines=5,
                    interactive=False
                )
        
        # 示例图片区域
        gr.Markdown("## 📋 使用说明")
        gr.Markdown("""
        1. **上传图片**: 点击上传区域选择包含文字的图片
        2. **配置文件**: 确保 `config.ini` 存在并包含必要的API配置
        3. **开始翻译**: 点击翻译按钮开始处理
        4. **查看结果**: 翻译完成后可以查看结果和检测信息
        
        **支持的图片格式**: JPG, PNG, JPEG, BMP, GIF 等
        """)
        
        # 绑定事件
        translate_btn.click(
            fn=translate_image,
            inputs=[image_input, config_input],
            outputs=[image_output, status_output, text_info_output]
        )
    
    return demo

if __name__ == "__main__":
    # 检查配置文件是否存在
    if not os.path.exists("config.ini"):
        print("⚠️  警告: config.ini 文件不存在，请确保配置文件正确设置")
    
    # 启动Gradio应用
    demo = main()
    demo.launch(
        server_name="0.0.0.0",  # 允许外部访问
        server_port=7860,       # 端口号
        share=False,            # 是否创建公共链接
        debug=True              # 调试模式
    )