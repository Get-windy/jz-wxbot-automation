# -*- coding: utf-8 -*-
"""
微信消息监听器
版本: v1.0.0
功能: 监听微信消息并触发回调
"""

import asyncio
import logging
import threading
import time
import re
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    LINK = "link"
    EMOTION = "emotion"
    SYSTEM = "system"


class ChatType(Enum):
    """聊天类型"""
    PRIVATE = "private"
    GROUP = "group"
    OFFICIAL = "official"


@dataclass
class WxMessage:
    """微信消息数据结构"""
    message_id: str
    sender_id: str
    sender_name: str
    chat_id: str
    chat_name: str
    content: str
    chat_type: ChatType = ChatType.PRIVATE
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)
    is_mentioned: bool = False
    at_user_ids: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'message_id': self.message_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'chat_id': self.chat_id,
            'chat_name': self.chat_name,
            'content': self.content,
            'chat_type': self.chat_type.value,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp.isoformat(),
            'is_mentioned': self.is_mentioned,
            'at_user_ids': self.at_user_ids,
            'extra': self.extra
        }


class MessageListener:
    """
    微信消息监听器
    
    通过 UI 自动化监听微信消息
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化消息监听器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 消息回调
        self.on_message: Optional[Callable[[WxMessage], None]] = None
        
        # 运行状态
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 消息去重
        self._seen_messages: Dict[str, float] = {}
        self._seen_messages_ttl = 300  # 5分钟
        
        # 统计
        self.stats = {
            'messages_received': 0,
            'errors': 0,
            'start_time': None
        }
        
        # 微信窗口句柄
        self._wechat_hwnd = None
        
    def start(self) -> bool:
        """
        启动消息监听
        
        Returns:
            bool: 是否启动成功
        """
        if self.running:
            logger.warning("消息监听器已在运行")
            return True
        
        try:
            logger.info("启动微信消息监听器...")
            
            # 查找微信窗口
            if not self._find_wechat_window():
                logger.error("未找到微信窗口")
                return False
            
            # 启动监听线程
            self.running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            
            self.stats['start_time'] = datetime.now()
            logger.info("消息监听器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动消息监听器失败: {e}")
            self.running = False
            return False
    
    def stop(self):
        """停止消息监听"""
        if not self.running:
            return
        
        logger.info("停止消息监听器...")
        
        self.running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        
        logger.info("消息监听器已停止")
    
    def _find_wechat_window(self) -> bool:
        """
        查找微信窗口
        
        Returns:
            bool: 是否找到
        """
        try:
            import win32gui
            import win32con
            
            def enum_windows_callback(hwnd, results):
                class_name = win32gui.GetClassName(hwnd)
                window_title = win32gui.GetWindowText(hwnd)
                
                # 微信主窗口类名
                if class_name == 'WeChatMainWndForPC':
                    results.append(hwnd)
                # 企业微信
                elif class_name == 'WXWorkWindow':
                    results.append(hwnd)
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            if windows:
                self._wechat_hwnd = windows[0]
                logger.info(f"找到微信窗口: {self._wechat_hwnd}")
                return True
            else:
                return False
                
        except ImportError:
            logger.warning("win32gui 未安装，使用备用方法")
            return self._find_wechat_window_fallback()
        except Exception as e:
            logger.error(f"查找微信窗口失败: {e}")
            return False
    
    def _find_wechat_window_fallback(self) -> bool:
        """
        备用方法查找微信窗口
        
        Returns:
            bool: 是否找到
        """
        try:
            import pyautogui
            
            # 尝试通过窗口标题查找
            # 这需要微信窗口可见
            screen_width, screen_height = pyautogui.size()
            
            # 点击屏幕左上角激活窗口
            pyautogui.click(100, 100)
            time.sleep(0.5)
            
            # 模拟方法，实际需要更复杂的实现
            return True
            
        except Exception as e:
            logger.error(f"备用查找微信窗口失败: {e}")
            return False
    
    def _listen_loop(self):
        """
        消息监听循环
        """
        logger.info("消息监听循环开始")
        
        poll_interval = self.config.get('poll_interval', 1.0)
        
        while self.running and not self._stop_event.is_set():
            try:
                # 轮询新消息
                messages = self._poll_messages()
                
                for msg in messages:
                    # 去重
                    if self._is_duplicate(msg):
                        continue
                    
                    # 触发回调
                    if self.on_message:
                        try:
                            self.on_message(msg)
                            self.stats['messages_received'] += 1
                        except Exception as e:
                            logger.error(f"消息回调错误: {e}")
                            self.stats['errors'] += 1
                
                # 清理过期消息
                self._cleanup_seen_messages()
                
                # 等待下次轮询
                self._stop_event.wait(poll_interval)
                
            except Exception as e:
                logger.error(f"消息监听错误: {e}")
                self.stats['errors'] += 1
                time.sleep(2)
        
        logger.info("消息监听循环结束")
    
    def _poll_messages(self) -> List[WxMessage]:
        """
        轮询新消息
        
        Returns:
            List[WxMessage]: 新消息列表
        """
        messages = []
        
        try:
            # 方法1: 使用 UI 自动化读取消息
            messages = self._read_messages_uia()
            
            if not messages:
                # 方法2: 使用剪贴板读取（备用）
                messages = self._read_messages_clipboard()
            
        except Exception as e:
            logger.error(f"轮询消息失败: {e}")
        
        return messages
    
    def _read_messages_uia(self) -> List[WxMessage]:
        """
        使用 UI 自动化读取消息
        
        Returns:
            List[WxMessage]: 消息列表
        """
        messages = []
        
        try:
            import pywinauto
            from pywinauto import Application
            
            # 连接到微信进程
            try:
                app = Application(backend='uia').connect(handle=self._wechat_hwnd)
                window = app.window(handle=self._wechat_hwnd)
                
                # 查找消息列表控件
                # 微信的消息列表通常是一个 List 控件
                message_list = window.child_window(
                    auto_id="messageList",
                    control_type="List"
                )
                
                if message_list.exists():
                    # 获取所有消息项
                    items = message_list.children()
                    
                    for item in items[-10:]:  # 只处理最近10条
                        try:
                            # 提取消息内容
                            content = item.window_text()
                            
                            if content and len(content) > 0:
                                msg = WxMessage(
                                    message_id=f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(content) % 10000}",
                                    sender_id="unknown",
                                    sender_name="未知用户",
                                    chat_id="current",
                                    chat_name="当前聊天",
                                    content=content,
                                    timestamp=datetime.now()
                                )
                                messages.append(msg)
                        except Exception as e:
                            logger.debug(f"解析消息项失败: {e}")
                            
            except Exception as e:
                logger.debug(f"连接微信窗口失败: {e}")
                
        except ImportError:
            logger.debug("pywinauto 未安装")
        except Exception as e:
            logger.error(f"UI 自动化读取消息失败: {e}")
        
        return messages
    
    def _read_messages_clipboard(self) -> List[WxMessage]:
        """
        使用剪贴板读取消息（备用方法）
        
        Returns:
            List[WxMessage]: 消息列表
        """
        messages = []
        
        try:
            import pyautogui
            import pyperclip
            
            # 激活微信窗口
            if self._wechat_hwnd:
                import win32gui
                win32gui.SetForegroundWindow(self._wechat_hwnd)
                time.sleep(0.3)
            
            # 快捷键复制消息
            # Ctrl+A 选择当前消息
            # Ctrl+C 复制
            
            # 这只是一个示例，实际实现需要更复杂的逻辑
            # 包括导航到不同的聊天
            
        except Exception as e:
            logger.debug(f"剪贴板读取消息失败: {e}")
        
        return messages
    
    def _is_duplicate(self, message: WxMessage) -> bool:
        """
        检查是否是重复消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否重复
        """
        key = f"{message.chat_id}:{message.message_id}"
        now = time.time()
        
        if key in self._seen_messages:
            return True
        
        self._seen_messages[key] = now
        return False
    
    def _cleanup_seen_messages(self):
        """清理过期的已见消息"""
        now = time.time()
        expired = [
            key for key, timestamp in self._seen_messages.items()
            if now - timestamp > self._seen_messages_ttl
        ]
        
        for key in expired:
            del self._seen_messages[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            'running': self.running,
            'messages_received': self.stats['messages_received'],
            'errors': self.stats['errors'],
            'uptime_seconds': uptime
        }


class MessagePoller:
    """
    消息轮询器
    
    主动轮询微信消息，适用于无法使用回调的场景
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化消息轮询器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.listener = MessageListener(config)
    
    def poll(self, count: int = 10, chat_id: str = None) -> List[WxMessage]:
        """
        轮询消息
        
        Args:
            count: 消息数量
            chat_id: 聊天 ID（可选）
            
        Returns:
            List[WxMessage]: 消息列表
        """
        # 一次性轮询
        messages = self.listener._poll_messages()
        
        # 过滤聊天
        if chat_id:
            messages = [m for m in messages if m.chat_id == chat_id]
        
        # 限制数量
        return messages[:count]
    
    def poll_unread(self) -> List[WxMessage]:
        """
        轮询未读消息
        
        Returns:
            List[WxMessage]: 未读消息列表
        """
        # 实现未读消息检测
        # 通常通过检查聊天列表上的红点数字
        return []


