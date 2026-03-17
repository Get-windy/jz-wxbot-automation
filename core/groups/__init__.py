# -*- coding: utf-8 -*-
"""
群消息处理模块
版本: v1.0.0

功能:
- 群消息监听 - 监听群聊消息
- @提及处理 - 识别和处理@机器人消息
- 群消息统计 - 群消息数量、活跃度统计
- 群管理功能 - 群成员管理、消息撤回等
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

class GroupMessageType(Enum):
    """群消息类型"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    VOICE = "voice"
    LINK = "link"
    REDPACKET = "redpacket"
    SYSTEM = "system"
    MEMBER_JOIN = "member_join"
    MEMBER_LEAVE = "member_leave"


class GroupRole(Enum):
    """群角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


@dataclass
class GroupMember:
    """群成员"""
    user_id: str
    display_name: str
    nickname: str
    role: GroupRole = GroupRole.MEMBER
    join_time: Optional[datetime] = None
    last_active: Optional[datetime] = None
    is_active: bool = True
    
    @property
    def name(self) -> str:
        return self.display_name or self.nickname


@dataclass
class GroupInfo:
    """群信息"""
    room_id: str
    name: str
    owner_id: str
    member_count: int = 0
    notice: Optional[str] = None
    is_muted: bool = False
    is_pinned: bool = False
    created_at: Optional[datetime] = None
    my_nickname: Optional[str] = None
    
    # 统计信息
    today_message_count: int = 0
    total_message_count: int = 0


@dataclass
class GroupMessage:
    """群消息"""
    msg_id: str
    room_id: str
    room_name: str
    sender_id: str
    sender_name: str
    content: str
    msg_type: GroupMessageType = GroupMessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)
    is_at_me: bool = False
    at_list: List[str] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)


@dataclass
class GroupStatistics:
    """群统计"""
    room_id: str
    total_messages: int = 0
    today_messages: int = 0
    week_messages: int = 0
    month_messages: int = 0
    member_count: int = 0
    active_members: int = 0
    top_speakers: List[Dict] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


# ==================== 群消息监听器 ====================

class GroupMessageListener:
    """群消息监听器
    
    专门监听群聊消息
    """
    
    def __init__(
        self,
        on_message: Callable[[GroupMessage], None] = None,
        poll_interval: float = 1.0,
        my_nickname: str = "我"
    ):
        """
        初始化监听器
        
        Args:
            on_message: 消息回调
            poll_interval: 轮询间隔
            my_nickname: 我的昵称
        """
        self.on_message = on_message
        self.poll_interval = poll_interval
        self.my_nickname = my_nickname
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._known_messages: Set[str] = set()
        self._message_queue: 'SyncQueue' = None
        self._callbacks: List[Callable] = []
        
        # 群配置
        self._monitored_groups: Set[str] = set()  # 监控的群
        self._excluded_groups: Set[str] = set()  # 排除的群
        self._all_groups: bool = True  # 监控所有群
    
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
        logger.info("群消息监听器已启动")
    
    def stop(self):
        """停止监听"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("群消息监听器已停止")
    
    def set_monitored_groups(self, groups: List[str]):
        """设置监控的群"""
        self._monitored_groups = set(groups)
        self._all_groups = False
    
    def set_excluded_groups(self, groups: List[str]):
        """设置排除的群"""
        self._excluded_groups = set(groups)
    
    def monitor_all_groups(self):
        """监控所有群"""
        self._all_groups = True
        self._monitored_groups.clear()
    
    def register_callback(self, callback: Callable):
        """注册回调"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """注销回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _listen_loop(self):
        """监听循环"""
        while self._running:
            try:
                # 获取原始消息
                raw_messages = self._fetch_group_messages()
                
                for raw in raw_messages:
                    msg_id = raw.get('msg_id', '')
                    
                    # 跳过已处理消息
                    if msg_id in self._known_messages:
                        continue
                    
                    # 检查是否应该处理
                    room_id = raw.get('room_id', '')
                    if not self._should_process(room_id):
                        continue
                    
                    # 解析消息
                    message = self._parse_message(raw)
                    if message:
                        self._known_messages.add(msg_id)
                        self._notify(message)
                        
            except Exception as e:
                logger.error(f"群消息监听错误: {e}")
            
            time.sleep(self.poll_interval)
    
    def _fetch_group_messages(self) -> List[Dict]:
        """获取群消息
        
        TODO: 需要对接 pywechat 获取群消息
        """
        return []
    
    def _should_process(self, room_id: str) -> bool:
        """检查是否应该处理"""
        if room_id in self._excluded_groups:
            return False
        
        if not self._all_groups and room_id not in self._monitored_groups:
            return False
        
        return True
    
    def _parse_message(self, raw: Dict) -> Optional[GroupMessage]:
        """解析群消息"""
        try:
            room_id = raw.get('room_id', '')
            room_name = raw.get('room_name', '群聊')
            sender_id = raw.get('from_user', '')
            sender_name = raw.get('from_nickname', '')
            content = raw.get('content', '')
            msg_type = raw.get('type', 1)
            
            # 检测@信息
            is_at_me, at_list = self._parse_at_mentions(content)
            
            return GroupMessage(
                msg_id=raw.get('msg_id', ''),
                room_id=room_id,
                room_name=room_name,
                sender_id=sender_id,
                sender_name=sender_name,
                content=content,
                msg_type=GroupMessageType(raw.get('msg_type', 'text')),
                timestamp=datetime.now(),
                is_at_me=is_at_me,
                at_list=at_list,
                raw_data=raw
            )
        except Exception as e:
            logger.error(f"解析群消息失败: {e}")
            return None
    
    def _parse_at_mentions(self, content: str) -> tuple:
        """解析@提及"""
        import re
        
        # 匹配@xxx
        at_pattern = re.compile(r'@(\S+?)(?:\s|$)')
        mentions = at_pattern.findall(content)
        
        is_at_me = self.my_nickname in mentions or '我' in mentions
        
        return is_at_me, mentions
    
    def _notify(self, message: GroupMessage):
        """通知回调"""
        if self.on_message:
            try:
                self.on_message(message)
            except Exception as e:
                logger.error(f"群消息回调错误: {e}")
        
        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"回调错误: {e}")


