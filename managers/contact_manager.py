# -*- coding: utf-8 -*-
"""
联系人管理模块
版本: v1.0.0
功能: 实现微信联系人管理功能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AddFriendStatus(Enum):
    """添加好友状态"""
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ContactInfo:
    """联系人信息数据结构"""
    user_id: str
    nickname: str
    remark: str = ""
    avatar: str = ""
    tags: List[str] = field(default_factory=list)
    region: str = ""
    signature: str = ""
    is_friend: bool = True
    add_time: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'nickname': self.nickname,
            'remark': self.remark,
            'avatar': self.avatar,
            'tags': self.tags,
            'region': self.region,
            'signature': self.signature,
            'is_friend': self.is_friend,
            'add_time': self.add_time.isoformat(),
            'extra': self.extra
        }


@dataclass
class AddFriendResult:
    """添加好友结果"""
    success: bool
    status: AddFriendStatus
    message: str = ""
    request_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class ContactManagerInterface(ABC):
    """联系人管理器接口基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化联系人管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.is_initialized = False
        self.manager_type = self.__class__.__name__
        
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化联系人管理器
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def get_contact_list(self) -> List[ContactInfo]:
        """
        获取联系人列表
        
        Returns:
            List[ContactInfo]: 联系人列表
        """
        pass
    
    @abstractmethod
    def search_contact(self, keyword: str) -> List[ContactInfo]:
        """
        搜索联系人
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[ContactInfo]: 搜索结果
        """
        pass
    
    @abstractmethod
    def add_friend(self, user_id: str, message: str = '') -> AddFriendResult:
        """
        添加好友
        
        Args:
            user_id: 用户ID
            message: 验证消息
            
        Returns:
            AddFriendResult: 添加结果
        """
        pass
    
    @abstractmethod
    def accept_friend_request(self, request_id: str) -> bool:
        """
        接受好友请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def delete_friend(self, user_id: str) -> bool:
        """
        删除好友
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def set_remark(self, user_id: str, remark: str) -> bool:
        """
        设置备注
        
        Args:
            user_id: 用户ID
            remark: 备注名
            
        Returns:
            bool: 是否成功
        """
        pass
    
    def get_manager_info(self) -> Dict[str, Any]:
        """
        获取管理器信息
        
        Returns:
            Dict: 管理器信息字典
        """
        return {
            "manager_type": self.manager_type,
            "is_initialized": self.is_initialized,
            "config": self.config
        }
