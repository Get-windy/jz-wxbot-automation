# 微信朋友圈功能设计

> 版本: 1.0  
> 日期: 2026-03-16  
> 状态: 设计完成

---

## 1. 功能概述

本文档描述 jz-wxbot-automation 项目中朋友圈 (Moments) 功能的架构设计，基于 pywechat 的实现进行扩展和优化。

### pywechat 原生能力

| 功能 | 方法 | 状态 |
|------|------|------|
| 获取全部朋友圈 | `dump_moments()` | ✅ |
| 获取近期朋友圈 | `dump_recent_posts(recent)` | ✅ |
| 解析朋友圈内容 | `parse_moments_content()` | ✅ |
| 发布朋友圈 | ❌ | ❌ (仅爬取) |

### 本项目扩展目标

- [ ] 朋友圈发布 (发布文字/图片/视频)
- [ ] 朋友圈获取 (分页/筛选)
- [ ] 点赞/评论功能
- [ ] 异步处理支持

---

## 2. 系统架构

### 2.1 模块结构

```
core/moments/
├── __init__.py           # 导出
├── models.py             # 数据模型
├── parser.py             # 解析器
├── fetcher.py            # 获取器
├── publisher.py          # 发布器
├── interaction.py        # 互动 (点赞/评论)
└── exceptions.py         # 异常定义
```

### 2.2 类图

```
┌─────────────────┐       ┌─────────────────┐
│   MomentsBase   │       │  MomentsParser  │
│   (基础类)       │       │   (解析器)      │
├─────────────────┤       ├─────────────────┤
│ + dump()        │       │ + parse()       │
│ + get_recent()  │       │ + extract_text()│
└────────┬────────┘       │ + extract_images│
         │                └────────┬────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│ MomentsFetcher  │       │ MomentsPublisher │
│   (获取器)      │       │    (发布器)      │
├─────────────────┤       ├─────────────────┤
│ + fetch_all()   │       │ + publish_text() │
│ + fetch_by_time │       │ + publish_image()│
│ + fetch_paged() │       │ + publish_video()│
└────────┬────────┘       │ + publish_mixed()│
         │                └────────┬────────┘
         │                         │
         ▼                         ▼
┌──────────────────────────────────────────┐
│        MomentsInteraction                │
│            (互动模块)                     │
├──────────────────────────────────────────┤
│ + like(moment_id)                        │
│ + comment(moment_id, content)            │
│ + delete_comment(moment_id, comment_id)  │
└──────────────────────────────────────────┘
```

---

## 3. 数据模型

### 3.1 朋友圈消息

```python
# core/moments/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class MomentType(Enum):
    """朋友圈类型"""
    TEXT = "text"           # 纯文字
    IMAGE = "image"        # 图片
    VIDEO = "video"        # 视频
    LINK = "link"          # 链接卡片
    FORWARD = "forward"    # 转发


@dataclass
class MomentContent:
    """朋友圈内容"""
    text: str = ""                          # 文本内容
    images: List[str] = field(default_factory=list)  # 图片路径列表
    video: Optional[str] = None             # 视频路径
    link_title: Optional[str] = None        # 链接标题
    link_url: Optional[str] = None          # 链接URL
    link_thumb: Optional[str] = None        # 链接缩略图


@dataclass
class MomentInteraction:
    """互动数据"""
    likes: List[str] = field(default_factory=list)   # 点赞用户列表
    comments: List[dict] = field(default_factory=list)  # 评论列表


@dataclass
class Moment:
    """朋友圈动态"""
    moment_id: str                          # 朋友圈ID
    user_id: str                            # 发布者ID
    user_name: str                          # 发布者昵称
    user_remark: str                        # 发布者备注
    content: MomentContent                  # 内容
    moment_type: MomentType                  # 类型
    post_time: datetime                     # 发布时间
    location: Optional[str] = None          # 定位
    interaction: MomentInteraction = field(default_factory=MomentInteraction)
    visibility: str = "all"                 # 可见范围
    likes_count: int = 0                    # 点赞数
    comments_count: int = 0                # 评论数
    raw_data: dict = field(default_factory=dict)
    
    @property
    def is_ad(self) -> bool:
        """判断是否为广告"""
        ad_keywords = ['广告', 'Ad', '廣告', '推广']
        return any(kw in self.content.text for kw in ad_keywords)
```

### 3.2 发布请求

