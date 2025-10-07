#!/usr/bin/env python3
"""
LLM图片翻译工具 - NiceGUI独立窗口应用
基于LLMtranslator.py核心模块，提供图形化界面
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import configparser
from PIL import Image
import io
import base64

from nicegui import app, ui, events
from nicegui.elements.mixins.value_element import ValueElement

# 导入核心翻译模块
from LLMtranslator import process_image_translation


class ImageTranslatorApp:
    """图片翻译应用主类"""
    
    def __init__(self):
        self.config_path = "config.ini"
        self.current_image: Optional[Image.Image] = None
        self.translated_image: Optional[Image.Image] = None
        self.translated_data: Optional[list] = None
        self.is_processing = False
        self.config = configparser.ConfigParser()
        
        # 应用状态
        self.app_state = {
            'normalize_coordinates': False,
            'config_valid': False,
            'api_key_set': False
        }
        
        # 初始化配置
        self.load_config()
        
        # 构建界面
        self.setup_ui()
        
        # 设置键盘快捷键
        self.setup_keyboard_shortcuts()
    
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                self.config.read(self.config_path, encoding='utf-8')
                # 检查API密钥是否设置
                api_key = self.config.get('Translator', 'api_key', fallback='None')
                self.app_state['api_key_set'] = api_key != 'None'
                self.app_state['config_valid'] = True
                return True
            else:
                self.app_state['config_valid'] = False
                return False
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.app_state['config_valid'] = False
            return False
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def pil_to_base64(self, image: Optional[Image.Image]) -> str:
        """将PIL图片转换为base64字符串"""
        if image is None:
            return ""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    def setup_ui(self):
        """设置用户界面"""
        
        # 应用标题 - 简化设计
        with ui.header().classes('bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 shadow-lg'):
            with ui.row().classes('w-full justify-center items-center'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('translate', size='lg').classes('text-white')
                    ui.label('🌍 LLM图片翻译工具').classes('text-2xl font-bold tracking-tight')
        
        # 主内容区域 - 左右排布布局
        with ui.row().classes('w-full h-[calc(100vh-80px)] bg-gray-50'):
            # 左侧控制面板 - 固定宽度
            with ui.column().classes('w-[400px] h-full p-4 bg-white border-r border-gray-200 shadow-sm'):
                self.setup_control_panel()
            
            # 右侧图片对比区域 - 自适应宽度
            with ui.column().classes('flex-1 h-full p-4'):
                self.setup_image_comparison()
    
    def setup_control_panel(self):
        """设置左侧控制面板"""
        
        # 图片上传区域 - 优化视觉设计
        with ui.card().classes('w-full mb-4 shadow-md border-0 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('cloud_upload', color='primary', size='sm')
                ui.label('图片上传').classes('text-lg font-bold text-gray-800')
            
            # 上传组件 - 添加悬停效果
            self.upload = ui.upload(
                label='选择或拖拽图片文件',
                multiple=False,
                on_upload=self.handle_image_upload
            ).props('accept=".jpg,.jpeg,.png,.bmp,.gif" color=primary rounded').classes('w-full hover:shadow-md transition-shadow duration-200')
            
            # 支持的格式提示 - 优化样式
            with ui.row().classes('items-center gap-2 mt-2'):
                ui.icon('info', size='xs', color='gray-500')
                ui.label('支持格式: JPG, PNG, JPEG, BMP, GIF').classes('text-xs text-gray-600')
        
        # 翻译控制区域 - 优化按钮布局和交互
        with ui.card().classes('w-full mb-4 shadow-md border-0 rounded-xl bg-white'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('play_arrow', color='primary', size='sm')
                ui.label('翻译控制').classes('text-lg font-bold text-gray-800')
            
            # 按钮水平排列 - 优化间距和悬停效果
            with ui.row().classes('w-full gap-3'):
                # 翻译按钮 - 添加加载状态和快捷键标识
                self.translate_btn = ui.button(
                    '开始翻译',
                    on_click=self.start_translation,
                    icon='translate'
                ).props('color=primary rounded data-testid=translate-btn').classes('flex-1 hover:shadow-lg transition-all duration-200')
                
                # 重置按钮 - 添加快捷键标识
                self.reset_btn = ui.button(
                    '重置',
                    on_click=self.reset_app,
                    icon='refresh'
                ).props('color=secondary rounded data-testid=reset-btn').classes('flex-1 hover:shadow-md transition-all duration-200')
            
            # 保存按钮 - 优化视觉层次和快捷键标识
            self.save_btn = ui.button(
                '保存结果',
                on_click=self.save_result,
                icon='save'
            ).props('color=positive rounded data-testid=save-btn').classes('w-full mt-3 hover:shadow-lg transition-all duration-200')
            
            # 快捷键提示
            ui.label('快捷键: Ctrl+T (翻译) | Ctrl+R (重置) | Ctrl+S (保存)').classes('text-xs text-gray-500 mt-2 text-center')
        
        # 翻译器配置区域
        with ui.card().classes('w-full mb-4 shadow-md border-0 rounded-xl bg-white'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('translate', color='primary', size='sm')
                ui.label('翻译器配置').classes('text-lg font-bold text-gray-800')
            
            # API密钥设置
            with ui.row().classes('w-full items-center mb-3'):
                ui.label('API密钥:').classes('w-24 font-medium text-gray-700')
                self.api_key_input = ui.input(
                    value=self.config.get('Translator', 'api_key', fallback=''),
                    on_change=lambda e: self.update_translator_config('api_key', e.value)
                ).props('dense outlined type=password').classes('flex-1 bg-gray-50')
            
            # API基础地址
            with ui.row().classes('w-full items-center mb-3'):
                ui.label('API地址:').classes('w-24 font-medium text-gray-700')
                self.api_base_input = ui.input(
                    value=self.config.get('Translator', 'api_base', fallback=''),
                    on_change=lambda e: self.update_translator_config('api_base', e.value)
                ).props('dense outlined').classes('flex-1 bg-gray-50')
            
            # 模型名称
            with ui.row().classes('w-full items-center mb-3'):
                ui.label('模型名称:').classes('w-24 font-medium text-gray-700')
                self.model_name_input = ui.input(
                    value=self.config.get('Translator', 'model_name', fallback=''),
                    on_change=lambda e: self.update_translator_config('model_name', e.value)
                ).props('dense outlined').classes('flex-1 bg-gray-50')
        
        # 图片处理配置区域
        with ui.card().classes('w-full mb-4 shadow-md border-0 rounded-xl bg-white'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('image', color='primary', size='sm')
                ui.label('图片处理配置').classes('text-lg font-bold text-gray-800')
            
            # 文本框透明度
            with ui.row().classes('w-full items-center mb-3'):
                ui.label('文本框透明度:').classes('w-32 font-medium text-gray-700')
                self.transparency_input = ui.number(
                    value=int(self.config.get('Image', 'text_box_transparency', fallback=180)),
                    min=0,
                    max=255,
                    on_change=lambda e: self.update_image_config('text_box_transparency', str(int(e.value)))
                ).props('dense outlined').classes('flex-1 bg-gray-50')
            
            # 背景褪色强度
            with ui.row().classes('w-full items-center mb-3'):
                ui.label('背景褪色强度:').classes('w-32 font-medium text-gray-700')
                self.discoloration_input = ui.number(
                    value=int(self.config.get('Image', 'background_discoloration_strength', fallback=40)),
                    min=0,
                    max=100,
                    on_change=lambda e: self.update_image_config('background_discoloration_strength', str(int(e.value)))
                ).props('dense outlined').classes('flex-1 bg-gray-50')
            
            # 背景采样边距
            with ui.row().classes('w-full items-center mb-3'):
                ui.label('采样边距:').classes('w-32 font-medium text-gray-700')
                self.margin_input = ui.number(
                    value=int(self.config.get('Image', 'background_sample_margin', fallback=10)),
                    min=0,
                    max=50,
                    on_change=lambda e: self.update_image_config('background_sample_margin', str(int(e.value)))
                ).props('dense outlined').classes('flex-1 bg-gray-50')
            
            # 字体路径
            with ui.row().classes('w-full items-center mb-3'):
                ui.label('字体路径:').classes('w-32 font-medium text-gray-700')
                self.font_path_input = ui.input(
                    value=self.config.get('Image', 'font_path', fallback='font/font.ttf'),
                    on_change=lambda e: self.update_image_config('font_path', e.value)
                ).props('dense outlined').classes('flex-1 bg-gray-50')
            
            # 归一化坐标模式
            with ui.row().classes('w-full items-center mb-2'):
                self.normalize_checkbox = ui.checkbox(
                    '使用归一化坐标模式',
                    value=self.config.getboolean('Image', 'normalize_coordinates', fallback=False),
                    on_change=lambda e: self.update_image_config('normalize_coordinates', str(e.value).lower())
                ).classes('flex-1')
                ui.tooltip('适用于某些压缩图片分辨率的API供应商').classes('text-xs')
            
            # 配置状态显示 - 优化视觉反馈
            with ui.row().classes('w-full items-center'):
                config_status = '✅ 配置有效' if self.app_state['config_valid'] else '❌ 配置无效'
                api_status = '✅ API密钥已设置' if self.app_state['api_key_set'] else '❌ API密钥未设置'
                status_color = 'bg-green-100 text-green-800' if self.app_state['config_valid'] and self.app_state['api_key_set'] else 'bg-red-100 text-red-800'
                ui.label(f'{config_status} | {api_status}').classes(f'text-sm px-3 py-2 rounded-lg {status_color} font-medium')
        
        # 状态显示区域 - 优化信息展示
        with ui.card().classes('w-full shadow-md border-0 rounded-xl bg-white'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('info', color='primary', size='sm')
                ui.label('状态信息').classes('text-lg font-bold text-gray-800')
            
            # 状态显示 - 优化视觉反馈
            self.status_label = ui.label('等待上传图片...').classes('text-sm mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800')
            
            # 进度指示器 - 优化视觉效果
            self.progress = ui.linear_progress(0).props('color=primary').classes('w-full mb-3 h-2 rounded-full')
            self.progress.visible = False
            
            # 检测信息显示 - 优化文本区域样式
            self.detection_info = ui.textarea(
                label='检测信息',
                placeholder='检测到的文字区域信息将显示在这里...'
            ).props('readonly outlined dense rows=5 bg-grey-2').classes('w-full border-gray-200')
    
    def setup_image_comparison(self):
        """设置右侧图片对比区域"""
        
        # 图片对比标题
        with ui.row().classes('w-full justify-center mb-4'):
            ui.label('🔄 图片对比').classes('text-2xl font-bold text-gray-800')
        
        # 图片对比容器 - 左右并排布局
        with ui.grid().classes('w-full h-[calc(100%-60px)] gap-6 grid-cols-2'):
            # 左侧原图区域
            with ui.column().classes('h-full bg-white rounded-lg shadow-md border border-gray-200'):
                with ui.column().classes('w-full h-full p-4'):
                    # 原图标题
                    with ui.row().classes('w-full justify-center mb-4'):
                        ui.label('📷 原图').classes('text-xl font-bold text-blue-600')
                    
                    # 原图显示区域 - 自适应大小
                    with ui.column().classes('flex-1 w-full items-center justify-center border-2 border-dashed border-blue-200 rounded-lg bg-blue-50 p-4'):
                        self.original_image = ui.image().classes('max-w-full max-h-full object-contain')
                        ui.label('请上传图片开始翻译').classes('text-center text-gray-500 mt-4').bind_visibility_from(
                            self.original_image, 'src', lambda src: not src
                        )
                    
                    # 原图操作按钮
                    with ui.row().classes('w-full justify-center gap-2 mt-4').bind_visibility_from(self.original_image, 'src'):
                        ui.button('下载原图', on_click=self.download_original, icon='download').props('outline color=primary rounded')
                        ui.button('放大查看', on_click=lambda: self.show_image_modal('original'), icon='zoom_in').props('outline color=secondary rounded')
            
            # 右侧翻译结果区域
            with ui.column().classes('h-full bg-white rounded-lg shadow-md border border-gray-200'):
                with ui.column().classes('w-full h-full p-4'):
                    # 翻译结果标题
                    with ui.row().classes('w-full justify-center mb-4'):
                        ui.label('✅ 翻译结果').classes('text-xl font-bold text-green-600')
                    
                    # 翻译结果显示区域 - 自适应大小
                    with ui.column().classes('flex-1 w-full items-center justify-center border-2 border-dashed border-green-200 rounded-lg bg-green-50 p-4'):
                        self.translated_image_display = ui.image().classes('max-w-full max-h-full object-contain')
                        ui.label('翻译结果将显示在这里').classes('text-center text-gray-500 mt-4').bind_visibility_from(
                            self.translated_image_display, 'src', lambda src: not src
                        )
                    
                    # 翻译结果操作按钮
                    with ui.row().classes('w-full justify-center gap-2 mt-4').bind_visibility_from(self.translated_image_display, 'src'):
                        ui.button('下载翻译结果', on_click=self.download_translated, icon='download').props('outline color=positive rounded')
                        ui.button('放大查看', on_click=lambda: self.show_image_modal('translated'), icon='zoom_in').props('outline color=secondary rounded')
    
    async def handle_image_upload(self, e: events.UploadEventArguments):
        """处理图片上传"""
        try:
            self.status_label.set_text('🔄 正在处理上传的图片...')
            self.progress.visible = True
            self.progress.value = 0.3
            
            # 读取上传的图片
            content = e.content.read()
            image = Image.open(io.BytesIO(content))
            self.current_image = image
            
            # 显示原图
            image_base64 = self.pil_to_base64(image)
            self.original_image.set_source(image_base64)
            
            self.progress.value = 1.0
            await asyncio.sleep(0.5)  # 让进度条完成动画
            self.progress.visible = False
            
            # 获取图片信息用于状态显示
            width, height = image.size
            file_size = len(content) / 1024  # KB
            
            self.status_label.set_text(f'✅ 图片上传成功 ({width}×{height}, {file_size:.1f}KB)，可以开始翻译')
            self.translate_btn.enable()
            
            ui.notify(f'📷 图片上传成功: {width}×{height}', type='positive')
            
        except Exception as ex:
            self.status_label.set_text(f'❌ 图片处理失败: {str(ex)}')
            self.progress.visible = False
            ui.notify(f'❌ 图片上传失败: {str(ex)}', type='negative')
    
    def update_config_path(self, new_path: str):
        """更新配置文件路径"""
        self.config_path = new_path
        self.load_config()
    
    def update_translator_config(self, key: str, value: str):
        """更新翻译器配置"""
        if not self.config.has_section('Translator'):
            self.config.add_section('Translator')
        self.config.set('Translator', key, value)
        self.save_config()
        self.load_config()  # 重新加载配置以更新状态
        ui.notify(f'翻译器配置已更新: {key}', type='positive')
    
    def update_image_config(self, key: str, value: str):
        """更新图片处理配置"""
        if not self.config.has_section('Image'):
            self.config.add_section('Image')
        self.config.set('Image', key, value)
        self.save_config()
        ui.notify(f'图片配置已更新: {key}', type='positive')
    
    def update_normalize_mode(self, enabled: bool):
        """更新归一化坐标模式"""
        self.app_state['normalize_coordinates'] = enabled
    
    async def start_translation(self):
        """开始翻译过程"""
        if not self.current_image:
            ui.notify('📷 请先上传图片', type='warning')
            return
        
        if not self.app_state['config_valid']:
            ui.notify('⚙️ 配置文件无效，请检查配置路径', type='negative')
            return
        
        if not self.app_state['api_key_set']:
            ui.notify('🔑 API密钥未设置，请在配置文件中设置有效的API密钥', type='negative')
            return
        
        try:
            self.is_processing = True
            self.translate_btn.disable()
            self.progress.visible = True
            self.progress.value = 0.2
            self.status_label.set_text('🔄 正在调用VL模型进行OCR识别和翻译...')
            
            # 更新按钮状态显示加载中
            self.translate_btn.props('loading')
            
            # 异步执行翻译任务
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                process_image_translation,
                self.current_image,
                self.config_path,
                self.app_state['normalize_coordinates']
            )
            
            self.progress.value = 0.8
            
            if result['success']:
                self.translated_image = result['translated_image']
                self.translated_data = result['detected_texts']
                
                # 显示翻译结果
                if self.translated_image:
                    translated_base64 = self.pil_to_base64(self.translated_image)
                    self.translated_image_display.set_source(translated_base64)
                
                # 更新检测信息 - 优化显示格式
                if self.translated_data:
                    info_text = f"✅ 翻译成功！\n\n📊 检测统计:\n"
                    info_text += f"• 检测到 {len(self.translated_data)} 个文字区域\n"
                    info_text += f"• 处理时间: {result.get('processing_time', '未知')}\n\n"
                    info_text += "📝 检测详情:\n"
                    for i, text_area in enumerate(self.translated_data, 1):
                        if isinstance(text_area, dict) and 'text' in text_area:
                            original_text = text_area.get('text', '')
                            translated_text = text_area.get('translated_text', '')
                            info_text += f"区域{i}:\n"
                            info_text += f"  原文: {original_text}\n"
                            if translated_text:
                                info_text += f"  译文: {translated_text}\n"
                            if 'box' in text_area:
                                info_text += f"  位置: {text_area['box']}\n"
                            info_text += "\n"
                    self.detection_info.set_value(info_text)
                else:
                    self.detection_info.set_value("✅ 翻译成功！\n\n📊 检测统计:\n• 未检测到文字区域\n• 图片可能不包含可识别文字")
                
                self.status_label.set_text(f'✅ {result["message"]}')
                ui.notify('🎉 翻译完成！', type='positive')
                
            else:
                self.status_label.set_text(f'❌ 翻译失败: {result["error"]}')
                ui.notify(f'❌ 翻译失败: {result["error"]}', type='negative')
            
        except Exception as ex:
            self.status_label.set_text(f'❌ 翻译过程中发生错误: {str(ex)}')
            ui.notify(f'❌ 处理错误: {str(ex)}', type='negative')
        
        finally:
            self.is_processing = False
            self.translate_btn.enable()
            self.translate_btn.props(remove='loading')
            self.progress.visible = False
    
    def reset_app(self):
        """重置应用状态"""
        self.current_image = None
        self.translated_image = None
        self.translated_data = None
        
        # 清除图片显示
        self.original_image.set_source('')
        self.translated_image_display.set_source('')
        self.detection_info.set_value('')
        self.status_label.set_text('等待上传图片...')
        
        ui.notify('应用已重置', type='info')
    
    def save_result(self):
        """保存翻译结果"""
        if not self.translated_image:
            ui.notify('没有可保存的翻译结果', type='warning')
            return
        
        try:
            # 创建输出目录
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # 生成输出文件名
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"translated_{timestamp}.png"
            
            # 保存图片
            self.translated_image.save(output_path, "PNG")
            
            ui.notify(f'图片已保存到: {output_path}', type='positive')
            self.status_label.set_text(f'✅ 结果已保存到: {output_path}')
            
        except Exception as ex:
            ui.notify(f'保存失败: {str(ex)}', type='negative')
            self.status_label.set_text(f'❌ 保存失败: {str(ex)}')
    
    def download_original(self):
        """下载原图"""
        if not self.current_image:
            ui.notify('没有可下载的原图', type='warning')
            return
        
        try:
            # 创建输出目录
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # 生成输出文件名
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"original_{timestamp}.png"
            
            # 保存图片
            self.current_image.save(output_path, "PNG")
            
            ui.notify(f'原图已保存到: {output_path}', type='positive')
            
        except Exception as ex:
            ui.notify(f'下载原图失败: {str(ex)}', type='negative')
    
    def download_translated(self):
        """下载翻译结果"""
        if not self.translated_image:
            ui.notify('没有可下载的翻译结果', type='warning')
            return
        
        try:
            # 创建输出目录
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # 生成输出文件名
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"translated_{timestamp}.png"
            
            # 保存图片
            self.translated_image.save(output_path, "PNG")
            
            ui.notify(f'✅ 翻译结果已保存到: {output_path}', type='positive')
            
        except Exception as ex:
            ui.notify(f'❌ 下载翻译结果失败: {str(ex)}', type='negative')
    
    def show_image_modal(self, image_type: str):
        """显示图片模态框用于放大查看"""
        if image_type == 'original' and not self.current_image:
            ui.notify('没有可查看的原图', type='warning')
            return
        elif image_type == 'translated' and not self.translated_image:
            ui.notify('没有可查看的翻译结果', type='warning')
            return
        
        # 创建模态框
        with ui.dialog().props('maximized') as dialog, ui.card().classes('w-full h-full bg-white'):
            with ui.column().classes('w-full h-full'):
                # 标题栏
                with ui.row().classes('w-full justify-between items-center p-4 border-b'):
                    title = '原图预览' if image_type == 'original' else '翻译结果预览'
                    ui.label(f'🔍 {title}').classes('text-xl font-bold')
                    ui.button('关闭', on_click=dialog.close, icon='close').props('flat round')
                
                # 图片显示区域
                with ui.column().classes('w-full h-full items-center justify-center p-8'):
                    if image_type == 'original':
                        image_base64 = self.pil_to_base64(self.current_image)
                    else:
                        image_base64 = self.pil_to_base64(self.translated_image)
                    
                    ui.image(image_base64).classes('max-w-full max-h-full object-contain')
        
        dialog.open()
    
    def setup_keyboard_shortcuts(self):
        """设置键盘快捷键"""
        # 使用JavaScript实现键盘快捷键
        ui.add_head_html('''
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey) {
                switch(e.key) {
                    case 't':
                        e.preventDefault();
                        // 触发翻译按钮点击
                        const translateBtn = document.querySelector('[data-testid="translate-btn"]');
                        if (translateBtn && !translateBtn.disabled) {
                            translateBtn.click();
                        }
                        break;
                    case 'r':
                        e.preventDefault();
                        // 触发重置按钮点击
                        const resetBtn = document.querySelector('[data-testid="reset-btn"]');
                        if (resetBtn) {
                            resetBtn.click();
                        }
                        break;
                    case 's':
                        e.preventDefault();
                        // 触发保存按钮点击
                        const saveBtn = document.querySelector('[data-testid="save-btn"]');
                        if (saveBtn) {
                            saveBtn.click();
                        }
                        break;
                }
            }
        });
        </script>
        ''')


def main():
    """主函数"""
    # 创建应用实例
    translator_app = ImageTranslatorApp()
    
    # 设置窗口标题和大小
    ui.page_title('LLM图片翻译工具')
    
    # 启动应用（独立窗口模式）
    ui.run(
        title='LLM图片翻译工具',
        native=True,  # 启用独立窗口模式
        window_size=(1200, 800),
        fullscreen=False,
        reload=False
    )


if __name__ == "__main__":
    main()