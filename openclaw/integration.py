# -*- coding: utf-8 -*-
"""
OpenClaw 集成接口
版本: v1.0.0

功能:
- MCP工具定义 - 定义微信控制工具
- 消息转发 - 将微信消息转发给OpenClaw
- 命令执行 - 执行OpenClaw返回的命令
- 状态同步 - 同步微信状态到OpenClaw
"""

import asyncio
import json
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ==================== 工具定义 ====================

class WeChatToolType(Enum):
    """微信工具类型"""
    # 消息类
    SEND_MESSAGE = "wechat.send_message"
    SEND_IMAGE = "wechat.send_image"
    SEND_FILE = "wechat.send_file"
    SEND_AT = "wechat.send_at"
    
    # 好友管理类
    ADD_FRIEND = "wechat.add_friend"
    DELETE_FRIEND = "wechat.delete_friend"
    GET_FRIEND_INFO = "wechat.get_friend_info"
    SEARCH_FRIEND = "wechat.search_friend"
    
    # 群管理类
    CREATE_GROUP = "wechat.create_group"
    INVITE_TO_GROUP = "wechat.invite_to_group"
    KICK_FROM_GROUP = "wechat.kick_from_group"
    CHANGE_GROUP_NAME = "wechat.change_group_name"
    SET_GROUP_NOTICE = "wechat.set_group_notice"
    PIN_GROUP = "wechat.pin_group"
    
    # 朋友圈类
    PUBLISH_MOMENTS = "wechat.publish_moments"
    GET_MOMENTS = "wechat.get_moments"
    LIKE_MOMENTS = "wechat.like_moments"
    COMMENT_MOMENTS = "wechat.comment_moments"
    
    # 查询类
    GET_CONTACTS = "wechat.get_contacts"
    GET_GROUPS = "wechat.get_groups"
    GET_CHAT_HISTORY = "wechat.get_chat_history"
    GET_MY_INFO = "wechat.get_my_info"
    
    # 设置类
    SET_REMARK = "wechat.set_remark"
    SET_MUTE = "wechat.set_mute"
    SET_PIN = "wechat.set_pin"


