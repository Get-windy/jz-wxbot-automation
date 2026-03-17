# 好友功能设计

> 版本: 1.0  
> 日期: 2026-03-16  
> 状态: 设计完成

---

## 1. 功能概述

本文档描述 jz-wxbot-automation 项目中好友添加/管理功能的架构设计。

### pywechat 现有能力

| 功能 | 方法 | 状态 |
|------|------|------|
| 添加新朋友 | `add_new_friend()` | ✅ |
| 删除好友 | `delete_friend()` | ✅ |
| 好友置顶 | `pin_friend()` | ✅ |
| 消息免打扰 | `mute_notification()` | ✅ |
| 修改备注 | `change_friend_remark()` | ✅ |
| 修改标签 | `change_friend_tag()` | ✅ |
| 修改描述 | `change_friend_description()` | ✅ |
| 修改电话 | `change_phoneNum()` | ✅ |
| 黑名单 | `add_to_blacklist()` | ✅ |
| 好友请求处理 | ❌ | ❌ (需扩展) |

---

## 2. 系统架构

### 2.1 模块结构

```
core/friends/
├── __init__.py              # 导出
├── models.py                # 数据模型
├── manager.py               # 好友管理器
├── search.py                # 好友搜索
├── auto_add.py              # 自动添加
├── request_handler.py       # 请求处理
├── watcher.py               # 请求监听
└── exceptions.py            # 异常定义
```

### 2.2 功能流

```
┌─────────────────────────────────────────────────────────────┐
│                     好友功能架构                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   搜索      │───▶│   添加      │───▶│   管理      │
│  Search     │    │   Add       │    │   Manage    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 微信ID搜索   │    │ 发送请求    │    │ 置顶/免打扰  │
│ 雷达加好友   │    │ 验证消息    │    │ 备注/标签   │
│ 群成员添加   │    │ 频率控制    │    │ 黑名单      │
└─────────────┘    └─────────────┘    └─────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    请求监听 (新增)                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   监听      │───▶│   解析      │───▶│   处理      │
│   Watch     │    │   Parse     │    │   Handle    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 新好友请求   │    │ 提取信息    │    │ 自动同意    │
│ 通知检测    │    │ 来源/验证   │    │ 拒绝/自定义 │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 3. 数据模型

### 3.1 好友信息模型

```python
# core/friends/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class FriendSource(Enum):
    """好友来源"""
    SEARCH = "search"           # 搜索微信号
    RADAR = "radar"             # 雷达加好友
    GROUP = "group"             # 群聊添加
    QR_CODE = "qr_code"         # 扫码
    PHONE = "phone"             # 手机通讯录
    FRIEND_RECOMMEND = "friend_recommend"  # 好友推荐
    THREE_PARTY = "three_party" # 第三方推送
    UNKNOWN = "unknown"


class FriendStatus(Enum):
    """好友状态"""
    NONE = "none"               # 无关系
    PENDING = "pending"         # 待验证
    ADDED = "added"             # 已添加
    DELETED = "deleted"         # 已删除
    BLACKLISTED = "blacklisted" # 黑名单


class RequestAction(Enum):
    """请求处理动作"""
    ACCEPT = "accept"           # 同意
    REJECT = "reject"           # 拒绝
    IGNORE = "ignore"           # 忽略
    AUTO = "auto"               # 自动处理


@dataclass
class FriendInfo:
    """好友信息"""
    user_id: str                # 用户ID
    nickname: str               # 昵称
    remark: Optional[str] = None  # 备注
    wechat_id: str              # 微信号
    avatar: Optional[str] = None  # 头像URL
    gender: str = "unknown"    # 性别
    province: Optional[str] = None  # 省份
    city: Optional[str] = None  # 城市
    source: FriendSource = FriendSource.UNKNOWN
    status: FriendStatus = FriendStatus.NONE
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None  # 描述
    phone: Optional[str] = None  # 电话
    added_at: Optional[datetime] = None
    last_interaction: Optional[datetime] = None


