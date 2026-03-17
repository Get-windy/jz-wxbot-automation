# OpenClaw 集成设计文档

> 版本: 1.0  
> 日期: 2026-03-16  
> 状态: 设计完成

---

## 1. 概述

本文档描述 jz-wxbot-automation 如何与 OpenClaw 平台集成，实现微信消息与 AI 助手的双向通信。

### 设计目标

- **消息转发**: 微信消息 → OpenClaw → AI 处理
- **回复返回**: AI 响应 → OpenClaw → 微信发送
- **会话管理**: 跨平台会话状态保持
- **安全隔离**: 敏感操作权限控制

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        微信客户端                                │
│                    (WeChat.exe / WeCom)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    jz-wxbot-automation                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │  消息监听器   │──▶│  消息解析器   │──▶│  消息分发器   │        │
│  │   Monitor   │   │   Parser    │   │  Dispatcher  │        │
│  └──────────────┘   └──────────────┘   └──────┬───────┘        │
│                                               │                │
│                           ┌───────────────────┼───────────────┐ │
│                           ▼                   ▼               ▼ │
│                    ┌──────────────┐   ┌──────────────┐   ┌─────┴────┐ │
│                    │ OpenClaw    │   │  消息处理器   │   │  MCP    │ │
│                    │ 转发器      │   │  Handlers   │   │ Client  │ │
│                    │ Forwarder  │   │              │   │         │ │
│                    └──────┬─────┘   └──────────────┘   └─────────┘ │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OpenClaw 平台                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   MCP Server │◀──│  Agent      │◀──│  会话管理     │        │
│  │              │   │  (AI)       │   │  Session    │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 消息流

#### 微信 → OpenClaw

```
1. Monitor 监听微信新消息
2. Parser 解析消息为 WeChatMessage
3. Dispatcher 分发给 OpenClawForwarder
4. MCP Client 发送到 OpenClaw MCP Server
5. OpenClaw 触发 Agent 处理
6. Agent 返回处理结果
7. MCP Client 接收响应
8. WeChatSender 发送回复到微信
```

#### OpenClaw → 微信

```
1. OpenClaw Agent 决定发送消息
2. MCP Server 调用发送接口
3. MCP Client 接收发送请求
4. WeChatSender 调用微信发送API
5. 微信发送成功/失败回调
6. 结果返回给 OpenClaw
```

---

## 3. MCP 接口规范

### 3.1 服务端接口 (OpenClaw 提供)

```python
# openclaw_mcp/types.py

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageSource(BaseModel):
    """消息来源"""
    platform: str = "wechat"           # 平台: wechat/wecom
    user_id: str                        # 用户ID
    user_name: str                      # 用户昵称
    room_id: Optional[str] = None       # 群ID (群聊时)
    room_name: Optional[str] = None     # 群名称
    msg_id: str                         # 消息ID


class MessageContent(BaseModel):
    """消息内容"""
    msg_type: str                       # 消息类型: text/image/voice/video/file
    content: str                        # 文本内容或文件路径
    raw_data: Optional[Dict] = None     # 原始数据


class WeChatMessage(BaseModel):
    """完整微信消息"""
    source: MessageSource
    content: MessageContent
    timestamp: datetime


class AgentRequest(BaseModel):
    """Agent请求"""
    message: WeChatMessage
    session_id: str                     # 会话ID
    context: Optional[Dict] = None      # 额外上下文
    timeout: int = 60                   # 超时秒数


class AgentResponse(BaseModel):
    """Agent响应"""
    session_id: str
    reply: Optional[str] = None         # 回复内容
    actions: Optional[List[Dict]] = None # 执行的动作
    error: Optional[str] = None          # 错误信息


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    target_type: str                    # private/group
    target_id: str                      # 好友ID或群ID
    content: str                        # 消息内容
    msg_type: str = "text"              # 消息类型


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool
    msg_id: Optional[str] = None
    error: Optional[str] = None
```

### 3.2 MCP 工具定义

