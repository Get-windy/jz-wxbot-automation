# -*- coding: utf-8 -*-
"""
消息读取器测试
测试 wechat_reader.py 和 wxwork_reader.py 的功能
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, '..')

from readers.wechat_reader import WeChatMessageReader
from readers.wxwork_reader import WXWorkMessageReader


class TestWeChatMessageReaderInit:
    """测试个人微信消息读取器初始化"""
    
    def test_wechat_reader_initialization(self):
        """测试读取器可以正常初始化"""
        config = {'check_interval': 1.0}
        reader = WeChatMessageReader(config)
        
        assert reader is not None
        assert reader.config == config
        assert reader.wechat_pid is None
        assert reader.main_window_hwnd is None
    
    def test_default_config(self):
        """测试默认配置"""
        reader = WeChatMessageReader()
        
        assert reader.is_initialized is False
        assert reader.wechat_pid is None
    
    def test_process_names(self):
        """测试微信进程名"""
        reader = WeChatMessageReader()
        
        assert 'WeChat.exe' in reader.process_names
        assert 'Weixin.exe' in reader.process_names
        assert 'wechat.exe' in reader.process_names


class TestWeChatMessageReaderMethods:
    """测试个人微信消息读取器方法"""
    
    @pytest.fixture
    def reader(self):
        """创建读取器实例"""
        return WeChatMessageReader()
    
    def test_human_ops_initialized(self, reader):
        """测试人性化操作模块已初始化"""
        assert reader.human_ops is not None
    
    def test_stop_event_initialized(self, reader):
        """测试停止事件已初始化"""
        assert reader._stop_event is not None
        assert reader._stop_event.is_set() is False
    
    def test_message_cache(self, reader):
        """测试消息缓存"""
        assert isinstance(reader._message_cache, list)
        assert len(reader._message_cache) == 0
    
    def test_last_message_time(self, reader):
        """测试最后消息时间"""
        assert isinstance(reader._last_message_time, datetime)


class TestWeChatReaderProcess:
    """测试进程查找"""
    
    @pytest.fixture
    def reader(self):
        """创建读取器实例"""
        return WeChatMessageReader()
    
    def test_find_wechat_process_not_found(self, reader):
        """测试未找到微信进程"""
        with patch('psutil.process_iter') as mock_iter:
            mock_iter.return_value = []
            result = reader._find_wechat_process()
            assert result is False
    
    def test_find_wechat_process_found(self, reader):
        """测试找到微信进程"""
        mock_proc = Mock()
        mock_proc.info = {'pid': 12345, 'name': 'WeChat.exe'}
        
        with patch('psutil.process_iter') as mock_iter:
            mock_iter.return_value = [mock_proc]
            result = reader._find_wechat_process()
            assert result is True
            assert reader.wechat_pid == 12345


class TestWxWorkMessageReaderInit:
    """测试企业微信消息读取器初始化"""
    
    def test_wxwork_reader_initialization(self):
        """测试企业微信读取器可以正常初始化"""
        config = {'check_interval': 1.0}
        reader = WXWorkMessageReader(config)
        
        assert reader is not None
        assert reader.config == config
    
    def test_default_config(self):
        """测试默认配置"""
        reader = WXWorkMessageReader()
        
        assert reader.is_initialized is False
        assert reader.wxwork_pid is None
    
    def test_process_names(self):
        """测试企业微信进程名"""
        reader = WXWorkMessageReader()
        
        assert 'wxwork.exe' in reader.process_names
        assert 'WeCom.exe' in reader.process_names


class TestWxWorkMessageReaderMethods:
    """测试企业微信消息读取器方法"""
    
    @pytest.fixture
    def reader(self):
        """创建读取器实例"""
        return WXWorkMessageReader()
    
    def test_human_ops_initialized(self, reader):
        """测试人性化操作模块已初始化"""
        assert reader.human_ops is not None
    
    def test_stop_event_initialized(self, reader):
        """测试停止事件已初始化"""
        assert reader._stop_event is not None
    
    def test_message_cache(self, reader):
        """测试消息缓存"""
        assert isinstance(reader._message_cache, list)
        assert len(reader._message_cache) == 0


class TestWxWorkReaderProcess:
    """测试企业微信进程查找"""
    
    @pytest.fixture
    def reader(self):
        """创建读取器实例"""
        return WXWorkMessageReader()
    
    def test_find_wxwork_process_not_found(self, reader):
        """测试未找到企业微信进程"""
        with patch('psutil.process_iter') as mock_iter:
            mock_iter.return_value = []
            result = reader._find_wxwork_process()
            assert result is False
    
    def test_find_wxwork_process_found(self, reader):
        """测试找到企业微信进程"""
        mock_proc = Mock()
        mock_proc.info = {'pid': 54321, 'name': 'wxwork.exe'}
        
        with patch('psutil.process_iter') as mock_iter:
            mock_iter.return_value = [mock_proc]
            result = reader._find_wxwork_process()
            assert result is True
            assert reader.wxwork_pid == 54321


class TestReaderComparison:
    """测试两种读取器的对比"""
    
    def test_both_readers_have_same_interface(self):
        """测试两个读取器有相同的接口"""
        wechat_reader = WeChatMessageReader()
        wxwork_reader = WxWorkMessageReader()
        
        # 检查共同的方法
        assert hasattr(wechat_reader, 'initialize')
        assert hasattr(wechat_reader, 'start_listening')
        assert hasattr(wechat_reader, 'stop_listening')
        assert hasattr(wechat_reader, 'get_messages')
        
        assert hasattr(wxwork_reader, 'initialize')
        assert hasattr(wxwork_reader, 'start_listening')
        assert hasattr(wxwork_reader, 'stop_listening')
        assert hasattr(wxwork_reader, 'get_messages')
    
    def test_different_process_names(self):
        """测试不同的进程名"""
        wechat_reader = WeChatMessageReader()
        wxwork_reader = WXWorkMessageReader()
        
        # 进程名应该不同
        assert wechat_reader.process_names != wxwork_reader.process_names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])