# -*- coding: utf-8 -*-
"""
消息处理模块测试
版本: v1.0.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import threading
import time
from datetime import datetime

from core.message_handler import (
    MessageHandler,
    MessageSender,
    MessageQueue,
    create_test_messages
)
from core.message_reader_interface import (
    WeChatMessage,
    MessageType,
    ChatType
)


class TestMessageQueue(unittest.TestCase):
    """消息队列测试"""
    
    def setUp(self):
        self.queue = MessageQueue(max_size=10)
    
    def test_put_and_get(self):
        """测试添加和获取消息"""
        msg = WeChatMessage(
            message_id="test_1",
            sender_id="user_1",
            sender_name="测试用户",
            chat_id="chat_1",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="测试内容"
        )
        
        self.assertTrue(self.queue.put(msg))
        self.assertEqual(self.queue.size(), 1)
        
        retrieved = self.queue.get(timeout=1)
        self.assertEqual(retrieved.message_id, "test_1")
        self.assertTrue(self.queue.is_empty())
    
    def test_batch_get(self):
        """测试批量获取"""
        messages = create_test_messages(5)
        for msg in messages:
            self.queue.put(msg)
        
        batch = self.queue.get_batch(3)
        self.assertEqual(len(batch), 3)
        self.assertEqual(self.queue.size(), 2)
    
    def test_queue_overflow(self):
        """测试队列溢出"""
        messages = create_test_messages(15)
        for msg in messages:
            self.queue.put(msg)
        
        # 队列应该只保留最新的max_size条
        self.assertEqual(self.queue.size(), 10)
    
    def test_clear(self):
        """测试清空队列"""
        messages = create_test_messages(5)
        for msg in messages:
            self.queue.put(msg)
        
        self.queue.clear()
        self.assertTrue(self.queue.is_empty())


class TestMessageHandler(unittest.TestCase):
    """消息处理器测试"""
    
    def setUp(self):
        self.handler = MessageHandler(config={'queue_size': 100})
    
    def test_callback_registration(self):
        """测试回调注册"""
        def callback(msg):
            pass
        
        self.handler.register_callback(callback)
        self.assertEqual(len(self.handler._callbacks), 1)
        
        self.handler.unregister_callback(callback)
        self.assertEqual(len(self.handler._callbacks), 0)
    
    def test_parse_message_type(self):
        """测试消息类型解析"""
        # 文本消息
        msg_type = self.handler.parse_message_type("你好")
        self.assertEqual(msg_type, MessageType.TEXT)
        
        # 图片消息
        msg_type = self.handler.parse_message_type("[图片]风景照")
        self.assertEqual(msg_type, MessageType.IMAGE)
        
        # 文件消息
        msg_type = self.handler.parse_message_type("[文件]report.pdf")
        self.assertEqual(msg_type, MessageType.FILE)
        
        # 视频消息
        msg_type = self.handler.parse_message_type("[视频]video.mp4")
        self.assertEqual(msg_type, MessageType.VIDEO)
        
        # 链接消息
        msg_type = self.handler.parse_message_type("[链接]https://example.com")
        self.assertEqual(msg_type, MessageType.LINK)
    
    def test_parse_at_users(self):
        """测试@用户解析"""
        content = "@张三 @李四 你们好"
        at_users = self.handler._parse_at_users(content)
        self.assertIn("张三", at_users)
        self.assertIn("李四", at_users)
    
    def test_create_message(self):
        """测试创建消息"""
        msg = self.handler.create_message(
            message_id="msg_1",
            sender_id="user_1",
            sender_name="张三",
            chat_id="chat_1",
            chat_name="技术群",
            chat_type="group",
            content="大家好"
        )
        
        self.assertEqual(msg.chat_type, ChatType.GROUP)
        self.assertEqual(msg.content, "大家好")
    
    def test_add_and_get_message(self):
        """测试添加和获取消息"""
        msg = WeChatMessage(
            message_id="test_1",
            sender_id="user_1",
            sender_name="测试用户",
            chat_id="chat_1",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="测试内容"
        )
        
        self.handler.add_message(msg)
        
        retrieved = self.handler.get_message(timeout=1)
        self.assertEqual(retrieved.message_id, "test_1")
    
    def test_listening(self):
        """测试消息监听"""
        self.handler.start_listening()
        self.assertTrue(self.handler._listening)
        
        time.sleep(2)  # 等待消息
        
        self.handler.stop_listening()
        self.assertFalse(self.handler._listening)
    
    def test_handler_info(self):
        """测试获取处理器信息"""
        info = self.handler.get_handler_info()
        
        self.assertEqual(info['handler_type'], 'MessageHandler')
        self.assertIn('is_listening', info)
        self.assertIn('queue_size', info)


class TestMessageSender(unittest.TestCase):
    """消息发送器测试"""
    
    def setUp(self):
        self.sender = MessageSender()
    
    def test_initialization(self):
        """测试初始化"""
        result = self.sender._initialize()
        self.assertTrue(result)
        self.assertTrue(self.sender._initialized)
    
    def test_send_text_message(self):
        """测试发送文本消息"""
        result = self.sender.send_text_message("chat_1", "测试消息")
        # 返回True表示发送逻辑正常（模拟环境）
        self.assertTrue(result)
    
    def test_send_image_message(self):
        """测试发送图片消息"""
        result = self.sender.send_image_message(
            "chat_1",
            "test.jpg",
            "测试图片"
        )
        self.assertTrue(result)
    
    def test_send_file_message(self):
        """测试发送文件消息"""
        result = self.sender.send_file_message(
            "chat_1",
            "test.pdf"
        )
        self.assertTrue(result)
    
    def test_send_group_message(self):
        """测试发送群消息"""
        result = self.sender.send_group_message("group_1", "群消息测试")
        self.assertTrue(result)
    
    def test_send_at_message(self):
        """测试发送@消息"""
        result = self.sender.send_at_message(
            "group_1",
            "user_123",
            "张三",
            "请查看"
        )
        self.assertTrue(result)
    
    def test_sender_info(self):
        """测试获取发送器信息"""
        info = self.sender.get_sender_info()
        
        self.assertEqual(info['sender_type'], 'MessageSender')
        self.assertIn('is_initialized', info)


class TestMessageCreation(unittest.TestCase):
    """消息创建测试"""
    
    def test_message_to_dict(self):
        """测试消息转字典"""
        msg = WeChatMessage(
            message_id="msg_1",
            sender_id="user_1",
            sender_name="张三",
            chat_id="chat_1",
            chat_name="测试会话",
            chat_type=ChatType.PRIVATE,
            content="你好"
        )
        
        data = msg.to_dict()
        
        self.assertEqual(data['message_id'], "msg_1")
        self.assertEqual(data['sender_id'], "user_1")
        self.assertEqual(data['chat_type'], "private")
        self.assertEqual(data['message_type'], "text")
    
    def test_message_from_dict(self):
        """测试从字典创建消息"""
        data = {
            'message_id': 'msg_1',
            'sender_id': 'user_1',
            'sender_name': '张三',
            'chat_id': 'chat_1',
            'chat_name': '测试会话',
            'chat_type': 'group',
            'content': '你好',
            'message_type': 'text',
            'timestamp': '2024-01-01T12:00:00',
            'is_mentioned': False,
            'at_user_ids': []
        }
        
        msg = WeChatMessage.from_dict(data)
        
        self.assertEqual(msg.message_id, "msg_1")
        self.assertEqual(msg.chat_type, ChatType.GROUP)
    
    def test_create_test_messages(self):
        """测试创建测试消息"""
        messages = create_test_messages(10)
        
        self.assertEqual(len(messages), 10)
        for msg in messages:
            self.assertIsInstance(msg, WeChatMessage)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMessageQueue))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageSender))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageCreation))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "="*50)
    print(f"测试完成: {result.testsRun} 个测试")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*50)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)