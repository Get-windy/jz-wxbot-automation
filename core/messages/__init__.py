# -*- coding: utf-8 -*-
"""
微信消息接收模块
版本: v1.0.0

功能:
- 消息监听器 - 监听微信消息事件
- 消息解析器 - 解析不同类型消息
- 消息队列 - 异步消息处理队列
- 消息处理器 - 消息分发和处理逻辑

依赖:
- core.message_reader_interface: 消息数据结构定义
- core.message_handler: 消息队列和处理器
"""

import os
import sys
import asyncio
import threading
import time
import queue
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
import hashlib
import json

# 导入现有模块
from core.message_reader_interface import (
    MessageReaderInterface,
    WeChatMessage,
    MessageType,
    ChatType,
    ReadResult
)
from core.message_handler import MessageHandler, MessageQueue as CoreMessageQueue

logger = logging.getLogger(__name__)


# ==================== 消息类型定义 ====================

class WeChatMessageType(Enum):
    """微信消息类型"""
    TEXT = 1           # 文本
    IMAGE = 2          # 图片
    VOICE = 3          # 语音
    VIDEO = 4          # 视频
    CARD = 42          # 名片
    FILE = 6           # 文件
    LINK = 49          # 链接
    EMOTION = 47       # 表情
    LOCATION = 48      # 位置
    REDPACKET = 49     # 红包
    SYSTEM = 10000     # 系统消息
    MINIPROGRAM = 33   # 小程序


class WeChatChatType(Enum):
    """微信聊天类型"""
    PRIVATE = 1        # 私聊
    GROUP = 2          # 群聊
    OFFICIAL = 3       # 公众号


class MessageSource(Enum):
    """消息来源"""
    CHAT_LIST = "chat_list"      # 会话列表
    CHAT_WINDOW = "chat_window"   # 聊天窗口
    NOTIFICATION = "notification" # 通知
    SYSTEM = "system"             # 系统


@dataclass
class RawWeChatMessage:
    """原始微信消息"""
    msg_id: str
    msg_type: WeChatMessageType
    from_user: str
    from_nickname: str
    from_remark: str = ""
    to_user: str = ""
    room_id: str = ""
    room_name: str = ""
    content: str = ""
    raw_content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    source: MessageSource = MessageSource.CHAT_LIST
    extra: Dict[str, Any] = field(default_factory=dict)


# ==================== 消息解析器 ====================

