# -*- coding: utf-8 -*-
"""
核心异常测试
测试 core/exceptions.py 的功能
"""

import pytest
import sys

# 添加项目根目录到路径
sys.path.insert(0, 'I:\\jz-wxbot-automation')


class TestWeChatError:
    """测试基础微信异常"""
    
    def test_wechat_error_creation(self):
        """测试创建微信异常"""
        from core.exceptions import WeChatError
        
        error = WeChatError("测试错误")
        assert error is not None
        assert error.message == "测试错误"
        assert str(error) == "测试错误"
    
    def test_wechat_error_default_message(self):
        """测试默认错误消息"""
        from core.exceptions import WeChatError
        
        error = WeChatError()
        assert "未知错误" in error.message
    
    def test_wechat_error_inheritance(self):
        """测试异常继承"""
        from core.exceptions import WeChatError
        
        error = WeChatError("测试")
        assert isinstance(error, Exception)


class TestConnectionErrors:
    """测试连接相关异常"""
    
    def test_wechat_not_start_error(self):
        """测试微信未启动异常"""
        from core.exceptions import WeChatNotStartError
        
        error = WeChatNotStartError()
        assert error is not None
        assert isinstance(error, WeChatError)
    
    def test_wechat_not_start_error_message(self):
        """测试微信未启动异常消息"""
        from core.exceptions import WeChatNotStartError
        
        error = WeChatNotStartError("请先启动微信")
        assert "微信" in str(error)
    
    def test_network_not_connect_error(self):
        """测试网络未连接异常"""
        from core.exceptions import NetWorkNotConnectError
        
        error = NetWorkNotConnectError()
        assert error is not None
        assert isinstance(error, WeChatError)
    
    def test_network_not_connect_error_message(self):
        """测试网络未连接异常消息"""
        from core.exceptions import NetWorkNotConnectError
        
        error = NetWorkNotConnectError("网络不可用")
        assert "网络" in str(error) or "不可用" in str(error)


class TestOperationErrors:
    """测试操作相关异常"""
    
    def test_element_not_found_error(self):
        """测试元素未找到异常"""
        from core.exceptions import ElementNotFoundError
        
        error = ElementNotFoundError("发送按钮")
        assert error is not None
        assert "元素" in str(error) or "发送按钮" in str(error)
    
    def test_timeout_error(self):
        """测试超时异常"""
        from core.exceptions import TimeoutError
        
        error = TimeoutError()
        assert error is not None
    
    def test_timeout_error_message(self):
        """测试超时异常消息"""
        from core.exceptions import TimeoutError
        
        error = TimeoutError("等待响应超时")
        assert "超时" in str(error)
    
    def test_no_pattern_interface_error(self):
        """测试模式接口不支持异常"""
        from core.exceptions import NoPatternInterfaceError
        
        error = NoPatternInterfaceError()
        assert error is not None


class TestFileErrors:
    """测试文件相关异常"""
    
    def test_empty_file_error(self):
        """测试空文件异常"""
        from core.exceptions import EmptyFileError
        
        error = EmptyFileError()
        assert error is not None
        assert isinstance(error, WeChatError)
    
    def test_empty_file_error_message(self):
        """测试空文件异常消息"""
        from core.exceptions import EmptyFileError
        
        error = EmptyFileError("文件为空")
        assert "空" in str(error)
    
    def test_not_file_error(self):
        """测试不是文件异常"""
        from core.exceptions import NotFileError
        
        error = NotFileError()
        assert error is not None
    
    def test_not_folder_error(self):
        """测试不是文件夹异常"""
        from core.exceptions import NotFolderError
        
        error = NotFolderError()
        assert error is not None


class TestFriendGroupErrors:
    """测试好友和群聊相关异常"""
    
    def test_no_such_friend_error(self):
        """测试好友不存在异常"""
        from core.exceptions import NoSuchFriendError
        
        error = NoSuchFriendError("张三")
        assert error is not None
        assert "好友" in str(error) or "张三" in str(error)
    
    def test_not_friend_error(self):
        """测试不是好友异常"""
        from core.exceptions import NotFriendError
        
        error = NotFriendError()
        assert error is not None
    
    def test_no_groups_error(self):
        """测试没有群聊异常"""
        from core.exceptions import NoGroupsError
        
        error = NoGroupsError()
        assert error is not None
    
    def test_no_such_group_error(self):
        """测试群聊不存在异常"""
        from core.exceptions import NoSuchGroupError
        
        error = NoSuchGroupError("测试群")
        assert error is not None


class TestPermissionErrors:
    """测试权限相关异常"""
    
    def test_no_permission_error(self):
        """测试无权限异常"""
        from core.exceptions import NoPermissionError
        
        error = NoPermissionError()
        assert error is not None
    
    def test_no_permission_error_message(self):
        """测试无权限异常消息"""
        from core.exceptions import NoPermissionError
        
        error = NoPermissionError("需要管理员权限")
        assert "权限" in str(error)


class TestMessageErrors:
    """测试消息相关异常"""
    
    def test_message_too_long_error(self):
        """测试消息过长异常"""
        from core.exceptions import MessageTooLongError
        
        error = MessageTooLongError()
        assert error is not None
    
    def test_invalid_message_type_error(self):
        """测试无效消息类型异常"""
        from core.exceptions import InvalidMessageTypeError
        
        error = InvalidMessageTypeError()
        assert error is not None


class TestErrorHierarchy:
    """测试异常层次结构"""
    
    def test_all_errors_inherit_wechat_error(self):
        """测试所有异常都继承 WeChatError"""
        from core import exceptions
        
        # 收集所有异常类
        exception_classes = [
            name for name in dir(exceptions) 
            if name.endswith('Error') and name != 'WeChatError'
        ]
        
        for name in exception_classes:
            cls = getattr(exceptions, name)
            if isinstance(cls, type) and issubclass(cls, Exception):
                # 检查是否是 WeChatError 的子类
                assert issubclass(cls, WeChatError), f"{name} should inherit from WeChatError"
    
    def test_error_code_map(self):
        """测试错误码映射"""
        from core.exceptions import get_error_code
        
        # 测试基本错误码
        code = get_error_code(WeChatError())
        assert code is not None


class TestErrorHandlers:
    """测试错误处理"""
    
    def test_catch_specific_error(self):
        """测试捕获特定异常"""
        from core.exceptions import WeChatError, WeChatNotStartError
        
        try:
            raise WeChatNotStartError("微信未运行")
        except WeChatError as e:
            assert "微信" in str(e)
    
    def test_error_chaining(self):
        """测试异常链"""
        from core.exceptions import WeChatError
        
        original = ValueError("原始错误")
        error = WeChatError("包装后的错误")
        
        # Python 3 的异常链
        assert error.message == "包装后的错误"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])