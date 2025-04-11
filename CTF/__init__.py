"""
CTF比赛推送插件

用于自动推送即将开始报名的CTF比赛信息到指定QQ群
数据来源: 
- 国内: https://raw.githubusercontent.com/ProbiusOfficial/Hello-CTFtime/main/CN.json
- 全球: https://raw.githubusercontent.com/ProbiusOfficial/Hello-CTFtime/main/Global.json
"""
from datetime import datetime, timedelta
from nonebot.log import logger
from pathlib import Path
import requests
from nonebot import get_bot, require, get_plugin_config, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, Bot
from nonebot.params import CommandArg
from .config import Config
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="CTF比赛推送",
    description="自动推送即将开始的CTF比赛信息，支持国内和国际CTF赛事",
    usage="""
    定时推送: 
    - 自动推送即将开始的国内和国际CTF赛事到指定QQ群
    
    手动查询: 
    - /查询赛事 [权重]: 查询国内和国际CTF赛事信息，国际赛事权重默认为50
    """,
    homepage="https://github.com/CG-Jue/NoneBotPlugins",
    type="application",
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "dog",
        "version": "1.0.0",
    },
)



# 获取配置
config = get_plugin_config(Config)
DEFAULT_LIMIT_TIME = 30  # 默认检查时间为30分钟
DEFAULT_WAIT_TIME = 3  # 默认提前3天推送
DEFAULT_GROUP_LIST = []  # 默认为空列表
DEFAULT_GLOBAL_MIN_WEIGHT = 50  # 默认全球CTF权重阈值

try:
    limit_time = config.CONFIG.get("LIMIT_TIME", DEFAULT_LIMIT_TIME)
    wait_time = config.CONFIG.get("SEND_TIME", DEFAULT_WAIT_TIME)
    group_list = config.CONFIG.get("SEND_LIST", DEFAULT_GROUP_LIST)
    global_min_weight = config.CONFIG.get("GLOBAL_MIN_WEIGHT", DEFAULT_GLOBAL_MIN_WEIGHT)
    logger.debug(f"配置项已加载: 检查时间：{limit_time}, 推送时间：{wait_time}, 发送的群聊：{group_list}, 比赛权重：{global_min_weight}")
except (AttributeError, KeyError):
    limit_time = DEFAULT_LIMIT_TIME
    wait_time = DEFAULT_WAIT_TIME
    group_list = DEFAULT_GROUP_LIST
    global_min_weight = DEFAULT_GLOBAL_MIN_WEIGHT
    logger.debug(f"配置项加载失败，使用默认值: 检查时间：{limit_time}, 推送时间：{wait_time}, 发送的群聊：{group_list}, 比赛权重：{global_min_weight}")

# 确保db.txt文件存在
DB_PATH = Path(__file__).parent / "db.txt"
if not DB_PATH.exists():
    with open(DB_PATH, "w", encoding="utf-8") as f:
        f.write("")

 
def format_time(time_str: str) -> str:
    """
    格式化时间字符串，只保留月日时分
    
    Args:
        time_str: 时间字符串，格式为"2023年10月01日 12:00"
    
    Returns:
        格式化后的时间字符串，如"10月01日 12:00"
    """
    time_obj = datetime.strptime(time_str, "%Y年%m月%d日 %H:%M")
    return time_obj.strftime("%m月%d日 %H:%M")


