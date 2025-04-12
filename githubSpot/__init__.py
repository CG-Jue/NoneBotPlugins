from nonebot.rule import T_State
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from .data_source import get_github_reposity_information
from nonebot.plugin import on_regex, PluginMetadata

import re

__plugin_meta__ = PluginMetadata(
    name="githubCard",
    description="自动检测GitHub仓库链接并自动发送卡片信息.",
    usage='通过正则表达式自动检测Github链接',
    type='application',
    homepage='',
    supported_adapters={"~onebot.v11"},
)


github = on_regex(r"https?://github\.com/([^/]+/[^/]+)", priority=10, block=False)

def match_link_parts(link):
    pattern = r'https?://github\.com/([^/]+/[^/]+)'
    match = re.search(pattern, link)
    if match:
        return match.group(0)
    else:
        return None
    
@github.handle()
async def github_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    url = match_link_parts(event.get_plaintext())
    imageUrl = await get_github_reposity_information(url)
    assert(imageUrl != "获取信息失败")
    logger.debug(f"获取到的GitHub卡片url信息: {imageUrl}")
    await github.send(MessageSegment.image(imageUrl))
    