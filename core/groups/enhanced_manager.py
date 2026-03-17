# -*- coding: utf-8 -*-
"""
群消息管理增强模块
版本: v1.0.0
功能: 智能@识别、群消息统计、群成员管理
"""

import re
import time
import threading
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class MemberRole(Enum):
    """成员角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    UNKNOWN = "unknown"


@dataclass
class GroupMember:
    """群成员"""
    user_id: str
    nickname: str
    display_name: Optional[str] = None
    role: MemberRole = MemberRole.MEMBER
    join_time: Optional[datetime] = None
    last_active: Optional[datetime] = None
    message_count: int = 0
    at_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GroupStats:
    """群统计"""
    group_id: str
    group_name: str
    member_count: int = 0
    total_messages: int = 0
    today_messages: int = 0
    active_members: int = 0
    last_active: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AtMention:
    """@提及信息"""
    mentioned_user_id: str
    mentioned_name: str
    mentioner_id: str
    mentioner_name: str
    chat_id: str
    message_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_bot: bool = False
    needs_response: bool = True


class AtMentionDetector:
    """智能@提及检测器"""
    
    # @提及模式
    PATTERNS = {
        # 标准@模式: @昵称
        'standard': re.compile(r'@([^\s@]{1,20})'),
        # 全角@模式: ＠昵称
        'fullwidth': re.compile(r'＠([^\s＠]{1,20})'),
        # 带[]模式: [@昵称]
        'bracket': re.compile(r'\[@([^\]]+)\]'),
        # 所有人模式: @所有人 @all
        'all': re.compile(r'@(所有人|all)', re.IGNORECASE),
    }
    
    def __init__(self, bot_names: List[str] = None):
        """
        初始化检测器
        
        Args:
            bot_names: 机器人名称列表
        """
        self.bot_names = set(name.lower() for name in (bot_names or []))
        self._nickname_to_id: Dict[str, str] = {}
    
    def update_nicknames(self, nickname_map: Dict[str, str]):
        """更新昵称映射"""
        self._nickname_to_id = {k.lower(): v for k, v in nickname_map.items()}
    
    def detect(self, 
               content: str,
               sender_id: str,
               sender_name: str,
               chat_id: str,
               message_id: str) -> List[AtMention]:
        """检测@提及"""
        mentions = []
        
        # 检测所有@模式
        detected_names = set()
        
        for pattern_name, pattern in self.PATTERNS.items():
            if pattern_name == 'all':
                # @所有人
                if pattern.search(content):
                    # 创建一个特殊的@所有人提及
                    mention = AtMention(
                        mentioned_user_id='all',
                        mentioned_name='所有人',
                        mentioner_id=sender_id,
                        mentioner_name=sender_name,
                        chat_id=chat_id,
                        message_id=message_id,
                        content=content,
                        is_bot=False,
                        needs_response=True
                    )
                    mentions.append(mention)
            else:
                for match in pattern.finditer(content):
                    name = match.group(1).strip()
                    if name and name not in detected_names:
                        detected_names.add(name)
                        
                        # 查找用户ID
                        user_id = self._nickname_to_id.get(name.lower(), name)
                        
                        # 检查是否@机器人
                        is_bot = name.lower() in self.bot_names
                        
                        mention = AtMention(
                            mentioned_user_id=user_id,
                            mentioned_name=name,
                            mentioner_id=sender_id,
                            mentioner_name=sender_name,
                            chat_id=chat_id,
                            message_id=message_id,
                            content=content,
                            is_bot=is_bot,
                            needs_response=is_bot
                        )
                        mentions.append(mention)
        
        return mentions
    
    def is_bot_mentioned(self, content: str) -> bool:
        """检查是否@了机器人"""
        content_lower = content.lower()
        for bot_name in self.bot_names:
            if f'@{bot_name}' in content_lower or f'＠{bot_name}' in content_lower:
                return True
        return False
    
    def extract_mentioned_names(self, content: str) -> List[str]:
        """提取所有被@的名称"""
        names = set()
        for pattern in self.PATTERNS.values():
            for match in pattern.finditer(content):
                name = match.group(1).strip()
                if name:
                    names.add(name)
        return list(names)


class GroupStatistics:
    """群消息统计器"""
    
    def __init__(self):
        self._group_stats: Dict[str, GroupStats] = {}
        self._member_stats: Dict[str, Dict[str, GroupMember]] = defaultdict(dict)
        self._daily_messages: Dict[str, Counter] = defaultdict(Counter)
        self._hourly_messages: Dict[str, Counter] = defaultdict(Counter)
        
        self._lock = threading.Lock()
    
    def record_message(self,
                       group_id: str,
                       group_name: str,
                       sender_id: str,
                       sender_name: str,
                       timestamp: datetime = None):
        """记录消息"""
        timestamp = timestamp or datetime.now()
        
        with self._lock:
            # 更新群统计
            if group_id not in self._group_stats:
                self._group_stats[group_id] = GroupStats(
                    group_id=group_id,
                    group_name=group_name
                )
            
            stats = self._group_stats[group_id]
            stats.total_messages += 1
            stats.today_messages += 1
            stats.last_active = timestamp
            stats.updated_at = timestamp
            
            # 更新成员统计
            if sender_id not in self._member_stats[group_id]:
                self._member_stats[group_id][sender_id] = GroupMember(
                    user_id=sender_id,
                    nickname=sender_name
                )
            
            member = self._member_stats[group_id][sender_id]
            member.message_count += 1
            member.last_active = timestamp
            if member.nickname != sender_name:
                member.nickname = sender_name
            
            # 更新时间统计
            today = timestamp.strftime('%Y-%m-%d')
            hour = timestamp.hour
            
            self._daily_messages[group_id][today] += 1
            self._hourly_messages[group_id][hour] += 1
    
    def record_at(self,
                  group_id: str,
                  sender_id: str):
        """记录@提及"""
        with self._lock:
            if group_id in self._member_stats:
                if sender_id in self._member_stats[group_id]:
                    self._member_stats[group_id][sender_id].at_count += 1
    
    def get_group_stats(self, group_id: str) -> Optional[GroupStats]:
        """获取群统计"""
        with self._lock:
            return self._group_stats.get(group_id)
    
    def get_member_stats(self, 
                         group_id: str,
                         user_id: str = None) -> Optional[GroupMember]:
        """获取成员统计"""
        with self._lock:
            if group_id not in self._member_stats:
                return None
            if user_id:
                return self._member_stats[group_id].get(user_id)
            return None
    
    def get_top_members(self,
                        group_id: str,
                        by: str = 'messages',
                        limit: int = 10) -> List[GroupMember]:
        """
        获取活跃成员排行
        
        Args:
            group_id: 群ID
            by: 排序方式 ('messages' 或 'at_count')
            limit: 返回数量
        """
        with self._lock:
            if group_id not in self._member_stats:
                return []
            
            members = list(self._member_stats[group_id].values())
            
            if by == 'messages':
                members.sort(key=lambda m: m.message_count, reverse=True)
            elif by == 'at_count':
                members.sort(key=lambda m: m.at_count, reverse=True)
            
            return members[:limit]
    
    def get_daily_stats(self,
                        group_id: str,
                        days: int = 7) -> Dict[str, int]:
        """获取每日消息统计"""
        with self._lock:
            if group_id not in self._daily_messages:
                return {}
            
            result = {}
            today = datetime.now()
            
            for i in range(days):
                date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                result[date] = self._daily_messages[group_id].get(date, 0)
            
            return result
    
    def get_hourly_stats(self,
                         group_id: str) -> Dict[int, int]:
        """获取每小时消息统计"""
        with self._lock:
            if group_id not in self._hourly_messages:
                return {}
            return dict(self._hourly_messages[group_id])
    
    def reset_daily(self):
        """重置每日统计"""
        with self._lock:
            for stats in self._group_stats.values():
                stats.today_messages = 0
    
    def cleanup(self, days: int = 30):
        """清理旧数据"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._lock:
            # 清理每日消息统计
            for group_id in list(self._daily_messages.keys()):
                dates_to_remove = [
                    date for date in self._daily_messages[group_id]
                    if datetime.strptime(date, '%Y-%m-%d') < cutoff
                ]
                for date in dates_to_remove:
                    del self._daily_messages[group_id][date]


