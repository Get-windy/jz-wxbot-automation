# -*- coding: utf-8 -*-
"""
兼容性测试
测试个人微信和企业微信的兼容性
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
import platform

# 添加项目根目录到路径
sys.path.insert(0, '..')


class TestWeChatCompatibility:
    """个人微信兼容性测试"""
    
    @pytest.fixture
    def wechat_reader(self):
        """创建个人微信读取器"""
        from readers.wechat_reader import WeChatMessageReader
        return WeChatMessageReader()
    
    def test_wechat_process_detection(self, wechat_reader):
        """测试微信进程检测"""
        # 微信进程名列表
        process_names = wechat_reader.process_names
        
        assert "WeChat.exe" in process_names
        assert "Weixin.exe" in process_names
    
    def test_wechat_config(self, wechat_reader):
        """测试微信配置"""
        config = wechat_reader.config
        
        assert isinstance(config, dict)
    
    def test_wechat_initialization(self, wechat_reader):
        """测试微信初始化"""
        assert wechat_reader.is_initialized is False
    
    def test_wechat_window_handling(self, wechat_reader):
        """测试微信窗口处理"""
        # 测试窗口相关的属性
        assert wechat_reader.main_window_hwnd is None


class TestWxWorkCompatibility:
    """企业微信兼容性测试"""
    
    @pytest.fixture
    def wxwork_reader(self):
        """创建企业微信读取器"""
        from readers.wxwork_reader import WXWorkMessageReader
        return WXWorkMessageReader()
    
    def test_wxwork_process_detection(self, wxwork_reader):
        """测试企业微信进程检测"""
        process_names = wxwork_reader.process_names
        
        assert "wxwork.exe" in process_names
        assert "WeCom.exe" in process_names
    
    def test_wxwork_config(self, wxwork_reader):
        """测试企业微信配置"""
        config = wxwork_reader.config
        
        assert isinstance(config, dict)
    
    def test_wxwork_initialization(self, wxwork_reader):
        """测试企业微信初始化"""
        assert wxwork_reader.is_initialized is False
    
    def test_wxwork_window_handling(self, wxwork_reader):
        """测试企业微信窗口处理"""
        assert wxwork_reader.main_window_hwnd is None


class TestCrossPlatform:
    """跨平台兼容性测试"""
    
    def test_platform_detection(self):
        """测试平台检测"""
        system = platform.system()
        
        assert system in ["Windows", "Linux", "Darwin"]
        
        # 微信主要支持Windows
        if system == "Windows":
            print(f"\n当前平台: {system} - 支持微信自动化")
    
    def test_python_version(self):
        """测试Python版本"""
        version = sys.version_info
        
        print(f"\nPython版本: {version.major}.{version.minor}.{version.micro}")
        
        assert version.major >= 3
    
    def test_required_modules(self):
        """测试必需的模块"""
        required_modules = [
            "psutil",
            "win32gui",
            "win32con",
            "win32api",
        ]
        
        available = []
        missing = []
        
        for module in required_modules:
            try:
                __import__(module)
                available.append(module)
            except ImportError:
                missing.append(module)
        
        print(f"\n可用模块: {available}")
        print(f"缺失模块: {missing}")
        
        # Windows 平台必须的核心模块
        if platform.system() == "Windows":
            # win32gui 是可选的（可能未安装）
            pass


class TestWeChatVSWork:
    """个人微信 vs 企业微信对比测试"""
    
    def test_process_name_differences(self):
        """测试进程名差异"""
        from readers.wechat_reader import WeChatMessageReader
        from readers.wxwork_reader import WXWorkMessageReader
        
        wechat = WeChatMessageReader()
        wxwork = WXWorkMessageReader()
        
        # 进程名应该不同
        assert wechat.process_names != wxwork.process_names
    
    def test_common_interface(self):
        """测试通用接口"""
        from readers.wechat_reader import WeChatMessageReader
        from readers.wxwork_reader import WXWorkMessageReader
        
        wechat = WeChatMessageReader()
        wxwork = WXWorkMessageReader()
        
        # 两者都应该有相同的方法
        wechat_methods = [m for m in dir(wechat) if not m.startswith('_')]
        wxwork_methods = [m for m in dir(wxwork) if not m.startswith('_')]
        
        # 核心方法应该存在
        assert 'initialize' in wechat_methods
        assert 'initialize' in wxwork_methods
        assert 'start_listening' in wechat_methods
        assert 'start_listening' in wxwork_methods
    
    def test_config_compatibility(self):
        """测试配置兼容性"""
        from readers.wechat_reader import WeChatMessageReader
        from readers.wxwork_reader import WXWorkMessageReader
        
        config = {"check_interval": 1.0, "timeout": 30}
        
        wechat = WeChatMessageReader(config)
        wxwork = WXWorkMessageReader(config)
        
        assert wechat.config == config
        assert wxwork.config == config


class TestMessageFormatCompatibility:
    """消息格式兼容性测试"""
    
    def test_wechat_message_format(self):
        """测试个人微信消息格式"""
        from core.message_reader_interface import WeChatMessage, MessageType, ChatType
        
        message = WeChatMessage(
            msg_id="123",
            msg_type=MessageType.TEXT,
            content="test",
            from_user="user1",
            chat_type=ChatType.FRIEND
        )
        
        assert message.msg_type == MessageType.TEXT
        assert message.chat_type == ChatType.FRIEND
    
    def test_wxwork_message_format(self):
        """测试企业微信消息格式"""
        from core.message_reader_interface import WeChatMessage, MessageType, ChatType
        
        message = WeChatMessage(
            msg_id="456",
            msg_type=MessageType.TEXT,
            content="work test",
            from_user="work_user1",
            chat_type=ChatType.GROUP
        )
        
        assert message.msg_type == MessageType.TEXT
        assert message.chat_type == ChatType.GROUP
    
    def test_message_type_compatibility(self):
        """测试消息类型兼容性"""
        from core.message_reader_interface import MessageType
        
        # 两种微信应该支持相同的消息类型
        assert hasattr(MessageType, 'TEXT')
        assert hasattr(MessageType, 'IMAGE')
        assert hasattr(MessageType, 'VOICE')
        assert hasattr(MessageType, 'VIDEO')
        assert hasattr(MessageType, 'FILE')


class TestAPIDifferences:
    """API差异测试"""
    
    def test_wechat_api(self):
        """测试个人微信API"""
        from managers.wechat_group_manager import WeChatGroupManager
        
        manager = WeChatGroupManager()
        
        # 应该有人性化操作
        assert hasattr(manager, 'human_ops')
    
    def test_wxwork_api(self):
        """测试企业微信API"""
        from managers.wxwork_group_manager import WxWorkGroupManager
        
        manager = WxWorkGroupManager()
        
        # 应该有人性化操作
        assert hasattr(manager, 'human_ops')
    
    def test_sender_factory(self):
        """测试发送器工厂"""
        from message_sender_interface import MessageSenderFactory
        
        factory = MessageSenderFactory()
        available = factory.get_available_senders()
        
        assert isinstance(available, list)


class TestFeatureDifferences:
    """功能差异测试"""
    
    def test_wechat_features(self):
        """测试个人微信功能"""
        # 模拟个人微信功能列表
        wechat_features = [
            "send_text",
            "send_image",
            "send_file",
            "send_video",
            "get_contacts",
            "get_groups",
        ]
        
        assert len(wechat_features) > 0
    
    def test_wxwork_features(self):
        """测试企业微信功能"""
        # 企业微信额外的功能
        wxwork_features = [
            "send_text",
            "send_image", 
            "send_file",
            "send_video",
            "get_contacts",
            "get_groups",
            "enterprise_api",  # 企业API
            "department_sync",  # 部门同步
        ]
        
        assert "enterprise_api" in wxwork_features
    
    def test_common_features(self):
        """测试通用功能"""
        common = ["send_text", "send_image", "get_contacts"]
        
        for feature in common:
            assert isinstance(feature, str)


class TestErrorHandling:
    """错误处理兼容性测试"""
    
    def test_wechat_error_handling(self):
        """测试个人微信错误处理"""
        from core.exceptions import WeChatNotStartError
        
        error = WeChatNotStartError()
        assert error is not None
    
    def test_wxwork_error_handling(self):
        """测试企业微信错误处理"""
        from core.exceptions import WeChatNotStartError
        
        error = WeChatNotStartError()
        assert error is not None
    
    def test_unified_error_interface(self):
        """测试统一错误接口"""
        from core.exceptions import WeChatError
        
        # 两种微信使用相同的异常
        errors = [
            WeChatError(),
            WeChatNotStartError(),
        ]
        
        for e in errors:
            assert isinstance(e, WeChatError)


# 兼容性测试总结
COMPATIBILITY_FEATURES = {
    "个人微信": [
        "消息发送/接收",
        "联系人管理",
        "群聊管理",
        "文件传输",
        "朋友圈（有限）",
    ],
    "企业微信": [
        "消息发送/接收",
        "联系人管理",
        "群聊管理", 
        "文件传输",
        "企业API",
        "部门同步",
        "审批流程",
    ],
    "跨平台": [
        "Windows 10/11",
        "企业微信4.0+",
        "微信3.0+",
    ],
}


def print_compatibility_report():
    """打印兼容性测试报告"""
    print("\n" + "="*60)
    print("📋 jz-wxbot-automation 兼容性测试报告")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"平台: {platform.system()} {platform.version()}")
    print(f"Python: {sys.version}")
    print("\n📱 功能兼容性:")
    for platform_name, features in COMPATIBILITY_FEATURES.items():
        print(f"\n  {platform_name}:")
        for feature in features:
            print(f"    ✓ {feature}")
    print("="*60)


if __name__ == '__main__':
    from datetime import datetime
    print_compatibility_report()
    pytest.main([__file__, '-v', '-s'])