```python
# openclaw_mcp/tools.py

from typing import List
from mcp.types import Tool, ToolCall


# 可用工具列表
AVAILABLE_TOOLS = [
    # 消息相关
    Tool(
        name="wechat_receive_message",
        description="接收微信消息并转发给AI处理",
        inputSchema={
            "type": "object",
            "properties": {
                "message": {"type": "object", "description": "微信消息对象"}
            },
            "required": ["message"]
        }
    ),
    
    Tool(
        name="wechat_send_message",
        description="发送消息到微信",
        inputSchema={
            "type": "object",
            "properties": {
                "target_type": {"type": "string", "enum": ["private", "group"]},
                "target_id": {"type": "string"},
                "content": {"type": "string"},
                "msg_type": {"type": "string", "default": "text"}
            },
            "required": ["target_type", "target_id", "content"]
        }
    ),
    
    Tool(
        name="wechat_send_image",
        description="发送图片到微信",
        inputSchema={
            "type": "object",
            "properties": {
                "target_type": {"type": "string"},
                "target_id": {"type": "string"},
                "image_path": {"type": "string"}
            },
            "required": ["target_type", "target_id", "image_path"]
        }
    ),
    
    # 会话相关
    Tool(
        name="wechat_create_session",
        description="创建新会话",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "context": {"type": "object"}
            },
            "required": ["user_id"]
        }
    ),
    
    Tool(
        name="wechat_get_session",
        description="获取会话历史",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "limit": {"type": "number", "default": 20}
            },
            "required": ["session_id"]
        }
    ),
    
    Tool(
        name="wechat_close_session",
        description="关闭会话",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"}
            },
            "required": ["session_id"]
        }
    ),
    
    # 用户相关
    Tool(
        name="wechat_get_user_info",
        description="获取用户信息",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        }
    ),
    
    Tool(
        name="wechat_get_friends",
        description="获取好友列表",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "number", "default": 100}
            }
        }
    ),
]
```

---

## 4. OpenClaw MCP Server 实现

### 4.1 Server 主类

```python
# openclaw_mcp/server.py

import asyncio
import json
from typing import Dict, Optional, Callable
from datetime import datetime

from .types import (
    WeChatMessage, AgentRequest, AgentResponse,
    SendMessageRequest, SendMessageResponse
)
from .tools import AVAILABLE_TOOLS


class OpenClawMCPServer:
    """
    OpenClaw MCP Server for WeChat
    
    负责:
    1. 接收微信消息
    2. 转发给 OpenClaw Agent
    3. 处理 Agent 响应
    """
    
    def __init__(
        self,
        openclaw_url: str = "http://localhost:3000",
        mcp_port: int = 3100,
        wechat_sender: Optional[Callable] = None
    ):
        self.openclaw_url = openclaw_url
        self.mcp_port = mcp_port
        self.wechat_sender = wechat_sender
        self._sessions: Dict[str, Dict] = {}
        self._running = False
    
    async def start(self):
        """启动 MCP Server"""
        self._running = True
        # 启动 HTTP/WebSocket 服务器
        await self._start_server()
    
    async def stop(self):
        """停止 MCP Server"""
        self._running = False
    
    async def handle_message(self, message: WeChatMessage) -> AgentResponse:
        """
        处理微信消息
        
        Args:
            message: 微信消息
            
        Returns:
            Agent响应
        """
        # 1. 创建或获取会话
        session_id = self._get_or_create_session(
            message.source.user_id,
            message.source.room_id
        )
        
        # 2. 构建请求
        request = AgentRequest(
            message=message,
            session_id=session_id,
            context={"platform": "wechat"}
        )
        
        # 3. 发送到 OpenClaw
        try:
            response = await self._call_agent(request)
            
            # 4. 如果有回复，发送到微信
            if response.reply and self.wechat_sender:
                send_result = await self.wechat_sender.send(
                    target_type="group" if message.source.room_id else "private",
                    target_id=message.source.room_id or message.source.user_id,
                    content=response.reply
                )
            
            return response
            
        except Exception as e:
            return AgentResponse(
                session_id=session_id,
                error=str(e)
            )
    
    async def send_wechat_message(
        self,
        target_type: str,
        target_id: str,
        content: str,
        msg_type: str = "text"
    ) -> SendMessageResponse:
        """发送微信消息 (被 MCP 工具调用)"""
        if not self.wechat_sender:
            return SendMessageResponse(
                success=False,
                error="WeChat sender not configured"
            )
        
        try:
            result = await self.wechat_sender.send(
                target_type=target_type,
                target_id=target_id,
                content=content,
                msg_type=msg_type
            )
            return SendMessageResponse(
                success=result.get("success", False),
                msg_id=result.get("msg_id")
            )
        except Exception as e:
            return SendMessageResponse(
                success=False,
                error=str(e)
            )
    
    def _get_or_create_session(self, user_id: str, room_id: Optional[str]) -> str:
        """获取或创建会话"""
        # 使用 user_id + room_id 作为会话键
        session_key = f"{user_id}:{room_id or 'private'}"
        
        if session_key not in self._sessions:
            self._sessions[session_key] = {
                "session_id": session_key,
                "user_id": user_id,
                "room_id": room_id,
                "created_at": datetime.now(),
                "messages": []
            }
        
        return session_key
    
    async def _call_agent(self, request: AgentRequest) -> AgentResponse:
        """调用 OpenClaw Agent"""
        # TODO: 实现实际的 HTTP/WebSocket 调用
        # 这里是一个模拟实现
        return AgentResponse(
            session_id=request.session_id,
            reply="这是 AI 的自动回复",
            actions=[]
        )
```