class MessageParser:
    """消息解析器
    
    负责解析不同类型的微信消息
    """
    
    # 消息类型映射
    MSG_TYPE_MAP = {
        1: MessageType.TEXT,
        2: MessageType.IMAGE,
        3: MessageType.VOICE,
        4: MessageType.VIDEO,
        6: MessageType.FILE,
        42: MessageType.TEXT,   # 名片转文本
        47: MessageType.EMOTION,
        48: MessageType.TEXT,   # 位置转文本
        49: MessageType.LINK,
        33: MessageType.LINK,  # 小程序转链接
        10000: MessageType.TEXT,
    }
    
    def __init__(self, my_user_id: str = "self", my_nickname: str = "我"):
        """
        初始化解析器
        
        Args:
            my_user_id: 我的用户ID
            my_nickname: 我的昵称
        """
        self.my_user_id = my_user_id
        self.my_nickname = my_nickname
    
    def parse(self, raw_message: RawWeChatMessage) -> WeChatMessage:
        """
        解析原始消息
        
        Args:
            raw_message: 原始微信消息
            
        Returns:
            WeChatMessage: 结构化消息对象
        """
        # 解析聊天类型
        chat_type = self._parse_chat_type(raw_message)
        
        # 解析消息类型
        message_type = self._parse_message_type(raw_message)
        
        # 解析@信息
        is_mentioned, at_users = self._parse_mentions(
            raw_message.content, 
            chat_type
        )
        
        # 检查是否@我
        is_at_me = self._check_at_me(raw_message.content)
        
        return WeChatMessage(
            message_id=raw_message.msg_id,
            sender_id=raw_message.from_user,
            sender_name=raw_message.from_remark or raw_message.from_nickname,
            chat_id=raw_message.room_id or raw_message.from_user,
            chat_name=raw_message.room_name or raw_message.from_nickname,
            chat_type=chat_type,
            content=raw_message.content,
            message_type=message_type,
            timestamp=raw_message.timestamp,
            is_mentioned=is_mentioned or is_at_me,
            at_user_ids=at_users,
            extra=self._build_extra(raw_message)
        )
    
    def _parse_chat_type(self, msg: RawWeChatMessage) -> ChatType:
        """解析聊天类型"""
        if msg.room_id:
            return ChatType.GROUP
        return ChatType.PRIVATE
    
    def _parse_message_type(self, msg: RawWeChatMessage) -> MessageType:
        """解析消息类型"""
        return self.MSG_TYPE_MAP.get(msg.msg_type.value, MessageType.TEXT)
    
    def _parse_mentions(self, content: str, chat_type: ChatType) -> tuple:
        """解析@提及"""
        import re
        
        if chat_type != ChatType.GROUP:
            return False, []
        
        # 匹配@xxx
        at_pattern = re.compile(r'@(\S+?)(?:\s|$)')
        mentions = at_pattern.findall(content)
        
        is_mentioned = len(mentions) > 0
        return is_mentioned, mentions
    
    def _check_at_me(self, content: str) -> bool:
        """检查是否@我"""
        return f'@{self.my_nickname}' in content
    
    def _build_extra(self, msg: RawWeChatMessage) -> Dict[str, Any]:
        """构建额外信息"""
        return {
            "raw_content": msg.raw_content,
            "source": msg.source.value,
            "extra": msg.extra,
            "to_user": msg.to_user,
        }
    
    def parse_text_message(self, content: str, raw: Dict = None) -> str:
        """解析文本消息内容"""
        if not raw:
            return content
        
        # 处理不同类型的消息内容
        msg_type = raw.get('type', 1)
        
        if msg_type == 1:  # 文本
            return content
        elif msg_type == 2:  # 图片
            return f"[图片]{content}"
        elif msg_type == 3:  # 语音
            return f"[语音]{content}"
        elif msg_type == 4:  # 视频
            return f"[视频]{content}"
        elif msg_type == 6:  # 文件
            return f"[文件]{content}"
        
        return content


# ==================== 消息队列 ====================

