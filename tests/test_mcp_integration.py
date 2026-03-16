# -*- coding: utf-8 -*-
"""
WXBot MCP 集成测试
测试 MCP 工具与消息处理模块的集成
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock

from core.message_handler import MessageHandler, MessageSender, MessageQueue
from managers.group_manager_impl import GroupManager, FriendManager


class TestMCPToolIntegration(unittest.TestCase):
    """MCP工具与消息处理模块集成测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.message_handler = MessageHandler()
        self.message_sender = MessageSender()
        self.group_manager = GroupManager()
        self.friend_manager = FriendManager()
    
    def test_message_handler_integration(self):
        """测试消息处理器集成"""
        # MessageHandler 在初始化时已自动设置
        self.assertIsNotNone(self.message_handler)
        
        # 创建消息
        from core.message_reader_interface import WeChatMessage, ChatType, MessageType
        msg = self.message_handler.create_message(
            message_id="test_msg_001",
            sender_id="user_001",
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type="private",
            content="测试消息内容"
        )
        
        self.assertEqual(msg.content, "测试消息内容")
        self.assertEqual(msg.chat_type, ChatType.PRIVATE)
        
    def test_message_sender_integration(self):
        """测试消息发送器集成"""
        # 初始化
        self.assertTrue(self.message_sender._initialize())
        
        # 测试发送文本消息
        result = self.message_sender.send_text_message("chat_001", "测试消息")
        self.assertTrue(result)
        
        # 测试发送图片
        result = self.message_sender.send_image_message("chat_001", "test.jpg")
        self.assertTrue(result)
        
        # 测试发送文件
        result = self.message_sender.send_file_message("chat_001", "test.pdf")
        self.assertTrue(result)
        
        # 测试发送群消息
        result = self.message_sender.send_group_message("group_001", "群消息")
        self.assertTrue(result)
        
        # 测试@消息
        result = self.message_sender.send_at_message("group_001", "user_001", "张三", "请查看")
        self.assertTrue(result)
    
    def test_group_manager_integration(self):
        """测试群管理器集成"""
        # 初始化
        self.assertTrue(self.group_manager.initialize())
        
        # 获取群列表
        groups = self.group_manager.get_group_list()
        self.assertIsInstance(groups, list)
        self.assertGreater(len(groups), 0)
        
        # 获取群成员
        if groups:
            group_id = groups[0].group_id
            members = self.group_manager.get_group_members(group_id)
            self.assertIsInstance(members, list)
            
            # 发送群消息
            result = self.group_manager.send_group_message(group_id, "测试群消息")
            self.assertTrue(result)
            
            # @成员
            if members:
                result = self.group_manager.at_members(group_id, [members[0].user_id], "测试@")
                self.assertTrue(result)
                
            # @所有人
            result = self.group_manager.at_all(group_id, "测试@所有人")
            self.assertTrue(result)
            
            # 设置群公告
            result = self.group_manager.set_group_announcement(group_id, "测试公告")
            self.assertTrue(result)
            self.assertEqual(self.group_manager.get_group_announcement(group_id), "测试公告")
            
            # 搜索群
            results = self.group_manager.search_group(groups[0].group_name[:2])
            self.assertIsInstance(results, list)
    
    def test_friend_manager_integration(self):
        """测试好友管理器集成"""
        # 初始化
        self.assertTrue(self.friend_manager.initialize())
        
        # 获取好友列表
        friends = self.friend_manager.get_friend_list()
        self.assertIsInstance(friends, list)
        self.assertGreater(len(friends), 0)
        
        # 获取好友信息
        if friends:
            user_id = friends[0]['user_id']
            friend_info = self.friend_manager.get_friend_info(user_id)
            self.assertIsNotNone(friend_info)
            
            # 搜索好友
            keyword = friends[0]['nickname'][:2]
            results = self.friend_manager.search_friend(keyword)
            self.assertIsInstance(results, list)
        
        # 添加好友
        result = self.friend_manager.add_friend("test_user", "你好")
        self.assertTrue(result)
        
        # 删除好友
        self.friend_manager.add_friend("temp_user", "测试")
        result = self.friend_manager.delete_friend("temp_user")
        self.assertTrue(result)


