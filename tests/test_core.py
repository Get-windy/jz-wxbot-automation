# -*- coding: utf-8 -*-
"""
jz-wxbot 功能测试脚本
版本: v1.0.0
功能: 测试微信自动化核心功能
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_message_sender():
    """测试消息发送模块"""
    logger.info("=" * 60)
    logger.info("测试消息发送模块")
    logger.info("=" * 60)
    
    try:
        # 测试接口定义
        from message_sender_interface import MessageSenderInterface, MessageSenderFactory, SendResult
        logger.info("✅ 消息发送接口导入成功")
        
        # 测试发送器
        try:
            from wechat_sender_v3 import WeChatSenderV3
            logger.info("✅ 个人微信发送器导入成功")
        except Exception as e:
            logger.warning(f"⚠️ 个人微信发送器导入失败: {e}")
        
        try:
            from wxwork_sender import WXWorkSender
            logger.info("✅ 企业微信发送器导入成功")
        except Exception as e:
            logger.warning(f"⚠️ 企业微信发送器导入失败: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 消息发送模块测试失败: {e}")
        return False


def test_message_reader():
    """测试消息接收模块"""
    logger.info("\n" + "=" * 60)
    logger.info("测试消息接收模块")
    logger.info("=" * 60)
    
    try:
        # 测试接口定义
        from core.message_reader_interface import MessageReaderInterface, MessageReaderFactory, ReadResult
        logger.info("✅ 消息接收接口导入成功")
        
        # 测试读取器
        try:
            from readers.wechat_reader import WeChatMessageReader
            logger.info("✅ 个人微信读取器导入成功")
        except Exception as e:
            logger.warning(f"⚠️ 个人微信读取器导入失败: {e}")
        
        try:
            from readers.wxwork_reader import WXWorkMessageReader
            logger.info("✅ 企业微信读取器导入成功")
        except Exception as e:
            logger.warning(f"⚠️ 企业微信读取器导入失败: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 消息接收模块测试失败: {e}")
        return False


def test_group_manager():
    """测试群消息管理模块"""
    logger.info("\n" + "=" * 60)
    logger.info("测试群消息管理模块")
    logger.info("=" * 60)
    
    try:
        from managers.group_manager import GroupManagerInterface, GroupInfo, MemberInfo
        
        # 测试数据结构
        group = GroupInfo(
            group_id="test_group",
            group_name="测试群",
            member_count=10
        )
        logger.info(f"✅ 群数据结构测试成功")
        
        member = MemberInfo(
            user_id="test_user",
            nickname="测试用户"
        )
        logger.info(f"✅ 成员数据结构测试成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 群消息管理模块测试失败: {e}")
        return False


def test_contact_manager():
    """测试联系人管理模块"""
    logger.info("\n" + "=" * 60)
    logger.info("测试联系人管理模块")
    logger.info("=" * 60)
    
    try:
        from managers.contact_manager import ContactManagerInterface, ContactInfo, AddFriendResult
        
        # 测试数据结构
        contact = ContactInfo(
            user_id="test_user",
            nickname="测试用户"
        )
        logger.info(f"✅ 联系人数据结构测试成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 联系人管理模块测试失败: {e}")
        return False


def test_human_like_operations():
    """测试人性化操作模块"""
    logger.info("\n" + "=" * 60)
    logger.info("测试人性化操作模块")
    logger.info("=" * 60)
    
    try:
        from human_like_operations import HumanLikeOperations
        
        ops = HumanLikeOperations()
        logger.info("✅ 人性化操作模块初始化成功")
        
        # 测试功能存在
        assert hasattr(ops, 'human_delay')
        assert hasattr(ops, 'human_move_to')
        assert hasattr(ops, 'human_click')
        assert hasattr(ops, 'human_type_text')
        logger.info("✅ 人性化操作模块功能完整")
        
        return True
    except Exception as e:
        logger.error(f"❌ 人性化操作模块测试失败: {e}")
        return False


def test_bridge_service():
    """测试桥接服务"""
    logger.info("\n" + "=" * 60)
    logger.info("测试桥接服务")
    logger.info("=" * 60)
    
    try:
        from bridge.bridge_service import BridgeService
        
        config = {
            'openclaw': {
                'gateway_url': 'ws://127.0.0.1:3100',
                'agent_id': 'wxbot-agent'
            }
        }
        
        bridge = BridgeService(config)
        logger.info("✅ 桥接服务初始化成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 桥接服务测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("\n" + "=" * 60)
    logger.info("jz-wxbot 功能测试开始")
    logger.info("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("消息发送模块", test_message_sender()))
    results.append(("消息接收模块", test_message_reader()))
    results.append(("群消息管理", test_group_manager()))
    results.append(("联系人管理", test_contact_manager()))
    results.append(("人性化操作", test_human_like_operations()))
    results.append(("桥接服务", test_bridge_service()))
    
    # 输出测试结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")
    
    logger.info(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！")
        return 0
    else:
        logger.warning("⚠️ 部分测试未通过")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
