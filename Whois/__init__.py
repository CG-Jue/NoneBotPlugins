import httpx
import re
import os
from nonebot.permission import SUPERUSER

from nonebot import on_command, on_message, on_regex
from nonebot.adapters.onebot.v11 import Message, Bot, Event, GroupMessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot import get_plugin_config
from typing import Optional, Tuple, List, Set
from .rule import is_group_allowed, add_abled_group, remove_abled_group

__plugin_meta__ = PluginMetadata(
    name="whois查询",
    description="查询域名的whois信息，包括注册信息、到期日期等详细数据",
    usage="""
    自动查询:
    - 直接发送域名，机器人会自动识别并查询
    
    指令查询:
    - /whois <域名>: 查询指定域名的whois信息
    - /whois <域名> -all: 查询完整的原始whois信息
    
    管理命令(仅超级用户):
    - /启用whois: 在当前群启用whois功能
    - /禁用whois: 在当前群禁用whois功能
    """,
    type="application",
    homepage="https://github.com/CG-Jue/NoneBotPlugins",
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "dog",
        "version": "1.0.0",
    },
)

# 添加权限控制命令，只允许超级用户使用
disable_whois = on_regex(r"^/禁用\s*whois$", priority=5, permission=SUPERUSER)
enable_whois = on_regex(r"^/启用\s*whois$", priority=5, permission=SUPERUSER)

# 原有的whois命令，添加权限检查rule
whois_search = on_command('/whois', aliases={'/whois查询'}, priority=5, rule=is_group_allowed)

# 域名匹配处理器，添加权限检查rule
domain_matcher = on_message(rule=is_group_allowed, priority=10)

# 定义常见的顶级域名(TLDs)
COMMON_TLDS = {
    # 通用顶级域名
    "com", "org", "net", "edu", "gov", "mil", "int", "info", "biz", "name", 
    "pro", "museum", "aero", "coop", "jobs", "travel", "mobi", "asia", "tel",
    "xxx", "app", "blog", "dev", "online", "site", "store", "tech", "xyz",
    
    # 国家和地区顶级域名
    "cn", "us", "uk", "jp", "fr", "de", "ru", "au", "ca", "br", "in", 
    "it", "nl", "es", "se", "no", "fi", "dk", "ch", "at", "be", "hk", 
    "tw", "sg", "kr", "nz", "mx", "ar", "co", "eu", "io", "me", "tv",
    
    # 常见多级域名
    "co.uk", "co.jp", "com.cn", "org.cn", "net.cn", "gov.cn", "ac.cn",
    "com.hk", "com.tw", "co.nz", "co.kr", "or.jp", "ac.jp", "ne.jp"

    # 补充
    "ci"
}

# 判断是否为有效的常见域名
def is_common_domain(text: str) -> bool:
    # 先执行简单的格式检查
    if not "." in text:
        return False
        
    # 检查是否只包含有效字符
    if not all(c.isalnum() or c in ".-" for c in text):
        return False
        
    # 验证顶级域名是否在常见列表中
    parts = text.lower().split('.')
    
    # 限制只匹配两段式域名格式 (如example.com)，不匹配三段或更多段的域名
    if len(parts) != 2:
        return False
    
    # 检查是否为常见的顶级域名
    tld = parts[-1]
    return tld in COMMON_TLDS

async def get_whois_info(domain: str) -> Optional[dict]:
    url = f"http://whois.4.cn/api/main?domain={domain}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            if response.status_code != 200:
                return None
            data = response.json()
            if data.get("retcode") != 0:
                return None
            return data.get("data")
    except Exception:
        return None

def parse_domain(input: str) -> Tuple[str, bool]:
    parts = input.split()
    if not parts:
        return "", False
    if parts[-1].lower() == "-all":
        return " ".join(parts[:-1]), True
    return " ".join(parts), False

