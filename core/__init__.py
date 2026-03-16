# -*- coding: utf-8 -*-
"""
jz-wxbot 核心模块
"""

# Import from message_reader_interface
from .message_reader_interface import (
    MessageReaderInterface, 
    MessageReaderFactory, 
    WeChatMessage, 
    MessageType, 
    ChatType,
    ReadResult
)

# Import from message_handler
from .message_handler import (
    MessageHandler, 
    MessageSender, 
    MessageQueue
)

# Import human_like_operations if available
try:
    from ..human_like_operations import HumanLikeOperations
    __all__ = [
        'MessageReaderInterface',
        'MessageReaderFactory',
        'WeChatMessage',
        'MessageType',
        'ChatType',
        'ReadResult',
        'MessageHandler',
        'MessageSender',
        'MessageQueue',
        'HumanLikeOperations',
    ]
except ImportError:
    __all__ = [
        'MessageReaderInterface',
        'MessageReaderFactory',
        'WeChatMessage',
        'MessageType',
        'ChatType',
        'ReadResult',
        'MessageHandler',
        'MessageSender',
        'MessageQueue',
    ]