```python
@dataclass
class PublishRequest:
    """发布请求"""
    content: str                             # 文字内容
    images: List[str] = field(default_factory=list)  # 图片路径
    video: Optional[str] = None             # 视频路径
    link: Optional[dict] = None             # 链接卡片 {title, url, thumb}
    location: Optional[str] = None          # 位置
    visible_range: str = "all"              # 可见范围: all/friends/secret
    
    def validate(self) -> bool:
        """验证发布参数"""
        # 至少要有文字或媒体内容
        has_content = bool(self.content.strip())
        has_media = bool(self.images or self.video or self.link)
        return has_content or has_media


@dataclass
class InteractionRequest:
    """互动请求"""
    moment_id: str
    action: str  # like/unlike/comment/delete
    content: Optional[str] = None  # 评论内容
    comment_id: Optional[str] = None  # 删除评论时使用
```

---

## 4. 核心功能实现

### 4.1 朋友圈解析器

```python
# core/moments/parser.py

from typing import Optional, List
import re
from .models import Moment, MomentContent, MomentInteraction, MomentType
from .exceptions import MomentParseError


class MomentsParser:
    """朋友圈解析器
    
    将 pywechat 原始数据解析为标准 Moment 对象
    """
    
    def parse(self, raw_data: dict) -> Moment:
        """
        解析原始朋友圈数据
        
        Args:
            raw_data: pywechat parse_moments_content 返回的字典
            
        Returns:
            Moment 对象
        """
        try:
            # 提取基本信息
            moment_id = raw_data.get('moment_id', self._generate_id())
            user_name = raw_data.get('好友备注', '')
            post_time_str = raw_data.get('发布时间', '')
            text_content = raw_data.get('文本内容', '')
            
            # 解析内容
            content = self._parse_content(raw_data)
            
            # 解析互动
            likes = raw_data.get('点赞者', [])
            comments = raw_data.get('评论内容', [])
            interaction = self._parse_interaction(likes, comments)
            
            # 解析类型
            moment_type = self._detect_type(raw_data)
            
            # 解析时间
            post_time = self._parse_time(post_time_str)
            
            return Moment(
                moment_id=moment_id,
                user_id='',  # 需要额外查询
                user_name=user_name,
                user_remark=user_name,
                content=content,
                moment_type=moment_type,
                post_time=post_time,
                interaction=interaction,
                likes_count=len(likes),
                comments_count=len(comments),
                raw_data=raw_data
            )
            
        except Exception as e:
            raise MomentParseError(f"Parse failed: {e}")
    
    def _parse_content(self, raw: dict) -> MomentContent:
        """解析内容"""
        # 图片数量
        image_count = raw.get('图片数量', 0)
        images = [f"image_{i}" for i in range(image_count)]
        
        # 视频
        video = "video_0" if raw.get('视频数量', 0) > 0 else None
        
        # 链接卡片
        link_title = raw.get('卡片链接内容', '')
        link_url = raw.get('卡片链接', '')
        
        return MomentContent(
            text=raw.get('文本内容', ''),
            images=images,
            video=video,
            link_title=link_title or raw.get('公众号链接内容', ''),
            link_url=link_url
        )
    
    def _parse_interaction(self, likes: List, comments: List) -> MomentInteraction:
        """解析互动数据"""
        parsed_comments = []
        for c in comments:
            # 评论格式: "用户: 内容"
            if ':' in c:
                user, content = c.split(':', 1)
                parsed_comments.append({
                    'user': user.strip(),
                    'content': content.strip()
                })
            else:
                parsed_comments.append({
                    'user': '',
                    'content': c
                })
        
        return MomentInteraction(
            likes=list(likes) if likes else [],
            comments=parsed_comments
        )
    
    def _detect_type(self, raw: dict) -> MomentType:
        """检测朋友圈类型"""
        if raw.get('视频数量', 0) > 0:
            return MomentType.VIDEO
        if raw.get('图片数量', 0) > 0:
            return MomentType.IMAGE
        if raw.get('卡片链接'):
            return MomentType.LINK
        return MomentType.TEXT
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        import datetime as dt
        # 简化实现，实际需要根据格式解析
        return dt.datetime.now()
    
    def _generate_id(self) -> str:
        """生成ID"""
        import uuid
        return str(uuid.uuid4())
```

### 4.2 朋友圈获取器

