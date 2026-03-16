# -*- coding: utf-8 -*-
"""
企业微信消息读取器
版本: v1.0.0
功能: 实现企业微信消息接收功能
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


class WXWorkMessageReader(MessageReaderInterface):
    """企业微信消息读取器"""
    
    def __init__(self, config: dict = None):
        """初始化消息读取器"""
        super().__init__(config)
        
        self.process_names = ["WXWork.exe", "wxwork.exe"]
        self.wxwork_pid = None
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
            logger.info("初始化企业微信消息读取器...")
            
            # 查找企业微信进程
            if not self._find_wxwork_process():
                logger.error("未找到企业微信进程")
                return False
            
            # 查找企业微信窗口
            if not self._find_wxwork_window():
                logger.error("未找到企业微信窗口")
                return False
            
            self.is_initialized = True
            logger.info("企业微信消息读取器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def _find_wxwork_process(self) -> bool:
        """查找企业微信进程"""
        try:
            wxwork_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    proc_name = proc.info['name']
                    if any(name.lower() in proc_name.lower() for name in self.process_names):
                        memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                        wxwork_processes.append({
                            'pid': proc.pid,
                            'name': proc_name,
                            'memory_mb': memory_mb
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not wxwork_processes:
                return False
            
            # 选择内存最大的主进程
            main_process = max(wxwork_processes, key=lambda p: p['memory_mb'])
            self.wxwork_pid = main_process['pid']
            logger.info(f"找到企业微信进程 PID: {self.wxwork_pid}")
            return True
            
        except Exception as e:
            logger.error(f"查找进程失败: {e}")
            return False
    
    def _find_wxwork_window(self) -> bool:
        """查找企业微信主窗口"""
        try:
            def enum_windows(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    _, pid = win32gui.GetWindowThreadProcessId(hwnd)
                    if pid == self.wxwork_pid:
                        class_name = win32gui.GetClassName(hwnd)
                        if class_name == "WeWorkWindow":
                            self.main_window_hwnd = hwnd
                            return False
                return True
            
            win32gui.EnumWindows(enum_windows, None)
            
            if self.main_window_hwnd:
                logger.info(f"找到企业微信窗口句柄: {self.main_window_hwnd}")
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
            logger.info("企业微信消息监听已启动")
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
            logger.info("企业微信消息监听已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止监听失败: {e}")
            return False
    
    def _listen_loop(self):
        """监听循环"""
        logger.info("企业微信消息监听线程启动")
        
        while not self._stop_event.is_set():
            try:
                # 模拟消息检测
                messages = self._detect_new_messages()
                
                for msg in messages:
                    if self._message_callback:
                        self._message_callback(msg)
                
                # 短暂休眠
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"监听循环错误: {e}")
                time.sleep(5)
        
        logger.info("企业微信消息监听线程结束")
    
    def _detect_new_messages(self) -> List[WeChatMessage]:
        """检测新消息（模拟实现）"""
        # TODO: 实现真实的消息检测逻辑
        return []
    
    def get_unread_messages(self, count: int = 10) -> List[WeChatMessage]:
        """获取未读消息"""
        # TODO: 实现获取未读消息逻辑
        return []


# 注册到工厂
from core.message_reader_interface import MessageReaderFactory
MessageReaderFactory.register_reader('wxwork', WXWorkMessageReader)
