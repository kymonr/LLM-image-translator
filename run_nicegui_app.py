#!/usr/bin/env python3
"""
LLM图片翻译工具 - NiceGUI应用启动脚本
"""

import os
import sys

def safe_print(text):
    """安全打印，处理Windows编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        # 如果遇到编码问题，使用ASCII替代
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import nicegui
        import PIL
        import requests
        import colorama
        import configparser
        safe_print("所有依赖已安装")
        return True
    except ImportError as e:
        safe_print(f"缺少依赖: {e}")
        safe_print("请运行: pip install -r requirements.txt")
        return False

def check_config():
    """检查配置文件"""
    if not os.path.exists("config.ini"):
        safe_print("警告: config.ini 文件不存在")
        if os.path.exists("config.ini.example"):
            safe_print("正在从 config.ini.example 创建 config.ini...")
            import shutil
            shutil.copy("config.ini.example", "config.ini")
            safe_print("已创建 config.ini，请编辑文件设置API密钥")
        else:
            safe_print("config.ini.example 也不存在，请确保配置文件存在")
            return False
    return True

def main():
    """主函数"""
    safe_print("LLM图片翻译工具 - NiceGUI版本")
    safe_print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置
    if not check_config():
        safe_print("请确保配置文件正确设置后再运行应用")
        sys.exit(1)
    
    # 检查核心模块
    if not os.path.exists("LLMtranslator.py"):
        safe_print("LLMtranslator.py 核心模块不存在")
        sys.exit(1)
    
    safe_print("环境检查通过")
    safe_print("正在启动NiceGUI应用...")
    
    # 导入并启动应用
    try:
        from nicegui_app import main as app_main
        app_main()
    except Exception as e:
        safe_print(f"启动应用失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()