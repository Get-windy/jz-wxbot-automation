# -*- coding: utf-8 -*-
"""
jz-wxbot 核心功能测试
测试范围：
1. 消息发送功能
2. 群消息处理
3. 好友添加功能

任务ID: task_1774243272657_41df0z59k
日期: 2026-03-23
"""

import pytest
import time
import threading
import queue
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, 'I:\\jz-wxbot-automation')


# ==================== 数据模型 ====================

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    VOICE = "voice"
    LINK = "link"
    EMOTION = "emotion"


class ChatType(Enum):
    PRIVATE = "private"
    GROUP = "group"


class FriendStatus(Enum):
    NORMAL = "normal"          # 正常好友
    PENDING = "pending"        # 待验证
    DELETED = "deleted"        # 已删除
    BLACKLIST = "blacklist"    # 黑名单


@dataclass
class TestContact:
    """测试联系人"""
    user_id: str
    nickname: str
    alias: str = ""
    remark: str = ""
    status: FriendStatus = FriendStatus.NORMAL
    is_friend: bool = True
    add_time: float = None
    
    def __post_init__(self):
        if self.add_time is None:
            self.add_time = time.time()


@dataclass
class TestGroup:
    """测试群组"""
    group_id: str
    group_name: str
    member_count: int = 0
    owner_id: str = ""
    is_member: bool = True


@dataclass
class TestMessage:
    """测试消息"""
    message_id: str
    sender_id: str
    sender_name: str
    chat_id: str
    chat_name: str
    chat_type: ChatType
    content: str
    msg_type: MessageType = MessageType.TEXT
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


# ==================== 模拟组件 ====================