class GroupMemberManager:
    """群成员管理器"""
    
    def __init__(self):
        self._members: Dict[str, Dict[str, GroupMember]] = defaultdict(dict)
        self._name_index: Dict[str, Dict[str, str]] = defaultdict(dict)  # 群ID -> {昵称 -> 用户ID}
        self._lock = threading.Lock()
    
    def add_member(self,
                   group_id: str,
                   user_id: str,
                   nickname: str,
                   role: MemberRole = MemberRole.MEMBER,
                   display_name: str = None) -> bool:
        """添加群成员"""
        with self._lock:
            if user_id in self._members[group_id]:
                # 更新现有成员
                member = self._members[group_id][user_id]
                member.nickname = nickname
                if display_name:
                    member.display_name = display_name
                member.role = role
            else:
                # 添加新成员
                member = GroupMember(
                    user_id=user_id,
                    nickname=nickname,
                    display_name=display_name,
                    role=role,
                    join_time=datetime.now()
                )
                self._members[group_id][user_id] = member
            
            # 更新名称索引
            self._name_index[group_id][nickname.lower()] = user_id
            if display_name:
                self._name_index[group_id][display_name.lower()] = user_id
            
            return True
    
    def remove_member(self, group_id: str, user_id: str) -> bool:
        """移除群成员"""
        with self._lock:
            if user_id in self._members[group_id]:
                member = self._members[group_id][user_id]
                
                # 从名称索引中移除
                if member.nickname:
                    self._name_index[group_id].pop(member.nickname.lower(), None)
                if member.display_name:
                    self._name_index[group_id].pop(member.display_name.lower(), None)
                
                # 从成员列表中移除
                del self._members[group_id][user_id]
                return True
            return False
    
    def get_member(self, group_id: str, user_id: str) -> Optional[GroupMember]:
        """获取群成员"""
        with self._lock:
            return self._members[group_id].get(user_id)
    
    def get_member_by_name(self, group_id: str, name: str) -> Optional[GroupMember]:
        """通过昵称获取群成员"""
        with self._lock:
            user_id = self._name_index[group_id].get(name.lower())
            if user_id:
                return self._members[group_id].get(user_id)
            return None
    
    def get_all_members(self, group_id: str) -> List[GroupMember]:
        """获取所有群成员"""
        with self._lock:
            return list(self._members[group_id].values())
    
    def get_members_by_role(self, 
                             group_id: str,
                             role: MemberRole) -> List[GroupMember]:
        """获取指定角色的成员"""
        with self._lock:
            return [
                m for m in self._members[group_id].values()
                if m.role == role
            ]
    
    def update_role(self, 
                    group_id: str,
                    user_id: str,
                    role: MemberRole) -> bool:
        """更新成员角色"""
        with self._lock:
            if user_id in self._members[group_id]:
                self._members[group_id][user_id].role = role
                return True
            return False
    
    def get_member_count(self, group_id: str) -> int:
        """获取成员数量"""
        with self._lock:
            return len(self._members[group_id])
    
    def get_nickname_map(self, group_id: str) -> Dict[str, str]:
        """获取昵称到用户ID的映射"""
        with self._lock:
            return dict(self._name_index[group_id])


