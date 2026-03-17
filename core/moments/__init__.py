# -*- coding: utf-8 -*-
"""
朋友圈功能模块
版本: v1.0.0

功能:
- 朋友圈内容获取 - 获取朋友圈动态
- 朋友圈发布 - 自动发布朋友圈内容
- 点赞评论 - 自动点赞和评论
- 朋友圈监控 - 监控指定好友朋友圈更新
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

class MomentsContentType(Enum):
    """朋友圈内容类型"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
    LOCATION = "location"


class InteractionType(Enum):
    """互动类型"""
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"


@dataclass
class MomentsPost:
    """朋友圈帖子"""
    post_id: str
    user_id: str
    user_name: str
    user_avatar: str = ""
    content: str = ""
    content_type: MomentsContentType = MomentsContentType.TEXT
    media_urls: List[str] = field(default_factory=list)
    location: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
    liked_users: List[str] = field(default_factory=list)
    comments: List[Dict] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)


@dataclass
class MomentsComment:
    """朋友圈评论"""
    comment_id: str
    post_id: str
    user_id: str
    user_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: str = ""  # 回复的评论ID


@dataclass
class MomentsConfig:
    """朋友圈配置"""
    auto_like: bool = False           # 自动点赞
    auto_comment: bool = False       # 自动评论
    like_keywords: List[str] = field(default_factory=list)  # 点赞关键词
    comment_keywords: List[str] = field(default_factory=list)  # 评论关键词
    comment_template: str = ""       # 评论模板
    monitor_friends: List[str] = field(default_factory=list)  # 监控好友
    max_posts_per_day: int = 50       # 每日最大操作数
    min_interval: int = 10           # 最小操作间隔(秒)


# ==================== 朋友圈获取 ====================