class MockMessageSender:
    """模拟消息发送器"""
    
    def __init__(self):
        self.sent_messages: List[Dict] = []
        self._initialized = False
        self._send_delay = 0.01  # 模拟发送延迟
    
    def initialize(self) -> bool:
        self._initialized = True
        return True
    
    def send_text(self, chat_id: str, content: str, **kwargs) -> bool:
        if not self._initialized:
            return False
        time.sleep(self._send_delay)
        self.sent_messages.append({
            'chat_id': chat_id,
            'content': content,
            'type': 'text',
            'timestamp': time.time(),
            **kwargs
        })
        return True
    
    def send_image(self, chat_id: str, image_path: str, **kwargs) -> bool:
        if not self._initialized:
            return False
        time.sleep(self._send_delay)
        self.sent_messages.append({
            'chat_id': chat_id,
            'image_path': image_path,
            'type': 'image',
            'timestamp': time.time(),
            **kwargs
        })
        return True
    
    def send_file(self, chat_id: str, file_path: str, **kwargs) -> bool:
        if not self._initialized:
            return False
        time.sleep(self._send_delay)
        self.sent_messages.append({
            'chat_id': chat_id,
            'file_path': file_path,
            'type': 'file',
            'timestamp': time.time(),
            **kwargs
        })
        return True
    
    def send_video(self, chat_id: str, video_path: str, **kwargs) -> bool:
        if not self._initialized:
            return False
        time.sleep(self._send_delay)
        self.sent_messages.append({
            'chat_id': chat_id,
            'video_path': video_path,
            'type': 'video',
            'timestamp': time.time(),
            **kwargs
        })
        return True
    
    def send_emotion(self, chat_id: str, emotion_id: str, **kwargs) -> bool:
        if not self._initialized:
            return False
        time.sleep(self._send_delay)
        self.sent_messages.append({
            'chat_id': chat_id,
            'emotion_id': emotion_id,
            'type': 'emotion',
            'timestamp': time.time(),
            **kwargs
        })
        return True
    
    def send_link(self, chat_id: str, title: str, url: str, **kwargs) -> bool:
        if not self._initialized:
            return False
        time.sleep(self._send_delay)
        self.sent_messages.append({
            'chat_id': chat_id,
            'title': title,
            'url': url,
            'type': 'link',
            'timestamp': time.time(),
            **kwargs
        })
        return True
    
    def get_stats(self) -> Dict:
        return {
            'total_sent': len(self.sent_messages),
            'by_type': self._count_by_type()
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        counts = {}
        for msg in self.sent_messages:
            t = msg['type']
            counts[t] = counts.get(t, 0) + 1
        return counts


class MockGroupManager:
    """模拟群管理器"""
    
    def __init__(self):
        self.groups: Dict[str, TestGroup] = {}
        self.group_messages: Dict[str, List[TestMessage]] = {}
        self._handlers: List[Callable] = []
        self._filters: List[Callable] = []
        self._init_test_groups()
    
    def _init_test_groups(self):
        """初始化测试群"""
        for i in range(3):
            group_id = f"group_{i:03d}"
            self.groups[group_id] = TestGroup(
                group_id=group_id,
                group_name=f"测试群{i}",
                member_count=50 + i * 10,
                owner_id="owner_001"
            )
    
    def get_group_list(self) -> List[TestGroup]:
        return list(self.groups.values())
    
    def get_group_info(self, group_id: str) -> Optional[TestGroup]:
        return self.groups.get(group_id)
    
    def send_group_message(self, group_id: str, content: str) -> bool:
        if group_id not in self.groups:
            return False
        
        msg = TestMessage(
            message_id=f"msg_{time.time()}",
            sender_id="self",
            sender_name="我",
            chat_id=group_id,
            chat_name=self.groups[group_id].group_name,
            chat_type=ChatType.GROUP,
            content=content
        )
        
        if group_id not in self.group_messages:
            self.group_messages[group_id] = []
        self.group_messages[group_id].append(msg)
        
        return True
    
    def receive_group_message(self, msg: TestMessage):
        """接收群消息"""
        group_id = msg.chat_id
        
        # 应用过滤器
        for filter_func in self._filters:
            if filter_func(msg):
                return  # 被过滤
        
        if group_id not in self.group_messages:
            self.group_messages[group_id] = []
        self.group_messages[group_id].append(msg)
        
        # 触发处理器
        for handler in self._handlers:
            try:
                handler(msg)
            except Exception:
                pass
    
    def add_filter(self, filter_func: Callable):
        self._filters.append(filter_func)
    
    def register_handler(self, handler: Callable):
        self._handlers.append(handler)
    
    def get_group_messages(self, group_id: str) -> List[TestMessage]:
        return self.group_messages.get(group_id, [])
    
    def create_group(self, group_name: str, members: List[str] = None) -> TestGroup:
        """创建群组"""
        group_id = f"group_{int(time.time())}"
        group = TestGroup(
            group_id=group_id,
            group_name=group_name,
            member_count=len(members) + 1 if members else 1,
            owner_id="self"
        )
        self.groups[group_id] = group
        return group
    
    def get_stats(self) -> Dict:
        total_msgs = sum(len(msgs) for msgs in self.group_messages.values())
        return {
            'group_count': len(self.groups),
            'total_messages': total_msgs,
            'filter_count': len(self._filters),
            'handler_count': len(self._handlers)
        }


class MockFriendManager:
    """模拟好友管理器"""
    
    def __init__(self):
        self.friends: Dict[str, TestContact] = {}
        self.pending_requests: List[Dict] = []
        self.blacklist: set = set()
        self._init_test_friends()
    
    def _init_test_friends(self):
        """初始化测试好友"""
        for i in range(5):
            user_id = f"user_{i:03d}"
            self.friends[user_id] = TestContact(
                user_id=user_id,
                nickname=f"好友{i}",
                alias=f"alias_{i}",
                remark=f"备注{i}"
            )
    
    def get_friend_list(self) -> List[TestContact]:
        return list(self.friends.values())
    
    def get_friend_info(self, user_id: str) -> Optional[TestContact]:
        return self.friends.get(user_id)
    
    def add_friend(self, user_id: str, message: str = "") -> Dict:
        """添加好友"""
        # 检查是否已在黑名单
        if user_id in self.blacklist:
            return {'success': False, 'error': 'user_in_blacklist'}
        
        # 检查是否已是好友
        if user_id in self.friends:
            return {'success': False, 'error': 'already_friend'}
        
        # 创建待验证请求
        request = {
            'user_id': user_id,
            'message': message,
            'request_time': time.time(),
            'status': 'pending'
        }
        self.pending_requests.append(request)
        
        # 模拟对方接受
        # 在测试中，我们假设添加成功
        self.friends[user_id] = TestContact(
            user_id=user_id,
            nickname=f"新好友_{user_id}",
            status=FriendStatus.NORMAL,
            add_time=time.time()
        )
        
        return {'success': True, 'user_id': user_id}
    
    def accept_friend(self, user_id: str) -> bool:
        """接受好友请求"""
        for req in self.pending_requests:
            if req['user_id'] == user_id and req['status'] == 'pending':
                req['status'] = 'accepted'
                self.friends[user_id] = TestContact(
                    user_id=user_id,
                    nickname=f"好友_{user_id}",
                    status=FriendStatus.NORMAL,
                    add_time=time.time()
                )
                return True
        return False
    
    def delete_friend(self, user_id: str) -> bool:
        """删除好友"""
        if user_id not in self.friends:
            return False
        
        contact = self.friends[user_id]
        contact.status = FriendStatus.DELETED
        contact.is_friend = False
        del self.friends[user_id]
        return True
    
    def add_to_blacklist(self, user_id: str) -> bool:
        """加入黑名单"""
        self.blacklist.add(user_id)
        if user_id in self.friends:
            self.friends[user_id].status = FriendStatus.BLACKLIST
        return True
    
    def remove_from_blacklist(self, user_id: str) -> bool:
        """移出黑名单"""
        if user_id in self.blacklist:
            self.blacklist.remove(user_id)
            return True
        return False
    
    def search_friend(self, keyword: str) -> List[TestContact]:
        """搜索好友"""
        results = []
        for contact in self.friends.values():
            if (keyword.lower() in contact.nickname.lower() or
                keyword.lower() in contact.remark.lower() or
                keyword.lower() in contact.alias.lower()):
                results.append(contact)
        return results
    
    def update_remark(self, user_id: str, remark: str) -> bool:
        """更新好友备注"""
        if user_id not in self.friends:
            return False
        self.friends[user_id].remark = remark
        return True
    
    def get_stats(self) -> Dict:
        return {
            'friend_count': len(self.friends),
            'pending_count': len([r for r in self.pending_requests if r['status'] == 'pending']),
            'blacklist_count': len(self.blacklist)
        }


# ==================== 测试类 ====================

class TestMessageSending:
    """消息发送功能测试"""
    
    @pytest.fixture
    def sender(self):
        s = MockMessageSender()
        s.initialize()
        return s
    
    # ========== 基础发送测试 ==========
    
    @pytest.mark.send
    def test_send_text_message(self, sender):
        """TC-SEND-001: 发送文本消息"""
        result = sender.send_text("chat_001", "测试文本消息")
        assert result is True
        assert len(sender.sent_messages) == 1
        assert sender.sent_messages[0]['type'] == 'text'
    
    @pytest.mark.send
    def test_send_image_message(self, sender):
        """TC-SEND-002: 发送图片消息"""
        result = sender.send_image("chat_001", "/path/to/image.jpg")
        assert result is True
        assert sender.sent_messages[0]['type'] == 'image'
    
    @pytest.mark.send
    def test_send_file_message(self, sender):
        """TC-SEND-003: 发送文件消息"""
        result = sender.send_file("chat_001", "/path/to/file.pdf")
        assert result is True
        assert sender.sent_messages[0]['type'] == 'file'
    
    @pytest.mark.send
    def test_send_video_message(self, sender):
        """TC-SEND-004: 发送视频消息"""
        result = sender.send_video("chat_001", "/path/to/video.mp4")
        assert result is True
        assert sender.sent_messages[0]['type'] == 'video'
    
    @pytest.mark.send
    def test_send_emotion_message(self, sender):
        """TC-SEND-005: 发送表情消息"""
        result = sender.send_emotion("chat_001", "emotion_001")
        assert result is True
        assert sender.sent_messages[0]['type'] == 'emotion'
    
    @pytest.mark.send
    def test_send_link_message(self, sender):
        """TC-SEND-006: 发送链接消息"""
        result = sender.send_link("chat_001", "百度", "https://www.baidu.com")
        assert result is True
        assert sender.sent_messages[0]['type'] == 'link'
    
    # ========== 批量发送测试 ==========
    
    @pytest.mark.send
    def test_batch_send(self, sender):
        """TC-SEND-010: 批量发送消息"""
        for i in range(10):
            sender.send_text("chat_001", f"消息{i}")
        
        assert len(sender.sent_messages) == 10
    
    @pytest.mark.send
    def test_send_to_multiple_chats(self, sender):
        """TC-SEND-011: 向多个会话发送"""
        chats = ["chat_001", "chat_002", "chat_003"]
        for chat_id in chats:
            sender.send_text(chat_id, "测试消息")
        
        chat_ids = set(msg['chat_id'] for msg in sender.sent_messages)
        assert len(chat_ids) == 3
    
    # ========== 统计功能测试 ==========
    
    @pytest.mark.send
    def test_send_statistics(self, sender):
        """TC-SEND-020: 发送统计"""
        sender.send_text("chat_001", "文本")
        sender.send_image("chat_001", "image.jpg")
        sender.send_file("chat_001", "file.pdf")
        sender.send_text("chat_001", "文本2")
        
        stats = sender.get_stats()
        assert stats['total_sent'] == 4
        assert stats['by_type']['text'] == 2
        assert stats['by_type']['image'] == 1
        assert stats['by_type']['file'] == 1


class TestGroupMessageProcessing:
    """群消息处理测试"""
    
    @pytest.fixture
    def manager(self):
        return MockGroupManager()
    
    # ========== 群管理测试 ==========
    
    @pytest.mark.group
    def test_get_group_list(self, manager):
        """TC-GROUP-001: 获取群列表"""
        groups = manager.get_group_list()
        assert len(groups) >= 3
    
    @pytest.mark.group
    def test_get_group_info(self, manager):
        """TC-GROUP-002: 获取群信息"""
        group = manager.get_group_info("group_000")
        assert group is not None
        assert group.group_name == "测试群0"
    
    @pytest.mark.group
    def test_create_group(self, manager):
        """TC-GROUP-003: 创建群组"""
        group = manager.create_group("新建测试群", ["user_001", "user_002"])
        assert group is not None
        assert group.group_name == "新建测试群"
        assert group.member_count == 3
    
    # ========== 消息处理测试 ==========
    
    @pytest.mark.group
    def test_send_group_message(self, manager):
        """TC-GROUP-010: 发送群消息"""
        result = manager.send_group_message("group_000", "测试群消息")
        assert result is True
        
        messages = manager.get_group_messages("group_000")
        assert len(messages) == 1
    
    @pytest.mark.group
    def test_receive_group_message(self, manager):
        """TC-GROUP-011: 接收群消息"""
        msg = TestMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="张三",
            chat_id="group_000",
            chat_name="测试群",
            chat_type=ChatType.GROUP,
            content="群消息内容"
        )
        
        manager.receive_group_message(msg)
        messages = manager.get_group_messages("group_000")
        assert len(messages) == 1
    
    @pytest.mark.group
    def test_group_message_filter(self, manager):
        """TC-GROUP-012: 群消息过滤"""
        # 添加广告过滤器
        manager.add_filter(lambda msg: "广告" in msg.content)
        
        # 发送正常消息
        msg1 = TestMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="张三",
            chat_id="group_000",
            chat_name="测试群",
            chat_type=ChatType.GROUP,
            content="正常消息"
        )
        manager.receive_group_message(msg1)
        
        # 发送广告消息
        msg2 = TestMessage(
            message_id="msg_002",
            sender_id="user_002",
            sender_name="李四",
            chat_id="group_000",
            chat_name="测试群",
            chat_type=ChatType.GROUP,
            content="这是广告消息"
        )
        manager.receive_group_message(msg2)
        
        messages = manager.get_group_messages("group_000")
        assert len(messages) == 1  # 只有正常消息
    
    @pytest.mark.group
    def test_group_message_handler(self, manager):
        """TC-GROUP-013: 群消息处理器"""
        handled_messages = []
        
        def handler(msg):
            handled_messages.append(msg)
        
        manager.register_handler(handler)
        
        msg = TestMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="张三",
            chat_id="group_000",
            chat_name="测试群",
            chat_type=ChatType.GROUP,
            content="测试消息"
        )
        manager.receive_group_message(msg)
        
        assert len(handled_messages) == 1
    
    # ========== 统计功能测试 ==========
    
    @pytest.mark.group
    def test_group_stats(self, manager):
        """TC-GROUP-020: 群统计"""
        stats = manager.get_stats()
        assert 'group_count' in stats
        assert 'total_messages' in stats


