from pydantic import BaseModel


class Config(BaseModel):
    CONFIG: dict = {
        # "SEND_LIST": [629590326,445629724], # 推送的群号列表 测试
        "SEND_LIST": [936493920,391680981], # 推送的群号列表
        "SEND_TIME": 1,                     # 推送时间差值，即距离报名开始多少天推送
        }