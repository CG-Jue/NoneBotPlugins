import os
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent
from pathlib import Path

# 存储启用群号的文件路径
ABLED_GROUPS_FILE = Path(__file__).parent / "abled_groups.txt"

# 确保文件存在
if not ABLED_GROUPS_FILE.exists():
    with open(ABLED_GROUPS_FILE, "w") as f:
        pass

def get_abled_groups() -> set:
    """获取启用Whois的群组ID列表"""
    if not ABLED_GROUPS_FILE.exists():
        return set()
        
    with open(ABLED_GROUPS_FILE, "r") as f:
        groups = set()
        for line in f.readlines():
            line = line.strip()
            if line and line.isdigit():
                groups.add(int(line))
        return groups

def add_abled_group(group_id: int) -> bool:
    """添加一个群到启用列表"""
    abled_groups = get_abled_groups()
    
    # 如果已经在列表中，不需要添加
    if group_id in abled_groups:
        return False
    
    abled_groups.add(group_id)
    
    with open(ABLED_GROUPS_FILE, "w") as f:
        for gid in abled_groups:
            f.write(f"{gid}\n")
    
    return True

def remove_abled_group(group_id: int) -> bool:
    """从启用列表中移除一个群"""
    abled_groups = get_abled_groups()
    
    # 如果不在列表中，不需要移除
    if group_id not in abled_groups:
        return False
    
    abled_groups.remove(group_id)
    
    with open(ABLED_GROUPS_FILE, "w") as f:
        for gid in abled_groups:
            f.write(f"{gid}\n")
    
    return True

async def is_group_allowed(event: Event) -> bool:
    """检查群组是否允许使用Whois功能"""
    # 私聊消息总是允许
    if not isinstance(event, GroupMessageEvent):
        return True
    
    # 检查群号是否在启用列表中
    group_id = event.group_id
    abled_groups = get_abled_groups()
    
    # 返回True表示允许，False表示禁用
    return group_id in abled_groups
