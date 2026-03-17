# -*- coding: utf-8 -*-
"""
消息接收模块测试
"""

import unittest
import asyncio
import threading
import time
import queue

from core.messages import (
    MessageParser,
    MessageListener,
    AsyncMessageQueue,
    SyncMessageQueue,
    RawWeChatMessage,
    WeChatMessageType,
    MessageSource,
    MessageProcessor,
    TextMessageHandler,
    AtMessageHandler,
    CommandMessageHandler,
)

from core.message_reader_interface import WeChatMessage, MessageType, ChatType


class TestMessageParser(unittest.TestCase):
    """消息解析器测试"""
    
    def setUp(self):
        self.parser = MessageParser(my_user_id='self', my_nickname='小助手')
    
    def test_parse_text_message(self):
        """测试解析文本消息"""
        raw = RawWeChatMessage(
            msg_id='msg_001',
            msg_type=WeChatMessageType.TEXT,
            from_user='user_123',
            from_nickname='张三',
            content='你好'
        )
        
        msg = self.parser.parse(raw)
        
        self.assertEqual(msg.message_id, 'msg_001')
        self.assertEqual(msg.sender_name, '张三')
        self.assertEqual(msg.content, '你好')
        self.assertEqual(msg.message_type, MessageType.TEXT)
    
    def test_parse_image_message(self):
        """测试解析图片消息"""
        raw = RawWeChatMessage(
            msg_id='msg_002',
            msg_type=WeChatMessageType.IMAGE,
            from_user='user_123',
            from_nickname='张三',
            content='[图片]'
        )
        
        msg = self.parser.parse(raw)
        
        self.assertEqual(msg.message_type, MessageType.IMAGE)
    
    def test_parse_group_message(self):
        """测试解析群消息"""
        raw = RawWeChatMessage(
            msg_id='msg_003',
            msg_type=WeChatMessageType.TEXT,
            from_user='user_456',
            from_nickname='李四',
            room_id='room_001',
            room_name='测试群',
            content='大家好'
        )
        
        msg = self.parser.parse(raw)
        
        self.assertEqual(msg.chat_type, ChatType.GROUP)
        self.assertEqual(msg.chat_name, '测试群')
    
    def test_parse_at_message(self):
        """测试解析@消息"""
        raw = RawWeChatMessage(
            msg_id='msg_004',
            msg_type=WeChatMessageType.TEXT,
            from_user='user_456',
            from_nickname='李四',
            room_id='room_001',
            room_name='测试群',
            content='@小助手 你好'
        )
        
        msg = self.parser.parse(raw)
        
        self.assertTrue(msg.is_mentioned)
        self.assertIn('小助手', msg.at_user_ids)


class TestAsyncMessageQueue(unittest.TestCase):
    """异步消息队列测试"""
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.queue = AsyncMessageQueue(max_size=10)
    
    def tearDown(self):
        self.loop.close()
    
    def test_put_and_get(self):
        """测试添加和获取"""
        async def test():
            msg = WeChatMessage(
                message_id='test_001',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='测试',
                message_type=MessageType.TEXT
            )
            
            await self.queue.put(msg)
            self.assertEqual(self.queue.qsize(), 1)
            
            result = await self.queue.get(timeout=1)
            self.assertEqual(result.message_id, 'test_001')
        
        self.loop.run_until_complete(test())
    
    def test_get_batch(self):
        """测试批量获取"""
        async def test():
            # 添加多条消息
            for i in range(5):
                msg = WeChatMessage(
                    message_id=f'test_{i}',
                    sender_id='user_1',
                    sender_name='用户',
                    chat_id='chat_1',
                    chat_name='聊天',
                    chat_type=ChatType.PRIVATE,
                    content=f'消息 {i}',
                    message_type=MessageType.TEXT
                )
                await self.queue.put(msg)
            
            # 批量获取
            messages = await self.queue.get_batch(count=3)
            self.assertEqual(len(messages), 3)
        
        self.loop.run_until_complete(test())
    
    def test_timeout(self):
        """测试超时"""
        async def test():
            result = await self.queue.get(timeout=0.5)
            self.assertIsNone(result)
        
        self.loop.run_until_complete(test())


class TestSyncMessageQueue(unittest.TestCase):
    """同步消息队列测试"""
    
    def setUp(self):
        self.queue = SyncMessageQueue(max_size=10)
    
    def test_put_and_get(self):
        """测试添加和获取"""
        msg = WeChatMessage(
            message_id='test_001',
            sender_id='user_1',
            sender_name='用户',
            chat_id='chat_1',
            chat_name='聊天',
            chat_type=ChatType.PRIVATE,
            content='测试',
            message_type=MessageType.TEXT
        )
        
        self.queue.put(msg)
        self.assertEqual(self.queue.qsize(), 1)
        
        result = self.queue.get(timeout=1)
        self.assertEqual(result.message_id, 'test_001')
    
    def test_thread_safety(self):
        """测试线程安全"""
        results = []
        results_lock = threading.Lock()
        
        def producer():
            for i in range(20):
                msg = WeChatMessage(
                    message_id=f'prod_{i}',
                    sender_id='user_1',
                    sender_name='用户',
                    chat_id='chat_1',
                    chat_name='聊天',
                    chat_type=ChatType.PRIVATE,
                    content=f'消息 {i}',
                    message_type=MessageType.TEXT
                )
                self.queue.put(msg)
                time.sleep(0.01)
        
        def consumer():
            for _ in range(20):
                try:
                    msg = self.queue.get(timeout=2)
                    with results_lock:
                        results.append(msg.message_id)
                except queue.Empty:
                    break
        
        t1 = threading.Thread(target=producer)
        t2 = threading.Thread(target=consumer)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        self.assertEqual(len(results), 20)


