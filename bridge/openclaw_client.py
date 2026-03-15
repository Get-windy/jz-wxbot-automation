# -*- coding: utf-8 -*-
"""
OpenClaw 客户端 - 微信桥接核心模块
版本: v1.0.0
功能: 与 OpenClaw 平台通信，实现消息路由和命令执行
"""

import asyncio
import json
import logging
import time
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    LINK = "link"
    VIDEO = "video"
    EMOTION = "emotion"


class ChatType(Enum):
    """聊天类型枚举"""
    PRIVATE = "private"
    GROUP = "group"
    OFFICIAL = "official"  # 公众号


@dataclass
class WeChatMessage:
    """微信消息数据结构"""
    message_id: str
    sender_id: str
    sender_name: str
    chat_id: str
    chat_name: str
    chat_type: ChatType
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)
    is_mentioned: bool = False
    at_user_ids: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'message_id': self.message_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'chat_id': self.chat_id,
            'chat_name': self.chat_name,
            'chat_type': self.chat_type.value,
            'content': self.content,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp.isoformat(),
            'is_mentioned': self.is_mentioned,
            'at_user_ids': self.at_user_ids,
            'extra': self.extra
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeChatMessage':
        """从字典创建"""
        return cls(
            message_id=data.get('message_id', ''),
            sender_id=data.get('sender_id', ''),
            sender_name=data.get('sender_name', ''),
            chat_id=data.get('chat_id', ''),
            chat_name=data.get('chat_name', ''),
            chat_type=ChatType(data.get('chat_type', 'private')),
            content=data.get('content', ''),
            message_type=MessageType(data.get('message_type', 'text')),
            timestamp=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now(),
            is_mentioned=data.get('is_mentioned', False),
            at_user_ids=data.get('at_user_ids', []),
            extra=data.get('extra', {})
        )


@dataclass
class OpenClawResponse:
    """OpenClaw 响应数据结构"""
    success: bool
    should_reply: bool = False
    content: str = ""
    reply_type: str = "text"
    context: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def from_json(cls, json_str: str) -> 'OpenClawResponse':
        """从 JSON 创建"""
        try:
            data = json.loads(json_str)
            return cls(
                success=data.get('success', True),
                should_reply=data.get('should_reply', False),
                content=data.get('content', ''),
                reply_type=data.get('reply_type', 'text'),
                context=data.get('context', {}),
                error=data.get('error')
            )
        except Exception as e:
            logger.error(f"解析 OpenClaw 响应失败: {e}")
            return cls(success=False, error=str(e))


