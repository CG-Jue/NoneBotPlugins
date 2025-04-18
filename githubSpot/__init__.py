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


# 使用改进的正则表达式匹配可能以 #/ 结尾的链接，并且在遇到换行符时停止匹配
github = on_regex(r"https?://github\.com/([^/\n]+/[^/\n\s]+)(?:#/)?", priority=10, block=False)

# GitHub URL代理类 - 负责处理和清洗URL
class GitHubUrlProxy:
    def __init__(self):
        # 修改正则表达式，确保不会跨越换行符
        self.pattern = r'https?://github\.com/([^/\n]+/[^/\n\s]+)(?:#/)?'
    
    def extract_url(self, text):
        """从文本中提取GitHub URL并清洗"""
        match = re.search(self.pattern, text)
        if not match:
            return None
            
        # 获取匹配的URL并移除#/后缀
        full_url = match.group(0)
        return full_url.split('#')[0]  # 移除#及其后面的内容
    
    async def get_card_info(self, url):
        """代理方法，通过URL获取GitHub卡片信息"""
        if not url:
            return "获取信息失败"
            
        try:
            return await get_github_reposity_information(url)
        except Exception as e:
            logger.error(f"获取GitHub信息时出错: {e}, URL: {url}")
            return "获取信息失败"

# 创建URL代理实例
github_url_proxy = GitHubUrlProxy()
    
@github.handle()
async def github_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 通过代理提取和处理URL
    url = github_url_proxy.extract_url(event.get_plaintext())
    if not url:
        return
    
    # 通过代理获取卡片信息
    imageUrl = await github_url_proxy.get_card_info(url)
    if imageUrl == "获取信息失败":
        logger.error(f"获取GitHub信息失败，URL: {url}")
        return
        
    logger.debug(f"获取到的GitHub卡片url信息: {imageUrl}")
    await github.send(MessageSegment.image(imageUrl))