class GroupManager:
    """群管理器（整合所有功能）"""
    
    def __init__(self, bot_names: List[str] = None):
        self.at_detector = AtMentionDetector(bot_names)
        self.statistics = GroupStatistics()
        self.member_manager = GroupMemberManager()
        
        self._at_handlers: List[Callable] = []
        self._lock = threading.Lock()
    
    def process_message(self,
                        group_id: str,
                        group_name: str,
                        sender_id: str,
                        sender_name: str,
                        content: str,
                        message_id: str,
                        timestamp: datetime = None) -> Dict[str, Any]:
        """处理群消息"""
        timestamp = timestamp or datetime.now()
        
        # 1. 记录消息统计
        self.statistics.record_message(
            group_id, group_name, sender_id, sender_name, timestamp
        )
        
        # 2. 检测@提及
        mentions = self.at_detector.detect(
            content, sender_id, sender_name, group_id, message_id
        )
        
        # 3. 更新成员信息
        self.member_manager.add_member(group_id, sender_id, sender_name)
        
        # 4. 处理@提及
        for mention in mentions:
            self.statistics.record_at(group_id, mention.mentioned_user_id)
            self._notify_at_handlers(mention)
        
        return {
            'group_id': group_id,
            'mentions': mentions,
            'stats': self.statistics.get_group_stats(group_id)
        }
    
    def register_at_handler(self, handler: Callable):
        """注册@提及处理器"""
        self._at_handlers.append(handler)
    
    def unregister_at_handler(self, handler: Callable):
        """取消注册@提及处理器"""
        if handler in self._at_handlers:
            self._at_handlers.remove(handler)
    
    def _notify_at_handlers(self, mention: AtMention):
        """通知@提及处理器"""
        for handler in self._at_handlers:
            try:
                handler(mention)
            except Exception as e:
                logger.error(f"@提及处理器执行失败: {e}")
    
    def get_group_summary(self, group_id: str) -> Dict[str, Any]:
        """获取群摘要"""
        stats = self.statistics.get_group_stats(group_id)
        member_count = self.member_manager.get_member_count(group_id)
        top_members = self.statistics.get_top_members(group_id, limit=5)
        
        return {
            'stats': stats,
            'member_count': member_count,
            'top_members': [
                {
                    'user_id': m.user_id,
                    'nickname': m.nickname,
                    'message_count': m.message_count
                }
                for m in top_members
            ]
        }