@dataclass
class FriendRequest:
    """好友请求"""
    request_id: str              # 请求ID
    from_user_id: str           # 请求者ID
    from_nickname: str          # 请求者昵称
    from_remark: Optional[str] = None  # 请求者备注
    from_wechat_id: str         # 请求者微信号
    source: FriendSource = FriendSource.UNKNOWN
    verify_content: Optional[str] = None  # 验证消息
    avatar: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: dict = field(default_factory=dict)
    
    @property
    def display_name(self) -> str:
        return self.from_remark or self.from_nickname


@dataclass
class AutoAddConfig:
    """自动添加配置"""
    enabled: bool = False
    # 关键词过滤
    keywords_allow: List[str] = field(default_factory=list)  # 允许的关键词
    keywords_deny: List[str] = field(default_factory=list)  # 拒绝的关键词
    # 来源过滤
    sources_allow: List[FriendSource] = field(default_factory=list)  # 允许的来源
    # 数量限制
    max_daily: int = 20          # 每日最大添加数
    min_interval: int = 60       # 最小间隔(秒)
    # 验证消息
    auto_accept: bool = False    # 自动同意
    auto_reply: Optional[str] = None  # 自动回复消息
    # 备注
    auto_remark: bool = False    # 自动备注
    remark_template: str = "来自:{source}"  # 备注模板
    # 标签
    auto_tag: bool = False       # 自动标签
    tags: List[str] = field(default_factory=list)
```

---

## 4. 核心模块

### 4.1 好友管理器

```python
# core/friends/manager.py

from typing import List, Optional, Dict
from datetime import datetime
from .models import FriendInfo, FriendStatus, FriendSource
from .search import FriendSearcher
from .auto_add import AutoAddEngine
from .request_handler import RequestHandler
from .watcher import RequestWatcher


