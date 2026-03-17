# 群消息处理功能设计

> 版本: 1.0  
> 日期: 2026-03-16  
> 状态: 设计完成

---

## 1. 功能概述

本文档描述 jz-wxbot-automation 项目中群消息 (Group Messages) 处理功能的架构设计。

### pywechat 群相关能力

| 功能 | 方法 | 状态 |
|------|------|------|
| 群置顶 | `pin_group()` | ✅ |
| 创建群聊 | `create_group_chat()` | ✅ |
| 群聊管理 | 群名/公告/邀请 | ✅ |
| 获取群列表 | `get_group_list()` | ✅ |
| 群消息处理 | ❌ | ❌ (需扩展) |

---

## 2. 系统架构

### 2.1 模块结构

```
core/groups/
├── __init__.py              # 导出
├── models.py                # 数据模型
├── monitor.py               # 群消息监听
├── parser.py                # 群消息解析
├── dispatcher.py            # 群消息分发
├── handlers/                # 处理器
│   ├── __init__.py
│   ├── at_handler.py        # @消息处理
│   ├── keyword_handler.py   # 关键词处理
│   ├── command_handler.py   # 命令处理
│   └── openclaw_handler.py # OpenClaw转发
└── exceptions.py            # 异常定义
```

### 2.2 消息流

```
┌─────────────────────────────────────────────────────────────┐
│                        微信群                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    GroupMonitor                             │
│                  (群消息监听器)                              │
│  1. 识别群消息                                               │
│  2. 提取@信息                                                │
│  3. 区分私聊/群聊                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   GroupMessageParser                        │
│                   (群消息解析器)                             │
│  1. 解析消息类型                                             │
│  2. 提取发送者                                                │
│  3. 提取@列表                                                │
│  4. 提取命令/关键词                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  GroupDispatcher                            │
│                   (群消息分发器)                             │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ @消息处理   │  │ 关键词处理  │  │ 命令处理    │            │
│  │  AtHandler  │  │ KeywordHdlr │  │ CommandHdlr │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                   │
│  ┌─────────────────────────────────────────────────────┐       │
│  │           OpenClawHandler (转发)                     │       │
│  │    群消息 → OpenClaw AI → 回复 → 自动发送           │       │
│  └─────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 数据模型

### 3.1 群消息模型

```python
# core/groups/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class GroupMessageType(Enum):
    """群消息类型"""
    TEXT = "text"           # 文本
    IMAGE = "image"         # 图片
    VOICE = "voice"         # 语音
    VIDEO = "video"         # 视频
    FILE = "file"           # 文件
    LINK = "link"           # 链接
    CARD = "card"           # 名片
    SYSTEM = "system"       # 系统消息
    REDPACKET = "redpacket" # 红包
    AT = "at"               # @消息


class MessageTarget(Enum):
    """消息目标"""
    ALL = "all"             # @所有人
    SPECIFIC = "specific"  # @特定人
    NONE = "none"           # 无@


@dataclass
class GroupMessage:
    """群消息"""
    msg_id: str                         # 消息ID
    room_id: str                        # 群ID
    room_name: str                      # 群名称
    sender_id: str                      # 发送者ID
    sender_name: str                    # 发送者名称
    sender_remark: str                  # 发送者备注
    content: str                        # 消息内容
    msg_type: GroupMessageType          # 消息类型
    target: MessageTarget = MessageTarget.NONE  # @目标
    at_list: List[str] = field(default_factory=list)  # @列表
    is_at_me: bool = False              # 是否@我
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: dict = field(default_factory=dict)
    
    @property
    def is_at_all(self) -> bool:
        """是否@所有人"""
        return self.target == MessageTarget.ALL
    
    @property
    def is_command(self) -> bool:
        """是否命令消息"""
        return self.content.startswith('/') or self.content.startswith('!')
    
    @property
    def command(self) -> Optional[str]:
        """提取命令"""
        if self.is_command:
            parts = self.content[1:].split()
            return parts[0] if parts else None
        return None


