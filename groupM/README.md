# GroupM - 群组与好友管理插件

[![NoneBot2](https://img.shields.io/badge/NoneBot2-2.0.0+-green.svg)](https://v2.nonebot.dev/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![OneBot V11](https://img.shields.io/badge/OneBot-v11-black)](https://onebot.dev/)

基于 NoneBot2 和 OneBot V11 协议的群组与好友管理插件，提供入群申请、群聊邀请和好友申请的人工审核系统。

## 功能特点

- 🔐 入群申请审核系统
- 🌐 群聊邀请审核系统
- 👥 好友申请审核系统
- 📨 自动转发审核信息至指定审核群
- 📝 支持回复消息快速处理申请
- 📋 支持通过命令手动处理申请
- 💾 持久化存储待处理申请数据
- 📊 合并转发方式查看申请列表

## 安装方法

### 方法一: 使用 nb-cli 安装（推荐）

```bash
# 使用 nb-cli 安装插件
nb plugin install nonebot-plugin-groupm
```

### 方法二: 直接克隆到本地（手动安装）

1. 将本插件克隆到你的 NoneBot2 项目的 plugins 目录下
   ```bash
   cd your-bot/src/plugins
   git clone https://github.com/yourusername/nonebot-plugin-groupm.git groupM
   ```

2. 安装依赖（本插件依赖于 NoneBot2 和 nonebot-adapter-onebot）
   ```bash
   pip install nonebot2 nonebot-adapter-onebot
   ```

3. 在项目的 `pyproject.toml` 中添加插件
   ```toml
   [tool.nonebot]
   plugins = ["groupM"]
   ```

## 配置说明

在 NoneBot2 全局配置文件 `.env` 或 `.env.prod` 中添加以下配置项：

```
# 审核群组ID，管理员在这个群中审核入群和好友申请
AUDIT_GROUP_ID=629590326
```

说明：
- `AUDIT_GROUP_ID`：必填，指定处理审核消息的群聊ID，所有入群申请、群聊邀请和好友申请将会被转发到这个群进行处理
- 好友申请只能由超级管理员（SUPERUSER）处理
- 入群申请和群聊邀请可以由群主、管理员或超级管理员处理

## 使用方法

### 审核流程

1. 当机器人收到入群申请、被邀请进群或好友申请时，会自动将申请信息转发到指定的审核群
2. 管理员可以通过以下两种方式之一处理申请：
   - 回复审核消息并发送「同意」或「拒绝 [拒绝理由]」
   - 直接在审核群发送命令「/同意 [请求标识]」或「/拒绝 [请求标识] [拒绝理由]」
3. 对于好友申请，只有超级管理员才能处理
4. 处理完成后，相关请求信息会自动从持久化存储中删除
5. 机器人被邀请进群的请求会有特定的审核提示，与普通入群申请区分显示

### 命令列表

| 命令 | 权限 | 说明 |
|------|------|------|
| `查看入群审核` | 群管理员、群主、超管 | 显示所有待处理的入群申请和群聊邀请 |
| `查看好友审核` | 超级管理员 | 显示所有待处理的好友申请 |
| `查看所有审核` | 群管理员、群主、超管 | 以合并转发方式显示所有待处理申请 |
| `/同意 [请求标识]` | 群管理员、群主、超管* | 手动同意指定请求 |
| `/拒绝 [请求标识] [理由]` | 群管理员、群主、超管* | 手动拒绝指定请求，理由可选 |

注：*好友申请只能由超级管理员处理

### 使用示例

#### 查看待审核的入群申请和群聊邀请
```
查看入群审核
```

#### 查看待审核的好友申请
```
查看好友审核
```

#### 查看所有待处理的申请（合并转发方式）
```
查看所有审核
```

#### 手动同意指定请求
```
/同意 1a2b3c4d5e6f
```

#### 手动拒绝指定请求
```
/拒绝 1a2b3c4d5e6f 请先通过群主验证
```

## 数据结构

所有待处理的请求数据保存在插件目录下的 `data` 文件夹中：

- `pending_requests.json`: 存储入群请求和群聊邀请，通过sub_type字段区分
- `pending_friend_requests.json`: 存储好友请求
- `message_to_flag.json`: 存储消息ID到请求标识的映射
- `flag_type.json`: 存储请求标识对应的类型（group_add、group_invite、friend）

## 开发者信息

- 作者: dog
- 版本: v1.2.0
- 反馈: 如有问题或建议，请在 GitHub 上提交 issue

## 更新日志

### v1.2.0
- 添加群聊邀请审核功能
- 优化审核消息显示，区分不同请求类型
- 增强错误处理和未知请求类型处理
- 修复多种请求类型并存时的显示问题

### v1.1.0
- 添加好友申请审核功能
- 添加持久化存储功能
- 优化合并转发显示
- 修复命令处理冲突问题

### v1.0.0 
- 实现基础入群申请审核功能
- 支持回复消息处理申请