import os
import tempfile
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from nonebot.rule import to_me
import nonebot
from nonebot import on_message, get_plugin_config, on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment

from nonebot.typing import T_State
from nonebot.log import logger
from nonebot.exception import FinishedException
from nonebot.params import CommandArg
from openai import OpenAI
import httpx
import traceback
import asyncio

from .config import Config

# 获取配置
config = get_plugin_config(Config)

DEFAULT_KIMI_API_BASE_URL = 'https://api.moonshot.cn/v1'  # 默认为空列表
DEFAULT_KIMI_MODEL = "moonshot-v1-32k"  # 默认模型
try:
    KIMI_API_KEY = config.CONFIG.get("kimi_api_key", '')
    KIMI_API_BASE_URL = config.CONFIG.get("kimi_api_base_url", DEFAULT_KIMI_API_BASE_URL)

    KIMI_MODEL = config.CONFIG.get("kimi_model", DEFAULT_KIMI_MODEL)

except (AttributeError, KeyError):
    # 中断程序，必须要求配置
    raise ValueError("请配置 KIMI_API_KEY")

# 初始化OpenAI客户端
client = OpenAI(
    api_key=KIMI_API_KEY,
    base_url=KIMI_API_BASE_URL,
)

# 全局锁变量，用于控制并发请求
processing_lock = asyncio.Lock()
is_processing = False


async def build_file_mapping(bot: Bot, groupId: int) -> Dict[str, Dict[str, Any]]:
    """
    构建文件名到file_id的映射字典，包括根目录和所有文件夹内的文件
    
    :param bot: 机器人实例
    :param groupId: 群号
    :return: 文件名到{file_id, busid}的映射字典
    """
    file_mapping = {}
    
    try:
        # 获取根目录文件列表
        root_files = await bot.call_api("get_group_root_files", group_id=groupId)
        logger.debug(f"根目录文件列表: {root_files}")
        
        # 处理根目录文件
        if 'files' in root_files:
            for file_info in root_files['files']:
                if 'file_name' in file_info and 'file_id' in file_info:
                    # 存储file_id和busid，下载时都需要
                    file_mapping[file_info['file_name']] = {
                        'file_id': file_info['file_id'], 
                        'busid': file_info.get('busid', 0)
                    }
        
        # 处理文件夹
        if 'folders' in root_files:
            for folder in root_files['folders']:
                if 'folder_id' in folder:
                    try:
                        # 使用正确的API获取文件夹内的文件
                        folder_files = await bot.call_api(
                            "get_group_files_by_folder", 
                            group_id=groupId, 
                            folder_id=folder['folder_id'],
                            file_count=0  # 不限制数量
                        )
                        
                        logger.debug(f"文件夹 {folder['folder_name']} 的文件列表: {folder_files}")
                        
                        if 'files' in folder_files:
                            for file_info in folder_files['files']:
                                # 把文件夹名称加到文件名前，避免同名文件冲突
                                folder_prefix = f"{folder['folder_name']}/"
                                mapped_name = folder_prefix + file_info['file_name']
                                
                                file_mapping[mapped_name] = {
                                    'file_id': file_info['file_id'],
                                    'busid': file_info.get('busid', 0),
                                    'folder_id': folder['folder_id']
                                }
                                
                                # 同时保留不带路径前缀的映射，但如果有同名文件会被最后一个覆盖
                                file_mapping[file_info['file_name']] = {
                                    'file_id': file_info['file_id'],
                                    'busid': file_info.get('busid', 0),
                                    'folder_id': folder['folder_id']
                                }
                                
                    except Exception as e:
                        error_detail = traceback.format_exc()
                        logger.error(f"获取文件夹'{folder.get('folder_name', '未知')}' ({folder['folder_id']})内容失败: {e}\n{error_detail}")
                        # 这里不抛出异常，继续处理其他文件夹
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"构建文件映射时出错: {e}\n{error_detail}")
        raise RuntimeError(f"获取群文件列表时出错: {str(e)}")
    
    return file_mapping


