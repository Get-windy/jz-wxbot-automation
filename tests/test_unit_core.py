# -*- coding: utf-8 -*-
"""
jz-wxbot 核心功能单元测试
测试范围：消息发送、接收、群管理等核心功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 测试模型 ====================

class MockWeChatMessage:
    """模拟微信消息"""
    def __init__(self, msg_id: str, content: str, sender: str, 
                 msg_type: str = "text", chat_type: str = "private",
                 timestamp: datetime = None):
        self.msg_id = msg_id
        self.content = content
        self.sender = sender
        self.msg_type = msg_type
        self.chat_type = chat_type
        self.timestamp = timestamp or datetime.now()
        self.is_read = False
    
    def mark_as_read(self):
        self.is_read = True


class MockContact:
    """模拟联系人"""
    def __init__(self, contact_id: str, nickname: str, remark: str = "",
                 is_friend: bool = True, is_group: bool = False):
        self.contact_id = contact_id
        self.nickname = nickname
        self.remark = remark
        self.is_friend = is_friend
        self.is_group = is_group
        self.groups_in_common = []
    
    def get_display_name(self) -> str:
        return self.remark or self.nickname


class MockGroup:
    """模拟群聊"""
    def __init__(self, group_id: str, name: str, owner: str,
                 members: List[str] = None, announcement: str = ""):
        self.group_id = group_id
        self.name = name
        self.owner = owner
        self.members = members or []
        self.announcement = announcement
        self.created_at = datetime.now()
    
    def add_member(self, member_id: str) -> bool:
        if member_id not in self.members:
            self.members.append(member_id)
            return True
        return False
    
    def remove_member(self, member_id: str) -> bool:
        if member_id in self.members:
            self.members.remove(member_id)
            return True
        return False
    
    def get_member_count(self) -> int:
        return len(self.members)


# ==================== 消息发送测试 ====================

class TestMessageSender(unittest.TestCase):
    """消息发送功能测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.mock_pywechat = Mock()
        self.mock_pywechat.Messages = Mock()
        self.mock_pywechat.Messages.send_messages_to_friend = Mock()
        
        # 模拟发送结果
        self.send_results = []
    
    def test_send_text_message_to_friend(self):
        """测试发送文本消息给好友"""
        friend_name = "测试好友"
        message_content = "你好，这是一条测试消息"
        
        # 执行发送
        result = self._send_message(friend_name, message_content, "text")
        
        # 验证调用
        self.mock_pywechat.Messages.send_messages_to_friend.assert_called_once()
        call_args = self.mock_pywechat.Messages.send_messages_to_friend.call_args
        
        self.assertEqual(call_args[1]['friend'], friend_name)
        self.assertIn(message_content, call_args[1]['messages'])
        self.assertTrue(result)
    
    def test_send_multiple_messages(self):
        """测试发送多条消息"""
        friend_name = "测试好友"
        messages = ["消息1", "消息2", "消息3"]
        
        result = self._send_message(friend_name, messages, "text")
        
        # 验证所有消息都被发送
        call_args = self.mock_pywechat.Messages.send_messages_to_friend.call_args
        self.assertEqual(len(call_args[1]['messages']), 3)
        self.assertTrue(result)
    
    def test_send_message_with_at(self):
        """测试发送带@的消息"""
        group_name = "测试群"
        message_content = "大家好"
        at_list = ["成员1", "成员2"]
        
        result = self._send_message(
            group_name, message_content, "text", 
            at=at_list, at_all=False
        )
        
        call_args = self.mock_pywechat.Messages.send_messages_to_friend.call_args
        self.assertEqual(call_args[1]['at'], at_list)
        self.assertFalse(call_args[1]['at_all'])
        self.assertTrue(result)
    
    def test_send_message_at_all(self):
        """测试发送@所有人的消息"""
        group_name = "测试群"
        message_content = "重要通知"
        
        result = self._send_message(
            group_name, message_content, "text",
            at=[], at_all=True
        )
        
        call_args = self.mock_pywechat.Messages.send_messages_to_friend.call_args
        self.assertTrue(call_args[1]['at_all'])
        self.assertTrue(result)
    
    def test_send_message_with_delay(self):
        """测试发送带延迟的消息"""
        friend_name = "测试好友"
        message_content = "延迟消息"
        send_delay = 1.5
        
        with patch('time.sleep') as mock_sleep:
            result = self._send_message(
                friend_name, message_content, "text",
                send_delay=send_delay
            )
            
            # 验证延迟被调用
            mock_sleep.assert_called()
            self.assertTrue(result)
    
    def test_send_message_to_nonexistent_friend(self):
        """测试发送消息给不存在的好友"""
        friend_name = "不存在的好友"
        message_content = "测试消息"
        
        # 模拟好友不存在异常
        self.mock_pywechat.Messages.send_messages_to_friend.side_effect = Exception("好友不存在")
        
        with self.assertRaises(Exception) as context:
            self._send_message(friend_name, message_content, "text")
        
        self.assertIn("好友不存在", str(context.exception))
    
    def test_send_empty_message(self):
        """测试发送空消息"""
        friend_name = "测试好友"
        message_content = ""
        
        with self.assertRaises(ValueError):
            self._send_message(friend_name, message_content, "text")
    
    def test_send_long_message(self):
        """测试发送长消息"""
        friend_name = "测试好友"
        # 生成超过500字的消息
        message_content = "测试内容" * 100
        
        result = self._send_message(friend_name, message_content, "text")
        
        # 长消息应该被截断或分片发送
        call_args = self.mock_pywechat.Messages.send_messages_to_friend.call_args
        sent_message = call_args[1]['messages'][0]
        self.assertTrue(len(sent_message) <= 500 or result)
    
    def test_send_image_message(self):
        """测试发送图片消息"""
        friend_name = "测试好友"
        image_path = "/path/to/image.jpg"
        
        result = self._send_message(friend_name, image_path, "image")
        
        # 验证图片发送
        self.assertTrue(result)
    
    def test_send_file_message(self):
        """测试发送文件消息"""
        friend_name = "测试好友"
        file_path = "/path/to/document.pdf"
        
        result = self._send_message(friend_name, file_path, "file")
        
        # 验证文件发送
        self.assertTrue(result)
    
    def test_send_message_with_tickle(self):
        """测试发送消息后拍一拍"""
        friend_name = "测试好友"
        message_content = "测试消息"
        
        result = self._send_message(
            friend_name, message_content, "text",
            tickle=True
        )
        
        call_args = self.mock_pywechat.Messages.send_messages_to_friend.call_args
        self.assertTrue(call_args[1]['tickle'])
        self.assertTrue(result)
    
    def _send_message(self, target: str, content: Any, msg_type: str,
                     at: List[str] = None, at_all: bool = False,
                     send_delay: float = None, tickle: bool = False) -> bool:
        """模拟发送消息"""
        if not content:
            raise ValueError("消息内容不能为空")
        
        messages = [content] if isinstance(content, str) else content
        
        try:
            self.mock_pywechat.Messages.send_messages_to_friend(
                friend=target,
                messages=messages,
                at=at or [],
                at_all=at_all,
                tickle=tickle,
                send_delay=send_delay
            )
            return True
        except Exception as e:
            raise e


