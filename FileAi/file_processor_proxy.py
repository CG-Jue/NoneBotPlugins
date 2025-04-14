from typing import Dict, List, Optional
from pathlib import Path
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.log import logger

from .file_processor import FileProcessor, ImageFileProcessor, DocumentFileProcessor
from .utils import is_supported_file_format


class FileProcessorProxy:
    """文件处理代理类"""
    
    # 图片文件扩展名列表
    IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    def __init__(self):
        """初始化处理器"""
        self.image_processor = ImageFileProcessor()
        self.document_processor = DocumentFileProcessor()
    
    def is_image_file(self, file_name: str) -> bool:
        """
        判断文件是否为图片文件
        :param file_name: 文件名
        :return: 是否为图片
        """
        return any(file_name.lower().endswith(ext) for ext in self.IMAGE_EXTENSIONS)
    
    async def get_file_url(self, bot: Bot, event: MessageEvent, file_info: Dict[str, str]) -> Optional[str]:
        """
        获取文件URL
        :param bot: 机器人实例
        :param event: 消息事件
        :param file_info: 文件信息
        :return: 文件URL
        """
        try:
            # 从file_info中提取必要信息
            file_id = file_info.get('file_id')
            busid = file_info.get('busid', 0)
            
            if not file_id:
                logger.error("无法获取文件ID")
                return None
            
            # 获取群ID (仅支持群聊)
            from nonebot.adapters.onebot.v11 import GroupMessageEvent
            if isinstance(event, GroupMessageEvent):
                group_id = event.group_id
                file_url_info = await bot.call_api(
                    "get_group_file_url", 
                    group_id=group_id, 
                    file_id=file_id,
                    busid=busid
                )
            else:
                # 私聊消息的处理逻辑
                logger.error("目前仅支持在群聊中分析文件")
                return None
            
            if 'url' not in file_url_info:
                logger.error(f"获取文件URL失败，返回数据不包含url字段: {file_url_info}")
                return None
            
            file_url = file_url_info['url']
            
            # 将URL添加到file_info中
            file_info['url'] = file_url
            
            return file_url
            
        except Exception as e:
            logger.error(f"获取文件URL时出错: {e}")
            return None
    
    async def process_file(self, bot: Bot, event: MessageEvent, file_info: Dict[str, str], 
                    question: str) -> str:
        """
        处理文件，根据文件类型选择适当的处理器
        :param bot: 机器人实例
        :param event: 消息事件
        :param file_info: 文件信息
        :param question: 用户问题
        :return: 处理结果
        """
        # 获取文件名
        file_name = file_info.get('file_name', "未知文件")
        
        # 检查文件格式是否支持
        if not is_supported_file_format(file_name):
            return f"不支持的文件格式: {file_name}。请上传支持的文件类型，如PDF、DOC、TXT等常见文档格式或者JPG、PNG等图片格式。"
            
        # 获取文件URL
        file_url = await self.get_file_url(bot, event, file_info)
        if not file_url:
            return "获取文件下载链接失败，无法进行分析"
        
        # 根据文件类型选择处理器
        if self.is_image_file(file_name):
            logger.info(f"检测到图片文件: {file_name}，使用图片处理器")
            return await self.image_processor.process_file(bot, event, file_info, question)
        else:
            logger.info(f"使用文档处理器处理文件: {file_name}")
            return await self.document_processor.process_file(bot, event, file_info, question)