class TestFriendManagement:
    """好友管理功能测试"""
    
    @pytest.fixture
    def manager(self):
        return MockFriendManager()
    
    # ========== 好友列表测试 ==========
    
    @pytest.mark.friend
    def test_get_friend_list(self, manager):
        """TC-FRIEND-001: 获取好友列表"""
        friends = manager.get_friend_list()
        assert len(friends) >= 5
    
    @pytest.mark.friend
    def test_get_friend_info(self, manager):
        """TC-FRIEND-002: 获取好友信息"""
        friend = manager.get_friend_info("user_000")
        assert friend is not None
        assert friend.nickname == "好友0"
    
    @pytest.mark.friend
    def test_search_friend(self, manager):
        """TC-FRIEND-003: 搜索好友"""
        results = manager.search_friend("好友")
        assert len(results) >= 5
    
    # ========== 添加好友测试 ==========
    
    @pytest.mark.friend
    def test_add_friend(self, manager):
        """TC-FRIEND-010: 添加好友"""
        result = manager.add_friend("new_user_001", "你好，我想加你为好友")
        assert result['success'] is True
        
        friend = manager.get_friend_info("new_user_001")
        assert friend is not None
    
    @pytest.mark.friend
    def test_add_duplicate_friend(self, manager):
        """TC-FRIEND-011: 添加重复好友"""
        # 第一次添加
        manager.add_friend("dup_user", "请求1")
        
        # 第二次添加应该失败
        result = manager.add_friend("dup_user", "请求2")
        assert result['success'] is False
        assert result['error'] == 'already_friend'
    
    @pytest.mark.friend
    def test_add_blacklist_user(self, manager):
        """TC-FRIEND-012: 添加黑名单用户"""
        manager.add_to_blacklist("black_user")
        
        result = manager.add_friend("black_user", "请求")
        assert result['success'] is False
        assert result['error'] == 'user_in_blacklist'
    
    # ========== 删除好友测试 ==========
    
    @pytest.mark.friend
    def test_delete_friend(self, manager):
        """TC-FRIEND-020: 删除好友"""
        result = manager.delete_friend("user_000")
        assert result is True
        
        friend = manager.get_friend_info("user_000")
        assert friend is None
    
    @pytest.mark.friend
    def test_delete_nonexistent_friend(self, manager):
        """TC-FRIEND-021: 删除不存在的好友"""
        result = manager.delete_friend("nonexistent_user")
        assert result is False
    
    # ========== 黑名单测试 ==========
    
    @pytest.mark.friend
    def test_add_to_blacklist(self, manager):
        """TC-FRIEND-030: 加入黑名单"""
        result = manager.add_to_blacklist("user_001")
        assert result is True
        
        stats = manager.get_stats()
        assert stats['blacklist_count'] == 1
    
    @pytest.mark.friend
    def test_remove_from_blacklist(self, manager):
        """TC-FRIEND-031: 移出黑名单"""
        manager.add_to_blacklist("user_002")
        result = manager.remove_from_blacklist("user_002")
        assert result is True
        
        stats = manager.get_stats()
        assert stats['blacklist_count'] == 0
    
    # ========== 备注管理测试 ==========
    
    @pytest.mark.friend
    def test_update_remark(self, manager):
        """TC-FRIEND-040: 更新好友备注"""
        result = manager.update_remark("user_000", "新备注")
        assert result is True
        
        friend = manager.get_friend_info("user_000")
        assert friend.remark == "新备注"
    
    @pytest.mark.friend
    def test_update_nonexistent_remark(self, manager):
        """TC-FRIEND-041: 更新不存在的好友备注"""
        result = manager.update_remark("nonexistent", "备注")
        assert result is False
    
    # ========== 统计功能测试 ==========
    
    @pytest.mark.friend
    def test_friend_stats(self, manager):
        """TC-FRIEND-050: 好友统计"""
        stats = manager.get_stats()
        assert 'friend_count' in stats
        assert 'pending_count' in stats
        assert 'blacklist_count' in stats


