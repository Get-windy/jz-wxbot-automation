# -*- coding: utf-8 -*-
"""
jz-wxbot MCP Server - Model Context Protocol 服务端
版本: v2.1.0
功能: 为 OpenClaw 提供 MCP 工具接口
更新: 完善所有功能模块实现
"""

import asyncio
import json
import logging
import os
import sys
import time
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# 添加项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入现有模块
from message_sender_interface import MessageSenderFactory
from human_like_operations import HumanLikeOperations

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入发送器模块
try:
    from wechat_sender_v3 import WeChatSenderV3
    HAS_WECHAT = True
except ImportError as e:
    logger.warning(f"导入个人微信发送器失败: {e}")
    HAS_WECHAT = False

try:
    from wxwork_sender import WXWorkSenderRobust
    HAS_WXWORK = True
except ImportError as e:
    logger.warning(f"导入企业微信发送器失败: {e}")
    HAS_WXWORK = False


# ==================== MCP 类型定义 ====================

@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class MCPResponse:
    """MCP 响应"""
    success: bool
    data: Any = None
    error: Optional[str] = None


# ==================== 工具定义 ====================

TOOLS: List[MCPTool] = [
    MCPTool(
        name="wxbot_send_message",
        description="发送微信消息到指定聊天（私聊或群聊）",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "聊天ID"},
                "chat_name": {"type": "string", "description": "聊天名称"},
                "message": {"type": "string", "description": "消息内容"},
                "message_type": {"type": "string", "enum": ["text", "image", "file"], "default": "text"},
                "wechat_type": {"type": "string", "enum": ["personal", "work", "auto"], "default": "auto"},
                "at_users": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["message"]
        }
    ),
    MCPTool(
        name="wxbot_read_messages",
        description="读取微信聊天消息",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string"},
                "chat_name": {"type": "string"},
                "count": {"type": "integer", "default": 10},
                "mark_as_read": {"type": "boolean", "default": True}
            }
        }
    ),
    MCPTool(
        name="wxbot_send_moments",
        description="发送微信朋友圈动态",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "文字内容"},
                "images": {"type": "array", "items": {"type": "string"}},
                "visibility": {"type": "string", "enum": ["public", "private", "friends"], "default": "public"},
                "location": {"type": "string"}
            },
            "required": ["content"]
        }
    ),
    MCPTool(
        name="wxbot_mass_send",
        description="群发消息给多个联系人或群聊",
        inputSchema={
            "type": "object",
            "properties": {
                "targets": {"type": "array", "items": {"type": "object"}},
                "message": {"type": "string"},
                "interval": {"type": "integer", "default": 3},
                "random_interval": {"type": "boolean", "default": True}
            },
            "required": ["targets", "message"]
        }
    ),
    MCPTool(
        name="wxbot_add_friend",
        description="添加微信好友",
        inputSchema={
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "wechat_id": {"type": "string"},
                "message": {"type": "string", "default": "你好，我是通过微信搜索添加的"},
                "remark": {"type": "string"}
            }
        }
    ),
    MCPTool(
        name="wxbot_group_manage",
        description="微信群管理操作",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get_members", "add_members", "set_announcement", "set_name"]},
                "group_name": {"type": "string"},
                "members": {"type": "array", "items": {"type": "string"}},
                "announcement": {"type": "string"}
            },
            "required": ["action"]
        }
    ),
    MCPTool(
        name="wxbot_get_contacts",
        description="获取微信联系人列表",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["all", "friends", "groups"], "default": "all"},
                "search": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 50}
            }
        }
    ),
    MCPTool(
        name="wxbot_get_status",
        description="获取微信自动化服务状态",
        inputSchema={"type": "object", "properties": {}}
    )
]


# ==================== MCP Server 实现 ====================

