# 微信消息处理模块设计

> 版本: 1.0  
> 日期: 2026-03-16  
> 状态: 设计完成

---

## 1. 概述

本文档描述 jz-wxbot-automation 项目中微信消息接收和处理模块的架构设计。

### 设计目标

- **实时性**: 快速响应新消息
- **可扩展性**: 支持多种消息类型和处理器
- **可靠性**: 消息不丢失，错误可恢复
- **可测试性**: 模块间解耦，便于单元测试

---

## 2. 消息接收流程

### 2.1 整体流程图

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   微信客户端  │───>│ 消息监听器  │───>│ 消息解析器  │───>│ 消息分发器  │
│ (WeChat.exe)│    │  Monitor   │    │  Parser    │    │ Dispatcher │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                     │
                              ┌──────────────────────────────────────┘
                              ▼
                       ┌─────────────┐
                       │  消息处理器  │
                       │  Handlers  │
                       └─────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  ┌───────────┐        ┌───────────┐        ┌───────────┐
  │ 自动回复   │        │ 消息转发   │        │ 命令处理   │
  │ AutoReply │        │ Forwarder │        │  Command  │
  └───────────┘        └───────────┘        └───────────┘
```

### 2.2 流程说明

1. **消息监听 (Monitor)**
   - 轮询检测微信新消息
   - 从会话列表或聊天窗口获取消息内容
   - 支持私聊和群聊消息

2. **消息解析 (Parser)**
   - 解析消息类型 (文本、图片、语音、视频、文件等)
   - 提取消息元数据 (发送者、接收者、时间、群成员等)
   - 标准化消息格式为 `WeChatMessage` 对象

3. **消息分发 (Dispatcher)**
   - 根据消息类型和规则分发给对应的处理器
   - 支持优先级和过滤条件
   - 支持同步/异步处理

4. **消息处理 (Handler)**
   - 实现具体的业务逻辑
   - 可自定义多个处理器

---

## 3. 核心接口设计

### 3.1 消息模型

```python
# core/models/message.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"           # 文本
    IMAGE = "image"         # 图片
    VOICE = "voice"         # 语音
    VIDEO = "video"         # 视频
    FILE = "file"           # 文件
    CARD = "card"           # 名片
    LINK = "link"           # 链接
    LOCATION = "location"   # 位置
    SYSTEM = "system"       # 系统消息


class ChatType(Enum):
    """聊天类型"""
    PRIVATE = "private"    # 私聊
    GROUP = "group"        # 群聊


@dataclass
class WeChatMessage:
    """微信消息模型"""
    msg_id: str                    # 消息ID
    msg_type: MessageType          # 消息类型
    chat_type: ChatType            # 聊天类型
    content: str                   # 消息内容
    sender_id: str                 # 发送者ID
    sender_name: str                # 发送者名称
    room_id: Optional[str] = None  # 群ID (群聊时)
    room_name: Optional[str] = None # 群名称
    avatar: Optional[str] = None   # 发送者头像
    timestamp: datetime = None    # 时间戳
    raw_data: dict = None          # 原始数据
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.raw_data is None:
            self.raw_data = {}
```

### 3.2 消息解析器接口

```python
# core/interfaces/parser.py

from abc import ABC, abstractmethod
from typing import Optional
from core.models.message import WeChatMessage, MessageType, ChatType


class MessageParser(ABC):
    """
    消息解析器接口
    
    负责将原始微信数据解析为标准化的 WeChatMessage 对象
    """
    
    @abstractmethod
    def parse(self, raw_message: dict) -> Optional[WeChatMessage]:
        """
        解析原始消息
        
        Args:
            raw_message: 从微信获取的原始消息数据
            
        Returns:
            解析后的 WeChatMessage 对象，如果解析失败返回 None
        """
        pass
    
    @abstractmethod
    def detect_message_type(self, content: str, raw_data: dict) -> MessageType:
        """
        检测消息类型
        
        Args:
            content: 消息内容
            raw_data: 原始数据
            
        Returns:
            消息类型
        """
        pass
    
    @abstractmethod
    def extract_sender_info(self, raw_data: dict) -> dict:
        """
        提取发送者信息
        
        Args:
            raw_data: 原始数据
            
        Returns:
            发送者信息字典
        """
        pass
```

### 3.3 消息分发器接口

```python
# core/interfaces/dispatcher.py

from abc import ABC, abstractmethod
from typing import List, Callable, Optional
from core.models.message import WeChatMessage
from core.interfaces.handler import MessageHandler


