# -*- coding: utf-8 -*-
"""
微信自动化异常模块
基于 pywechat Errors.py 改编

异常分类:
- 基础异常: WeChatError
- 连接异常: WeChatNotStartError, NetWorkNotConnectError
- 操作异常: ElementNotFoundError, TimeoutError, NoPatternInterfaceError
- 文件异常: EmptyFileError, NotFileError, NotFolderError
- 好友/群聊异常: NoSuchFriendError, NotFriendError, NoGroupsError
- 权限异常: NoPermissionError

使用示例:
    from core.exceptions import (
        WeChatNotStartError,
        NoSuchFriendError,
        WeChatError
    )
    
    try:
        # 操作微信
        pass
    except WeChatNotStartError as e:
        print(f"微信未启动: {e}")
    except NoSuchFriendError as e:
        print(f"好友不存在: {e}")
"""

# 尝试导入 pywinauto 异常 (如果可用)
try:
    from pywinauto.findwindows import ElementNotFoundError as PywinautoElementNotFoundError
    from pywinauto.timings import TimeoutError as PywinautoTimeoutError
    from pywinauto.uia_defines import NoPatternInterfaceError as PywinautoNoPatternError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    PywinautoElementNotFoundError = Exception
    PywinautoTimeoutError = Exception
    PywinautoNoPatternError = Exception


# ============================================================
# 基础异常类
# ============================================================

class WeChatError(Exception):
    """微信自动化基础异常"""
    def __init__(self, message: str = "微信自动化未知错误"):
        super().__init__(message)
        self.message = message


# ============================================================
# pywinauto 异常封装
# ============================================================

if PYWINAUTO_AVAILABLE:
    class ElementNotFoundError(WeChatError, PywinautoElementNotFoundError):
        """UI 元素未找到异常"""
        def __init__(self, message: str = "未找到指定的 UI 元素"):
            WeChatError.__init__(self, message)
    
    class TimeoutError(WeChatError, PywinautoTimeoutError):
        """操作超时异常"""
        def __init__(self, message: str = "操作超时"):
            WeChatError.__init__(self, message)
    
    class NoPatternInterfaceError(WeChatError, PywinautoNoPatternError):
        """UI 模式接口不支持异常"""
        def __init__(self, message: str = "UI 元素不支持该操作"):
            WeChatError.__init__(self, message)
else:
    # 如果 pywinauto 不可用，使用基础异常
    class ElementNotFoundError(WeChatError):
        """UI 元素未找到异常"""
        def __init__(self, message: str = "未找到指定的 UI 元素"):
            super().__init__(message)
    
    class TimeoutError(WeChatError):
        """操作超时异常"""
        def __init__(self, message: str = "操作超时"):
            super().__init__(message)
    
    class NoPatternInterfaceError(WeChatError):
        """UI 模式接口不支持异常"""
        def __init__(self, message: str = "UI 元素不支持该操作"):
            super().__init__(message)


# ============================================================
# 连接相关异常
# ============================================================

class WeChatNotStartError(WeChatError):
    """微信未启动异常"""
    def __init__(self, message: str = "微信未启动, 请启动后再调用此函数!"):
        super().__init__(message)


class NetWorkNotConnectError(WeChatError):
    """网络未连接异常"""
    def __init__(self, message: str = "网络可能未连接, 无法进入微信! 请连接网络后重试"):
        super().__init__(message)


class ScanCodeToLogInError(WeChatError):
    """未开启自动登录异常"""
    def __init__(self, message: str = "请在手机端开启 PC 端微信自动登录"):
        super().__init__(message)


# ============================================================
# 文件操作异常
# ============================================================

class EmptyFileError(WeChatError):
    """空文件异常"""
    def __init__(self, message: str = "不能发送空文件! 请重新选择文件路径"):
        super().__init__(message)


class EmptyFolderError(WeChatError):
    """空文件夹异常"""
    def __init__(self, message: str = "文件夹内没有文件! 请重新选择"):
        super().__init__(message)


class NotFileError(WeChatError):
    """路径不是文件异常"""
    def __init__(self, message: str = "该路径下的内容不是文件, 无法发送!"):
        super().__init__(message)


class NotFolderError(WeChatError):
    """路径不是文件夹异常"""
    def __init__(self, message: str = "给定路径不是文件夹! 若需发送多个文件, 请将文件置于文件夹内"):
        super().__init__(message)


# ============================================================
# 好友/群聊相关异常
# ============================================================

class NoSuchFriendError(WeChatError):
    """好友不存在异常"""
    def __init__(self, message: str = "好友或群聊备注有误! 查无此人! 请提供准确的好友或群聊备注"):
        super().__init__(message)


class NotFriendError(WeChatError):
    """非好友异常"""
    def __init__(self, message: str = "该用户不是您的好友"):
        super().__init__(message)


class NoGroupsError(WeChatError):
    """没有群聊异常"""
    def __init__(self, message: str = "还未加入过任何群聊, 无法获取群聊信息"):
        super().__init__(message)


