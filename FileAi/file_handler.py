import traceback
from typing import Dict, Any, Optional, Tuple
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot
from pathlib import Path

async def build_file_mapping(bot: Bot, group_id: int) -> Dict[str, Dict[str, Any]]:
    """
    构建文件名到file_id的映射字典，包括根目录和所有文件夹内的文件
    
    :param bot: 机器人实例
    :param group_id: 群号
    :return: 文件名到{file_id, busid}的映射字典
    """
    file_mapping = {}
    
    try:
        # 获取根目录文件列表
        root_files = await bot.call_api("get_group_root_files", group_id=group_id)
        # logger.debug(f"根目录文件列表: {root_files}")
        
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
                            group_id=group_id, 
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

async def get_file_url(bot: Bot, group_id: int, file_name: str) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    从群文件中查找并获取文件的下载URL
    
    :param bot: 机器人实例
    :param group_id: 群号
    :param file_name: 文件名
    :return: (成功状态, 文件URL, 错误信息, 文件信息)
    """
    try:
        # 构建文件名到file_id的映射
        file_mapping = await build_file_mapping(bot, group_id)
        logger.debug(f"文件映射: {file_mapping}")
        
        # 查找对应的文件
        if file_name in file_mapping:
            file_info = file_mapping[file_name]
            file_id = file_info['file_id']
            busid = file_info['busid']
            is_in_folder = 'folder_id' in file_info
            
            logger.debug(f"找到文件ID: {file_id}, busid: {busid}, 是否在文件夹中: {is_in_folder}")
            
            # 获取文件URL
            try:
                file_url_info = await bot.call_api(
                    "get_group_file_url", 
                    group_id=group_id, 
                    file_id=file_id,
                    busid=busid
                )
                
                if 'url' not in file_url_info:
                    logger.error(f"获取文件URL失败，返回数据不包含url字段: {file_url_info}")
                    return False, None, "获取文件下载链接失败，无法获取有效的下载地址", None

                file_url = file_url_info['url']
                logger.debug(f"文件下载URL: {file_url}")
                return True, file_url, None, file_info
                
            except Exception as e:
                error_detail = traceback.format_exc()
                logger.error(f"获取文件下载链接时出错: {e}\n{error_detail}")
                return False, None, f"获取文件下载链接失败，原因：{str(e)}", None
        else:
            return False, None, f"在群文件中找不到名为 {file_name} 的文件", None
            
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"获取文件URL时出错: {e}\n{error_detail}")
        return False, None, f"获取文件信息失败，原因：{str(e)}", None