class MessageDispatcher(ABC):
    """
    消息分发器接口
    
    负责将解析后的消息分发给对应的处理器
    """
    
    @abstractmethod
    def register_handler(
        self, 
        handler: MessageHandler,
        message_types: Optional[List[str]] = None,
        priority: int = 0
    ) -> None:
        """
        注册消息处理器
        
        Args:
            handler: 消息处理器实例
            message_types: 处理的 message_type 列表，None 表示全部
            priority: 优先级，数字越大优先级越高
        """
        pass
    
    @abstractmethod
    def dispatch(self, message: WeChatMessage) -> bool:
        """
        分发消息
        
        Args:
            message: 微信消息对象
            
        Returns:
            是否处理成功
        """
        pass
    
    @abstractmethod
    def unregister_handler(self, handler: MessageHandler) -> None:
        """
        注销消息处理器
        
        Args:
            handler: 消息处理器实例
        """
        pass
```

### 3.4 消息处理器接口

```python
# core/interfaces/handler.py

from abc import ABC, abstractmethod
from typing import Optional, List
from core.models.message import WeChatMessage, MessageType, ChatType


class MessageHandler(ABC):
    """
    消息处理器接口
    
    具体的业务逻辑处理
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """处理器名称"""
        pass
    
    @property
    @abstractmethod
    def supported_types(self) -> Optional[List[MessageType]]:
        """支持的消息类型，None 表示全部"""
        pass
    
    @property
    @abstractmethod
    def supported_chats(self) -> Optional[List[ChatType]]:
        """支持的聊天类型，None 表示全部"""
        pass
    
    @abstractmethod
    async def handle(self, message: WeChatMessage) -> Optional[str]:
        """
        处理消息
        
        Args:
            message: 微信消息对象
            
        Returns:
            处理结果回复消息，如果是 None 表示不回复
        """
        pass
    
    def should_handle(self, message: WeChatMessage) -> bool:
        """
        判断是否应该处理此消息
        
        Args:
            message: 微信消息对象
            
        Returns:
            是否应该处理
        """
        # 检查消息类型
        if self.supported_types and message.msg_type not in self.supported_types:
            return False
        
        # 检查聊天类型
        if self.supported_chats and message.chat_type not in self.supported_chats:
            return False
        
        return True
```

---

## 4. 核心模块实现

### 4.1 消息监听器

```python
# core/monitor.py

import time
import asyncio
from typing import Callable, Optional
from core.interfaces.parser import MessageParser
from core.models.message import WeChatMessage


class WeChatMonitor:
    """
    微信消息监听器
    
    负责监控微信新消息并触发回调
    """
    
    def __init__(
        self,
        parser: MessageParser,
        on_message: Callable[[WeChatMessage], None],
        poll_interval: float = 1.0,
        max_retries: int = 3
    ):
        self.parser = parser
        self.on_message = on_message
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self._running = False
        self._last_msg_id = None
    
    async def start(self):
        """启动监听"""
        self._running = True
        while self._running:
            try:
                messages = self._fetch_new_messages()
                for raw_msg in messages:
                    msg = self.parser.parse(raw_msg)
                    if msg:
                        self.on_message(msg)
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(self.poll_interval * 2)
            
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """停止监听"""
        self._running = False
    
    def _fetch_new_messages(self) -> List[dict]:
        """获取新消息 (需要对接具体实现)"""
        # TODO: 实现从微信获取消息的逻辑
        return []
```

### 4.2 默认消息解析器

```python
# core/parsers/default_parser.py

import re
from typing import Optional
from core.interfaces.parser import MessageParser
from core.models.message import WeChatMessage, MessageType, ChatType
from core.exceptions import WeChatError


class DefaultMessageParser(MessageParser):
    """默认消息解析器实现"""
    
    def parse(self, raw_message: dict) -> Optional[WeChatMessage]:
        try:
            msg_type = self.detect_message_type(
                raw_message.get('content', ''),
                raw_message
            )
            
            sender_info = self.extract_sender_info(raw_message)
            
            return WeChatMessage(
                msg_id=raw_message.get('msg_id', ''),
                msg_type=msg_type,
                chat_type=ChatType.PRIVATE if not raw_message.get('room_id') else ChatType.GROUP,
                content=raw_message.get('content', ''),
                sender_id=sender_info.get('id', ''),
                sender_name=sender_info.get('name', ''),
                room_id=raw_message.get('room_id'),
                room_name=raw_message.get('room_name'),
                avatar=sender_info.get('avatar'),
                raw_data=raw_message
            )
        except Exception as e:
            raise WeChatError(f"Message parse failed: {e}")
    
    def detect_message_type(self, content: str, raw_data: dict) -> MessageType:
        # 检测图片
        if raw_data.get('type') == 2 or '[图片]' in content:
            return MessageType.IMAGE
        # 检测语音
        if raw_data.get('type') == 3 or '[语音]' in content:
            return MessageType.VOICE
        # 检测视频
        if raw_data.get('type') == 4 or '[视频]' in content:
            return MessageType.VIDEO
        # 检测文件
        if raw_data.get('type') == 6 or '[文件]' in content:
            return MessageType.FILE
        # 检测名片
        if raw_data.get('type') == 42 or '[名片]' in content:
            return MessageType.CARD
        # 检测位置
        if raw_data.get('type') == 48 or '[位置]' in content:
            return MessageType.LOCATION
        # 检测链接
        if raw_data.get('type') == 49 or 'http' in content.lower():
            return MessageType.LINK
        # 检测系统消息
        if raw_data.get('type') == 10000:
            return MessageType.SYSTEM
        
        return MessageType.TEXT
    
    def extract_sender_info(self, raw_data: dict) -> dict:
        return {
            'id': raw_data.get('from_user', ''),
            'name': raw_data.get('from_nickname', ''),
            'avatar': raw_data.get('from_avatar', '')
        }
```

### 4.3 消息分发器实现

```python
# core/dispatcher.py

import asyncio
from typing import List, Optional, Dict
from core.interfaces.dispatcher import MessageDispatcher
from core.interfaces.handler import MessageHandler
from core.models.message import WeChatMessage


class SimpleMessageDispatcher(MessageDispatcher):
    """简单消息分发器"""
    
    def __init__(self):
        self._handlers: List[Dict] = []
    
    def register_handler(
        self,
        handler: MessageHandler,
        message_types: Optional[List[str]] = None,
        priority: int = 0
    ) -> None:
        # 移除已存在的同名处理器
        self.unregister_handler(handler)
        
        self._handlers.append({
            'handler': handler,
            'types': message_types,
            'priority': priority
        })
        
        # 按优先级排序
        self._handlers.sort(key=lambda x: x['priority'], reverse=True)
    
    def dispatch(self, message: WeChatMessage) -> bool:
        """同步分发消息到所有匹配的处理器"""
        for handler_dict in self._handlers:
            handler = handler_dict['handler']
            
            # 检查是否应该处理
            if not handler.should_handle(message):
                continue
            
            # 检查消息类型过滤
            types = handler_dict.get('types')
            if types and message.msg_type.value not in types:
                continue
            
            try:
                # 同步执行处理
                result = asyncio.run(handler.handle(message))
                if result:
                    # 如果有回复，可以选择立即返回或继续处理
                    pass
            except Exception as e:
                print(f"Handler {handler.name} error: {e}")
        
        return True
    
    def unregister_handler(self, handler: MessageHandler) -> None:
        self._handlers = [
            h for h in self._handlers 
            if h['handler'].name != handler.name
        ]
```

---

## 5. 使用示例

```python
# main.py

import asyncio
from core.monitor import WeChatMonitor
from core.parsers.default_parser import DefaultMessageParser
from core.dispatcher import SimpleMessageDispatcher
from core.handlers.auto_reply import AutoReplyHandler
from core.handlers.command import CommandHandler
from core.models.message import MessageType, ChatType


async def main():
    # 1. 创建解析器
    parser = DefaultMessageParser()
    
    # 2. 创建分发器
    dispatcher = SimpleMessageDispatcher()
    
    # 3. 注册处理器
    auto_reply = AutoReplyHandler()
    dispatcher.register_handler(
        auto_reply,
        message_types=['text'],
        priority=10
    )
    
    command = CommandHandler()
    dispatcher.register_handler(
        command,
        message_types=['text'],
        priority=20
    )
    
    # 4. 定义消息处理回调
    def on_message(message):
        print(f"收到消息: {message.content}")
        dispatcher.dispatch(message)
    
    # 5. 启动监听
    monitor = WeChatMonitor(
        parser=parser,
        on_message=on_message,
        poll_interval=1.0
    )
    
    print("微信消息监听已启动...")
    await monitor.start()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. 扩展点

| 扩展点 | 接口 | 说明 |
|--------|------|------|
| 消息解析 | `MessageParser` | 支持自定义解析逻辑 |
| 消息处理 | `MessageHandler` | 添加新的业务处理器 |
| 消息存储 | `MessageStore` | 持久化消息 (可选) |
| 消息过滤 | `Filter` | 自定义过滤规则 |

---

## 7. 总结

- **模块化**: 各组件通过接口解耦，便于测试和替换
- **可扩展**: 新增消息类型只需实现对应 Handler
- **异步化**: 支持异步处理，提高响应速度
- **错误处理**: 完善的异常体系，支持错误恢复