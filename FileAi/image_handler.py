import os
import traceback
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
import httpx
from nonebot.log import logger

class ImageHandler:
    @staticmethod
    async def get_image_url(message_data: Dict[str, Any]) -> Optional[str]:
        """
        从消息数据中提取图片URL
        
        :param message_data: 消息数据
        :return: 图片URL或None
        """
        try:
            # 遍历消息段寻找图片类型
            if 'message' in message_data:
                for segment in message_data['message']:
                    # 图片消息段
                    if segment.get('type') == 'image' and 'data' in segment:
                        # 优先使用url
                        if 'url' in segment['data']:
                            return segment['data']['url']
                        # 备选file
                        elif 'file' in segment['data']:
                            # 有时file是本地路径，有时是URL，需要检查
                            file_path = segment['data']['file']
                            # 如果看起来像URL，则返回
                            if file_path.startswith(('http://', 'https://')):
                                return file_path
                            # 如果是本地路径，可能需要另外处理
                            # 例如：构建完整URL或使用其他API获取图片
                        
            # 未找到图片
            return None
            
        except Exception as e:
            logger.error(f"提取图片URL时出错: {e}")
            return None
            
    @staticmethod
    async def is_valid_image(url: str) -> bool:
        """
        检查URL是否指向有效的图片
        
        :param url: 图片URL
        :return: 是否是有效图片
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            async with httpx.AsyncClient(verify=False) as client:
                # 只获取headers，不下载整个图片
                response = await client.head(url, headers=headers, follow_redirects=True, timeout=5.0)
                
                # 检查状态码
                if response.status_code != 200:
                    logger.error(f"图片URL返回非200状态码: {response.status_code}")
                    return False
                
                # 检查内容类型
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.error(f"URL指向的不是图片，内容类型: {content_type}")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"验证图片URL时出错: {e}")
            return False
            
    @staticmethod
    async def is_appropriate_content(image_path: Path) -> bool:
        """
        检查图片内容是否合适（简单实现版本）
        
        :param image_path: 图片路径
        :return: 内容是否合适
        """
        # 这里可以实现图像内容审核逻辑
        # 如果有第三方内容审核服务可以调用
        
        # 简单版本：只检查文件大小
        try:
            if not image_path.exists():
                logger.error(f"图片文件不存在: {image_path}")
                return False
                
            file_size = image_path.stat().st_size
            
            # 过大的图片可能是高清图或不适当内容
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                logger.warning(f"图片过大: {file_size} 字节，超过 {max_size} 字节")
                return False
            
            return True
        except Exception as e:
            logger.error(f"检查图片内容时出错: {e}")
            return False