from pydantic import BaseModel
from nonebot import get_driver

class Config(BaseModel):
    """CTF比赛推送插件设置"""
    
    CONFIG :dict= {
        "SEND_LIST": [], # 推送的群号列表 测试
        "SEND_TIME": 3,  # 提前天数
        "LIMIT_TIME": 30,  # 检查是否推送的时间，单位为分钟
        "GLOBAL_MIN_WEIGHT": 50  # 国际比赛的最小权重阈值
    }