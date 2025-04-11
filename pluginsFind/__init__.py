import nonebot
from nonebot.log import logger
from nonebot.plugin import Plugin, PluginMetadata
from nonebot.adapters.onebot.v11 import MessageEvent, Message, MessageSegment
from nonebot import on_command
from nonebot.params import CommandArg
from typing import Dict, List, Optional, Tuple, Set
import os
from pathlib import Path
from nonebot.permission import SUPERUSER

'''
完成"获取插件的帮助信息"的计划
其实是获取__plugin_meta__

但是通过插件名字获取信息很不人性化，如下：
    例如本插件所在的位置是 src/plugins/pluginsFind/，所以通过名字获取本插件信息的方式是
    plugin = nonebot.get_plugin("pluginsFind")
    我们把pluginsFind称为plugin_name,为了下面好区分

计划通过__plugin_meta__中的name属性来获取插件信息
1. 先建立name和plugin_name的映射关系
    可以通过plugin_name = nonebot.get_available_plugin_names()获取
    返回数据是{'nonebot_plugin_apscheduler', 'echo', 'nonebot_plugin_localstore', 'group', 'CTF', 'FileAi', 'Whois', 'pluginsFind', 'helpmain'}
2. 当用户输入插件名称时
    先通过name找到plugin_name
    然后再通过plugin_name获取插件信息
3. 把获取到的插件信息发送给用户
    获取插件信息的方式是
    plugin = nonebot.get_plugin(str(plugin_name))
    获取的数据格式是：Plugin(name='CTF', module=<module 'src.plugins.CTF' from '/Users/cgz/Project/QQBOT/nonebot/cg/src/plugins/CTF/__init__.py'>, module_name='src.plugins.CTF', manager=PluginManager(available_plugins={'nonebot_plugin_localstore': 'nonebot_plugin_localstore', 'nonebot_plugin_apscheduler': 'nonebot_plugin_apscheduler', 'CTF': 'src.plugins.CTF', 'FileAi': 'src.plugins.FileAi', 'Whois': 'src.plugins.Whois', 'group': 'src.plugins.group', 'helpmain': 'src.plugins.helpmain', 'pluginsFind': 'src.plugins.pluginsFind'}), matcher={Matcher(type='message', module=src.plugins.CTF, lineno=284)}, parent_plugin=None, sub_plugins=set(), metadata=PluginMetadata(name='CTF比赛推送', description='自动推送即将开始的CTF比赛信息，支持国内和国际CTF赛事', usage='\n    定时推送: \n    - 自动推送即将开始的国内和国际CTF赛事到指定QQ群\n    \n    手动查询: \n    - /查询赛事 [权重]: 查询国内和国际CTF赛事信息，国际赛事权重默认为50\n    ', type='application', homepage=None, config=<class 'src.plugins.CTF.config.Config'>, supported_adapters={'~onebot.v11'}, extra={'author': 'dog', 'version': '1.0.0'}))
    如果插件没有__plugin_meta__，则返回：Plugin(name='FileAi', module=<module 'src.plugins.FileAi' from '/Users/cgz/Project/QQBOT/nonebot/cg/src/plugins/FileAi/__init__.py'>, module_name='src.plugins.FileAi', manager=PluginManager(available_plugins={'nonebot_plugin_localstore': 'nonebot_plugin_localstore', 'nonebot_plugin_apscheduler': 'nonebot_plugin_apscheduler', 'CTF': 'src.plugins.CTF', 'FileAi': 'src.plugins.FileAi', 'Whois': 'src.plugins.Whois', 'group': 'src.plugins.group', 'helpmain': 'src.plugins.helpmain', 'pluginsFind': 'src.plugins.pluginsFind'}), matcher={Matcher(type='message', module=src.plugins.FileAi, lineno=366)}, parent_plugin=None, sub_plugins=set(), metadata=None)
    
    其实要获取的信息是metadata，可以看到如果没有__plugin_meta__，则metadata为None
    如果为none的话，就不把这个插件的信息返回给用户
    这有个插件信息的格式问题，为了简洁只推送这几个即可
    1. 插件名称 （其实是metadata中的name，其余类似）
    2. 插件用法
    3. 插件描述

4.使用方法
    1.先使用/插件信息 获取插件列表树
        1. 其中只包括有__plugin_meta__的插件，如果不存在不加入到列表中
        2. 获取到的信息里只包括插件的名称和插件的描述
        
    2. 用户输入插件名称 即使用 /插件信息 插件名称
        1. 例如 /插件信息 CTF
        2. 返回插件的详细信息
        3. 如果插件不在列表中则返回插件不存在
'''