async def download_file(file_url: str, filename: str) -> Optional[Path]:
    """下载文件到临时目录"""
    try:
        # 创建临时文件夹
        temp_dir = Path(tempfile.gettempdir()) / "qqbot_file_analysis"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 清理特殊字符，防止文件名不合法
        safe_filename = "".join([c for c in filename if c.isalnum() or c in "._- "])
        if not safe_filename:
            safe_filename = "downloaded_file"
        
        file_path = temp_dir / safe_filename
        
        # 下载文件
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(file_url, follow_redirects=True, timeout=30.0)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    return file_path
                else:
                    logger.error(f"下载文件失败，HTTP状态码: {response.status_code}，响应内容: {response.text[:200]}")
                    raise RuntimeError(f"下载文件失败，服务器返回状态码: {response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"请求文件时网络错误: {e}")
                raise RuntimeError(f"下载文件时网络错误: {str(e)}")
        
    except Exception as e:
        if not isinstance(e, RuntimeError):
            error_detail = traceback.format_exc()
            logger.error(f"下载文件'{filename}'时出错: {e}\n{error_detail}")
            raise RuntimeError(f"下载文件过程中出错: {str(e)}")
        raise e


async def analyze_file_with_kimi(file_path: Path, filename: str, message: str) -> Tuple[bool, str, Optional[str], Optional[int]]:
    """使用Kimi API解析文件内容
    
    返回: (成功状态, 结果或错误信息, kimi_file_id, token数量)
    """
    kimi_file_id = None
    token_count = None
    try:
        # 上传文件
        try:
            file_object = client.files.create(file=file_path, purpose="file-extract")
            kimi_file_id = file_object.id
            logger.debug(f"文件上传到Kimi成功，文件ID: {kimi_file_id}")
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"上传文件到Kimi API失败: {e}\n{error_detail}")
            return False, f"上传文件到AI服务时出错: {str(e)}", None, None
        
        # 获取文件内容
        try:
            file_content = client.files.content(file_id=kimi_file_id).text
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"从Kimi API获取文件内容失败: {e}\n{error_detail}")
            return False, f"AI服务提取文件内容时出错: {str(e)}", kimi_file_id, None
        
        # 构建请求
        messages = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手。请分析用户上传的文件内容，并提供清晰、简洁的总结，不要使用markdown格式回答，请使用纯字符串回答。只关注文件的主要内容，不要提及自己是AI助手。",
            },
            {
                "role": "system",
                "content": file_content,  # 文件内容
            },
            {"role": "user", "content": f"请查找这个文件（{filename}）的内容，并且{message}"},
        ]
        
        # 计算token数量
        token_count = await estimate_token_count(messages)
        logger.debug(f"消息的token数量: {token_count}")
        
        # 调用API获取回答
        try:
            # 设置较长的超时时间
            completion = client.chat.completions.create(
                model=KIMI_MODEL,
                messages=messages,
                temperature=0.3,
                timeout=60.0  # 增加超时时间到60秒
            )
            if not completion or not completion.choices:
                logger.error("Kimi API返回的结果为空或没有选项")
                return False, "AI返回的结果为空，请稍后再试", kimi_file_id, token_count
                
            return True, completion.choices[0].message.content, kimi_file_id, token_count
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"调用Kimi API解析文件内容失败: {e}\n{error_detail}")
            return False, f"AI分析文件内容时出错: {str(e)}", kimi_file_id, token_count
        
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"文件分析过程中出错: {e}\n{error_detail}")
        return False, f"解析文件时出错: {str(e)}", kimi_file_id, token_count


