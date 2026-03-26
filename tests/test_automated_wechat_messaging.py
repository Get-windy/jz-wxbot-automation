# -*- coding: utf-8 -*-
"""
jz-wxbot 微信消息模块自动化测试
覆盖消息发送、接收、处理等功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from datetime import datetime
import secrets

from core.message_reader_interface import (
    WeChatMessage,
    MessageType,
    ChatType
)


class TestWeChatMessagingAutomated(unittest.TestCase):
    """微信消息自动化测试"""
    
    def setUp(self):
        self.messages_db = []
        self.test_user_id = secrets.token_hex(16)
    
    def test_send_text_message(self):
        """TC-M001: 发送文本消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="测试消息内容",
            message_type=MessageType.TEXT
        )
        self.messages_db.append(msg)
        self.assertEqual(len(self.messages_db), 1)
        self.assertEqual(msg.content, "测试消息内容")
    
    def test_send_image_message(self):
        """TC-M002: 发送图片消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="[图片]",
            message_type=MessageType.IMAGE,
            extra={'image_url': 'https://example.com/img.jpg'}
        )
        self.messages_db.append(msg)
        self.assertEqual(msg.message_type, MessageType.IMAGE)
    
    def test_send_file_message(self):
        """TC-M003: 发送文件消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="[文件] doc.pdf",
            message_type=MessageType.FILE,
            extra={'filename': 'doc.pdf'}
        )
        self.messages_db.append(msg)
        self.assertEqual(msg.message_type, MessageType.FILE)
    
    def test_send_voice_message(self):
        """TC-M004: 发送语音消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="[语音]",
            message_type=MessageType.VOICE,
            extra={'duration': 5}
        )
        self.messages_db.append(msg)
        self.assertEqual(msg.message_type, MessageType.VOICE)
    
    def test_send_video_message(self):
        """TC-M005: 发送视频消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="[视频]",
            message_type=MessageType.VIDEO,
            extra={'duration': 30}
        )
        self.messages_db.append(msg)
        self.assertEqual(msg.message_type, MessageType.VIDEO)
    
    def test_send_link_message(self):
        """TC-M006: 发送链接消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="https://example.com",
            message_type=MessageType.LINK,
            extra={'title': '链接标题'}
        )
        self.messages_db.append(msg)
        self.assertEqual(msg.message_type, MessageType.LINK)
    
    def test_send_group_message(self):
        """TC-M007: 发送群消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="group_001",
            chat_name="测试群",
            chat_type=ChatType.GROUP,
            content="群消息",
            message_type=MessageType.TEXT
        )
        self.messages_db.append(msg)
        self.assertEqual(msg.chat_type, ChatType.GROUP)
    
    def test_send_at_message(self):
        """TC-M008: 发送@消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id=self.test_user_id,
            sender_name="测试用户",
            chat_id="group_001",
            chat_name="测试群",
            chat_type=ChatType.GROUP,
            content="@张三 你好",
            message_type=MessageType.TEXT,
            is_mentioned=True,
            at_user_ids=['user_001']
        )
        self.messages_db.append(msg)
        self.assertTrue(msg.is_mentioned)
    
    def test_receive_text_message(self):
        """TC-M009: 接收文本消息"""
        msg = WeChatMessage(
            message_id=secrets.token_hex(16),
            sender_id='sender_001',
            sender_name="发送者",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="收到消息",
            message_type=MessageType.TEXT,
            timestamp=datetime.now()
        )
        self.messages_db.append(msg)
        found = next((m for m in self.messages_db if m.message_id == msg.message_id), None)
        self.assertIsNotNone(found)
    
    def test_message_to_dict(self):
        """TC-M010: 消息转字典"""
        msg = WeChatMessage(
            message_id='msg_001',
            sender_id='user_001',
            sender_name="测试",
            chat_id="chat_001",
            chat_name="会话",
            chat_type=ChatType.PRIVATE,
            content="测试内容",
            message_type=MessageType.TEXT
        )
        data = msg.to_dict()
        self.assertEqual(data['message_id'], 'msg_001')
        self.assertEqual(data['content'], '测试内容')


if __name__ == '__main__':
    unittest.main()
