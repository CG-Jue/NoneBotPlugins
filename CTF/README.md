# CTF比赛推送插件
> 虽然已经有官网机器人了，但是需要手动去获取比赛信息，Ctfer还是太懒了？ 本文档由AI生成

一个基于NoneBot2的QQ机器人插件，用于自动推送即将开始报名的CTF比赛信息到指定QQ群。

## 功能特点

- 自动获取最新的CTF赛事信息
- 定时检查并推送即将开始报名的比赛
- 可配置推送时间和推送群组
- 防止重复推送同一比赛

## 数据来源

比赛数据来自：[Hello-CTFtime](https://raw.githubusercontent.com/ProbiusOfficial/Hello-CTFtime/main/CN.json)

## 安装方法

### 环境要求

- Python 3.7+
- NoneBot2
- nonebot-plugin-apscheduler 插件

### 安装步骤

1. 在你的NoneBot2项目中安装该插件：

```bash
# 在nonebot项目目录下执行
pip install nonebot-plugin-apscheduler
```

2. 将插件文件夹 `CTF` 复制到你的 NoneBot2 项目的 plugins 目录下

3. 在 .env 文件中启用该插件：

```
PLUGIN_DIRS=["src/plugins"]
```

## 配置说明

在 config.py 中可以配置以下参数：

- `SEND_LIST`: 推送目标群号列表，例如 `[936493920, 391680981]`
- `SEND_TIME`: 推送时间设置，表示提前多少天推送比赛信息，默认为1天

示例配置：

```python
class Config(BaseModel):
    CONFIG: dict = {
        "SEND_LIST": [], # 推送的群号列表
        "SEND_TIME": 1,  # 推送时间差值，即距离报名开始多少天推送
    }
```

## 使用说明

安装并配置好插件后，机器人将自动执行以下操作：

1. 每30分钟检查一次是否有即将开始报名的CTF比赛
2. 如果发现比赛将在配置的时间内开始报名（默认1天内），且未推送过，则向指定的群组发送比赛信息

推送的比赛信息包括：
- 比赛名称
- 报名时间
- 比赛时间
- 比赛链接

## 文件结构

```
CTF/
├── __init__.py  # 主要功能实现
├── config.py    # 插件配置
└── db.txt       # 已推送比赛记录（自动生成）
```

## 贡献指南

如果你想为这个项目做出贡献，欢迎提交 Pull Request 或 Issue。

## 许可证

本项目采用 MIT 许可证。