class TestTextMessageHandler(unittest.TestCase):
    """文本消息处理器测试"""
    
    def setUp(self):
        self.handler = TextMessageHandler({
            'hello': '你好！',
            '天气': '今天天气很好！',
            'help': '你可以问我天气、时间等问题',
        })
    
    def test_keyword_match(self):
        """测试关键词匹配"""
        async def test():
            msg = WeChatMessage(
                message_id='test_001',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='hello world',
                message_type=MessageType.TEXT
            )
            
            result = await self.handler.handle(msg)
            self.assertEqual(result, '你好！')
        
        asyncio.run(test())
    
    def test_no_match(self):
        """测试无匹配"""
        async def test():
            msg = WeChatMessage(
                message_id='test_002',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='random text',
                message_type=MessageType.TEXT
            )
            
            result = await self.handler.handle(msg)
            self.assertIsNone(result)
        
        asyncio.run(test())


class TestAtMessageHandler(unittest.TestCase):
    """@消息处理器测试"""
    
    def setUp(self):
        self.handler = AtMessageHandler(bot_name='小助手')
    
    def test_at_message(self):
        """测试@消息"""
        async def test():
            msg = WeChatMessage(
                message_id='test_001',
                sender_id='user_1',
                sender_name='用户',
                chat_id='room_1',
                chat_name='测试群',
                chat_type=ChatType.GROUP,
                content='@小助手 你好',
                message_type=MessageType.TEXT,
                is_mentioned=True
            )
            
            result = await self.handler.handle(msg)
            self.assertEqual(result, '收到: 你好')
        
        asyncio.run(test())
    
    def test_not_at_me(self):
        """测试非@我"""
        async def test():
            msg = WeChatMessage(
                message_id='test_002',
                sender_id='user_1',
                sender_name='用户',
                chat_id='room_1',
                chat_name='测试群',
                chat_type=ChatType.GROUP,
                content='@其他人 你好',
                message_type=MessageType.TEXT,
                is_mentioned=False
            )
            
            result = await self.handler.handle(msg)
            self.assertIsNone(result)
        
        asyncio.run(test())


class TestCommandMessageHandler(unittest.TestCase):
    """命令消息处理器测试"""
    
    def setUp(self):
        self.handler = CommandMessageHandler()
    
    def test_help_command(self):
        """测试help命令"""
        async def test():
            msg = WeChatMessage(
                message_id='test_001',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='/help',
                message_type=MessageType.TEXT
            )
            
            result = await self.handler.handle(msg)
            self.assertIn('help', result.lower())
        
        asyncio.run(test())
    
    def test_ping_command(self):
        """测试ping命令"""
        async def test():
            msg = WeChatMessage(
                message_id='test_002',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='/ping',
                message_type=MessageType.TEXT
            )
            
            result = await self.handler.handle(msg)
            self.assertEqual(result, 'pong')
        
        asyncio.run(test())
    
    def test_status_command(self):
        """测试status命令"""
        async def test():
            msg = WeChatMessage(
                message_id='test_003',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='/status',
                message_type=MessageType.TEXT
            )
            
            result = await self.handler.handle(msg)
            self.assertIn('状态', result)
        
        asyncio.run(test())
    
    def test_unknown_command(self):
        """测试未知命令"""
        async def test():
            msg = WeChatMessage(
                message_id='test_004',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='/unknown',
                message_type=MessageType.TEXT
            )
            
            result = await self.handler.handle(msg)
            self.assertIn('未知命令', result)
        
        asyncio.run(test())


class TestMessageProcessor(unittest.TestCase):
    """消息处理器测试"""
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.processor = MessageProcessor({'my_nickname': '小助手'})
    
    def tearDown(self):
        self.loop.close()
    
    def test_register_handler(self):
        """测试注册处理器"""
        async def test():
            received = []
            
            def callback(msg):
                received.append(msg)
            
            self.processor.on_message(callback)
            self.processor.register_handler('text', TextMessageHandler({
                'test': '响应'
            }).handle)
        
        self.loop.run_until_complete(test())
    
    def test_put_message(self):
        """测试手动添加消息"""
        async def test():
            msg = WeChatMessage(
                message_id='test_001',
                sender_id='user_1',
                sender_name='用户',
                chat_id='chat_1',
                chat_name='聊天',
                chat_type=ChatType.PRIVATE,
                content='test',
                message_type=MessageType.TEXT
            )
            
            await self.processor.put_message(msg)
            await asyncio.sleep(0.1)
            
            self.assertEqual(self.processor.queue.qsize(), 1)
        
        self.loop.run_until_complete(test())


if __name__ == '__main__':
    unittest.main(verbosity=2)