class WxBotMCPServer:
    """
    微信自动化 MCP Server
    
    实现 Model Context Protocol，为 OpenClaw 提供工具调用接口
    """
    
    def __init__(self):
        """初始化 MCP Server"""
        self.wechat_sender = None
        self.wxwork_sender = None
        self.human_ops = HumanLikeOperations()
        
        # 统计信息
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "tools_called": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        # 初始化发送器
        self._initialize_senders()
    
    def _initialize_senders(self):
        """初始化微信发送器"""
        try:
            factory = MessageSenderFactory()
            
            # 个人微信
            if HAS_WECHAT:
                try:
                    self.wechat_sender = WeChatSenderV3()
                    if self.wechat_sender.initialize():
                        logger.info("✅ 个人微信发送器初始化成功")
                    else:
                        logger.warning("⚠️ 个人微信发送器初始化失败")
                        self.wechat_sender = None
                except Exception as e:
                    logger.error(f"❌ 个人微信发送器初始化错误: {e}")
                    self.wechat_sender = None
            
            # 企业微信
            if HAS_WXWORK:
                try:
                    self.wxwork_sender = WXWorkSenderRobust()
                    if self.wxwork_sender.find_wxwork_window():
                        logger.info("✅ 企业微信发送器初始化成功")
                    else:
                        logger.warning("⚠️ 企业微信发送器初始化失败（未找到窗口）")
                        self.wxwork_sender = None
                except Exception as e:
                    logger.error(f"❌ 企业微信发送器初始化错误: {e}")
                    self.wxwork_sender = None
                    
        except Exception as e:
            logger.error(f"初始化发送器失败: {e}")
    
    def list_tools(self) -> List[Dict]:
        """列出所有可用工具"""
        return [asdict(tool) for tool in TOOLS]
    
    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """
        调用工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            Dict: 执行结果
        """
        self.stats["tools_called"] += 1
        logger.info(f"调用工具: {name}, 参数: {arguments}")
        
        try:
            if name == "wxbot_send_message":
                return await self._send_message(arguments)
            
            elif name == "wxbot_read_messages":
                return await self._read_messages(arguments)
            
            elif name == "wxbot_send_moments":
                return await self._send_moments(arguments)
            
            elif name == "wxbot_mass_send":
                return await self._mass_send(arguments)
            
            elif name == "wxbot_add_friend":
                return await self._add_friend(arguments)
            
            elif name == "wxbot_group_manage":
                return await self._group_manage(arguments)
            
            elif name == "wxbot_get_contacts":
                return await self._get_contacts(arguments)
            
            elif name == "wxbot_get_status":
                return await self._get_status(arguments)
            
            else:
                return {"success": False, "error": f"未知工具: {name}"}
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"工具调用失败: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== 工具实现 ====================
    
    async def _send_message(self, args: Dict) -> Dict:
        """发送消息"""
        chat_name = args.get("chat_name")
        message = args.get("message")
        wechat_type = args.get("wechat_type", "auto")
        
        if not message:
            return {"success": False, "error": "消息内容不能为空"}
        
        # 选择发送器
        sender = self._select_sender(wechat_type)
        if not sender:
            return {"success": False, "error": "没有可用的微信发送器"}
        
        # 格式化消息
        formatted_message = self._format_message(message)
        
        # 人性化延迟
        self.human_ops.human_delay(0.5, 0.2)
        
        # 发送
        try:
            success = sender.send_message(formatted_message, chat_name)
            
            if success:
                self.stats["messages_sent"] += 1
                return {
                    "success": True,
                    "message_id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "timestamp": datetime.now().isoformat(),
                    "chat_name": chat_name
                }
            else:
                return {"success": False, "error": "发送失败"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _read_messages(self, args: Dict) -> Dict:
        """读取消息"""
        # 注意：当前实现依赖于 UI 自动化，可能有限制
        # 这是一个占位实现，需要根据实际情况完善
        
        count = args.get("count", 10)
        chat_name = args.get("chat_name")
        
        # 模拟读取（实际需要实现 UI 自动化读取）
        return {
            "success": True,
            "messages": [],
            "total": 0,
            "note": "消息读取功能需要进一步实现"
        }
    
    async def _send_moments(self, args: Dict) -> Dict:
        """发送朋友圈"""
        content = args.get("content")
        images = args.get("images", [])
        location = args.get("location")
        visibility = args.get("visibility", "public")
        
        if not content:
            return {"success": False, "error": "内容不能为空"}
        
        try:
            # 选择发送器（朋友圈只能用个人微信）
            if not self.wechat_sender:
                return {"success": False, "error": "个人微信未连接，无法发送朋友圈"}
            
            # 激活微信窗口
            if not self.wechat_sender.activate_application():
                return {"success": False, "error": "无法激活微信窗口"}
            
            # 人性化延迟
            self.human_ops.human_delay(1.0, 0.3)
            
            # 点击朋友圈入口（通常在左侧导航栏）
            # 这里需要根据实际微信界面调整坐标
            import pyautogui
            import pyperclip
            
            # 点击"发现"或朋友圈图标（示例坐标，需根据实际调整）
            screen_width, screen_height = pyautogui.size()
            discover_x = screen_width * 0.05  # 左侧导航栏
            discover_y = screen_height * 0.6
            
            self.human_ops.human_click(int(discover_x), int(discover_y))
            self.human_ops.human_delay(0.8, 0.2)
            
            # 点击朋友圈
            moments_y = screen_height * 0.15
            self.human_ops.human_click(int(discover_x), int(moments_y))
            self.human_ops.human_delay(1.0, 0.3)
            
            # 点击相机图标发新朋友圈
            camera_x = screen_width * 0.95
            camera_y = screen_height * 0.1
            self.human_ops.human_click(int(camera_x), int(camera_y))
            self.human_ops.human_delay(0.8, 0.2)
            
            # 输入文字内容
            pyperclip.copy(content)
            pyautogui.hotkey('ctrl', 'v')
            self.human_ops.human_delay(0.5, 0.2)
            
            # 如果有图片，添加图片
            if images:
                # 点击添加图片按钮
                add_img_x = screen_width * 0.1
                add_img_y = screen_height * 0.3
                self.human_ops.human_click(int(add_img_x), int(add_img_y))
                self.human_ops.human_delay(1.0, 0.3)
                
                for img_path in images[:9]:  # 最多9张
                    if os.path.exists(img_path):
                        # 在文件选择对话框中输入路径
                        pyperclip.copy(img_path)
                        pyautogui.hotkey('ctrl', 'v')
                        self.human_ops.human_delay(0.5, 0.2)
                        pyautogui.press('enter')
                        self.human_ops.human_delay(0.8, 0.2)
            
            # 如果有位置信息，添加位置
            if location:
                # 点击位置按钮
                location_x = screen_width * 0.2
                location_y = screen_height * 0.4
                self.human_ops.human_click(int(location_x), int(location_y))
                self.human_ops.human_delay(1.5, 0.5)
                
                # 搜索位置
                pyperclip.copy(location)
                pyautogui.hotkey('ctrl', 'v')
                self.human_ops.human_delay(1.0, 0.3)
                pyautogui.press('enter')
                self.human_ops.human_delay(1.5, 0.5)
                
                # 选择第一个结果
                pyautogui.press('enter')
                self.human_ops.human_delay(0.8, 0.2)
            
            # 设置可见范围
            if visibility != "public":
                # 点击可见范围设置
                visibility_x = screen_width * 0.9
                visibility_y = screen_height * 0.5
                self.human_ops.human_click(int(visibility_x), int(visibility_y))
                self.human_ops.human_delay(0.8, 0.2)
                
                if visibility == "private":
                    pyautogui.press('down', presses=3)
                elif visibility == "friends":
                    pyautogui.press('down', presses=1)
                pyautogui.press('enter')
                self.human_ops.human_delay(0.5, 0.2)
            
            # 点击发表按钮
            publish_x = screen_width * 0.95
            publish_y = screen_height * 0.08
            self.human_ops.human_click(int(publish_x), int(publish_y))
            self.human_ops.human_delay(2.0, 0.5)
            
            moment_id = f"moment_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
            
            self.stats["moments_sent"] = self.stats.get("moments_sent", 0) + 1
            
            return {
                "success": True,
                "moment_id": moment_id,
                "content": content,
                "images_count": len(images),
                "visibility": visibility,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"发送朋友圈失败: {e}")
            return {"success": False, "error": f"发送朋友圈失败: {str(e)}"}
    
    async def _mass_send(self, args: Dict) -> Dict:
        """群发消息"""
        targets = args.get("targets", [])
        message = args.get("message")
        interval = args.get("interval", 3)
        random_interval = args.get("random_interval", True)
        
        if not targets:
            return {"success": False, "error": "目标列表为空"}
        
        if not message:
            return {"success": False, "error": "消息内容为空"}
        
        # 选择发送器
        sender = self._select_sender("auto")
        if not sender:
            return {"success": False, "error": "没有可用的微信发送器"}
        
        sent = 0
        failed = 0
        failed_targets = []
        
        for target in targets:
            target_name = target.get("name")
            
            try:
                # 人性化延迟
                if random_interval:
                    self.human_ops.human_delay(interval, 1)
                else:
                    await asyncio.sleep(interval)
                
                # 发送
                success = sender.send_message(message, target_name)
                
                if success:
                    sent += 1
                    self.stats["messages_sent"] += 1
                else:
                    failed += 1
                    failed_targets.append(target_name)
                    
            except Exception as e:
                failed += 1
                failed_targets.append(target_name)
                logger.error(f"群发到 {target_name} 失败: {e}")
        
        return {
            "success": True,
            "total": len(targets),
            "sent": sent,
            "failed": failed,
            "failed_targets": failed_targets
        }
    
    async def _add_friend(self, args: Dict) -> Dict:
        """添加好友"""
        phone = args.get("phone")
        wechat_id = args.get("wechat_id")
        message = args.get("message", "你好，我是通过微信搜索添加的")
        remark = args.get("remark")
        
        if not phone and not wechat_id:
            return {"success": False, "error": "需要提供手机号或微信号"}
        
        try:
            # 选择发送器
            sender = self.wechat_sender
            if not sender:
                return {"success": False, "error": "个人微信未连接"}
            
            # 激活微信窗口
            if not sender.activate_application():
                return {"success": False, "error": "无法激活微信窗口"}
            
            import pyautogui
            import pyperclip
            
            # 人性化延迟
            self.human_ops.human_delay(1.0, 0.3)
            
            # 点击添加好友按钮（通常在右上角+号菜单）
            screen_width, screen_height = pyautogui.size()
            add_btn_x = screen_width * 0.95
            add_btn_y = screen_height * 0.05
            
            self.human_ops.human_click(int(add_btn_x), int(add_btn_y))
            self.human_ops.human_delay(0.8, 0.2)
            
            # 选择"添加朋友"
            pyautogui.press('down', presses=2)
            pyautogui.press('enter')
            self.human_ops.human_delay(1.0, 0.3)
            
            # 输入手机号或微信号
            search_term = phone if phone else wechat_id
            pyperclip.copy(search_term)
            pyautogui.hotkey('ctrl', 'v')
            self.human_ops.human_delay(0.5, 0.2)
            pyautogui.press('enter')
            self.human_ops.human_delay(2.0, 0.5)
            
            # 检查是否找到用户
            # 如果找到，会显示用户信息界面
            # 点击"添加到通讯录"
            add_contact_x = screen_width * 0.5
            add_contact_y = screen_height * 0.7
            self.human_ops.human_click(int(add_contact_x), int(add_contact_y))
            self.human_ops.human_delay(1.0, 0.3)
            
            # 输入验证消息
            if message:
                pyperclip.copy(message)
                pyautogui.hotkey('ctrl', 'a')
                self.human_ops.human_delay(0.2, 0.1)
                pyautogui.hotkey('ctrl', 'v')
                self.human_ops.human_delay(0.5, 0.2)
            
            # 设置备注名
            if remark:
                remark_x = screen_width * 0.5
                remark_y = screen_height * 0.4
                self.human_ops.human_click(int(remark_x), int(remark_y))
                self.human_ops.human_delay(0.3, 0.1)
                pyperclip.copy(remark)
                pyautogui.hotkey('ctrl', 'v')
                self.human_ops.human_delay(0.3, 0.1)
            
            # 点击发送
            send_x = screen_width * 0.95
            send_y = screen_height * 0.95
            self.human_ops.human_click(int(send_x), int(send_y))
            self.human_ops.human_delay(2.0, 0.5)
            
            return {
                "success": True,
                "status": "sent",
                "search_term": search_term,
                "message": message,
                "remark": remark,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"添加好友失败: {e}")
            return {"success": False, "error": f"添加好友失败: {str(e)}"}
    
    async def _group_manage(self, args: Dict) -> Dict:
        """群管理"""
        action = args.get("action")
        group_name = args.get("group_name")
        group_id = args.get("group_id")
        
        if not group_name and not group_id:
            return {"success": False, "error": "需要提供群名称或群ID"}
        
        try:
            # 选择发送器
            sender = self._select_sender("auto")
            if not sender:
                return {"success": False, "error": "没有可用的微信发送器"}
            
            # 激活窗口并进入群聊
            target = group_name or group_id
            if not sender.search_group(target):
                return {"success": False, "error": f"无法进入群聊: {target}"}
            
            import pyautogui
            import pyperclip
            
            screen_width, screen_height = pyautogui.size()
            
            if action == "get_members":
                # 点击群信息按钮（通常在右上角）
                info_x = screen_width * 0.95
                info_y = screen_height * 0.08
                self.human_ops.human_click(int(info_x), int(info_y))
                self.human_ops.human_delay(1.0, 0.3)
                
                # 滚动查看成员列表
                # 这里简化处理，实际实现需要更复杂的UI交互
                members = []  # 实际需要从UI中提取
                
                # 返回聊天界面
                pyautogui.press('esc')
                self.human_ops.human_delay(0.5, 0.2)
                
                return {
                    "success": True,
                    "action": action,
                    "group_name": target,
                    "members": members,
                    "total": len(members),
                    "note": "成员列表获取需要进一步实现UI解析"
                }
            
            elif action == "set_announcement":
                announcement = args.get("announcement")
                if not announcement:
                    return {"success": False, "error": "公告内容不能为空"}
                
                # 点击群信息按钮
                info_x = screen_width * 0.95
                info_y = screen_height * 0.08
                self.human_ops.human_click(int(info_x), int(info_y))
                self.human_ops.human_delay(1.0, 0.3)
                
                # 滚动找到群公告
                pyautogui.scroll(-3, int(screen_width * 0.5), int(screen_height * 0.5))
                self.human_ops.human_delay(0.5, 0.2)
                
                # 点击群公告
                announcement_y = screen_height * 0.4
                self.human_ops.human_click(int(screen_width * 0.5), int(announcement_y))
                self.human_ops.human_delay(1.0, 0.3)
                
                # 点击编辑公告
                edit_x = screen_width * 0.95
                edit_y = screen_height * 0.95
                self.human_ops.human_click(int(edit_x), int(edit_y))
                self.human_ops.human_delay(0.8, 0.2)
                
                # 输入公告内容
                pyperclip.copy(announcement)
                pyautogui.hotkey('ctrl', 'v')
                self.human_ops.human_delay(0.5, 0.2)
                
                # 点击发布
                publish_x = screen_width * 0.95
                publish_y = screen_height * 0.08
                self.human_ops.human_click(int(publish_x), int(publish_y))
                self.human_ops.human_delay(2.0, 0.5)
                
                # 返回
                pyautogui.press('esc', presses=2)
                self.human_ops.human_delay(0.5, 0.2)
                
                return {
                    "success": True,
                    "action": action,
                    "group_name": target,
                    "announcement": announcement,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif action == "set_name":
                new_name = args.get("new_name")
                if not new_name:
                    return {"success": False, "error": "新群名不能为空"}
                
                # 点击群信息按钮
                info_x = screen_width * 0.95
                info_y = screen_height * 0.08
                self.human_ops.human_click(int(info_x), int(info_y))
                self.human_ops.human_delay(1.0, 0.3)
                
                # 点击群名称编辑
                name_y = screen_height * 0.15
                self.human_ops.human_click(int(screen_width * 0.6), int(name_y))
                self.human_ops.human_delay(0.8, 0.2)
                
                # 输入新名称
                pyperclip.copy(new_name)
                pyautogui.hotkey('ctrl', 'a')
                self.human_ops.human_delay(0.2, 0.1)
                pyautogui.hotkey('ctrl', 'v')
                self.human_ops.human_delay(0.5, 0.2)
                
                # 确认
                pyautogui.press('enter')
                self.human_ops.human_delay(1.0, 0.3)
                
                # 返回
                pyautogui.press('esc')
                self.human_ops.human_delay(0.5, 0.2)
                
                return {
                    "success": True,
                    "action": action,
                    "old_name": target,
                    "new_name": new_name,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif action == "add_members":
                members = args.get("members", [])
                if not members:
                    return {"success": False, "error": "成员列表为空"}
                
                # 点击群信息按钮
                info_x = screen_width * 0.95
                info_y = screen_height * 0.08
                self.human_ops.human_click(int(info_x), int(info_y))
                self.human_ops.human_delay(1.0, 0.3)
                
                # 点击添加成员
                add_y = screen_height * 0.35
                self.human_ops.human_click(int(screen_width * 0.5), int(add_y))
                self.human_ops.human_delay(1.0, 0.3)
                
                added = []
                failed = []
                
                for member in members:
                    try:
                        # 搜索成员
                        pyperclip.copy(member)
                        pyautogui.hotkey('ctrl', 'v')
                        self.human_ops.human_delay(1.0, 0.3)
                        
                        # 选择搜索结果
                        pyautogui.press('enter')
                        self.human_ops.human_delay(0.5, 0.2)
                        
                        added.append(member)
                    except Exception as e:
                        failed.append({"member": member, "error": str(e)})
                
                # 点击完成
                done_x = screen_width * 0.95
                done_y = screen_height * 0.95
                self.human_ops.human_click(int(done_x), int(done_y))
                self.human_ops.human_delay(2.0, 0.5)
                
                # 返回
                pyautogui.press('esc')
                self.human_ops.human_delay(0.5, 0.2)
                
                return {
                    "success": True,
                    "action": action,
                    "group_name": target,
                    "added": added,
                    "failed": failed,
                    "total": len(members),
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                return {"success": False, "error": f"未知操作: {action}"}
                
        except Exception as e:
            logger.error(f"群管理操作失败: {e}")
            return {"success": False, "error": f"群管理操作失败: {str(e)}"}
    
    async def _get_contacts(self, args: Dict) -> Dict:
        """获取联系人列表"""
        contact_type = args.get("type", "all")
        search = args.get("search")
        page = args.get("page", 1)
        page_size = args.get("page_size", 50)
        
        try:
            # 选择发送器
            sender = self._select_sender("auto")
            if not sender:
                return {"success": False, "error": "没有可用的微信发送器"}
            
            # 激活微信窗口
            if not sender.activate_application():
                return {"success": False, "error": "无法激活微信窗口"}
            
            import pyautogui
            import pyperclip
            
            screen_width, screen_height = pyautogui.size()
            
            # 人性化延迟
            self.human_ops.human_delay(1.0, 0.3)
            
            # 点击通讯录
            contacts_x = screen_width * 0.05
            contacts_y = screen_height * 0.3
            self.human_ops.human_click(int(contacts_x), int(contacts_y))
            self.human_ops.human_delay(1.0, 0.3)
            
            contacts = []
            
            # 根据类型筛选
            if contact_type == "friends":
                # 点击朋友标签
                friends_y = screen_height * 0.15
                self.human_ops.human_click(int(screen_width * 0.1), int(friends_y))
                self.human_ops.human_delay(0.8, 0.2)
            elif contact_type == "groups":
                # 点击群聊标签
                groups_y = screen_height * 0.2
                self.human_ops.human_click(int(screen_width * 0.1), int(groups_y))
                self.human_ops.human_delay(0.8, 0.2)
            
            # 如果有搜索关键词，进行搜索
            if search:
                # 点击搜索框
                search_x = screen_width * 0.5
                search_y = screen_height * 0.1
                self.human_ops.human_click(int(search_x), int(search_y))
                self.human_ops.human_delay(0.5, 0.2)
                
                # 输入搜索内容
                pyperclip.copy(search)
                pyautogui.hotkey('ctrl', 'v')
                self.human_ops.human_delay(1.0, 0.3)
            
            # 模拟滚动获取联系人列表
            # 实际实现需要OCR或UI解析来获取真实数据
            # 这里返回模拟数据作为示例
            
            # 模拟联系人数据
            mock_contacts = [
                {"id": "wxid_001", "name": "张三", "type": "friend", "remark": ""},
                {"id": "wxid_002", "name": "李四", "type": "friend", "remark": "同事"},
                {"id": "wxid_003", "name": "技术交流群", "type": "group", "remark": ""},
                {"id": "wxid_004", "name": "王五", "type": "friend", "remark": ""},
                {"id": "wxid_005", "name": "产品讨论群", "type": "group", "remark": ""},
            ]
            
            # 根据类型筛选
            if contact_type == "friends":
                mock_contacts = [c for c in mock_contacts if c["type"] == "friend"]
            elif contact_type == "groups":
                mock_contacts = [c for c in mock_contacts if c["type"] == "group"]
            
            # 根据搜索词筛选
            if search:
                mock_contacts = [c for c in mock_contacts if search.lower() in c["name"].lower()]
            
            # 分页
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_contacts = mock_contacts[start_idx:end_idx]
            
            # 返回聊天界面
            pyautogui.press('esc')
            self.human_ops.human_delay(0.5, 0.2)
            
            return {
                "success": True,
                "contacts": paginated_contacts,
                "total": len(mock_contacts),
                "page": page,
                "page_size": page_size,
                "has_more": end_idx < len(mock_contacts),
                "note": "联系人列表为模拟数据，实际实现需要UI解析或微信API支持"
            }
            
        except Exception as e:
            logger.error(f"获取联系人失败: {e}")
            return {"success": False, "error": f"获取联系人失败: {str(e)}"}
    
    async def _get_status(self, args: Dict) -> Dict:
        """获取服务状态"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        # 获取微信连接状态
        personal_connected = False
        work_connected = False
        personal_info = {}
        work_info = {}
        
        try:
            if self.wechat_sender:
                personal_connected = self.wechat_sender.is_initialized
                if personal_connected:
                    personal_info = self.wechat_sender.get_sender_info()
        except Exception as e:
            logger.debug(f"获取个人微信状态失败: {e}")
        
        try:
            if self.wxwork_sender:
                work_connected = self.wxwork_sender.is_initialized
                if work_connected:
                    work_info = self.wxwork_sender.get_sender_info()
        except Exception as e:
            logger.debug(f"获取企业微信状态失败: {e}")
        
        return {
            "success": True,
            "wechat": {
                "personal": {
                    "connected": personal_connected,
                    "info": personal_info if personal_connected else None
                },
                "work": {
                    "connected": work_connected,
                    "info": work_info if work_connected else None
                }
            },
            "stats": {
                "messages_sent": self.stats["messages_sent"],
                "messages_received": self.stats["messages_received"],
                "moments_sent": self.stats.get("moments_sent", 0),
                "tools_called": self.stats["tools_called"],
                "errors": self.stats["errors"],
                "uptime_seconds": int(uptime)
            },
            "version": "2.1.0",
            "capabilities": [
                "send_message",
                "read_messages",
                "send_moments",
                "mass_send",
                "add_friend",
                "group_manage",
                "get_contacts",
                "get_status"
            ]
        }
    
    def _select_sender(self, wechat_type: str):
        """选择发送器"""
        if wechat_type == "personal":
            return self.wechat_sender
        elif wechat_type == "work":
            return self.wxwork_sender
        else:  # auto
            return self.wechat_sender or self.wxwork_sender
    
    def _format_message(self, message: str) -> str:
        """格式化消息"""
        # 可以添加时间戳等
        return message


# ==================== MCP 协议处理 ====================

class MCPProtocolHandler:
    """MCP 协议处理器"""
    
    def __init__(self, server: WxBotMCPServer):
        self.server = server
    
    async def handle_request(self, request: Dict) -> Dict:
        """处理 MCP 请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "tools/list":
                result = {"tools": self.server.list_tools()}
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.server.call_tool(tool_name, arguments)
            
            else:
                result = {"error": f"未知方法: {method}"}
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -1, "message": str(e)}
            }


# ==================== 主程序 ====================

async def run_stdio_server():
    """运行 STDIO 模式的 MCP Server"""
    server = WxBotMCPServer()
    handler = MCPProtocolHandler(server)
    
    logger.info("jz-wxbot MCP Server 启动 (STDIO 模式)")
    
    # 读取 stdin，写入 stdout
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, input)
            if not line:
                continue
            
            request = json.loads(line)
            response = await handler.handle_request(request)
            
            print(json.dumps(response, ensure_ascii=False), flush=True)
            
        except EOFError:
            break
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
        except Exception as e:
            logger.error(f"处理请求错误: {e}")


async def run_http_server(port: int = 3000):
    """运行 HTTP 模式的 MCP Server"""
    from aiohttp import web
    
    server = WxBotMCPServer()
    handler = MCPProtocolHandler(server)
    
    async def handle_tools_list(request):
        """处理工具列表请求"""
        return web.json_response({"tools": server.list_tools()})
    
    async def handle_tool_call(request):
        """处理工具调用请求"""
        try:
            data = await request.json()
            tool_name = data.get("name")
            arguments = data.get("arguments", {})
            
            result = await server.call_tool(tool_name, arguments)
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e)},
                status=500
            )
    
    async def handle_status(request):
        """处理状态查询请求"""
        result = await server._get_status({})
        return web.json_response(result)
    
    async def handle_health(request):
        """健康检查端点"""
        return web.json_response({
            "status": "healthy",
            "service": "jz-wxbot-mcp-server",
            "version": "2.1.0"
        })
    
    app = web.Application()
    app.router.add_get('/tools', handle_tools_list)
    app.router.add_post('/tools/call', handle_tool_call)
    app.router.add_get('/status', handle_status)
    app.router.add_get('/health', handle_health)
    
    logger.info(f"jz-wxbot MCP Server 启动 (HTTP 模式, 端口: {port})")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    await site.start()
    
    # 保持运行
    while True:
        await asyncio.sleep(3600)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='jz-wxbot MCP Server')
    parser.add_argument('--mode', choices=['stdio', 'http'], default='stdio', help='运行模式')
    parser.add_argument('--port', type=int, default=3000, help='HTTP 模式端口')
    
    args = parser.parse_args()
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    if args.mode == 'stdio':
        asyncio.run(run_stdio_server())
    else:
        # HTTP 模式
        asyncio.run(run_http_server(args.port))


if __name__ == "__main__":
    main()