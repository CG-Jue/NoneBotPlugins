import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional
from pathlib import Path
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.log import logger
from nonebot import get_plugin_config

from .config import Config
from .models import ModelManager
from .api_client import KimiApiClient
from .utils import download_file, MAX_FILE_SIZE_BYTES


class FileProcessor(ABC):
    """文件处理器抽象基类"""
    
    @abstractmethod
    async def process_file(self, bot: Bot, event: MessageEvent, file_info: Dict[str, str], 
                    question: str) -> str:
        """处理文件并返回结果"""
        pass


class ImageFileProcessor(FileProcessor):
    """图片文件处理器，使用视觉模型"""
    
    def __init__(self):
        # 获取配置
        config_dict = get_plugin_config(Config)
        self.api_key = config_dict.CONFIG.get("kimi_api_key", "")
        self.api_base_url = config_dict.CONFIG.get("kimi_api_base_url", "")
        self.model_manager = ModelManager()
    
    async def process_file(self, bot: Bot, event: MessageEvent, file_info: Dict[str, str], 
                    question: str) -> str:
        """
        处理图片文件
        :param bot: 机器人实例
        :param event: 消息事件
        :param file_info: 文件信息
        :param question: 用户问题
        :return: 处理结果
        """
        # 开始计时
        start_time = time.time()
        
        if not self.api_key or not self.api_base_url:
            return "API配置错误，请联系管理员设置正确的API密钥和地址"
        
        # 使用视觉模型
        current_vision_model = self.model_manager.current_vision_model
        
        # 创建API客户端
        api_client = KimiApiClient(self.api_key, self.api_base_url)
        
        # 获取文件名和URL
        file_name = file_info.get('file_name', "未知文件")
        file_url = file_info.get('url')
        
        if not file_url:
            return "无法获取文件URL，请确保文件可访问"
        
        # 下载文件
        local_file_path = None
        
        try:
            await bot.send(event, f"正在使用视觉模型分析图片: 《{file_name}》，请稍等...")
            
            # 下载文件到本地
            local_file_path = await download_file(file_url, file_name)
            
            if not local_file_path:
                return "下载图片文件失败，请检查文件是否存在或稍后再试"
            
            # 检查文件大小是否超过限制
            file_size = os.path.getsize(local_file_path)
            if file_size > MAX_FILE_SIZE_BYTES:
                # 直接删除本地文件
                try:
                    os.remove(local_file_path)
                except Exception as e:
                    logger.debug(f"删除过大图片文件时出错: {e}")
                return f"图片过大（{file_size/1024/1024:.2f}MB），超过了大小限制（{MAX_FILE_SIZE_BYTES/1024/1024}MB）"
            
            # 使用API分析图片
            success, result, _, token_count, model_used = await api_client.analyze_image(
                image_path=local_file_path,
                filename=file_name,
                message=question if question else "请详细描述这张图片的内容",
                vision_model=current_vision_model
            )
            
            # 清理临时文件
            try:
                if local_file_path and os.path.exists(local_file_path):
                    os.remove(local_file_path)
                    logger.debug(f"成功删除本地临时图片文件: {local_file_path}")
            except Exception as e:
                logger.debug(f"删除临时图片文件时出错: {e}")
            
            # 计算处理时间
            elapsed_time = time.time() - start_time
            
            # 查询余额
            balance = await self.model_manager.get_moonshot_balance(self.api_key, self.api_base_url)
            balance_str = f"¥{balance:.2f}" if balance is not None else "查询失败"
            
            if success:
                # 准备回复
                reply = f"图片「{file_name}」分析结果：\n------------------------\n\n{result}"
                # 添加分隔符和统计信息
                reply += f"\n\n------------------------\n耗时: {elapsed_time:.1f}s | 模型: {model_used} | token: {token_count or '未知'} | 余额: {balance_str}"
                return reply
            else:
                return f"分析图片失败: {result}"
                
        except Exception as e:
            # 确保资源被清理
            try:
                if local_file_path and os.path.exists(local_file_path):
                    os.remove(local_file_path)
            except Exception:
                pass
            logger.error(f"图片文件分析过程中发生错误: {e}")
            return f"处理图片文件过程中出错: {str(e)}"


