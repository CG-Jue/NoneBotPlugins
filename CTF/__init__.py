"""
CTF比赛推送插件

用于自动推送即将开始报名的CTF比赛信息到指定QQ群
数据来源: https://raw.githubusercontent.com/ProbiusOfficial/Hello-CTFtime/main/CN.json
"""

from datetime import datetime, timedelta
from pathlib import Path
import requests
from nonebot import get_bot, require, get_plugin_config
from .config import Config

# 获取配置
config = get_plugin_config(Config)
DEFAULT_WAIT_TIME = 1  # 默认提前1天推送
DEFAULT_GROUP_LIST = []  # 默认为空列表

try:
    wait_time = config.CONFIG.get("SEND_TIME", DEFAULT_WAIT_TIME)
    group_list = config.CONFIG.get("SEND_LIST", DEFAULT_GROUP_LIST)
except (AttributeError, KeyError):
    wait_time = DEFAULT_WAIT_TIME
    group_list = DEFAULT_GROUP_LIST

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


def fetch_ctf_data() -> dict:
    """
    获取CTF数据
    
    Returns:
        CTF比赛数据或None(获取失败)
    """
    url = "https://raw.githubusercontent.com/ProbiusOfficial/Hello-CTFtime/main/CN.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"获取CTF数据失败: {e}")
        return None
    

def is_to_push(start_time: str, wait_time: int) -> bool:
    """
    判断比赛是否在推送时间范围内
    
    Args:
        start_time: 比赛开始报名时间
        wait_time: 提前多少天推送
        
    Returns:
        是否应该推送
    """
    time_difference = calculate_time_difference(start_time)
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
    ctf_data = fetch_ctf_data()
    if not ctf_data:
        return None

    upcoming_ctf_list = []
    
    # 查找符合条件的比赛
    for ctf in ctf_data["data"]["result"]:
        if (ctf.get("status") == "即将开始" and 
            is_to_push(ctf["reg_time_start"], wait_days) and 
            is_ctf_has_push(ctf["name"])):
            upcoming_ctf_list.append(ctf)
    
    # 没有符合条件的比赛
    if not upcoming_ctf_list:
        return None
    
    # 组装第一个符合条件的比赛信息
    ctf = upcoming_ctf_list[0]
    msg = (
        f"（¯﹃¯）{wait_days * 24}小时内开始报名的比赛:\n"
        f"比赛名称: {ctf['name']}\n"
        f"报名时间: \n {format_time(ctf['reg_time_start'])} - {format_time(ctf['reg_time_end'])}\n"
        f"比赛时间: \n {format_time(ctf['comp_time_start'])} - {format_time(ctf['comp_time_end'])}\n"
        f"比赛链接: {ctf['link']}"
    )
    return msg


# 注册定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler

@scheduler.scheduled_job("interval", minutes=30)
async def ctf_push_job():
    """定时任务，每30分钟执行一次"""
    msg = push_ctf(wait_time)
    
    if not msg:
        return
        
    bot = get_bot()
    for group_id in group_list:
        try:
            await bot.send_msg(group_id=group_id, message=str(msg))
        except Exception as e:
            print(f"向群 {group_id} 发送消息失败: {e}")