class AsyncMessageQueue:
    """异步消息队列
    
    支持异步添加和获取消息
    """
    
    def __init__(self, max_size: int = 1000):
        """
        初始化队列
        
        Args:
            max_size: 最大队列长度
        """
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._max_size = max_size
    
    async def put(self, message: WeChatMessage):
        """添加消息"""
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            # 队列满，丢弃最旧的消息
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(message)
            except:
                pass
    
    async def get(self, timeout: float = None) -> Optional[WeChatMessage]:
        """获取消息"""
        try:
            if timeout:
                return await asyncio.wait_for(
                    self._queue.get(), 
                    timeout=timeout
                )
            return await self._queue.get()
        except asyncio.TimeoutError:
            return None
    
    async def get_batch(self, count: int = 10, timeout: float = 1.0) -> List[WeChatMessage]:
        """批量获取消息"""
        messages = []
        for _ in range(count):
            try:
                msg = await asyncio.wait_for(
                    self._queue.get(), 
                    timeout=timeout
                )
                messages.append(msg)
            except asyncio.TimeoutError:
                break
        return messages
    
    def qsize(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """检查是否为空"""
        return self._queue.empty()
    
    def full(self) -> bool:
        """检查是否满"""
        return self._queue.full()
    
    def clear(self):
        """清空队列"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except:
                break


class SyncMessageQueue:
    """同步消息队列
    
    线程安全的同步队列
    """
    
    def __init__(self, max_size: int = 1000):
        self._queue = queue.Queue(maxsize=max_size)
        self._max_size = max_size
    
    def put(self, message: WeChatMessage, block: bool = True, timeout: float = None):
        """添加消息"""
        self._queue.put(message, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: float = None) -> WeChatMessage:
        """获取消息"""
        return self._queue.get(block=block, timeout=timeout)
    
    def get_nowait(self) -> WeChatMessage:
        """非阻塞获取"""
        return self._queue.get_nowait()
    
    def put_nowait(self, message: WeChatMessage):
        """非阻塞添加"""
        self._queue.put_nowait(message)
    
    def qsize(self) -> int:
        return self._queue.qsize()
    
    def empty(self) -> bool:
        return self._queue.empty()


# ==================== 消息监听器 ====================

class MessageListener:
    """消息监听器
    
    监听微信消息事件
    """
    
    def __init__(
        self,
        parser: MessageParser = None,
        on_message: Callable[[WeChatMessage], None] = None,
        poll_interval: float = 1.0
    ):
        """
        初始化监听器
        
        Args:
            parser: 消息解析器
            on_message: 消息回调
            poll_interval: 轮询间隔(秒)
        """
        self.parser = parser or MessageParser()
        self.on_message = on_message
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._known_messages: set = set()
        self._message_queue = SyncMessageQueue()
        self._callbacks: List[Callable] = []
        
    def start(self):
        """启动监听"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True
        )
        self._thread.start()
        logger.info("消息监听器已启动")
    
    def stop(self):
        """停止监听"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("消息监听器已停止")
    
    def _listen_loop(self):
        """监听循环"""
        while self._running:
            try:
                raw_messages = self._fetch_messages()
                for raw in raw_messages:
                    msg_id = raw.get('msg_id', '')
                    
                    # 跳过已处理的消息
                    if msg_id in self._known_messages:
                        continue
                    
                    # 解析消息
                    raw_msg = self._convert_to_raw(raw)
                    if raw_msg:
                        self._known_messages.add(msg_id)
                        
                        # 解析为结构化消息
                        message = self.parser.parse(raw_msg)
                        
                        # 添加到队列
                        self._message_queue.put_nowait(message)
                        
                        # 触发回调
                        self._notify(message)
                        
            except Exception as e:
                logger.error(f"监听循环错误: {e}")
            
            time.sleep(self.poll_interval)
    
    def _fetch_messages(self) -> List[Dict]:
        """获取消息
        
        需要对接 pywechat 的消息获取功能
        """
        # TODO: 实现从 pywechat 获取消息
        # 目前返回空列表，需要集成 pywechat 的消息监听
        return []
    
    def _convert_to_raw(self, data: Dict) -> Optional[RawWeChatMessage]:
        """转换为原始消息"""
        try:
            return RawWeChatMessage(
                msg_id=data.get('msg_id', ''),
                msg_type=WeChatMessageType(data.get('type', 1)),
                from_user=data.get('from_user', ''),
                from_nickname=data.get('from_nickname', ''),
                from_remark=data.get('from_remark', ''),
                to_user=data.get('to_user', ''),
                room_id=data.get('room_id', ''),
                room_name=data.get('room_name', ''),
                content=data.get('content', ''),
                raw_content=data.get('raw_content', ''),
                timestamp=datetime.fromtimestamp(
                    data.get('timestamp', time.time())
                ) if 'timestamp' in data else datetime.now(),
                source=MessageSource(data.get('source', 'chat_list')),
                extra=data.get('extra', {})
            )
        except Exception as e:
            logger.error(f"转换消息失败: {e}")
            return None
    
    def _notify(self, message: WeChatMessage):
        """通知回调"""
        # 调用on_message
        if self.on_message:
            try:
                self.on_message(message)
            except Exception as e:
                logger.error(f"消息回调错误: {e}")
        
        # 调用注册的回调
        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"回调错误: {e}")
    
    def register_callback(self, callback: Callable):
        """注册回调"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """注销回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_message(self, timeout: float = None) -> Optional[WeChatMessage]:
        """获取消息"""
        try:
            return self._message_queue.get(timeout=timeout)
        except queue.Empty:
            return None


# ==================== 消息处理器 ====================

