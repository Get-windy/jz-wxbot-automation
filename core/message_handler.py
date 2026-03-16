# -*- coding: utf-8 -*-
"""
微信消息处理器
版本: v1.0.0
功能: 实现微信消息的接收、解析、队列管理
"""

import queue
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from collections import deque
import logging

from core.message_reader_interface import (
    MessageReaderInterface,
    WeChatMessage,
    MessageType,
    ChatType,
    ReadResult
)

logger = logging.getLogger(__name__)


class MessageQueue:
    """消息队列管理"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化消息队列
        
        Args:
            max_size: 队列最大容量
        """
        self._queue = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        
    def put(self, message: WeChatMessage) -> bool:
        """
        添加消息到队列
        
        Args:
            message: 微信消息对象
            
        Returns:
            bool: 添加是否成功
        """
        with self._lock:
            if len(self._queue) >= self._queue.maxlen:
                logger.warning("消息队列已满，丢弃最旧的消息")
                return False
            self._queue.append(message)
            self._not_empty.notify()
            return True
    
    def get(self, timeout: float = None) -> Optional[WeChatMessage]:
        """
        获取消息
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            WeChatMessage: 消息对象，超时返回None
        """
        with self._not_empty:
            if not self._queue:
                self._not_empty.wait(timeout)
            if self._queue:
                return self._queue.popleft()
            return None
    
    def get_batch(self, count: int = 10) -> List[WeChatMessage]:
        """
        批量获取消息
        
        Args:
            count: 获取数量
            
        Returns:
            List[WeChatMessage]: 消息列表
        """
        messages = []
        with self._lock:
            for _ in range(min(count, len(self._queue))):
                if self._queue:
                    messages.append(self._queue.popleft())
        return messages
    
    def clear(self):
        """清空队列"""
        with self._lock:
            self._queue.clear()
    
    def size(self) -> int:
        """获取队列大小"""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """检查队列是否为空"""
        with self._lock:
            return len(self._queue) == 0


