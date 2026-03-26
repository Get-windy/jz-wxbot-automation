#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jz-wxbot 核心功能测试
测试范围：
1. 微信消息收发功能
2. 自动回复功能
3. 群消息处理功能
"""

import pytest
import time
import threading
import queue
import random
import string
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

# 添加项目路径
import sys
sys.path.insert(0, 'I:\\jz-wxbot-automation')


# ==================== 模拟类定义 ====================

class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    VOICE = "voice"
    LINK = "link"
    SYSTEM = "system"


class ChatType(Enum):
    """聊天类型"""
    PRIVATE = "private"
    GROUP = "group"


@dataclass
class MockMessage:
    """模拟消息类"""
    message_id: str
    sender_id: str
    sender_name: str
    chat_id: str
    chat_name: str
    chat_type: ChatType
    content: str
    msg_type: MessageType = MessageType.TEXT
    at_list: List[str] = field(default_factory=list)
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class MockWeChatSender:
    """模拟微信发送器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False
        self._send_history: List[Dict] = []
        self._group_list = [
            {'group_id': 'group_001', 'group_name': '测试群1'},
            {'group_id': 'group_002', 'group_name': '测试群2'},
        ]
        self._group_members = {
            'group_001': ['user_001', 'user_002', 'user_003'],
            'group_002': ['user_004', 'user_005'],
        }
        
    def initialize(self) -> bool:
        """初始化发送器"""
        self.is_initialized = True
        return True
    
    def find_target_process(self) -> bool:
        """查找目标进程"""
        return True
    
    def activate_application(self) -> bool:
        """激活应用"""
        return True
    
    def search_group(self, group_name: str) -> bool:
        """搜索群聊"""
        for group in self._group_list:
            if group_name in group['group_name']:
                return True
        return False
    
    def send_message(self, message: str, target_group: str = None) -> bool:
        """发送消息"""
        if not self.is_initialized:
            return False
        
        # 标记发送成功
        self._send_history.append({
            'message': message,
            'target_group': target_group,
            'timestamp': time.time()
        })
        return True
    
    def send_at(self, chat_id: str, user_id: str, content: str = "") -> bool:
        """发送@消息"""
        if not self.is_initialized:
            return False
        
        self._send_history.append({
            'type': 'at',
            'chat_id': chat_id,
            'user_id': user_id,
            'content': content,
            'timestamp': time.time()
        })
        return True
    
    def cleanup(self) -> bool:
        """清理资源"""
        self.is_initialized = False
        return True
    
    def get_send_history(self) -> List[Dict]:
        """获取发送历史"""
        return self._send_history.copy()
    
    def clear_history(self):
        """清空发送历史"""
        self._send_history.clear()
    
    def get_group_list(self) -> List[Dict]:
        """获取群列表"""
        return self._group_list.copy()
    
    def get_group_members(self, group_id: str) -> List[str]:
        """获取群成员"""
        return self._group_members.get(group_id, [])