class CantCreateGroupError(WeChatError):
    """无法创建群聊异常"""
    def __init__(self, message: str = "除自身外至少需要两人以上才可以创建群聊"):
        super().__init__(message)


class NoChatsError(WeChatError):
    """没有聊天记录异常"""
    def __init__(self, message: str = "会话列表为空, 无最近聊天对象"):
        super().__init__(message)


# ============================================================
# 公众号相关异常
# ============================================================

class NotInstalledError(WeChatError):
    """微信未安装异常"""
    def __init__(self, message: str = "未找到微信安装路径, 可能未安装微信或注册表被删除"):
        super().__init__(message)


class NoSubOffAccError(WeChatError):
    """没有关注公众号异常"""
    def __init__(self, message: str = "从未关注过任何公众号, 无法获取已关注的公众号名称"):
        super().__init__(message)


# ============================================================
# 企业微信相关异常
# ============================================================

class NoWecomFriendsError(WeChatError):
    """企业微信好友不存在异常"""
    def __init__(self, message: str = "未查找到企业微信好友, 无法获取企业微信好友信息"):
        super().__init__(message)


# ============================================================
# 权限/认证异常
# ============================================================

class NoPermissionError(WeChatError):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足, 无法执行此操作"):
        super().__init__(message)


# ============================================================
# 聊天记录异常
# ============================================================

class NoChatHistoryError(WeChatError):
    """聊天记录不足异常"""
    def __init__(self, message: str = "聊天记录不足, 无法执行此操作"):
        super().__init__(message)


# ============================================================
# 时间格式异常
# ============================================================

class TimeNotCorrectError(WeChatError):
    """时间格式错误异常"""
    def __init__(self, message: str = "请输入合法的时间长度!"):
        super().__init__(message)


# ============================================================
# 拍一拍异常
# ============================================================

class TickleError(WeChatError):
    """拍一拍异常"""
    def __init__(self, message: str = "拍一拍操作失败"):
        super().__init__(message)


# ============================================================
# 搜索结果异常
# ============================================================

class NoResultsError(WeChatError):
    """搜索无结果异常"""
    def __init__(self, message: str = "搜索无结果"):
        super().__init__(message)


# ============================================================
# 异常映射表 (用于统一错误处理)
# ============================================================

ERROR_CODE_MAP = {
    'WECHAT_NOT_START': WeChatNotStartError,
    'NETWORK_ERROR': NetWorkNotConnectError,
    'SCAN_CODE_ERROR': ScanCodeToLogInError,
    'ELEMENT_NOT_FOUND': ElementNotFoundError,
    'TIMEOUT': TimeoutError,
    'EMPTY_FILE': EmptyFileError,
    'NOT_FILE': NotFileError,
    'NOT_FOLDER': NotFolderError,
    'NO_SUCH_FRIEND': NoSuchFriendError,
    'NOT_FRIEND': NotFriendError,
    'NO_GROUPS': NoGroupsError,
    'CANT_CREATE_GROUP': CantCreateGroupError,
    'NO_CHATS': NoChatsError,
    'NOT_INSTALLED': NotInstalledError,
    'NO_SUB_OFF_ACC': NoSubOffAccError,
    'NO_WECOM_FRIENDS': NoWecomFriendsError,
    'NO_PERMISSION': NoPermissionError,
    'NO_CHAT_HISTORY': NoChatHistoryError,
    'TIME_NOT_CORRECT': TimeNotCorrectError,
    'TICKLE_ERROR': TickleError,
    'NO_RESULTS': NoResultsError,
}


def get_error_by_code(error_code: str) -> type:
    """
    根据错误码获取异常类
    
    Args:
        error_code: 错误码 (如 'WECHAT_NOT_START')
    
    Returns:
        异常类
    """
    return ERROR_CODE_MAP.get(error_code, WeChatError)


# 导出所有异常
__all__ = [
    # 基础
    'WeChatError',
    'ElementNotFoundError',
    'TimeoutError',
    'NoPatternInterfaceError',
    # 连接
    'WeChatNotStartError',
    'NetWorkNotConnectError',
    'ScanCodeToLogInError',
    # 文件
    'EmptyFileError',
    'EmptyFolderError',
    'NotFileError',
    'NotFolderError',
    # 好友/群聊
    'NoSuchFriendError',
    'NotFriendError',
    'NoGroupsError',
    'CantCreateGroupError',
    'NoChatsError',
    # 公众号
    'NotInstalledError',
    'NoSubOffAccError',
    # 企业微信
    'NoWecomFriendsError',
    # 权限
    'NoPermissionError',
    # 聊天记录
    'NoChatHistoryError',
    # 时间
    'TimeNotCorrectError',
    # 拍一拍
    'TickleError',
    # 搜索
    'NoResultsError',
    # 工具
    'ERROR_CODE_MAP',
    'get_error_by_code',
]