class MessageHandler:
    """微信消息处理器 - UI自动化实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化消息处理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._message_queue = MessageQueue(max_size=self.config.get('queue_size', 1000))
        self._callbacks: List[Callable[[WeChatMessage], None]] = []
        self._listening = False
        self._listener_thread: Optional[threading.Thread] = None
        self._last_message_id = ""
        
    def register_callback(self, callback: Callable[[WeChatMessage], None]):
        """
        注册消息回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks.append(callback)
        logger.info(f"已注册消息回调: {callback.__name__}")
    
    def unregister_callback(self, callback: Callable[[WeChatMessage], None]):
        """
        注销消息回调
        
        Args:
            callback: 回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.info(f"已注销消息回调: {callback.__name__}")
    
    def _notify_callbacks(self, message: WeChatMessage):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"执行回调失败: {e}")
    
    def parse_message_type(self, content: str, raw_data: Dict = None) -> MessageType:
        """
        解析消息类型
        
        Args:
            content: 消息内容
            raw_data: 原始数据
            
        Returns:
            MessageType: 消息类型
        """
        if raw_data:
            msg_type = raw_data.get('message_type', '')
            if msg_type == 'image':
                return MessageType.IMAGE
            elif msg_type == 'file':
                return MessageType.FILE
            elif msg_type == 'link':
                return MessageType.LINK
            elif msg_type == 'video':
                return MessageType.VIDEO
            elif msg_type == 'voice':
                return MessageType.VOICE
            elif msg_type == 'emotion':
                return MessageType.EMOTION
        
        # 根据内容特征判断
        if content.startswith('[图片]'):
            return MessageType.IMAGE
        elif content.startswith('[文件]'):
            return MessageType.FILE
        elif content.startswith('[视频]'):
            return MessageType.VIDEO
        elif content.startswith('[链接]'):
            return MessageType.LINK
        elif content.startswith('[表情]'):
            return MessageType.EMOTION
            
        return MessageType.TEXT
    
    def create_message(
        self,
        message_id: str,
        sender_id: str,
        sender_name: str,
        chat_id: str,
        chat_name: str,
        chat_type: str,
        content: str,
        raw_data: Dict = None
    ) -> WeChatMessage:
        """
        创建消息对象
        
        Args:
            message_id: 消息ID
            sender_id: 发送者ID
            sender_name: 发送者名称
            chat_id: 会话ID
            chat_name: 会话名称
            chat_type: 会话类型
            content: 消息内容
            raw_data: 原始数据
            
        Returns:
            WeChatMessage: 消息对象
        """
        # 解析聊天类型
        chat_type_enum = ChatType.PRIVATE
        if chat_type == 'group':
            chat_type_enum = ChatType.GROUP
        elif chat_type == 'official':
            chat_type_enum = ChatType.OFFICIAL
        
        # 解析消息类型
        message_type_enum = self.parse_message_type(content, raw_data)
        
        # 检测@提及
        is_mentioned = '@' in content and chat_type_enum == ChatType.GROUP
        
        return WeChatMessage(
            message_id=message_id,
            sender_id=sender_id,
            sender_name=sender_name,
            chat_id=chat_id,
            chat_name=chat_name,
            chat_type=chat_type_enum,
            content=content,
            message_type=message_type_enum,
            timestamp=datetime.now(),
            is_mentioned=is_mentioned,
            at_user_ids=self._parse_at_users(content) if is_mentioned else []
        )
    
    def _parse_at_users(self, content: str) -> List[str]:
        """
        解析@用户
        
        Args:
            content: 消息内容
            
        Returns:
            List[str]: 被@的用户ID列表
        """
        # 简单解析，实际需要根据具体格式调整
        at_users = []
        # 示例: @用户1 @用户2
        parts = content.split('@')
        for part in parts[1:]:
            username = part.strip().split()[0] if part.strip() else ""
            if username:
                at_users.append(username)
        return at_users
    
    def add_message(self, message: WeChatMessage):
        """
        添加消息到队列
        
        Args:
            message: 微信消息对象
        """
        if self._message_queue.put(message):
            logger.debug(f"添加消息到队列: {message.message_id}")
            self._notify_callbacks(message)
    
    def get_message(self, timeout: float = None) -> Optional[WeChatMessage]:
        """
        获取消息
        
        Args:
            timeout: 超时时间
            
        Returns:
            WeChatMessage: 消息对象
        """
        return self._message_queue.get(timeout)
    
    def get_messages(self, count: int = 10) -> List[WeChatMessage]:
        """
        批量获取消息
        
        Args:
            count: 获取数量
            
        Returns:
            List[WeChatMessage]: 消息列表
        """
        return self._message_queue.get_batch(count)
    
    def start_listening(self) -> bool:
        """
        启动消息监听
        
        Returns:
            bool: 启动是否成功
        """
        if self._listening:
            logger.warning("消息监听已在运行")
            return True
        
        self._listening = True
        self._listener_thread = threading.Thread(
            target=self._listen_messages,
            daemon=True
        )
        self._listener_thread.start()
        logger.info("消息监听已启动")
        return True
    
    def stop_listening(self) -> bool:
        """
        停止消息监听
        
        Returns:
            bool: 停止是否成功
        """
        self._listening = False
        if self._listener_thread:
            self._listener_thread.join(timeout=2)
            self._listener_thread = None
        logger.info("消息监听已停止")
        return True
    
    def _listen_messages(self):
        """后台监听线程"""
        logger.info("消息监听线程已启动")
        
        while self._listening:
            try:
                # 这里应该是UI自动化读取消息的逻辑
                # 由于是模拟实现，每5秒生成一条测试消息
                message = self._generate_test_message()
                if message:
                    self.add_message(message)
                    
            except Exception as e:
                logger.error(f"监听消息时出错: {e}")
            
            time.sleep(5)  # 5秒检查一次
    
    def _generate_test_message(self) -> Optional[WeChatMessage]:
        """生成测试消息"""
        import random
        
        test_messages = [
            ("测试消息1", "private", "用户A"),
            ("测试消息2", "group", "技术交流群"),
            ("收到文件: report.pdf", "private", "用户B"),
            ("[图片] 风景照", "group", "旅行爱好者"),
        ]
        
        content, chat_type, chat_name = random.choice(test_messages)
        
        message_id = f"msg_{int(time.time() * 1000)}"
        
        return self.create_message(
            message_id=message_id,
            sender_id=f"user_{random.randint(1000, 9999)}",
            sender_name=f"用户{random.randint(1, 100)}",
            chat_id=f"chat_{random.randint(100, 999)}",
            chat_name=chat_name,
            chat_type=chat_type,
            content=content
        )
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self._message_queue.size()
    
    def clear_queue(self):
        """清空队列"""
        self._message_queue.clear()
        logger.info("消息队列已清空")
    
    def get_handler_info(self) -> Dict[str, Any]:
        """
        获取处理器信息
        
        Returns:
            Dict: 处理器信息
        """
        return {
            "handler_type": "MessageHandler",
            "is_listening": self._listening,
            "queue_size": self.get_queue_size(),
            "callback_count": len(self._callbacks),
            "config": self.config
        }


class MessageSender:
    """消息发送器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化消息发送器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._initialized = False
        self._human_ops = None
        
        # 延迟导入，避免循环依赖
        try:
            from human_like_operations import HumanLikeOperations
            self._human_ops = HumanLikeOperations()
        except ImportError:
            logger.warning("未找到human_like_operations模块")
    
    def _initialize(self) -> bool:
        """
        初始化发送器
        
        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return True
        
        # 这里添加UI自动化初始化逻辑
        # 例如：启动微信、激活窗口等
        self._initialized = True
        logger.info("消息发送器已初始化")
        return True
    
    def send_text_message(self, chat_id: str, content: str) -> bool:
        """
        发送文本消息
        
        Args:
            chat_id: 会话ID
            content: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        if not self._initialized:
            self._initialize()
        
        try:
            # 添加人性化延迟
            if self._human_ops:
                self._human_ops.human_delay(base_time=0.5, variance=0.2)
            
            # TODO: 实现UI自动化发送逻辑
            # 1. 查找窗口
            # 2. 激活窗口
            # 3. 找到聊天窗口
            # 4. 输入内容
            # 5. 发送
            
            logger.info(f"发送文本消息到 {chat_id}: {content}")
            return True
            
        except Exception as e:
            logger.error(f"发送文本消息失败: {e}")
            return False
    
    def send_image_message(self, chat_id: str, image_path: str, caption: str = "") -> bool:
        """
        发送图片消息
        
        Args:
            chat_id: 会话ID
            image_path: 图片路径
            caption: 图片说明
            
        Returns:
            bool: 发送是否成功
        """
        if not self._initialized:
            self._initialize()
        
        try:
            if self._human_ops:
                self._human_ops.human_delay(base_time=0.8, variance=0.3)
            
            # TODO: 实现图片发送逻辑
            logger.info(f"发送图片到 {chat_id}: {image_path}")
            return True
            
        except Exception as e:
            logger.error(f"发送图片消息失败: {e}")
            return False
    
    def send_file_message(self, chat_id: str, file_path: str) -> bool:
        """
        发送文件消息
        
        Args:
            chat_id: 会话ID
            file_path: 文件路径
            
        Returns:
            bool: 发送是否成功
        """
        if not self._initialized:
            self._initialize()
        
        try:
            if self._human_ops:
                self._human_ops.human_delay(base_time=1.0, variance=0.3)
            
            # TODO: 实现文件发送逻辑
            logger.info(f"发送文件到 {chat_id}: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"发送文件消息失败: {e}")
            return False
    
    def send_group_message(self, group_id: str, content: str) -> bool:
        """
        发送群消息
        
        Args:
            group_id: 群ID
            content: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        return self.send_text_message(group_id, content)
    
    def send_at_message(self, group_id: str, user_id: str, user_name: str, content: str) -> bool:
        """
        发送@消息
        
        Args:
            group_id: 群ID
            user_id: 用户ID
            user_name: 用户昵称
            content: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        at_content = f"@{user_name} {content}"
        return self.send_text_message(group_id, at_content)
    
    def get_sender_info(self) -> Dict[str, Any]:
        """
        获取发送器信息
        
        Returns:
            Dict: 发送器信息
        """
        return {
            "sender_type": "MessageSender",
            "is_initialized": self._initialized,
            "config": self.config
        }


def create_test_messages(count: int = 10) -> List[WeChatMessage]:
    """
    创建测试消息
    
    Args:
        count: 消息数量
        
    Returns:
        List[WeChatMessage]: 消息列表
    """
    import random
    
    messages = []
    chat_types = ['private', 'group']
    message_contents = [
        "这是一条测试消息",
        "Hello World!",
        "今天天气真好",
        "[图片] 风景照",
        "收到文件: document.pdf",
    ]
    
    for i in range(count):
        chat_type = random.choice(chat_types)
        message = WeChatMessage(
            message_id=f"test_msg_{i}",
            sender_id=f"user_{random.randint(1000, 9999)}",
            sender_name=f"用户{random.randint(1, 50)}",
            chat_id=f"chat_{random.randint(100, 999)}",
            chat_name=f"会话{random.randint(1, 50)}",
            chat_type=ChatType.PRIVATE if chat_type == 'private' else ChatType.GROUP,
            content=random.choice(message_contents),
            message_type=MessageType.TEXT,
            timestamp=datetime.now()
        )
        messages.append(message)
    
    return messages


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试消息处理器
    handler = MessageHandler()
    
    def on_message(msg: WeChatMessage):
        print(f"收到消息: {msg.content}")
    
    handler.register_callback(on_message)
    handler.start_listening()
    
    # 运行10秒
    time.sleep(10)
    
    handler.stop_listening()
    print(f"队列大小: {handler.get_queue_size()}")
    print(f"处理器信息: {handler.get_handler_info()}")