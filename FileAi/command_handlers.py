import os
import time
from typing import Optional, Dict, Any, List, Tuple
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent
from nonebot.log import logger
from pathlib import Path
from nonebot import get_plugin_config
from .config import Config
from .models import ModelManager, AVAILABLE_MODELS, MODEL_INFO, VISION_MODEL_INFO
from .api_client import KimiApiClient
from .file_handler import get_file_url
from .utils import download_file, cleanup_files, is_supported_file_format, MAX_FILE_SIZE_BYTES

async def handle_image_analysis(bot: Bot, event: MessageEvent, image_url: str, question: str) -> str:
    """
    处理图像分析命令
    
    :param bot: 机器人实例
    :param event: 消息事件
    :param image_url: 图片URL
    :param question: 用户问题
    :return: 回复消息
    """
    # 开始计时
    start_time = time.time()
    
    # 获取配置
    config_dict = get_plugin_config(Config)

    api_key = config_dict.CONFIG.get("kimi_api_key", "")
    api_base_url = config_dict.CONFIG.get("kimi_api_base_url", "")
    
    if not api_key or not api_base_url:
        return "API配置错误，请联系管理员设置正确的API密钥和地址"
    
    # 加载模型配置
    model_manager = ModelManager()
    current_vision_model = model_manager.current_vision_model
    
    # 创建API客户端
    api_client = KimiApiClient(api_key, api_base_url)
    
    # 从URL下载图片
    local_image_path = None
    
    try:
        await bot.send(event, "正在分析图片，请稍等...")
        
        # 从URL下载图片
        image_filename = f"image_{event.message_id}.jpg"
        local_image_path = await download_file(image_url, image_filename)
        
        if not local_image_path:
            return "下载图片失败，请检查图片是否存在或稍后再试"
        
        # 检查文件大小
        file_size = os.path.getsize(local_image_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            # 直接删除本地文件，避免使用cleanup_files
            try:
                os.remove(local_image_path)
            except Exception as e:
                logger.debug(f"删除过大图片文件时出错: {e}")
            return f"图片过大（{file_size/1024/1024:.2f}MB），超过了大小限制（{MAX_FILE_SIZE_BYTES/1024/1024}MB）"
        
        # 使用API分析图片
        success, result, _, token_count, model_used = await api_client.analyze_image(
            image_path=local_image_path,
            filename=image_filename,
            message=question,
            vision_model=current_vision_model
        )
        
        # 清理临时文件，但不传入client参数，避免FinishedException
        try:
            if local_image_path and os.path.exists(local_image_path):
                os.remove(local_image_path)
                logger.debug(f"成功删除本地临时图片文件: {local_image_path}")
        except Exception as e:
            logger.debug(f"删除临时图片文件时出错: {e}")
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        
        # 查询余额
        balance = await model_manager.get_moonshot_balance(api_key, api_base_url)
        balance_str = f"¥{balance:.2f}" if balance is not None else "查询失败"
        
        if success:
            # 准备回复
            reply = f"图片分析结果：\n------------------------\n\n{result}"
            # 添加分隔符和统计信息
            reply += f"\n\n------------------------\n耗时: {elapsed_time:.1f}s | 模型: {model_used} | token: {token_count or '未知'} | 余额: {balance_str}"
            return reply
        else:
            return f"分析图片失败: {result}"
            
    except Exception as e:
        # 确保资源被清理，但不使用可能导致FinishedException的方法
        try:
            if local_image_path and os.path.exists(local_image_path):
                os.remove(local_image_path)
        except Exception:
            pass
        logger.error(f"图片分析过程中发生错误: {e}")
        return f"处理图片过程中出错: {str(e)}"

async def handle_set_model(args: List[str]) -> str:
    """
    处理设置模型命令
    
    :param args: 命令参数
    :return: 回复消息
    """
    # 参数检查
    if len(args) < 1:
        # 显示当前模型和可选模型
        model_manager = ModelManager()
        current_model = model_manager.current_model
        
        models_list = "\n".join([f"- {model}: {info}" for model, info in MODEL_INFO.items()])
        
        return f"当前模型：{current_model}\n\n可选模型：\n{models_list}\n\n使用方法：#设置模型 模型名称"
    
    # 获取要设置的模型
    model_name = args[0]
    
    # 检查模型是否有效
    if model_name not in AVAILABLE_MODELS:
        models_str = "、".join(AVAILABLE_MODELS)
        return f"无效的模型名称。可用的模型有：{models_str}"
    
    # 设置模型
    model_manager = ModelManager()
    if model_manager.set_model(model_name):
        return f"模型设置成功：{model_name}"
    else:
        return "设置模型失败，请稍后再试"

async def handle_set_vision_model(args: List[str]) -> str:
    """
    处理设置视觉模型命令
    
    :param args: 命令参数
    :return: 回复消息
    """
    # 参数检查
    if len(args) < 1:
        # 显示当前模型和可选模型
        model_manager = ModelManager()
        current_vision_model = model_manager.current_vision_model
        
        models_list = "\n".join([f"- {model}: {info}" for model, info in VISION_MODEL_INFO.items()])
        
        return f"当前视觉模型：{current_vision_model}\n\n可选视觉模型：\n{models_list}\n\n使用方法：#设置视觉模型 模型名称"
    
    # 获取要设置的模型
    model_name = args[0]
    
    # 检查模型是否有效
    if model_name not in VISION_MODEL_INFO:
        models_str = "、".join(VISION_MODEL_INFO.keys())
        return f"无效的视觉模型名称。可用的视觉模型有：{models_str}"
    
    # 设置模型
    model_manager = ModelManager()
    if model_manager.set_vision_model(model_name):
        return f"视觉模型设置成功：{model_name}"
    else:
        return "设置视觉模型失败，请稍后再试"

async def handle_check_balance() -> str:
    """
    检查API余额
    
    :return: 回复消息
    """
    # 获取配置
    config_dict = get_plugin_config(Config)
    api_key = config_dict.CONFIG.get("kimi_api_key", "")
    api_base_url = config_dict.CONFIG.get("kimi_api_base_url", "")
    
    if not api_key or not api_base_url:
        return "API配置错误，请联系管理员设置正确的API密钥和地址"
    
    # 查询余额
    model_manager = ModelManager()
    balance = await model_manager.get_moonshot_balance(api_key, api_base_url)
    
    if balance is not None:
        return f"当前账户余额: ¥{balance:.2f}"
    else:
        return "查询余额失败，请稍后再试"

async def handle_help() -> str:
    """
    显示帮助信息
    
    :return: 帮助消息
    """
    help_text = """# 文件AI助手使用指南

## 基本命令
- **#分析文件 [问题]**: 回复包含文件的消息，分析该文件并回答问题
例如: #分析文件 总结一下这个文件的主要内容

- **#分析图片 [问题]**: 回复包含图片的消息，分析图片内容
例如: #分析图片 这是什么植物？

## 模型设置
- **#设置模型 <模型名称>**: 设置文本分析模型
例如: #设置模型 moonshot-v1-32k

- **#设置视觉模型 <模型名称>**: 设置图像分析模型
例如: #设置视觉模型 moonshot-v1-32k-vision-preview

## 其他命令
- **#查询余额**: 查询API账户余额
- **#帮助**: 显示此帮助信息

## 支持的文件格式
- 文档: PDF, TXT, DOC, DOCX, XLS, XLSX...
- 图片: PNG, JPG, JPEG
- 代码: PY, JS, JAVA, C, CPP...

## 使用提示
1. 要分析文件或图片，请先发送文件/图片，然后回复该消息使用对应的命令
2. 可以在命令后添加具体问题，如"#分析文件 请总结主要观点"
3. 大文件处理需要较长时间，请耐心等待
"""
    return help_text

async def handle_file_analysis_from_message(bot: Bot, event: MessageEvent, file_info: Dict[str, str], question: str) -> str:
    """
    处理从消息中提取的文件分析命令，使用代理模式自动判断文件类型
    
    :param bot: 机器人实例
    :param event: 消息事件
    :param file_info: 文件信息，包含file_id, file_name等
    :param question: 用户问题
    :return: 回复消息
    """
    try:
        # 使用文件处理代理类处理文件
        from .file_processor_proxy import FileProcessorProxy
        processor_proxy = FileProcessorProxy()
        
        # 调用代理类处理文件
        result = await processor_proxy.process_file(bot, event, file_info, question)
        
        return result
        
    except Exception as e:
        logger.error(f"文件分析过程中发生错误: {e}")
        return f"处理文件过程中出错: {str(e)}"