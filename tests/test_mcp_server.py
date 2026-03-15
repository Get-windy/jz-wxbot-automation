# -*- coding: utf-8 -*-
"""
MCP Server 测试模块
版本: v1.0.0
功能: 测试 MCP Server 的各项功能
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server import WxBotMCPServer, MCPProtocolHandler, TOOLS


class TestMCPTools(unittest.TestCase):
    """测试 MCP 工具定义"""
    
    def test_tools_count(self):
        """测试工具数量"""
        self.assertEqual(len(TOOLS), 8)
    
    def test_tool_names(self):
        """测试工具名称"""
        expected_names = [
            "wxbot_send_message",
            "wxbot_read_messages",
            "wxbot_send_moments",
            "wxbot_mass_send",
            "wxbot_add_friend",
            "wxbot_group_manage",
            "wxbot_get_contacts",
            "wxbot_get_status"
        ]
        actual_names = [tool.name for tool in TOOLS]
        self.assertEqual(sorted(actual_names), sorted(expected_names))
    
    def test_send_message_schema(self):
        """测试发送消息工具的模式定义"""
        tool = next(t for t in TOOLS if t.name == "wxbot_send_message")
        self.assertIn("message", tool.inputSchema["properties"])
        self.assertIn("chat_name", tool.inputSchema["properties"])
        self.assertIn("message", tool.inputSchema["required"])
    
    def test_send_moments_schema(self):
        """测试朋友圈工具的模式定义"""
        tool = next(t for t in TOOLS if t.name == "wxbot_send_moments")
        self.assertIn("content", tool.inputSchema["properties"])
        self.assertIn("images", tool.inputSchema["properties"])
        self.assertIn("visibility", tool.inputSchema["properties"])
        self.assertIn("content", tool.inputSchema["required"])


class TestWxBotMCPServer(unittest.TestCase):
    """测试 MCP Server 核心功能"""
    
    def setUp(self):
        """测试前准备"""
        self.server = WxBotMCPServer()
    
    def test_list_tools(self):
        """测试列出工具"""
        tools = self.server.list_tools()
        self.assertEqual(len(tools), 8)
        self.assertIn("name", tools[0])
        self.assertIn("description", tools[0])
        self.assertIn("inputSchema", tools[0])
    
    def test_select_sender_auto(self):
        """测试自动选择发送器"""
        # 没有发送器时返回 None
        sender = self.server._select_sender("auto")
        self.assertIsNone(sender)
    
    def test_format_message(self):
        """测试消息格式化"""
        message = "测试消息"
        formatted = self.server._format_message(message)
        self.assertEqual(formatted, message)


class TestAsyncMethods(unittest.IsolatedAsyncioTestCase):
    """测试异步方法"""
    
    async def asyncSetUp(self):
        """异步测试前准备"""
        self.server = WxBotMCPServer()
    
    async def test_get_status(self):
        """测试获取状态"""
        result = await self.server._get_status({})
        self.assertTrue(result["success"])
        self.assertIn("wechat", result)
        self.assertIn("stats", result)
        self.assertIn("version", result)
        self.assertIn("capabilities", result)
    
    async def test_send_message_validation(self):
        """测试发送消息参数验证"""
        # 空消息应该失败
        result = await self.server._send_message({})
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    async def test_send_moments_validation(self):
        """测试朋友圈参数验证"""
        # 空内容应该失败
        result = await self.server._send_moments({})
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    async def test_mass_send_validation(self):
        """测试群发参数验证"""
        # 空目标应该失败
        result = await self.server._mass_send({"message": "test"})
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        
        # 空消息应该失败
        result = await self.server._mass_send({"targets": [{"name": "test"}]})
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    async def test_add_friend_validation(self):
        """测试添加好友参数验证"""
        # 没有手机号或微信号应该失败
        result = await self.server._add_friend({})
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    async def test_group_manage_validation(self):
        """测试群管理参数验证"""
        # 没有群名称应该失败
        result = await self.server._group_manage({"action": "get_members"})
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    async def test_get_contacts(self):
        """测试获取联系人"""
        result = await self.server._get_contacts({})
        # 由于没有微信连接，可能会返回错误
        self.assertIn("success", result)


class TestMCPProtocolHandler(unittest.IsolatedAsyncioTestCase):
    """测试 MCP 协议处理器"""
    
    async def asyncSetUp(self):
        """异步测试前准备"""
        self.server = WxBotMCPServer()
        self.handler = MCPProtocolHandler(self.server)
    
    async def test_handle_tools_list(self):
        """测试处理工具列表请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        response = await self.handler.handle_request(request)
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("tools", response["result"])
    
    async def test_handle_unknown_method(self):
        """测试处理未知方法"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {}
        }
        response = await self.handler.handle_request(request)
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("error", response["result"])
    
    async def test_handle_tool_call(self):
        """测试处理工具调用"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "wxbot_get_status",
                "arguments": {}
            }
        }
        response = await self.handler.handle_request(request)
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("success", response["result"])


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """集成测试"""
    
    async def asyncSetUp(self):
        """异步测试前准备"""
        self.server = WxBotMCPServer()
    
    async def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 获取状态
        status = await self.server._get_status({})
        self.assertTrue(status["success"])
        
        # 2. 获取联系人（模拟）
        contacts = await self.server._get_contacts({"type": "all"})
        # 可能会因为无微信连接而失败
        
        # 3. 验证统计信息
        self.assertIn("messages_sent", status["stats"])
        self.assertIn("tools_called", status["stats"])


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMCPTools))
    suite.addTests(loader.loadTestsFromTestCase(TestWxBotMCPServer))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPProtocolHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    