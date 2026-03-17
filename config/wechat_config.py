# -*- coding: utf-8 -*-
"""
微信自动化配置模块
基于 pywechat GlobalConfig 改编

使用示例:
    from config.wechat_config import GlobalConfig, WeChatConfig
    
    # 全局配置
    GlobalConfig.is_maximize = True
    GlobalConfig.load_delay = 2.0
    
    # 或创建独立配置实例
    config = WeChatConfig()
    config.is_maximize = False
"""

from typing import Tuple


class WeChatConfig:
    """
    微信自动化配置类 (单例模式)
    提供全局配置管理
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_defaults()
        return cls._instance
    
    def _initialize_defaults(self):
        """初始化默认配置"""
        self._is_maximize = False
        self._close_wechat = True
        self._load_delay = 3.5
        self._search_pages = 5
        self._window_maximize = False
        self._send_delay = 0.2
        self._window_size = (1000, 800)
        self._wechat_path = None
        self._auto_login = True
        self._retry_count = 3
        self._screenshot_on_error = True
    
    @property
    def is_maximize(self) -> bool:
        """微信主界面全屏"""
        return self._is_maximize
    
    @is_maximize.setter
    def is_maximize(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"is_maximize 必须是 bool 类型, 但传入了 {type(value)}: {value}")
        self._is_maximize = value
    
    @property
    def window_size(self) -> Tuple[int, int]:
        """微信主界面大小 (宽, 高)"""
        return self._window_size
    
    @window_size.setter
    def window_size(self, value: Tuple[int, int]):
        if not isinstance(value, tuple) or len(value) != 2:
            raise TypeError(f"window_size 必须是 (宽, 高) 元组, 但传入了 {type(value)}: {value}")
        self._window_size = value
    
    @property
    def close_wechat(self) -> bool:
        """任务结束后是否关闭微信"""
        return self._close_wechat
    
    @close_wechat.setter
    def close_wechat(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"close_wechat 必须是 bool 类型, 但传入了 {type(value)}: {value}")
        self._close_wechat = value
    
    @property
    def load_delay(self) -> float:
        """打开小程序/视频号/公众号的加载时长 (秒)"""
        return self._load_delay
    
    @load_delay.setter
    def load_delay(self, value: float):
        if not isinstance(value, (int, float)) or value < 0:
            raise TypeError(f"load_delay 必须是正数, 但传入了 {type(value)}: {value}")
        self._load_delay = float(value)
    
    @property
    def search_pages(self) -> int:
        """会话列表搜索页数"""
        return self._search_pages
    
    @search_pages.setter
    def search_pages(self, value: int):
        if not isinstance(value, int) or value < 0:
            raise TypeError(f"search_pages 必须是正整数, 但传入了 {type(value)}: {value}")
        self._search_pages = value
    
    @property
    def window_maximize(self) -> bool:
        """独立窗口全屏"""
        return self._window_maximize
    
    @window_maximize.setter
    def window_maximize(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"window_maximize 必须是 bool 类型, 但传入了 {type(value)}: {value}")
        self._window_maximize = value
    
    @property
    def send_delay(self) -> float:
        """发送消息间隔 (秒)"""
        return self._send_delay
    
    @send_delay.setter
    def send_delay(self, value: float):
        if not isinstance(value, (int, float)) or value < 0:
            raise TypeError(f"send_delay 必须是正数, 但传入了 {type(value)}: {value}")
        self._send_delay = float(value)
    
    @property
    def wechat_path(self) -> str:
        """微信安装路径"""
        return self._wechat_path
    
    @wechat_path.setter
    def wechat_path(self, value: str):
        self._wechat_path = value
    
    @property
    def auto_login(self) -> bool:
        """自动登录 PC 微信"""
        return self._auto_login
    
    @auto_login.setter
    def auto_login(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"auto_login 必须是 bool 类型")
        self._auto_login = value
    
    @property
    def retry_count(self) -> int:
        """操作重试次数"""
        return self._retry_count
    
    @retry_count.setter
    def retry_count(self, value: int):
        if not isinstance(value, int) or value < 0:
            raise TypeError(f"retry_count 必须是正整数")
        self._retry_count = value
    
    @property
    def screenshot_on_error(self) -> bool:
        """出错时自动截图"""
        return self._screenshot_on_error
    
    @screenshot_on_error.setter
    def screenshot_on_error(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"screenshot_on_error 必须是 bool 类型")
        self._screenshot_on_error = value
    
    def to_dict(self) -> dict:
        """导出配置为字典"""
        return {
            'is_maximize': self._is_maximize,
            'close_wechat': self._close_wechat,
            'load_delay': self._load_delay,
            'search_pages': self._search_pages,
            'window_maximize': self._window_maximize,
            'send_delay': self._send_delay,
            'window_size': self._window_size,
            'wechat_path': self._wechat_path,
            'auto_login': self._auto_login,
            'retry_count': self._retry_count,
            'screenshot_on_error': self._screenshot_on_error,
        }
    
    @classmethod
    def from_dict(cls, config_dict: dict):
        """从字典加载配置"""
        instance = cls()
        for key, value in config_dict.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    def reset(self):
        """重置为默认配置"""
        self._initialize_defaults()


# 全局单例实例
GlobalConfig = WeChatConfig()