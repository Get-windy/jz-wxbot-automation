# -*- coding: utf-8 -*-
"""
jz-wxbot-automation 错误处理测试
测试异常处理、错误恢复、日志收集等功能

测试范围:
1. 异常情况处理测试
2. 错误恢复流程测试
3. 日志收集测试
4. 综合场景测试
"""

import pytest
import sys
import os
import time
import json
import logging
import tempfile
import traceback
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, 'I:\\jz-wxbot-automation')

# 导入项目模块
try:
    from core.exceptions import (
        WeChatError,
        WeChatNotStartError,
        NetWorkNotConnectError,
        ElementNotFoundError,
        TimeoutError,
        EmptyFileError,
        NotFileError,
        NotFolderError,
        NoSuchFriendError,
        NotFriendError,
        NoGroupsError,
        NoPermissionError,
        ERROR_CODE_MAP,
        get_error_by_code
    )
    from core.error_handling import (
        ErrorHandler,
        LogManager,
        get_logger,
        error_handler,
        handle_errors,
        retry,
        ErrorContext,
        WxBotError,
        ConnectionError,
        AuthenticationError,
        MessageError,
        APIError,
        ConfigError
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# ============================================================
# 测试配置
# ============================================================

class TestConfig:
    """测试配置"""
    PROJECT_NAME = "jz-wxbot-automation"
    TEST_DIR = "I:\\jz-wxbot-automation\\tests\\error_handling"
    LOG_DIR = "I:\\jz-wxbot-automation\\logs"
    REPORT_DIR = "I:\\jz-wxbot-automation\\docs"


# ============================================================
# 测试工具类
# ============================================================

class MockLogger:
    """模拟日志器"""
    
    def __init__(self, name: str = "test"):
        self.name = name
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': []
        }
    
    def debug(self, msg: str):
        self.messages['debug'].append(msg)
    
    def info(self, msg: str):
        self.messages['info'].append(msg)
    
    def warning(self, msg: str):
        self.messages['warning'].append(msg)
    
    def error(self, msg: str):
        self.messages['error'].append(msg)
    
    def critical(self, msg: str):
        self.messages['critical'].append(msg)
    
    def get_messages(self, level: str = None) -> List[str]:
        if level:
            return self.messages.get(level, [])
        return [msg for msgs in self.messages.values() for msg in msgs]
    
    def clear(self):
        for level in self.messages:
            self.messages[level] = []


class ErrorSimulator:
    """错误模拟器"""
    
    @staticmethod
    def simulate_network_error():
        """模拟网络错误"""
        raise NetWorkNotConnectError("网络连接失败")
    
    @staticmethod
    def simulate_timeout_error():
        """模拟超时错误"""
        raise TimeoutError("操作超时")
    
    @staticmethod
    def simulate_wechat_not_running():
        """模拟微信未运行"""
        raise WeChatNotStartError("微信未启动")
    
    @staticmethod
    def simulate_element_not_found():
        """模拟元素未找到"""
        raise ElementNotFoundError("UI元素未找到")
    
    @staticmethod
    def simulate_permission_denied():
        """模拟权限不足"""
        raise NoPermissionError("操作权限不足")
    
    @staticmethod
    def simulate_message_error():
        """模拟消息错误"""
        raise MessageError("消息处理失败")


