from nonebot import logger, get_driver
import nonebot

async def 踢出(gid, uid_or_uidlist:list | int, reject_add_request=False):
    '''
    踢出群

    参数：

    gid: 群号

    uid_or_uidlist : 单个 或者 数组

    reject_add_request: 是否拉黑，默认不拉黑
    
    '''

    state = ",已拉黑." if reject_add_request else "."
    bot = nonebot.get_bot()
    
    # 一个人
    if isinstance(uid_or_uidlist, int): 
        await bot.call_api("set_group_kick", gid, uid_or_uidlist, reject_add_request)
        logger.debug(f"在群 {gid} 踢出 {uid}{state}")
    
    # 适用于连坐
    if isinstance(uid_or_uidlist, int): 
        for uid in uid_or_uidlist:
            await bot.call_api("set_group_kick", gid, uid_or_uidlist, reject_add_request)
            logger.debug(f"在群 {gid} 踢出 {uid}{state}")
            




async def 禁言(gid, uid, time:int = 10 * 60 ):

    """
    禁言
    
    参数：

    gid: 群号

    uid: 用户号

    time: 禁言时间，单位秒，默认10分钟
    """

    bot = nonebot.get_bot()

    await bot.set_group_ban(group_id=gid, user_id=uid, duration=time)
    logger.info(f"禁言成功，群号：{gid}，用户号：{uid}，禁言时间：{time}秒")


async def 撤回消息(msgid):

    """
    撤回消息
    
    参数：

    msgid: 消息id

    """

    bot = nonebot.get_bot()


    await bot.delete_msg(message_id=msgid)
    logger.info(f"撤回消息成功，消息id：{msgid}")


async def 查找用户角色(gid, uid) -> str:
    """
    查找用户在群主的角色   群主/管理/成员
    
    参数：

    gid: 群号

    uid: 用户号

    返回值：

    role: 用户角色，可能的值为：owner, admin, member
    """

    bot = nonebot.get_bot()

    result = await bot.get_group_member_info(group_id=gid, user_id=uid)
    logger.info(f"查找用户角色成功，群号：{gid}，用户号：{uid}，角色：{result['role']}")
    return result['role']

async def 设置群头衔(gid, uid, title):
    '''
    设置群头衔
    
    参数：

    gid: 群号

    uid: 用户号

    title: 群头衔

    '''

    bot = nonebot.get_bot()

    await bot.set_group_special_title(group_id=gid, user_id=uid, special_title=title)
    logger.info(f"设置群头衔成功，群号：{gid}，用户号：{uid}，群头衔：{title}")



async def 警告用户(gid, uid):
    '''
    对故意恶意操作的用户进行警告
        
    参数：

    gid: 群号

    uid: 用户号

    '''


async def 警示语录():
    '''
    用于错误操作的警示语录
    ？闲的
    '''


async def AI语音(gid, character, text):
    """
    发送ai语音
    """


    bot = nonebot.get_bot()

    await bot.send_group_ai_record(group_id=gid, character=character, text=text)
    logger.info(f"发送ai语音成功，群号：{gid}，ai编号：{character}，文本：{text}")



