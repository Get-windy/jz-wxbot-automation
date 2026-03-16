# -*- coding: utf-8 -*-
"""
个人微信消息读取器
版本: v1.0.0
功能: 实现个人微信消息接收功能
"""

import time
import threading
import win32gui
import win32con
import psutil
from typing import Callable, List, Optional
from datetime import datetime
import logging

from core.message_reader_interface import (
    MessageReaderInterface, 
    WeChatMessage, 
    MessageType, 
    ChatType,
    ReadResult
)
from human_like_operations import HumanLikeOperations

logger = logging.getLogger(__name__)


class WeChatMessageReader(MessageReaderInterface):
    """个人微信消息读取器"""
    
    def __init__(self, config: dict = None):
        """初始化消息读取器"""
        super().__init__(config)
        
        self.process_names = ["WeChat.exe", "Weixin.exe", "wechat.exe"]
        self.wechat_pid = None
        self.main_window_hwnd = None
        
        # 人性化操作
        self.human_ops = HumanLikeOperations()
        
        # 监听线程
        self._listen_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 消息缓存
        self._message_cache = []
        self._last_message_time = datetime.now()
        
    def initialize(self) -> bool:
        """初始化读取器"""
        try:
            logger.info("初始化个人微信消息读取器...")
            
            # 查找微信进程
            if not self._find_wechat_process():
                logger.error("未找到个人微信进程")
                return False
            
            # 查找微信窗口
            if not self._find_wechat_window():
                logger.error("未找到个人微信窗口")
                return False
            
            self.is_initialized = True
            logger.info("个人微信消息读取器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def _find_wechat_process(self) -> bool:
        """查找微信进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if any(name.lower() in proc.info['name'].lower() for name in self.process_names):
                        self.wechat_pid = proc.info['pid']
                        logger.info(f"找到微信进程 PID: {self.wechat_pid}")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception as e:
            logger.error(f"查找进程失败: {e}")
            return False
    
    def _find_wechat_window(self) -> bool:
        """查找微信主窗口"""
        try:
            def enum_windows(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    _, pid = win32gui.GetWindowThreadProcessId(hwnd)
                    if pid == self.wechat_pid:
                        class_name = win32gui.GetClassName(hwnd)
                        if "WeChatMainWndFor" in class_name or "WeChat" in class_name:
                            self.main_window_hwnd = hwnd
                            return False
                return True
            
            win32gui.EnumWindows(enum_windows, None)
            
            if self.main_window_hwnd:
                logger.info(f"找到微信窗口句柄: {self.main_window_hwnd}")
                return True
            return False
        except Exception as e:
            logger.error(f"查找窗口失败: {e}")
            return False
    
    def start_listening(self, callback: Callable[[WeChatMessage], None]) -> bool:
        """启动消息监听"""
        try:
            if not self.is_initialized:
                logger.error("读取器未初始化")
                return False
            
            if self._listening:
                logger.warning("已经在监听中")
                return True
            
            self._message_callback = callback
            self._stop_event.clear()
            
            # 启动监听线程
            self._listen_thread = threading.Thread(
                target=self._listen_loop,
                daemon=True
            )
            self._listen_thread.start()
            
            self._listening = True
            logger.info("消息监听已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动监听失败: {e}")
            return False
    
    def stop_listening(self) -> bool:
        """停止消息监听"""
        try:
            if not self._listening:
                return True
            
            self._stop_event.set()
            
            if self._listen_thread:
                self._listen_thread.join(timeout=5)
            
            self._listening = False
            logger.info("消息监听已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止监听失败: {e}")
            return False
    
    def _listen_loop(self):
        """监听循环"""
        logger.info("消息监听线程启动")
        
        while not self._stop_event.is_set():
            try:
                # 模拟消息检测（实际实现需要更复杂的逻辑）
                messages = self._detect_new_messages()
                
                for msg in messages:
                    if self._message_callback:
                        self._message_callback(msg)
                
                # 短暂休眠
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"监听循环错误: {e}")
                time.sleep(5)
        
        logger.info("消息监听线程结束")
    
    def _detect_new_messages(self) -> List[WeChatMessage]:
        """检测新消息（模拟实现）"""
        # TODO: 实现真实的消息检测逻辑
        # 这里使用模拟数据演示
        return []
    
    def get_unread_messages(self, count: int = 10) -> List[WeChatMessage]:
        """获取未读消息"""
        # TODO: 实现获取未读消息逻辑
        return []


# 注册到工厂
from core.message_reader_interface import MessageReaderFactory
MessageReaderFactory.register_reader('wechat', WeChatMessageReader)
