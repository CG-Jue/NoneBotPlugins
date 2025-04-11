# Whois 查询插件

适用于 Nonebot2 的 Whois 域名信息查询插件，支持多种查询方式和群组权限控制。

## 功能特点

- 通过命令查询域名的 Whois 信息
- 自动识别常见域名格式，直接查询
- 支持查询详细 Whois 原始信息
- 智能过滤不常见域名，避免误触发
- 群组禁用功能，超级用户可控制插件启用状态
- 美观易读的结构化输出格式
- 支持查询域名的创建/到期/更新时间、注册商、DNS和所有者信息


## 使用方法

### 基本命令

1. **通过命令查询**
   ```
   /whois example.com
   ```

2. **查看原始 Whois 信息**
   ```
   /whois example.com -all
   ```

3. **直接发送域名**
   
   直接在群聊中发送域名文本 (如 `example.com`)，机器人会自动识别并查询

### 管理命令

> ⚠️ 注意：以下命令仅限超级用户使用

1. **禁用群组的 Whois 查询功能**
   ```
   /禁止whois
   ```

2. **启用群组的 Whois 查询功能**
   ```
   /允许whois
   ```

## 查询结果示例

```
🔍 whois 查询结果 [ example.com ]
──────────────────────────────
🗓 注册信息：
├ 注册机构：某注册商
├ 创建时间：2023-01-01
├ 到期时间：2024-01-01
└ 更新时间：2023-06-01

📊 域名状态：
• clientTransferProhibited
• serverDeleteProhibited

🌐 DNS 服务器：
• ns1.example.net
• ns2.example.net

👤 持有人信息：
├ 姓名：域名持有者
├ 机构：某公司
├ 邮箱：contact@example.com
└ 电话：+1.1234567890
──────────────────────────────
```

## 权限控制说明

- 插件支持群组级别的启用/禁用控制
- 禁用的群组中，所有 Whois 查询功能都将被关闭
- 群组禁用状态会被记录在插件目录下的 `disabled_groups.txt` 文件中
- 只有超级用户可以修改群组的禁用状态

## 配置说明

插件无需额外配置即可使用。所有群组默认启用 Whois 查询功能，直到被超级用户禁用。

## 工作原理

1. **域名识别机制**
   - 通过预设的顶级域名列表筛选有效域名
   - 支持常见通用顶级域名和国家地区顶级域名
   - 同时支持多级域名格式 (如 co.uk, com.cn 等)

2. **Whois 查询**
   - 调用 whois.4.cn 的公开 API 获取域名信息
   - 格式化信息为美观易读的输出格式

3. **权限控制**
   - 使用文本文件存储禁用群组列表，无需数据库支持
   - 使用 Nonebot2 的 Rule 系统实现权限检查

## 支持的顶级域名

本插件支持以下常见顶级域名的自动识别：

### 通用顶级域名
com, org, net, edu, gov, mil, int, info, biz, name,
pro, museum, aero, coop, jobs, travel, mobi, asia, tel,
xxx, app, blog, dev, online, site, store, tech, xyz

### 国家和地区顶级域名
cn, us, uk, jp, fr, de, ru, au, ca, br, in, 
it, nl, es, se, no, fi, dk, ch, at, be, hk, 
tw, sg, kr, nz, mx, ar, co, eu, io, me, tv

### 多级顶级域名
co.uk, co.jp, com.cn, org.cn, net.cn, gov.cn, ac.cn,
com.hk, com.tw, co.nz, co.kr, or.jp, ac.jp, ne.jp

## 常见问题

**Q: 为什么有些域名无法识别？**
A: 插件只识别常见顶级域名，以避免误触发。如果需要查询不常见域名，请使用命令 `/whois 域名` 的方式查询。

**Q: Whois 信息查询失败怎么办？**
A: 可能是 API 暂时无法访问或域名不存在，请稍后再试。

**Q: 如何添加更多顶级域名支持？**
A: 可在代码中的 `COMMON_TLDS` 集合中添加更多顶级域名。

**Q: 为什么某些域名的持有人信息显示"暂无信息"？**
A: 某些域名可能启用了隐私保护服务，或注册局不公开此类信息。

## 版本信息

- **版本**: 1.0.0
- **作者**: dog
- **主页**: https://github.com/CG-Jue/NoneBotPlugins

## 许可证

MIT License