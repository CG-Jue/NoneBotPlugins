# FileAi - QQ文件解读与图片分析插件

这个NoneBot2插件可以使用Kimi API解析QQ中的文件内容和图片，并提供内容的总结和分析。

## 功能

- 回复包含文件的消息，使用`#分析文件`命令触发文件解析
- 回复包含图片的消息，使用`#分析图片`命令触发图片分析
- **自动识别文件类型**，图片文件自动使用视觉模型处理，文档使用文本模型处理
- 支持多种文件格式，包括文本文件、文档、代码文件等
- 提取文件和图片的关键信息和主要内容
- 显示处理用时、使用的模型信息
- 显示消耗的 Token 数量以及当前 API 余额
- 自动检测不支持的文件格式并提示用户
- 支持超级用户切换文本和视觉AI模型，提供多种容量选择

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

### 图片类
- PNG图像 (`.png`)
- JPG/JPEG图像 (`.jpg`, `.jpeg`)
- GIF动图 (`.gif`)
- BMP图像 (`.bmp`)
- WEBP图像 (`.webp`)
- TIFF图像 (`.tiff`, `.tif`)

## 项目结构

```
FileAi/
├── __init__.py              # 插件入口文件，定义命令和事件处理器
├── api_client.py            # Kimi API客户端，处理与Moonshot API的通信
├── command_handlers.py      # 命令处理函数，实现各个具体命令的处理逻辑
├── config.py                # 插件配置文件，定义API密钥等配置项
├── file_handler.py          # 文件处理模块，处理QQ群文件的下载和解析
├── file_message_handler.py  # 文件消息处理，提取消息中的文件信息
├── file_processor.py        # 文件处理器基类及具体实现，分别处理图片和文档文件
├── file_processor_proxy.py  # 文件处理代理，自动识别文件类型并选择合适的处理器
├── image_handler.py         # 图片处理模块，处理QQ消息中的图片
├── model_config.txt         # 文本模型配置存储文件
├── models.py                # 模型管理器，处理AI模型的选择和切换
├── utils.py                 # 工具函数，提供各种辅助功能
├── vision_model_config.txt  # 视觉模型配置存储文件
└── README.md                # 本文档
```

## 组件功能说明

### 核心组件

1. **__init__.py**
   - 插件入口点
   - 定义了事件响应器和命令处理器
   - 设置插件元数据和使用说明
   - 实现消息处理和并发控制

2. **api_client.py**
   - 封装了与Moonshot Kimi API的通信
   - 实现文件分析功能
   - 实现图片分析功能
   - 提供余额查询功能
   - 估算Token使用量的功能

3. **command_handlers.py**
   - 实现所有命令的处理逻辑
   - 处理文件分析请求
   - 处理图片分析请求
   - 处理模型设置请求
   - 处理余额查询请求

4. **models.py**
   - 定义可用的AI模型信息
   - 提供模型管理器，用于切换和保存模型设置
   - 管理文本模型和视觉模型的配置

### 文件处理组件

5. **file_processor.py**
   - 定义文件处理器的抽象基类
   - 提供图片文件处理器实现，使用视觉模型
   - 提供文档文件处理器实现，使用文本模型

6. **file_processor_proxy.py**
   - 实现代理模式，自动识别文件类型
   - 根据文件扩展名选择合适的处理器
   - 为不同类型文件提供统一的处理接口

7. **file_handler.py**
   - 处理QQ群文件的下载和提取
   - 获取文件URL和信息
   - 支持多种文件格式

8. **file_message_handler.py**
   - 从QQ消息中解析和提取文件信息
   - 处理文件分享消息的格式处理

9. **image_handler.py**
   - 从QQ消息中提取图片URL
   - 处理图片下载和分析

10. **utils.py**
    - 提供通用工具函数
    - 文件下载功能
    - 临时文件清理功能
    - 文件格式检查功能

### 配置文件

11. **config.py**
    - 定义插件配置项
    - 管理API密钥和基础URL
    - 设置默认模型选择

12. **model_config.txt/vision_model_config.txt**
    - 持久化保存用户设置的模型选择
    - 在插件重启后恢复上次的模型设置

## 安装和配置

1. 确保插件已放入正确的插件目录中

2. 在配置文件 `src/plugins/FileAi/config.py` 中设置以下参数：
   ```python
   class Config(BaseModel):
       CONFIG: dict = {
           "kimi_api_key": "你的Kimi API密钥",  # 从 Moonshot 平台获取
           "kimi_api_base_url": "https://api.moonshot.cn/v1",  # API 基础 URL
           "kimi_model": "moonshot-v1-32k",     # 使用的模型名称
           "kimi_vision_model": "moonshot-v1-vision",  # 使用的视觉模型名称
       }
   ```

## 可用模型

### 文本分析模型
插件支持多种Moonshot Kimi模型，你可以根据需要选择使用不同的模型:
- **moonshot-v1-auto**: 自动选择模型，根据使用token数量自动选择最合适的模型
- **moonshot-v1-128k**: 大容量模型，最大支持128k上下文长度，适合处理大型文档
- **moonshot-v1-32k**: 标准模型，支持32k上下文长度，适合大多数场景(默认)
- **moonshot-v1-8k**: 轻量级模型，支持8k上下文长度，处理速度较快

### 视觉分析模型
- **moonshot-v1-vision**: 标准视觉模型，适用于多数图片分析场景
- **moonshot-v1-vision-pro**: 高级视觉模型，提供更详细的图片分析

## 使用方法

### 文件解读与智能识别