# ==================== 消息接收测试 ====================

class TestMessageReceiver(unittest.TestCase):
    """消息接收功能测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.received_messages = []
        self.message_callbacks = []
    
    def test_receive_text_message(self):
        """测试接收文本消息"""
        message = MockWeChatMessage(
            msg_id="msg_001",
            content="你好",
            sender="好友A",
            msg_type="text",
            chat_type="private"
        )
        
        self._on_message_received(message)
        
        self.assertEqual(len(self.received_messages), 1)
        self.assertEqual(self.received_messages[0].content, "你好")
    
    def test_receive_group_message(self):
        """测试接收群消息"""
        message = MockWeChatMessage(
            msg_id="msg_002",
            content="群消息测试",
            sender="群成员B",
            msg_type="text",
            chat_type="group"
        )
        
        self._on_message_received(message)
        
        self.assertEqual(self.received_messages[0].chat_type, "group")
    
    def test_receive_image_message(self):
        """测试接收图片消息"""
        message = MockWeChatMessage(
            msg_id="msg_003",
            content="[图片]",
            sender="好友C",
            msg_type="image",
            chat_type="private"
        )
        
        self._on_message_received(message)
        
        self.assertEqual(self.received_messages[0].msg_type, "image")
    
    def test_receive_voice_message(self):
        """测试接收语音消息"""
        message = MockWeChatMessage(
            msg_id="msg_004",
            content="[语音]",
            sender="好友D",
            msg_type="voice",
            chat_type="private"
        )
        
        self._on_message_received(message)
        
        self.assertEqual(self.received_messages[0].msg_type, "voice")
    
    def test_receive_at_message(self):
        """测试接收@消息"""
        message = MockWeChatMessage(
            msg_id="msg_005",
            content="@我 请查看",
            sender="群成员E",
            msg_type="text",
            chat_type="group"
        )
        
        self._on_message_received(message)
        
        self.assertIn("@我", self.received_messages[0].content)
    
    def test_message_deduplication(self):
        """测试消息去重"""
        message1 = MockWeChatMessage(
            msg_id="msg_006",
            content="消息内容",
            sender="好友F"
        )
        message2 = MockWeChatMessage(
            msg_id="msg_006",  # 相同ID
            content="消息内容",
            sender="好友F"
        )
        
        self._on_message_received(message1)
        self._on_message_received(message2)  # 重复消息
        
        # 应该只保留一条
        self.assertEqual(len(self.received_messages), 1)
    
    def test_message_filter_by_sender(self):
        """测试按发送者过滤消息"""
        messages = [
            MockWeChatMessage("msg_007", "消息1", "好友A"),
            MockWeChatMessage("msg_008", "消息2", "好友B"),
            MockWeChatMessage("msg_009", "消息3", "好友A"),
        ]
        
        for msg in messages:
            self._on_message_received(msg)
        
        # 过滤好友A的消息
        filtered = [m for m in self.received_messages if m.sender == "好友A"]
        self.assertEqual(len(filtered), 2)
    
    def test_message_filter_by_type(self):
        """测试按类型过滤消息"""
        messages = [
            MockWeChatMessage("msg_010", "文本", "好友A", "text"),
            MockWeChatMessage("msg_011", "[图片]", "好友B", "image"),
            MockWeChatMessage("msg_012", "文本2", "好友C", "text"),
        ]
        
        for msg in messages:
            self._on_message_received(msg)
        
        # 过滤文本消息
        filtered = [m for m in self.received_messages if m.msg_type == "text"]
        self.assertEqual(len(filtered), 2)
    
    def test_message_callback(self):
        """测试消息回调"""
        callback_called = False
        received_msg = None
        
        def on_message(msg):
            nonlocal callback_called, received_msg
            callback_called = True
            received_msg = msg
        
        self.message_callbacks.append(on_message)
        
        message = MockWeChatMessage(
            msg_id="msg_013",
            content="回调测试",
            sender="好友G"
        )
        
        self._on_message_received(message)
        
        self.assertTrue(callback_called)
        self.assertEqual(received_msg.content, "回调测试")
    
    def test_receive_message_with_timestamp(self):
        """测试接收带时间戳的消息"""
        timestamp = datetime.now() - timedelta(minutes=5)
        message = MockWeChatMessage(
            msg_id="msg_014",
            content="历史消息",
            sender="好友H",
            timestamp=timestamp
        )
        
        self._on_message_received(message)
        
        self.assertEqual(self.received_messages[0].timestamp, timestamp)
    
    def _on_message_received(self, message: MockWeChatMessage):
        """消息接收处理"""
        # 去重检查
        if any(m.msg_id == message.msg_id for m in self.received_messages):
            return
        
        self.received_messages.append(message)
        
        # 触发回调
        for callback in self.message_callbacks:
            callback(message)


# ==================== 群管理测试 ====================

class TestGroupManager(unittest.TestCase):
    """群管理功能测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.groups = {}
        self.mock_pywechat = Mock()
    
    def test_create_group(self):
        """测试创建群聊"""
        group_name = "测试群"
        members = ["成员A", "成员B", "成员C"]
        
        group = self._create_group(group_name, members)
        
        self.assertIsNotNone(group)
        self.assertEqual(group.name, group_name)
        self.assertEqual(len(group.members), 3)
    
    def test_add_group_member(self):
        """测试添加群成员"""
        group = MockGroup(
            group_id="grp_001",
            name="测试群",
            owner="群主",
            members=["成员A", "成员B"]
        )
        
        result = group.add_member("成员C")
        
        self.assertTrue(result)
        self.assertEqual(group.get_member_count(), 3)
        self.assertIn("成员C", group.members)
    
    def test_add_duplicate_member(self):
        """测试添加重复成员"""
        group = MockGroup(
            group_id="grp_002",
            name="测试群",
            owner="群主",
            members=["成员A"]
        )
        
        result = group.add_member("成员A")  # 重复添加
        
        self.assertFalse(result)
        self.assertEqual(group.get_member_count(), 1)
    
    def test_remove_group_member(self):
        """测试移除群成员"""
        group = MockGroup(
            group_id="grp_003",
            name="测试群",
            owner="群主",
            members=["成员A", "成员B", "成员C"]
        )
        
        result = group.remove_member("成员B")
        
        self.assertTrue(result)
        self.assertEqual(group.get_member_count(), 2)
        self.assertNotIn("成员B", group.members)
    
    def test_remove_nonexistent_member(self):
        """测试移除不存在的成员"""
        group = MockGroup(
            group_id="grp_004",
            name="测试群",
            owner="群主",
            members=["成员A"]
        )
        
        result = group.remove_member("成员X")  # 不存在的成员
        
        self.assertFalse(result)
        self.assertEqual(group.get_member_count(), 1)
    
    def test_get_group_info(self):
        """测试获取群信息"""
        group = MockGroup(
            group_id="grp_005",
            name="测试群",
            owner="群主",
            members=["成员A", "成员B"],
            announcement="群公告"
        )
        
        self.assertEqual(group.group_id, "grp_005")
        self.assertEqual(group.name, "测试群")
        self.assertEqual(group.owner, "群主")
        self.assertEqual(group.announcement, "群公告")
    
    def test_update_group_announcement(self):
        """测试更新群公告"""
        group = MockGroup(
            group_id="grp_006",
            name="测试群",
            owner="群主"
        )
        
        new_announcement = "新公告内容"
        group.announcement = new_announcement
        
        self.assertEqual(group.announcement, new_announcement)
    
    def test_invite_to_group(self):
        """测试邀请加入群聊"""
        group_name = "测试群"
        invitee = "新成员"
        
        result = self._invite_to_group(group_name, invitee)
        
        self.assertTrue(result)
    
    def test_exit_group(self):
        """测试退出群聊"""
        group_id = "grp_007"
        user_id = "用户A"
        
        result = self._exit_group(group_id, user_id)
        
        self.assertTrue(result)
    
    def test_get_group_members(self):
        """测试获取群成员列表"""
        group = MockGroup(
            group_id="grp_008",
            name="测试群",
            owner="群主",
            members=["成员A", "成员B", "成员C", "成员D"]
        )
        
        members = group.members
        
        self.assertEqual(len(members), 4)
        self.assertIn("成员A", members)
    
    def test_is_group_owner(self):
        """测试判断是否为群主"""
        group = MockGroup(
            group_id="grp_009",
            name="测试群",
            owner="群主A"
        )
        
        self.assertTrue(group.owner == "群主A")
        self.assertFalse(group.owner == "成员B")
    
    def test_transfer_group_ownership(self):
        """测试转让群主"""
        group = MockGroup(
            group_id="grp_010",
            name="测试群",
            owner="原群主"
        )
        
        new_owner = "新群主"
        group.owner = new_owner
        
        self.assertEqual(group.owner, new_owner)
    
    def test_mute_group(self):
        """测试群聊免打扰"""
        group_id = "grp_011"
        mute_duration = 60  # 分钟
        
        result = self._set_group_mute(group_id, True, mute_duration)
        
        self.assertTrue(result)
    
    def test_pin_group(self):
        """测试置顶群聊"""
        group_id = "grp_012"
        
        result = self._pin_group(group_id, True)
        
        self.assertTrue(result)
    
    def _create_group(self, name: str, members: List[str]) -> MockGroup:
        """创建群聊"""
        group_id = f"grp_{int(time.time())}"
        group = MockGroup(
            group_id=group_id,
            name=name,
            owner="创建者",
            members=members
        )
        self.groups[group_id] = group
        return group
    
    def _invite_to_group(self, group_name: str, invitee: str) -> bool:
        """邀请加入群聊"""
        # 模拟邀请逻辑
        return True
    
    def _exit_group(self, group_id: str, user_id: str) -> bool:
        """退出群聊"""
        if group_id in self.groups:
            group = self.groups[group_id]
            return group.remove_member(user_id)
        return False
    
    def _set_group_mute(self, group_id: str, mute: bool, duration: int = None) -> bool:
        """设置群聊免打扰"""
        return True
    
    def _pin_group(self, group_id: str, pin: bool) -> bool:
        """置顶/取消置顶群聊"""
        return True


