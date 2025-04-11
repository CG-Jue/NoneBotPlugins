import traceback
import base64
import httpx
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from nonebot.log import logger
from openai import OpenAI

class KimiApiClient:
    def __init__(self, api_key: str, api_base_url: str):
        """
        初始化Kimi API客户端
        
        :param api_key: API密钥
        :param api_base_url: API基础URL
        """
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base_url,
        )
        
    async def estimate_token_count(self, messages: list, model: str) -> Optional[int]:
        """
        估算消息的 token 数量
        
        :param messages: 消息列表
        :param model: 使用的模型名称
        :return: token 数量，如果请求失败则返回 None
        """
        try:
            # 根据 Moonshot 官方文档实现 token 计算
            # 参考: https://platform.moonshot.cn/docs/api/misc#%E8%AE%A1%E7%AE%97-token
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"{self.api_base_url}/tokenizers/estimate-token-count",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json={
                        "model": model,
                        "messages": messages
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.debug(f"Token 计算响应: {result}")
                    
                    # 检查响应格式，从正确的字段中提取 token 数量
                    if "data" in result and "total_tokens" in result["data"]:
                        token_count = result["data"]["total_tokens"]
                        logger.debug(f"估算的 token 数量: {token_count}")
                        return token_count
                
                logger.error(f"计算 token 失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"计算 token 数量时出错: {e}\n{error_detail}")
            return None
    
    async def analyze_file(self, file_path: Path, filename: str, message: str, model: str) -> Tuple[bool, str, Optional[str], Optional[int], str]:
        """使用Kimi API解析文件内容
        
        :param file_path: 文件路径
        :param filename: 文件名
        :param message: 用户发送的消息/指令
        :param model: 使用的模型名称
        :return: (成功状态, 结果或错误信息, kimi_file_id, token数量, 使用的模型名称)
        """
        kimi_file_id = None
        token_count = None
        
        try:
            # 上传文件
            try:
                file_object = self.client.files.create(file=file_path, purpose="file-extract")
                kimi_file_id = file_object.id
                logger.debug(f"文件上传到Kimi成功，文件ID: {kimi_file_id}")
            except Exception as e:
                error_detail = traceback.format_exc()
                logger.error(f"上传文件到Kimi API失败: {e}\n{error_detail}")
                return False, f"上传文件到AI服务时出错: {str(e)}", None, None, model
            
            # 获取文件内容
            try:
                file_content = self.client.files.content(file_id=kimi_file_id).text
            except Exception as e:
                error_detail = traceback.format_exc()
                logger.error(f"从Kimi API获取文件内容失败: {e}\n{error_detail}")
                return False, f"AI服务提取文件内容时出错: {str(e)}", kimi_file_id, None, model
            
            if not message:
                message = "请分析文件内容并总结要点"

            # 构建请求
            messages = [
                {
                    "role": "system",
                    "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手。请分析用户上传的文件内容，并提供清晰、简洁的总结，不要使用markdown格式回答，请使用纯字符串回答，如过结果中有markdown格式的字符，请去除。只关注文件的主要内容，不要提及自己是AI助手。以最简洁的方式回答用户的问题。",
                },
                {
                    "role": "system",
                    "content": file_content,  # 文件内容
                },
                {"role": "user", "content": f"请基于文件（{filename}）的内容回答。{message}"},
            ]
            
            # 计算 token 数量
            try:
                token_count = await self.estimate_token_count(messages, model)
                logger.debug(f"文件分析请求的 token 数量: {token_count}")
            except Exception as e:
                logger.warning(f"计算 token 失败，但将继续处理请求: {e}")
            
            # 调用API获取回答
            try:
                # 设置较长的超时时间
                completion = self.client.chat.completions.create(
                    model=model,  # 使用指定的模型
                    messages=messages,
                    temperature=0.3,
                    timeout=60.0  # 增加超时时间到60秒
                )
                if not completion or not completion.choices:
                    logger.error("Kimi API返回的结果为空或没有选项")
                    return False, "AI返回的结果为空，请稍后再试", kimi_file_id, token_count, model
                    
                return True, completion.choices[0].message.content, kimi_file_id, token_count, model
            except Exception as e:
                error_detail = traceback.format_exc()
                logger.error(f"调用Kimi API解析文件内容失败: {e}\n{error_detail}")
                return False, f"AI分析文件内容时出错: {str(e)}", kimi_file_id, token_count, model
            
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"文件分析过程中出错: {e}\n{error_detail}")
            return False, f"解析文件时出错: {str(e)}", kimi_file_id, token_count, model
            
    async def analyze_image(self, image_path: Path, filename: str, message: str, vision_model: str) -> Tuple[bool, str, Optional[str], Optional[int], str]:
        """使用 Kimi 视觉模型解析图片内容
        
        :param image_path: 图片路径
        :param filename: 文件名
        :param message: 用户发送的消息/指令
        :param vision_model: 使用的视觉模型名称
        :return: (成功状态, 结果或错误信息, kimi_file_id, token数量, 使用的模型名称)
        """
        kimi_file_id = None
        token_count = None
        
        try:
            # 检查图片格式，确保是支持的图片类型
            if not str(image_path).lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif')):
                return False, "不支持的图片格式，仅支持 JPG、JPEG、PNG、GIF、BMP、WEBP 和 TIFF 格式", None, None, vision_model
                
            # 读取图片文件，转换为 base64 编码
            try:
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    logger.debug(f"成功读取图片并转换为 base64，大小: {len(image_bytes)} 字节")
            except Exception as e:
                error_detail = traceback.format_exc()
                logger.error(f"读取图片文件失败: {e}\n{error_detail}")
                return False, f"读取图片文件失败: {str(e)}", None, None, vision_model
                
            # 构建请求消息
            if not message:
                message = "请描述这张图片的内容"
                
            # 构建带图片的消息
            messages = [
                {
                    "role": "system",
                    "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手。请分析用户上传的图片内容，并提供清晰、简洁的描述，不要使用markdown格式回答，请使用纯字符串回答，如过结果中有markdown格式的字符，请去除。只关注图片的主要内容，不要提及自己是AI助手。以最简洁的方式回答用户的问题。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
                
            # 计算 token 数量 - 注意：对于图片请求可能不支持预估 token
            try:
                token_count = await self.estimate_token_count(messages, vision_model)
                logger.debug(f"图片分析请求的 token 数量: {token_count}")
            except Exception as e:
                logger.warning(f"计算图片请求的 token 失败，但将继续处理请求: {e}")
                
            # 调用API获取回答
            try:
                # 设置较长的超时时间
                completion = self.client.chat.completions.create(
                    model=vision_model,  # 使用指定的视觉模型
                    messages=messages,
                    temperature=0.3,
                    timeout=60.0  # 增加超时时间到60秒
                )
                
                if not completion or not completion.choices:
                    logger.error("Kimi API返回的结果为空或没有选项")
                    return False, "AI返回的结果为空，请稍后再试", None, token_count, vision_model
                    
                return True, completion.choices[0].message.content, None, token_count, vision_model
                
            except Exception as e:
                error_detail = traceback.format_exc()
                logger.error(f"调用Kimi API解析图片内容失败: {e}\n{error_detail}")
                return False, f"AI分析图片内容时出错: {str(e)}", None, token_count, vision_model
            
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"图片分析过程中出错: {e}\n{error_detail}")
            return False, f"解析图片时出错: {str(e)}", kimi_file_id, token_count, vision_model

    async def get_moonshot_balance(self) -> Optional[float]:
        """
        查询 Moonshot API 账户余额
        
        :return: 可用余额，如果请求失败则返回 None
        """
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{self.api_base_url}/users/me/balance",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.debug(f"余额查询响应: {result}")
                    
                    # 检查响应格式，从正确的字段中提取余额
                    if "data" in result and "available_balance" in result["data"]:
                        balance = result["data"]["available_balance"]
                        logger.debug(f"可用余额: {balance}")
                        return balance
                
                logger.error(f"查询余额失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"查询余额时出错: {e}\n{error_detail}")
            return None