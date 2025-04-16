'''
主要处理：
1. 别人邀请bot进群
2. 添加bot为好友
3. 管理的群有人员变更
4. 入群申请审核系统
'''
from nonebot import on_command, on_request, on_fullmatch, on_regex, on_notice, logger, get_driver
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, GroupRequestEvent, FriendRequestEvent, MessageEvent, Message, MessageSegment
from nonebot.adapters.onebot.v11 import GroupIncreaseNoticeEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11.event import Reply
from nonebot.adapters.onebot.v11.message import MessageSegment as MS
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
import re
import logging
from typing import Dict, Optional, List
import time
import json
import os
import pathlib
from .rule import checkIfWWD

__plugin_meta__ = PluginMetadata(
    name="群组与好友管理",
    description="处理群聊邀请、入群申请、好友申请等事件的审核插件",
    usage="""
    【管理员命令】(仅在审核群有效)
    - 查看入群审核：显示所有待处理的入群申请和群聊邀请
    - 查看好友审核：显示所有待处理的好友申请(仅超管可用)
    - 查看所有审核：以合并转发方式显示所有待处理申请
    - /同意 [请求标识]：手动同意指定请求
    - /拒绝 [请求标识] [理由]：手动拒绝指定请求
    
    【审核流程】
    1. 收到入群申请/群聊邀请/好友申请时，消息会发送到审核群
    2. 管理员可通过回复原消息"同意"或"拒绝 理由"来处理
    3. 管理员也可通过命令"/同意 请求标识"或"/拒绝 请求标识 理由"来处理
    4. 好友申请只能由超级管理员处理
    5. 机器人被邀请进群的请求会显示特定的审核提示
    """,
    extra={
        "unique_name": "group_management",
        "example": "查看所有审核",
        "author": "dog",
        "version": "1.2.0",
    },
)

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
REQUESTS_FILE = os.path.join(DATA_DIR, "pending_requests.json")
FRIEND_REQUESTS_FILE = os.path.join(DATA_DIR, "pending_friend_requests.json")
MESSAGE_MAP_FILE = os.path.join(DATA_DIR, "message_to_flag.json")
FLAG_TYPE_FILE = os.path.join(DATA_DIR, "flag_type.json")

# 确保数据目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 存储待审核的入群请求
# 格式: {flag: {'user_id': user_id, 'group_id': group_id, 'comment': comment, 'time': timestamp, 'message_id': message_id}}
pending_requests: Dict[str, Dict] = {}
# 存储待审核的好友请求
# 格式: {flag: {'user_id': user_id, 'comment': comment, 'time': timestamp, 'message_id': message_id, 'type': 'friend'}}
pending_friend_requests: Dict[str, Dict] = {}
# 消息ID到flag的映射，用于快速查找回复的消息对应的请求
message_to_flag: Dict[int, str] = {}
# 消息类型映射，用于区分不同类型的请求 (group 或 friend)
flag_type: Dict[str, str] = {}

# 配置审核群组ID，管理员在这个群中进行审核
AUDIT_GROUP_ID = 629590326  # 请替换为实际的审核群组ID