class WebhookMessageReceiver:
    """
    Webhook 消息接收器
    
    通过 HTTP Webhook 接收微信消息（需要配合其他服务）
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 Webhook 接收器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.on_message: Optional[Callable[[WxMessage], None]] = None
        
        # HTTP 服务器
        self._server = None
        self._port = config.get('port', 8080)
    
    async def start(self):
        """启动 Webhook 服务器"""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/webhook/message', self._handle_message)
        app.router.add_get('/health', self._handle_health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        self._server = web.TCPSite(runner, '0.0.0.0', self._port)
        await self._server.start()
        
        logger.info(f"Webhook 消息接收器已启动，端口: {self._port}")
    
    async def _handle_message(self, request):
        """
        处理消息 Webhook 请求
        """
        try:
            data = await request.json()
            
            # 解析消息
            msg = WxMessage(
                message_id=data.get('message_id', ''),
                sender_id=data.get('sender_id', ''),
                sender_name=data.get('sender_name', ''),
                chat_id=data.get('chat_id', ''),
                chat_name=data.get('chat_name', ''),
                content=data.get('content', ''),
                chat_type=ChatType(data.get('chat_type', 'private')),
                message_type=MessageType(data.get('message_type', 'text')),
                timestamp=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now(),
                is_mentioned=data.get('is_mentioned', False),
                at_user_ids=data.get('at_user_ids', []),
                extra=data.get('extra', {})
            )
            
            # 触发回调
            if self.on_message:
                await self.on_message(msg) if asyncio.iscoroutinefunction(self.on_message) else self.on_message(msg)
            
            return web.json_response({'success': True})
            
        except Exception as e:
            logger.error(f"处理 Webhook 消息失败: {e}")
            return web.json_response({'success': False, 'error': str(e)}, status=500)
    
    async def _handle_health(self, request):
        """健康检查"""
        return web.json_response({'status': 'healthy'})


# 导出
__all__ = [
    'MessageListener',
    'MessagePoller',
    'WebhookMessageReceiver',
    'WxMessage',
    'MessageType',
    'ChatType'
]