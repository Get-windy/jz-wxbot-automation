# -*- coding: utf-8 -*-
"""
jz-wxbot 增强日志系统
支持日志轮转、结构化日志、错误追踪、性能监控
"""

import logging
import logging.handlers
import sys
import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# ============================================================
# 配置
# ============================================================

@dataclass
class LogConfig:
    """日志配置"""
    # 日志目录
    log_dir: str = str(PROJECT_ROOT / "logs")
    
    # 日志级别
    console_level: int = logging.INFO
    file_level: int = logging.DEBUG
    
    # 日志轮转
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 10
    
    # 日志格式
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    
    # 结构化日志
    json_format: bool = True
    json_log_file: str = "wxbot_structured.jsonl"
    
    # 性能监控
    enable_performance_log: bool = True
    performance_log_file: str = "performance.log"
    
    # 错误追踪
    error_tracking_enabled: bool = True
    error_log_file: str = "errors.log"


# ============================================================
# 日志级别扩展
# ============================================================

class LogLevel(Enum):
    """扩展日志级别"""
    TRACE = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


# ============================================================
# 结构化日志格式化器
# ============================================================

class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器（JSON格式）"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加额外字段
        if hasattr(record, 'extra_data') and record.extra_data:
            log_data['data'] = record.extra_data
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info),
            }
        
        return json.dumps(log_data, ensure_ascii=False)


# ============================================================
# 日志处理器
# ============================================================

class LogHandler:
    """日志处理器管理"""
    
    def __init__(self, config: Optional[LogConfig] = None):
        self.config = config or LogConfig()
        self._ensure_log_dir()
        
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        Path(self.config.log_dir).mkdir(parents=True, exist_ok=True)
    
    def create_console_handler(self) -> logging.Handler:
        """创建控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.config.console_level)
        formatter = logging.Formatter(
            self.config.log_format,
            datefmt=self.config.date_format
        )
        handler.setFormatter(formatter)
        return handler
    
    def create_file_handler(self, filename: str) -> logging.Handler:
        """创建文件处理器（支持轮转）"""
        filepath = Path(self.config.log_dir) / filename
        handler = logging.handlers.RotatingFileHandler(
            filepath,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        handler.setLevel(self.config.file_level)
        formatter = logging.Formatter(
            self.config.log_format,
            datefmt=self.config.date_format
        )
        handler.setFormatter(formatter)
        return handler
    
    def create_json_handler(self) -> logging.Handler:
        """创建JSON格式处理器"""
        filepath = Path(self.config.log_dir) / self.config.json_log_file
        handler = logging.handlers.RotatingFileHandler(
            filepath,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(StructuredFormatter())
        return handler
    
    def create_error_handler(self) -> logging.Handler:
        """创建错误专用处理器"""
        filepath = Path(self.config.log_dir) / self.config.error_log_file
        handler = logging.handlers.RotatingFileHandler(
            filepath,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s\n'
            'File: %(filename)s:%(lineno)d\n'
            'Function: %(funcName)s\n'
            'Message: %(message)s\n'
            '%(exc_info)s\n' + '-' * 80,
            datefmt=self.config.date_format
        )
        handler.setFormatter(formatter)
        return handler


# ============================================================
# 增强日志器
# ============================================================

class EnhancedLogger:
    """增强日志器"""
    
    def __init__(self, name: str, config: Optional[LogConfig] = None):
        self.name = name
        self.config = config or LogConfig()
        self._logger = logging.getLogger(name)
        self._setup_handlers()
        self._error_counts: Dict[str, int] = {}
        self._performance_data: Dict[str, list] = {}
        self._lock = threading.Lock()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 清除现有处理器
        self._logger.handlers.clear()
        
        handler = LogHandler(self.config)
        
        # 添加控制台处理器
        self._logger.addHandler(handler.create_console_handler())
        
        # 添加文件处理器
        self._logger.addHandler(handler.create_file_handler("wxbot.log"))
        
        # 添加JSON格式处理器
        if self.config.json_format:
            self._logger.addHandler(handler.create_json_handler())
        
        # 添加错误专用处理器
        if self.config.error_tracking_enabled:
            self._logger.addHandler(handler.create_error_handler())
        
        self._logger.setLevel(logging.DEBUG)
    
    def _log_with_data(self, level: int, message: str, data: Optional[Dict] = None, **kwargs):
        """带额外数据的日志记录"""
        record = self._logger.makeRecord(
            self.name, level, '', 0, message, (), None
        )
        if data:
            record.extra_data = data
        self._logger.handle(record)
    
    # 基础日志方法
    def trace(self, message: str, **kwargs):
        """追踪级别日志"""
        self._log_with_data(LogLevel.TRACE.value, message, kwargs)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """错误日志"""
        self._logger.error(message, exc_info=exc_info, **kwargs)
        
        # 记录错误计数
        with self._lock:
            error_key = message[:50]  # 使用前50字符作为key
            self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
    
    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """严重错误日志"""
        self._logger.critical(message, exc_info=exc_info, **kwargs)
    
    # 专用日志方法
    def operation(self, operation: str, target: str, success: bool = True, **kwargs):
        """操作日志"""
        status = "✅ 成功" if success else "❌ 失败"
        self.info(f"{status} | 操作: {operation} | 目标: {target}", **kwargs)
    
    def performance(self, operation: str, duration_ms: float, **kwargs):
        """性能日志"""
        data = {
            'operation': operation,
            'duration_ms': duration_ms,
            **kwargs
        }
        self._log_with_data(logging.INFO, f"⏱️ 性能 | {operation} | {duration_ms:.2f}ms", data)
        
        # 记录性能数据
        with self._lock:
            if operation not in self._performance_data:
                self._performance_data[operation] = []
            self._performance_data[operation].append(duration_ms)
    
    def security(self, event: str, details: Optional[Dict] = None):
        """安全日志"""
        self.warning(f"🔒 安全事件 | {event}", extra={'extra_data': details})
    
    def api_call(self, api: str, params: Optional[Dict] = None, response_time: Optional[float] = None):
        """API调用日志"""
        data = {'api': api, 'params': params, 'response_time_ms': response_time}
        self._log_with_data(logging.DEBUG, f"🌐 API调用 | {api}", data)
    
    # 统计方法
    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计"""
        with self._lock:
            return dict(self._error_counts)
    
    def get_performance_stats(self) -> Dict[str, Dict]:
        """获取性能统计"""
        with self._lock:
            stats = {}
            for op, times in self._performance_data.items():
                if times:
                    stats[op] = {
                        'count': len(times),
                        'avg_ms': sum(times) / len(times),
                        'min_ms': min(times),
                        'max_ms': max(times),
                    }
            return stats
    
    def reset_stats(self):
        """重置统计"""
        with self._lock:
            self._error_counts.clear()
            self._performance_data.clear()