class MessageDispatcher:
    """消息分发器
    
    负责将消息分发给不同的处理器
    """
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._default_handler: Optional[Callable] = None
        self._priority_handlers: List[tuple] = []
    
    def register(self, msg_type: str, handler: Callable[[WeChatMessage], Any]):
        """
        注册处理器
        
        Args:
            msg_type: 消息类型 (text/image/file/link/video/voice)
            handler: 处理函数
        """
        self._handlers[msg_type] = handler
    
    def register_default(self, handler: Callable[[WeChatMessage], Any]):
        """注册默认处理器"""
        self._default_handler = handler
    
    def register_priority(self, name: str, handler: Callable, priority: int = 0):
        """注册优先级处理器"""
        self._priority_handlers.append((name, handler, priority))
        self._priority_handlers.sort(key=lambda x: x[2], reverse=True)
    
    async def dispatch(self, message: WeChatMessage) -> Any:
        """
        分发消息
        
        Args:
            message: 微信消息
            
        Returns:
            处理结果
        """
        # 先尝试优先级处理器
        for name, handler, _ in self._priority_handlers:
            try:
                result = await self._call_handler(handler, message)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"优先级处理器 {name} 错误: {e}")
        
        # 按类型分发
        msg_type = message.message_type.value
        if msg_type in self._handlers:
            return await self._call_handler(self._handlers[msg_type], message)
        
        # 默认处理器
        if self._default_handler:
            return await self._call_handler(self._default_handler, message)
        
        return None
    
    async def _call_handler(self, handler: Callable, message: WeChatMessage) -> Any:
        """调用处理器"""
        if asyncio.iscoroutinefunction(handler):
            return await handler(message)
        else:
            return handler(message)


class MessageProcessor:
    """消息处理器
    
    统一管理消息监听、解析、分发
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 初始化组件
        self.parser = MessageParser(
            my_user_id=self.config.get('my_user_id', 'self'),
            my_nickname=self.config.get('my_nickname', '我')
        )
        
        self.queue = AsyncMessageQueue(
            max_size=self.config.get('queue_size', 1000)
        )
        
        self.listener = MessageListener(
            parser=self.parser,
            poll_interval=self.config.get('poll_interval', 1.0)
        )
        
        self.dispatcher = MessageDispatcher()
        
        self._running = False
        self._process_task: Optional[asyncio.Task] = None
    
    def on_message(self, callback: Callable[[WeChatMessage], None]):
        """设置消息回调"""
        self.listener.on_message = callback
        self.listener.register_callback(callback)
    
    async def start(self):
        """启动处理器"""
        if self._running:
            return
        
        self._running = True
        self.listener.start()
        
        # 启动消息处理协程
        self._process_task = asyncio.create_task(self._process_loop())
        
        logger.info("消息处理器已启动")
    
    async def stop(self):
        """停止处理器"""
        self._running = False
        self.listener.stop()
        
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        
        logger.info("消息处理器已停止")
    
    async def _process_loop(self):
        """消息处理循环"""
        while self._running:
            try:
                # 批量获取消息
                messages = await self.queue.get_batch(
                    count=10,
                    timeout=1.0
                )
                
                for message in messages:
                    await self.dispatcher.dispatch(message)
                    
            except Exception as e:
                logger.error(f"处理循环错误: {e}")
                await asyncio.sleep(1)
    
    async def put_message(self, message: WeChatMessage):
        """手动添加消息"""
        await self.queue.put(message)
    
    def register_handler(self, msg_type: str, handler: Callable):
        """注册消息处理器"""
        self.dispatcher.register(msg_type, handler)
    
    def register_priority_handler(self, name: str, handler: Callable, priority: int):
        """注册优先级处理器"""
        self.dispatcher.register_priority(name, handler, priority)


# ==================== 消息处理器实现 ====================

class TextMessageHandler:
    """文本消息处理器"""
    
    def __init__(self, keywords: Dict[str, str] = None):
        self.keywords = keywords or {}
    
    async def handle(self, message: WeChatMessage) -> Optional[str]:
        """处理文本消息"""
        content = message.content.lower()
        
        # 关键词匹配
        for keyword, response in self.keywords.items():
            if keyword.lower() in content:
                return response
        
        return None


class AtMessageHandler:
    """@消息处理器"""
    
    def __init__(self, bot_name: str = "我"):
        self.bot_name = bot_name
    
    async def handle(self, message: WeChatMessage) -> Optional[str]:
        """处理@消息"""
        if not message.is_mentioned:
            return None
        
        # 移除@信息，获取实际内容
        content = message.content.replace(f'@{self.bot_name}', '').strip()
        
        if not content:
            return "有什么可以帮你的？"
        
        # TODO: 调用 AI 处理
        return f"收到: {content}"


class CommandMessageHandler:
    """命令消息处理器"""
    
    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self._register_default_commands()
    
    def _register_default_commands(self):
        """注册默认命令"""
        self.commands = {
            '/help': self._cmd_help,
            '/status': self._cmd_status,
            '/ping': self._cmd_ping,
        }
    
    async def _cmd_ping(self, message: WeChatMessage) -> str:
        """ping命令"""
        return 'pong'
    
    async def handle(self, message: WeChatMessage) -> Optional[str]:
        """处理命令消息"""
        content = message.content.strip()
        
        if not content.startswith('/') and not content.startswith('!'):
            return None
        
        # 提取命令 (保持前缀)
        parts = content[1:].split()
        cmd = '/' + (parts[0] if parts else '')  # Add back the slash
        
        if cmd in self.commands:
            return await self.commands[cmd](message)
        
        return f"未知命令: {cmd}"
    
    async def _cmd_help(self, message: WeChatMessage) -> str:
        return """可用命令:
