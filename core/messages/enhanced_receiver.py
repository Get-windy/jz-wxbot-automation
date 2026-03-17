# -*- coding: utf-8 -*-
"""
增强版消息接收器
版本: v1.0.0
功能: 提供消息过滤、消息解析增强、智能路由
"""

import re
import time
import threading
import logging
from typing import Callable, List, Optional, Dict, Any, Pattern
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from core.message_reader_interface import (
    WeChatMessage,
    MessageType,
    ChatType
)

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class MessageFilter:
    """消息过滤器"""
    name: str
    pattern: Optional[Pattern] = None
    message_types: Optional[List[MessageType]] = None
    chat_types: Optional[List[ChatType]] = None
    sender_ids: Optional[List[str]] = None
    chat_ids: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    priority: MessagePriority = MessagePriority.NORMAL
    enabled: bool = True


@dataclass
class FilteredMessage:
    """过滤后的消息"""
    message: WeChatMessage
    matched_filters: List[str] = field(default_factory=list)
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageFilterEngine:
    """消息过滤引擎"""
    
    def __init__(self):
        self.filters: Dict[str, MessageFilter] = {}
        self._lock = threading.Lock()
        
    def add_filter(self, message_filter: MessageFilter) -> bool:
        """添加消息过滤器"""
        with self._lock:
            if message_filter.name in self.filters:
                logger.warning(f"过滤器已存在: {message_filter.name}")
                return False
            self.filters[message_filter.name] = message_filter
            logger.info(f"添加消息过滤器: {message_filter.name}")
            return True
    
    def remove_filter(self, name: str) -> bool:
        """移除消息过滤器"""
        with self._lock:
            if name not in self.filters:
                return False
            del self.filters[name]
            logger.info(f"移除消息过滤器: {name}")
            return True
    
    def apply_filters(self, message: WeChatMessage) -> FilteredMessage:
        """应用所有过滤器到消息"""
        matched_filters = []
        highest_priority = MessagePriority.NORMAL
        
        with self._lock:
            for name, f in self.filters.items():
                if not f.enabled:
                    continue
                    
                if self._match_filter(message, f):
                    matched_filters.append(name)
                    if f.priority.value > highest_priority.value:
                        highest_priority = f.priority
        
        return FilteredMessage(
            message=message,
            matched_filters=matched_filters,
            priority=highest_priority
        )
    
    def _match_filter(self, message: WeChatMessage, f: MessageFilter) -> bool:
        """检查消息是否匹配过滤器"""
        # 检查消息类型
        if f.message_types and message.message_type not in f.message_types:
            return False
        
        # 检查聊天类型
        if f.chat_types and message.chat_type not in f.chat_types:
            return False
        
        # 检查发送者ID
        if f.sender_ids and message.sender_id not in f.sender_ids:
            return False
        
        # 检查聊天ID
        if f.chat_ids and message.chat_id not in f.chat_ids:
            return False
        
        # 检查正则模式
        if f.pattern and not f.pattern.search(message.content):
            return False
        
        # 检查关键词
        if f.keywords:
            content_lower = message.content.lower()
            if not any(kw.lower() in content_lower for kw in f.keywords):
                return False
        
        # 检查排除关键词
        if f.exclude_keywords:
            content_lower = message.content.lower()
            if any(kw.lower() in content_lower for kw in f.exclude_keywords):
                return False
        
        return True