class SyncQueue:
    """同步队列"""
    
    def __init__(self, maxsize: int = 1000):
        import queue
        self._queue = queue.Queue(maxsize=maxsize)
    
    def put(self, item, block=True, timeout=None):
        self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block=True, timeout=None):
        return self._queue.get(block=block, timeout=timeout)
    
    def qsize(self):
        return self._queue.qsize()


# ==================== @提及处理器 ====================

class AtMentionHandler:
    """@提及处理器
    
    处理群聊中@机器人的消息
    """
    
    def __init__(self, bot_name: str = "我"):
        self.bot_name = bot_name
        self._handlers: List[Callable] = []
        self._keyword_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, handler: Callable[[GroupMessage], Any]):
        """注册处理函数"""
        self._handlers.append(handler)
    
    def register_keyword_handler(self, keyword: str, handler: Callable):
        """注册关键词处理器"""
        self._keyword_handlers[keyword.lower()] = handler
    
    async def handle(self, message: GroupMessage) -> Optional[str]:
        """
        处理@消息
        
        Args:
            message: 群消息
            
        Returns:
            回复内容
        """
        if not message.is_at_me:
            return None
        
        # 获取实际内容 (移除@信息)
        content = self._remove_at_mentions(message.content)
        
        # 关键词匹配
        content_lower = content.lower()
        for keyword, handler in self._keyword_handlers.items():
            if keyword in content_lower:
                result = await self._call_handler(handler, message, content)
                if result:
                    return result
        
        # 通用处理器
        for handler in self._handlers:
            result = await self._call_handler(handler, message, content)
            if result:
                return result
        
        # 默认回复
        return self._default_reply(content)
    
    def _remove_at_mentions(self, content: str) -> str:
        """移除@提及"""
        import re
        # 移除@xxx
        content = re.sub(rf'@{self.bot_name}\s*', '', content)
        content = re.sub(r'@\S+\s*', '', content)
        return content.strip()
    
    async def _call_handler(self, handler, message: GroupMessage, content: str):
        """调用处理器"""
        import asyncio
        if asyncio.iscoroutinefunction(handler):
            return await handler(message, content)
        else:
            return handler(message, content)
    
    def _default_reply(self, content: str) -> str:
        """默认回复"""
        if not content:
            return "有什么可以帮你的？"
        
        return f"收到: {content}"


