from pydantic import BaseModel
import nonebot

'''
考虑到开源，可能有信息泄漏（虽然没啥用），所以不直接写在代码里
'''

class Config(BaseModel):
    CONFIG: dict = {

        "SEND_LIST": [], # 推送的群号列表

        "SEND_TIME": 1,      # 推送时间差值，即距离报名开始多少天推送
        }