async def cleanup_files(kimi_file_id: Optional[str], local_file_path: Optional[Path]):
    """清理文件，删除Kimi API中的文件和本地临时文件"""
    # 删除Kimi API中的文件
    if kimi_file_id:
        try:
            # 先检查文件是否存在 (可选，但OpenAI的API不支持这种检查)
            try:
                client.files.delete(file_id=kimi_file_id)
                logger.debug(f"成功删除Kimi API中的文件: {kimi_file_id}")
            except Exception as e:
                # 检查是否是404错误 (文件不存在)
                if "404" in str(e) or "not found" in str(e).lower():
                    logger.debug(f"文件 {kimi_file_id} 可能已被删除或不存在，跳过删除操作")
                else:
                    # 如果是其他错误，记录但不中断程序
                    logger.warning(f"删除Kimi API中的文件时出错: {e}")
        except Exception as e:
            # 捕获所有异常，确保不会中断程序
            logger.error(f"处理Kimi文件删除时发生未预期的错误: {e}")
    
    # 删除本地临时文件
    if local_file_path and local_file_path.exists():
        try:
            os.remove(local_file_path)
            logger.debug(f"成功删除本地临时文件: {local_file_path}")
        except PermissionError:
            logger.warning(f"无权限删除文件: {local_file_path}，可能被其他程序占用")
        except FileNotFoundError:
            logger.debug(f"文件已不存在，无需删除: {local_file_path}")
        except Exception as e:
            logger.error(f"删除本地临时文件时出错: {e}")
            
    # 清理整个临时目录中过期的文件（可选，防止临时文件积累）
    try:
        temp_dir = Path(tempfile.gettempdir()) / "qqbot_file_analysis"
        if temp_dir.exists():
            current_time = time.time()
            # 删除超过1小时的临时文件
            for file_path in temp_dir.iterdir():
                if (file_path.is_file() and (current_time - file_path.stat().st_mtime > 3600)):
                    try:
                        file_path.unlink()
                        logger.debug(f"删除过期的临时文件: {file_path}")
                    except Exception as e:
                        logger.debug(f"删除过期文件失败: {file_path}, 错误: {e}")
    except Exception as e:
        logger.debug(f"清理临时目录时出错: {e}")


async def estimate_token_count(messages: list) -> Optional[int]:
    """
    计算消息使用的token数量
    
    :param messages: 消息列表
    :return: token数量，如果请求失败则返回None
    """
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{KIMI_API_BASE_URL}/tokenizers/estimate-token-count",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {KIMI_API_KEY}"
                },
                json={
                    "model": KIMI_MODEL,
                    "messages": messages
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status", False) and "data" in result:
                    return result["data"]["total_tokens"]
            
            logger.error(f"计算token失败，状态码: {response.status_code}, 响应: {response.text}")
            return None
            
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"计算token数量时出错: {e}\n{error_detail}")
        return None


async def get_moonshot_balance() -> Optional[float]:
    """
    查询Moonshot API余额
    
    :return: 可用余额，如果请求失败则返回None
    """
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{KIMI_API_BASE_URL}/users/me/balance",
                headers={
                    "Authorization": f"Bearer {KIMI_API_KEY}"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status", False) and "data" in result:
                    return result["data"].get("available_balance")
            
            logger.error(f"查询余额失败，状态码: {response.status_code}, 响应: {response.text}")
            return None
            
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"查询余额时出错: {e}\n{error_detail}")
        return None


# 创建事件处理器
file_analysis = on_command("解读", priority=5, rule=to_me())