# ==================== 群消息统计 ====================

class GroupStatisticsCollector:
    """群消息统计收集器
    
    收集和分析群消息统计数据
    """
    
    def __init__(self):
        self._stats: Dict[str, GroupStatistics] = {}
        self._message_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        self._member_activity: Dict[str, Dict[str, datetime]] = defaultdict(dict)
    
    def record_message(self, message: GroupMessage):
        """记录消息"""
        room_id = message.room_id
        
        # 初始化统计
        if room_id not in self._stats:
            self._stats[room_id] = GroupStatistics(room_id=room_id)
        
        stats = self._stats[room_id]
        
        # 更新计数
        stats.total_messages += 1
        stats.today_messages += 1
        stats.week_messages += 1
        stats.month_messages += 1
        
        # 更新成员活跃
        self._member_activity[room_id][message.sender_id] = datetime.now()
        
        # 记录消息历史
        self._message_history[room_id].append({
            'msg_id': message.msg_id,
            'sender_id': message.sender_id,
            'sender_name': message.sender_name,
            'content': message.content,
            'timestamp': message.timestamp,
            'msg_type': message.msg_type.value
        })
        
        # 更新发言排行
        self._update_top_speakers(room_id, message.sender_id)
    
    def _update_top_speakers(self, room_id: str, sender_id: str):
        """更新发言排行"""
        stats = self._stats[room_id]
        
        # 简化实现
        pass
    
    def get_statistics(self, room_id: str) -> Optional[GroupStatistics]:
        """获取统计信息"""
        return self._stats.get(room_id)
    
    def get_all_statistics(self) -> Dict[str, GroupStatistics]:
        """获取所有统计"""
        return self._stats
    
    def get_daily_stats(self, room_id: str) -> int:
        """获取今日消息数"""
        stats = self._stats.get(room_id)
        return stats.today_messages if stats else 0
    
    def get_weekly_stats(self, room_id: str) -> int:
        """获取本周消息数"""
        stats = self._stats.get(room_id)
        return stats.week_messages if stats else 0
    
    def get_top_speakers(self, room_id: str, limit: int = 10) -> List[Dict]:
        """获取活跃成员"""
        # 简化实现
        room_id = room_id
        activity = self._member_activity.get(room_id, {})
        
        sorted_members = sorted(
            activity.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {'user_id': uid, 'last_active': last_active}
            for uid, last_active in sorted_members[:limit]
        ]
    
    def get_active_members_count(self, room_id: str, hours: int = 24) -> int:
        """获取活跃成员数"""
        activity = self._member_activity.get(room_id, {})
        cutoff = datetime.now() - timedelta(hours=hours)
        
        count = sum(1 for t in activity.values() if t > cutoff)
        return count
    
    def reset_daily_stats(self):
        """重置每日统计"""
        for stats in self._stats.values():
            stats.today_messages = 0


# ==================== 群管理 ====================

