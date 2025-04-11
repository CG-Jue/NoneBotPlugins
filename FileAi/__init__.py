import asyncio
from pathlib import Path
from nonebot.rule import to_me
import nonebot
from nonebot import on_message, get_plugin_config, on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment, GroupMessageEvent
from nonebot.typing import T_State
from nonebot.log import logger
from nonebot.exception import FinishedException
from nonebot.params import CommandArg, ArgStr, ArgPlainText
from nonebot.plugin import PluginMetadata
from nonebot.permission import SUPERUSER

from .config import Config
from .models import ModelManager, MODEL_INFO, VISION_MODEL_INFO
from .api_client import KimiApiClient
from .file_handler import get_file_url
from .image_handler import ImageHandler
from .file_message_handler import FileMessageHandler
from .utils import download_file, cleanup_files, is_supported_file_format, MAX_FILE_SIZE_BYTES
from .command_handlers import (
    handle_file_analysis_from_message,
    handle_image_analysis, 
    handle_set_model,
    handle_set_vision_model,
    handle_check_balance
)

__plugin_meta__ = PluginMetadata(
    name="文件解读",
    description="通过AI解读和分析群文件内容，支持多种文档和代码格式",
    usage="""
    友情提示:
    - 此插件是作者用来偷懒不想看文件的时候让AI解读总结的
    - 没有上下文功能，建议只用来总结某个文件的内容

    基本命令:
    - #分析文件 [问题]: 回复带文件的消息，分析文件内容
    - #分析图片 [问题]: 回复带图片的消息，分析图片内容
    
    支持的文件格式:
    - 文档类: PDF、TXT、DOC/DOCX、XLS/XLSX、PPT/PPTX、MD、HTML等
    - 代码类: Python、Java、C/C++、JavaScript、TypeScript等常见编程语言
    - 其他类: JSON、YAML、日志文件、配置文件等
    - 图片类: PNG、JPG、JPEG等常见图片格式
    
    注意事项:
    - 大文件处理可能需要较长时间
    - 同一时间只能处理一个文件请求
    
    高级命令(仅超级用户可用):
    - 设置模型 <模型名称>: 设置文本分析模型
    - 设置视觉模型 <模型名称>: 设置图像分析模型
    - 查询余额: 查询API账户余额
    """,
    type="application",
    homepage="https://github.com/CG-Jue/NoneBotPlugins",
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "dog",
        "version": "1.1.0",
    },
)

# 全局锁变量，用于控制并发请求
processing_lock = asyncio.Lock()
is_processing = False

# 创建事件处理器
file_analyzer = on_command("分析文件", priority=5)
image_analyzer = on_command("分析图片", priority=5)
model_setter = on_command("设置模型", priority=5, permission=SUPERUSER)
vision_model_setter = on_command("设置视觉模型", priority=5, permission=SUPERUSER)
balance_checker = on_command("查询余额", priority=5, permission=SUPERUSER)

@file_analyzer.handle()
async def file_analyze_handler(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """
    处理文件分析请求
    :param bot: 机器人实例
    :param event: 消息事件
    :param args: 命令参数
    """
    global is_processing
    
    # 检查是否有正在处理的请求
    if is_processing:
        await file_analyzer.send(MessageSegment.reply(event.message_id)
                          + MessageSegment.at(int(event.user_id))
                          + MessageSegment.text("错误：已有一个文件正在处理中，请稍后再试"))
        return
    
    is_processing = True
    try:
        # 检查是否回复了带文件的消息
        if not hasattr(event, 'reply') or not event.reply:
            await file_analyzer.send(MessageSegment.reply(event.message_id)
                           + MessageSegment.at(int(event.user_id))
                           + MessageSegment.text("请回复带有文件的消息，例如：#分析文件 分析一下这个文件的内容"))
            is_processing = False
            return
            
        # 获取回复的消息ID
        reply_msg_id = event.reply.message_id
        
        # 获取原始消息
        reply_msg = await bot.get_msg(message_id=reply_msg_id)
        
        # 提取文件信息
        file_handler = FileMessageHandler()
        file_info = await file_handler.get_file_info_from_message(reply_msg)
        
        if not file_info:
            await file_analyzer.send(MessageSegment.reply(event.message_id)
                           + MessageSegment.at(int(event.user_id))
                           + MessageSegment.text("在回复的消息中没有找到文件，请确保回复的是包含文件的消息"))
            is_processing = False
            return
            
        # 提取问题
        question = args.extract_plain_text().strip()
        
        # 调用文件分析处理函数
        try:
            result = await handle_file_analysis_from_message(bot, event, file_info, question)
            
            # 发送结果
            await file_analyzer.send(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f" {result}"))
        except Exception as e:
            logger.error(f"调用文件分析函数时出错: {e}")
            await file_analyzer.send(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f"文件分析出错: {str(e)}"))
                      
    except Exception as e:
        logger.error(f"处理文件分析命令时出错: {e}")
        await file_analyzer.send(MessageSegment.reply(event.message_id)
                      + MessageSegment.at(int(event.user_id))
                      + MessageSegment.text(f"处理出错: {str(e)}"))
    finally:
        is_processing = False