class MessageParser:
    """增强版消息解析器"""
    
    # 常见消息模式
    PATTERNS = {
        # @提及模式
        'at_mention': re.compile(r'@([^\s@]+)'),
        # URL模式
        'url': re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+'),
        # 手机号模式
        'phone': re.compile(r'1[3-9]\d{9}'),
        # 邮箱模式
        'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        # 红包模式
        'red_packet': re.compile(r'\[红包\]'),
        # 表情模式
        'emotion': re.compile(r'\[[^\[\]]+\]'),
        # 命令模式
        'command': re.compile(r'^[/#!](\w+)(?:\s+(.*))?$'),
    }
    
    @classmethod
    def parse_at_mentions(cls, content: str) -> List[str]:
        """解析@提及"""
        matches = cls.PATTERNS['at_mention'].findall(content)
        return list(set(matches))
    
    @classmethod
    def parse_urls(cls, content: str) -> List[str]:
        """解析URL"""
        matches = cls.PATTERNS['url'].findall(content)
        return matches
    
    @classmethod
    def parse_phone_numbers(cls, content: str) -> List[str]:
        """解析手机号"""
        matches = cls.PATTERNS['phone'].findall(content)
        return matches
    
    @classmethod
    def parse_emails(cls, content: str) -> List[str]:
        """解析邮箱"""
        matches = cls.PATTERNS['email'].findall(content)
        return matches
    
    @classmethod
    def parse_command(cls, content: str) -> Optional[Dict[str, str]]:
        """解析命令"""
        match = cls.PATTERNS['command'].match(content.strip())
        if match:
            return {
                'command': match.group(1).lower(),
                'args': match.group(2) or ''
            }
        return None
    
    @classmethod
    def has_red_packet(cls, content: str) -> bool:
        """检查是否包含红包"""
        return bool(cls.PATTERNS['red_packet'].search(content))
    
    @classmethod
    def parse_emotions(cls, content: str) -> List[str]:
        """解析表情"""
        matches = cls.PATTERNS['emotion'].findall(content)
        return matches
    
    @classmethod
    def extract_metadata(cls, message: WeChatMessage) -> Dict[str, Any]:
        """提取消息元数据"""
        metadata = {
            'at_mentions': cls.parse_at_mentions(message.content),
            'urls': cls.parse_urls(message.content),
            'phone_numbers': cls.parse_phone_numbers(message.content),
            'emails': cls.parse_emails(message.content),
            'has_red_packet': cls.has_red_packet(message.content),
            'emotions': cls.parse_emotions(message.content),
            'command': cls.parse_command(message.content),
        }
        return metadata


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        self.routes: Dict[str, List[Callable]] = {}
        self.default_handler: Optional[Callable] = None
        self._lock = threading.Lock()
    
    def register_route(self, pattern: str, handler: Callable) -> bool:
        """注册路由"""
        with self._lock:
            if pattern not in self.routes:
                self.routes[pattern] = []
            self.routes[pattern].append(handler)
            logger.info(f"注册消息路由: {pattern}")
            return True
    
    def unregister_route(self, pattern: str, handler: Optional[Callable] = None) -> bool:
        """取消注册路由"""
        with self._lock:
            if pattern not in self.routes:
                return False
            if handler:
                try:
                    self.routes[pattern].remove(handler)
                except ValueError:
                    return False
            else:
                del self.routes[pattern]
            return True
    
    def set_default_handler(self, handler: Callable):
        """设置默认处理器"""
        self.default_handler = handler
    
    def route(self, filtered_message: FilteredMessage) -> Optional[Callable]:
        """路由消息到处理器"""
        message = filtered_message.message
        
        # 检查命令
        if filtered_message.metadata.get('command'):
            cmd = filtered_message.metadata['command']['command']
            route_key = f"command:{cmd}"
            if route_key in self.routes:
                return self.routes[route_key][0]
        
        # 检查@提及
        if filtered_message.metadata.get('at_mentions'):
            if 'mention' in self.routes:
                return self.routes['mention'][0]
        
        # 检查关键词路由
        content_lower = message.content.lower()
        for pattern, handlers in self.routes.items():
            if pattern.lower() in content_lower:
                return handlers[0]
        
        # 返回默认处理器
        return self.default_handler


class EnhancedMessageReceiver:
    """增强版消息接收器"""
    
    def __init__(self, max_queue_size: int = 1000):
        self.filter_engine = MessageFilterEngine()
        self.parser = MessageParser()
        self.router = MessageRouter()
        
        self._message_queue: deque = deque(maxlen=max_queue_size)
        self._priority_queue: deque = deque(maxlen=100)
        self._lock = threading.Lock()
        
        self._handlers: List[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def add_filter(self, message_filter: MessageFilter) -> bool:
        """添加过滤器"""
        return self.filter_engine.add_filter(message_filter)
    
    def remove_filter(self, name: str) -> bool:
        """移除过滤器"""
        return self.filter_engine.remove_filter(name)
    
    def register_handler(self, handler: Callable):
        """注册消息处理器"""
        self._handlers.append(handler)
    
    def unregister_handler(self, handler: Callable):
        """取消注册消息处理器"""
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    def process_message(self, message: WeChatMessage) -> FilteredMessage:
        """处理消息"""
        # 1. 应用过滤器
        filtered = self.filter_engine.apply_filters(message)
        
        # 2. 解析元数据
        filtered.metadata = self.parser.extract_metadata(message)
        
        # 3. 入队
        with self._lock:
            if filtered.priority == MessagePriority.URGENT:
                self._priority_queue.append(filtered)
            else:
                self._message_queue.append(filtered)
        
        # 4. 路由到处理器
        handler = self.router.route(filtered)
        if handler:
            try:
                handler(filtered)
            except Exception as e:
                logger.error(f"消息处理器执行失败: {e}")
        
        # 5. 通知所有处理器
        for h in self._handlers:
            try:
                h(filtered)
            except Exception as e:
                logger.error(f"消息处理器执行失败: {e}")
        
        return filtered
    
    def get_message(self, priority_first: bool = True) -> Optional[FilteredMessage]:
        """获取消息"""
        with self._lock:
            if priority_first and self._priority_queue:
                return self._priority_queue.popleft()
            if self._message_queue:
                return self._message_queue.popleft()
            if self._priority_queue:
                return self._priority_queue.popleft()
        return None
    
    def get_message_count(self) -> Dict[str, int]:
        """获取消息队列状态"""
        with self._lock:
            return {
                'normal': len(self._message_queue),
                'priority': len(self._priority_queue),
                'total': len(self._message_queue) + len(self._priority_queue)
            }


# 预定义过滤器
def create_default_filters() -> List[MessageFilter]:
    """创建默认过滤器集合"""
    return [
        # 高优先级：命令消息
        MessageFilter(
            name="commands",
            pattern=re.compile(r'^[/#!]'),
            priority=MessagePriority.HIGH,
            enabled=True
        ),
        # 高优先级：@提及消息
        MessageFilter(
            name="mentions",
            keywords=["@"],
            priority=MessagePriority.HIGH,
            enabled=True
        ),
        # 正常优先级：红包消息
        MessageFilter(
            name="red_packets",
            keywords=["[红包]"],
            priority=MessagePriority.NORMAL,
            enabled=True
        ),
        # 低优先级：系统消息
        MessageFilter(
            name="system",
            message_types=[MessageType.SYSTEM],
            priority=MessagePriority.LOW,
            enabled=True
        ),
    ]