@dataclass
class WeChatTool:
    """微信工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict] = field(default_factory=list)
    
    @classmethod
    def send_message(cls) -> 'WeChatTool':
        """发送消息工具"""
        return cls(
            name=WeChatToolType.SEND_MESSAGE.value,
            description="发送文本消息给指定好友或群聊",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "好友或群聊名称"
                    },
                    "message": {
                        "type": "string",
                        "description": "消息内容"
                    },
                    "at_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "@成员列表，仅群聊有效"
                    },
                    "at_all": {
                        "type": "boolean",
                        "description": "@所有人"
                    }
                },
                "required": ["target", "message"]
            },
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message_id": {"type": "string"}
                }
            },
            examples=[
                {
                    "target": "张三",
                    "message": "你好",
                    "description": "发送消息给张三"
                },
                {
                    "target": "测试群",
                    "message": "大家好",
                    "at_all": True,
                    "description": "在群聊中@所有人"
                }
            ]
        )
    
    @classmethod
    def send_image(cls) -> 'WeChatTool':
        """发送图片工具"""
        return cls(
            name=WeChatToolType.SEND_IMAGE.value,
            description="发送图片给指定好友或群聊",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "好友或群聊名称"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "图片路径或URL"
                    }
                },
                "required": ["target", "image_path"]
            }
        )
    
    @classmethod
    def add_friend(cls) -> 'WeChatTool':
        """添加好友工具"""
        return cls(
            name=WeChatToolType.ADD_FRIEND.value,
            description="通过微信号添加好友",
            parameters={
                "type": "object",
                "properties": {
                    "wechat_id": {
                        "type": "string",
                        "description": "微信号"
                    },
                    "verify_message": {
                        "type": "string",
                        "description": "验证消息"
                    }
                },
                "required": ["wechat_id"]
            }
        )
    
    @classmethod
    def get_contacts(cls) -> 'WeChatTool':
        """获取联系人工具"""
        return cls(
            name=WeChatToolType.GET_CONTACTS.value,
            description="获取所有联系人列表",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "偏移量"
                    }
                }
            }
        )
    
    @classmethod
    def get_groups(cls) -> 'WeChatTool':
        """获取群列表工具"""
        return cls(
            name=WeChatToolType.GET_GROUPS.value,
            description="获取所有群聊列表",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制"
                    }
                }
            }
        )


# ==================== MCP 客户端 ====================

class MCPClient:
    """OpenClaw MCP 客户端
    
    负责与 OpenClaw MCP Server 通信
    """
    
    def __init__(self, server_url: str = "http://localhost:8080"):
        """
        初始化 MCP 客户端
        
        Args:
            server_url: MCP Server 地址
        """
        self.server_url = server_url
        self.session_id = None
        self._connected = False
        self._tools: List[WeChatTool] = []
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        self._tools = [
            WeChatTool.send_message(),
            WeChatTool.send_image(),
            WeChatTool.add_friend(),
            WeChatTool.get_contacts(),
            WeChatTool.get_groups(),
        ]
    
    async def connect(self) -> bool:
        """
        连接到 MCP Server
        
        Returns:
            bool: 连接是否成功
        """
        # TODO: 实现实际的 MCP 连接
        # 这里模拟连接
        self._connected = True
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"已连接到 OpenClaw MCP Server: {self.server_url}")
        return True
    
    async def disconnect(self):
        """断开连接"""
        self._connected = False
        self.session_id = None
        logger.info("已断开 OpenClaw MCP Server 连接")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    def get_tools(self) -> List[WeChatTool]:
        """获取可用工具列表"""
        return self._tools
    
    def register_tool(self, tool: WeChatTool):
        """注册自定义工具"""
        self._tools.append(tool)
    
    async def call_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            Dict: 调用结果
        """
        if not self._connected:
            return {
                "success": False,
                "error": "未连接到 MCP Server"
            }
        
        # TODO: 实现实际的工具调用
        # 这里模拟调用
        logger.info(f"调用工具: {tool_name}, 参数: {parameters}")
        
        return {
            "success": True,
            "result": {
                "tool": tool_name,
                "executed_at": datetime.now().isoformat()
            }
        }
    
    async def send_message(
        self, 
        target: str, 
        message: str,
        at_list: List[str] = None,
        at_all: bool = False
    ) -> Dict[str, Any]:
        """发送消息"""
        return await self.call_tool(
            WeChatToolType.SEND_MESSAGE.value,
            {
                "target": target,
                "message": message,
                "at_list": at_list or [],
                "at_all": at_all
            }
        )
    
    async def get_contacts(self, limit: int = 100) -> Dict[str, Any]:
        """获取联系人"""
        return await self.call_tool(
            WeChatToolType.GET_CONTACTS.value,
            {"limit": limit}
        )
    
    async def get_groups(self, limit: int = 100) -> Dict[str, Any]:
        """获取群列表"""
        return await self.call_tool(
            WeChatToolType.GET_GROUPS.value,
            {"limit": limit}
        )


# ==================== 消息转发器 ====================