@image_analyzer.handle()
async def image_analyze_handler(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """
    处理图片分析请求
    :param bot: 机器人实例
    :param event: 消息事件
    :param args: 命令参数
    """
    global is_processing
    
    # 检查是否有正在处理的请求
    if is_processing:
        await image_analyzer.send(MessageSegment.reply(event.message_id)
                           + MessageSegment.at(int(event.user_id))
                           + MessageSegment.text("错误：已有一个任务正在处理中，请稍后再试"))
        return
    
    is_processing = True
    try:
        # 检查是否回复了带图片的消息
        if not hasattr(event, 'reply') or not event.reply:
            await image_analyzer.send(MessageSegment.reply(event.message_id)
                           + MessageSegment.at(int(event.user_id))
                           + MessageSegment.text("请回复带有图片的消息，例如：#分析图片 描述一下这张图的内容"))
            is_processing = False
            return
            
        # 获取回复的消息ID
        reply_msg_id = event.reply.message_id
        
        # 获取原始消息
        reply_msg = await bot.get_msg(message_id=reply_msg_id)
        
        # 提取图片URL
        image_handler = ImageHandler()
        image_url = await image_handler.get_image_url(reply_msg)
        
        if not image_url:
            await image_analyzer.send(MessageSegment.reply(event.message_id)
                           + MessageSegment.at(int(event.user_id))
                           + MessageSegment.text("在回复的消息中没有找到图片，请确保回复的是包含图片的消息"))
            is_processing = False
            return
            
        # 提取问题
        question = args.extract_plain_text().strip()
        
        # 调用图片分析处理函数
        try:
            result = await handle_image_analysis(bot, event, image_url, question)
            
            # 发送结果
            await image_analyzer.send(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f" {result}"))
        except Exception as e:
            logger.error(f"调用图片分析函数时出错: {e}")
            await image_analyzer.send(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f"图片分析出错: {str(e)}"))
    
    except Exception as e:
        logger.error(f"处理图片分析命令时出错: {e}")
        await image_analyzer.send(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f"处理出错: {str(e)}"))
    finally:
        is_processing = False

@model_setter.handle()
async def model_setter_handler(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    """
    处理设置模型命令
    :param bot: 机器人实例
    :param event: 消息事件
    :param state: 会话状态
    :param args: 命令参数
    """
    # 提取参数
    model_name = args.extract_plain_text().strip()
    
    # 加载模型管理器
    model_manager = ModelManager()
    current_model = model_manager.current_model
    
    if model_name:
        # 如果提供了参数，直接尝试设置
        try:
            result = await handle_set_model([model_name])
            await model_setter.finish(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f" {result}"))
        except Exception as e:
            logger.error(f"处理设置模型命令时出错: {e}")
            await model_setter.finish(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f"设置模型出错: {str(e)}"))
    else:
        # 显示当前模型和可选模型
        models = list(MODEL_INFO.items())
        models_text = "\n".join([f"{i+1}. {model}: {info}" for i, (model, info) in enumerate(models)])
        
        # 保存模型列表到state
        state["models"] = [model for model, _ in models]
        
        msg = f"当前模型：{current_model}\n\n请选择要设置的模型（输入数字）：\n{models_text}\n\n回复【取消】可取消操作"
        await model_setter.send(MessageSegment.reply(event.message_id) + MessageSegment.text(msg))

@model_setter.got("choice")
async def handle_model_choice(bot: Bot, event: MessageEvent, state: T_State, choice: str = ArgPlainText("choice")):
    """
    处理模型选择
    :param bot: 机器人实例
    :param event: 消息事件
    :param state: 会话状态
    :param choice: 用户输入的选择
    """
    # 检查是否取消
    if choice == "取消":
        await model_setter.finish(MessageSegment.reply(event.message_id)
                     + MessageSegment.at(int(event.user_id))
                     + MessageSegment.text(" 已取消设置模型"))
    
    # 获取模型列表
    models = state.get("models", [])
    
    # 检查输入是否有效
    try:
        choice_index = int(choice) - 1
        if choice_index < 0 or choice_index >= len(models):
            await model_setter.reject(MessageSegment.reply(event.message_id)
                        + MessageSegment.text(f"无效的选择，请输入1-{len(models)}之间的数字"))
        
        # 获取选择的模型
        selected_model = models[choice_index]
        
        # 设置模型
        try:
            result = await handle_set_model([selected_model])
            await model_setter.finish(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f" {result}"))
        except Exception as e:
            logger.error(f"设置模型时出错: {e}")
            await model_setter.finish(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f"设置模型出错: {str(e)}"))
            
    except ValueError:
        # 输入的不是数字
        await model_setter.reject(MessageSegment.reply(event.message_id)
                    + MessageSegment.text("请输入有效的数字，或回复【取消】以取消操作"))