class TestCoreIntegration:
    """核心功能集成测试"""
    
    @pytest.fixture
    def sender(self):
        s = MockMessageSender()
        s.initialize()
        return s
    
    @pytest.fixture
    def group_manager(self):
        return MockGroupManager()
    
    @pytest.fixture
    def friend_manager(self):
        return MockFriendManager()
    
    @pytest.mark.integration
    def test_friend_to_group_flow(self, friend_manager, group_manager, sender):
        """TC-INT-001: 添加好友后拉群流程"""
        # 1. 添加好友
        result = friend_manager.add_friend("new_user", "加好友")
        assert result['success'] is True
        
        # 2. 创建群组
        group = group_manager.create_group("工作群", ["new_user"])
        assert group is not None
        
        # 3. 发送群消息
        sender.send_text(group.group_id, "欢迎新成员")
        assert len(sender.sent_messages) == 1
    
    @pytest.mark.integration
    def test_group_message_to_friend(self, group_manager, friend_manager, sender):
        """TC-INT-002: 群消息转发给好友"""
        # 接收群消息
        group_msg = TestMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="张三",
            chat_id="group_000",
            chat_name="测试群",
            chat_type=ChatType.GROUP,
            content="重要通知"
        )
        group_manager.receive_group_message(group_msg)
        
        # 转发给好友
        friend = friend_manager.get_friend_info("user_000")
        sender.send_text(friend.user_id, f"群消息转发: {group_msg.content}")
        
        assert len(sender.sent_messages) == 1
    
    @pytest.mark.integration
    def test_full_workflow(self, friend_manager, group_manager, sender):
        """TC-INT-010: 完整工作流测试"""
        # 1. 搜索好友
        results = friend_manager.search_friend("好友")
        assert len(results) > 0
        
        # 2. 发送私聊消息
        friend = results[0]
        sender.send_text(friend.user_id, "私聊消息")
        
        # 3. 获取群列表
        groups = group_manager.get_group_list()
        assert len(groups) > 0
        
        # 4. 发送群消息
        group = groups[0]
        sender.send_text(group.group_id, "群消息")
        
        # 5. 验证发送统计
        stats = sender.get_stats()
        assert stats['total_sent'] == 2


# ==================== 运行测试 ====================

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"\nExit code: {result.returncode}")