class OpenClawClient:
    """
    OpenClaw 客户端
    
    负责:
    1. 与 OpenClaw Gateway 建立 WebSocket 连接
    2. 发送消息到 OpenClaw 进行 AI 处理
    3. 接收 OpenClaw 的响应和命令
    4. 管理会话和状态
    """
    
    def __init__(
        self,
        gateway_url: str = "ws://127.0.0.1:3100",
        agent_id: str = "wxbot-agent",
        session_prefix: str = "wechat"
    ):
        """
        初始化 OpenClaw 客户端
        
        Args:
            gateway_url: OpenClaw Gateway 地址
            agent_id: Agent ID
            session_prefix: Session ID 前缀
        """
        self.gateway_url = gateway_url
        self.agent_id = agent_id
        self.session_prefix = session_prefix
        
        # WebSocket 连接
        self.ws = None
        self.connected = False
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        
        # 命令处理器
        self.command_handlers: Dict[str, Callable] = {}
        
        # 会话上下文缓存
        self.session_contexts: Dict[str, Dict] = {}
        
        # 重连配置
        self.reconnect = True
        self.reconnect_interval = 5
        self.max_reconnect_attempts = 10
        
    async def connect(self) -> bool:
        """
        连接到 OpenClaw Gateway
        
        Returns:
            bool: 是否连接成功
        """
        try:
            import websockets
            
            logger.info(f"连接 OpenClaw Gateway: {self.gateway_url}")
            
            self.ws = await websockets.connect(
                self.gateway_url,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.connected = True
            logger.info("OpenClaw Gateway 连接成功")
            
            # 注册 Agent
            await self._register_agent()
            
            return True
            
        except Exception as e:
            logger.error(f"连接 OpenClaw Gateway 失败: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.ws:
            await self.ws.close()
            self.ws = None
        self.connected = False
        logger.info("已断开 OpenClaw Gateway 连接")
    
    async def _register_agent(self):
        """注册 Agent"""
        registration = {
            'type': 'register',
            'agent_id': self.agent_id,
            'capabilities': [
                'message.receive',
                'message.send',
                'group.manage',
                'contact.manage',
                'moments.manage',
                'mass.send'
            ],
            'metadata': {
                'name': 'WeChat Bot Agent',
                'version': '1.0.0',
                'platform': 'wechat'
            }
        }
        
        await self.ws.send(json.dumps(registration))
        logger.info(f"Agent {self.agent_id} 注册请求已发送")
    
    async def send_message(
        self,
        session_id: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> OpenClawResponse:
        """
        发送消息到 OpenClaw 进行处理
        
        Args:
            session_id: 会话 ID (通常是 chat_id)
            message: 消息内容
            context: 上下文信息
            
        Returns:
            OpenClawResponse: OpenClaw 的响应
        """
        try:
            # 构建完整 session ID
            full_session_id = f"{self.session_prefix}:{session_id}"
            
            # 合并上下文
            merged_context = {
                **self.session_contexts.get(session_id, {}),
                **(context or {}),
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # 构建消息
            payload = {
                'type': 'message',
                'session_id': full_session_id,
                'agent_id': self.agent_id,
                'content': message,
                'context': merged_context
            }
            
            if not self.connected:
                await self.connect()
            
            # 发送消息
            await self.ws.send(json.dumps(payload))
            logger.debug(f"消息已发送到 OpenClaw: {session_id}")
            
            # 等待响应
            response = await asyncio.wait_for(
                self.ws.recv(),
                timeout=30.0
            )
            
            return OpenClawResponse.from_json(response)
            
        except asyncio.TimeoutError:
            logger.error("等待 OpenClaw 响应超时")
            return OpenClawResponse(
                success=False,
                error="Response timeout"
            )
        except Exception as e:
            logger.error(f"发送消息到 OpenClaw 失败: {e}")
            return OpenClawResponse(
                success=False,
                error=str(e)
            )
    
    async def send_wechat_message(self, message: WeChatMessage) -> OpenClawResponse:
        """
        发送微信消息到 OpenClaw
        
        Args:
            message: 微信消息对象
            
        Returns:
            OpenClawResponse: OpenClaw 的响应
        """
        context = {
            'sender_name': message.sender_name,
            'chat_name': message.chat_name,
            'chat_type': message.chat_type.value,
            'is_mentioned': message.is_mentioned,
            'message_type': message.message_type.value
        }
        
        return await self.send_message(
            session_id=message.chat_id,
            message=message.content,
            context=context
        )
    
    def register_command_handler(self, command: str, handler: Callable):
        """
        注册命令处理器
        
        Args:
            command: 命令名称
            handler: 处理函数
        """
        self.command_handlers[command] = handler
        logger.info(f"已注册命令处理器: {command}")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self.message_handlers[message_type] = handler
        logger.info(f"已注册消息处理器: {message_type}")
    
    async def execute_command(self, command: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行命令
        
        Args:
            command: 命令名称
            args: 命令参数
            
        Returns:
            Dict: 执行结果
        """
        handler = self.command_handlers.get(command)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(args or {})
                else:
                    return handler(args or {})
            except Exception as e:
                logger.error(f"执行命令 {command} 失败: {e}")
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    async def update_session_context(self, session_id: str, context: Dict[str, Any]):
        """
        更新会话上下文
        
        Args:
            session_id: 会话 ID
            context: 上下文信息
        """
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = {}
        
        self.session_contexts[session_id].update(context)
    
    async def listen(self):
        """
        监听 OpenClaw 消息
        
        持续接收来自 OpenClaw 的消息和命令
        """
        if not self.connected:
            await self.connect()
        
        reconnect_attempts = 0
        
        while self.reconnect or reconnect_attempts < self.max_reconnect_attempts:
            try:
                async for message in self.ws:
                    try:
                        data = json.loads(message)
                        await self._handle_message(data)
                    except json.JSONDecodeError:
                        logger.error(f"无效的 JSON 消息: {message}")
                    except Exception as e:
                        logger.error(f"处理消息失败: {e}")
                        
            except Exception as e:
                logger.error(f"WebSocket 连接错误: {e}")
                self.connected = False
                
                if self.reconnect:
                    reconnect_attempts += 1
                    logger.info(f"尝试重连 ({reconnect_attempts}/{self.max_reconnect_attempts})...")
                    await asyncio.sleep(self.reconnect_interval)
                    await self.connect()
                else:
                    break
    
    async def _handle_message(self, data: Dict[str, Any]):
        """
        处理收到的消息
        
        Args:
            data: 消息数据
        """
        msg_type = data.get('type')
        
        if msg_type == 'command':
            # 命令消息
            command = data.get('command')
            args = data.get('args', {})
            result = await self.execute_command(command, args)
            
            # 发送结果
            await self.ws.send(json.dumps({
                'type': 'command_result',
                'command': command,
                'result': result
            }))
            
        elif msg_type == 'message':
            # 普通消息 - 调用处理器
            handler = self.message_handlers.get('default')
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
                    
        elif msg_type == 'ping':
            # 心跳
            await self.ws.send(json.dumps({'type': 'pong'}))
            
        else:
            logger.debug(f"未处理的消息类型: {msg_type}")


class OpenClawClientSync:
    """
    OpenClaw 客户端同步封装
    
    为不使用异步代码的场景提供同步接口
    """
    
    def __init__(self, gateway_url: str = "ws://127.0.0.1:3100", agent_id: str = "wxbot-agent"):
        self.gateway_url = gateway_url
        self.agent_id = agent_id
        self._async_client = OpenClawClient(gateway_url, agent_id)
        self._loop = None
    
    def _get_loop(self):
        """获取事件循环"""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def send_message(self, session_id: str, message: str, context: Dict = None) -> OpenClawResponse:
        """同步发送消息"""
        loop = self._get_loop()
        return loop.run_until_complete(
            self._async_client.send_message(session_id, message, context)
        )


# 单例模式
_instance: Optional[OpenClawClient] = None


def get_openclaw_client(
    gateway_url: str = "ws://127.0.0.1:3100",
    agent_id: str = "wxbot-agent"
) -> OpenClawClient:
    """
    获取 OpenClaw 客户端单例
    
    Args:
        gateway_url: Gateway URL
        agent_id: Agent ID
        
    Returns:
        OpenClawClient: 客户端实例
    """
    global _instance
    if _instance is None:
        _instance = OpenClawClient(gateway_url, agent_id)
    return _instance


if __name__ == "__main__":
    # 测试代码
    import sys
    
    async def test_client():
        client = OpenClawClient()
        
        # 测试连接
        if await client.connect():
            print("✅ 连接成功")
            
            # 测试发送消息
            response = await client.send_message(
                session_id="test_session",
                message="Hello OpenClaw!",
                context={'test': True}
            )
            
            print(f"响应: {response}")
            
            await client.disconnect()
        else:
            print("❌ 连接失败")
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_client())