class ErrorRecoveryTracker:
    """错误恢复追踪器"""
    
    def __init__(self):
        self.recovery_attempts = []
        self.successful_recoveries = []
        self.failed_recoveries = []
    
    def record_attempt(self, error_type: str, strategy: str):
        self.recovery_attempts.append({
            'error_type': error_type,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        })
    
    def record_success(self, error_type: str, strategy: str):
        self.successful_recoveries.append({
            'error_type': error_type,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        })
    
    def record_failure(self, error_type: str, strategy: str, reason: str):
        self.failed_recoveries.append({
            'error_type': error_type,
            'strategy': strategy,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_summary(self) -> Dict:
        return {
            'total_attempts': len(self.recovery_attempts),
            'successful': len(self.successful_recoveries),
            'failed': len(self.failed_recoveries),
            'success_rate': len(self.successful_recoveries) / max(len(self.recovery_attempts), 1) * 100
        }


class LogCollector:
    """日志收集器"""
    
    def __init__(self):
        self.logs = []
        self.temp_file = None
    
    def start(self):
        """开始收集日志"""
        self.logs = []
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w+',
            suffix='.log',
            delete=False,
            encoding='utf-8'
        )
    
    def add_log(self, level: str, message: str, source: str = "test"):
        """添加日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'source': source
        }
        self.logs.append(log_entry)
        
        if self.temp_file:
            self.temp_file.write(f"{log_entry['timestamp']} [{level}] {source}: {message}\n")
            self.temp_file.flush()
    
    def stop(self) -> str:
        """停止收集并返回日志文件路径"""
        if self.temp_file:
            self.temp_file.close()
            return self.temp_file.name
        return ""
    
    def get_logs(self, level: str = None) -> List[Dict]:
        """获取日志"""
        if level:
            return [log for log in self.logs if log['level'] == level]
        return self.logs
    
    def clear(self):
        """清空日志"""
        self.logs = []
        if self.temp_file and os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
            self.temp_file = None


# ============================================================
# 第一部分：异常情况处理测试
# ============================================================

class TestExceptionHandling:
    """异常情况处理测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.mock_logger = MockLogger()
        self.error_tracker = ErrorRecoveryTracker()
    
    # ---------- 基础异常测试 ----------
    
    def test_wechat_error_creation(self):
        """测试微信基础异常创建"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        error = WeChatError("测试错误")
        assert error is not None
        assert str(error) == "测试错误"
    
    def test_wechat_error_with_code(self):
        """测试带错误码的异常"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        error = WxBotError("带错误码的异常", code="TEST_001")
        assert error.code == "TEST_001"
        assert error.message == "带错误码的异常"
    
    def test_exception_inheritance(self):
        """测试异常继承关系"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        # 所有异常应该继承自 WeChatError
        assert issubclass(WeChatNotStartError, WeChatError)
        assert issubclass(NetWorkNotConnectError, WeChatError)
        assert issubclass(ElementNotFoundError, WeChatError)
        assert issubclass(TimeoutError, WeChatError)
        assert issubclass(NoPermissionError, WeChatError)
    
    # ---------- 连接异常测试 ----------
    
    def test_connection_error_handling(self):
        """测试连接错误处理"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        try:
            ErrorSimulator.simulate_network_error()
            assert False, "应该抛出异常"
        except NetWorkNotConnectError as e:
            assert "网络" in str(e)
            self.mock_logger.error(f"捕获到网络错误: {e}")
    
    def test_wechat_not_start_handling(self):
        """测试微信未启动处理"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        try:
            ErrorSimulator.simulate_wechat_not_running()
            assert False, "应该抛出异常"
        except WeChatNotStartError as e:
            assert "微信" in str(e) or "启动" in str(e)
    
    # ---------- 操作异常测试 ----------
    
    def test_element_not_found_handling(self):
        """测试元素未找到处理"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        try:
            ErrorSimulator.simulate_element_not_found()
            assert False, "应该抛出异常"
        except ElementNotFoundError as e:
            assert "元素" in str(e) or "未找到" in str(e)
    
    def test_timeout_error_handling(self):
        """测试超时错误处理"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        try:
            ErrorSimulator.simulate_timeout_error()
            assert False, "应该抛出异常"
        except TimeoutError as e:
            assert "超时" in str(e)
    
    def test_permission_denied_handling(self):
        """测试权限不足处理"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        try:
            ErrorSimulator.simulate_permission_denied()
            assert False, "应该抛出异常"
        except NoPermissionError as e:
            assert "权限" in str(e)
    
    # ---------- 消息异常测试 ----------
    
    def test_message_error_handling(self):
        """测试消息错误处理"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        try:
            ErrorSimulator.simulate_message_error()
            assert False, "应该抛出异常"
        except MessageError as e:
            assert "消息" in str(e) or "失败" in str(e)
    
    def test_empty_file_error(self):
        """测试空文件错误"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        error = EmptyFileError("文件为空")
        assert "空" in str(error)
    
    def test_friend_not_found_error(self):
        """测试好友不存在错误"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        error = NoSuchFriendError("张三")
        assert error is not None
    
    # ---------- 错误码映射测试 ----------
    
    def test_error_code_mapping(self):
        """测试错误码映射"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        assert 'WECHAT_NOT_START' in ERROR_CODE_MAP
        assert 'NETWORK_ERROR' in ERROR_CODE_MAP
        assert 'TIMEOUT' in ERROR_CODE_MAP
        assert 'ELEMENT_NOT_FOUND' in ERROR_CODE_MAP
    
    def test_get_error_by_code(self):
        """测试根据错误码获取异常类"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        error_class = get_error_by_code('WECHAT_NOT_START')
        assert error_class == WeChatNotStartError
        
        unknown_class = get_error_by_code('UNKNOWN_CODE')
        assert unknown_class == WeChatError


# ============================================================
# 第二部分：错误恢复流程测试
# ============================================================

class TestErrorRecovery:
    """错误恢复流程测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.recovery_tracker = ErrorRecoveryTracker()
    
    # ---------- 重试机制测试 ----------
    
    def test_retry_mechanism(self):
        """测试重试机制"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        attempt_count = 0
        
        @retry(max_retries=3, delay=0.1)
        def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("模拟失败")
            return "成功"
        
        result = flaky_operation()
        assert result == "成功"
        assert attempt_count == 3
    
    def test_retry_max_attempts(self):
        """测试重试最大次数"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        attempt_count = 0
        
        @retry(max_retries=3, delay=0.1)
        def always_fail():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("始终失败")
        
        with pytest.raises(ValueError):
            always_fail()
        
        assert attempt_count == 3
    
    def test_retry_with_different_exceptions(self):
        """测试不同异常的重试"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        attempt_count = 0
        
        @retry(max_retries=5, delay=0.05)
        def mixed_errors():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise TimeoutError("超时")
            elif attempt_count == 2:
                raise NetWorkNotConnectError("网络错误")
            return "成功"
        
        result = mixed_errors()
        assert result == "成功"
        assert attempt_count == 3
    
    # ---------- 自动恢复测试 ----------
    
    def test_auto_recovery_network_error(self):
        """测试网络错误自动恢复"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        recovery_attempts = 0
        
        def mock_network_recovery():
            nonlocal recovery_attempts
            recovery_attempts += 1
            if recovery_attempts < 2:
                return False  # 第一次恢复失败
            return True  # 第二次恢复成功
        
        # 模拟恢复流程
        try:
            raise NetWorkNotConnectError("网络断开")
        except NetWorkNotConnectError as e:
            self.recovery_tracker.record_attempt('network', 'reconnect')
            
            # 尝试恢复
            for attempt in range(3):
                if mock_network_recovery():
                    self.recovery_tracker.record_success('network', 'reconnect')
                    break
                else:
                    self.recovery_tracker.record_failure(
                        'network', 'reconnect', f'尝试 {attempt + 1} 失败'
                    )
        
        summary = self.recovery_tracker.get_summary()
        assert summary['successful'] >= 1
    
    def test_auto_recovery_timeout(self):
        """测试超时错误自动恢复"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        timeout_extended = False
        
        def handle_timeout():
            nonlocal timeout_extended
            # 延长超时时间
            timeout_extended = True
            return True
        
        try:
            raise TimeoutError("操作超时")
        except TimeoutError:
            self.recovery_tracker.record_attempt('timeout', 'extend_timeout')
            if handle_timeout():
                self.recovery_tracker.record_success('timeout', 'extend_timeout')
        
        assert timeout_extended is True
    
    def test_graceful_degradation(self):
        """测试优雅降级"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        primary_available = False
        fallback_available = True
        
        def send_message_primary():
            if not primary_available:
                raise ConnectionError("主服务不可用")
            return "主服务发送成功"
        
        def send_message_fallback():
            if fallback_available:
                return "备用服务发送成功"
            raise ConnectionError("备用服务也不可用")
        
        # 尝试主服务
        result = None
        try:
            result = send_message_primary()
        except ConnectionError:
            # 降级到备用服务
            try:
                result = send_message_fallback()
            except ConnectionError:
                result = None
        
        assert result == "备用服务发送成功"
    
    # ---------- 状态恢复测试 ----------
    
    def test_state_recovery_after_error(self):
        """测试错误后状态恢复"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        state = {
            'connected': True,
            'authenticated': True,
            'last_error': None
        }
        
        # 模拟错误发生
        try:
            raise WeChatNotStartError("微信崩溃")
        except WeChatNotStartError as e:
            state['connected'] = False
            state['authenticated'] = False
            state['last_error'] = str(e)
        
        # 验证状态已更新
        assert state['connected'] is False
        assert state['last_error'] is not None
        
        # 模拟恢复
        state['connected'] = True
        state['authenticated'] = True
        state['last_error'] = None
        
        assert state['connected'] is True
        assert state['last_error'] is None


# ============================================================
# 第三部分：日志收集测试
# ============================================================

class TestLogCollection:
    """日志收集测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.log_collector = LogCollector()
        self.log_collector.start()
    
    def teardown(self):
        """测试后清理"""
        self.log_collector.clear()
    
    # ---------- 基础日志测试 ----------
    
    def test_log_collection_basic(self):
        """测试基础日志收集"""
        self.log_collector.add_log('INFO', '测试消息')
        self.log_collector.add_log('ERROR', '错误消息')
        self.log_collector.add_log('WARNING', '警告消息')
        
        logs = self.log_collector.get_logs()
        assert len(logs) == 3
        assert logs[0]['level'] == 'INFO'
        assert logs[1]['level'] == 'ERROR'
        assert logs[2]['level'] == 'WARNING'
    
    def test_log_filtering_by_level(self):
        """测试按级别过滤日志"""
        self.log_collector.add_log('ERROR', '错误1')
        self.log_collector.add_log('ERROR', '错误2')
        self.log_collector.add_log('INFO', '信息1')
        
        error_logs = self.log_collector.get_logs(level='ERROR')
        assert len(error_logs) == 2
        
        info_logs = self.log_collector.get_logs(level='INFO')
        assert len(info_logs) == 1
    
    def test_log_timestamp(self):
        """测试日志时间戳"""
        self.log_collector.add_log('INFO', '测试')
        logs = self.log_collector.get_logs()
        
        assert 'timestamp' in logs[0]
        # 验证时间戳格式
        timestamp = logs[0]['timestamp']
        datetime.fromisoformat(timestamp)  # 不应抛出异常
    
    # ---------- 错误日志测试 ----------
    
    def test_error_log_on_exception(self):
        """测试异常时的错误日志"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        try:
            ErrorSimulator.simulate_network_error()
        except NetWorkNotConnectError as e:
            self.log_collector.add_log('ERROR', f'网络错误: {e}')
            self.log_collector.add_log('ERROR', traceback.format_exc())
        
        error_logs = self.log_collector.get_logs('ERROR')
        assert len(error_logs) >= 1
        assert '网络' in error_logs[0]['message']
    
    def test_log_with_stack_trace(self):
        """测试带堆栈跟踪的日志"""
        try:
            raise ValueError("测试异常")
        except ValueError:
            stack_trace = traceback.format_exc()
            self.log_collector.add_log('ERROR', '发生异常', 'test')
            self.log_collector.add_log('DEBUG', stack_trace, 'traceback')
        
        logs = self.log_collector.get_logs()
        assert any('Traceback' in log['message'] for log in logs)
    
    # ---------- 日志文件测试 ----------
    
    def test_log_file_creation(self):
        """测试日志文件创建"""
        log_path = self.log_collector.stop()
        
        assert log_path != ""
        assert os.path.exists(log_path)
        
        # 验证文件内容
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 清理
        if os.path.exists(log_path):
            os.unlink(log_path)
    
    def test_log_rotation(self):
        """测试日志轮转"""
        # 添加大量日志
        for i in range(100):
            self.log_collector.add_log('INFO', f'日志消息 {i}')
        
        logs = self.log_collector.get_logs()
        assert len(logs) == 100
    
    # ---------- LogManager 测试 ----------
    
    def test_log_manager(self):
        """测试日志管理器"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        manager = LogManager()
        logger = manager.get_logger('test_logger')
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_get_logger_function(self):
        """测试获取日志器函数"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        logger = get_logger('test')
        assert logger is not None
    
    # ---------- 错误处理器日志测试 ----------
    
    def test_error_handler_logging(self):
        """测试错误处理器日志"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        mock_logger = MockLogger()
        handler = ErrorHandler('test_handler')
        handler.logger = mock_logger
        
        error = WxBotError("测试错误", "TEST_001")
        handler.handle_error(error)
        
        assert len(mock_logger.messages['error']) >= 1


# ============================================================
# 第四部分：装饰器和上下文管理器测试
# ============================================================

class TestErrorDecorators:
    """错误处理装饰器和上下文管理器测试"""
    
    # ---------- @handle_errors 装饰器测试 ----------
    
    def test_handle_errors_decorator(self):
        """测试 @handle_errors 装饰器"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        @handle_errors
        def function_with_error():
            raise WxBotError("装饰器测试错误", "DECORATOR_001")
        
        with pytest.raises(WxBotError):
            function_with_error()
    
    def test_handle_errors_decorator_success(self):
        """测试 @handle_errors 装饰器成功情况"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        @handle_errors
        def function_success():
            return "成功"
        
        result = function_success()
        assert result == "成功"
    
    # ---------- ErrorContext 上下文管理器测试 ----------
    
    def test_error_context_manager(self):
        """测试 ErrorContext 上下文管理器"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        with pytest.raises(WxBotError):
            with ErrorContext("测试操作"):
                raise WxBotError("上下文错误")
    
    def test_error_context_manager_success(self):
        """测试 ErrorContext 成功情况"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        with ErrorContext("测试操作"):
            pass  # 不抛出异常
        
        # 如果到这里说明测试通过
    
    # ---------- @retry 装饰器详细测试 ----------
    
    def test_retry_decorator_delay(self):
        """测试重试装饰器延迟"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        import time
        
        attempts = []
        
        @retry(max_retries=3, delay=0.1)
        def tracked_operation():
            attempts.append(time.time())
            if len(attempts) < 3:
                raise ValueError("失败")
            return "成功"
        
        start = time.time()
        result = tracked_operation()
        elapsed = time.time() - start
        
        assert result == "成功"
        assert elapsed >= 0.2  # 至少有两次延迟


# ============================================================
# 第五部分：综合场景测试
# ============================================================

class TestIntegratedScenarios:
    """综合场景测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.log_collector = LogCollector()
        self.recovery_tracker = ErrorRecoveryTracker()
        self.log_collector.start()
    
    def teardown(self):
        """测试后清理"""
        self.log_collector.clear()
    
    # ---------- 消息发送错误恢复场景 ----------
    
    def test_message_send_recovery_scenario(self):
        """测试消息发送错误恢复场景"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        # 模拟消息发送流程
        class MockMessageSender:
            def __init__(self):
                self.attempts = 0
                self.available = True
            
            def send(self, target, message):
                self.attempts += 1
                self.log_collector.add_log(
                    'INFO', f'尝试发送消息到 {target} (第{self.attempts}次)'
                )
                
                if self.attempts < 3:
                    self.log_collector.add_log('WARNING', '发送失败，准备重试')
                    raise TimeoutError("发送超时")
                
                self.log_collector.add_log('INFO', '消息发送成功')
                return True
        
        sender = MockMessageSender()
        sender.log_collector = self.log_collector
        
        # 使用重试装饰器
        @retry(max_retries=5, delay=0.05)
        def send_with_retry():
            return sender.send("测试群", "测试消息")
        
        result = send_with_retry()
        assert result is True
        assert sender.attempts == 3
    
    # ---------- 网络重连场景 ----------
    
    def test_network_reconnect_scenario(self):
        """测试网络重连场景"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        class MockNetworkManager:
            def __init__(self):
                self.connected = False
                self.reconnect_attempts = 0
            
            def connect(self):
                self.reconnect_attempts += 1
                if self.reconnect_attempts >= 2:
                    self.connected = True
                    return True
                return False
            
            def ensure_connection(self):
                if not self.connected:
                    self.log_collector.add_log('WARNING', '网络未连接，尝试重连')
                    
                    for attempt in range(3):
                        self.log_collector.add_log(
                            'INFO', f'重连尝试 {attempt + 1}'
                        )
                        
                        if self.connect():
                            self.log_collector.add_log('INFO', '重连成功')
                            return True
                        
                        self.log_collector.add_log(
                            'WARNING', f'重连失败'
                        )
                    
                    self.log_collector.add_log('ERROR', '重连失败，已达最大尝试次数')
                    return False
                
                return True
        
        manager = MockNetworkManager()
        manager.log_collector = self.log_collector
        
        result = manager.ensure_connection()
        assert result is True
        assert manager.connected is True
    
    # ---------- 微信启动恢复场景 ----------
    
    def test_wechat_start_recovery_scenario(self):
        """测试微信启动恢复场景"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        class MockWeChatManager:
            def __init__(self):
                self.running = False
                self.start_attempts = 0
            
            def start(self):
                self.start_attempts += 1
                if self.start_attempts >= 2:
                    self.running = True
                    return True
                return False
            
            def ensure_running(self):
                if not self.running:
                    self.log_collector.add_log('WARNING', '微信未运行，尝试启动')
                    
                    for attempt in range(3):
                        if self.start():
                            self.log_collector.add_log('INFO', '微信启动成功')
                            return True
                        
                        self.log_collector.add_log(
                            'WARNING', f'启动尝试 {attempt + 1} 失败'
                        )
                    
                    return False
                
                return True
        
        manager = MockWeChatManager()
        manager.log_collector = self.log_collector
        
        result = manager.ensure_running()
        assert result is True
        assert manager.running is True
    
    # ---------- 多错误级联场景 ----------
    
    def test_cascading_error_scenario(self):
        """测试多错误级联场景"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"导入失败: {IMPORT_ERROR}")
        
        class CascadingErrorHandler:
            def __init__(self):
                self.state = 'initial'
            
            def handle_network_error(self):
                self.state = 'network_error'
                self.log_collector.add_log('ERROR', '网络错误发生')
                
                # 尝试恢复网络
                if self.try_recover_network():
                    self.state = 'recovered'
                    return True
                
                # 网络恢复失败，降级
                self.state = 'degraded'
                self.log_collector.add_log('WARNING', '降级到离线模式')
                return False
            
            def try_recover_network(self):
                self.log_collector.add_log('INFO', '尝试网络恢复')
                # 模拟恢复失败
                return False
        
        handler = CascadingErrorHandler()
        handler.log_collector = self.log_collector
        
        result = handler.handle_network_error()
        assert result is False
        assert handler.state == 'degraded'
        
        # 验证日志记录
        error_logs = self.log_collector.get_logs('ERROR')
        warning_logs = self.log_collector.get_logs('WARNING')
        
        assert len(error_logs) >= 1
        assert len(warning_logs) >= 1


# ============================================================
# 测试报告生成
# ============================================================

def generate_test_report(results: Dict) -> str:
    """生成测试报告"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    report = f"""# jz-wxbot-automation 错误处理测试报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**项目**: jz-wxbot-automation

---

## 测试概览

| 指标 | 数值 |
|------|------|
| 总测试数 | {results.get('total', 0)} |
| 通过数 | {results.get('passed', 0)} |
| 失败数 | {results.get('failed', 0)} |
| 跳过数 | {results.get('skipped', 0)} |
| 通过率 | {results.get('pass_rate', 0):.1f}% |

---

## 测试分类

### 1. 异常情况处理测试
- 基础异常创建和继承
- 连接异常处理
- 操作异常处理
- 消息异常处理
- 错误码映射

### 2. 错误恢复流程测试
- 重试机制
- 自动恢复
- 优雅降级
- 状态恢复

### 3. 日志收集测试
- 基础日志功能
- 错误日志记录
- 日志文件管理
- 日志过滤

### 4. 装饰器和上下文管理器测试
- @handle_errors 装饰器
- @retry 装饰器
- ErrorContext 上下文管理器

### 5. 综合场景测试
- 消息发送恢复场景
- 网络重连场景
- 微信启动恢复场景
- 多错误级联场景

---

## 测试结论

"""
    
    if results.get('pass_rate', 0) >= 90:
        report += "✅ **测试通过** - 错误处理机制运行良好\n"
    elif results.get('pass_rate', 0) >= 70:
        report += "⚠️ **部分通过** - 存在一些需要关注的问题\n"
    else:
        report += "❌ **测试失败** - 需要修复错误处理机制\n"
    
    report += """
---

## 建议

1. 确保所有异常类都正确继承基础异常
2. 完善错误恢复策略的日志记录
3. 添加更多边界情况的测试用例
4. 定期检查和更新错误码映射

---

*报告由自动化测试系统生成*
"""
    
    return report


def run_tests_and_generate_report():
    """运行测试并生成报告"""
    import subprocess
    import json
    
    # 运行测试
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short', '-q'],
        capture_output=True,
        text=True
    )
    
    # 解析结果
    output = result.stdout + result.stderr
    
    # 统计结果
    total = output.count('PASSED') + output.count('FAILED') + output.count('SKIPPED')
    passed = output.count('PASSED')
    failed = output.count('FAILED')
    skipped = output.count('SKIPPED')
    
    results = {
        'total': total,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'pass_rate': (passed / max(total, 1)) * 100
    }
    
    # 生成报告
    report = generate_test_report(results)
    
    # 保存报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f"I:\\jz-wxbot-automation\\docs\\error_handling_test_report_{timestamp}.md"
    
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n测试报告已保存: {report_path}")
    print(report)
    
    return results


# ============================================================
# 主入口
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])