@vision_model_setter.handle()
async def vision_model_setter_handler(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    """
    处理设置视觉模型命令
    :param bot: 机器人实例
    :param event: 消息事件
    :param state: 会话状态
    :param args: 命令参数
    """
    # 提取参数
    model_name = args.extract_plain_text().strip()
    
    # 加载模型管理器
    model_manager = ModelManager()
    current_vision_model = model_manager.current_vision_model
    
    if model_name:
        # 如果提供了参数，直接尝试设置
        try:
            result = await handle_set_vision_model([model_name])
            await vision_model_setter.finish(MessageSegment.reply(event.message_id)
                             + MessageSegment.at(int(event.user_id))
                             + MessageSegment.text(f" {result}"))
        except Exception as e:
            logger.error(f"处理设置视觉模型命令时出错: {e}")
            await vision_model_setter.finish(MessageSegment.reply(event.message_id)
                             + MessageSegment.at(int(event.user_id))
                             + MessageSegment.text(f"设置视觉模型出错: {str(e)}"))
    else:
        # 显示当前模型和可选模型
        models = list(VISION_MODEL_INFO.items())
        models_text = "\n".join([f"{i+1}. {model}: {info}" for i, (model, info) in enumerate(models)])
        
        # 保存模型列表到state
        state["models"] = [model for model, _ in models]
        
        msg = f"当前视觉模型：{current_vision_model}\n\n请选择要设置的视觉模型（输入数字）：\n{models_text}\n\n回复【取消】可取消操作"
        await vision_model_setter.send(MessageSegment.reply(event.message_id) + MessageSegment.text(msg))

@vision_model_setter.got("choice")
async def handle_vision_model_choice(bot: Bot, event: MessageEvent, state: T_State, choice: str = ArgPlainText("choice")):
    """
    处理视觉模型选择
    :param bot: 机器人实例
    :param event: 消息事件
    :param state: 会话状态
    :param choice: 用户输入的选择
    """
    # 检查是否取消
    if choice == "取消":
        await vision_model_setter.finish(MessageSegment.reply(event.message_id)
                           + MessageSegment.at(int(event.user_id))
                           + MessageSegment.text(" 已取消设置视觉模型"))
    
    # 获取模型列表
    models = state.get("models", [])
    
    # 检查输入是否有效
    try:
        choice_index = int(choice) - 1
        if choice_index < 0 or choice_index >= len(models):
            await vision_model_setter.reject(MessageSegment.reply(event.message_id)
                              + MessageSegment.text(f"无效的选择，请输入1-{len(models)}之间的数字"))
        
        # 获取选择的模型
        selected_model = models[choice_index]
        
        # 设置模型
        try:
            result = await handle_set_vision_model([selected_model])
            await vision_model_setter.finish(MessageSegment.reply(event.message_id)
                             + MessageSegment.at(int(event.user_id))
                             + MessageSegment.text(f" {result}"))
        except Exception as e:
            logger.error(f"设置视觉模型时出错: {e}")
            await vision_model_setter.finish(MessageSegment.reply(event.message_id)
                             + MessageSegment.at(int(event.user_id))
                             + MessageSegment.text(f"设置视觉模型出错: {str(e)}"))
            
    except ValueError:
        # 输入的不是数字
        await vision_model_setter.reject(MessageSegment.reply(event.message_id)
                          + MessageSegment.text("请输入有效的数字，或回复【取消】以取消操作"))

@balance_checker.handle()
async def balance_checker_handler(event: MessageEvent):
    """
    处理查询余额命令
    :param event: 消息事件
    """
    try:
        # 调用处理函数
        result = await handle_check_balance()
        
        # 发送结果
        await balance_checker.send(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f" {result}"))
    except Exception as e:
        logger.error(f"处理查询余额命令时出错: {e}")
        await balance_checker.send(MessageSegment.reply(event.message_id)
                       + MessageSegment.at(int(event.user_id))
                       + MessageSegment.text(f"查询余额出错: {str(e)}"))
