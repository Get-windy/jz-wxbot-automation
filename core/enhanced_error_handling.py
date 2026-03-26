# -*- coding: utf-8 -*-
"""
jz-wxbot 增强错误处理系统
集成异常处理、错误恢复、错误报告
"""

import asyncio
import functools
import traceback
from typing import Optional, Callable, Any, Dict, List, Type, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import threading

from .exceptions import (
    WeChatError,
    WeChatNotStartError,
    NetWorkNotConnectError,
    ElementNotFoundError,
    TimeoutError,
)
from .enhanced_logging import get_logger, EnhancedLogger

# ============================================================
# 错误严重级别
# ============================================================

class ErrorSeverity(Enum):
    """错误严重级别"""
    LOW = 'low'           # 可忽略，不影响功能
    MEDIUM = 'medium'     # 部分功能受影响
    HIGH = 'high'         # 核心功能受影响
    CRITICAL = 'critical' # 系统崩溃


# ============================================================
# 错误恢复策略
# ============================================================

class RecoveryStrategy(Enum):
    """错误恢复策略"""
    IGNORE = 'ignore'           # 忽略错误
    RETRY = 'retry'             # 重试操作
    FALLBACK = 'fallback'       # 使用备用方案
    RESTART = 'restart'         # 重启服务
    SHUTDOWN = 'shutdown'       # 关闭服务
    NOTIFY = 'notify'           # 通知用户


# ============================================================
# 错误处理配置
# ============================================================

@dataclass
class ErrorHandlerConfig:
    """错误处理配置"""
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0  # 指数退避因子
    
    # 错误阈值
    error_threshold: int = 10   # 触发告警的错误数量
    time_window: int = 300      # 统计时间窗口（秒）
    
    # 恢复策略
    auto_recovery: bool = True
    recovery_timeout: float = 30.0
    
    # 通知配置
    notify_on_error: bool = True
    notify_on_critical: bool = True


# ============================================================
# 错误上下文
# ============================================================

@dataclass
class ErrorContext:
    """错误上下文"""
    operation: str              # 操作名称
    component: str              # 组件名称
    severity: ErrorSeverity     # 严重级别
    recovery: RecoveryStrategy  # 恢复策略
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    traceback: Optional[str] = None
    handled: bool = False
    retry_count: int = 0


# ============================================================
# 错误处理器
# ============================================================