class GroupManager:
    """群管理
    
    群成员管理、消息管理等
    """
    
    def __init__(self):
        self._groups: Dict[str, GroupInfo] = {}
        self._members: Dict[str, Dict[str, GroupMember]] = defaultdict(dict)
    
    async def get_group_info(self, room_id: str) -> Optional[GroupInfo]:
        """获取群信息"""
        # TODO: 实际获取群信息
        return self._groups.get(room_id)
    
    async def get_group_list(self) -> List[GroupInfo]:
        """获取群列表"""
        # TODO: 实际获取群列表
        return list(self._groups.values())
    
    async def get_group_members(self, room_id: str) -> List[GroupMember]:
        """获取群成员列表"""
        return list(self._members.get(room_id, {}).values())
    
    async def get_member_info(
        self, 
        room_id: str, 
        user_id: str
    ) -> Optional[GroupMember]:
        """获取成员信息"""
        members = self._members.get(room_id, {})
        return members.get(user_id)
    
    async def change_nickname(
        self, 
        room_id: str, 
        nickname: str
    ) -> bool:
        """修改群昵称"""
        # TODO: 调用 pywechat
        logger.info(f"修改群昵称为: {nickname}")
        return True
    
    async def change_notice(
        self, 
        room_id: str, 
        notice: str
    ) -> bool:
        """修改群公告"""
        # TODO: 调用 pywechat
        logger.info(f"修改群公告: {notice}")
        return True
    
    async def invite_member(
        self, 
        room_id: str, 
        user_ids: List[str]
    ) -> bool:
        """邀请成员"""
        # TODO: 调用 pywechat
        logger.info(f"邀请成员: {user_ids}")
        return True
    
    async def remove_member(
        self, 
        room_id: str, 
        user_id: str
    ) -> bool:
        """移除成员"""
        # TODO: 调用 pywechat
        logger.info(f"移除成员: {user_id}")
        return True
    
    async def set_admin(
        self, 
        room_id: str, 
        user_id: str,
        is_admin: bool = True
    ) -> bool:
        """设置管理员"""
        # TODO: 调用 pywechat
        logger.info(f"设置管理员: {user_id}, is_admin={is_admin}")
        return True
    
    async def pin_group(
        self, 
        room_id: str, 
        pin: bool = True
    ) -> bool:
        """置顶/取消置顶群聊"""
        # TODO: 调用 pywechat
        logger.info(f"置顶群聊: {pin}")
        return True
    
    async def mute_group(
        self, 
        room_id: str, 
        mute: bool = True
    ) -> bool:
        """开启/关闭消息免打扰"""
        # TODO: 调用 pywechat
        logger.info(f"群消息免打扰: {mute}")
        return True
    
    async def quit_group(self, room_id: str) -> bool:
        """退出群聊"""
        # TODO: 调用 pywechat
        logger.info(f"退出群聊: {room_id}")
        return True
    
    async def dissolve_group(self, room_id: str) -> bool:
        """解散群聊"""
        # TODO: 调用 pywechat
        logger.info(f"解散群聊: {room_id}")
        return True
    
    def add_group(self, group: GroupInfo):
        """添加群信息"""
        self._groups[group.room_id] = group
    
    def add_member(self, room_id: str, member: GroupMember):
        """添加群成员"""
        self._members[room_id][member.user_id] = member


# ==================== 群消息处理器 ====================