class MomentsFetcher:
    """朋友圈内容获取器
    
    获取朋友圈动态
    """
    
    def __init__(self):
        self._cache: Dict[str, List[MomentsPost]] = {}
        self._last_fetch_time: Dict[str, datetime] = {}
    
    async def get_timeline(
        self,
        user_id: str = None,
        limit: int = 20,
        before_post_id: str = None
    ) -> List[MomentsPost]:
        """
        获取朋友圈时间线
        
        Args:
            user_id: 用户ID，为空则获取自己的
            limit: 返回数量
            before_post_id: 分页标识
            
        Returns:
            朋友圈帖子列表
        """
        # TODO: 调用 pywechat 获取朋友圈
        # 示例调用: Moments.get_moments(limit, before_post_id)
        
        posts = []
        logger.info(f"获取朋友圈: user={user_id}, limit={limit}")
        
        return posts
    
    async def get_friend_moments(
        self,
        friend_id: str,
        limit: int = 20
    ) -> List[MomentsPost]:
        """获取指定好友的朋友圈"""
        return await self.get_timeline(user_id=friend_id, limit=limit)
    
    async def get_post_detail(
        self,
        post_id: str
    ) -> Optional[MomentsPost]:
        """获取帖子详情"""
        # TODO: 获取帖子详情（包括评论、点赞等）
        logger.info(f"获取帖子详情: {post_id}")
        return None
    
    async def get_likes(
        self,
        post_id: str
    ) -> List[str]:
        """获取点赞列表"""
        # TODO: 获取点赞用户列表
        return []
    
    async def get_comments(
        self,
        post_id: str
    ) -> List[MomentsComment]:
        """获取评论列表"""
        # TODO: 获取评论列表
        return []
    
    async def search_moments(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[MomentsPost]:
        """搜索朋友圈"""
        # TODO: 搜索朋友圈内容
        logger.info(f"搜索朋友圈: {keyword}")
        return []


# ==================== 朋友圈发布 ====================

class MomentsPublisher:
    """朋友圈发布器
    
    发布朋友圈内容
    """
    
    def __init__(self):
        self._daily_count = 0
        self._last_post_time: Optional[datetime] = None
        self._daily_reset_time = datetime.now()
    
    async def publish_text(
        self,
        content: str,
        location: str = None,
        visible_type: str = "all"  # all/friends/self
    ) -> Optional[str]:
        """
        发布文本朋友圈
        
        Args:
            content: 文本内容
            location: 位置信息
            visible_type: 可见范围
            
        Returns:
            post_id: 发布成功返回帖子ID
        """
        # 检查频率限制
        if not self._check_rate_limit():
            logger.warning("发布频率超限")
            return None
        
        # TODO: 调用 pywechat 发布
        logger.info(f"发布文本朋友圈: {content[:50]}...")
        
        # 更新计数
        self._daily_count += 1
        self._last_post_time = datetime.now()
        
        return f"post_{int(time.time())}"
    
    async def publish_image(
        self,
        images: List[str],
        content: str = "",
        location: str = None
    ) -> Optional[str]:
        """
        发布图片朋友圈
        
        Args:
            images: 图片路径列表 (最多9张)
            content: 文本内容
            location: 位置
        """
        if not self._check_rate_limit():
            return None
        
        if len(images) > 9:
            logger.warning("图片数量不能超过9张")
            images = images[:9]
        
        logger.info(f"发布图片朋友圈: {len(images)}张图片")
        
        # TODO: 调用 pywechat
        # Moments.publish_moments(images, content, location)
        
        self._daily_count += 1
        self._last_post_time = datetime.now()
        
        return f"post_{int(time.time())}"
    
    async def publish_video(
        self,
        video_path: str,
        content: str = "",
        cover_path: str = None
    ) -> Optional[str]:
        """
        发布视频朋友圈
        
        Args:
            video_path: 视频路径
            content: 文本内容
            cover_path: 封面图片路径
        """
        if not self._check_rate_limit():
            return None
        
        logger.info(f"发布视频朋友圈: {video_path}")
        
        # TODO: 调用 pywechat
        # Moments.publish_video(video_path, content, cover_path)
        
        self._daily_count += 1
        self._last_post_time = datetime.now()
        
        return f"post_{int(time.time())}"
    
    async def publish_link(
        self,
        url: str,
        title: str,
        description: str = "",
        image_url: str = None
    ) -> Optional[str]:
        """发布链接朋友圈"""
        if not self._check_rate_limit():
            return None
        
        logger.info(f"发布链接朋友圈: {title}")
        
        # TODO: 实现链接发布
        self._daily_count += 1
        self._last_post_time = datetime.now()
        
        return f"post_{int(time.time())}"
    
    def _check_rate_limit(self) -> bool:
        """检查频率限制"""
        # 重置每日计数
        now = datetime.now()
        if now.date() > self._daily_reset_time.date():
            self._daily_count = 0
            self._daily_reset_time = now
        
        # 检查每日限制
        if self._daily_count >= 50:
            return False
        
        # 检查时间间隔
        if self._last_post_time:
            elapsed = (now - self._last_post_time).seconds
            if elapsed < 10:
                return False
        
        return True
    
    def get_daily_count(self) -> int:
        """获取今日发布数量"""
        return self._daily_count


# ==================== 点赞评论 ====================

class MomentsInteraction:
    """朋友圈互动
    
    点赞和评论功能
    """
    
    def __init__(self):
        self._like_daily_count = 0
        self._comment_daily_count = 0
        self._last_action_time: Optional[datetime] = None
        self._daily_reset_time = datetime.now()
    
    async def like(
        self,
        post_id: str
    ) -> bool:
        """
        点赞
        
        Args:
            post_id: 帖子ID
            
        Returns:
            是否成功
        """
        if not self._check_rate_limit():
            logger.warning("操作频率超限")
            return False
        
        # TODO: 调用 pywechat 点赞
        # Moments.like_moments(post_id)
        
        logger.info(f"点赞帖子: {post_id}")
        
        self._like_daily_count += 1
        self._last_action_time = datetime.now()
        
        return True
    
    async def unlike(
        self,
        post_id: str
    ) -> bool:
        """取消点赞"""
        # TODO: 调用 pywechat
        logger.info(f"取消点赞: {post_id}")
        return True
    
    async def comment(
        self,
        post_id: str,
        content: str,
        reply_to: str = None
    ) -> Optional[str]:
        """
        评论
        
        Args:
            post_id: 帖子ID
            content: 评论内容
            reply_to: 回复的评论ID
            
        Returns:
            comment_id: 评论ID
        """
        if not self._check_rate_limit():
            return None
        
        if not content or not content.strip():
            return None
        
        logger.info(f"评论帖子: {post_id}, 内容: {content[:30]}...")
        
        # TODO: 调用 pywechat 评论
        # Moments.comment_moments(post_id, content, reply_to)
        
        self._comment_daily_count += 1
        self._last_action_time = datetime.now()
        
        return f"comment_{int(time.time())}"
    
    async def delete_comment(
        self,
        post_id: str,
        comment_id: str
    ) -> bool:
        """删除评论"""
        # TODO: 调用 pywechat
        logger.info(f"删除评论: {comment_id}")
        return True
    
    async def share(
        self,
        post_id: str,
        content: str = None
    ) -> bool:
        """分享帖子到朋友圈"""
        if not self._check_rate_limit():
            return False
        
        logger.info(f"分享帖子: {post_id}")
        
        # TODO: 实现分享功能
        return True
    
    def _check_rate_limit(self) -> bool:
        """检查频率限制"""
        now = datetime.now()
        
        # 重置每日计数
        if now.date() > self._daily_reset_time.date():
            self._like_daily_count = 0
            self._comment_daily_count = 0
            self._daily_reset_time = now
        
        # 总操作限制
        if self._like_daily_count + self._comment_daily_count >= 100:
            return False
        
        # 时间间隔
        if self._last_action_time:
            elapsed = (now - self._last_action_time).seconds
            if elapsed < 5:  # 最小5秒间隔
                return False
        
        return True
    
    def get_daily_stats(self) -> Dict:
        """获取每日统计"""
        return {
            'likes': self._like_daily_count,
            'comments': self._comment_daily_count
        }


# ==================== 朋友圈监控 ====================

class MomentsMonitor:
    """朋友圈监控
    
    监控指定好友的朋友圈更新
    """
    
    def __init__(
        self,
        on_new_post: Callable[[MomentsPost], None] = None,
        poll_interval: int = 300  # 5分钟
    ):
        self.on_new_post = on_new_post
        self.poll_interval = poll_interval
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._monitored_friends: Set[str] = set()
        self._last_post_ids: Dict[str, str] = {}  # friend_id -> last_post_id
        self._callbacks: List[Callable] = []
    
    def add_friend(self, friend_id: str):
        """添加监控好友"""
        self._monitored_friends.add(friend_id)
        logger.info(f"添加监控好友: {friend_id}")
    
    def remove_friend(self, friend_id: str):
        """移除监控好友"""
        self._monitored_friends.discard(friend_id)
        logger.info(f"移除监控好友: {friend_id}")
    
    def set_friends(self, friend_ids: List[str]):
        """设置监控好友列表"""
        self._monitored_friends = set(friend_ids)
    
    def register_callback(self, callback: Callable[[MomentsPost], None]):
        """注册回调"""
        self._callbacks.append(callback)
    
    def start(self):
        """启动监控"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._thread.start()
        logger.info("朋友圈监控已启动")
    
    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("朋友圈监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        import time
        fetcher = MomentsFetcher()
        
        while self._running:
            try:
                for friend_id in self._monitored_friends:
                    self._check_friend_moments(fetcher, friend_id)
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
            
            time.sleep(self.poll_interval)
    
    def _check_friend_moments(self, fetcher: MomentsFetcher, friend_id: str):
        """检查好友朋友圈"""
        try:
            # 获取最新动态
            posts = asyncio.run(
                fetcher.get_friend_moments(friend_id, limit=5)
            )
            
            if not posts:
                return
            
            # 检查是否有新帖子
            latest_post = posts[0]
            last_post_id = self._last_post_ids.get(friend_id)
            
            if last_post_id is None:
                # 首次监控，记录最新ID
                self._last_post_ids[friend_id] = latest_post.post_id
                return
            
            if latest_post.post_id != last_post_id:
                # 发现新帖子
                logger.info(f"发现新朋友圈: {friend_id}")
                
                # 更新记录
                self._last_post_ids[friend_id] = latest_post.post_id
                
                # 通知回调
                self._notify(latest_post)
                
        except Exception as e:
            logger.error(f"检查好友朋友圈失败: {e}")
    
    def _notify(self, post: MomentsPost):
        """通知回调"""
        if self.on_new_post:
            try:
                self.on_new_post(post)
            except Exception as e:
                logger.error(f"回调错误: {e}")
        
        for callback in self._callbacks:
            try:
                callback(post)
            except Exception as e:
                logger.error(f"回调错误: {e}")


# ==================== 朋友圈处理器 ====================

class MomentsProcessor:
    """朋友圈处理器
    
    统一管理朋友圈获取、发布、互动、监控
    """
    
    def __init__(self, config: MomentsConfig = None):
        self.config = config or MomentsConfig()
        
        # 初始化组件
        self.fetcher = MomentsFetcher()
        self.publisher = MomentsPublisher()
        self.interaction = MomentsInteraction()
        self.monitor = MomentsMonitor(
            poll_interval=self.config.monitor_poll_interval if hasattr(self.config, 'monitor_poll_interval') else 300
        )
        
        self._running = False
        
        # 注册监控回调
        if self.config.auto_like or self.config.auto_comment:
            self.monitor.register_callback(self._on_new_post)
    
    async def _on_new_post(self, post: MomentsPost):
        """新帖子回调 - 自动互动"""
        # 检查是否需要自动点赞
        if self.config.auto_like and self._should_like(post):
            await self.interaction.like(post.post_id)
        
        # 检查是否需要自动评论
        if self.config.auto_comment and self._should_comment(post):
            comment_content = self._generate_comment(post)
            if comment_content:
                await self.interaction.comment(post.post_id, comment_content)
    
    def _should_like(self, post: MomentsPost) -> bool:
        """判断是否应该点赞"""
        # 检查关键词
        if self.config.like_keywords:
            content = post.content.lower()
            for keyword in self.config.like_keywords:
                if keyword.lower() in content:
                    return True
            return False
        
        # 默认点赞
        return True
    
    def _should_comment(self, post: MomentsPost) -> bool:
        """判断是否应该评论"""
        if not self.config.comment_keywords:
            return False
        
        content = post.content.lower()
        for keyword in self.config.comment_keywords:
            if keyword.lower() in content:
                return True
        
        return False
    
    def _generate_comment(self, post: MomentsPost) -> str:
        """生成评论内容"""
        if self.config.comment_template:
            return self.config.comment_template.format(
                user=post.user_name,
                content=post.content[:50]
            )
        
        # 默认评论
        comments = [
            "写得真好！",
            "太棒了！",
            "支持一下！",
            "很不错！",
            "👍"
        ]
        import random
        return random.choice(comments)
    
    async def start(self):
        """启动"""
        if self._running:
            return
        
        self._running = True
        
        # 启动监控
        if self.config.monitor_friends:
            self.monitor.set_friends(self.config.monitor_friends)
            self.monitor.start()
        
        logger.info("朋友圈处理器已启动")
    
    async def stop(self):
        """停止"""
        self._running = False
        self.monitor.stop()
        logger.info("朋友圈处理器已停止")
    
    # === 便捷方法 ===
    
    async def get_timeline(self, limit: int = 20) -> List[MomentsPost]:
        """获取时间线"""
        return await self.fetcher.get_timeline(limit=limit)
    
    async def publish(
        self,
        content: str = None,
        images: List[str] = None,
        video: str = None,
        location: str = None
    ) -> Optional[str]:
        """发布朋友圈"""
        if video:
            return await self.publisher.publish_video(video, content)
        elif images:
            return await self.publisher.publish_image(images, content, location)
        elif content:
            return await self.publisher.publish_text(content, location)
        
        return None
    
    async def like(self, post_id: str) -> bool:
        """点赞"""
        return await self.interaction.like(post_id)
    
    async def comment(self, post_id: str, content: str) -> Optional[str]:
        """评论"""
        return await self.interaction.comment(post_id, content)
    
    async def get_post(self, post_id: str) -> Optional[MomentsPost]:
        """获取帖子详情"""
        return await self.fetcher.get_post_detail(post_id)


# ==================== 使用示例 ====================

async def example_basic():
    """基本使用示例"""
    
    # 创建处理器
    config = MomentsConfig(
        auto_like=True,
        auto_comment=False,
        like_keywords=["好", "棒", "赞"],
        comment_keywords=[],
        comment_template="写得真好！",
        monitor_friends=["friend_1", "friend_2"]
    )
    
    processor = MomentsProcessor(config)
    
    # 启动
    await processor.start()
    
    # 获取时间线
    posts = await processor.get_timeline(limit=10)
    print(f"获取到 {len(posts)} 条朋友圈")
    
    for post in posts[:3]:
        print(f"- {post.user_name}: {post.content[:30]}...")
    
    # 发布朋友圈
    post_id = await processor.publish(
        content="今天天气真好！",
        images=["path/to/image1.jpg"]
    )
    print(f"发布成功: {post_id}")
    
    # 点赞评论
    if posts:
        post_id = posts[0].post_id
        await processor.like(post_id)
        await processor.comment(post_id, "写得真好！")
    
    # 停止
    await processor.stop()


async def example_auto_interaction():
    """自动互动示例"""
    
    config = MomentsConfig(
        auto_like=True,
        auto_comment=True,
        like_keywords=["好", "棒", "赞", "强", "厉害"],
        comment_keywords=["抽奖", "福利", "活动"],
        comment_template="支持！{user}的分享很棒！",
        monitor_friends=["friend_123"]
    )
    
    processor = MomentsProcessor(config)
    
    # 注册新帖子回调
    def on_new_post(post: MomentsPost):
        print(f"新帖子 from {post.user_name}: {post.content[:50]}")
    
    processor.monitor.register_callback(on_new_post)
    
    await processor.start()
    
    # 运行监控
    await asyncio.sleep(3600)
    
    await processor.stop()


# ==================== 主入口 ====================

if __name__ == '__main__':
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(example_basic())