# ============================================================
# 性能监控装饰器
# ============================================================

def log_performance(logger: Optional[EnhancedLogger] = None, operation: Optional[str] = None):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = (time.perf_counter() - start) * 1000
                op_name = operation or func.__name__
                if logger:
                    logger.performance(op_name, duration)
        return wrapper
    return decorator


def async_log_performance(logger: Optional[EnhancedLogger] = None, operation: Optional[str] = None):
    """异步性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = (time.perf_counter() - start) * 1000
                op_name = operation or func.__name__
                if logger:
                    logger.performance(op_name, duration)
        return wrapper
    return decorator


# ============================================================
# 错误追踪
# ============================================================

@dataclass
class ErrorReport:
    """错误报告"""
    timestamp: str
    error_type: str
    message: str
    traceback: str
    context: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


class ErrorTracker:
    """错误追踪器"""
    
    def __init__(self, logger: EnhancedLogger):
        self.logger = logger
        self._errors: list = []
        self._max_errors = 100
    
    def track(self, error: Exception, context: Optional[Dict] = None):
        """追踪错误"""
        report = ErrorReport(
            timestamp=datetime.now().isoformat(),
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc() if hasattr(error, '__traceback__') else '',
            context=context or {},
        )
        
        self._errors.append(report)
        
        # 限制数量
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]
        
        self.logger.error(
            f"错误追踪: {report.error_type} - {report.message}",
            extra={'extra_data': asdict(report)}
        )
    
    def get_recent_errors(self, count: int = 10) -> list:
        """获取最近的错误"""
        return self._errors[-count:]
    
    def export_errors(self, filepath: str):
        """导出错误报告"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for error in self._errors:
                f.write(error.to_json() + '\n')


# ============================================================
# 全局日志管理器
# ============================================================

class LoggerManager:
    """全局日志管理器"""
    
    _instance: Optional['LoggerManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._loggers: Dict[str, EnhancedLogger] = {}
        self._config = LogConfig()
        self._error_tracker: Optional[ErrorTracker] = None
    
    def get_logger(self, name: str) -> EnhancedLogger:
        """获取日志器"""
        if name not in self._loggers:
            self._loggers[name] = EnhancedLogger(name, self._config)
            if self._error_tracker is None:
                self._error_tracker = ErrorTracker(self._loggers[name])
        return self._loggers[name]
    
    def set_config(self, config: LogConfig):
        """设置配置"""
        self._config = config
        # 重新初始化所有日志器
        for name, logger in self._loggers.items():
            logger.config = config
            logger._setup_handlers()
    
    def get_error_tracker(self) -> Optional[ErrorTracker]:
        """获取错误追踪器"""
        return self._error_tracker


# 全局实例
logger_manager = LoggerManager()


def get_logger(name: str = 'wxbota') -> EnhancedLogger:
    """获取日志器（便捷方法）"""
    return logger_manager.get_logger(name)


# ============================================================
# 初始化
# ============================================================

def init_logging(config: Optional[LogConfig] = None):
    """初始化日志系统"""
    if config:
        logger_manager.set_config(config)
    
    logger = get_logger('wxbota')
    logger.info("=" * 60)
    logger.info("jz-wxbot 日志系统初始化完成")
    logger.info(f"日志目录: {logger.config.log_dir}")
    logger.info("=" * 60)
    
    return logger


# ============================================================
# 导出
# ============================================================

__all__ = [
    'LogConfig',
    'EnhancedLogger',
    'ErrorTracker',
    'ErrorReport',
    'LoggerManager',
    'get_logger',
    'init_logging',
    'log_performance',
    'async_log_performance',
]