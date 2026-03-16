# -*- coding: utf-8 -*-
"""
消息读取接口
版本: v1.0.0
功能: 定义消息读取器的通用接口，支持接收微信消息
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    LINK = "link"
    VIDEO = "video"
    VOICE = "voice"
    EMOTION = "emotion"


class ChatType(Enum):
    """聊天类型枚举"""
    PRIVATE = "private"
    GROUP = "group"
    OFFICIAL = "official"


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


class MessageReaderInterface(ABC):
    """消息读取器接口基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化消息读取器
        
        Args:
            config: 读取器配置字典
        """
        self.config = config or {}
        self.is_initialized = False
        self.reader_type = self.__class__.__name__
        self._message_callback: Optional[Callable[[WeChatMessage], None]] = None
        self._listening = False
        
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化读取器
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def start_listening(self, callback: Callable[[WeChatMessage], None]) -> bool:
        """
        启动消息监听
        
        Args:
            callback: 消息接收回调函数
            
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def stop_listening(self) -> bool:
        """
        停止消息监听
        
        Returns:
            bool: 停止是否成功
        """
        pass
    
    @abstractmethod
    def get_unread_messages(self, count: int = 10) -> List[WeChatMessage]:
        """
        获取未读消息
        
        Args:
            count: 获取消息数量
            
        Returns:
            List[WeChatMessage]: 未读消息列表
        """
        pass
    
    def is_listening(self) -> bool:
        """
        检查是否正在监听
        
        Returns:
            bool: 是否正在监听
        """
        return self._listening
    
    def get_reader_info(self) -> Dict[str, Any]:
        """
        获取读取器信息
        
        Returns:
            Dict: 读取器信息字典
        """
        return {
            "reader_type": self.reader_type,
            "is_initialized": self.is_initialized,
            "is_listening": self._listening,
            "config": self.config
        }


class MessageReaderFactory:
    """消息读取器工厂类"""
    
    _readers = {}
    
    @classmethod
    def register_reader(cls, reader_type: str, reader_class: type):
        """
        注册消息读取器
        
        Args:
            reader_type: 读取器类型名称
            reader_class: 读取器类
        """
        cls._readers[reader_type] = reader_class
        logger.info(f"已注册消息读取器: {reader_type}")
    
    @classmethod
    def create_reader(cls, reader_type: str, config: Dict[str, Any] = None) -> Optional[MessageReaderInterface]:
        """
        创建消息读取器实例
        
        Args:
            reader_type: 读取器类型
            config: 配置字典
            
        Returns:
            MessageReaderInterface: 读取器实例，如果类型不存在则返回None
        """
        if reader_type not in cls._readers:
            logger.error(f"未知的读取器类型: {reader_type}")
            return None
        
        try:
            reader_class = cls._readers[reader_type]
            return reader_class(config)
        except Exception as e:
            logger.error(f"创建读取器失败: {e}")
            return None
    
    @classmethod
    def get_available_readers(cls) -> List[str]:
        """
        获取可用的读取器类型列表
        
        Returns:
            List[str]: 读取器类型列表
        """
        return list(cls._readers.keys())


# 读取结果枚举
class ReadResult:
    """读取结果常量"""
    SUCCESS = "success"
    FAILED = "failed"
    PROCESS_NOT_FOUND = "process_not_found"
    WINDOW_NOT_FOUND = "window_not_found"
    INITIALIZATION_FAILED = "initialization_failed"
    NOT_LISTENING = "not_listening"