async def 连坐链子(gid, uid, iuid):
    '''
    邀请进群的连坐机制
    分群处理
    用类似
    用户1-> 用户2
    用户2-> 用户3
    用户3-> 用户4
    的链子表示
    用户1邀请用户2
    用户2邀请用户3
    细则：
    当链子中存在管理时，链子到此为止，不在迭代判断
    保存每个用户的信息，json即可，考虑到后续人数较多，需要注意性能问题
    应该包括：（如果预留漏洞 可以用序列化存储数据，保存信息添加一个可控的字段，如保留QQ昵称？
        （内容不可控）
        邀请人
        邀请时间
        群角色（是不是管理，但是在管理变更时需要更新）

    '''

    '''
    参数：

    gid: 群号

    uid: 用户号

    iuid : 被邀请人
    
    '''

    '''
    json格式

        {
      "群号1": {
        "用户A_ID": {
          "inviter": null, // 初始成员或未知
          "invite_time": "2024-01-01T10:00:00Z" // ISO 8601 格式时间戳
          "role": "owner" // 群主
        },
        "用户B_ID": {
          "inviter": "用户A_ID", // 用户B由用户A邀请
          "invite_time": "2025-04-17T10:30:00Z"
        },
        "用户C_ID": {
          "inviter": "用户B_ID", // 用户C由用户B邀请
          "invite_time": "2025-04-17T11:00:00Z"
        },
        "管理员D_ID": {
          "inviter": "用户A_ID", // 管理员D由用户A邀请
          "invite_time": "2025-04-17T12:00:00Z"
        },
        "用户E_ID": {
          "inviter": "管理员D_ID", // 用户E由管理员D邀请 (如果规则允许，或者需要记录)
          "invite_time": "2025-04-17T13:00:00Z"
        }
      },
      "群号2": {
        "用户X_ID": {
          "inviter": null,
          "invite_time": "2024-02-15T09:00:00Z"
        },
        "用户Y_ID": {
          "inviter": "用户X_ID",
          "invite_time": "2025-04-16T15:00:00Z"
        }
      }
      // ... 其他群聊
    }
    '''

    import json
    import os
    import datetime
    from nonebot import logger
    
    # 数据文件路径
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    invite_chain_file = os.path.join(data_dir, "invite_chain.json")
    
    # 确保数据目录存在
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 读取现有的邀请链数据
    invite_data = {}
    if os.path.exists(invite_chain_file):
        try:
            with open(invite_chain_file, 'r', encoding='utf-8') as f:
                invite_data = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"读取邀请链文件失败，文件可能损坏: {invite_chain_file}")
        except Exception as e:
            logger.error(f"读取邀请链文件时出错: {e}")
    
    # 确保群号存在于数据中
    gid_str = str(gid)
    if gid_str not in invite_data:
        invite_data[gid_str] = {}
    
    # 获取被邀请人的角色
    iuid_str = str(iuid)
    uid_str = str(uid)
    
    try:
        # 获取被邀请人的角色
        iuid_role = await 查找用户角色(gid, iuid)
        
        # 如果邀请人不在数据中，且不是被邀请人自己添加自己，则添加邀请人信息
        if uid_str != iuid_str and uid_str not in invite_data[gid_str]:
            # 获取邀请人的角色
            uid_role = await 查找用户角色(gid, uid)
            invite_data[gid_str][uid_str] = {
                "inviter": None,  # 邀请人未知或为初始成员
                "invite_time": datetime.datetime.now().isoformat(),
                "role": uid_role
            }
        
        # 添加被邀请人信息
        invite_data[gid_str][iuid_str] = {
            "inviter": uid_str,
            "invite_time": datetime.datetime.now().isoformat(),
            "role": iuid_role
        }
        
        # 持久化到文件
        try:
            with open(invite_chain_file, 'w', encoding='utf-8') as f:
                json.dump(invite_data, f, ensure_ascii=False, indent=2)
            logger.info(f"邀请链数据已更新: 群 {gid}, 邀请人 {uid}, 被邀请人 {iuid}")
        except Exception as e:
            logger.error(f"保存邀请链数据失败: {e}")
            
    except Exception as e:
        logger.error(f"构建邀请链时出错: {e}")

async def 获取连坐链子(gid, uid):
    '''
    获取用户的邀请链，直到找到群主或管理员为止
    
    参数：
    gid: 群号
    uid: 用户号
    
    返回值：
    邀请链数组，包含从用户到第一个管理员/群主的所有邀请人的uid
    例如: [用户A, 用户B, 管理员C] 表示 用户A被用户B邀请，用户B被管理员C邀请
    数组的第一个元素是传入的uid，最后一个元素是链条中的管理员/群主(如果存在)
    如果没有找到邀请链或者用户是初始成员，返回只包含该用户的数组
    '''
    import json
    import os
    from nonebot import logger
    
    # 数据文件路径
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    invite_chain_file = os.path.join(data_dir, "invite_chain.json")
    
    # 验证数据文件是否存在
    if not os.path.exists(invite_chain_file):
        logger.warning(f"邀请链数据文件不存在: {invite_chain_file}")
        return [str(uid)]  # 如果文件不存在，返回只包含当前用户的数组
    
    # 读取邀请链数据
    try:
        with open(invite_chain_file, 'r', encoding='utf-8') as f:
            invite_data = json.load(f)
    except Exception as e:
        logger.error(f"读取邀请链数据失败: {e}")
        return [str(uid)]  # 如果读取失败，返回只包含当前用户的数组
    
    # 检查群组是否在数据中
    gid_str = str(gid)
    if gid_str not in invite_data:
        logger.info(f"群 {gid} 没有邀请链数据")
        return [str(uid)]  # 如果群不在数据中，返回只包含当前用户的数组
    
    # 获取群组数据
    group_data = invite_data[gid_str]
    
    # 初始化邀请链数组，第一个元素是传入的用户ID
    invite_chain = [str(uid)]
    current_uid = str(uid)
    
    # 循环查找邀请链，直到找到群主/管理员或者链条结束
    while current_uid in group_data:
        # 获取当前用户的数据
        user_data = group_data[current_uid]
        
        # 检查是否有邀请人
        if user_data.get('inviter') is None:
            # 用户是初始成员或无邀请人记录
            break
        
        # 获取邀请人ID
        inviter_id = user_data['inviter']
        
        # 检查邀请人是否在群数据中
        if inviter_id not in group_data:
            # 邀请人数据不存在，可能是已退群或数据不完整
            logger.warning(f"邀请人 {inviter_id} 在群 {gid} 中没有数据记录")
            break
        
        # 将邀请人添加到链条中
        invite_chain.append(inviter_id)
        
        # 检查邀请人角色
        inviter_role = group_data[inviter_id].get('role')
        if inviter_role in ['owner', 'admin']:
            # 如果邀请人是群主或管理员，停止查找
            logger.info(f"在邀请链中找到管理员/群主 {inviter_id}，角色: {inviter_role}")
            break
        
        # 更新当前用户为邀请人，继续查找
        current_uid = inviter_id
    
    return invite_chain
