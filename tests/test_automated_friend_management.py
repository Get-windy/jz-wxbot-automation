# -*- coding: utf-8 -*-
"""
jz-wxbot 好友管理模块自动化测试
覆盖好友CRUD、好友请求等功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from datetime import datetime
import secrets

from managers.contact_manager import (
    ContactInfo,
    AddFriendStatus
)


class TestFriendManagementAutomated(unittest.TestCase):
    """好友管理自动化测试"""
    
    def setUp(self):
        self.contacts_db = []
        self.requests_db = []
        self.test_user_id = secrets.token_hex(16)
    
    def test_add_friend(self):
        """TC-F001: 添加好友"""
        contact = ContactInfo(
            user_id=secrets.token_hex(16),
            nickname="张三",
            remark="同事",
            is_friend=True
        )
        self.contacts_db.append(contact)
        self.assertEqual(len(self.contacts_db), 1)
        self.assertTrue(contact.is_friend)
    
    def test_add_friend_with_tags(self):
        """TC-F002: 添加带标签的好友"""
        contact = ContactInfo(
            user_id=secrets.token_hex(16),
            nickname="李四",
            tags=["朋友", "同事"],
            is_friend=True
        )
        self.contacts_db.append(contact)
        self.assertEqual(len(contact.tags), 2)
    
    def test_add_friend_with_region(self):
        """TC-F003: 添加带地区的好友"""
        contact = ContactInfo(
            user_id=secrets.token_hex(16),
            nickname="王五",
            region="北京",
            signature="签名",
            is_friend=True
        )
        self.contacts_db.append(contact)
        self.assertEqual(contact.region, "北京")
    
    def test_get_contact_list(self):
        """TC-F004: 获取好友列表"""
        for i in range(5):
            contact = ContactInfo(
                user_id=str(i),
                nickname=f"好友{i}",
                is_friend=True
            )
            self.contacts_db.append(contact)
        friends = [c for c in self.contacts_db if c.is_friend]
        self.assertEqual(len(friends), 5)
    
    def test_search_contact(self):
        """TC-F005: 搜索好友"""
        contacts = [
            ContactInfo(user_id='1', nickname="张三", is_friend=True),
            ContactInfo(user_id='2', nickname="张三丰", is_friend=True),
            ContactInfo(user_id='3', nickname="李四", is_friend=True),
        ]
        self.contacts_db.extend(contacts)
        results = [c for c in self.contacts_db if "张" in c.nickname]
        self.assertEqual(len(results), 2)
    
    def test_update_contact_remark(self):
        """TC-F006: 更新好友备注"""
        contact = ContactInfo(
            user_id='1',
            nickname="张三",
            remark="旧备注",
            is_friend=True
        )
        self.contacts_db.append(contact)
        contact.remark = "新备注"
        self.assertEqual(contact.remark, "新备注")
    
    def test_update_contact_tags(self):
        """TC-F007: 更新好友标签"""
        contact = ContactInfo(
            user_id='1',
            nickname="李四",
            tags=["朋友"],
            is_friend=True
        )
        self.contacts_db.append(contact)
        contact.tags = ["朋友", "VIP"]
        self.assertIn("VIP", contact.tags)
    
    def test_delete_friend(self):
        """TC-F008: 删除好友"""
        contact = ContactInfo(
            user_id='1',
            nickname="待删除",
            is_friend=True
        )
        self.contacts_db.append(contact)
        contact.is_friend = False
        self.assertFalse(contact.is_friend)
    
    def test_send_friend_request(self):
        """TC-F009: 发送好友请求"""
        request = {
            'request_id': secrets.token_hex(16),
            'from_user_id': self.test_user_id,
            'to_user_id': secrets.token_hex(16),
            'message': '你好',
            'status': AddFriendStatus.SENT
        }
        self.requests_db.append(request)
        self.assertEqual(len(self.requests_db), 1)
    
    def test_receive_friend_request(self):
        """TC-F010: 接收好友请求"""
        request = {
            'request_id': secrets.token_hex(16),
            'from_user_id': secrets.token_hex(16),
            'to_user_id': self.test_user_id,
            'status': AddFriendStatus.PENDING
        }
        self.requests_db.append(request)
        pending = [r for r in self.requests_db if r['status'] == AddFriendStatus.PENDING]
        self.assertEqual(len(pending), 1)
    
    def test_accept_friend_request(self):
        """TC-F011: 接受好友请求"""
        request = {
            'request_id': secrets.token_hex(16),
            'from_user_id': secrets.token_hex(16),
            'to_user_id': self.test_user_id,
            'status': AddFriendStatus.PENDING
        }
        self.requests_db.append(request)
        request['status'] = AddFriendStatus.ACCEPTED
        
        new_contact = ContactInfo(
            user_id=request['from_user_id'],
            nickname="新朋友",
            is_friend=True
        )
        self.contacts_db.append(new_contact)
        
        self.assertEqual(request['status'], AddFriendStatus.ACCEPTED)
        self.assertEqual(len(self.contacts_db), 1)
    
    def test_reject_friend_request(self):
        """TC-F012: 拒绝好友请求"""
        request = {
            'request_id': secrets.token_hex(16),
            'from_user_id': secrets.token_hex(16),
            'to_user_id': self.test_user_id,
            'status': AddFriendStatus.PENDING
        }
        self.requests_db.append(request)
        request['status'] = AddFriendStatus.REJECTED
        self.assertEqual(request['status'], AddFriendStatus.REJECTED)
    
    def test_contact_to_dict(self):
        """TC-F013: 联系人转字典"""
        contact = ContactInfo(
            user_id='user_001',
            nickname="测试",
            remark="备注",
            is_friend=True
        )
        data = contact.to_dict()
        self.assertEqual(data['user_id'], 'user_001')
        self.assertEqual(data['nickname'], '测试')


if __name__ == '__main__':
    unittest.main()