class MessageForwarder:
    """消息转发器
    
    将微信消息转发到 OpenClaw
    """
    
    def __init__(self, mcp_client: MCPClient):
        """
        初始化转发器
        
        Args:
            mcp_client: MCP 客户端
        """
        self.mcp_client = mcp_client
        self._forward_rules: List[Dict] = []
        self._default_enabled = True
        self._on_response_callbacks: List[Callable] = []
        
        # 默认转发规则
        self._add_default_rules()
    
    def _add_default_rules(self):
        """添加默认规则"""
        # @我的消息
        self.add_rule({
            "name": "at_me",
            "enabled": True,
            "condition": {"is_mentioned": True},
            "priority": 100
        })
        
        # 私聊消息
        self.add_rule({
            "name": "private_chat",
            "enabled": True,
            "condition": {"chat_type": "private"},
            "priority": 50
        })
        
        # 群聊消息
        self.add_rule({
            "name": "group_chat",
            "enabled": False,
            "condition": {"chat_type": "group"},
            "priority": 30
        })
    
    def add_rule(self, rule: Dict):
        """添加转发规则"""
        self._forward_rules.append(rule)
        self._forward_rules.sort(key=lambda x: x.get('priority', 0), reverse=True)
    
    def remove_rule(self, name: str):
        """移除转发规则"""
        self._forward_rules = [r for r in self._forward_rules if r.get('name') != name]
    
    def set_default_enabled(self, enabled: bool):
        """设置默认转发开关"""
        self._default_enabled = enabled
    
    def on_response(self, callback: Callable):
        """设置响应回调"""
        self._on_response_callbacks.append(callback)
    
    async def forward(self, message_data: Dict) -> Optional[Dict]:
        """
        转发消息
        
        Args:
            message_data: 消息数据
            
        Returns:
            Optional[Dict]: OpenClaw 响应
        """
        if not self.mcp_client.is_connected():
            logger.warning("MCP 未连接，无法转发消息")
            return None
        
        # 检查是否匹配转发规则
        if not self._should_forward(message_data):
            return None
        
        try:
            # 转发到 OpenClaw
            response = await self.mcp_client.call_tool(
                "openclaw.handle_message",
                {
                    "message": message_data,
                    "session_id": self.mcp_client.session_id
                }
            )
            
            # 处理响应
            if response.get('success') and response.get('result'):
                await self._handle_response(response['result'], message_data)
            
            return response
            
        except Exception as e:
            logger.error(f"转发消息失败: {e}")
            return None
    
    def _should_forward(self, message_data: Dict) -> bool:
        """检查是否应该转发"""
        # 检查规则
        for rule in self._forward_rules:
            if not rule.get('enabled', True):
                continue
            
            condition = rule.get('condition', {})
            
            # 检查所有条件
            match = True
            for key, value in condition.items():
                if message_data.get(key) != value:
                    match = False
                    break
            
            if match:
                return True
        
        # 默认规则
        return self._default_enabled
    
    async def _handle_response(self, response: Dict, original_message: Dict):
        """处理响应"""
        # 提取回复内容
        reply = response.get('reply')
        actions = response.get('actions', [])
        
        # 执行动作
        for action in actions:
            await self._execute_action(action, original_message)
        
        # 触发回调
        for callback in self._on_response_callbacks:
            try:
                callback(response, original_message)
            except Exception as e:
                logger.error(f"响应回调错误: {e}")
    
    async def _execute_action(self, action: Dict, context: Dict):
        """执行动作"""
        action_type = action.get('type')
        params = action.get('params', {})
        
        if action_type == "send_message":
            await self.mcp_client.send_message(
                target=params.get('target'),
                message=params.get('message')
            )
        elif action_type == "send_at":
            await self.mcp_client.send_message(
                target=params.get('target'),
                message=params.get('message'),
                at_list=params.get('at_list', []),
                at_all=params.get('at_all', False)
            )


# ==================== 命令执行器 ====================