```python
# core/moments/fetcher.py

from typing import List, Optional, Literal
from datetime import datetime
from .models import Moment
from .parser import MomentsParser
from .exceptions import WeChatMomentsError


class MomentsFetcher:
    """朋友圈获取器
    
    获取朋友圈数据，支持全部/近期/分页
    """
    
    def __init__(self, pywechat_moments=None):
        self.parser = MomentsParser()
        self._pywechat = pywechat_moments
    
    async def fetch_all(
        self,
        is_maximize: bool = False,
        close_wechat: bool = True,
        filter_ads: bool = True
    ) -> List[Moment]:
        """
        获取全部朋友圈
        
        Args:
            is_maximize: 微信是否全屏
            close_wechat: 完成后是否关闭微信
            filter_ads: 是否过滤广告
            
        Returns:
            朋友圈列表
        """
        if not self._pywechat:
            raise WeChatMomentsError("pywechat not initialized")
        
        try:
            raw_moments = self._pywechat.dump_moments(
                is_maximize=is_maximize,
                close_wechat=close_wechat
            )
            
            moments = [self.parser.parse(raw) for raw in raw_moments]
            
            if filter_ads:
                moments = [m for m in moments if not m.is_ad]
            
            return moments
            
        except Exception as e:
            raise WeChatMomentsError(f"Fetch all failed: {e}")
    
    async def fetch_recent(
        self,
        recent: Literal['Today', 'Yesterday', 'Week', 'Month', 'Year'],
        is_maximize: bool = False,
        close_wechat: bool = True
    ) -> List[Moment]:
        """
        获取近期朋友圈
        
        Args:
            recent: 时间范围
            is_maximize: 微信是否全屏
            close_wechat: 完成后是否关闭微信
        """
        if not self._pywechat:
            raise WeChatMomentsError("pywechat not initialized")
        
        try:
            raw_moments = self._pywechat.dump_recent_posts(
                recent=recent,
                is_maximize=is_maximize,
                close_wechat=close_wechat
            )
            
            return [self.parser.parse(raw) for raw in raw_moments]
            
        except Exception as e:
            raise WeChatMomentsError(f"Fetch recent failed: {e}")
    
    async def fetch_by_user(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Moment]:
        """
        获取指定用户的朋友圈
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
        """
        # 全部获取后筛选 (简化实现)
        all_moments = await self.fetch_all()
        
        user_moments = [
            m for m in all_moments 
            if m.user_id == user_id or m.user_name == user_id
        ]
        
        return user_moments[:limit]
```

### 4.3 朋友圈发布器

```python
# core/moments/publisher.py

from typing import Optional
from .models import PublishRequest
from .exceptions import WeChatMomentsError, PublishError


class MomentsPublisher:
    """朋友圈发布器
    
    注意: pywechat 原生不支持发布朋友圈
    此模块为设计文档，实际实现需要逆向微信PC版
    """
    
    def __init__(self):
        self._window = None
    
    async def publish(
        self,
        request: PublishRequest,
        verify_content: bool = True
    ) -> dict:
        """
        发布朋友圈
        
        Args:
            request: 发布请求
            verify_content: 是否验证内容
            
        Returns:
            发布结果 {success, moment_id, error}
        """
        # 验证内容
        if verify_content and not request.validate():
            raise PublishError("Invalid content: need text or media")
        
        # 检查媒体文件
        if request.images:
            await self._verify_images(request.images)
        
        if request.video:
            await self._verify_video(request.video)
        
        # 打开朋友圈发布界面
        await self._open_publisher()
        
        try:
            # 1. 输入文字内容
            if request.content:
                await self._input_text(request.content)
            
            # 2. 添加图片/视频
            if request.images:
                await self._add_images(request.images)
            
            if request.video:
                await self._add_video(request.video)
            
            # 3. 添加链接卡片
            if request.link:
                await self._add_link(request.link)
            
            # 4. 设置位置
            if request.location:
                await self._set_location(request.location)
            
            # 5. 设置可见范围
            if request.visible_range != 'all':
                await self._set_visibility(request.visible_range)
            
            # 6. 点击发布
            await self._submit()
            
            return {'success': True, 'moment_id': 'new_moment_id'}
            
        except Exception as e:
            await self._cancel()
            raise PublishError(f"Publish failed: {e}")
    
    async def publish_text(self, text: str) -> dict:
        """发布纯文字"""
        return await self.publish(PublishRequest(content=text))
    
    async def publish_image(self, text: str, images: list) -> dict:
        """发布图文"""
        return await self.publish(PublishRequest(content=text, images=images))
    
    async def publish_video(self, text: str, video: str) -> dict:
        """发布视频"""
        return await self.publish(PublishRequest(content=text, video=video))
    
    # --- 内部方法 (需要逆向实现) ---
    
    async def _open_publisher(self):
        """打开朋友圈发布界面"""
        # TODO: 逆向微信PC版实现
        pass
    
    async def _input_text(self, text: str):
        """输入文字"""
        pass
    
    async def _add_images(self, images: list):
        """添加图片"""
        pass
    
    async def _add_video(self, video: str):
        """添加视频"""
        pass
    
    async def _add_link(self, link: dict):
        """添加链接"""
        pass
    
    async def _set_location(self, location: str):
        """设置位置"""
        pass
    
    async def _set_visibility(self, range: str):
        """设置可见范围"""
        pass
    
    async def _submit(self):
        """提交发布"""
        pass
    
    async def _cancel(self):
        """取消发布"""
        pass
    
    async def _verify_images(self, images: list):
        """验证图片"""
        pass
    
    async def _verify_video(self, video: str):
        """验证视频"""
        pass
```