/help - 显示帮助
/status - 状态信息
/ping - 测试"""
    
    async def _cmd_status(self, message: WeChatMessage) -> str:
        return "状态: 在线 | 版本: 1.0.0"


# ==================== 使用示例 ====================

async def example_basic():
    """基本使用示例"""
    
    # 创建处理器
    processor = MessageProcessor({
        'my_nickname': '小助手',
        'queue_size': 1000,
        'poll_interval': 1.0
    })
    
    # 注册消息回调
    def on_message(msg: WeChatMessage):
        print(f"[{msg.chat_name}] {msg.sender_name}: {msg.content}")
    
    processor.on_message(on_message)
    
    # 注册处理器
    processor.register_handler('text', TextMessageHandler({
        'hello': '你好！',
        '天气': '今天天气很好！',
    }).handle)
    
    processor.register_priority_handler(
        'at_handler',
        AtMessageHandler('小助手').handle,
        priority=100
    )
    
    # 启动
    await processor.start()
    
    # 模拟接收消息
    test_msg = WeChatMessage(
        message_id='test_001',
        sender_id='user_123',
        sender_name='测试用户',
        chat_id='chat_001',
        chat_name='测试群',
        chat_type=ChatType.GROUP,
        content='@小助手 你好',
        message_type=MessageType.TEXT,
        is_mentioned=True
    )
    await processor.put_message(test_msg)
    
    # 运行一段时间
    await asyncio.sleep(10)
    
    # 停止
    await processor.stop()


async def example_with_queue():
    """使用队列示例"""
    
    queue = AsyncMessageQueue(max_size=100)
    
    # 生产者
    async def producer():
        for i in range(10):
            msg = WeChatMessage(
                message_id=f'msg_{i}',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content=f'消息 {i}',
                message_type=MessageType.TEXT
            )
            await queue.put(msg)
            await asyncio.sleep(0.1)
    
    # 消费者
    async def consumer():
        while True:
            msg = await queue.get(timeout=5)
            if msg:
                print(f"收到: {msg.content}")
            else:
                break
    
    await asyncio.gather(producer(), consumer())


def example_sync_queue():
    """同步队列示例"""
    
    queue = SyncMessageQueue(max_size=100)
    
    # 生产者线程
    def producer():
        for i in range(10):
            msg = WeChatMessage(
                message_id=f'msg_{i}',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content=f'消息 {i}',
                message_type=MessageType.TEXT
            )
            queue.put(msg)
            time.sleep(0.1)
    
    # 消费者线程
    def consumer():
        for _ in range(10):
            msg = queue.get(timeout=5)
            if msg:
                print(f"收到: {msg.content}")
    
    t1 = threading.Thread(target=producer)
    t2 = threading.Thread(target=consumer)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()


# ==================== 主入口 ====================

if __name__ == '__main__':
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行示例
    asyncio.run(example_basic())