class CommandExecutor:
    """命令执行器
    
    执行 OpenClaw 返回的命令
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self._command_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认命令处理器"""
        self._command_handlers = {
            "send_message": self._handle_send_message,
            "send_image": self._handle_send_image,
            "send_file": self._handle_send_file,
            "add_friend": self._handle_add_friend,
            "create_group": self._handle_create_group,
            "invite_member": self._handle_invite_member,
            "kick_member": self._handle_kick_member,
            "set_remark": self._handle_set_remark,
            "set_mute": self._handle_set_mute,
            "set_pin": self._handle_set_pin,
        }
    
    def register_handler(self, command: str, handler: Callable):
        """注册命令处理器"""
        self._command_handlers[command] = handler
    
    async def execute(self, commands: List[Dict]) -> List[Dict]:
        """
        执行命令列表
        
        Args:
            commands: 命令列表
            
        Returns:
            List[Dict]: 执行结果列表
        """
        results = []
        
        for cmd in commands:
            result = await self._execute_single(cmd)
            results.append(result)
        
        return results
    
    async def _execute_single(self, command: Dict) -> Dict:
        """执行单个命令"""
        cmd_type = command.get('type')
        params = command.get('params', {})
        
        handler = self._command_handlers.get(cmd_type)
        
        if handler:
            try:
                result = await handler(params)
                return {
                    "type": cmd_type,
                    "success": True,
                    "result": result
                }
            except Exception as e:
                logger.error(f"执行命令失败: {cmd_type}, 错误: {e}")
                return {
                    "type": cmd_type,
                    "success": False,
                    "error": str(e)
                }
        else:
            return {
                "type": cmd_type,
                "success": False,
                "error": f"未知命令: {cmd_type}"
            }
    
    async def _handle_send_message(self, params: Dict) -> Any:
        """处理发送消息"""
        return await self.mcp_client.send_message(
            target=params.get('target'),
            message=params.get('message')
        )
    
    async def _handle_send_image(self, params: Dict) -> Any:
        """处理发送图片"""
        return await self.mcp_client.call_tool(
            WeChatToolType.SEND_IMAGE.value,
            params
        )
    
    async def _handle_send_file(self, params: Dict) -> Any:
        """处理发送文件"""
        return await self.mcp_client.call_tool(
            WeChatToolType.SEND_FILE.value,
            params
        )
    
    async def _handle_add_friend(self, params: Dict) -> Any:
        """处理添加好友"""
        return await self.mcp_client.call_tool(
            WeChatToolType.ADD_FRIEND.value,
            params
        )
    
    async def _handle_create_group(self, params: Dict) -> Any:
        """处理创建群聊"""
        return await self.mcp_client.call_tool(
            WeChatToolType.CREATE_GROUP.value,
            params
        )
    
    async def _handle_invite_member(self, params: Dict) -> Any:
        """处理邀请成员"""
        return await self.mcp_client.call_tool(
            WeChatToolType.INVITE_TO_GROUP.value,
            params
        )
    
    async def _handle_kick_member(self, params: Dict) -> Any:
        """处理踢出成员"""
        return await self.mcp_client.call_tool(
            WeChatToolType.KICK_FROM_GROUP.value,
            params
        )
    
    async def _handle_set_remark(self, params: Dict) -> Any:
        """处理设置备注"""
        return await self.mcp_client.call_tool(
            WeChatToolType.SET_REMARK.value,
            params
        )
    
    async def _handle_set_mute(self, params: Dict) -> Any:
        """处理设置免打扰"""
        return await self.mcp_client.call_tool(
            WeChatToolType.SET_MUTE.value,
            params
        )
    
    async def _handle_set_pin(self, params: Dict) -> Any:
        """处理设置置顶"""
        return await self.mcp_client.call_tool(
            WeChatToolType.SET_PIN.value,
            params
        )


# ==================== 状态同步器 ====================