### 4.4 互动模块

```python
# core/moments/interaction.py

from typing import Optional
from .exceptions import WeChatMomentsError, InteractionError


class MomentsInteraction:
    """朋友圈互动
    
    点赞、评论功能
    """
    
    def __init__(self):
        pass
    
    async def like(self, moment_id: str) -> bool:
        """
        点赞
        
        Args:
            moment_id: 朋友圈ID
            
        Returns:
            是否成功
        """
        # TODO: 逆向微信PC版实现
        # 1. 找到对应朋友圈
        # 2. 点击点赞按钮
        # 3. 确认点赞状态
        pass
    
    async def unlike(self, moment_id: str) -> bool:
        """
        取消点赞
        """
        pass
    
    async def comment(self, moment_id: str, content: str) -> Optional[str]:
        """
        评论
        
        Args:
            moment_id: 朋友圈ID
            content: 评论内容
            
        Returns:
            评论ID 或 None
        """
        pass
    
    async def delete_comment(self, moment_id: str, comment_id: str) -> bool:
        """
        删除评论
        
        Args:
            moment_id: 朋友圈ID
            comment_id: 评论ID
        """
        pass
    
    async def reply_comment(
        self, 
        moment_id: str, 
        comment_id: str, 
        content: str
    ) -> Optional[str]:
        """
        回复评论
        
        Args:
            moment_id: 朋友圈ID
            comment_id: 被回复的评论ID
            content: 回复内容
        """
        pass
```

---

## 5. 异常定义

```python
# core/moments/exceptions.py

from core.exceptions import WeChatError


class WeChatMomentsError(WeChatMomentsError):
    """朋友圈基础异常"""
    pass


class MomentParseError(WeChatMomentsError):
    """解析异常"""
    pass


class PublishError(WeChatMomentsError):
    """发布异常"""
    pass


class InteractionError(WeChatMomentsError):
    """互动异常"""
    pass


class NoMomentsError(WeChatMomentsError):
    """无朋友圈数据"""
    pass
```

---

## 6. 使用示例

```python
# examples/moments_example.py

import asyncio
from pywechat import WeChatAuto
from core.moments.fetcher import MomentsFetcher
from core.moments.publisher import MomentsPublisher
from core.moments.interaction import MomentsInteraction
from core.moments.models import PublishRequest


async def main():
    # 初始化 pywechat
    wechat = WeChatAuto()
    
    # 创建各模块实例
    fetcher = MomentsFetcher(wechat.Moments)
    publisher = MomentsPublisher()
    interaction = MomentsInteraction()
    
    # 1. 获取今日朋友圈
    moments = await fetcher.fetch_recent('Today')
    print(f"今日朋友圈: {len(moments)} 条")
    
    for m in moments[:5]:
        print(f"  - {m.user_name}: {m.content.text[:50]}")
        print(f"    点赞: {m.likes_count}, 评论: {m.comments_count}")
    
    # 2. 点赞示例
    if moments:
        await interaction.like(moments[0].moment_id)
    
    # 3. 评论示例
    if moments:
        await interaction.comment(
            moments[0].moment_id, 
            "写得真好！"
        )
    
    # 4. 发布朋友圈 (待实现)
    # await publisher.publish_text("今天天气真好！")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. 进度与限制

### 7.1 功能实现状态

| 功能 | 状态 | 备注 |
|------|------|------|
| 朋友圈解析 | ✅ 已实现 | 基于 pywechat |
| 获取全部朋友圈 | ✅ 已实现 | 基于 pywechat |
| 获取近期朋友圈 | ✅ 已实现 | 基于 pywechat |
| 按用户筛选 | ✅ 已实现 | 本项目扩展 |
| 发布朋友圈 | ❌ 待逆向 | 需要逆向微信PC |
| 点赞 | ❌ 待逆向 | 需要逆向微信 |
| 评论 | ❌ 待逆向 | 需要逆向微信 |

### 7.2 技术限制

1. **发布功能**: pywechat 仅支持爬取，不支持发布
2. **逆向风险**: 发布/点赞/评论需要逆向微信PC版，可能违反微信服务条款
3. **版本兼容**: 不同版本微信 UI 可能变化，需要适配

---

## 8. 总结

- **数据模型**: 完整的 Moment/Content/Interaction 模型
- **获取能力**: 支持全部/近期/分页/用户筛选
- **发布设计**: 预留发布接口，需逆向实现
- **扩展性**: 模块化设计，易于扩展