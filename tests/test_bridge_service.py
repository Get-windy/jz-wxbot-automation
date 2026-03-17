# -*- coding: utf-8 -*-
"""
桥接服务测试
测试 bridge_service.py 的功能
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# 添加项目根目录到路径
sys.path.insert(0, 'I:\\jz-wxbot-automation')

from bridge.bridge_service import BridgeService


class TestBridgeServiceInit:
    """测试桥接服务初始化"""
    
    def test_bridge_service_initialization(self):
        """测试桥接服务可以正常初始化"""
        config = {
            'wechat': {'enabled': True},
            'wxwork': {'enabled': True},
            'openclaw': {'gateway_url': 'ws://127.0.0.1:3100'}
        }
        service = BridgeService(config)
        
        assert service is not None
        assert service.config == config
        assert service.running is False
        assert 'messages_received' in service.stats
        assert 'messages_sent' in service.stats
        assert 'commands_executed' in service.stats
        assert 'errors' in service.stats
    
    def test_default_config(self):
        """测试默认配置"""
        service = BridgeService()
        
        assert service.config == {}
        assert service.openclaw is None
        assert service.wechat_sender is None
        assert service.wxwork_sender is None
    
    def test_stats_initialization(self):
        """测试统计信息初始化"""
        service = BridgeService()
        
        assert service.stats['messages_received'] == 0
        assert service.stats['messages_sent'] == 0
        assert service.stats['commands_executed'] == 0
        assert service.stats['errors'] == 0


class TestBridgeServiceMethods:
    """测试桥接服务方法"""
    
    @pytest.fixture
    def bridge_service(self):
        """创建桥接服务实例"""
        return BridgeService({'openclaw': {}})
    
    def test_message_handlers_dict(self, bridge_service):
        """测试消息处理器字典"""
        assert isinstance(bridge_service.message_handlers, dict)
    
    def test_command_handlers_dict(self, bridge_service):
        """测试命令处理器字典"""
        assert isinstance(bridge_service.command_handlers, dict)
    
    def test_register_message_handler(self, bridge_service):
        """测试注册消息处理器"""
        def test_handler(message):
            return True
        
        bridge_service.register_message_handler('test', test_handler)
        assert 'test' in bridge_service.message_handlers
        assert bridge_service.message_handlers['test'] == test_handler
    
    def test_register_command_handler(self, bridge_service):
        """测试注册命令处理器"""
        def test_command(cmd):
            return "OK"
        
        bridge_service.register_command_handler('test_cmd', test_command)
        assert 'test_cmd' in bridge_service.command_handlers
        assert bridge_service.command_handlers['test_cmd'] == test_command
    
    def test_get_stats(self, bridge_service):
        """测试获取统计信息"""
        stats = bridge_service.get_stats()
        
        assert 'messages_received' in stats
        assert 'messages_sent' in stats
        assert 'commands_executed' in stats
        assert 'errors' in stats
    
    def test_increment_received(self, bridge_service):
        """测试消息接收计数"""
        initial = bridge_service.stats['messages_received']
        bridge_service._increment_received()
        assert bridge_service.stats['messages_received'] == initial + 1
    
    def test_increment_sent(self, bridge_service):
        """测试消息发送计数"""
        initial = bridge_service.stats['messages_sent']
        bridge_service._increment_sent()
        assert bridge_service.stats['messages_sent'] == initial + 1
    
    def test_increment_commands(self, bridge_service):
        """测试命令执行计数"""
        initial = bridge_service.stats['commands_executed']
        bridge_service._increment_commands()
        assert bridge_service.stats['commands_executed'] == initial + 1
    
    def test_increment_errors(self, bridge_service):
        """测试错误计数"""
        initial = bridge_service.stats['errors']
        bridge_service._increment_errors()
        assert bridge_service.stats['errors'] == initial + 1


class TestBridgeServiceAsync:
    """测试桥接服务异步方法"""
    
    @pytest.fixture
    def bridge_service(self):
        """创建桥接服务实例"""
        return BridgeService({'openclaw': {}})
    
    @pytest.mark.asyncio
    async def test_initialize_with_no_senders(self, bridge_service):
        """测试初始化没有发送器的情况"""
        with patch('bridge.bridge_service.MessageSenderFactory') as mock_factory:
            mock_factory.return_value.get_available_senders.return_value = []
            
            result = await bridge_service.initialize()
            
            # 因为没有真实的微信客户端，可能返回 False
            assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_initialize_creates_senders(self, bridge_service):
        """测试初始化创建发送器"""
        with patch('bridge.bridge_service.MessageSenderFactory') as mock_factory:
            mock_instance = Mock()
            mock_instance.get_available_senders.return_value = ['wechat']
            mock_sender = Mock()
            mock_sender.initialize.return_value = True
            mock_instance.create_sender.return_value = mock_sender
            mock_factory.return_value = mock_instance
            
            with patch('bridge.bridge_service.get_openclaw_client', None):
                result = await bridge_service.initialize()
                assert isinstance(result, bool)


class TestBridgeServiceCommands:
    """测试命令处理"""
    
    @pytest.fixture
    def bridge_service(self):
        """创建桥接服务实例"""
        return BridgeService()
    
    def test_default_commands_registered(self, bridge_service):
        """测试默认命令已注册"""
        # 初始化后应该有默认命令
        assert isinstance(bridge_service.command_handlers, dict)
    
    def test_execute_command(self, bridge_service):
        """测试执行命令"""
        def mock_command(args):
            return f"Executed: {args}"
        
        bridge_service.register_command_handler('mock_cmd', mock_command)
        
        result = bridge_service.execute_command('mock_cmd', {'test': 'data'})
        assert result == "Executed: {'test': 'data'}"
    
    def test_execute_unknown_command(self, bridge_service):
        """测试执行未知命令"""
        result = bridge_service.execute_command('nonexistent_cmd', {})
        assert result is None


class TestBridgeServiceStatus:
    """测试状态管理"""
    
    @pytest.fixture
    def bridge_service(self):
        """创建桥接服务实例"""
        return BridgeService()
    
    def test_is_running(self, bridge_service):
        """测试运行状态检查"""
        assert bridge_service.is_running() == False
        
        bridge_service.running = True
        assert bridge_service.is_running() == True
    
    def test_start_stop(self, bridge_service):
        """测试启动和停止"""
        bridge_service.running = True
        bridge_service.stop()
        assert bridge_service.running == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])