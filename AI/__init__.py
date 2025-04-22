from .callai import KimiApiClient
from .rule import *
from .config import Config
from .msghandle import * 

import asyncio
from pathlib import Path
from nonebot.rule import to_me
import nonebot
from nonebot import on_message, get_plugin_config, on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment, GroupMessageEvent
from nonebot.typing import T_State
from nonebot.log import logger
from nonebot.exception import FinishedException
from nonebot.params import CommandArg, ArgStr, ArgPlainText
from nonebot.plugin import PluginMetadata
from nonebot.permission import SUPERUSER
from nonebot import logger



# 获取配置
config_dict = get_plugin_config(Config)

api_key = config_dict.CONFIG.get("kimi_api_key", "")
api_base_url = config_dict.CONFIG.get("kimi_api_base_url", "")
kimi_model = config_dict.CONFIG.get("kimi_model", "")

if not api_key or not api_base_url:
   logger.debug(f"api配置出错")
    

api_client = KimiApiClient(api_key, api_base_url)


history = []

ai_message = on_message(rule=check_if_group_is_true, priority=1, block=False)

@ai_message.handle()
async def ai_msg(bot: Bot, event: Event):

    msg = event.get_plaintext().strip()
    user = event.get_user_id()

    logger.debug(f"消息：{msg}")

    if not msg:
        pass
        # await ai_message.finish("？")
    success, result, token_count, model_used = await api_client.analyze_message(msg, history, kimi_model, user)
   
    success, msg = msghd(success, result)
    if success and not msg == "null":
        await ai_message.finish(msg)
    else:
        logger.debug(f"处理七七的话时出错{msg}")