# 添加插件元数据
__plugin_meta__ = PluginMetadata(
    name="插件查询",
    description="查询已安装的所有插件及其使用方法",
    usage="""
    查询插件列表:
    - /插件信息: 获取所有带元数据的插件列表
    
    查询具体插件:
    - /插件信息 <插件名称>: 查询指定插件的详细信息
    
    超级用户命令:
    - /屏蔽插件 <插件名称>: 将插件从列表中隐藏
    - /取消屏蔽 <插件名称>: 将插件恢复显示
    """,
    type="application",
    homepage="https://github.com/CG-Jue/NoneBotPlugins",
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "dog",
        "version": "1.0.0",
    },
)

# 保存屏蔽插件列表的文件路径
HIDDEN_PLUGINS_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "hidden_plugins.txt"

# 命令注册
findplugins = on_command("/插件信息", priority=1, block=True)
hide_plugin = on_command("/屏蔽插件", permission=SUPERUSER, priority=1, block=True)
show_plugin = on_command("/取消屏蔽", permission=SUPERUSER, priority=1, block=True)

def get_hidden_plugins() -> Set[str]:
    """
    获取屏蔽的插件列表
    :return: 屏蔽插件名称集合
    """
    hidden_plugins = set()
    if HIDDEN_PLUGINS_FILE.exists():
        try:
            with open(HIDDEN_PLUGINS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    plugin = line.strip()
                    if plugin:
                        hidden_plugins.add(plugin)
        except Exception as e:
            logger.error(f"读取屏蔽插件列表失败: {e}")
    return hidden_plugins

def save_hidden_plugins(hidden_plugins: Set[str]) -> bool:
    """
    保存屏蔽的插件列表
    :param hidden_plugins: 屏蔽插件名称集合
    :return: 是否保存成功
    """
    try:
        with open(HIDDEN_PLUGINS_FILE, "w", encoding="utf-8") as f:
            for plugin in hidden_plugins:
                f.write(f"{plugin}\n")
        return True
    except Exception as e:
        logger.error(f"保存屏蔽插件列表失败: {e}")
        return False

def build_plugin_mapping() -> Dict[str, str]:
    """
    建立插件显示名称和插件ID的映射关系
    :return: 名称到插件ID的映射字典
    """
    mapping = {}
    plugin_ids = nonebot.get_available_plugin_names()
    
    for plugin_id in plugin_ids:
        plugin = nonebot.get_plugin(str(plugin_id))
        if plugin and plugin.metadata:
            # 如果插件有元数据，则使用元数据中的name作为显示名称
            mapping[plugin.metadata.name] = plugin_id
            
    return mapping

def get_plugin_list() -> List[Dict[str, str]]:
    """
    获取所有带元数据的插件列表（排除被屏蔽的插件）
    :return: 插件列表，每个元素包含名称和描述
    """
    plugin_list = []
    plugin_ids = nonebot.get_available_plugin_names()
    hidden_plugins = get_hidden_plugins()
    
    for plugin_id in plugin_ids:
        plugin = nonebot.get_plugin(str(plugin_id))
        if plugin and plugin.metadata:
            # 排除被屏蔽的插件
            if plugin.metadata.name not in hidden_plugins:
                plugin_list.append({
                    "name": plugin.metadata.name,
                    "description": plugin.metadata.description
                })
            
    return plugin_list

def get_all_plugin_list() -> List[Dict[str, str]]:
    """
    获取所有带元数据的插件列表（包括被屏蔽的插件）
    :return: 完整插件列表，每个元素包含名称、描述和屏蔽状态
    """
    plugin_list = []
    plugin_ids = nonebot.get_available_plugin_names()
    hidden_plugins = get_hidden_plugins()
    
    for plugin_id in plugin_ids:
        plugin = nonebot.get_plugin(str(plugin_id))
        if plugin and plugin.metadata:
            is_hidden = plugin.metadata.name in hidden_plugins
            plugin_list.append({
                "name": plugin.metadata.name,
                "description": plugin.metadata.description,
                "is_hidden": is_hidden
            })
            
    return plugin_list

def get_plugin_detail(plugin_name: str) -> Optional[Dict[str, str]]:
    """
    获取指定插件的详细信息，只能通过元数据中的name字段精确匹配
    :param plugin_name: 插件名称（必须是元数据中的name）
    :return: 插件详细信息，如果未找到插件则返回None
    """
    mapping = build_plugin_mapping()
    
    # 只通过name精确匹配，不再尝试通过插件ID或模糊匹配查询
    if plugin_name in mapping:
        plugin_id = mapping[plugin_name]
        plugin = nonebot.get_plugin(plugin_id)
        
        if plugin and plugin.metadata:
            return {
                "name": plugin.metadata.name,
                "description": plugin.metadata.description,
                "usage": plugin.metadata.usage,
                "type": plugin.metadata.type,
                "extra": plugin.metadata.extra if plugin.metadata.extra else {}
            }
    
    return None

def format_plugin_list(plugin_list: List[Dict[str, str]]) -> str:
    """
    格式化插件列表为简洁易读的字符串
    :param plugin_list: 插件列表
    :return: 格式化后的字符串
    """
    if not plugin_list:
        return "暂无可用插件信息"
    
    result = f"已安装的插件列表 | 共{len(plugin_list)} 个\n\n"
    for i, plugin in enumerate(plugin_list, start=1):
        # result += f"{i}. {plugin['name']} - {plugin['description']}\n"
        result += f"{i}. {plugin['name']}\n"
    
    result += "\n详细用法➡️「/插件信息 插件名」"
    
    return result

def format_all_plugin_list(plugin_list: List[Dict[str, str]]) -> str:
    """
    格式化所有插件列表，包括被屏蔽的插件，专供超级用户使用
    :param plugin_list: 插件列表
    :return: 格式化后的字符串
    """
    if not plugin_list:
        return "暂无可用插件信息"
    
    visible_count = sum(1 for plugin in plugin_list if not plugin['is_hidden'])
    hidden_count = len(plugin_list) - visible_count
    
    result = f"已安装的插件列表 (总计 {len(plugin_list)} 个，其中 {visible_count} 个可见，{hidden_count} 个已屏蔽)：\n\n"
    
    for i, plugin in enumerate(plugin_list, start=1):
        status = "🔒" if plugin['is_hidden'] else "✅" 
        result += f"{i}. {status} {plugin['name']} - {plugin['description']}\n"
    
    result += f"\n详细用法➡️「/插件信息 插件名」"
    
    return result

def format_plugin_detail(plugin_info: Dict[str, str]) -> str:
    """
    格式化插件详情为简洁易读的字符串
    :param plugin_info: 插件详情
    :return: 格式化后的字符串
    """
    result = f"【{plugin_info['name']}】\n"
    result += f"{plugin_info['description']}\n\n"
    result += f"使用方法:\n{plugin_info['usage']}"
    
    return result

@findplugins.handle()
async def handle_findplugins(event: MessageEvent, args: Message = CommandArg()):
    """
    处理插件信息请求
    :param event: 消息事件
    :param args: 命令参数
    """
    # 获取用户输入的插件名称
    plugin_name = args.extract_plain_text().strip()
    logger.debug(f"查询插件名称: {plugin_name}")
    
    # 判断是否为超级用户
    is_superuser = str(event.user_id) in nonebot.get_driver().config.superusers
    hidden_plugins = get_hidden_plugins()
    
    # 如果没有输入插件名称，则返回插件列表
    if not plugin_name:
        if is_superuser:
            # 超级用户可以看到所有插件，包括被屏蔽的
            all_plugins = get_all_plugin_list()
            result = format_all_plugin_list(all_plugins)
        else:
            # 普通用户只能看到未被屏蔽的插件
            plugin_list = get_plugin_list()
            result = format_plugin_list(plugin_list)
        await findplugins.finish(result)
    
    # 根据输入的插件名查找插件详情
    plugin_info = get_plugin_detail(plugin_name)
    
    # 如果找到了插件信息
    if plugin_info:
        # 检查插件是否被屏蔽
        if plugin_info["name"] in hidden_plugins:
            # 对于非超级用户，被屏蔽的插件不可见
            if not is_superuser:
                await findplugins.finish(f"未找到插件「{plugin_name}」的信息，请检查输入是否正确")
            else:
                # 超级用户可以看到被屏蔽的插件信息
                result = format_plugin_detail(plugin_info)
                result += "\n\n[⚠️] 此插件已被屏蔽，普通用户无法查看"
                await findplugins.finish(result)
        else:
            # 未屏蔽的插件，所有用户都可以查看
            result = format_plugin_detail(plugin_info)
            await findplugins.finish(result)
    else:
        # 插件不存在或没有元数据
        await findplugins.finish(f"未找到插件「{plugin_name}」的信息，请检查输入是否正确")

@hide_plugin.handle()
async def handle_hide_plugin(event: MessageEvent, args: Message = CommandArg()):
    """
    处理屏蔽插件请求
    :param event: 消息事件
    :param args: 命令参数
    """
    plugin_name = args.extract_plain_text().strip()
    if not plugin_name:
        await hide_plugin.finish("请指定要屏蔽的插件名称")
    
    # 验证插件是否存在
    plugin_info = get_plugin_detail(plugin_name)
    if not plugin_info:
        await hide_plugin.finish(f"未找到插件「{plugin_name}」，请检查输入是否正确")
    
    # 插件存在，将其添加到屏蔽列表
    hidden_plugins = get_hidden_plugins()
    real_name = plugin_info["name"]
    
    if real_name in hidden_plugins:
        await hide_plugin.finish(f"插件「{real_name}」已经在屏蔽列表中")
    
    hidden_plugins.add(real_name)
    if save_hidden_plugins(hidden_plugins):
        await hide_plugin.finish(f"已成功屏蔽插件「{real_name}」")
    else:
        await hide_plugin.finish(f"屏蔽插件「{real_name}」失败，请检查日志")

@show_plugin.handle()
async def handle_show_plugin(event: MessageEvent, args: Message = CommandArg()):
    """
    处理取消屏蔽插件请求
    :param event: 消息事件
    :param args: 命令参数
    """
    plugin_name = args.extract_plain_text().strip()
    if not plugin_name:
        await show_plugin.finish("请指定要取消屏蔽的插件名称")
    
    # 获取所有插件，包括被屏蔽的
    hidden_plugins = get_hidden_plugins()
    
    # 尝试查找插件（即使被屏蔽了）
    plugin_info = get_plugin_detail(plugin_name)
    real_name = plugin_name  # 默认使用输入名称
    
    if plugin_info:
        real_name = plugin_info["name"]
    
    # 如果插件名在屏蔽列表中，移除它
    if real_name in hidden_plugins:
        hidden_plugins.remove(real_name)
        if save_hidden_plugins(hidden_plugins):
            await show_plugin.finish(f"已成功取消屏蔽插件「{real_name}」")
        else:
            await show_plugin.finish(f"取消屏蔽插件「{real_name}」失败，请检查日志")
    else:
        await show_plugin.finish(f"插件「{real_name}」不在屏蔽列表中")

