# FileAi - QQ文件解读插件

这个NoneBot2插件可以使用Kimi API解析QQ中的文件内容，并提供文件内容的总结和分析。

## 功能

- 回复包含文件的消息，同时@机器人并加上"解读"关键词，即可触发文件解析
- 支持多种文件格式，包括文本文件、文档、代码文件等
- 提取文件的关键信息和主要内容
- 显示处理用时、使用的模型信息
- 显示消耗的 Token 数量以及当前 API 余额
- 自动检测不支持的文件格式并提示用户

## 支持的文件格式

### 文档类
- PDF文件 (`.pdf`)
- 文本文档 (`.txt`)
- Excel表格 (`.csv`, `.xls`, `.xlsx`)
- Word文档 (`.doc`, `.docx`)
- PowerPoint演示文稿 (`.ppt`, `.pptx`)
- Markdown文档 (`.md`)
- 电子书 (`.epub`, `.mobi`)
- 网页文件 (`.html`)
- JSON数据 (`.json`)

### 日志和配置文件
- 日志文件 (`.log`)
- 配置文件 (`.yaml`, `.yml`, `.ini`, `.conf`)

### 代码类
- 常见编程语言文件 (`.go`, `.h`, `.c`, `.cpp`, `.cxx`, `.cc`, `.cs`, `.java`, `.js`, `.ts`, `.tsx`, `.php`, `.py`, `.py3`, `.asp`)
- 网页相关文件 (`.css`, `.jsp`)

## 安装和配置

1. 确保插件已放入正确的插件目录中

2. 在配置文件 `src/plugins/FileAi/config.py` 中设置以下参数：
   ```python
   class Config(BaseModel):
       CONFIG: dict = {
           "kimi_api_key": "你的Kimi API密钥",  # 从 Moonshot 平台获取
           "kimi_api_base_url": "https://api.moonshot.cn/v1",  # API 基础 URL
           "kimi_model": "moonshot-v1-32k",     # 使用的模型名称
       }
   ```

## 使用方法

1. 有人在群聊中发送文件
2. 回复该文件消息，并在回复中@机器人，同时包含"解读"关键词和额外的解读指令
3. 机器人会下载该文件，使用Kimi API分析内容，然后发送分析结果

例如：
```
@机器人 解读 帮我总结一下这个文档的主要内容
@机器人 解读 提取这个文件中的关键信息
```

## 输出示例

解析完成后，机器人将返回如下格式的内容：

```
文件「example.pdf」的解读结果：

[解析内容...]

---
处理用时: 10秒
使用模型: moonshot-v1-32k
消耗Token: 1234
可用余额: 49.59
```

## 注意事项

- 需要机器人具有接收和下载文件的权限
- 大文件可能需要较长的处理时间
- 由于Kimi API的限制，不支持图片文件格式
- 使用前需要从Moonshot开放平台申请API密钥
- 每次解析都会消耗 Token，请关注余额情况
- 当前仅支持群聊文件解析