@file_analysis.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    # 获取消息内容
    message = args.extract_plain_text()
    logger.debug(f"收到消息: {message}")
    # 获取消息中的文件id
    file_id = None
    local_file_path = None
    kimi_file_id = None
    
    # 添加开始时间记录
    start_time = time.time()
    
    # 检查是否有正在处理的请求
    global is_processing
    if is_processing:
        await file_analysis.finish(MessageSegment.reply(event.message_id)
                                  + MessageSegment.at(int(event.user_id))
                                  + MessageSegment.text("错误：已有一个文件正在解读中，请稍后再试"))
        return
    
    # 使用异步锁确保并发控制的线程安全
    async with processing_lock:
        # 设置处理标志
        is_processing = True
        
        try:
            try:
                groupId = event.group_id
            except AttributeError:
                is_processing = False  # 重置处理标志
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text("错误：该功能仅支持群聊使用"))
                return

            # 检查是否是回复消息
            if not hasattr(event, 'reply') or not event.reply:
                is_processing = False  # 重置处理标志
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text("错误：请回复包含文件的消息并添加'解读'关键词"))
                return

            # 先获取被回复的消息的id
            reply_msg_id = event.reply.message_id
            
            # 获取原始消息
            try:
                reply_msg = await bot.get_msg(message_id=reply_msg_id)
                raw_message = reply_msg["message"]
            except Exception as e:
                logger.error(f"获取回复消息内容时出错: {e}")
                is_processing = False  # 重置处理标志
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text(f"错误：获取回复消息内容失败，原因：{str(e)}"))
                return

            # 检查是否包含文件
            try:
                seg = raw_message[0]
                logger.debug(f"回复消息内容: {seg}")

                if seg.get('type', None) == "file":
                    file_name = seg.get("data").get("file").replace("/", "")
                    logger.debug(f"文件名: {file_name}")
                else: 
                    is_processing = False  # 重置处理标志
                    await file_analysis.finish(MessageSegment.reply(event.message_id)
                                              + MessageSegment.at(int(event.user_id))
                                              + MessageSegment.text("错误：未在回复的消息中找到文件，请确保回复的消息包含文件"))
                    return
            except (IndexError, KeyError, AttributeError) as e:
                logger.error(f"解析回复消息中的文件信息时出错: {e}")
                is_processing = False  # 重置处理标志
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text(f"错误：解析文件信息失败，原因：{str(e)}"))
                return

            # 发送正在处理的消息
            await file_analysis.send(MessageSegment.reply(event.message_id)
                                    + MessageSegment.at(int(event.user_id))
                                    + MessageSegment.text("正在处理文件，请稍候..."))

            try:
                # 构建文件名到file_id的映射
                file_mapping = await build_file_mapping(bot, groupId)
                logger.debug(f"文件映射: {file_mapping}")
                
                # 查找对应的文件
                if file_name in file_mapping:
                    file_info = file_mapping[file_name]
                    file_id = file_info['file_id']
                    busid = file_info['busid']
                    is_in_folder = 'folder_id' in file_info
                    
                    logger.debug(f"找到文件ID: {file_id}, busid: {busid}, 是否在文件夹中: {is_in_folder}")
                else:
                    is_processing = False  # 重置处理标志
                    await file_analysis.finish(MessageSegment.reply(event.message_id)
                                              + MessageSegment.at(int(event.user_id))
                                              + MessageSegment.text(f"错误：在群文件中找不到名为 {file_name} 的文件，请检查文件名是否正确"))
                    return
            except Exception as e:
                logger.error(f"查找文件映射时出错: {e}")
                is_processing = False  # 重置处理标志
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text(f"错误：查找文件信息失败，原因：{str(e)}"))
                return
            
            # 获取文件URL
            try:
                file_url_info = await bot.call_api(
                    "get_group_file_url", 
                    group_id=groupId, 
                    file_id=file_id,
                    busid=busid
                )
                
                if 'url' not in file_url_info:
                    logger.error(f"获取文件URL失败，返回数据不包含url字段: {file_url_info}")
                    is_processing = False  # 重置处理标志
                    await file_analysis.finish(MessageSegment.reply(event.message_id)
                                              + MessageSegment.at(int(event.user_id))
                                              + MessageSegment.text(f"错误：获取文件下载链接失败，无法获取有效的下载地址"))
                    return

                file_url = file_url_info['url']
                logger.debug(f"文件下载URL: {file_url}")
            except Exception as e:
                logger.error(f"获取文件下载链接时出错: {e}")
                is_processing = False  # 重置处理标志
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text(f"错误：获取文件下载链接失败，原因：{str(e)}"))
                return
            
            # 下载文件
            try:
                local_file_path = await download_file(file_url, file_name)
                if not local_file_path:
                    is_processing = False  # 重置处理标志
                    await file_analysis.finish(MessageSegment.reply(event.message_id)
                                              + MessageSegment.at(int(event.user_id))
                                              + MessageSegment.text("错误：文件下载失败，未能获取到文件内容"))
                    return
            except Exception as e:
                logger.error(f"下载文件时出错: {e}")
                is_processing = False  # 重置处理标志
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text(f"错误：下载文件失败，原因：{str(e)}"))
                return
            
            # 调用Kimi API进行分析
            try:
                # 确保只调用一次finish
                success, result, kimi_file_id, token_count = await analyze_file_with_kimi(local_file_path, file_name, message)
                
                # 无论分析是否成功，都尝试清理文件
                asyncio.create_task(cleanup_files(kimi_file_id, local_file_path))
                
                # 计算处理时间
                end_time = time.time()
                total_seconds = int(end_time - start_time)
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                # 构造时间字符串
                time_str = ""
                if hours > 0:
                    time_str += f"{hours}小时"
                if minutes > 0:
                    time_str += f"{minutes}分钟"
                time_str += f"{seconds}秒"
                
                # 获取API余额
                balance = await get_moonshot_balance()
                
                # 添加模型信息
                model_info = f"使用模型: {KIMI_MODEL}"
                
                # 添加时间、模型、token和余额信息到结果中
                token_info = f"消耗Token: {token_count}" if token_count is not None else ""
                balance_info = f"可用余额: {balance:.2f}" if balance is not None else ""
                
                # 组装所有信息
                time_and_model_info = f"\n\n---\n处理用时: {time_str}\n{model_info}"
                if token_info:
                    time_and_model_info += f"\n{token_info}"
                if balance_info:
                    time_and_model_info += f"\n{balance_info}"
                
                is_processing = False  # 重置处理标志，无论是否成功都释放锁
                if success:
                    await file_analysis.finish(MessageSegment.reply(event.message_id)
                                              + MessageSegment.at(int(event.user_id))
                                              + MessageSegment.text(f"文件「{file_name}」的解读结果：\n\n{result}{time_and_model_info}"))
                else:
                    await file_analysis.finish(MessageSegment.reply(event.message_id)
                                              + MessageSegment.at(int(event.user_id))
                                              + MessageSegment.text(f"错误：AI解析文件内容失败，{result}{time_and_model_info}"))
            except FinishedException:
                # 捕获FinishedException，不做处理，防止异常继续传播
                is_processing = False  # 重置处理标志
                # 尝试清理文件
                asyncio.create_task(cleanup_files(kimi_file_id, local_file_path))
                pass
            except Exception as e:
                logger.error(f"分析文件内容时出错: {e}")
                is_processing = False  # 重置处理标志
                # 尝试清理文件
                asyncio.create_task(cleanup_files(kimi_file_id, local_file_path))
                
                # 防止重复finish，检查异常是否已经是FinishedException
                if not isinstance(e, FinishedException):
                    # 计算处理时间
                    end_time = time.time()
                    total_seconds = int(end_time - start_time)
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    # 构造时间字符串
                    time_str = ""
                    if hours > 0:
                        time_str += f"{hours}小时"
                    if minutes > 0:
                        time_str += f"{minutes}分钟"
                    time_str += f"{seconds}秒"
                    
                    # 添加模型信息
                    time_and_model_info = f"\n\n---\n处理用时: {time_str}"
                    
                    await file_analysis.finish(MessageSegment.reply(event.message_id)
                                              + MessageSegment.at(int(event.user_id))
                                              + MessageSegment.text(f"错误：AI解析文件内容失败，原因：{str(e)}{time_and_model_info}"))
                return
                
        except FinishedException:
            # 捕获FinishedException，不做处理
            is_processing = False  # 重置处理标志
            # 尝试清理文件
            asyncio.create_task(cleanup_files(kimi_file_id, local_file_path))
            pass
        except Exception as e:
            is_processing = False  # 重置处理标志
            # 尝试清理文件
            asyncio.create_task(cleanup_files(kimi_file_id, local_file_path))
            
            if not isinstance(e, FinishedException):  # 防止重复finish
                # 计算处理时间
                end_time = time.time()
                total_seconds = int(end_time - start_time)
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                # 构造时间字符串
                time_str = ""
                if hours > 0:
                    time_str += f"{hours}小时"
                if minutes > 0:
                    time_str += f"{minutes}分钟"
                time_str += f"{seconds}秒"
                
                # 添加模型信息
                time_and_model_info = f"\n\n---\n处理用时: {time_str}"
                
                error_detail = traceback.format_exc()
                logger.error(f"文件解析过程中发生未预期的错误: {e}\n{error_detail}")
                await file_analysis.finish(MessageSegment.reply(event.message_id)
                                          + MessageSegment.at(int(event.user_id))
                                          + MessageSegment.text(f"错误：处理文件过程中出现未预期的问题，原因：{str(e)}{time_and_model_info}"))
        finally:
            # 确保在所有情况下都重置处理标志
            is_processing = False
            # 最后一次尝试清理文件（确保一定会执行）
            asyncio.create_task(cleanup_files(kimi_file_id, local_file_path))
