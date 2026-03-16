# -*- coding: utf-8 -*-
"""
群管理功能测试
版本: v1.0.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import time
import threading

from managers.group_manager_impl import (
    GroupManager,
    FriendManager
)
from managers.group_manager import (
    GroupInfo,
    MemberInfo
)


class TestGroupManager(unittest.TestCase):
    """群管理器测试"""
    
    def setUp(self):
        self.manager = GroupManager()
    
    def test_initialization(self):
        """测试初始化"""
        result = self.manager.initialize()
        self.assertTrue(result)
        self.assertTrue(self.manager.is_initialized)
    
    def test_get_group_list(self):
        """测试获取群列表"""
        self.manager.initialize()
        groups = self.manager.get_group_list()
        
        self.assertIsInstance(groups, list)
        self.assertGreater(len(groups), 0)
        
        # 验证群信息结构
        for group in groups:
            self.assertIsInstance(group, GroupInfo)
            self.assertIsNotNone(group.group_id)
            self.assertIsNotNone(group.group_name)
    
    def test_get_group_info(self):
        """测试获取群信息"""
        self.manager.initialize()
        
        # 先获取群列表
        groups = self.manager.get_group_list()
        if groups:
            group_id = groups[0].group_id
            
            # 获取群信息
            group_info = self.manager.get_group_info(group_id)
            
            self.assertIsNotNone(group_info)
            self.assertEqual(group_info.group_id, group_id)
    
    def test_get_group_members(self):
        """测试获取群成员"""
        self.manager.initialize()
        
        groups = self.manager.get_group_list()
        if groups:
            group_id = groups[0].group_id
            members = self.manager.get_group_members(group_id)
            
            self.assertIsInstance(members, list)
            
            # 验证成员信息结构
            for member in members:
                self.assertIsInstance(member, MemberInfo)
                self.assertIsNotNone(member.user_id)
                self.assertIsNotNone(member.nickname)
                self.assertIn(member.role, ['owner', 'admin', 'member'])
    
    def test_send_group_message(self):
        """测试发送群消息"""
        self.manager.initialize()
        
        groups = self.manager.get_group_list()
        if groups:
            result = self.manager.send_group_message(
                groups[0].group_id,
                "测试消息"
            )
            self.assertTrue(result)
    
    def test_at_members(self):
        """测试@成员"""
        self.manager.initialize()
        
        groups = self.manager.get_group_list()
        if groups:
            group_id = groups[0].group_id
            members = self.manager.get_group_members(group_id)
            
            if members:
                member_ids = [members[0].user_id]
                result = self.manager.at_members(
                    group_id,
                    member_ids,
                    "请查看"
                )
                self.assertTrue(result)
    
    def test_at_all(self):
        """测试@所有人"""
        self.manager.initialize()
        
        groups = self.manager.get_group_list()
        if groups:
            result = self.manager.at_all(
                groups[0].group_id,
                "各位好"
            )
            self.assertTrue(result)
    
    def test_set_group_announcement(self):
        """测试设置群公告"""
        self.manager.initialize()
        
        groups = self.manager.get_group_list()
        if groups:
            group_id = groups[0].group_id
            announcement = "欢迎大家加入本群！"
            
            result = self.manager.set_group_announcement(group_id, announcement)
            self.assertTrue(result)
            
            # 验证公告已更新
            updated = self.manager.get_group_announcement(group_id)
            self.assertEqual(updated, announcement)
    
    def test_search_group(self):
        """测试搜索群"""
        self.manager.initialize()
        
        groups = self.manager.get_group_list()
        if groups:
            keyword = groups[0].group_name[:2]  # 取群名前两个字
            results = self.manager.search_group(keyword)
            
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)
            
            for group in results:
                self.assertIn(keyword, group.group_name)
    
    def test_monitoring(self):
        """测试群消息监控"""
        self.manager.initialize()
        
        # 启动监控
        result = self.manager.start_monitoring()
        self.assertTrue(result)
        self.assertTrue(self.manager._monitoring)
        
        # 运行2秒
        time.sleep(2)
        
        # 停止监控
        result = self.manager.stop_monitoring()
        self.assertTrue(result)
        self.assertFalse(self.manager._monitoring)
    
    def test_manager_info(self):
        """测试获取管理器信息"""
        self.manager.initialize()
        
        info = self.manager.get_manager_info()
        
        self.assertEqual(info['manager_type'], 'GroupManager')
        self.assertTrue(info['is_initialized'])
        self.assertIn('group_count', info)


class TestFriendManager(unittest.TestCase):
    """好友管理器测试"""
    
    def setUp(self):
        self.manager = FriendManager()
    
    def test_initialization(self):
        """测试初始化"""
        result = self.manager.initialize()
        self.assertTrue(result)
        self.assertIsNotNone(self.manager._friends)
    
    def test_get_friend_list(self):
        """测试获取好友列表"""
        self.manager.initialize()
        friends = self.manager.get_friend_list()
        
        self.assertIsInstance(friends, list)
        self.assertGreater(len(friends), 0)
        
        # 验证好友信息结构
        for friend in friends:
            self.assertIn('user_id', friend)
            self.assertIn('nickname', friend)
    
    def test_get_friend_info(self):
        """测试获取好友信息"""
        self.manager.initialize()
        
        friends = self.manager.get_friend_list()
        if friends:
            user_id = friends[0]['user_id']
            
            friend_info = self.manager.get_friend_info(user_id)
            
            self.assertIsNotNone(friend_info)
            self.assertEqual(friend_info['user_id'], user_id)
    
    def test_add_friend(self):
        """测试添加好友"""
        self.manager.initialize()
        
        result = self.manager.add_friend(
            "test_user_123",
            "你好，我是XXX"
        )
        self.assertTrue(result)
    
    def test_delete_friend(self):
        """测试删除好友"""
        self.manager.initialize()
        
        # 先添加好友
        self.manager.add_friend("temp_user", "测试")
        
        # 删除好友
        result = self.manager.delete_friend("temp_user")
        self.assertTrue(result)
        
        # 验证已删除
        friend = self.manager.get_friend_info("temp_user")
        self.assertIsNone(friend)
    
    def test_search_friend(self):
        """测试搜索好友"""
        self.manager.initialize()
        
        friends = self.manager.get_friend_list()
        if friends:
            keyword = friends[0]['nickname'][:2]
            results = self.manager.search_friend(keyword)
            
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)
            
            for friend in results:
                self.assertIn(keyword, friend.get('nickname', '') + friend.get('remark', ''))


class TestGroupInfo(unittest.TestCase):
    """群信息数据类测试"""
    
    def test_group_info_creation(self):
        """测试创建群信息"""
        group = GroupInfo(
            group_id="group_1",
            group_name="测试群",
            member_count=100,
            owner_id="user_1",
            announcement="欢迎"
        )
        
        self.assertEqual(group.group_id, "group_1")
        self.assertEqual(group.group_name, "测试群")
        self.assertEqual(group.member_count, 100)
        self.assertEqual(group.owner_id, "user_1")
    
    def test_group_info_to_dict(self):
        """测试群信息转字典"""
        group = GroupInfo(
            group_id="group_1",
            group_name="测试群",
            member_count=100
        )
        
        data = group.to_dict()
        
        self.assertEqual(data['group_id'], "group_1")
        self.assertEqual(data['group_name'], "测试群")
        self.assertEqual(data['member_count'], 100)


class TestMemberInfo(unittest.TestCase):
    """成员信息数据类测试"""
    
    def test_member_info_creation(self):
        """测试创建成员信息"""
        member = MemberInfo(
            user_id="user_1",
            nickname="张三",
            remark="老张",
            role="admin"
        )
        
        self.assertEqual(member.user_id, "user_1")
        self.assertEqual(member.nickname, "张三")
        self.assertEqual(member.remark, "老张")
        self.assertEqual(member.role, "admin")
    
    def test_member_info_to_dict(self):
        """测试成员信息转字典"""
        member = MemberInfo(
            user_id="user_1",
            nickname="张三",
            role="member"
        )
        
        data = member.to_dict()
        
        self.assertEqual(data['user_id'], "user_1")
        self.assertEqual(data['nickname'], "张三")
        self.assertEqual(data['role'], "member")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestGroupManager))
    suite.addTests(loader.loadTestsFromTestCase(TestFriendManager))
    suite.addTests(loader.loadTestsFromTestCase(TestGroupInfo))
    suite.addTests(loader.loadTestsFromTestCase(TestMemberInfo))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "="*50)
    print(f"测试完成: {result.testsRun} 个测试")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*50)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)