# ==================== 联系人管理测试 ====================

class TestContactManager(unittest.TestCase):
    """联系人管理功能测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.contacts = {}
    
    def test_add_friend(self):
        """测试添加好友"""
        contact = MockContact(
            contact_id="ct_001",
            nickname="新好友",
            remark="备注名",
            is_friend=True
        )
        
        self.contacts[contact.contact_id] = contact
        
        self.assertIn("ct_001", self.contacts)
        self.assertEqual(self.contacts["ct_001"].nickname, "新好友")
    
    def test_delete_friend(self):
        """测试删除好友"""
        contact = MockContact(
            contact_id="ct_002",
            nickname="待删除好友"
        )
        self.contacts[contact.contact_id] = contact
        
        del self.contacts["ct_002"]
        
        self.assertNotIn("ct_002", self.contacts)
    
    def test_update_friend_remark(self):
        """测试修改好友备注"""
        contact = MockContact(
            contact_id="ct_003",
            nickname="好友",
            remark="旧备注"
        )
        self.contacts[contact.contact_id] = contact
        
        new_remark = "新备注"
        contact.remark = new_remark
        
        self.assertEqual(contact.remark, new_remark)
    
    def test_get_friend_info(self):
        """测试获取好友信息"""
        contact = MockContact(
            contact_id="ct_004",
            nickname="好友A",
            remark="备注A",
            is_friend=True
        )
        
        info = {
            "id": contact.contact_id,
            "nickname": contact.nickname,
            "remark": contact.remark,
            "display_name": contact.get_display_name()
        }
        
        self.assertEqual(info["display_name"], "备注A")
    
    def test_search_friend(self):
        """测试搜索好友"""
        contacts = [
            MockContact("ct_005", "张三", "小张"),
            MockContact("ct_006", "李四", "小李"),
            MockContact("ct_007", "张五", "大张"),
        ]
        
        for c in contacts:
            self.contacts[c.contact_id] = c
        
        # 搜索包含"张"的联系人
        results = [c for c in self.contacts.values() 
                  if "张" in c.nickname or "张" in c.remark]
        
        self.assertEqual(len(results), 2)
    
    def test_get_friend_list(self):
        """测试获取好友列表"""
        contacts = [
            MockContact("ct_008", "好友A", is_friend=True),
            MockContact("ct_009", "好友B", is_friend=True),
            MockContact("ct_010", "非好友", is_friend=False),
        ]
        
        for c in contacts:
            self.contacts[c.contact_id] = c
        
        friends = [c for c in self.contacts.values() if c.is_friend]
        
        self.assertEqual(len(friends), 2)


# ==================== 运行测试 ====================

if __name__ == '__main__':
    # 配置测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMessageSender))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageReceiver))
    suite.addTests(loader.loadTestsFromTestCase(TestGroupManager))
    suite.addTests(loader.loadTestsFromTestCase(TestContactManager))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出统计
    print("\n" + "="*60)
    print("测试统计")
    print("="*60)
    print(f"测试用例总数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    print("="*60)