def format_global_time(time_str: str) -> str:
    """
    格式化全球赛事时间字符串，转为短格式
    
    Args:
        time_str: 时间字符串，格式为"2025-04-12 01:00:00 - 2025-04-13 01:00:00 UTC+8"
    
    Returns:
        格式化后的时间字符串
    """
    # 提取开始和结束时间
    start_time_str, end_time_str = time_str.split(" - ")
    start_time = datetime.strptime(start_time_str.strip(), "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(end_time_str.split(" UTC")[0].strip(), "%Y-%m-%d %H:%M:%S")
    
    # 格式化为简短形式
    return f"{start_time.strftime('%m月%d日 %H:%M')} - {end_time.strftime('%m月%d日 %H:%M')}"


def calculate_time_difference(start_time: str) -> timedelta:
    """
    计算当前时间和比赛开始报名时间之间的差值
    
    Args:
        start_time: 比赛开始报名时间，格式为"2023年10月01日 12:00"
        
    Returns:
        时间差值 (timedelta)
    """
    start_datetime = datetime.strptime(start_time, "%Y年%m月%d日 %H:%M")
    return start_datetime - datetime.now()


def calculate_global_time_difference(time_str: str) -> timedelta:
    """
    计算当前时间和全球比赛开始时间之间的差值
    
    Args:
        time_str: 时间字符串，格式为"2025-04-12 01:00:00 - 2025-04-13 01:00:00 UTC+8"
        
    Returns:
        时间差值 (timedelta)
    """
    start_time_str = time_str.split(" - ")[0].strip()
    start_datetime = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    return start_datetime - datetime.now()


def fetch_ctf_data(is_global: bool = False) -> dict:
    """
    获取CTF数据
    
    Args:
        is_global: 是否获取全球CTF数据
    
    Returns:
        CTF比赛数据或None(获取失败)
    """
    url = "https://raw.githubusercontent.com/ProbiusOfficial/Hello-CTFtime/main/Global.json" if is_global else "https://raw.githubusercontent.com/ProbiusOfficial/Hello-CTFtime/main/CN.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.debug(f"获取CTF数据失败: {e}")
        return None
    

def is_to_push(time_str: str, wait_time: int, is_global: bool = False) -> bool:
    """
    判断比赛是否在推送时间范围内
    
    Args:
        time_str: 比赛时间字符串
        wait_time: 提前多少天推送
        is_global: 是否为全球比赛
        
    Returns:
        是否应该推送
    """
    if is_global:
        time_difference = calculate_global_time_difference(time_str)
    else:
        time_difference = calculate_time_difference(time_str)
    return time_difference <= timedelta(days=wait_time)


def is_ctf_has_push(ctf_name: str) -> bool:
    """
    判断比赛是否已经推送过
    
    Args:
        ctf_name: 比赛名称
        
    Returns:
        True: 比赛未推送过，已将名称添加到记录
        False: 比赛已推送过
    """
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db_list = [x.strip() for x in f.readlines()]
        
        if ctf_name in db_list:
            return False
        
        with open(DB_PATH, "a", encoding="utf-8") as f:
            f.write(f"{ctf_name}\n")
        return True
    except IOError as e:
        print(f"读写推送记录文件失败: {e}")
        return False


def push_ctf(wait_days: int) -> str:
    """
    获取即将开始的CTF比赛信息
    
    Args:
        wait_days: 提前多少天推送
        
    Returns:
        格式化的比赛信息或None(无需推送)
    """
    # 先检查国内CTF
    ctf_data = fetch_ctf_data(is_global=False)
    if ctf_data:
        upcoming_ctf_list = []
        
        # 查找符合条件的国内比赛
        for ctf in ctf_data["data"]["result"]:
            if (ctf.get("status") == "即将开始" and 
                is_to_push(ctf["reg_time_start"], wait_days) and 
                is_ctf_has_push(ctf["name"])):
                upcoming_ctf_list.append(ctf)
        
        # 有符合条件的国内比赛
        if upcoming_ctf_list:
            ctf = upcoming_ctf_list[0]
            msg = (
                f"（¯﹃¯）{wait_days * 24}小时内开始报名的国内比赛:\n"
                f"比赛名称: {ctf['name']}\n"
                f"报名时间: \n {format_time(ctf['reg_time_start'])} - {format_time(ctf['reg_time_end'])}\n"
                f"比赛时间: \n {format_time(ctf['comp_time_start'])} - {format_time(ctf['comp_time_end'])}\n"
                f"比赛链接: {ctf['link']}\n"
                f"数据来源: Hello-CTFtime\n"
                f"获取其余赛事 /查询赛事 权重(可选)\n"
            )
            return msg
    
    # 检查全球CTF
    global_data = fetch_ctf_data(is_global=True)
    if global_data:
        upcoming_global_ctf_list = []
        
        # 查找符合条件的全球比赛
        for ctf in global_data:
            if (ctf.get("比赛状态") == "oncoming" and 
                float(ctf.get("比赛权重", "0")) >= global_min_weight and
                is_to_push(ctf["比赛时间"], wait_days, is_global=True) and 
                is_ctf_has_push(ctf["比赛名称"])):
                upcoming_global_ctf_list.append(ctf)
        
        # 有符合条件的全球比赛
        if upcoming_global_ctf_list:
            ctf = upcoming_global_ctf_list[0]
            msg = (
                f"（¯﹃¯）{wait_days * 24}小时内开始的国际比赛:\n"
                f"比赛名称: {ctf['比赛名称']}\n"
                f"比赛时间（UTC+8）: \n {format_global_time(ctf['比赛时间'])}\n"
                f"比赛形式: {ctf.get('比赛形式', '未知')}\n"
                f"比赛权重: {ctf.get('比赛权重', '未知')}（仅>={global_min_weight}）\n"
                f"赛事主办: {ctf.get('赛事主办', '未知').split(' (')[0]}\n"
                f"比赛链接: {ctf['比赛链接']}\n"
                f"数据来源: Hello-CTFtime\n"
                f"获取其余赛事 /查询赛事 权重(可选)"
            )
            return msg
    
    return None


# 注册定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler

@scheduler.scheduled_job("interval", minutes=limit_time)
async def ctf_push_job():
    """定时任务，每limit_time分钟执行一次"""
    msg = push_ctf(wait_time)
    # logger.debug(f"CTF推送消息: {msg}")
    if not msg:
        logger.debug("没有符合条件的CTF比赛，无需推送")
        return
    bot = get_bot()
    if not bot:
        logger.debug("获取bot实例失败")
        return
    for group_id in group_list:
        try:
            await bot.send_msg(group_id=group_id, message=str(msg))
        except Exception as e:
            logger.debug(f"向群 {group_id} 发送消息失败: {e}")

# 查询命令注册
query_ctf = on_command("/查询赛事", priority=5)

def get_start_time(ctf: dict) -> datetime:
    """
    从比赛时间中提取开始时间
    
    Args:
        ctf: CTF比赛数据
        
    Returns:
        比赛开始时间的datetime对象
    """
    time_str = ctf["比赛时间"].split(" - ")[0].strip()
    return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")

def fetch_global_ctf_data(min_weight: float = 50.0) -> dict:
    """
    获取全球CTF比赛数据并按权重过滤
    
    Args:
        min_weight: 最小权重阈值
        
    Returns:
        符合条件的CTF比赛列表
    """
    global_data = fetch_ctf_data(is_global=True)
    if not global_data:
        return {"upcoming": [], "ongoing": []}
    
    upcoming_ctfs = []
    ongoing_ctfs = []
    
    for ctf in global_data:
        if ctf.get("比赛状态") not in ["oncoming", "nowrunning"]:  # 跳过已结束的比赛
            continue
        
        try:
            weight = float(ctf.get("比赛权重", "0"))
        except ValueError:
            weight = 0.0
            
        if weight >= min_weight:
            if ctf.get("比赛状态") == "oncoming":
                upcoming_ctfs.append(ctf)
            else:
                ongoing_ctfs.append(ctf)
    
    # 根据开始时间排序，越早开始的排在越前面
    upcoming_ctfs.sort(key=get_start_time)
    ongoing_ctfs.sort(key=get_start_time)
    
    return {"upcoming": upcoming_ctfs, "ongoing": ongoing_ctfs}

def format_ctf_message(ctf: dict, is_upcoming: bool) -> str:
    """
    格式化CTF比赛信息
    
    Args:
        ctf: CTF比赛数据
        is_upcoming: 是否是即将开始的比赛
        
    Returns:
        格式化后的比赛信息
    """
    status = "即将开始" if is_upcoming else "正在进行"
    
    return (
        f"[{status}] {ctf['比赛名称']}\n"
        f"比赛时间: \n {format_global_time(ctf['比赛时间'])}\n"
        f"比赛形式: {ctf.get('比赛形式', '未知')}\n"
        f"比赛权重: {ctf.get('比赛权重', '未知')}\n"
        f"赛事主办: {ctf.get('赛事主办', '未知').split(' (')[0]}\n"
        f"比赛链接: {ctf['比赛链接']}\n"
        f"数据来源: Hello-CTFtime"
    )

def get_cn_start_time(ctf: dict) -> datetime:
    """从国内比赛时间中提取开始时间"""
    try:
        time_str = ctf["comp_time_start"]
        return datetime.strptime(time_str, "%Y年%m月%d日 %H:%M")
    except (KeyError, ValueError):
        # 如果解析失败，返回未来很远的日期，排在最后
        return datetime.now() + timedelta(days=3650)


def fetch_cn_ctf_data() -> dict:
    """获取国内CTF比赛数据"""
    cn_data = fetch_ctf_data(is_global=False)
    if not cn_data or "data" not in cn_data or "result" not in cn_data["data"]:
        return {"upcoming": [], "ongoing": []}
    
    upcoming_ctfs = []
    ongoing_ctfs = []
    
    for ctf in cn_data["data"]["result"]:
        if ctf.get("status") not in ["即将开始", "正在进行"]:  # 跳过已结束的比赛
            continue
        
        if ctf.get("status") == "即将开始":
            upcoming_ctfs.append(ctf)
        else:
            ongoing_ctfs.append(ctf)
    
    # 根据开始时间排序，越早开始的排在越前面
    upcoming_ctfs.sort(key=get_cn_start_time)
    ongoing_ctfs.sort(key=get_cn_start_time)
    
    return {"upcoming": upcoming_ctfs, "ongoing": ongoing_ctfs}


def format_cn_ctf_message(ctf: dict, is_upcoming: bool) -> str:
    """格式化国内CTF比赛信息"""
    status = "即将开始" if is_upcoming else "正在进行"
    contact_info = ""
    if ctf.get("contac") and isinstance(ctf["contac"], dict) and ctf["contac"]:
        contact_items = []
        for k, v in ctf["contac"].items():
            contact_items.append(f"{k}: {v}")
        contact_info = f"联系方式: \n {' | '.join(contact_items)}\n"
    
    return (
        f"[{status}] {ctf['name']}\n"
        f"比赛时间: \n {format_time(ctf['comp_time_start'])} - {format_time(ctf['comp_time_end'])}\n"
        f"报名时间: \n {format_time(ctf['reg_time_start'])} - {format_time(ctf['reg_time_end'])}\n"
        f"比赛形式: {ctf.get('type', '未知')}\n"
        f"比赛标签: {ctf.get('tag', '未知')}\n"
        f"赛事主办: {ctf.get('organizer', '未知')}\n"
        f"{contact_info}"
        f"比赛链接: {ctf['link']}\n"
        f"数据来源: Hello-CTFtime"
    )

@query_ctf.handle()
async def handle_query_ctf(bot:Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """处理查询CTF赛事命令"""
    # 解析权重参数
    arg_str = args.extract_plain_text().strip()
    try:
        min_weight = float(arg_str) if arg_str else DEFAULT_GLOBAL_MIN_WEIGHT
    except ValueError:
        await query_ctf.finish("请输入有效的权重值！(float类型)")
        return
    
    # 获取数据
    global_ctfs = fetch_global_ctf_data(min_weight)
    cn_ctfs = fetch_cn_ctf_data()
    
    # 检查是否有符合条件的比赛
    has_cn_ctf = cn_ctfs["upcoming"] or cn_ctfs["ongoing"]
    has_global_ctf = global_ctfs["upcoming"] or global_ctfs["ongoing"]
    
    if not has_cn_ctf and not has_global_ctf:
        await query_ctf.finish(f"未找到符合条件的比赛信息。")
        return
    
    # 生成主合并转发消息
    main_messages = []
    
    # 添加总览信息
    cn_overview = []
    global_overview = []
    
    # 国内比赛场数统计
    cn_ongoing_count = len(cn_ctfs["ongoing"])
    cn_upcoming_count = len(cn_ctfs["upcoming"])
    
    # 国际比赛场数统计
    global_ongoing_count = len(global_ctfs["ongoing"])
    global_upcoming_count = len(global_ctfs["upcoming"])

    if has_cn_ctf:
        if cn_ongoing_count:
            cn_overview.append(f"正在进行: {cn_ongoing_count}场")
        if cn_upcoming_count:
            cn_overview.append(f"即将开始: {cn_upcoming_count}场")
    
    if has_global_ctf:
        if global_ongoing_count:
            global_overview.append(f"正在进行: {global_ongoing_count}场")
        if global_upcoming_count:
            global_overview.append(f"即将开始: {global_upcoming_count}场")
    
    overview_msg = "CTF比赛查询结果\n"
    if cn_overview:
        overview_msg += f"国内赛事: {' | '.join(cn_overview)}\n"
    if global_overview:
        overview_msg += f"国际赛事: {' | '.join(global_overview)} (权重 ≥ {min_weight})"
    
    main_messages.append({
        'type': 'node',
        'data': {
            'name': 'CTF比赛查询',
            'uin': event.self_id,
            'content': overview_msg
        }
    })
    
    # 构建news参数
    main_news = [{"text": f"CTF比赛查询: {overview_msg}"}]
    
    # 处理国内赛事
    if has_cn_ctf:
        cn_prompt = "国内CTF赛事信息"
        main_messages.append({
            'type': 'node',
            'data': {
                'name': 'CTF比赛查询',
                'uin': event.self_id,
                'content': cn_prompt
            }
        })
        
        # 创建国内比赛合并转发消息
        cn_messages = []
        
        # 添加标题
        cn_messages.append({
            'type': 'node',
            'data': {
                'name': 'CTF比赛查询',
                'uin': event.self_id,
                'content': f"【国内CTF比赛】共{cn_ongoing_count + cn_upcoming_count}场"
            }
        })
        
        # 处理国内正在进行和即将开始的比赛
        if cn_ongoing_count > 0:
            # 添加正在进行的比赛提示
            cn_ongoing_prompt = f"正在进行的比赛 | {cn_ongoing_count}场"
            cn_messages.append({
                'type': 'node',
                'data': {
                    'name': 'CTF比赛查询',
                    'uin': event.self_id,
                    'content': cn_ongoing_prompt
                }
            })
            
            # 创建正在进行的比赛消息列表
            cn_ongoing_messages = []
            for ctf in cn_ctfs["ongoing"]:
                msg_content = format_cn_ctf_message(ctf, is_upcoming=False)
                cn_ongoing_messages.append({
                    'type': 'node',
                    'data': {
                        'name': 'CTF比赛查询',
                        'uin': event.self_id,
                        'content': msg_content
                    }
                })
            
            # 将正在进行的比赛添加到国内比赛消息中
            cn_messages.append({
                'type': 'node',
                'data': {
                    'name': '正在进行的比赛',
                    'uin': event.self_id,
                    'content': cn_ongoing_messages
                }
            })
        
        if cn_upcoming_count > 0:
            # 添加即将开始的比赛提示
            cn_upcoming_prompt = f"即将开始的比赛 | {cn_upcoming_count}场"
            cn_messages.append({
                'type': 'node',
                'data': {
                    'name': 'CTF比赛查询',
                    'uin': event.self_id,
                    'content': cn_upcoming_prompt
                }
            })
            
            # 创建即将开始的比赛消息列表
            cn_upcoming_messages = []
            for ctf in cn_ctfs["upcoming"]:
                msg_content = format_cn_ctf_message(ctf, is_upcoming=True)
                cn_upcoming_messages.append({
                    'type': 'node',
                    'data': {
                        'name': 'CTF比赛查询',
                        'uin': event.self_id,
                        'content': msg_content
                    }
                })
            
            # 将即将开始的比赛添加到国内比赛消息中
            cn_messages.append({
                'type': 'node',
                'data': {
                    'name': '即将开始的比赛',
                    'uin': event.self_id,
                    'content': cn_upcoming_messages
                }
            })
        
        # 将国内比赛消息添加到主消息中
        main_messages.append({
            'type': 'node',
            'data': {
                'name': '国内CTF比赛',
                'uin': event.self_id,
                'content': cn_messages,
                'news': [{"text": f"国内CTF比赛: 共{cn_ongoing_count + cn_upcoming_count}场比赛"}]
            }
        })
        
        # 添加到news中
        main_news.append({"text": f"CTF比赛查询: {cn_prompt}"})
        main_news.append({"text": f"国内CTF比赛: [聊天记录]"})
    
    # 处理国际赛事
    if has_global_ctf:
        global_prompt = f"国际CTF赛事信息 (权重 ≥ {min_weight})"
        main_messages.append({
            'type': 'node',
            'data': {
                'name': 'CTF比赛查询',
                'uin': event.self_id,
                'content': global_prompt
            }
        })
        
        # 创建国际比赛合并转发消息
        global_messages = []
        
        # 添加标题
        global_messages.append({
            'type': 'node',
            'data': {
                'name': 'CTF比赛查询',
                'uin': event.self_id,
                'content': f"【国际CTF比赛】共{global_ongoing_count + global_upcoming_count}场"
            }
        })
        
        # 处理国际正在进行和即将开始的比赛
        if global_ongoing_count > 0:
            # 添加正在进行的比赛提示
            global_ongoing_prompt = f"正在进行的比赛 | {global_ongoing_count}场"
            global_messages.append({
                'type': 'node',
                'data': {
                    'name': 'CTF比赛查询',
                    'uin': event.self_id,
                    'content': global_ongoing_prompt
                }
            })
            
            # 创建正在进行的比赛消息列表
            global_ongoing_messages = []
            for ctf in global_ctfs["ongoing"]:
                msg_content = format_ctf_message(ctf, is_upcoming=False)
                global_ongoing_messages.append({
                    'type': 'node',
                    'data': {
                        'name': 'CTF比赛查询',
                        'uin': event.self_id,
                        'content': msg_content
                    }
                })
            
            # 将正在进行的比赛添加到国际比赛消息中
            global_messages.append({
                'type': 'node',
                'data': {
                    'name': '正在进行的比赛',
                    'uin': event.self_id,
                    'content': global_ongoing_messages
                }
            })
        
        if global_upcoming_count > 0:
            # 添加即将开始的比赛提示
            global_upcoming_prompt = f"即将开始的比赛 | {global_upcoming_count}场"
            global_messages.append({
                'type': 'node',
                'data': {
                    'name': 'CTF比赛查询',
                    'uin': event.self_id,
                    'content': global_upcoming_prompt
                }
            })
            
            # 创建即将开始的比赛消息列表
            global_upcoming_messages = []
            for ctf in global_ctfs["upcoming"]:
                msg_content = format_ctf_message(ctf, is_upcoming=True)
                global_upcoming_messages.append({
                    'type': 'node',
                    'data': {
                        'name': 'CTF比赛查询',
                        'uin': event.self_id,
                        'content': msg_content
                    }
                })
            
            # 将即将开始的比赛添加到国际比赛消息中
            global_messages.append({
                'type': 'node',
                'data': {
                    'name': '即将开始的比赛',
                    'uin': event.self_id,
                    'content': global_upcoming_messages
                }
            })
        
        # 将国际比赛消息添加到主消息中
        main_messages.append({
            'type': 'node',
            'data': {
                'name': '国际CTF比赛',
                'uin': event.self_id,
                'content': global_messages,
                'news': [{"text": f"国际CTF比赛: 共{global_ongoing_count + global_upcoming_count}场比赛 (权重 ≥ {min_weight})"}]
            }
        })
        
        # 添加到news中
        main_news.append({"text": f"CTF比赛查询: {global_prompt}"})
        main_news.append({"text": f"国际CTF比赛: [聊天记录]"})
    
    # 发送合并转发消息
    try:
        await bot.call_api(
            "send_group_forward_msg", 
            group_id=event.group_id, 
            messages=main_messages,
            news=main_news
        )
    except Exception as e:
        await query_ctf.finish(f"发送失败: {e}")