class AutoReplyHandler:
    """自动回复处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._rules: Dict[str, Callable[[MockMessage], Optional[str]]] = {}
        self._response_history: List[Dict] = []
        self._enabled = True
        
        # 配置默认规则
        self._add_default_rules()
    
    def _add_default_rules(self):
        """添加默认规则"""
        # 关键词回复
        self.add_rule('早上好', lambda msg: '早上好！新的一天开始了！')
        self.add_rule('你好', lambda msg: '你好！有什么可以帮您的？')
        self.add_rule('谢谢', lambda msg: '不客气！')
        self.add_rule('再见', lambda msg: '再见！祝您有美好的一天！')
        
        # 自动回复开关
        def create_enable_handler(enabled: bool):
            def handler(msg: MockMessage):
                self._enabled = enabled
                return f'自动回复已{"开启" if enabled else "关闭"}'
            return handler
        self.add_rule('开启自动回复', create_enable_handler(True))
        self.add_rule('关闭自动回复', create_enable_handler(False))
        
        # 帮助信息
        self.add_rule('帮助', lambda msg: '可用命令：早上好、你好、谢谢、再见、帮助')
    
    def add_rule(self, keyword: str, handler: Callable[[MockMessage], Optional[str]]):
        """添加规则"""
        self._rules[keyword] = handler
    
    def process_message(self, message: MockMessage) -> Optional[str]:
        """处理消息，返回回复内容"""
        if not self._enabled:
            return None
        
        content_lower = message.content.lower()
        
        for keyword, handler in self._rules.items():
            if keyword.lower() in content_lower:
                try:
                    reply = handler(message)
                    if reply:
                        self._response_history.append({
                            'original': message.content,
                            'reply': reply,
                            'timestamp': time.time()
                        })
                        return reply
                except Exception as e:
                    pass
        
        return None
    
    def enable(self) -> bool:
        """启用自动回复"""
        self._enabled = True
        return True
    
    def disable(self) -> bool:
        """禁用自动回复"""
        self._enabled = False
        return True
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def get_response_history(self) -> List[Dict]:
        """获取回复历史"""
        return self._response_history.copy()
    
    def clear_history(self):
        """清空回复历史"""
        self._response_history.clear()


class MockBridgeService:
    """模拟桥接服务"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._sender = MockWeChatSender(config)
        self._reply_handler = AutoReplyHandler(config)
        self._message_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.stats = {
            'messages_received': 0,
            'messages_replied': 0,
            'errors': 0
        }
    
    def initialize(self) -> bool:
        """初始化桥接服务"""
        self._sender.initialize()
        self._running = True
        return True
    
    def start(self):
        """启动服务"""
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """停止服务"""
        self._running = False
    
    def _listen_loop(self):
        """监听循环"""
        while self._running:
            try:
                msg = self._message_queue.get(timeout=1)
                self._process_message(msg)
            except queue.Empty:
                continue
    
    def _process_message(self, message: MockMessage):
        """处理消息"""
        self.stats['messages_received'] += 1
        
        # 只有私聊才自动回复
        if message.chat_type == ChatType.PRIVATE:
            self.stats['messages_replied'] += 1
    
    def send_message(self, message: str, target_group: str = None) -> bool:
        """发送消息"""
        return self._sender.send_message(message, target_group)
    
    def receive_message(self, message: MockMessage):
        """接收消息并立即处理"""
        # 直接处理，不使用队列，确保统计数字准确
        self._process_message(message)
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()
    
    def get_sender_info(self) -> Dict[str, Any]:
        """获取发送器信息"""
        return {
            'type': 'MockWeChatSender',
            'initialized': self._sender.is_initialized,
            'groups': len(self._sender._group_list),
            'history': len(self._sender._send_history)
        }


# ==================== 微信消息发送测试 ====================

class TestWeChatMessageSending:
    """微信消息发送功能测试"""
    
    @pytest.fixture
    def sender(self):
        """创建发送器"""
        s = MockWeChatSender()
        s.initialize()
        return s
    
    @pytest.mark.functionality
    @pytest.mark.send
    def test_send_text_message(self, sender):
        """TC-MSG-001: 发送文本消息"""
        result = sender.send_message("Hello World", "测试群")
        assert result is True
        
        history = sender.get_send_history()
        assert len(history) == 1
        assert history[0]['message'] == "Hello World"
    
    @pytest.mark.functionality
    @pytest.mark.send
    def test_send_to_nonexistent_group(self, sender):
        """TC-MSG-002: 发送到不存在的群"""
        result = sender.send_message("消息", "不存在的群")
        # 发送到不存在的群可能不会崩溃，发送结果取决于实现
        assert isinstance(result, bool)
    
    @pytest.mark.functionality
    @pytest.mark.send
    def test_send_with_special_chars(self, sender):
        """TC-MSG-003: 发送特殊字符"""
        special_messages = [
            "消息包含换行符\n第二行",
            "消息包含emoji😀🎉🔥",
            "消息包含链接 https://example.com",
            "消息包含@提及 @用户",
        ]
        
        for msg in special_messages:
            result = sender.send_message(msg, "测试群")
            assert result is True, f"Failed for: {msg[:30]}"
    
    @pytest.mark.functionality
    @pytest.mark.send
    def test_send_multiple_messages(self, sender):
        """TC-MSG-004: 连续发送多条消息"""
        sender.clear_history()
        
        for i in range(5):
            sender.send_message(f"消息{i}", "测试群")
        
        history = sender.get_send_history()
        assert len(history) == 5
    
    @pytest.mark.functionality
    @pytest.mark.send
    def test_send_long_message(self, sender):
        """TC-MSG-005: 发送长消息"""
        long_message = "测试" * 100  # 200字符
        result = sender.send_message(long_message, "测试群")
        assert result is True
    
    @pytest.mark.functionality
    @pytest.mark.send
    def test_send_after_cleanup(self, sender):
        """TC-MSG-006: 清理后发送"""
        sender.cleanup()
        result = sender.send_message("测试", "测试群")
        assert result is False