class FriendManager:
    """好友管理器
    
    统一管理好友相关操作
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.searcher = FriendSearcher()
        self.auto_add = AutoAddEngine()
        self.request_handler = RequestHandler()
        self.watcher = RequestWatcher(self.request_handler)
    
    async def add_friend(
        self, 
        wechat_id: str, 
        verify_content: str = None,
        wait_response: bool = True
    ) -> Dict:
        """添加好友
        
        Args:
            wechat_id: 微信号
            verify_content: 验证消息
            wait_response: 是否等待响应
            
        Returns:
            result: 操作结果
        """
        try:
            # 调用 pywechat
            from pywechat.WechatAuto import FriendSettings
            FriendSettings.add_new_friend(
                wechat_number=wechat_id,
                request_content=verify_content
            )
            
            return {
                "success": True,
                "wechat_id": wechat_id,
                "message": "好友请求已发送"
            }
        except Exception as e:
            return {
                "success": False,
                "wechat_id": wechat_id,
                "error": str(e)
            }
    
    async def delete_friend(self, friend: str) -> bool:
        """删除好友"""
        from pywechat.WechatAuto import FriendSettings
        FriendSettings.delete_friend(friend=friend)
        return True
    
    async def update_remark(
        self, 
        friend: str, 
        remark: str
    ) -> bool:
        """修改备注"""
        from pywechat.WechatAuto import FriendSettings
        FriendSettings.change_friend_remark(
            friend=friend,
            remark=remark
        )
        return True
    
    async def update_tag(
        self, 
        friend: str, 
        tag: str,
        clear_all: bool = False
    ) -> bool:
        """修改标签"""
        from pywechat.WechatAuto import FriendSettings
        FriendSettings.change_friend_tag(
            friend=friend,
            tag=tag,
            clear_all=clear_all
        )
        return True
    
    async def set_mute(
        self, 
        friend: str, 
        mute: bool = True
    ) -> bool:
        """设置免打扰"""
        from pywechat.WechatAuto import FriendSettings
        state = "open" if mute else "close"
        FriendSettings.mute_notification(
            friend=friend,
            state=state
        )
        return True
    
    async def set_pin(
        self, 
        friend: str, 
        pin: bool = True
    ) -> bool:
        """设置置顶"""
        from pywechat.WechatAuto import FriendSettings
        state = "open" if pin else "close"
        FriendSettings.pin_friend(
            friend=friend,
            state=state
        )
        return True
    
    async def add_to_blacklist(
        self, 
        friend: str,
        block: bool = True
    ) -> bool:
        """加入/移出黑名单"""
        from pywechat.WechatAuto import FriendSettings
        state = "open" if block else "close"
        FriendSettings.add_to_blacklist(
            friend=friend,
            state=state
        )
        return True
    
    async def search_friend(
        self, 
        keyword: str
    ) -> List[FriendInfo]:
        """搜索好友"""
        return await self.searcher.search(keyword)
    
    def start_watching(self):
        """开始监听好友请求"""
        self.watcher.start()
    
    def stop_watching(self):
        """停止监听"""
        self.watcher.stop()
```

### 4.2 好友搜索

```python
# core/friends/search.py

from typing import List, Optional
from .models import FriendInfo, FriendSource


class FriendSearcher:
    """好友搜索器
    
    通过多种方式搜索好友
    """
    
    async def search(self, keyword: str) -> List[FriendInfo]:
        """搜索好友
        
        Args:
            keyword: 搜索关键词(微信号/昵称/备注)
            
        Returns:
            好友列表
        """
        results = []
        
        # 尝试直接搜索微信号
        if self._is_wechat_id(keyword):
            friend = await self._search_by_wechat_id(keyword)
            if friend:
                results.append(friend)
        
        # 搜索昵称/备注
        if not results:
            results = await self._search_by_nickname(keyword)
        
        return results
    
    async def search_by_wechat_id(self, wechat_id: str) -> Optional[FriendInfo]:
        """通过微信号搜索"""
        return await self._search_by_wechat_id(wechat_id)
    
    async def _search_by_wechat_id(self, wechat_id: str) -> Optional[FriendInfo]:
        """通过微信号搜索实现"""
        try:
            from pywechat.WechatAuto import FriendSettings
            # 尝试打开好友资料页
            # 如果能找到则返回好友信息
            # pywechat 目前没有直接返回搜索结果的方法
            # 这里需要扩展
            return None
        except Exception as e:
            print(f"Search error: {e}")
            return None
    
    async def _search_by_nickname(self, nickname: str) -> List[FriendInfo]:
        """通过昵称搜索"""
        # TODO: 实现昵称搜索
        return []
    
    def _is_wechat_id(self, text: str) -> bool:
        """判断是否为微信号格式"""
        import re
        # 微信号: 6-20位字母数字下划线
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]{5,19}$'
        return bool(re.match(pattern, text))
    
    async def get_friend_info(self, friend: str) -> Optional[FriendInfo]:
        """获取好友详细信息"""
        # TODO: 实现获取好友详情
        return None
```

### 4.3 自动添加引擎

```python
# core/friends/auto_add.py

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from .models import AutoAddConfig, FriendRequest, FriendSource


class AutoAddEngine:
    """自动添加引擎
    
    自动处理好友请求
    """
    
    def __init__(self):
        self.config = AutoAddConfig()
        self._daily_count = 0
        self._last_add_time = None
        self._daily_reset_time = datetime.now()
    
    def set_config(self, config: AutoAddConfig):
        """设置配置"""
        self.config = config
    
    async def should_process(self, request: FriendRequest) -> bool:
        """判断是否应该处理这个请求"""
        # 检查每日限制
        self._check_daily_reset()
        if self._daily_count >= self.config.max_daily:
            return False
        
        # 检查时间间隔
        if self._last_add_time:
            elapsed = (datetime.now() - self._last_add_time).seconds
            if elapsed < self.config.min_interval:
                return False
        
        # 检查关键词
        if not self._check_keywords(request):
            return False
        
        # 检查来源
        if self.config.sources_allow:
            if request.source not in self.config.sources_allow:
                return False
        
        return True
    
    async def process(self, request: FriendRequest) -> str:
        """处理请求
        
        Returns:
            处理动作描述
        """
        if not await self.should_process(request):
            return "skipped: 条件不满足"
        
        # 同意好友请求
        action = await self._accept_request(request)
        
        if action == "accepted":
            self._daily_count += 1
            self._last_add_time = datetime.now()
            
            # 自动回复
            if self.config.auto_reply:
                await self._send_auto_reply(request)
            
            # 自动备注
            if self.config.auto_remark:
                await self._set_auto_remark(request)
            
            # 自动标签
            if self.config.auto_tag:
                await self._set_auto_tag(request)
        
        return action
    
    async def _accept_request(self, request: FriendRequest) -> str:
        """同意请求"""
        # TODO: 调用 pywechat 同意请求
        # 需要扩展 pywechat 来实现
        return "accepted"
    
    async def _send_auto_reply(self, request: FriendRequest) -> bool:
        """发送自动回复"""
        if not self.config.auto_reply:
            return False
        
        # TODO: 发送消息
        return True
    
    async def _set_auto_remark(self, request: FriendRequest) -> bool:
        """设置自动备注"""
        template = self.config.remark_template
        remark = template.format(
            source=request.source.value,
            nickname=request.from_nickname,
            wechat_id=request.from_wechat_id
        )
        
        # TODO: 调用修改备注
        return True
    
    async def _set_auto_tag(self, request: FriendRequest) -> bool:
        """设置自动标签"""
        for tag in self.config.tags:
            # TODO: 调用添加标签
            pass
        return True
    
    def _check_keywords(self, request: FriendRequest) -> bool:
        """检查关键词"""
        content = request.verify_content or ""
        
        # 检查拒绝关键词
        for kw in self.config.keywords_deny:
            if kw.lower() in content.lower():
                return False
        
        # 检查允许关键词 (如果设置了)
        if self.config.keywords_allow:
            for kw in self.config.keywords_allow:
                if kw.lower() in content.lower():
                    return True
            return False
        
        return True
    
    def _check_daily_reset(self):
        """检查并重置每日计数"""
        now = datetime.now()
        if now.date() > self._daily_reset_time.date():
            self._daily_count = 0
            self._daily_reset_time = now
```

### 4.4 请求监听器

```python
# core/friends/watcher.py

import asyncio
from typing import Callable, Optional
from .models import FriendRequest
from .request_handler import RequestHandler


class RequestWatcher:
    """好友请求监听器
    
    监听并检测新的好友请求
    """
    
    def __init__(self, handler: RequestHandler):
        self.handler = handler
        self._running = False
        self._poll_interval = 2.0  # 轮询间隔(秒)
        self._on_request_callback: Optional[Callable] = None
    
    def on_request(self, callback: Callable[[FriendRequest], None]):
        """设置请求回调"""
        self._on_request_callback = callback
    
    async def start(self):
        """启动监听"""
        self._running = True
        while self._running:
            try:
                requests = await self._check_pending_requests()
                for req in requests:
                    # 处理请求
                    result = await self.handler.handle(req)
                    
                    # 触发回调
                    if self._on_request_callback:
                        self._on_request_callback(req, result)
                        
            except Exception as e:
                print(f"Request watcher error: {e}")
            
            await asyncio.sleep(self._poll_interval)
    
    def stop(self):
        """停止监听"""
        self._running = False
    
    async def _check_pending_requests(self) -> list:
        """检查待处理的请求
        
        需要检测:
        1. 微信通知区域的新请求提示
        2. 通讯录中的新好友请求
        """
        # TODO: 实现请求检测
        # 需要检测 UI 元素变化:
        # - 微信左下角/右下角的 "新的朋友" 红点提示
        # - 通讯录中的等待验证好友
        
        # 检测方式:
        # 1. 使用 pywinauto 检测通知区域
        # 2. 检测 "通讯录" -> "新的朋友" 入口
        
        return []
```

### 4.5 请求处理器

```python
# core/friends/request_handler.py

from typing import Optional
from .models import FriendRequest, RequestAction


class RequestHandler:
    """好友请求处理器
    
    处理好友请求的逻辑
    """
    
    def __init__(self):
        self._handlers = []
    
    def register_handler(self, handler: callable):
        """注册自定义处理器"""
        self._handlers.append(handler)
    
    async def handle(self, request: FriendRequest) -> str:
        """处理请求
        
        Args:
            request: 好友请求
            
        Returns:
            处理结果描述
        """
        # 尝试自定义处理器
        for handler in self._handlers:
            result = await handler(request)
            if result:
                return result
        
        # 默认处理: 记录日志，不自动同意
        return await self._default_handle(request)
    
    async def accept(
        self, 
        request: FriendRequest,
        remark: str = None,
        add_to_contact: bool = True
    ) -> bool:
        """同意好友请求
        
        Args:
            request: 好友请求
            remark: 备注
            add_to_contact: 是否添加到通讯录
        """
        # TODO: 实现同意请求
        # 需要:
        # 1. 点击 "同意" 按钮
        # 2. 如果设置了备注，填写备注
        # 3. 点击确定
        return True
    
    async def reject(self, request: FriendRequest, reason: str = None) -> bool:
        """拒绝好友请求
        
        Args:
            request: 好友请求
            reason: 拒绝原因 (可选)
        """
        # TODO: 实现拒绝请求
        return True
    
    async def _default_handle(self, request: FriendRequest) -> str:
        """默认处理逻辑"""
        # 不自动同意，只记录
        print(f"New friend request from {request.display_name}: {request.verify_content}")
        return "pending"
```

---

## 5. 使用示例

### 5.1 基本使用

```python
# examples/add_friend_example.py

import asyncio
from core.friends.manager import FriendManager
from core.friends.models import AutoAddConfig, FriendSource


async def main():
    # 创建好友管理器
    manager = FriendManager()
    
    # 添加好友
    result = await manager.add_friend(
        wechat_id="wxid_example123",
        verify_content="你好，我是XXX"
    )
    print(result)
    
    # 管理好友
    await manager.set_mute("张三", mute=True)
    await manager.set_pin("张三", pin=True)
    await manager.update_remark("张三", "同事-张三")
    await manager.update_tag("张三", "工作")


asyncio.run(main())
```

### 5.2 自动处理请求

```python
# examples/auto_accept_example.py

import asyncio
from core.friends.manager import FriendManager
from core.friends.models import AutoAddConfig, FriendSource


async def main():
    manager = FriendManager()
    
    # 配置自动添加
    config = AutoAddConfig(
        enabled=True,
        keywords_allow=["来自", "合作", "商务"],
        keywords_deny=["兼职", "刷单", "推广"],
        max_daily=20,
        min_interval=30,
        auto_accept=True,
        auto_reply="你好，已通过验证，有事请留言~",
        auto_remark=True,
        remark_template="来自:{source}",
        auto_tag=True,
        tags=["自动添加"]
    )
    
    manager.auto_add.set_config(config)
    
    # 启动监听
    def on_request(request, result):
        print(f"处理请求: {request.display_name}, 结果: {result}")
    
    manager.watcher.on_request(on_request)
    manager.start_watching()
    
    print("开始监听好友请求...")
    await asyncio.sleep(3600)  # 监听1小时


asyncio.run(main())
```

---

## 6. 扩展点

### 6.1 需要扩展 pywechat 的功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 同意好友请求 | 需要找到并点击"同意"按钮 | 高 |
| 拒绝好友请求 | 需要找到并点击"拒绝"按钮 | 高 |
| 获取好友详情 | 从资料页提取详细信息 | 中 |
| 检测新请求 | 监听通知区域的请求提示 | 高 |
| 雷达加好友 | 调用雷达加好友功能 | 低 |

### 6.2 UI 元素需求

```python
# 需要在 Uielements.py 中添加

class Buttons():
    def __init__(self):
        # ... existing buttons ...
        
        # 新增好友请求相关按钮
        self.AcceptFriendButton = {'title': '同意', 'control_type': 'Button'}
        self.RejectFriendButton = {'title': '拒绝', 'control_type': 'Button'}
        self.AddToContactsButton = {'title': '添加到通讯录', 'control_type': 'Button'}
        self.NewFriendsButton = {'title': '新的朋友', 'control_type': 'Button'}
```

---

## 7. 实现状态

| 功能 | 状态 |
|------|------|
| 添加好友 (搜索微信号) | ✅ 已有 |
| 删除好友 | ✅ 已有 |
| 修改备注 | ✅ 已有 |
| 修改标签 | ✅ 已有 |
| 设置免打扰 | ✅ 已有 |
| 设置置顶 | ✅ 已有 |
| 黑名单管理 | ✅ 已有 |
| 好友请求监听 | 🔄 需扩展 |
| 自动同意请求 | 🔄 需扩展 |
| 雷达加好友 | ❌ 不支持 |

---

## 8. 总结

- **现有能力**: pywechat 已支持大部分好友管理功能
- **需扩展**: 好友请求的自动处理需要扩展 UI 自动化
- **架构**: 分离搜索、添加、监听、处理模块，易于扩展
- **安全性**: 添加频率控制，防止被微信检测