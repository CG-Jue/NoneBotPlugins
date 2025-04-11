import os
from pathlib import Path
from typing import Dict, Optional, List
from nonebot.log import logger
import httpx

# 默认配置常量
DEFAULT_KIMI_API_BASE_URL = 'https://api.moonshot.cn/v1'
DEFAULT_KIMI_MODEL = "moonshot-v1-32k"  # 默认模型
# 模型可选 moonshot-v1-128k、moonshot-v1-8k、moonshot-v1-32k、moonshot-v1-auto

# 可用的模型列表及说明
MODEL_INFO = {
    "moonshot-v1-auto": "自动选择模型，根据使用token数量自动选择最合适的模型",
    "moonshot-v1-128k": "大容量模型，最大支持128k上下文长度，适合处理大型文档",
    "moonshot-v1-32k": "标准模型，支持32k上下文长度，适合大多数场景",
    "moonshot-v1-8k": "轻量级模型，支持8k上下文长度，处理速度较快"
}

# 视觉模型列表及说明 
VISION_MODEL_INFO = {
    "moonshot-v1-8k-vision-preview": "视觉轻量级模型，支持8k上下文长度，处理速度较快",
    "moonshot-v1-32k-vision-preview": "视觉标准模型，支持32k上下文长度，适合大多数场景",
    "moonshot-v1-128k-vision-preview": "视觉大容量模型，最大支持128k上下文长度"
}

# 模型与对应视觉模型的映射
MODEL_TO_VISION = {
    "moonshot-v1-auto": "moonshot-v1-32k-vision-preview",  # 自动模式默认使用32k视觉模型
    "moonshot-v1-8k": "moonshot-v1-8k-vision-preview",
    "moonshot-v1-32k": "moonshot-v1-32k-vision-preview", 
    "moonshot-v1-128k": "moonshot-v1-128k-vision-preview"
}

AVAILABLE_MODELS = list(MODEL_INFO.keys())

class ModelManager:
    def __init__(self):
        self.base_path = Path(os.path.dirname(os.path.abspath(__file__)))
        # 模型配置文件路径
        self.model_config_file = self.base_path / "model_config.txt"
        self.vision_model_config_file = self.base_path / "vision_model_config.txt"
        
        # 加载初始模型配置
        self.current_model = self.load_model_config()
        self.current_vision_model = self.load_vision_model_config()
        
    def load_model_config(self) -> str:
        """
        从配置文件加载保存的模型配置
        :return: 保存的模型名称，如果没有保存则返回默认模型
        """
        if self.model_config_file.exists():
            try:
                with open(self.model_config_file, "r", encoding="utf-8") as f:
                    saved_model = f.read().strip()
                    if saved_model and saved_model in AVAILABLE_MODELS:
                        logger.debug(f"从配置文件加载模型: {saved_model}")
                        return saved_model
            except Exception as e:
                logger.error(f"读取模型配置文件失败: {e}")
        
        # 如果没有保存的配置或读取失败，返回默认模型
        return DEFAULT_KIMI_MODEL

    def save_model_config(self, model: str) -> bool:
        """
        保存模型配置到文件
        :param model: 要保存的模型名称
        :return: 是否保存成功
        """
        try:
            with open(self.model_config_file, "w", encoding="utf-8") as f:
                f.write(model)
            logger.info(f"模型配置保存成功: {model}")
            return True
        except Exception as e:
            logger.error(f"保存模型配置文件失败: {e}")
            return False

    def load_vision_model_config(self) -> str:
        """
        从配置文件加载保存的视觉模型配置
        :return: 保存的视觉模型名称，如果没有保存则返回默认视觉模型
        """
        if self.vision_model_config_file.exists():
            try:
                with open(self.vision_model_config_file, "r", encoding="utf-8") as f:
                    saved_model = f.read().strip()
                    if saved_model and saved_model in VISION_MODEL_INFO.keys():
                        logger.debug(f"从配置文件加载视觉模型: {saved_model}")
                        return saved_model
            except Exception as e:
                logger.error(f"读取视觉模型配置文件失败: {e}")
        
        # 如果没有保存的配置或读取失败，返回映射的视觉模型
        return MODEL_TO_VISION.get(self.current_model, "moonshot-v1-32k-vision-preview")

    def save_vision_model_config(self, model: str) -> bool:
        """
        保存视觉模型配置到文件
        :param model: 要保存的视觉模型名称
        :return: 是否保存成功
        """
        try:
            with open(self.vision_model_config_file, "w", encoding="utf-8") as f:
                f.write(model)
            logger.info(f"视觉模型配置保存成功: {model}")
            return True
        except Exception as e:
            logger.error(f"保存视觉模型配置文件失败: {e}")
            return False
    
    def set_model(self, model_name: str) -> bool:
        """
        设置当前使用的模型
        :param model_name: 模型名称
        :return: 是否设置成功
        """
        if model_name not in AVAILABLE_MODELS:
            return False
        
        self.current_model = model_name
        return self.save_model_config(model_name)
    
    def set_vision_model(self, model_name: str) -> bool:
        """
        设置当前使用的视觉模型
        :param model_name: 视觉模型名称
        :return: 是否设置成功
        """
        if model_name not in VISION_MODEL_INFO.keys():
            return False
        
        self.current_vision_model = model_name
        return self.save_vision_model_config(model_name)
    
    async def estimate_token_count(self, messages: list, api_key: str, api_base_url: str) -> Optional[int]:
        """
        计算消息使用的token数量
        
        :param messages: 消息列表
        :param api_key: API密钥
        :param api_base_url: API基础URL
        :return: token数量，如果请求失败则返回None
        """
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"{api_base_url}/tokenizers/estimate-token-count",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    },
                    json={
                        "model": self.current_model,  # 使用当前设置的模型
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
            logger.error(f"计算token数量时出错: {e}")
            return None
    
    async def get_moonshot_balance(self, api_key: str, api_base_url: str) -> Optional[float]:
        """
        查询Moonshot API余额
        
        :param api_key: API密钥
        :param api_base_url: API基础URL
        :return: 可用余额，如果请求失败则返回None
        """
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{api_base_url}/users/me/balance",
                    headers={
                        "Authorization": f"Bearer {api_key}"
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
            logger.error(f"查询余额时出错: {e}")
            return None