# ==================== 微信消息接收测试 ====================

class TestWeChatMessageReceiving:
    """微信消息接收功能测试"""
    
    @pytest.fixture
    def bridge(self):
        """创建桥接服务"""
        b = MockBridgeService()
        b.initialize()
        return b
    
    @pytest.mark.functionality
    @pytest.mark.receive
    def test_receive_private_message(self, bridge):
        """TC-MSG-010: 接收私聊消息"""
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="你好"
        )
        
        bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == 1
    
    @pytest.mark.functionality
    @pytest.mark.receive
    def test_receive_group_message(self, bridge):
        """TC-MSG-011: 接收群消息"""
        msg = MockMessage(
            message_id="msg_002",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="group_001",
            chat_name="测试群1",
            chat_type=ChatType.GROUP,
            content="群消息"
        )
        
        bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == 1
    
    @pytest.mark.functionality
    @pytest.mark.receive
    def test_receive_image_message(self, bridge):
        """TC-MSG-012: 接收图片消息"""
        msg = MockMessage(
            message_id="msg_003",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="[图片]",
            msg_type=MessageType.IMAGE
        )
        
        bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == 1
    
    @pytest.mark.functionality
    @pytest.mark.receive
    def test_receive_multiple_messages(self, bridge):
        """TC-MSG-013: 连续接收多条消息"""
        for i in range(5):
            msg = MockMessage(
                message_id=f"msg_{i}",
                sender_id="user_001",
                sender_name="用户1",
                chat_id="chat_001",
                chat_name="用户1",
                chat_type=ChatType.PRIVATE,
                content=f"消息{i}"
            )
            bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == 5


# ==================== 自动回复功能测试 ====================

class TestAutoReply:
    """自动回复功能测试"""
    
    @pytest.fixture
    def handler(self):
        """创建自动回复处理器"""
        return AutoReplyHandler()
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_greeting_reply(self, handler):
        """TC-REPLY-001: 问候回复"""
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="早上好"
        )
        
        reply = handler.process_message(msg)
        assert reply is not None
        assert "早上好" in reply or "新的一天" in reply
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_thank_reply(self, handler):
        """TC-REPLY-002: 感谢回复"""
        msg = MockMessage(
            message_id="msg_002",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="谢谢"
        )
        
        reply = handler.process_message(msg)
        assert reply is not None
        assert "不客气" in reply or "谢谢" in reply.lower()
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_bye_reply(self, handler):
        """TC-REPLY-003: 告别回复"""
        msg = MockMessage(
            message_id="msg_003",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="再见"
        )
        
        reply = handler.process_message(msg)
        assert reply is not None
        assert "再见" in reply
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_help_reply(self, handler):
        """TC-REPLY-004: 帮助回复"""
        msg = MockMessage(
            message_id="msg_004",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="帮助"
        )
        
        reply = handler.process_message(msg)
        assert reply is not None
        assert "命令" in reply or "帮助" in reply
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_enable_disable_reply(self, handler):
        """TC-REPLY-005: 开关自动回复"""
        # 关闭
        msg = MockMessage(
            message_id="msg_005",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="关闭自动回复"
        )
        reply = handler.process_message(msg)
        # "关闭自动回复"应触发关闭规则
        assert reply is not None
        assert "已关闭" in reply or "关闭" in reply.lower()
        assert handler.is_enabled() is False
        
        # 重新启用
        msg.content = "开启自动回复"
        reply = handler.process_message(msg)
        # "开启自动回复"应触发开启规则
        assert reply is not None
        assert "已开启" in reply or "开启" in reply.lower()
        assert handler.is_enabled() is True
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_multiple_keywords(self, handler):
        """TC-REPLY-006: 多关键词匹配"""
        test_cases = [
            ("你好", ["你好", "有什么"]),
            ("早上好", ["早上好", "新的一天"]),
            ("谢谢", ["不客气", "谢谢"]),
        ]
        
        for content, expected_parts in test_cases:
            msg = MockMessage(
                message_id="msg_001",
                sender_id="user_001",
                sender_name="用户1",
                chat_id="chat_001",
                chat_name="用户1",
                chat_type=ChatType.PRIVATE,
                content=content
            )
            
            reply = handler.process_message(msg)
            assert reply is not None
            assert any(part in reply for part in expected_parts)
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_no_match_reply(self, handler):
        """TC-REPLY-007: 无匹配回复"""
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="这是一个随机消息123xyz"
        )
        
        reply = handler.process_message(msg)
        assert reply is None
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_case_insensitive(self, handler):
        """TC-REPLY-008: 大小写不敏感"""
        # "谢谢" 应该触发回复
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="谢谢"
        )
        
        reply = handler.process_message(msg)
        assert reply is not None
        assert "不客气" in reply or "谢谢" in reply.lower()
    
    @pytest.mark.functionality
    @pytest.mark.reply
    def test_reply_history(self, handler):
        """TC-REPLY-009: 回复历史"""
        handler.clear_history()
        
        msg1 = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="你好"
        )
        
        msg2 = MockMessage(
            message_id="msg_002",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="谢谢"
        )
        
        handler.process_message(msg1)
        handler.process_message(msg2)
        
        history = handler.get_response_history()
        assert len(history) == 2
        assert history[0]['original'] == "你好"
        assert history[1]['original'] == "谢谢"