1. 有人在群聊中发送文件
2. 回复该文件消息，并使用指令：`#分析文件 [分析要求]`
3. 机器人会自动识别文件类型：
   - 如果是图片文件（jpg、png等），将自动使用视觉模型分析
   - 如果是文档或代码文件，将使用文本模型分析
4. 机器人会下载该文件，使用对应的API分析内容，然后发送分析结果

例如：
```
#分析文件 帮我总结一下这个文档的主要内容
#分析文件 提取这个文件中的关键信息
#分析文件 解释这段代码的功能
#分析文件 描述一下这张图片的内容 (当文件为图片时)
```

### 图片分析

1. 有人在群聊中发送图片
2. 回复该图片消息，并使用指令：`#分析图片 [分析要求]`
3. 机器人会处理该图片，使用Kimi视觉API分析内容，然后发送分析结果

例如：
```
#分析图片 描述一下这张图片的内容
#分析图片 这张截图中有什么重要信息
#分析图片 解释这张图表的含义
```

### 模型管理(仅超级用户)

1. 查询API余额
   ```
   #查询余额
   ```

2. 设置文本分析模型
   ```
   #设置模型
   ```
   机器人会以交互式菜单方式列出可用模型，回复对应数字即可选择。

3. 设置图片分析模型
   ```
   #设置视觉模型
   ```
   同样以交互式菜单方式选择。

## 输出示例

### 文件分析结果示例

```
文件「example.pdf」的解读结果：

[解析内容...]

---
处理用时: 10秒
使用模型: moonshot-v1-32k
消耗Token: 1234
可用余额: 49.59
```

### 图片分析结果示例

```
图片「photo.jpg」的分析结果：

[分析内容...]

---
处理用时: 5秒
使用模型: moonshot-v1-vision
消耗Token: 567
可用余额: 49.12
```

## 智能处理和代理模式

本插件使用代理模式实现了智能文件处理：

- 自动检测文件类型，为不同类型的文件选择最合适的处理方式
- 图片文件会自动使用视觉模型处理，将用户的问题作为分析提示词
- 文档和代码文件会使用文本模型处理，专注于内容解析
- 使用统一的命令接口，简化用户操作

该设计提供了以下优势:
- **便捷性**: 使用同一命令处理不同类型文件
- **智能性**: 根据文件类型自动选择最合适的模型
- **扩展性**: 可以方便地增加新的文件类型处理方式
- **一致性**: 保持处理结果的输出格式一致

## 并发处理

为了确保系统稳定性和API调用效率，插件实现了并发控制：

- 同一时间只处理一个文件或图片请求
- 当有请求正在处理时，会提示用户稍后再试
- 处理完成后自动释放资源，可以处理下一个请求

## Moonshot API平台说明

1. **注册账户**: 访问 [Moonshot AI 开放平台](https://www.moonshot.cn/) 注册开发者账户

2. **创建应用**: 在开放平台创建应用获取API密钥

3. **配额与计费**: 
   - API使用基于Token计费，不同模型费率不同
   - 新用户通常有免费额度可以使用
   - 可在平台上查看详细的使用统计和余额

4. **API文档**: 平台提供详细的API文档，可以了解更多高级功能

## 常见问题

1. **文件无法解析**:
   - 检查文件格式是否支持
   - 文件大小是否超过限制(一般不超过20MB)
   - 文件内容是否可读取

2. **图片分析失败**:
   - 确认图片格式为常见图像格式
   - 图片是否有合理的分辨率和清晰度
   - 部分特殊图片内容可能无法被正确识别

3. **API调用错误**:
   - 检查API密钥是否正确设置
   - 确认API账户余额充足
   - 检查网络连接是否稳定

4. **模型设置问题**:
   - 只有超级用户才能更改模型设置
   - 当找不到指定模型时会使用默认模型

## 注意事项

- 需要机器人具有接收和下载文件及图片的权限
- 大文件或高清图片可能需要较长的处理时间
- 同一时间只能处理一个文件/图片请求(有并发限制)
- 超大型文件可能会被拒绝处理以保护系统
- 使用前需要从Moonshot开放平台申请API密钥
- 每次解析都会消耗 Token，请关注余额情况
- 模型设置会被保存，重启机器人后依然生效
- 根据实际需求选择合适的模型，大容量模型消耗的费用更多

## 错误处理

插件会自动处理常见错误，包括但不限于:

- 不支持的文件或图片格式提示
- 文件/图片下载失败的错误信息
- API调用失败的错误反馈
- 文件不存在的提示
- 并发请求限制提醒
- API余额不足警告

## 版本历史

- **1.0.0**: 初始版本，支持基本文件解读功能
- **1.1.0**: 添加模型切换功能，支持多种容量模型
- **1.2.0**: 添加Token统计和余额查询功能
- **1.3.0**: 支持自动模型选择
- **1.4.0**: 增加图片分析功能，支持视觉模型切换
- **1.5.0**: 扩展支持的图片格式，新增GIF、BMP、WEBP和TIFF格式
- **1.6.0**: 使用代理模式实现文件类型自动识别，图片文件自动使用视觉模型处理

## 开发者信息

- **作者**: dog
- **主页**: [https://github.com/CG-Jue/NoneBotPlugins](https://github.com/CG-Jue/NoneBotPlugins)
- **版本**: 1.6.0
- **支持的适配器**: OneBot V11

## 贡献与反馈

欢迎通过以下方式提供贡献和反馈:
- 在GitHub上提交Issue或Pull Request
- 报告bug或提出功能建议
- 分享使用体验和改进意见

## 许可协议

本插件遵循开源协议，详见项目GitHub页面。
