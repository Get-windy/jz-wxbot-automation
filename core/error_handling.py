"""
jz-wxbot 错误处理与日志系统
统一错误处理和日志记录
"""

import logging
import sys
from datetime import datetime
from typing import Optional, Callable, Any
from functools import wraps
import traceback

# 日志配置
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 错误级别
class ErrorLevel:
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'

# 错误类型
class WxBotError(Exception):
    """微信机器人基础错误"""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or 'UNKNOWN_ERROR'
        self.timestamp = datetime.now()
        super().__init__(self.message)

class ConnectionError(WxBotError):
    """连接错误"""
    pass

class AuthenticationError(WxBotError):
    """认证错误"""
    pass

class MessageError(WxBotError):
    """消息处理错误"""
    pass

class APIError(WxBotError):
    """API调用错误"""
    pass

class ConfigError(WxBotError):
    """配置错误"""
    pass

# 日志管理器
class LogManager:
    """统一日志管理器"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.log_dir = 'logs'
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """配置根日志器"""
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
            handlers=[
                logging.StreamHandler(sys.stdout),
            ]
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志器"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            self._loggers[name] = logger
        return self._loggers[name]
    
    def add_file_handler(self, name: str, filename: str):
        """添加文件处理器"""
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        logger = self.get_logger(name)
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, filename),
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(file_handler)

# 全局日志管理器
log_manager = LogManager()

def get_logger(name: str = 'wxbota') -> logging.Logger:
    """获取日志器"""
    return log_manager.get_logger(name)

# 错误处理器
class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, logger_name: str = 'wxbota'):
        self.logger = get_logger(logger_name)
        self.error_callbacks = []
    
    def register_callback(self, callback: Callable[[WxBotError], None]):
        """注册错误回调"""
        self.error_callbacks.append(callback)
    
    def handle_error(self, error: WxBotError):
        """处理错误"""
        self.logger.error(f"[{error.code}] {error.message}")
        
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                self.logger.error(f"Error callback failed: {e}")
    
    def handle_exception(self, exc: Exception, context: Optional[dict] = None):
        """处理异常"""
        if isinstance(exc, WxBotError):
            self.handle_error(exc)
        else:
            self.logger.error(f"Unexpected error: {exc}\n{traceback.format_exc()}")

# 全局错误处理器
error_handler = ErrorHandler()

# 装饰器：自动错误处理
def handle_errors(func: Callable) -> Callable:
    """错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except WxBotError as e:
            error_handler.handle_error(e)
            raise
        except Exception as e:
            error_handler.handle_exception(e)
            raise
    return wrapper

# 装饰器：重试机制
def retry(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    import time
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    get_logger().warning(
                        f"Retry {attempt + 1}/{max_retries} failed: {e}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_error
        return wrapper
    return decorator

# 上下文管理器：错误捕获
class ErrorContext:
    """错误捕获上下文管理器"""
    
    def __init__(self, error_message: str = "Operation failed"):
        self.error_message = error_message
        self.logger = get_logger()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(f"{self.error_message}: {exc_val}")
            if isinstance(exc_val, WxBotError):
                error_handler.handle_error(exc_val)
            return False  # 不抑制异常
        return True

# 使用示例
if __name__ == '__main__':
    logger = get_logger('test')
    logger.info("日志系统初始化完成")
    
    @handle_errors
    def test_function():
        raise WxBotError("测试错误", "TEST_ERROR")
    
    # 测试错误处理
    try:
        test_function()
    except WxBotError:
        print("错误已捕获并记录")