def format_whois_result(data: dict) -> str:
    def get_field(field, default="暂无信息"):
        return data.get(field) or default
    
    domain_name = get_field("domain_name")
    registrars = get_field("registrars")
    expire_date = get_field("expire_date")
    create_date = get_field("create_date")
    update_date = get_field("update_date")
    
    
    status_list = data.get("status", [])
    status = "\n".join([f"• {s}" for s in status_list]) if status_list else "• 暂无状态信息"
    
    
    nameserver_list = data.get("nameserver", [])
    nameserver = "\n".join([f"• {ns}" for ns in nameserver_list]) if nameserver_list else "• 暂无DNS信息"
    
    
    owner_info = [
        f"├ 姓名：{get_field('owner_name')}",
        f"├ 机构：{get_field('owner_org')}",
        f"├ 邮箱：{get_field('owner_email')}",
        f"└ 电话：{get_field('owner_phone')}"
    ]
    
    return f"""
🔍 whois 查询结果 [ {domain_name} ]
──────────────────────────────
🗓 注册信息：
├ 注册机构：{registrars}
├ 创建时间：{create_date}
├ 到期时间：{expire_date}
└ 更新时间：{update_date}

📊 域名状态：
{status}

🌐 DNS 服务器：
{nameserver}

👤 持有人信息：
{'\n'.join(owner_info)}
──────────────────────────────
""".strip()

@disable_whois.handle()
async def handle_disable_whois(bot: Bot, event: Event):
    # 只处理群消息
    if not isinstance(event, GroupMessageEvent):
        await disable_whois.finish(MessageSegment.reply(event.message_id) 
                                 + MessageSegment.at(int(event.user_id))
                                 + MessageSegment.text("此命令仅在群聊中可用"))
        
    
    # 从启用列表中移除
    success = remove_abled_group(event.group_id)
    if success:
        await disable_whois.finish(MessageSegment.reply(event.message_id) 
                                 + MessageSegment.at(int(event.user_id))
                                 + MessageSegment.text("已禁用本群的whois查询功能"))
    else:
        await disable_whois.finish(MessageSegment.reply(event.message_id) 
                                 + MessageSegment.at(int(event.user_id))
                                 + MessageSegment.text("本群的whois查询功能已经是禁用状态"))
        
@enable_whois.handle()
async def handle_enable_whois(bot: Bot, event: Event):
    # 只处理群消息
    if not isinstance(event, GroupMessageEvent):
        await enable_whois.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("此命令仅在群聊中可用"))
        
    
    # 添加到启用列表
    success = add_abled_group(event.group_id)
    if success:
        await enable_whois.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("已启用本群的whois查询功能"))
    else:
        await enable_whois.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("本群的whois查询功能已经是启用状态"))

@whois_search.handle()
async def handle_whois_search(bot: Bot, event: Event, args: Message = CommandArg()):
    input_str = args.extract_plain_text().strip()
    if not input_str:
        await whois_search.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("请输入要查询的域名，例如：/whois example.com"))
    
    domain, show_all = parse_domain(input_str)
    if not domain:
        await whois_search.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("域名不能为空！"))
    
    # 只可以在群聊中使用
    if not isinstance(event, GroupMessageEvent):
        await whois_search.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("whois查询功能仅在群聊中可用"))

    data = await get_whois_info(domain)
    if not data:
        await whois_search.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("whois查询失败，请检查域名格式或稍后再试"))
    
    if show_all:
        raw_data = data.get("meta_data", "暂无原始信息")
        await whois_search.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text(f"原始whois信息：\n{raw_data}"))
    else:
        result = format_whois_result(data)
        await whois_search.finish(MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text(result))

@domain_matcher.handle()
async def handle_domain_message(bot: Bot, event: Event):
    # 获取消息文本
    msg = event.get_plaintext().strip()
    
    # 忽略过短的消息
    if len(msg) < 4:  # 最短的域名如a.io长度为4
        return
    
    # 忽略命令消息
    if msg.startswith('/') or msg.startswith('!') or msg.startswith('！'):
        return
    
    # 检查是否是群聊消息
    if not isinstance(event, GroupMessageEvent):
        return

    # 检查消息是否就是一个域名（无需正则匹配）
    if is_common_domain(msg):
        domain = msg
        await bot.send(event, MessageSegment.reply(event.message_id) 
                            + MessageSegment.at(int(event.user_id))
                            + MessageSegment.text(f"检测到域名: {domain} 正在查询whois信息..."))
        
        data = await get_whois_info(domain)
        if not data:
            await bot.send(event, MessageSegment.reply(event.message_id) 
                                + MessageSegment.at(int(event.user_id))
                                + MessageSegment.text("whois查询失败，请检查域名格式或稍后再试"))
            return
        
        result = format_whois_result(data)
        await bot.send(event, MessageSegment.reply(event.message_id) 
                            + MessageSegment.at(int(event.user_id))
                            + MessageSegment.text(result))
        return