@dataclass
class GroupInfo:
    """群信息"""
    room_id: str
    name: str
    owner_id: str
    owner_name: str
    member_count: int
    notice: Optional[str] = None
    is_muted: bool = False
    is_pinned: bool = False
    created_at: Optional[datetime] = None
    my_nickname: Optional[str] = None


@dataclass
class GroupMember:
    """群成员"""
    user_id: str
    display_name: str
    nickname: str
    role: str  # owner/admin/member
    join_time: Optional[datetime] = None
    is_active: bool = True
```

### 3.2 处理配置

```python
@dataclass
class GroupHandlerConfig:
    """群处理器配置"""
    enabled: bool = True
    groups: List[str] = field(default_factory=list)  # 启用群ID列表
    exclude_groups: List[str] = field(default_factory=list)  # 排除群ID
    at_reply: bool = True              # 回复@消息
    keyword_reply: bool = True         # 关键词回复
    command_enabled: bool = True      # 命令启用
    openclaw_forward: bool = True     # 转发到OpenClaw
    min_interval: int = 3              # 最小回复间隔(秒)
    max_daily: int = 100               # 每日最大回复数


@dataclass
class ReplyConfig:
    """回复配置"""
    prefix: str = ""                   # 回复前缀
    suffix: str = ""                   # 回复后缀
    mention_sender: bool = True        # 是否@发送者
    template: Optional[str] = None     # 回复模板
```

---

## 4. 核心模块

### 4.1 群消息监听器

```python
# core/groups/monitor.py

import asyncio
from typing import Callable, Optional
from .models import GroupMessage, GroupInfo
from .parser import GroupMessageParser