class ErrorHandler:
    """增强错误处理器"""
    
    def __init__(self, config: Optional[ErrorHandlerConfig] = None):
        self.config = config or ErrorHandlerConfig()
        self.logger = get_logger('error_handler')
        
        # 错误统计
        self._error_counts: Dict[str, int] = {}
        self._error_history: List[ErrorContext] = []
        self._lock = threading.Lock()
        
        # 错误处理器映射
        self._handlers: Dict[Type[Exception], Callable] = {}
        self._recovery_handlers: Dict[RecoveryStrategy, Callable] = {}
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认错误处理器"""
        # 微信未启动
        self.register_handler(WeChatNotStartError, self._handle_wechat_not_start)
        
        # 网络错误
        self.register_handler(NetWorkNotConnectError, self._handle_network_error)
        
        # 元素未找到
        self.register_handler(ElementNotFoundError, self._handle_element_not_found)
        
        # 超时错误
        self.register_handler(TimeoutError, self._handle_timeout)
        
        # 通用错误
        self.register_handler(WeChatError, self._handle_wechat_error)
        
        # 注册恢复策略
        self._recovery_handlers = {
            RecoveryStrategy.RETRY: self._strategy_retry,
            RecoveryStrategy.FALLBACK: self._strategy_fallback,
            RecoveryStrategy.NOTIFY: self._strategy_notify,
        }
    
    # ========================================================
    # 公共方法
    # ========================================================
    
    def register_handler(self, exception_type: Type[Exception], handler: Callable):
        """注册错误处理器"""
        self._handlers[exception_type] = handler
    
    def handle(self, error: Exception, context: Optional[ErrorContext] = None) -> Any:
        """处理错误"""
        # 创建上下文
        if context is None:
            context = ErrorContext(
                operation='unknown',
                component='unknown',
                severity=ErrorSeverity.MEDIUM,
                recovery=RecoveryStrategy.NOTIFY,
                traceback=traceback.format_exc(),
            )
        
        context.traceback = context.traceback or traceback.format_exc()
        
        # 记录错误
        self._record_error(error, context)
        
        # 查找处理器
        handler = self._find_handler(error)
        
        if handler:
            try:
                result = handler(error, context)
                context.handled = True
                return result
            except Exception as e:
                self.logger.error(f"错误处理器执行失败: {e}")
        
        # 默认处理
        self._default_handle(error, context)
        return None
    
    def wrap(self, func: Callable, **context_kwargs) -> Callable:
        """包装函数，自动处理错误"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    operation=func.__name__,
                    component=func.__module__,
                    severity=ErrorSeverity.MEDIUM,
                    recovery=RecoveryStrategy.NOTIFY,
                )
                return self.handle(e, context)
        return wrapper
    
    def async_wrap(self, func: Callable, **context_kwargs) -> Callable:
        """包装异步函数"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    operation=func.__name__,
                    component=func.__module__,
                    severity=ErrorSeverity.MEDIUM,
                    recovery=RecoveryStrategy.NOTIFY,
                )
                return self.handle(e, context)
        return wrapper
    
    # ========================================================
    # 错误处理器
    # ========================================================
    
    def _handle_wechat_not_start(self, error: WeChatNotStartError, context: ErrorContext) -> Any:
        """处理微信未启动错误"""
        self.logger.warning(f"微信未启动: {error.message}")
        
        # 更新上下文
        context.severity = ErrorSeverity.HIGH
        context.recovery = RecoveryStrategy.NOTIFY
        
        # 可以尝试自动启动微信
        # TODO: 实现自动启动逻辑
        
        return {'status': 'error', 'code': 'WECHAT_NOT_START', 'message': error.message}
    
    def _handle_network_error(self, error: NetWorkNotConnectError, context: ErrorContext) -> Any:
        """处理网络错误"""
        self.logger.error(f"网络连接错误: {error.message}")
        
        context.severity = ErrorSeverity.HIGH
        context.recovery = RecoveryStrategy.RETRY
        
        return {'status': 'error', 'code': 'NETWORK_ERROR', 'message': error.message}
    
    def _handle_element_not_found(self, error: ElementNotFoundError, context: ErrorContext) -> Any:
        """处理元素未找到错误"""
        self.logger.warning(f"UI元素未找到: {error.message}")
        
        context.severity = ErrorSeverity.MEDIUM
        context.recovery = RecoveryStrategy.RETRY
        
        return {'status': 'error', 'code': 'ELEMENT_NOT_FOUND', 'message': error.message}
    
    def _handle_timeout(self, error: TimeoutError, context: ErrorContext) -> Any:
        """处理超时错误"""
        self.logger.warning(f"操作超时: {error.message}")
        
        context.severity = ErrorSeverity.MEDIUM
        context.recovery = RecoveryStrategy.RETRY
        
        return {'status': 'error', 'code': 'TIMEOUT', 'message': error.message}
    
    def _handle_wechat_error(self, error: WeChatError, context: ErrorContext) -> Any:
        """处理通用微信错误"""
        self.logger.error(f"微信错误: {error.message}")
        
        context.severity = ErrorSeverity.MEDIUM
        context.recovery = RecoveryStrategy.NOTIFY
        
        return {'status': 'error', 'code': 'WECHAT_ERROR', 'message': error.message}
    
    def _default_handle(self, error: Exception, context: ErrorContext):
        """默认处理"""
        self.logger.error(
            f"未处理的异常: {type(error).__name__}: {error}",
            exc_info=True
        )
    
    # ========================================================
    # 恢复策略
    # ========================================================
    
    def _strategy_retry(self, context: ErrorContext, func: Callable, *args, **kwargs) -> Any:
        """重试策略"""
        import time
        
        max_retries = self.config.max_retries
        delay = self.config.retry_delay
        
        for attempt in range(max_retries):
            try:
                context.retry_count = attempt + 1
                self.logger.info(f"重试 {attempt + 1}/{max_retries}")
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= self.config.retry_backoff
                else:
                    raise
        
        return None
    
    def _strategy_fallback(self, context: ErrorContext, fallback_func: Callable, *args, **kwargs) -> Any:
        """备用方案策略"""
        self.logger.info(f"使用备用方案: {fallback_func.__name__}")
        return fallback_func(*args, **kwargs)
    
    def _strategy_notify(self, context: ErrorContext, message: str) -> None:
        """通知策略"""
        # TODO: 实现通知逻辑（发送到OpenClaw或企业微信）
        self.logger.warning(f"需要通知: {message}")
    
    # ========================================================
    # 辅助方法
    # ========================================================
    
    def _find_handler(self, error: Exception) -> Optional[Callable]:
        """查找错误处理器"""
        for exception_type, handler in self._handlers.items():
            if isinstance(error, exception_type):
                return handler
        return None
    
    def _record_error(self, error: Exception, context: ErrorContext):
        """记录错误"""
        with self._lock:
            # 更新计数
            error_type = type(error).__name__
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
            
            # 添加到历史
            self._error_history.append(context)
            
            # 限制历史长度
            if len(self._error_history) > 100:
                self._error_history = self._error_history[-100:]
            
            # 检查阈值
            if self._error_counts[error_type] >= self.config.error_threshold:
                self.logger.critical(
                    f"错误阈值告警: {error_type} 在 {self.config.time_window}秒内 "
                    f"发生了 {self._error_counts[error_type]} 次"
                )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            return {
                'counts': dict(self._error_counts),
                'recent_errors': [
                    {
                        'operation': ctx.operation,
                        'component': ctx.component,
                        'severity': ctx.severity.value,
                        'timestamp': ctx.timestamp.isoformat(),
                    }
                    for ctx in self._error_history[-10:]
                ],
            }
    
    def reset_stats(self):
        """重置统计"""
        with self._lock:
            self._error_counts.clear()
            self._error_history.clear()


# ============================================================
# 重试装饰器
# ============================================================

def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    logger: Optional[EnhancedLogger] = None,
):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            current_delay = delay
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if logger:
                        logger.warning(
                            f"重试 {attempt + 1}/{max_retries}: {func.__name__} - {e}"
                        )
                    if attempt < max_retries - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            if logger:
                logger.error(f"重试全部失败: {func.__name__}")
            raise last_error
        
        return wrapper
    return decorator


def async_retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    logger: Optional[EnhancedLogger] = None,
):
    """异步重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            current_delay = delay
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if logger:
                        logger.warning(
                            f"重试 {attempt + 1}/{max_retries}: {func.__name__} - {e}"
                        )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            if logger:
                logger.error(f"重试全部失败: {func.__name__}")
            raise last_error
        
        return wrapper
    return decorator


# ============================================================
# 全局错误处理器
# ============================================================

_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def init_error_handler(config: Optional[ErrorHandlerConfig] = None) -> ErrorHandler:
    """初始化错误处理器"""
    global _global_error_handler
    _global_error_handler = ErrorHandler(config)
    return _global_error_handler


# ============================================================
# 导出
# ============================================================

__all__ = [
    'ErrorSeverity',
    'RecoveryStrategy',
    'ErrorHandlerConfig',
    'ErrorContext',
    'ErrorHandler',
    'retry_on_error',
    'async_retry_on_error',
    'get_error_handler',
    'init_error_handler',
]