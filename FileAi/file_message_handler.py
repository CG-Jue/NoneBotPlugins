import os
import traceback
from typing import Optional, Dict, Any
from nonebot.log import logger

class FileMessageHandler:
    @staticmethod
    async def get_file_info_from_message(message_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        从消息数据中提取文件信息
        
        :param message_data: 消息数据
        :return: 包含文件信息的字典或None
        """
        try:
            # 首先检查消息中是否包含 'message' 字段
            if 'message' in message_data:
                # 遍历消息段寻找文件类型
                for segment in message_data['message']:
                    # 检查是否是文件类型消息段
                    if segment.get('type') == "file":
                        file_info = {}
                        
                        # 参考代码中的方法：直接从 data.file 获取文件名
                        if 'data' in segment:
                            data = segment['data']
                            
                            # 使用 get('file') 获取文件名 - 基于参考实现
                            if 'file' in data:
                                file_name = data['file'].replace("/", "")
                                file_info['file_name'] = file_name
                            # 兼容旧方式
                            elif 'name' in data:
                                file_info['file_name'] = data['name']
                                
                            # 获取文件ID
                            if 'file_id' in data:
                                file_info['file_id'] = data['file_id']
                                
                            # 获取文件大小
                            if 'size' in data:
                                file_info['file_size'] = data['size']
                            
                            # 获取busid (如果有)
                            if 'busid' in data:
                                file_info['busid'] = data['busid']
                            
                            # 如果至少有文件名和文件ID，则返回
                            if 'file_name' in file_info and 'file_id' in file_info:
                                return file_info

                # 尝试其他方式 - 处理特殊格式的文件消息
                for segment in message_data['message']:
                    # 检查其他可能包含文件的消息类型
                    if segment.get('type') == 'json' and 'data' in segment:
                        try:
                            import json
                            json_data = json.loads(segment['data']['data'])
                            
                            # 尝试从自定义JSON格式中提取文件信息
                            if 'file' in json_data:
                                file_data = json_data['file']
                                file_info = {}
                                
                                if 'name' in file_data:
                                    file_info['file_name'] = file_data['name']
                                
                                if 'id' in file_data:
                                    file_info['file_id'] = file_data['id']
                                    
                                if 'size' in file_data:
                                    file_info['file_size'] = file_data['size']
                                    
                                if 'busid' in file_data:
                                    file_info['busid'] = file_data['busid']
                                
                                if 'file_name' in file_info and 'file_id' in file_info:
                                    return file_info
                        except Exception as e:
                            logger.debug(f"解析JSON消息段时出错: {e}")
            
            # 未找到文件
            logger.debug("在消息中未找到文件信息")
            return None
            
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"提取文件信息时出错: {e}\n{error_detail}")
            return None