class DocumentFileProcessor(FileProcessor):
    """普通文档处理器，使用文本模型"""
    
    def __init__(self):
        # 获取配置
        config_dict = get_plugin_config(Config)
        self.api_key = config_dict.CONFIG.get("kimi_api_key", "")
        self.api_base_url = config_dict.CONFIG.get("kimi_api_base_url", "")
        self.model_manager = ModelManager()
    
    async def process_file(self, bot: Bot, event: MessageEvent, file_info: Dict[str, str], 
                    question: str) -> str:
        """
        处理文档文件
        :param bot: 机器人实例
        :param event: 消息事件
        :param file_info: 文件信息
        :param question: 用户问题
        :return: 处理结果
        """
        # 开始计时
        start_time = time.time()
        
        if not self.api_key or not self.api_base_url:
            return "API配置错误，请联系管理员设置正确的API密钥和地址"
            
        # 使用文本模型
        current_model = self.model_manager.current_model
        
        # 获取文件名和URL
        file_name = file_info.get('file_name', "未知文件")
        file_url = file_info.get('url')
        
        if not file_url:
            return "无法获取文件URL，请确保文件可访问"
        
        # 创建API客户端
        api_client = KimiApiClient(self.api_key, self.api_base_url)
        
        # 下载文件
        local_file_path = None
        kimi_file_id = None
        
        try:
            await bot.send(event, f"正在处理文件: 《{file_name}》，请稍等...")
            
            # 下载文件到本地
            local_file_path = await download_file(file_url, file_name)
            
            if not local_file_path:
                return "下载文件失败，请检查文件是否存在或稍后再试"
            
            # 检查文件大小是否超过限制
            file_size = os.path.getsize(local_file_path)
            if file_size > MAX_FILE_SIZE_BYTES:
                # 直接删除本地文件
                try:
                    os.remove(local_file_path)
                except Exception as e:
                    logger.debug(f"删除过大文件时出错: {e}")
                return f"文件过大（{file_size/1024/1024:.2f}MB），超过了大小限制（{MAX_FILE_SIZE_BYTES/1024/1024}MB）"
            
            # 使用API分析文件
            success, result, kimi_file_id, token_count, model_used = await api_client.analyze_file(
                file_path=local_file_path,
                filename=file_name,
                message=question,
                model=current_model
            )
            
            # 清理临时文件
            try:
                if local_file_path and os.path.exists(local_file_path):
                    os.remove(local_file_path)
                    logger.debug(f"成功删除本地临时文件: {local_file_path}")
                    
                if kimi_file_id:
                    try:
                        api_client.client.files.delete(file_id=kimi_file_id)
                        logger.debug(f"成功删除Kimi API中的文件: {kimi_file_id}")
                    except Exception as e:
                        logger.debug(f"删除Kimi API中的文件时出错: {e}")
            except Exception as e:
                logger.debug(f"删除临时文件时出错: {e}")
            
            # 计算处理时间
            elapsed_time = time.time() - start_time
            
            # 查询余额
            balance = await self.model_manager.get_moonshot_balance(self.api_key, self.api_base_url)
            balance_str = f"¥{balance:.2f}" if balance is not None else "查询失败"
            
            if success:
                # 准备回复
                reply = f"文件「{file_name}」分析结果：\n------------------------\n\n{result}"
                # 添加分隔符和统计信息
                reply += f"\n\n------------------------\n耗时: {elapsed_time:.1f}s | 模型: {model_used} | token: {token_count or '未知'} | 余额: {balance_str}"
                return reply
            else:
                return f"分析文件失败: {result}"
                
        except Exception as e:
            # 确保资源被清理
            try:
                if local_file_path and os.path.exists(local_file_path):
                    os.remove(local_file_path)
            except Exception:
                pass
            logger.error(f"文件分析过程中发生错误: {e}")
            return f"处理文件过程中出错: {str(e)}"