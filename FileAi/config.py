from pydantic import BaseModel

'''
考虑到开源，泄漏信息（虽然没啥用），所以不直接写在代码里
'''

class Config(BaseModel):
    CONFIG: dict = {
        "kimi_api_key": "sk-", # apikey
        "kimi_api_base_url": "https://api.moonshot.cn/v1",  # api地址                    
        "kimi_model": "moonshot-v1-auto",      # 模型
        "kimi_vision_model": "moonshot-v1-8k-vision-preview"  # 视觉模型
        }