# -*- coding: utf-8 -*-
"""
OpenClaw 微信桥接服务
版本: v1.0.0
功能: 连接微信自动化和 OpenClaw 平台
"""

import asyncio
import logging
import threading
import time
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime

from openclaw_client import (
    OpenClawClient, 
    WeChatMessage, 
    OpenClawResponse,
    ChatType,
    MessageType,
    get_openclaw_client
)

# 导入现有的发送器
import sys
sys.path.insert(0, '..')
from message_sender_interface import MessageSenderFactory
from human_like_operations import HumanLikeOperations

logger = logging.getLogger(__name__)


class BridgeService:
    """
    OpenClaw 微信桥接服务
    
    核心功能:
    1. 消息监听 - 接收微信消息并转发到 OpenClaw
    2. 消息发送 - 将 OpenClaw 的回复发送到微信
    3. 命令执行 - 执行 OpenClaw 下发的命令
    4. 状态同步 - 同步微信状态到 OpenClaw
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化桥接服务
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # OpenClaw 客户端
        self.openclaw: Optional[OpenClawClient] = None
        
        # 微信发送器
        self.wechat_sender = None
        self.wxwork_sender = None
        
        # 人性化操作模块
        self.human_ops = HumanLikeOperations()
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        
        # 命令处理器
        self.command_handlers: Dict[str, Callable] = {}
        
        # 运行状态
        self.running = False
        self._thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.stats = {
            'messages_received': 0,
            'messages_sent': 0,
            'commands_executed': 0,
            'errors': 0
        }
    
    async def initialize(self) -> bool:
        """
        初始化桥接服务
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            logger.info("初始化 OpenClaw 微信桥接服务...")
            
            # 1. 初始化微信发送器
            await self._initialize_senders()
            
            # 2. 初始化 OpenClaw 客户端
            await self._initialize_openclaw()
            
            # 3. 注册命令处理器
            self._register_default_commands()
            
            logger.info("桥接服务初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化桥接服务失败: {e}")
            return False
    
    async def _initialize_senders(self):
        """初始化微信发送器"""
        try:
            # 尝试初始化个人微信
            wechat_factory = MessageSenderFactory()
            if 'wechat' in wechat_factory.get_available_senders():
                self.wechat_sender = wechat_factory.create_sender('wechat', self.config.get('wechat', {}))
                if self.wechat_sender and self.wechat_sender.initialize():
                    logger.info("个人微信发送器初始化成功")
                else:
                    logger.warning("个人微信发送器初始化失败")
                    self.wechat_sender = None
            else:
                logger.info("个人微信发送器不可用")
            
            # 尝试初始化企业微信
            if 'wxwork' in wechat_factory.get_available_senders():
                self.wxwork_sender = wechat_factory.create_sender('wxwork', self.config.get('wxwork', {}))
                if self.wxwork_sender and self.wxwork_sender.initialize():
                    logger.info("企业微信发送器初始化成功")
                else:
                    logger.warning("企业微信发送器初始化失败")
                    self.wxwork_sender = None
            else:
                logger.info("企业微信发送器不可用")
                
        except Exception as e:
            logger.error(f"初始化发送器失败: {e}")
    
    async def _initialize_openclaw(self):
        """初始化 OpenClaw 客户端"""
        try:
            openclaw_config = self.config.get('openclaw', {})
            
            self.openclaw = get_openclaw_client(
                gateway_url=openclaw_config.get('gateway_url', 'ws://127.0.0.1:3100'),
                agent_id=openclaw_config.get('agent_id', 'wxbot-agent')
            )
            
            if await self.openclaw.connect():
                logger.info("OpenClaw 客户端连接成功")
            else:
                logger.warning("OpenClaw 客户端连接失败")
                
        except Exception as e:
            logger.error(f"初始化 OpenClaw 客户端失败: {e}")
    
    def _register_default_commands(self):
        """注册默认命令处理器"""
        
        @self.command('status')
        async def cmd_status(args: Dict) -> Dict:
            """获取服务状态"""
            return {
                'success': True,
                'running': self.running,
                'wechat_available': self.wechat_sender is not None,
                'wxwork_available': self.wxwork_sender is not None,
                'openclaw_connected': self.openclaw.connected if self.openclaw else False,
                'stats': self.stats
            }
        
        @self.command('send')
        async def cmd_send(args: Dict) -> Dict:
            """发送消息命令"""
            chat_id = args.get('chat_id')
            message = args.get('message')
            chat_type = args.get('chat_type', 'private')
            
            if not chat_id or not message:
                return {'success': False, 'error': 'Missing chat_id or message'}
            
            result = await self.send_message(chat_id, message, chat_type)
            return {'success': result}
        
        @self.command('help')
        async def cmd_help(args: Dict) -> Dict:
            """帮助命令"""
            return {
                'success': True,
                'commands': {
                    'status': '获取服务状态',
                    'send': '发送消息 (chat_id, message, chat_type)',
                    'help': '显示帮助信息'
                }
            }
    
    def command(self, name: str):
        """
        命令装饰器
        
        Args:
            name: 命令名称
        """
        def decorator(func):
            self.command_handlers[name] = func
            if self.openclaw:
                self.openclaw.register_command_handler(name, func)
            logger.info(f"注册命令: {name}")
            return func
        return decorator
    
    async def on_message_received(self, message: WeChatMessage):
        """
        消息接收回调
        
        Args:
            message: 微信消息
        """
        try:
            self.stats['messages_received'] += 1
            
            logger.info(f"收到消息: [{message.chat_name}] {message.sender_name}: {message.content[:50]}...")
            
            # 判断是否需要 AI 处理
            should_process = self._should_process_message(message)
            
            if should_process and self.openclaw:
                # 发送到 OpenClaw 进行 AI 处理
                response = await self.openclaw.send_wechat_message(message)
                
                # 如果需要回复，发送回复
                if response.should_reply and response.content:
                    await self.send_message(
                        message.chat_id, 
                        response.content,
                        message.chat_type.value
                    )
                    
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.stats['errors'] += 1
    
    def _should_process_message(self, message: WeChatMessage) -> bool:
        """
        判断是否需要处理消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否需要处理
        """
        # 配置获取
        message_config = self.config.get('openclaw', {}).get('message', {})
        
        if message.chat_type == ChatType.PRIVATE:
            # 私聊消息
            return message_config.get('private_chat', {}).get('enabled', True)
        
        elif message.chat_type == ChatType.GROUP:
            # 群聊消息
            group_config = message_config.get('group_chat', {})
            
            if not group_config.get('enabled', True):
                return False
            
            # 检查是否需要 @ 才触发
            if group_config.get('mention_only', True):
                return message.is_mentioned
            
            # 检查前缀
            prefix = group_config.get('prefix', '')
            if prefix:
                return message.content.startswith(prefix)
            
            return True
        
        return False
    
    async def send_message(self, chat_id: str, message: str, chat_type: str = 'private') -> bool:
        """
        发送消息到微信
        
        Args:
            chat_id: 聊天 ID
            message: 消息内容
            chat_type: 聊天类型
            
        Returns:
            bool: 是否发送成功
        """
        try:
            # 格式化消息
            formatted_message = self._format_message(message)
            
            # 选择发送器
            sender = self._select_sender()
            if not sender:
                logger.error("没有可用的微信发送器")
                return False
            
            # 发送消息
            success = sender.send_message(formatted_message, chat_id)
            
            if success:
                self.stats['messages_sent'] += 1
                logger.info(f"消息发送成功: {chat_id}")
            else:
                logger.warning(f"消息发送失败: {chat_id}")
                self.stats['errors'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            self.stats['errors'] += 1
            return False
    
    def _select_sender(self):
        """选择发送器"""
        # 优先使用个人微信
        if self.wechat_sender:
            return self.wechat_sender
        
        # 回退到企业微信
        if self.wxwork_sender:
            return self.wxwork_sender
        
        return None
    
    def _format_message(self, message: str) -> str:
        """
        格式化消息
        
        Args:
            message: 原始消息
            
        Returns:
            str: 格式化后的消息
        """
        # 添加时间戳（可选）
        if self.config.get('add_timestamp', True):
            timestamp = datetime.now().strftime('%m月%d日 %H:%M')
            return f"{message}\n\n_发送于 {timestamp}_"
        
        return message
    
    async def start(self):
        """
        启动桥接服务
        """
        if self.running:
            logger.warning("服务已在运行")
            return
        
        logger.info("启动 OpenClaw 微信桥接服务...")
        
        # 初始化
        if not await self.initialize():
            raise RuntimeError("初始化失败")
        
        self.running = True
        
        # 启动 OpenClaw 监听
        if self.openclaw:
            asyncio.create_task(self.openclaw.listen())
        
        logger.info("桥接服务已启动")
    
    async def stop(self):
        """
        停止桥接服务
        """
        logger.info("停止桥接服务...")
        
        self.running = False
        
        # 断开 OpenClaw
        if self.openclaw:
            await self.openclaw.disconnect()
        
        # 清理发送器
        if self.wechat_sender:
            self.wechat_sender.cleanup()
        
        if self.wxwork_sender:
            self.wxwork_sender.cleanup()
        
        logger.info("桥接服务已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        Returns:
            Dict: 状态信息
        """
        return {
            'running': self.running,
            'wechat_available': self.wechat_sender is not None,
            'wxwork_available': self.wxwork_sender is not None,
            'openclaw_connected': self.openclaw.connected if self.openclaw else False,
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }


# 单例
_bridge_instance: Optional[BridgeService] = None


def get_bridge_service(config: Dict = None) -> BridgeService:
    """获取桥接服务单例"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = BridgeService(config)
    return _bridge_instance


if __name__ == "__main__":
    # 测试代码
    import sys
    
    async def test_bridge():
        bridge = BridgeService({
            'openclaw': {
                'gateway_url': 'ws://127.0.0.1:3100',
                'agent_id': 'wxbot-agent'
            }
        })
        
        await bridge.start()
        
        # 测试发送消息
        test_message = WeChatMessage(
            message_id='test_001',
            sender_id='sender_001',
            sender_name='测试用户',
            chat_id='chat_001',
            chat_name='测试群',
            chat_type=ChatType.GROUP,
            content='@机器人 你好',
            is_mentioned=True
        )
        
        await bridge.on_message_received(test_message)
        
        # 等待一下
        await asyncio.sleep(2)
        
        await bridge.stop()
        
        print(f"服务状态: {bridge.get_status()}")
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_bridge())