class GroupMessageProcessor:
    """群消息处理器
    
    统一管理群消息监听、@处理、统计、管理
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 初始化各组件
        self.listener = GroupMessageListener(
            my_nickname=self.config.get('my_nickname', '我'),
            poll_interval=self.config.get('poll_interval', 1.0)
        )
        
        self.at_handler = AtMentionHandler(
            bot_name=self.config.get('my_nickname', '我')
        )
        
        self.statistics = GroupStatisticsCollector()
        self.manager = GroupManager()
        
        self._running = False
        self._on_at_message_callbacks: List[Callable] = []
        self._on_message_callbacks: List[Callable] = []
        
        # 注册默认回调
        self.listener.register_callback(self._on_new_message)
    
    def _on_new_message(self, message: GroupMessage):
        """新消息回调"""
        # 记录统计
        self.statistics.record_message(message)
        
        # 如果是@消息，触发@处理
        if message.is_at_me:
            asyncio.create_task(self._handle_at_message(message))
        
        # 触发消息回调
        for callback in self._on_message_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"消息回调错误: {e}")
    
    async def _handle_at_message(self, message: GroupMessage):
        """处理@消息"""
        # 调用@处理器
        reply = await self.at_handler.handle(message)
        
        if reply:
            logger.info(f"回复: {reply}")
            # TODO: 发送回复
        
        # 触发@消息回调
        for callback in self._on_at_message_callbacks:
            try:
                callback(message, reply)
            except Exception as e:
                logger.error(f"@消息回调错误: {e}")
    
    def on_message(self, callback: Callable):
        """注册消息回调"""
        self._on_message_callbacks.append(callback)
    
    def on_at_message(self, callback: Callable):
        """注册@消息回调"""
        self._on_at_message_callbacks.append(callback)
    
    def register_at_handler(self, handler: Callable):
        """注册@处理器"""
        self.at_handler.register_handler(handler)
    
    def register_keyword(self, keyword: str, handler: Callable):
        """注册关键词"""
        self.at_handler.register_keyword_handler(keyword, handler)
    
    async def start(self):
        """启动处理器"""
        if self._running:
            return
        
        self._running = True
        self.listener.start()
        
        logger.info("群消息处理器已启动")
    
    async def stop(self):
        """停止处理器"""
        self._running = False
        self.listener.stop()
        
        logger.info("群消息处理器已停止")
    
    def get_statistics(self, room_id: str) -> Optional[GroupStatistics]:
        """获取群统计"""
        return self.statistics.get_statistics(room_id)
    
    def get_all_statistics(self) -> Dict[str, GroupStatistics]:
        """获取所有统计"""
        return self.statistics.get_all_statistics()
    
    async def get_group_list(self) -> List[GroupInfo]:
        """获取群列表"""
        return await self.manager.get_group_list()
    
    async def get_group_members(self, room_id: str) -> List[GroupMember]:
        """获取群成员"""
        return await self.manager.get_group_members(room_id)


# ==================== 使用示例 ====================

async def example_basic():
    """基本使用示例"""
    
    # 创建处理器
    processor = GroupMessageProcessor({
        'my_nickname': '小助手',
        'poll_interval': 1.0
    })
    
    # 注册消息回调
    def on_group_message(msg: GroupMessage):
        print(f"[{msg.room_name}] {msg.sender_name}: {msg.content}")
    
    processor.on_message(on_group_message)
    
    # 注册@消息回调
    def on_at_message(msg: GroupMessage, reply: str):
        print(f"@消息 from {msg.sender_name}, 回复: {reply}")
    
    processor.on_at_message(on_at_message)
    
    # 注册关键词处理器
    processor.register_keyword('天气', lambda m, c: '今天天气很好！')
    processor.register_keyword('帮助', lambda m, c: '有什么可以帮你的？')
    
    # 启动
    await processor.start()
    
    # 运行一段时间
    await asyncio.sleep(30)
    
    # 获取统计
    stats = processor.get_statistics('group_001')
    if stats:
        print(f"今日消息: {stats.today_messages}")
        print(f"总消息: {stats.total_messages}")
    
    # 获取群列表
    groups = await processor.get_group_list()
    print(f"群数量: {len(groups)}")
    
    # 停止
    await processor.stop()


async def example_with_handlers():
    """自定义处理器示例"""
    
    processor = GroupMessageProcessor()
    
    # 自定义@处理器
    async def custom_at_handler(message: GroupMessage, content: str) -> str:
        # 处理业务逻辑
        if '查询' in content:
            return "查询功能开发中..."
        elif '帮助' in content:
            return "可用命令: 天气、查询、帮助"
        
        return "收到消息"
    
    processor.register_at_handler(custom_at_handler)
    
    await processor.start()
    await asyncio.sleep(60)
    await processor.stop()


# ==================== 主入口 ====================

if __name__ == '__main__':
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(example_basic())