---

## 5. 消息转发器实现

### 5.1 OpenClaw 转发器

```python
# core/handlers/openclaw_forwarder.py

import asyncio
from typing import Optional
from core.interfaces.handler import MessageHandler
from core.models.message import WeChatMessage, MessageType, ChatType
from core.exceptions import WeChatError
from openclaw_mcp.server import OpenClawMCPServer


class OpenClawForwarder(MessageHandler):
    """
    OpenClaw 消息转发器
    
    将微信消息转发到 OpenClaw 平台处理
    """
    
    def __init__(self, mcp_server: OpenClawMCPServer):
        self.mcp_server = mcp_server
    
    @property
    def name(self) -> str:
        return "openclaw_forwarder"
    
    @property
    def supported_types(self) -> Optional[list]:
        # 支持所有消息类型
        return None
    
    @property
    def supported_chats(self) -> Optional[list]:
        # 支持私聊和群聊
        return None
    
    async def handle(self, message: WeChatMessage) -> Optional[str]:
        """处理消息并返回回复"""
        try:
            # 转换消息格式
            oc_message = self._convert_message(message)
            
            # 发送到 OpenClaw
            response = await self.mcp_server.handle_message(oc_message)
            
            return response.reply
            
        except Exception as e:
            raise WeChatError(f"OpenClaw forward failed: {e}")
    
    def _convert_message(self, message: WeChatMessage) -> WeChatMessage:
        """转换为 OpenClaw 消息格式"""
        from openclaw_mcp.types import MessageSource, MessageContent
        
        return WeChatMessage(
            source=MessageSource(
                platform="wechat",
                user_id=message.sender_id,
                user_name=message.sender_name,
                room_id=message.room_id,
                room_name=message.room_name,
                msg_id=message.msg_id
            ),
            content=MessageContent(
                msg_type=message.msg_type.value,
                content=message.content,
                raw_data=message.raw_data
            ),
            timestamp=message.timestamp
        )
    
    def should_handle(self, message: WeChatMessage) -> bool:
        """判断是否处理"""
        # 排除系统消息
        if message.msg_type == MessageType.SYSTEM:
            return False
        
        # 排除自己发送的消息
        if message.sender_id == "self":
            return False
        
        return True
```

---

## 6. 配置与使用

### 6.1 配置文件

```yaml
# config/openclaw.yaml

openclaw:
  # OpenClaw 平台地址
  url: "http://localhost:3000"
  
  # MCP 服务配置
  mcp:
    host: "0.0.0.0"
    port: 3100
    path: "/mcp"
  
  # 认证
  auth:
    enabled: true
    api_key: "your-api-key"
  
  # 会话配置
  session:
    timeout: 300          # 会话超时(秒)
    max_history: 50       # 最大历史消息数
  
  # 消息转发配置
  forward:
    enabled: true
    # 转发哪些类型的消息
    message_types:
      - text
      - image
      - voice
    # 排除的用户ID
    exclude_users: []
    # 只转发指定群
    include_rooms: []

wechat:
  # 微信配置
  sender:
    retry_count: 3
    retry_delay: 1
```

### 6.2 启动集成

```python
# main.py

import asyncio
from core.monitor import WeChatMonitor
from core.parsers.default_parser import DefaultMessageParser
from core.dispatcher import SimpleMessageDispatcher
from openclaw_mcp.server import OpenClawMCPServer
from core.handlers.openclaw_forwarder import OpenClawForwarder


async def main():
    # 1. 创建 OpenClaw MCP Server
    mcp_server = OpenClawMCPServer(
        openclaw_url="http://localhost:3000",
        mcp_port=3100,
        wechat_sender=wechat_sender  # 微信发送器
    )
    
    # 2. 创建转发器
    forwarder = OpenClawForwarder(mcp_server)
    
    # 3. 创建分发器并注册
    dispatcher = SimpleMessageDispatcher()
    dispatcher.register_handler(forwarder, priority=100)
    
    # 4. 启动 MCP Server
    await mcp_server.start()
    
    # 5. 启动消息监听
    parser = DefaultMessageParser()
    monitor = WeChatMonitor(
        parser=parser,
        on_message=lambda msg: dispatcher.dispatch(msg)
    )
    
    print("OpenClaw 集成已启动...")
    await monitor.start()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. 安全性

### 7.1 权限控制

- API Key 认证
- 白名单用户/群
- 消息内容过滤
- 敏感操作确认

### 7.2 速率限制

- 每用户消息频率限制
- 每日消息配额
- API 调用频率控制

---

## 8. 总结

- **架构**: MCP Client/Server 模式
- **消息流**: 微信 ↔ jz-wxbot ↔ OpenClaw ↔ AI Agent
- **核心接口**: 消息收发、会话管理、用户查询
- **安全**: API Key + 速率限制