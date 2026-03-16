# jz-wxbot-automation API 使用指南

**版本**: v1.0  
**创建日期**: 2026-03-16  
**项目**: jz-wxbot-automation  
**适用对象**: 开发者、集成人员

---

## 📋 目录

1. [API 概述](#api 概述)
2. [MCP 工具 API](#mcp 工具 api)
3. [Python SDK API](#python-sdk-api)
4. [使用示例](#使用示例)
5. [错误处理](#错误处理)
6. [最佳实践](#最佳实践)

---

## API 概述

jz-wxbot-automation 提供两种 API 接口：

### 1. MCP 工具 API（推荐）

通过 **MCP (Model Context Protocol)** 协议向 AI 助手（如 OpenClaw）提供微信操作能力。

**特点**：
- ✅ 标准化协议，即插即用
- ✅ AI 助手自动发现和调用
- ✅ 支持工具、资源、提示词
- ✅ 安全可控，权限隔离

**适用场景**：
- AI 助手集成
- 智能消息处理
- 自动化工作流

### 2. Python SDK API

直接调用 Python 模块和类进行微信操作。

**特点**：
- ✅ 直接控制，灵活性高
- ✅ 无需额外依赖
- ✅ 适合脚本和自动化

**适用场景**：
- 本地脚本
- 定时任务
- 批量操作

---

## MCP 工具 API

### 工具列表

| 工具名称 | 描述 | 输入参数 | 输出 |
|---------|------|---------|------|
| `wxbot_send_message` | 发送微信消息 | target, message, chat_type | 发送结果 |
| `wxbot_read_messages` | 读取新消息 | chat_type, limit | 消息列表 |
| `wxbot_send_moments` | 发送朋友圈 | content, images, visibility | 发布结果 |
| `wxbot_mass_send` | 群发消息 | targets, message, interval | 发送统计 |
| `wxbot_add_friend` | 添加好友 | keyword, verify_message, source | 添加结果 |

---

### wxbot_send_message

**功能**: 发送微信消息到指定联系人或群聊

**输入参数**：
```json
{
  "target": "string (必填) - 目标用户昵称或群名",
  "message": "string (必填) - 消息内容",
  "chat_type": "string (可选) - 聊天类型：private|group，默认 private"
}
```

**输出示例**：
```json
{
  "success": true,
  "target": "张三",
  "message_length": 18,
  "timestamp": "2026-03-16T09:30:00",
  "sender_type": "wechat"
}
```

**调用示例**：
```python
# 通过 MCP 客户端调用
from mcp import Client

client = Client()
await client.connect_to_server("jz-wxbot")

result = await client.call_tool(
    "wxbot_send_message",
    {
        "target": "技术交流群",
        "message": "大家好，今天下午 3 点开会",
        "chat_type": "group"
    }
)

print(result[0].text)  # JSON 格式的响应
```

---

### wxbot_read_messages

**功能**: 读取微信新消息

**输入参数**：
```json
{
  "chat_type": "string (可选) - 聊天类型：private|group|all，默认 all",
  "limit": "integer (可选) - 最大消息数量，默认 10"
}
```

**输出示例**：
```json
{
  "count": 3,
  "messages": [
    {
      "sender": "李四",
      "content": "产品多少钱？",
      "chat_type": "private",
      "chat_name": "李四",
      "timestamp": "2026-03-16T09:29:00",
      "is_mention": false
    },
    {
      "sender": "王五",
      "content": "@我 有人知道吗",
      "chat_type": "group",
      "chat_name": "技术交流群",
      "timestamp": "2026-03-16T09:28:30",
      "is_mention": true
    }
  ]
}
```

**调用示例**：
```python
result = await client.call_tool(
    "wxbot_read_messages",
    {
        "chat_type": "all",
        "limit": 20
    }
)

messages = json.loads(result[0].text)
for msg in messages["messages"]:
    print(f"{msg['sender']}: {msg['content']}")
```

---

### wxbot_send_moments

**功能**: 发送朋友圈

**输入参数**：
```json
{
  "content": "string (必填) - 朋友圈文字内容",
  "images": "array (可选) - 图片路径列表，最多 9 张",
  "visibility": "string (可选) - 可见范围：public|private|partial，默认 public"
}
```

**输出示例**：
```json
{
  "success": true,
  "content_length": 50,
  "image_count": 3,
  "timestamp": "2026-03-16T10:00:00"
}
```

**调用示例**：
```python
result = await client.call_tool(
    "wxbot_send_moments",
    {
        "content": "今天天气真好！",
        "images": [
            "C:/photos/sunny_day.jpg",
            "C:/photos/park.jpg"
        ],
        "visibility": "public"
    }
)
```

---

### wxbot_mass_send

**功能**: 群发消息（需要管理员权限）

**输入参数**：
```json
{
  "targets": "array (必填) - 目标用户/群列表",
  "message": "string (必填) - 消息内容",
  "interval": "object (可选) - 发送间隔范围（秒）",
  "interval.min": "number - 最小间隔，默认 3",
  "interval.max": "number - 最大间隔，默认 10"
}
```

**输出示例**：
```json
{
  "total": 10,
  "success_count": 9,
  "fail_count": 1,
  "details": [
    {
      "target": "张三",
      "success": true,
      "timestamp": "2026-03-16T10:05:00"
    },
    {
      "target": "李四",
      "success": false,
      "error": "用户不存在"
    }
  ]
}
```

**调用示例**：
```python
result = await client.call_tool(
    "wxbot_mass_send",
    {
        "targets": ["张三", "李四", "技术交流群"],
        "message": "新年快乐！",
        "interval": {"min": 5, "max": 10}
    }
)

stats = json.loads(result[0].text)
print(f"成功：{stats['success_count']}, 失败：{stats['fail_count']}")
```

**限制**：
- ⚠️ 单次群发 ≤ 50 人
- ⚠️ 每日群发 ≤ 200 人
- ⚠️ 需要管理员权限

---

### wxbot_add_friend

**功能**: 添加微信好友

**输入参数**：
```json
{
  "keyword": "string (必填) - 微信号、手机号或群内用户",
  "verify_message": "string (可选) - 好友验证消息",
  "source": "string (可选) - 添加来源：search|group|qr，默认 search"
}
```

**输出示例**：
```json
{
  "success": true,
  "keyword": "13800138000",
  "timestamp": "2026-03-16T10:10:00",
  "status": "pending"  // pending: 等待验证，accepted: 已通过
}
```

**调用示例**：
```python
result = await client.call_tool(
    "wxbot_add_friend",
    {
        "keyword": "13800138000",
        "verify_message": "你好，我是张三",
        "source": "search"
    }
)
```

**限制**：
- ⚠️ 每日添加 ≤ 20 人（新号≤10 人）
- ⚠️ 添加间隔 ≥ 3 分钟

---

## Python SDK API

### 基础使用

#### 1. 导入模块

```python
from wechat_sender_v3 import WeChatSender
from wxwork_sender_robust import WXWorkSenderRobust
from human_like_operations import HumanLikeOperations
```

#### 2. 发送消息

```python
# 个人微信发送
sender = WeChatSender()
success = sender.send_message("技术交流群", "大家好！")

# 企业微信发送
wxwork_sender = WXWorkSenderRobust()
success = wxwork_sender.send_message("项目组", "下午开会")
```

#### 3. 人性化操作

```python
human_ops = HumanLikeOperations()

# 人性化延迟
human_ops.human_delay(base_time=2.0)

# 人性化鼠标移动
human_ops.human_move_to(x=500, y=300)

# 模拟阅读停顿
human_ops.simulate_reading_pause()
```

---

### 高级 API

#### AutoReportSystemV2 - 自动化系统

```python
from auto_daily_report_v2 import AutoReportSystemV2

# 创建系统实例
system = AutoReportSystemV2()

# 初始化发送器
system.initialize_senders()

# 查看状态
system.print_status()

# 执行完整自动化
result = system.run_full_automation()

print(f"发送成功：{result['success']}")
print(f"使用发送器：{result['sender_used']}")
```

#### MessageSenderInterface - 统一接口

```python
from message_sender_interface import MessageSenderInterface

def send_via_interface(sender: MessageSenderInterface, target: str, message: str):
    """通过统一接口发送消息"""
    if not sender.is_available():
        print("发送器不可用")
        return False
    
    success = sender.send_message(target, message)
    
    if success:
        info = sender.get_info()
        print(f"通过 {info['name']} 发送成功")
    
    return success
```

#### BridgeService - OpenClaw 桥接

```python
from bridge import BridgeService

async def main():
    # 创建桥接服务
    config = {
        "openclaw": {
            "api_key": "your-api-key",
            "workspace": "your-workspace"
        },
        "mcp": {
            "transport": "stdio"
        }
    }
    
    bridge = BridgeService(config)
    
    # 启动服务
    await bridge.start()
    
    # 处理消息
    message = {
        "sender": "张三",
        "content": "你好",
        "chat_type": "private"
    }
    
    reply = await bridge.process_message(message)
    print(f"AI 回复：{reply}")

# 运行
import asyncio
asyncio.run(main())
```

---

## 使用示例

### 示例 1: 智能客服自动回复

```python
from openclaw import Client
from mcp import Client as MCPClient
import asyncio

class SmartCustomerService:
    """智能客服系统"""
    
    def __init__(self):
        self.openclaw = Client(api_key="xxx")
        self.mcp = MCPClient()
    
    async def run(self):
        """运行客服系统"""
        await self.mcp.connect_to_server("jz-wxbot")
        
        while True:
            # 读取新消息
            messages = await self.read_new_messages()
            
            for msg in messages:
                # 通过 OpenClaw 生成回复
                reply = await self.generate_reply(msg)
                
                # 发送回复
                await self.send_reply(msg["sender"], reply)
            
            await asyncio.sleep(5)  # 每 5 秒检查一次
    
    async def read_new_messages(self):
        """读取新消息"""
        result = await self.mcp.call_tool(
            "wxbot_read_messages",
            {"chat_type": "private", "limit": 10}
        )
        data = json.loads(result[0].text)
        return data["messages"]
    
    async def generate_reply(self, message: dict):
        """生成回复"""
        response = await self.openclaw.chat(
            messages=[
                {"role": "system", "content": "你是专业的客服助手"},
                {"role": "user", "content": message["content"]}
            ]
        )
        return response.content
    
    async def send_reply(self, target: str, reply: str):
        """发送回复"""
        await self.mcp.call_tool(
            "wxbot_send_message",
            {
                "target": target,
                "message": reply,
                "chat_type": "private"
            }
        )

# 运行
service = SmartCustomerService()
asyncio.run(service.run())
```

---

### 示例 2: 定时消息发送

```python
import schedule
import time
from mcp import Client

class ScheduledMessenger:
    """定时消息发送器"""
    
    def __init__(self):
        self.mcp = Client()
    
    async def setup(self):
        """设置定时任务"""
        await self.mcp.connect_to_server("jz-wxbot")
        
        # 每天早上 9 点发送晨报
        schedule.every().day.at("09:00").do(
            self.send_morning_report
        )
        
        # 每天下午 6 点发送晚报
        schedule.every().day.at("18:00").do(
            self.send_evening_report
        )
        
        # 每周五发送周报
        schedule.every().friday.at("17:00").do(
            self.send_weekly_report
        )
    
    def send_morning_report(self):
        """发送晨报"""
        message = """
🌞 早安！新的一天开始了
        
今日天气：晴朗
气温：20-28°C
提醒：记得带伞
        
祝大家工作顺利！
        """
        self._send_to_group("公司群", message)
    
    def send_evening_report(self):
        """发送晚报"""
        message = """
🌙 晚安！今天辛苦了
        
明日预告：
- 上午 10 点：项目会议
- 下午 2 点：客户拜访
        
早点休息！
        """
        self._send_to_group("公司群", message)
    
    def send_weekly_report(self):
        """发送周报"""
        message = """
📊 本周工作总结
        
✅ 完成：
- 项目 A 开发
- 客户 B 拜访
- 团队培训

📅 下周计划：
- 项目 A 上线
- 新客户拓展

周末愉快！
        """
        self._send_to_group("公司群", message)
    
    def _send_to_group(self, group: str, message: str):
        """发送消息到群聊"""
        import asyncio
        asyncio.run(self.mcp.call_tool(
            "wxbot_send_message",
            {
                "target": group,
                "message": message,
                "chat_type": "group"
            }
        ))
    
    def run(self):
        """运行定时任务"""
        asyncio.run(self.setup())
        
        while True:
            schedule.run_pending()
            time.sleep(60)

# 运行
messenger = ScheduledMessenger()
messenger.run()
```

---

### 示例 3: 群消息监控和自动回复

```python
from mcp import Client
import asyncio
import json

class GroupMonitor:
    """群消息监控器"""
    
    def __init__(self, group_name: str, keywords: list):
        self.group_name = group_name
        self.keywords = keywords
        self.mcp = Client()
        self.last_message_id = None
    
    async def start(self):
        """启动监控"""
        await self.mcp.connect_to_server("jz-wxbot")
        
        print(f"开始监控群聊：{self.group_name}")
        print(f"关键词：{self.keywords}")
        
        while True:
            await self.check_messages()
            await asyncio.sleep(3)  # 每 3 秒检查一次
    
    async def check_messages(self):
        """检查新消息"""
        result = await self.mcp.call_tool(
            "wxbot_read_messages",
            {
                "chat_type": "group",
                "limit": 10
            }
        )
        
        data = json.loads(result[0].text)
        
        for msg in data["messages"]:
            # 检查是否是指定群聊
            if msg.get("chat_name") != self.group_name:
                continue
            
            # 检查是否是新消息
            msg_id = f"{msg['sender']}:{msg['timestamp']}"
            if msg_id == self.last_message_id:
                continue
            
            self.last_message_id = msg_id
            
            # 检查是否包含关键词
            for keyword in self.keywords:
                if keyword in msg["content"]:
                    print(f"检测到关键词 '{keyword}'")
                    await self.handle_keyword(msg, keyword)
                    break
    
    async def handle_keyword(self, message: dict, keyword: str):
        """处理关键词"""
        # 根据关键词自动回复
        replies = {
            "价格": "我们的产品价格是 XXX 元，具体规格请看官网",
            "联系": "联系方式：电话 12345678，微信 xxx",
            "地址": "公司地址：xxx 省 xxx 市 xxx 区",
            "帮助": "请问有什么可以帮助您的？"
        }
        
        reply = replies.get(keyword, "收到，稍后回复您")
        
        # 发送回复
        await self.mcp.call_tool(
            "wxbot_send_message",
            {
                "target": self.group_name,
                "message": f"@{message['sender']} {reply}",
                "chat_type": "group"
            }
        )

# 运行
monitor = GroupMonitor(
    group_name="客户咨询群",
    keywords=["价格", "联系", "地址", "帮助"]
)

asyncio.run(monitor.start())
```

---

## 错误处理

### MCP 工具调用错误

```python
from mcp.exceptions import ToolError, TimeoutError, ConnectionError

try:
    result = await client.call_tool("wxbot_send_message", args)
except ToolError as e:
    print(f"工具调用失败：{e.error_code} - {e.message}")
    # 可能的错误码：
    # - INVALID_ARGS: 参数无效
    # - TOOL_NOT_FOUND: 工具不存在
    # - EXECUTION_FAILED: 执行失败
except TimeoutError:
    print("工具调用超时")
except ConnectionError:
    print("MCP 服务器连接断开")
    # 尝试重连
    await client.connect_to_server("jz-wxbot")
except Exception as e:
    print(f"未知错误：{e}")
```

### Python SDK 错误

```python
from wechat_sender_v3 import WeChatSender, WeChatNotRunningError

sender = WeChatSender()

try:
    success = sender.send_message("群名", "消息")
    if not success:
        print("发送失败")
except WeChatNotRunningError:
    print("微信未运行，请启动微信")
except Exception as e:
    print(f"发送异常：{e}")
```

### 错误码说明

| 错误码 | 说明 | 解决方案 |
|--------|------|---------|
| `INVALID_ARGS` | 参数无效 | 检查参数类型和必填项 |
| `TOOL_NOT_FOUND` | 工具不存在 | 确认工具名称正确 |
| `EXECUTION_FAILED` | 执行失败 | 查看详细错误信息 |
| `WECHAT_NOT_RUNNING` | 微信未运行 | 启动微信客户端 |
| `WINDOW_NOT_FOUND` | 窗口未找到 | 检查窗口是否打开 |
| `RATE_LIMIT_EXCEEDED` | 频率超限 | 降低调用频率 |
| `PERMISSION_DENIED` | 权限不足 | 检查权限配置 |

---

## 最佳实践

### 1. 频率控制

```python
import time
import random

class RateLimitedSender:
    """限流发送器"""
    
    def __init__(self, min_interval=3, max_interval=10):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.last_send_time = 0
    
    async def send(self, target, message):
        """发送消息（带限流）"""
        # 检查间隔
        now = time.time()
        elapsed = now - self.last_send_time
        
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            await asyncio.sleep(wait_time)
        
        # 添加随机延迟
        delay = random.uniform(self.min_interval, self.max_interval)
        await asyncio.sleep(delay)
        
        # 发送消息
        result = await client.call_tool(
            "wxbot_send_message",
            {"target": target, "message": message}
        )
        
        self.last_send_time = time.time()
        return result
```

### 2. 重试机制

```python
import asyncio
from functools import wraps

def retry(max_attempts=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"第{attempt+1}次失败：{e}，重试中...")
                    await asyncio.sleep(delay * (attempt + 1))
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2)
async def send_with_retry(target, message):
    """发送消息（带重试）"""
    return await client.call_tool(
        "wxbot_send_message",
        {"target": target, "message": message}
    )
```

### 3. 日志记录

```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wxbot_api.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def send_with_logging(target, message):
    """发送消息（带日志）"""
    logger.info(f"准备发送消息到 {target}: {message[:50]}...")
    
    try:
        result = await client.call_tool(
            "wxbot_send_message",
            {"target": target, "message": message}
        )
        
        response = json.loads(result[0].text)
        
        if response.get("success"):
            logger.info(f"发送成功：{target}")
        else:
            logger.warning(f"发送失败：{target}")
        
        return result
    except Exception as e:
        logger.error(f"发送异常：{e}", exc_info=True)
        raise
```

### 4. 配置管理

```python
# config.py
from pydantic import BaseModel
import yaml

class AppConfig(BaseModel):
    """应用配置"""
    mcp_server: str = "jz-wxbot"
    default_chat_type: str = "private"
    rate_limit_min: int = 3
    rate_limit_max: int = 10
    max_retry: int = 3
    log_level: str = "INFO"

def load_config(path: str = "config.yaml") -> AppConfig:
    """加载配置"""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)

# 使用
config = load_config()
```

---

## 相关文档

- [开发指南](./DEVELOPMENT_GUIDE.md)
- [部署指南](./DEPLOYMENT_GUIDE.md)
- [MCP 集成指南](./MCP_INTEGRATION_GUIDE.md)
- [项目 README](../README.md)

---

**文档维护**: jz-wxbot-automation 开发团队  
**反馈邮箱**: dev@jz-wxbot.local  
**最后更新**: 2026-03-16