class GroupMonitor:
    """群消息监听器
    
    监听群消息，区分普通消息和@消息
    """
    
    def __init__(
        self,
        parser: GroupMessageParser,
        on_message: Callable[[GroupMessage], None],
        poll_interval: float = 1.0
    ):
        self.parser = parser
        self.on_message = on_message
        self.poll_interval = poll_interval
        self._running = False
        self._known_messages = set()
        self._my_user_id = "self"
    
    async def start(self):
        """启动监听"""
        self._running = True
        while self._running:
            try:
                raw_messages = await self._fetch_group_messages()
                for raw in raw_messages:
                    # 检查是否已处理
                    msg_id = raw.get('msg_id')
                    if msg_id in self._known_messages:
                        continue
                    
                    # 解析群消息
                    group_msg = self.parser.parse(raw, self._my_user_id)
                    if group_msg:
                        self._known_messages.add(msg_id)
                        self.on_message(group_msg)
                        
            except Exception as e:
                print(f"Group monitor error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """停止监听"""
        self._running = False
    
    async def _fetch_group_messages(self) -> list:
        """获取群消息 (需对接 pywechat)"""
        # TODO: 实现从 pywechat 获取群消息
        return []
    
    def set_my_user_id(self, user_id: str):
        """设置我的用户ID"""
        self._my_user_id = user_id
```

### 4.2 群消息解析器

```python
# core/groups/parser.py

import re
from typing import Optional
from .models import (
    GroupMessage, GroupMessageType, 
    MessageTarget, GroupInfo, GroupMember
)


class GroupMessageParser:
    """群消息解析器
    
    解析群消息，提取@信息、命令等
    """
    
    # @我的正则
    AT_ME_PATTERN = re.compile(r'@(\S+?)(?:\s|$)')
    AT_ALL_PATTERN = re.compile(r'@所有人')
    
    def __init__(self, my_nickname: str = "机器人"):
        self.my_nickname = my_nickname
    
    def parse(self, raw_data: dict, my_user_id: str) -> Optional[GroupMessage]:
        """解析原始群消息"""
        try:
            # 基础信息
            room_id = raw_data.get('room_id', '')
            room_name = raw_data.get('room_name', '')
            sender_id = raw_data.get('from_user', '')
            sender_name = raw_data.get('from_nickname', '')
            content = raw_data.get('content', '')
            
            # 解析@信息
            at_list, target, is_at_me = self._parse_at_info(
                content, 
                self.my_nickname
            )
            
            # 解析消息类型
            msg_type = self._detect_message_type(content, raw_data)
            
            return GroupMessage(
                msg_id=raw_data.get('msg_id', ''),
                room_id=room_id,
                room_name=room_name,
                sender_id=sender_id,
                sender_name=sender_name,
                sender_remark=raw_data.get('from_remark', sender_name),
                content=content,
                msg_type=msg_type,
                target=target,
                at_list=at_list,
                is_at_me=is_at_me,
                raw_data=raw_data
            )
            
        except Exception as e:
            print(f"Parse error: {e}")
            return None
    
    def _parse_at_info(self, content: str, my_nickname: str):
        """解析@信息"""
        at_list = []
        target = MessageTarget.NONE
        is_at_me = False
        
        # 检查@所有人
        if self.AT_ALL_PATTERN.search(content):
            target = MessageTarget.ALL
            is_at_me = True
        
        # 检查@特定人
        matches = self.AT_ME_PATTERN.findall(content)
        for name in matches:
            at_list.append(name)
            if name == my_nickname or name == "我":
                is_at_me = True
                if target != MessageTarget.ALL:
                    target = MessageTarget.SPECIFIC
        
        return at_list, target, is_at_me
    
    def _detect_message_type(self, content: str, raw_data: dict) -> GroupMessageType:
        """检测消息类型"""
        msg_type_raw = raw_data.get('type', 1)
        
        type_map = {
            1: GroupMessageType.TEXT,
            2: GroupMessageType.IMAGE,
            3: GroupMessageType.VOICE,
            4: GroupMessageType.VIDEO,
            6: GroupMessageType.FILE,
            42: GroupMessageType.CARD,
            49: GroupMessageType.LINK,
            10000: GroupMessageType.SYSTEM,
        }
        
        return type_map.get(msg_type_raw, GroupMessageType.TEXT)
```

### 4.3 群消息分发器

```python
# core/groups/dispatcher.py

import asyncio
from typing import List, Optional, Dict
from .models import GroupMessage, GroupHandlerConfig
from .handlers.at_handler import AtHandler
from .handlers.keyword_handler import KeywordHandler
from .handlers.command_handler import CommandHandler
from .handlers.openclaw_handler import OpenClawHandler


class GroupDispatcher:
    """群消息分发器
    
    将群消息分发给各处理器
    """
    
    def __init__(self, config: GroupHandlerConfig):
        self.config = config
        self.handlers: List[tuple] = []
        self._init_handlers()
    
    def _init_handlers(self):
        """初始化处理器"""
        # @消息处理器 (高优先级)
        if self.config.at_reply:
            self.handlers.append((AtHandler(), 100))
        
        # 命令处理器
        if self.config.command_enabled:
            self.handlers.append((CommandHandler(), 90))
        
        # 关键词处理器
        if self.config.keyword_reply:
            self.handlers.append((KeywordHandler(), 80))
        
        # OpenClaw转发处理器
        if self.config.openclaw_forward:
            self.handlers.append((OpenClawHandler(), 50))
        
        # 按优先级排序
        self.handlers.sort(key=lambda x: x[1], reverse=True)
    
    async def dispatch(self, message: GroupMessage) -> Optional[str]:
        """分发消息"""
        # 检查是否应该处理
        if not self._should_handle(message):
            return None
        
        # 按优先级尝试处理
        for handler, _ in self.handlers:
            if not handler.should_handle(message):
                continue
            
            try:
                result = await handler.handle(message)
                if result:
                    return result
            except Exception as e:
                print(f"Handler {handler.name} error: {e}")
        
        return None
    
    def _should_handle(self, message: GroupMessage) -> bool:
        """检查是否应该处理"""
        # 排除自己发送的消息
        if message.sender_id == "self":
            return False
        
        return True
```

---

## 5. 处理器实现

### 5.1 @消息处理器

```python
# core/groups/handlers/at_handler.py

from typing import Optional
from core.interfaces.handler import MessageHandler
from core.groups.models import GroupMessage


class AtHandler(MessageHandler):
    """@消息处理器
    
    处理@机器人的消息
    """
    
    def __init__(self):
        self.name = "at_handler"
    
    @property
    def supported_types(self):
        return None  # 所有类型
    
    async def handle(self, message: GroupMessage) -> Optional[str]:
        """处理@消息"""
        if not message.is_at_me:
            return None
        
        content = message.content
        # 移除@信息
        content = self._remove_at_mention(content)
        
        if not content.strip():
            return "有什么可以帮你的？"
        
        # 这里可以调用 AI 或其他处理
        return f"收到: {content}"
    
    def _remove_at_mention(self, content: str) -> str:
        """移除@提及"""
        import re
        # 移除@xxx
        content = re.sub(r'@\S+\s*', '', content)
        return content.strip()
```

### 5.2 关键词处理器

```python
# core/groups/handlers/keyword_handler.py

from typing import Optional, Dict, List
from core.interfaces.handler import MessageHandler
from core.groups.models import GroupMessage


class KeywordHandler(MessageHandler):
    """关键词处理器
    
    根据关键词回复
    """
    
    def __init__(self):
        self.name = "keyword_handler"
        self._keywords: Dict[str, str] = {}
        self._init_default_keywords()
    
    def _init_default_keywords(self):
        """初始化默认关键词"""
        self._keywords = {
            "help": "可用命令: /help, /status, /info",
            "帮助": "可用命令: /help, /status, /info",
            "hello": "你好！有什么可以帮你的？",
            "你好": "你好！有什么可以帮你的？",
        }
    
    @property
    def supported_types(self):
        return None
    
    def add_keyword(self, keyword: str, response: str):
        """添加关键词"""
        self._keywords[keyword.lower()] = response
    
    def remove_keyword(self, keyword: str):
        """移除关键词"""
        self._keywords.pop(keyword.lower(), None)
    
    async def handle(self, message: GroupMessage) -> Optional[str]:
        """处理关键词消息"""
        content = message.content.lower()
        
        # 精确匹配
        if content in self._keywords:
            return self._keywords[content]
        
        # 模糊匹配
        for keyword, response in self._keywords.items():
            if keyword in content:
                return response
        
        return None
```

### 5.3 命令处理器

```python
# core/groups/handlers/command_handler.py

from typing import Optional, Dict
from core.interfaces.handler import MessageHandler
from core.groups.models import GroupMessage


class CommandHandler(MessageHandler):
    """命令处理器
    
    处理命令消息
    """
    
    def __init__(self):
        self.name = "command_handler"
        self._commands: Dict[str, callable] = {}
        self._init_default_commands()
    
    def _init_default_commands(self):
        """初始化默认命令"""
        self._commands = {
            "/help": self._cmd_help,
            "/status": self._cmd_status,
            "/info": self._cmd_info,
            "/ping": lambda m: "pong",
        }
    
    @property
    def supported_types(self):
        return None
    
    def register_command(self, command: str, handler: callable):
        """注册命令"""
        self._commands[command] = handler
    
    async def handle(self, message: GroupMessage) -> Optional[str]:
        """处理命令"""
        if not message.is_command:
            return None
        
        command = message.command
        if command in self._commands:
            return await self._commands[command](message)
        
        return f"未知命令: {command}"
    
    async def _cmd_help(self, message: GroupMessage) -> str:
        return """可用命令:
/help - 显示帮助
/status - 状态信息
/info - 机器人信息
/ping - 测试"""
    
    async def _cmd_status(self, message: GroupMessage) -> str:
        return "状态: 在线 | 版本: 1.0.0"
    
    async def _cmd_info(self, message: GroupMessage) -> str:
        return "我是 AI 助手，有问题尽管问我！"
```

### 5.4 OpenClaw转发处理器

```python
# core/groups/handlers/openclaw_handler.py

from typing import Optional
from core.interfaces.handler import MessageHandler
from core.groups.models import GroupMessage
from openclaw_mcp.server import OpenClawMCPServer


class OpenClawHandler(MessageHandler):
    """OpenClaw转发处理器
    
    将群消息转发到 OpenClaw 处理
    """
    
    def __init__(self, mcp_server: OpenClawMCPServer = None):
        self.name = "openclaw_handler"
        self._mcp_server = mcp_server
    
    @property
    def supported_types(self):
        return None
    
    async def handle(self, message: GroupMessage) -> Optional[str]:
        """转发到 OpenClaw"""
        if not self._mcp_server:
            return None
        
        # 只转发@我的消息或高优先级消息
        if not message.is_at_me:
            # 可选：也可以转发所有消息
            # return await self._forward_to_openclaw(message)
            return None
        
        return await self._forward_to_openclaw(message)
    
    async def _forward_to_openclaw(self, message: GroupMessage) -> str:
        """转发到 OpenClaw 并获取回复"""
        try:
            response = await self._mcp_server.handle_message(message)
            return response.reply
        except Exception as e:
            print(f"OpenClaw forward error: {e}")
            return None
```

---

## 6. 使用示例

```python
# examples/group_message_example.py

import asyncio
from core.groups.monitor import GroupMonitor
from core.groups.parser import GroupMessageParser
from core.groups.dispatcher import GroupDispatcher
from core.groups.models import GroupHandlerConfig
from core.groups.handlers.keyword_handler import KeywordHandler


async def main():
    # 1. 配置
    config = GroupHandlerConfig(
        enabled=True,
        groups=["group-1", "group-2"],  # 启用的群
        at_reply=True,
        keyword_reply=True,
        command_enabled=True,
        openclaw_forward=True
    )
    
    # 2. 添加自定义关键词
    keyword_handler = KeywordHandler()
    keyword_handler.add_keyword("天气", "今天天气很好！")
    keyword_handler.add_keyword("股票", "投资有风险，入市需谨慎。")
    
    # 3. 创建分发器
    dispatcher = GroupDispatcher(config)
    
    # 4. 定义消息处理
    async def handle_group_message(message):
        print(f"[{message.room_name}] {message.sender_name}: {message.content}")
        
        # 分发处理
        reply = await dispatcher.dispatch(message)
        
        if reply:
            print(f"回复: {reply}")
            # TODO: 发送到群
    
    # 5. 启动监听
    parser = GroupMessageParser(my_nickname="小助手")
    monitor = GroupMonitor(
        parser=parser,
        on_message=handle_group_message
    )
    
    print("群消息监听已启动...")
    await monitor.start()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. 功能状态

| 功能 | 状态 | 备注 |
|------|------|------|
| 群消息解析 | ✅ 已实现 | 支持@解析 |
| @消息处理 | ✅ 已实现 | AtHandler |
| 关键词回复 | ✅ 已实现 | KeywordHandler |
| 命令处理 | ✅ 已实现 | CommandHandler |
| OpenClaw转发 | ✅ 已实现 | OpenClawHandler |
| 群消息监听 | 🔄 设计完成 | 需对接 pywechat |

---

## 8. 总结

- **模块化**: 处理器解耦，易于扩展
- **优先级**: @消息 > 命令 > 关键词 > OpenClaw
- **灵活性**: 支持配置启用/禁用
- **可扩展**: 预留 MCP 转发接口