class StatusSyncer:
    """状态同步器
    
    同步微信状态到 OpenClaw
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self._sync_interval = 60  # 默认60秒
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._last_sync_time: Optional[datetime] = None
    
    def set_interval(self, seconds: int):
        """设置同步间隔"""
        self._sync_interval = seconds
    
    async def start(self):
        """启动同步"""
        if self._running:
            return
        
        self._running = True
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True
        )
        self._sync_thread.start()
        logger.info("状态同步器已启动")
    
    def stop(self):
        """停止同步"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        logger.info("状态同步器已停止")
    
    def _sync_loop(self):
        """同步循环"""
        import time
        while self._running:
            try:
                asyncio.run(self._sync_status())
            except Exception as e:
                logger.error(f"状态同步失败: {e}")
            
            time.sleep(self._sync_interval)
    
    async def _sync_status(self):
        """同步状态"""
        if not self.mcp_client.is_connected():
            return
        
        # 获取微信状态
        status = await self._collect_status()
        
        # 发送到 OpenClaw
        await self.mcp_client.call_tool(
            "openclaw.sync_status",
            {
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        self._last_sync_time = datetime.now()
        logger.debug(f"状态已同步: {self._last_sync_time}")
    
    async def _collect_status(self) -> Dict:
        """收集状态"""
        # TODO: 实际获取微信状态
        return {
            "online": True,
            "contacts_count": 0,
            "groups_count": 0,
            "unread_count": 0,
        }
    
    async def sync_now(self):
        """立即同步"""
        await self._sync_status()


# ==================== OpenClaw 集成主类 ====================

class OpenClawIntegration:
    """OpenClaw 集成主类
    
    统一管理 MCP 客户端、消息转发、命令执行、状态同步
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化集成
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化 MCP 客户端
        self.mcp_client = MCPClient(
            server_url=self.config.get('server_url', 'http://localhost:8080')
        )
        
        # 初始化各个模块
        self.forwarder = MessageForwarder(self.mcp_client)
        self.executor = CommandExecutor(self.mcp_client)
        self.syncer = StatusSyncer(self.mcp_client)
        
        self._running = False
    
    async def start(self):
        """启动集成"""
        if self._running:
            return
        
        # 连接 MCP Server
        connected = await self.mcp_client.connect()
        if not connected:
            raise ConnectionError("无法连接到 OpenClaw MCP Server")
        
        # 启动状态同步
        await self.syncer.start()
        
        self._running = True
        logger.info("OpenClaw 集成已启动")
    
    async def stop(self):
        """停止集成"""
        self._running = False
        
        # 停止状态同步
        self.syncer.stop()
        
        # 断开连接
        await self.mcp_client.disconnect()
        
        logger.info("OpenClaw 集成已停止")
    
    async def forward_message(self, message_data: Dict) -> Optional[Dict]:
        """转发消息"""
        return await self.forwarder.forward(message_data)
    
    async def execute_commands(self, commands: List[Dict]) -> List[Dict]:
        """执行命令"""
        return await self.executor.execute(commands)
    
    async def sync_status(self):
        """立即同步状态"""
        await self.syncer.sync_now()
    
    def get_tools(self) -> List[WeChatTool]:
        """获取可用工具"""
        return self.mcp_client.get_tools()


# ==================== 使用示例 ====================

async def example_basic():
    """基本使用示例"""
    
    # 创建集成
    integration = OpenClawIntegration({
        'server_url': 'http://localhost:8080'
    })
    
    # 启动
    await integration.start()
    
    # 获取工具列表
    tools = integration.get_tools()
    print("可用工具:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # 转发消息示例
    message_data = {
        'message_id': 'msg_001',
        'sender_name': '张三',
        'chat_name': '测试群',
        'chat_type': 'group',
        'content': '@我 你好',
        'is_mentioned': True
    }
    
    response = await integration.forward_message(message_data)
    print(f"转发响应: {response}")
    
    # 执行命令示例
    commands = [
        {
            'type': 'send_message',
            'params': {
                'target': '张三',
                'message': '你好！'
            }
        }
    ]
    
    results = await integration.execute_commands(commands)
    print(f"命令执行结果: {results}")
    
    # 停止
    await integration.stop()


async def example_with_callbacks():
    """带回调示例"""
    
    integration = OpenClawIntegration()
    
    # 设置消息转发回调
    async def on_forward_response(response, original_message):
        print(f"收到响应: {response}")
        print(f"原始消息: {original_message['content']}")
    
    integration.forwarder.on_response(on_forward_response)
    
    # 启动
    await integration.start()
    
    # 运行一段时间
    await asyncio.sleep(60)
    
    # 停止
    await integration.stop()


# ==================== 主入口 ====================

if __name__ == '__main__':
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行示例
    asyncio.run(example_basic())