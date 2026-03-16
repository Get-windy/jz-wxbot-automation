# -*- coding: utf-8 -*-
"""
jz-wxbot 管理器模块
"""

from .group_manager import GroupManagerInterface, GroupInfo, MemberInfo
from .group_manager_impl import GroupManager, FriendManager

# Import from contact_manager
try:
    from .contact_manager import ContactInfo, AddFriendStatus
    __all__ = [
        'GroupManagerInterface',
        'GroupInfo',
        'MemberInfo',
        'GroupManager',
        'FriendManager',
        'ContactInfo',
        'AddFriendStatus',
    ]
except ImportError:
    __all__ = [
        'GroupManagerInterface',
        'GroupInfo',
        'MemberInfo',
        'GroupManager',
        'FriendManager',
    ]