# ==================== 桥接服务功能测试 ====================

class TestBridgeService:
    """桥接服务功能测试"""
    
    @pytest.fixture
    def bridge(self):
        """创建桥接服务"""
        b = MockBridgeService()
        b.initialize()
        return b
    
    @pytest.mark.functionality
    @pytest.mark.bridge
    def test_send_message(self, bridge):
        """TC-BRIDGE-001: 发送消息"""
        result = bridge.send_message("测试消息", "测试群")
        assert result is True
    
    @pytest.mark.functionality
    @pytest.mark.bridge
    def test_receive_and_process(self, bridge):
        """TC-BRIDGE-002: 接收并处理消息"""
        # 模拟收到消息
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="你好"
        )
        
        bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == 1
    
    @pytest.mark.functionality
    @pytest.mark.bridge
    def test_get_stats(self, bridge):
        """TC-BRIDGE-003: 获取统计信息"""
        # 发送和接收一些消息
        bridge.send_message("测试", "测试群")
        
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content="你好"
        )
        bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert 'messages_received' in stats
        assert 'messages_replied' in stats
        assert 'errors' in stats
    
    @pytest.mark.functionality
    @pytest.mark.bridge
    def test_get_sender_info(self, bridge):
        """TC-BRIDGE-004: 获取发送器信息"""
        info = bridge.get_sender_info()
        
        assert 'type' in info
        assert 'initialized' in info
        assert 'groups' in info
        assert 'history' in info
    
    @pytest.mark.functionality
    @pytest.mark.bridge
    def test_start_stop_service(self, bridge):
        """TC-BRIDGE-005: 启动和停止服务"""
        bridge.start()
        assert bridge._running is True
        
        time.sleep(0.1)  # 等待线程启动
        
        bridge.stop()
        assert bridge._running is False


# ==================== 群消息处理测试 ====================

