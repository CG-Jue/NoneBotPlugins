import os
import tempfile
import time
from pathlib import Path
import traceback
import httpx
from typing import Optional, Tuple, Dict, Any, List
from nonebot.log import logger

# 添加最大文件大小限制（100MB）
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB（字节）

def is_supported_file_format(filename: str) -> bool:
    """
    检查文件格式是否被Kimi支持
    
    :param filename: 文件名
    :return: 是否支持
    """
    # Kimi支持的文件扩展名列表
    supported_formats = [
        # 文档类
        '.pdf', '.txt', '.csv', '.doc', '.docx', '.xls', '.xlsx', 
        '.ppt', '.pptx', '.md', '.epub', '.html', '.json', '.mobi', 
        # 日志和配置文件
        '.log', '.yaml', '.yml', '.ini', '.conf',
        # 代码类
        '.go', '.h', '.c', '.cpp', '.cxx', '.cc', '.cs', '.java', 
        '.js', '.css', '.jsp', '.php', '.py', '.py3', '.asp', '.ts', '.tsx',
        # 图片类
        '.png', '.jpg', '.jpeg'
    ]
    
    # 提取文件扩展名（转为小写以便忽略大小写）
    _, file_extension = os.path.splitext(filename.lower())
    
    return file_extension in supported_formats

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
        
        # 尝试使用外部工具下载（通常对 SSL 问题更宽容）
        try:
            import subprocess
            import sys
            
            logger.debug(f"尝试使用 curl 下载文件: {file_url}")
            
            # 使用 curl 命令下载文件
            curl_cmd = [
                "curl", "-L", "-k", "-s", "-o", str(file_path), 
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "--connect-timeout", "30",
                file_url
            ]
            
            # 执行 curl 命令
            process = subprocess.Popen(
                curl_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            _, stderr = process.communicate()
            
            if process.returncode == 0 and file_path.exists() and file_path.stat().st_size > 0:
                logger.debug(f"使用 curl 成功下载文件: {file_path}")
                return file_path
            else:
                stderr_text = stderr.decode('utf-8', errors='ignore')
                logger.warning(f"使用 curl 下载文件失败: {stderr_text}")
                # 继续尝试其他方法
        except Exception as e:
            logger.warning(f"尝试使用 curl 下载失败: {e}，将尝试使用 httpx")
        
        # 如果 curl 失败，尝试使用 httpx
        try:
            # 构建自定义的 SSL 上下文
            import ssl
            
            # 创建最宽松的 SSL 上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.set_ciphers('DEFAULT')  # 使用系统默认的加密套件
            
            # 尝试使用所有可用的 TLS 版本
            ssl_context.options &= ~ssl.OP_NO_SSLv2
            ssl_context.options &= ~ssl.OP_NO_SSLv3
            ssl_context.options &= ~ssl.OP_NO_TLSv1
            ssl_context.options &= ~ssl.OP_NO_TLSv1_1
            ssl_context.options &= ~ssl.OP_NO_TLSv1_2
            ssl_context.options &= ~ssl.OP_NO_TLSv1_3
            
            logger.debug(f"尝试使用 httpx 下载文件: {file_url}")
            
            async with httpx.AsyncClient(
                verify=False,
                http2=True,  # 启用 HTTP/2
                timeout=60.0,  # 增加超时时间
                trust_env=True,  # 信任系统环境变量中的代理设置
            ) as client:
                response = await client.get(
                    file_url, 
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive"
                    }
                )
                
                if response.status_code == 200 and response.content:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    logger.debug(f"使用 httpx 成功下载文件: {file_path}")
                    return file_path
                else:
                    logger.warning(f"使用 httpx 下载文件失败，HTTP状态码: {response.status_code}，响应内容: {response.text[:200]}")
                    raise RuntimeError(f"下载文件失败，服务器返回状态码: {response.status_code}")
                    
        except httpx.ConnectError as e:
            logger.error(f"连接错误: {e}")
            if "ssl" in str(e).lower() or "tls" in str(e).lower():
                logger.error(f"SSL证书验证错误: {e}")
                # 不立即抛出错误，尝试最后一种方法
            else:
                logger.error(f"连接服务器失败: {e}")
                # 不立即抛出错误，尝试最后一种方法
        except httpx.RequestError as e:
            logger.error(f"请求文件时网络错误: {e}")
            # 不立即抛出错误，尝试最后一种方法
        
        # 最后尝试使用 urllib3
        try:
            import urllib3
            import certifi
            
            # 禁用警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 创建一个 PoolManager，禁用证书验证
            http = urllib3.PoolManager(
                cert_reqs='CERT_NONE',
                ca_certs=None,
                timeout=30.0,
                retries=3
            )
            
            logger.debug(f"尝试使用 urllib3 下载文件: {file_url}")
            
            response = http.request(
                'GET', 
                file_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                preload_content=False
            )
            
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.stream(1024):
                        f.write(chunk)
                response.release_conn()
                logger.debug(f"使用 urllib3 成功下载文件: {file_path}")
                return file_path
            else:
                response.release_conn()
                logger.warning(f"使用 urllib3 下载文件失败，HTTP状态码: {response.status}")
        except Exception as e:
            logger.error(f"使用 urllib3 下载文件失败: {e}")
        
        # 如果所有方法都失败了
        raise RuntimeError("尝试了多种下载方法，但都无法下载文件。请检查网络连接和文件URL是否有效。")
        
    except Exception as e:
        if not isinstance(e, RuntimeError):
            error_detail = traceback.format_exc()
            logger.error(f"下载文件'{filename}'时出错: {e}\n{error_detail}")
            raise RuntimeError(f"下载文件过程中出错: {str(e)}")
        raise e

async def cleanup_files(kimi_file_id: Optional[str], local_file_path: Optional[Path], client=None):
    """清理文件，删除Kimi API中的文件和本地临时文件"""
    # 删除Kimi API中的文件
    if kimi_file_id and client:
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