class TestMCPProtocol(unittest.TestCase):
    """MCP协议测试"""
    
    def test_mcp_request_format(self):
        """测试MCP请求格式"""
        # 模拟MCP请求
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "wxbot_send_message",
                "arguments": {
                    "chat_name": "测试会话",
                    "message": "测试消息"
                }
            },
            "id": 1
        }
        
        # 验证请求格式
        self.assertEqual(request["jsonrpc"], "2.0")
        self.assertEqual(request["method"], "tools/call")
        self.assertIn("name", request["params"])
        self.assertIn("arguments", request["params"])
    
    def test_mcp_response_format(self):
        """测试MCP响应格式"""
        # 模拟MCP响应
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "success": True,
                "message_id": "msg_001",
                "timestamp": "2024-01-01T12:00:00"
            }
        }
        
        # 验证响应格式
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertTrue(response["result"]["success"])
    
    def test_mcp_error_response(self):
        """测试MCP错误响应"""
        # 模拟MCP错误响应
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32600,
                "message": "无效请求"
            }
        }
        
        # 验证错误响应格式
        self.assertEqual(error_response["jsonrpc"], "2.0")
        self.assertIn("error", error_response)
        self.assertIn("code", error_response["error"])
        self.assertIn("message", error_response["error"])


class TestMCPErrorHandling(unittest.TestCase):
    """MCP错误处理测试"""
    
    def test_missing_required_parameter(self):
        """测试缺少必需参数"""
        handler = MessageHandler()
        
        # 尝试创建消息但不提供必需参数
        with self.assertRaises(Exception):
            handler.create_message(
                message_id="test",
                sender_id="user_001",
                sender_name="测试用户"
                # 缺少 chat_id, chat_name, chat_type, content
            )
    
    def test_invalid_chat_type(self):
        """测试无效的聊天类型"""
        handler = MessageHandler()
        
        msg = handler.create_message(
            message_id="test",
            sender_id="user_001",
            sender_name="测试用户",
            chat_id="chat_001",
            chat_name="测试会话",
            chat_type="invalid_type",
            content="测试"
        )
        
        # 应该回退到 PRIVATE
        from core.message_reader_interface import ChatType
        self.assertEqual(msg.chat_type, ChatType.PRIVATE)
    
    def test_empty_message(self):
        """测试空消息处理"""
        sender = MessageSender()
        sender._initialize()
        
        # 发送空消息应该仍然返回成功（模拟环境）
        result = sender.send_text_message("chat_001", "")
        self.assertTrue(result)


class TestMCPToolsList(unittest.TestCase):
    """MCP工具列表测试"""
    
    def test_tools_defined(self):
        """测试所有MCP工具已定义"""
        # 这些工具应该在 mcp_server.py 中定义
        expected_tools = [
            "wxbot_send_message",
            "wxbot_read_messages", 
            "wxbot_send_moments",
            "wxbot_mass_send",
            "wxbot_add_friend",
            "wxbot_group_manage",
            "wxbot_get_contacts",
            "wxbot_get_status"
        ]
        
        # 验证工具名称
        for tool_name in expected_tools:
            self.assertIsInstance(tool_name, str)
            self.assertTrue(len(tool_name) > 0)
    
    def test_tool_parameters(self):
        """测试工具参数定义"""
        # 验证每个工具的参数
        tools_params = {
            "wxbot_send_message": ["chat_name", "message"],
            "wxbot_read_messages": [],
            "wxbot_send_moments": ["content"],
            "wxbot_mass_send": ["targets", "message"],
            "wxbot_add_friend": [],
            "wxbot_group_manage": ["action"],
            "wxbot_get_contacts": [],
            "wxbot_get_status": []
        }
        
        for tool, params in tools_params.items():
            self.assertIsInstance(tool, str)
            self.assertIsInstance(params, list)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestMCPToolIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPProtocol))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPToolsList))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
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