# 加载持久化数据
def load_data():
    global pending_requests, pending_friend_requests, message_to_flag, flag_type
    
    try:
        if os.path.exists(REQUESTS_FILE):
            with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
                pending_requests = json.load(f)
                # 将字符串键的消息ID转换回整数
                for flag, data in pending_requests.items():
                    if "message_id" in data:
                        data["message_id"] = int(data["message_id"])
    except Exception as e:
        logger.error(f"加载入群请求数据失败: {e}")
        pending_requests = {}
    
    try:
        if os.path.exists(FRIEND_REQUESTS_FILE):
            with open(FRIEND_REQUESTS_FILE, "r", encoding="utf-8") as f:
                pending_friend_requests = json.load(f)
                # 将字符串键的消息ID转换回整数
                for flag, data in pending_friend_requests.items():
                    if "message_id" in data:
                        data["message_id"] = int(data["message_id"])
    except Exception as e:
        logger.error(f"加载好友请求数据失败: {e}")
        pending_friend_requests = {}
    
    try:
        if os.path.exists(MESSAGE_MAP_FILE):
            with open(MESSAGE_MAP_FILE, "r", encoding="utf-8") as f:
                # 将所有的字符串键转换为整数
                message_to_flag = {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        logger.error(f"加载消息映射数据失败: {e}")
        message_to_flag = {}
    
    try:
        if os.path.exists(FLAG_TYPE_FILE):
            with open(FLAG_TYPE_FILE, "r", encoding="utf-8") as f:
                flag_type = json.load(f)
    except Exception as e:
        logger.error(f"加载请求类型数据失败: {e}")
        flag_type = {}

# 保存持久化数据
def save_data():
    try:
        with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(pending_requests, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存入群请求数据失败: {e}")
    
    try:
        with open(FRIEND_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(pending_friend_requests, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存好友请求数据失败: {e}")
    
    try:
        # 将整数键转换为字符串，以符合JSON规范
        message_map_str_keys = {str(k): v for k, v in message_to_flag.items()}
        with open(MESSAGE_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(message_map_str_keys, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存消息映射数据失败: {e}")
    
    try:
        with open(FLAG_TYPE_FILE, "w", encoding="utf-8") as f:
            json.dump(flag_type, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存请求类型数据失败: {e}")

# 在启动时加载数据
driver = get_driver()

@driver.on_startup
async def _():
    load_data()
    logger.info("已加载审核请求持久化数据")

def 判断是否入群() -> bool:
    """
    根据自定义的逻辑判断是否入群
    
    :结果: 返回是否入群
    """
    # 这个函数将不再使用，改为人工审核
    return True

# 入群请求处理
group_req = on_request(priority=2, block=True)

@group_req.handle()
async def gr_(bot: Bot, matcher: Matcher, event: GroupRequestEvent):
    # 获取入群申请信息
    gid = str(event.group_id)
    flag = event.flag
    sub_type = event.sub_type
    uid = event.user_id
    
    # 只处理已知的请求类型，忽略未知类型
    if sub_type not in ['invite', 'add']:
        logger.warning(f"收到未知类型的群组请求: {sub_type}, flag: {flag}")
        return
    
    # 处理被邀请进群的情况
    if sub_type == 'invite':
        # 发送给审核群
        audit_msg = (
            f"【收到新的入群邀请】\n"
            f"邀请人: {uid}\n"
            f"目标群组: {gid}\n"
            f"请求标识: {flag}\n\n"
            f"管理员回复本条消息「同意」或「拒绝 拒绝理由」进行处理"
        )
        
        try:
            # 尝试发送到审核群
            msg_result = await bot.send_group_msg(group_id=AUDIT_GROUP_ID, message=audit_msg)
            # 存储消息ID和请求信息的映射关系
            message_id = msg_result['message_id']
            
            # 存储请求信息
            pending_requests[flag] = {
                'user_id': uid,
                'group_id': gid,
                'comment': "机器人被邀请进群",
                'time': int(time.time()),
                'message_id': message_id,
                'sub_type': 'invite'  # 标记为邀请类型
            }
            # 建立消息ID到flag的映射
            message_to_flag[message_id] = flag
            # 标记请求类型
            flag_type[flag] = 'group_invite'
            save_data()
            
        except Exception as e:
            # 发送失败，记录日志
            logger.error(f"发送邀请审核消息失败: {e}")
            await matcher.send(f"发送审核消息失败，请管理员手动处理该入群邀请")
        return  # 处理完邀请请求后返回
    
    # 处理普通入群申请
    if sub_type == 'add':
        comment = event.comment
        word = re.findall(re.compile('答案：(.*)'), comment)
        word = word[0] if word else comment
        
        # 发送给审核群
        audit_msg = (
            f"【收到新的入群申请】\n"
            f"申请人: {uid}\n"
            f"目标群组: {gid}\n"
            f"验证信息: {word}\n"
            f"请求标识: {flag}\n\n"
            f"管理员回复本条消息「同意」或「拒绝 拒绝理由」进行处理"
        )
        
        try:
            # 尝试发送到审核群
            msg_result = await bot.send_group_msg(group_id=AUDIT_GROUP_ID, message=audit_msg)
            # 存储消息ID和请求信息的映射关系
            message_id = msg_result['message_id']
            
            # 存储请求信息
            pending_requests[flag] = {
                'user_id': uid,
                'group_id': gid,
                'comment': word,
                'time': int(time.time()),
                'message_id': message_id,
                'sub_type': 'add'  # 标记为普通入群申请
            }
            # 建立消息ID到flag的映射
            message_to_flag[message_id] = flag
            # 标记请求类型
            flag_type[flag] = 'group_add'
            save_data()
            
        except Exception as e:
            # 发送失败，记录日志
            logger.error(f"发送审核消息失败: {e}")
            await matcher.send(f"发送审核消息失败，请管理员手动处理该入群申请")

# 通过回复消息处理入群申请
reply_handler = on_fullmatch("同意",rule=checkIfWWD,permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=2)

@reply_handler.handle()
async def handle_reply(bot: Bot, event: GroupMessageEvent, matcher: Matcher):
    # 只处理审核群中的消息
    if event.group_id != AUDIT_GROUP_ID:
        return
    
    # 检查是否为回复消息
    reply = event.reply
    if not reply:
        return
    
    # 获取被回复的消息ID
    source_message_id = reply.message_id
    
    # 检查是否是对请求消息的回复
    flag = message_to_flag.get(source_message_id)
    if not flag:
        return
    
    # 处理回复内容
    content = event.message.extract_plain_text().strip()
    
    # 检查请求类型并获取请求信息
    if flag in pending_requests:  # 入群请求
        request_info = pending_requests[flag]
        request_type = 'group'
        sub_type = request_info.get('sub_type', 'add')  # 获取子类型，默认为add
    elif flag in pending_friend_requests:  # 好友请求
        request_info = pending_friend_requests[flag]
        request_type = 'friend'
        sub_type = 'add'  # 好友请求没有子类型，统一设为add
        # 好友请求只允许超级管理员处理
        if not await SUPERUSER(bot, event):
            await matcher.send("只有超级管理员才能处理好友请求")
            return
    else:
        return
    
    if content.startswith("同意"):
        try:
            if request_type == 'group':
                if sub_type == 'invite':
                    # 同意邀请进群请求
                    await bot.set_group_add_request(flag=flag, sub_type="invite", approve=True, reason=' ')
                    await matcher.send(f"已同意接受用户 {request_info['user_id']} 的群聊邀请，已加入群 {request_info['group_id']}")
                else:
                    # 同意普通入群申请
                    await bot.set_group_add_request(flag=flag, sub_type="add", approve=True, reason=' ')
                    await matcher.send(f"已同意用户 {request_info['user_id']} 加入群 {request_info['group_id']}")
                # 移除已处理的请求
                pending_requests.pop(flag)
            else:  # friend
                # 同意好友申请
                await bot.set_friend_add_request(flag=flag, approve=True)
                await matcher.send(f"已同意用户 {request_info['user_id']} 的好友申请")
                # 移除已处理的请求
                pending_friend_requests.pop(flag)
            
            # 移除消息映射
            message_to_flag.pop(source_message_id)
            if flag in flag_type:
                flag_type.pop(flag)
            save_data()
                
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            await matcher.send(f"处理请求失败: {e}")
            
    elif content.startswith("拒绝"):
        reason = content[2:].strip() if len(content) > 2 else "管理员拒绝"
        try:
            if request_type == 'group':
                if sub_type == 'invite':
                    # 拒绝邀请进群
                    await bot.set_group_add_request(flag=flag, sub_type="invite", approve=False, reason=reason)
                    await matcher.send(f"已拒绝接受用户 {request_info['user_id']} 的群聊邀请，群号: {request_info['group_id']}，理由: {reason}")
                else:
                    # 拒绝普通入群申请
                    await bot.set_group_add_request(flag=flag, sub_type="add", approve=False, reason=reason)
                    await matcher.send(f"已拒绝用户 {request_info['user_id']} 加入群 {request_info['group_id']}，理由: {reason}")
                # 移除已处理的请求
                pending_requests.pop(flag)
            else:  # friend
                # 拒绝好友申请
                await bot.set_friend_add_request(flag=flag, approve=False)
                await matcher.send(f"已拒绝用户 {request_info['user_id']} 的好友申请，理由: {reason}")
                # 移除已处理的请求
                pending_friend_requests.pop(flag)
            
            # 移除消息映射
            message_to_flag.pop(source_message_id)
            if flag in flag_type:
                flag_type.pop(flag)
            save_data()
                
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            await matcher.send(f"处理请求失败: {e}")

# 查看待处理的入群请求
list_requests = on_command("查看入群审核", rule=checkIfWWD,permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=2, block=True)

@list_requests.handle()
async def handle_list_requests(bot: Bot, event: MessageEvent, matcher: Matcher):
    # 如果是群聊，检查是否在审核群
    if isinstance(event, GroupMessageEvent) and event.group_id != AUDIT_GROUP_ID:
        await matcher.send("此命令只能在指定的审核群中使用")
        return
    
    if not pending_requests:
        await matcher.send("当前没有待处理的入群请求")
        return
    
    msg = "待处理的入群请求列表：\n\n"
    
    for flag, request in pending_requests.items():
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(request['time']))
        msg += (
            f"请求标识: {flag}\n"
            f"申请人: {request['user_id']}\n"
            f"目标群组: {request['group_id']}\n"
            f"验证信息: {request['comment']}\n"
            f"申请时间: {time_str}\n"
            f"---------------------\n"
        )
    
    await matcher.send(msg)

# 查看待处理的好友请求
list_friend_requests = on_command("查看好友审核", rule=checkIfWWD, permission=SUPERUSER, priority=2, block=True)

@list_friend_requests.handle()
async def handle_list_friend_requests(bot: Bot, event: MessageEvent, matcher: Matcher):
    # 如果是群聊，检查是否在审核群
    if isinstance(event, GroupMessageEvent) and event.group_id != AUDIT_GROUP_ID:
        await matcher.send("此命令只能在指定的审核群中使用")
        return
    
    if not pending_friend_requests:
        await matcher.send("当前没有待处理的好友请求")
        return
    
    msg = "待处理的好友请求列表：\n\n"
    
    for flag, request in pending_friend_requests.items():
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(request['time']))
        msg += (
            f"请求标识: {flag}\n"
            f"申请人: {request['user_id']}\n"
            f"验证信息: {request['comment']}\n"
            f"申请时间: {time_str}\n"
            f"---------------------\n"
        )
    
    await matcher.send(msg)

# 查看所有待处理请求（使用合并转发）
list_all_requests = on_command("查看所有审核", rule=checkIfWWD, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=2, block=True)

@list_all_requests.handle()
async def handle_list_all_requests(bot: Bot, event: MessageEvent, matcher: Matcher):
    # 如果是群聊，检查是否在审核群
    if isinstance(event, GroupMessageEvent) and event.group_id != AUDIT_GROUP_ID:
        await matcher.send("此命令只能在指定的审核群中使用")
        return
    
    if not pending_requests and not pending_friend_requests:
        await matcher.send("当前没有任何待处理的请求")
        return
    
    forward_msgs: List[dict] = []
    bot_id = event.self_id  # 获取机器人QQ号
    
    # 添加标题消息
    forward_msgs.append({
        "type": "node",
        "data": {
            "name": "审核系统",
            "uin": bot_id,
            "content": "📋 待处理的审核请求列表"
        }
    })
    
    # 处理入群请求
    if pending_requests:
        # 添加入群请求标题
        forward_msgs.append({
            "type": "node",
            "data": {
                "name": "审核系统",
                "uin": bot_id,
                "content": "🔹 入群请求列表"
            }
        })
        
        # 为每个入群请求创建一条消息
        for flag, request in pending_requests.items():
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(request['time']))
            sub_type = request.get('sub_type', 'add')  # 获取子类型，默认为add
            
            # 根据请求类型创建不同的消息
            if sub_type == 'invite':
                req_type_text = "【群聊邀请】"
                info_text = f"邀请人: {request['user_id']}\n目标群组: {request['group_id']}"
            else:  # 'add'
                req_type_text = "【入群申请】"
                info_text = f"申请人: {request['user_id']}\n目标群组: {request['group_id']}\n验证信息: {request['comment']}"
            
            msg_content = (
                f"{req_type_text}\n"
                f"{info_text}\n"
                f"请求标识: {flag}\n"
                f"申请时间: {time_str}\n\n"
                f"回复「同意 {flag}」或「拒绝 {flag} 原因」处理"
            )
            
            forward_msgs.append({
                "type": "node",
                "data": {
                    "name": "入群申请",
                    "uin": bot_id,
                    "content": msg_content
                }
            })
    
    # 处理好友请求
    if pending_friend_requests:
        # 添加好友请求标题
        forward_msgs.append({
            "type": "node",
            "data": {
                "name": "审核系统",
                "uin": bot_id,
                "content": "🔸 好友请求列表"
            }
        })
        
        # 为每个好友请求创建一条消息
        for flag, request in pending_friend_requests.items():
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(request['time']))
            msg_content = (
                f"【好友申请】\n"
                f"申请人: {request['user_id']}\n"
                f"验证信息: {request['comment']}\n"
                f"请求标识: {flag}\n"
                f"申请时间: {time_str}\n\n"
                f"回复「同意 {flag}」或「拒绝 {flag} 原因」处理"
            )
            
            forward_msgs.append({
                "type": "node",
                "data": {
                    "name": "好友申请",
                    "uin": bot_id,
                    "content": msg_content
                }
            })
    
    # 添加使用说明
    forward_msgs.append({
        "type": "node",
        "data": {
            "name": "审核系统",
            "uin": bot_id,
            "content": "✅ 使用说明：\n1. 回复消息「同意」或「拒绝 原因」\n2. 直接发送「/同意 请求标识」\n3. 直接发送「/拒绝 请求标识 原因」"
        }
    })
    
    # 发送合并转发消息
    if isinstance(event, GroupMessageEvent):
        # 群聊使用合并转发
        await bot.send_group_forward_msg(group_id=event.group_id, messages=forward_msgs)
    else:
        # 私聊使用普通消息
        simple_msg = "当前待处理的请求如下，请在审核群中处理：\n\n"
        
        # 区分入群请求类型
        add_requests = sum(1 for req in pending_requests.values() if req.get('sub_type', 'add') == 'add')
        invite_requests = sum(1 for req in pending_requests.values() if req.get('sub_type') == 'invite')
        
        if add_requests > 0:
            simple_msg += f"入群申请: {add_requests}个\n"
        if invite_requests > 0:
            simple_msg += f"群聊邀请: {invite_requests}个\n"
        if pending_friend_requests:
            simple_msg += f"好友申请: {len(pending_friend_requests)}个\n"
            
        await matcher.send(simple_msg)

# 定期清理过期的入群请求（可选功能）
# 可以添加定时任务，清理长时间未处理的请求

# 好友请求处理
friend_req = on_request(priority=2, block=True)

@friend_req.handle()
async def fr_(bot: Bot, matcher: Matcher, event: FriendRequestEvent):
    # 获取好友申请信息
    flag = event.flag
    uid = event.user_id
    comment = event.comment or "无"
    
    # 发送给审核群
    audit_msg = (
        f"【收到新的好友申请】\n"
        f"申请人: {uid}\n"
        f"验证信息: {comment}\n"
        f"请求标识: {flag}\n\n"
        f"超级管理员回复本条消息「同意」或「拒绝 拒绝理由」进行处理"
    )

    try:
        # 尝试发送到审核群
        msg_result = await bot.send_group_msg(group_id=AUDIT_GROUP_ID, message=audit_msg)
        # 存储消息ID和请求信息的映射关系
        message_id = msg_result['message_id']
        
        # 存储请求信息
        pending_friend_requests[flag] = {
            'user_id': uid,
            'comment': comment,
            'time': int(time.time()),
            'message_id': message_id,
            'type': 'friend'
        }
        # 建立消息ID到flag的映射
        message_to_flag[message_id] = flag
        # 标记请求类型为好友请求
        flag_type[flag] = 'friend'
        save_data()
        
    except Exception as e:
        # 发送失败，记录日志
        logger.error(f"发送好友审核消息失败: {e}")
        await matcher.send(f"发送好友审核消息失败，请管理员手动处理该好友申请")

# 手动同意请求（通过请求标识）
manual_approve = on_command("/同意", rule=checkIfWWD, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=2, block=True)

@manual_approve.handle()
async def handle_manual_approve(bot: Bot, event: MessageEvent, matcher: Matcher, state: T_State):
    # 如果是群聊，检查是否在审核群
    if isinstance(event, GroupMessageEvent) and event.group_id != AUDIT_GROUP_ID:
        await matcher.send("此命令只能在指定的审核群中使用")
        return
    
    # 获取参数（请求标识）
    args = str(event.message).strip().split(" ", 1)
    if len(args) != 2 or not args[1].strip():
        await matcher.send("格式错误，请使用：同意 [请求标识]")
        
        return
    
    flag = args[1].strip()
    
    # 检查请求类型
    if flag in pending_requests:  # 入群请求
        request_info = pending_requests[flag]
        request_type = 'group'
        sub_type = request_info.get('sub_type', 'add')  # 获取子类型，默认为add
    elif flag in pending_friend_requests:  # 好友请求
        request_info = pending_friend_requests[flag]
        request_type = 'friend'
        # 好友请求只允许超级管理员处理
        if not await SUPERUSER(bot, event):
            await matcher.send("只有超级管理员才能处理好友请求")
            return
    else:
        await matcher.send(f"未找到请求标识为 {flag} 的申请")
        return
    
    try:
        if request_type == 'group':
            if sub_type == 'invite':
                # 同意邀请进群请求
                await bot.set_group_add_request(flag=flag, sub_type="invite", approve=True, reason=' ')
                await matcher.send(f"已同意接受用户 {request_info['user_id']} 的群聊邀请，已加入群 {request_info['group_id']}")
            else:
                # 同意普通入群申请
                await bot.set_group_add_request(flag=flag, sub_type="add", approve=True, reason=' ')
                await matcher.send(f"已同意用户 {request_info['user_id']} 加入群 {request_info['group_id']}")
            
            # 如果该请求有关联的消息ID，也从映射中删除
            if 'message_id' in request_info:
                message_id = request_info['message_id']
                if message_id in message_to_flag:
                    message_to_flag.pop(message_id)
            
            # 移除已处理的请求
            pending_requests.pop(flag)
        else:  # friend
            # 同意好友申请
            await bot.set_friend_add_request(flag=flag, approve=True)
            await matcher.send(f"已同意用户 {request_info['user_id']} 的好友申请")
            
            # 如果该请求有关联的消息ID，也从映射中删除
            if 'message_id' in request_info:
                message_id = request_info['message_id']
                if message_id in message_to_flag:
                    message_to_flag.pop(message_id)
            
            # 移除已处理的请求
            pending_friend_requests.pop(flag)
        
        # 从请求类型映射中删除
        if flag in flag_type:
            flag_type.pop(flag)
        
        # 保存更新后的数据
        save_data()
        
    except Exception as e:
        logger.error(f"手动处理请求失败: {e}")
        await matcher.send(f"处理请求失败: {e}")

# 手动拒绝请求（通过请求标识）
manual_reject = on_command("/拒绝", rule=checkIfWWD, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=2, block=True)

@manual_reject.handle()
async def handle_manual_reject(bot: Bot, event: MessageEvent, matcher: Matcher, state: T_State):
    # 如果是群聊，检查是否在审核群
    if isinstance(event, GroupMessageEvent) and event.group_id != AUDIT_GROUP_ID:
        await matcher.send("此命令只能在指定的审核群中使用")
        return
    
    # 获取参数（请求标识和拒绝理由）
    message_text = str(event.message).strip()
    parts = message_text.split(" ", 2)
    
    if len(parts) < 2:
        await matcher.send("格式错误，请使用：拒绝 [请求标识] [拒绝理由(可选)]")
        return
    
    flag = parts[1].strip()
    reason = parts[2].strip() if len(parts) > 2 else "管理员拒绝"
    
    # 检查请求类型
    if flag in pending_requests:  # 入群请求
        request_info = pending_requests[flag]
        request_type = 'group'
        sub_type = request_info.get('sub_type', 'add')  # 获取子类型，默认为add
    elif flag in pending_friend_requests:  # 好友请求
        request_info = pending_friend_requests[flag]
        request_type = 'friend'
        # 好友请求只允许超级管理员处理
        if not await SUPERUSER(bot, event):
            await matcher.send("只有超级管理员才能处理好友请求")
            return
    else:
        await matcher.send(f"未找到请求标识为 {flag} 的申请")
        return
    
    try:
        if request_type == 'group':
            if sub_type == 'invite':
                # 拒绝邀请进群请求
                await bot.set_group_add_request(flag=flag, sub_type="invite", approve=False, reason=reason)
                await matcher.send(f"已拒绝接受用户 {request_info['user_id']} 的群聊邀请，群号: {request_info['group_id']}，理由: {reason}")
            else:
                # 拒绝普通入群申请
                await bot.set_group_add_request(flag=flag, sub_type="add", approve=False, reason=reason)
                await matcher.send(f"已拒绝用户 {request_info['user_id']} 加入群 {request_info['group_id']}，理由: {reason}")
            
            # 如果该请求有关联的消息ID，也从映射中删除
            if 'message_id' in request_info:
                message_id = request_info['message_id']
                if message_id in message_to_flag:
                    message_to_flag.pop(message_id)
            
            # 移除已处理的请求
            pending_requests.pop(flag)
        else:  # friend
            # 拒绝好友申请
            await bot.set_friend_add_request(flag=flag, approve=False)
            await matcher.send(f"已拒绝用户 {request_info['user_id']} 的好友申请，理由: {reason}")
            
            # 如果该请求有关联的消息ID，也从映射中删除
            if 'message_id' in request_info:
                message_id = request_info['message_id']
                if message_id in message_to_flag:
                    message_to_flag.pop(message_id)
            
            # 移除已处理的请求
            pending_friend_requests.pop(flag)
        
        # 从请求类型映射中删除
        if flag in flag_type:
            flag_type.pop(flag)
        
        # 保存更新后的数据
        save_data()
        
    except Exception as e:
        logger.error(f"手动处理请求失败: {e}")
        await matcher.send(f"处理请求失败: {e}")

# 处理群成员增加通知事件
group_increase_notice = on_notice(priority=2, block=True)

@group_increase_notice.handle()
async def handle_group_increase_notice(bot: Bot, event: GroupIncreaseNoticeEvent):
    group_id = event.group_id
    user_id = event.user_id
    sub_type = event.sub_type
    operator_id = getattr(event, 'operator_id', None)
    
    # 判断是否为机器人被邀请进群的情况
    if sub_type == "invite" and user_id == event.self_id:
        # 发送通知消息到审核群
        notice_msg = (
            f"【机器人被邀请入群通知】\n"
            f"机器人已被 {operator_id} 邀请加入群 {group_id}\n"
            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    else:
        # 普通成员加入群的情况
        notice_msg = (
            f"【群成员增加通知】\n"
            f"群号: {group_id}\n"
            f"新成员: {user_id}\n"
            f"操作人: {operator_id}\n"
            f"加入方式: {sub_type}\n"
        )

    try:
        await bot.send_group_msg(group_id=AUDIT_GROUP_ID, message=notice_msg)
    except Exception as e:
        logger.error(f"发送群成员增加通知消息失败: {e}")