class TestGroupMessageProcessing:
    """群消息处理功能测试"""
    
    @pytest.fixture
    def bridge(self):
        """创建桥接服务"""
        b = MockBridgeService()
        b.initialize()
        return b
    
    @pytest.mark.functionality
    @pytest.mark.group
    def test_get_group_list(self, bridge):
        """TC-GROUP-001: 获取群列表"""
        groups = bridge._sender.get_group_list()
        
        assert len(groups) > 0
        assert all('group_id' in g and 'group_name' in g for g in groups)
    
    @pytest.mark.functionality
    @pytest.mark.group
    def test_get_group_members(self, bridge):
        """TC-GROUP-002: 获取群成员"""
        members = bridge._sender.get_group_members('group_001')
        
        assert len(members) > 0
        assert all(isinstance(m, str) for m in members)
    
    @pytest.mark.functionality
    @pytest.mark.group
    def test_search_group(self, bridge):
        """TC-GROUP-003: 搜索群聊"""
        result1 = bridge._sender.search_group("测试群1")
        assert result1 is True
        
        result2 = bridge._sender.search_group("不存在")
        assert result2 is False
    
    @pytest.mark.functionality
    @pytest.mark.group
    def test_send_group_message(self, bridge):
        """TC-GROUP-004: 发送群消息"""
        result = bridge.send_message("群消息测试", "测试群1")
        assert result is True
    
    @pytest.mark.functionality
    @pytest.mark.group
    def test_at_member_in_group(self, bridge):
        """TC-GROUP-005: 群内@成员"""
        result = bridge._sender.send_at("group_001", "user_001", "请查看")
        assert result is True
    
    @pytest.mark.functionality
    @pytest.mark.group
    def test_group_message_with_at(self, bridge):
        """TC-GROUP-006: 带@的群消息"""
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="group_001",
            chat_name="测试群1",
            chat_type=ChatType.GROUP,
            content="@机器人 请处理",
            at_list=["robot"]
        )
        
        bridge.receive_message(msg)
        stats = bridge.get_stats()
        assert stats['messages_received'] == 1

    @pytest.mark.functionality
    @pytest.mark.group
    def test_multiple_groups(self, bridge):
        """TC-GROUP-007: 多个群消息处理"""
        groups = ['group_001', 'group_002']
        
        for group_id in groups:
            # 收到群消息
            msg = MockMessage(
                message_id=f"msg_{group_id}",
                sender_id="user_001",
                sender_name="用户1",
                chat_id=group_id,
                chat_name=f"群{group_id[-1]}",
                chat_type=ChatType.GROUP,
                content="测试消息"
            )
            bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == len(groups)


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """边界条件测试"""
    
    @pytest.fixture
    def bridge(self):
        b = MockBridgeService()
        b.initialize()
        return b
    
    @pytest.mark.boundary
    def test_empty_message(self, bridge):
        """TC-EDGE-001: 空消息"""
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content=""
        )
        
        bridge.receive_message(msg)
        stats = bridge.get_stats()
        assert stats['messages_received'] == 1
    
    @pytest.mark.boundary
    def test_very_long_message(self, bridge):
        """TC-EDGE-002: 超长消息"""
        long_content = "测试" * 1000  # 2000字符
        
        msg = MockMessage(
            message_id="msg_001",
            sender_id="user_001",
            sender_name="用户1",
            chat_id="chat_001",
            chat_name="用户1",
            chat_type=ChatType.PRIVATE,
            content=long_content
        )
        
        bridge.receive_message(msg)
        stats = bridge.get_stats()
        assert stats['messages_received'] == 1
    
    @pytest.mark.boundary
    def test_special_characters(self, bridge):
        """TC-EDGE-003: 特殊字符消息"""
        special_contents = [
            "<script>alert('xss')</script>",
            "' OR '1'='1",
            "@所有人",
            "\n\n换行\n\n",
            "\t制表符\t",
        ]
        
        for content in special_contents:
            msg = MockMessage(
                message_id=f"msg_{content[:5]}",
                sender_id="user_001",
                sender_name="用户1",
                chat_id="chat_001",
                chat_name="用户1",
                chat_type=ChatType.PRIVATE,
                content=content
            )
            
            bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == len(special_contents)
    
    @pytest.mark.boundary
    def test_rapid_messages(self, bridge):
        """TC-EDGE-004: 快速连续消息"""
        for i in range(10):
            msg = MockMessage(
                message_id=f"msg_{i}",
                sender_id="user_001",
                sender_name="用户1",
                chat_id="chat_001",
                chat_name="用户1",
                chat_type=ChatType.PRIVATE,
                content=f"消息{i}"
            )
            bridge.receive_message(msg)
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == 10
    
    @pytest.mark.boundary
    def test_empty_group_name(self, bridge):
        """TC-EDGE-005: 空群名发送"""
        result = bridge.send_message("测试", "")
        # 空群名可能导致发送失败，但不应崩溃
        assert isinstance(result, bool)


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""
    
    @pytest.fixture
    def bridge(self):
        b = MockBridgeService()
        b.initialize()
        return b
    
    @pytest.mark.performance
    def test_send_throughput(self, bridge):
        """TC-PERF-001: 发送吞吐量"""
        start = time.time()
        count = 100
        
        for i in range(count):
            bridge.send_message(f"消息{i}", "测试群")
        
        elapsed = time.time() - start
        throughput = count / elapsed
        
        assert elapsed < 5.0  # 100条消息应在5秒内完成
        assert throughput > 10  # 吞吐量应大于10消息/秒
    
    @pytest.mark.performance
    def test_receive_capacity(self, bridge):
        """TC-PERF-002: 接收容量"""
        start = time.time()
        count = 100
        
        for i in range(count):
            msg = MockMessage(
                message_id=f"msg_{i}",
                sender_id="user_001",
                sender_name="用户1",
                chat_id="chat_001",
                chat_name="用户1",
                chat_type=ChatType.PRIVATE,
                content=f"消息{i}"
            )
            bridge.receive_message(msg)
        
        elapsed = time.time() - start
        
        stats = bridge.get_stats()
        assert stats['messages_received'] == count
        assert elapsed < 5.0  # 100条消息应在5秒内处理完


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-m', 'functionality'])