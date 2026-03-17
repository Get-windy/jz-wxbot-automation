# -*- coding: utf-8 -*-
"""
朋友圈功能增强模块
版本: v1.0.0
功能: 内容解析、自动互动、朋友圈监控
"""

import re
import time
import threading
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """内容类型"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
    LOCATION = "location"
    MUSIC = "music"
    ARTICLE = "article"
    MIXED = "mixed"


class InteractionType(Enum):
    """互动类型"""
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"


@dataclass
class MomentsUser:
    """朋友圈用户"""
    user_id: str
    nickname: str
    avatar: Optional[str] = None
    is_friend: bool = True
    is_blocked: bool = False
    is_starred: bool = False
    last_update: Optional[datetime] = None
    post_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MomentsPost:
    """朋友圈帖子"""
    post_id: str
    user_id: str
    user_name: str
    content: str
    content_type: ContentType = ContentType.TEXT
    images: List[str] = field(default_factory=list)
    video_url: Optional[str] = None
    link_url: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    likes: List[str] = field(default_factory=list)  # 点赞用户ID列表
    comments: List[Dict] = field(default_factory=list)  # 评论列表
    is_private: bool = False
    is_visible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionRecord:
    """互动记录"""
    post_id: str
    user_id: str
    interaction_type: InteractionType
    content: Optional[str] = None  # 评论内容
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = False
    error_message: Optional[str] = None


class ContentParser:
    """朋友圈内容解析器"""
    
    # 内容模式
    PATTERNS = {
        # URL
        'url': re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+'),
        # @提及
        'mention': re.compile(r'@([^\s@]+)'),
        # 话题
        'hashtag': re.compile(r'#([^#\s]+)#'),
        # 表情
        'emotion': re.compile(r'\[[^\[\]]+\]'),
        # 位置
        'location': re.compile(r'\[位置\]([^\[\]]+)'),
        # 音乐
        'music': re.compile(r'\[音乐\]([^\[\]]+)'),
    }
    
    @classmethod
    def parse_content(cls, content: str) -> Dict[str, Any]:
        """解析内容"""
        result = {
            'urls': cls.PATTERNS['url'].findall(content),
            'mentions': cls.PATTERNS['mention'].findall(content),
            'hashtags': cls.PATTERNS['hashtag'].findall(content),
            'emotions': cls.PATTERNS['emotion'].findall(content),
            'has_location': bool(cls.PATTERNS['location'].search(content)),
            'has_music': bool(cls.PATTERNS['music'].search(content)),
            'word_count': len(content),
            'char_count': len(content.replace(' ', ''))
        }
        
        # 判断内容类型
        if result['urls']:
            result['content_type'] = ContentType.LINK
        elif result['has_location']:
            result['content_type'] = ContentType.LOCATION
        elif result['has_music']:
            result['content_type'] = ContentType.MUSIC
        else:
            result['content_type'] = ContentType.TEXT
        
        return result
    
    @classmethod
    def extract_first_url(cls, content: str) -> Optional[str]:
        """提取第一个URL"""
        match = cls.PATTERNS['url'].search(content)
        return match.group(0) if match else None
    
    @classmethod
    def extract_hashtags(cls, content: str) -> List[str]:
        """提取所有话题"""
        return cls.PATTERNS['hashtag'].findall(content)
    
    @classmethod
    def clean_content(cls, content: str) -> str:
        """清理内容（移除表情等）"""
        cleaned = content
        for pattern in cls.PATTERNS.values():
            cleaned = pattern.sub('', cleaned)
        return cleaned.strip()


class AutoInteraction:
    """自动互动器"""
    
    def __init__(self, 
                 like_probability: float = 0.3,
                 comment_templates: List[str] = None):
        """
        初始化自动互动器
        
        Args:
            like_probability: 点赞概率 (0-1)
            comment_templates: 评论模板列表
        """
        self.like_probability = like_probability
        self.comment_templates = comment_templates or [
            "👍",
            "❤️",
            "很棒！",
            "支持！",
            "加油！",
            "太厉害了！",
            "学习了！",
            "谢谢分享！"
        ]
        
        # 已互动记录（防止重复）
        self._interacted: Set[str] = set()
        self._lock = threading.Lock()
        
        # 互动规则
        self._rules: List[Dict] = []
    
    def add_rule(self,
                 condition: Callable[[MomentsPost], bool],
                 action: str,
                 probability: float = 1.0,
                 comment_template: str = None):
        """
        添加互动规则
        
        Args:
            condition: 条件函数
            action: 动作 ('like', 'comment', 'both')
            probability: 触发概率
            comment_template: 评论模板
        """
        self._rules.append({
            'condition': condition,
            'action': action,
            'probability': probability,
            'comment_template': comment_template
        })
    
    def should_interact(self, post: MomentsPost) -> Optional[Dict[str, Any]]:
        """
        判断是否应该互动
        
        Returns:
            互动动作字典，或None
        """
        with self._lock:
            # 检查是否已互动
            if post.post_id in self._interacted:
                return None
            
            # 检查自定义规则
            for rule in self._rules:
                if rule['condition'](post):
                    import random
                    if random.random() < rule['probability']:
                        return {
                            'action': rule['action'],
                            'comment_template': rule.get('comment_template')
                        }
            
            # 默认随机点赞
            import random
            if random.random() < self.like_probability:
                return {'action': 'like'}
            
            return None
    
    def get_comment(self, post: MomentsPost, template: str = None) -> str:
        """生成评论"""
        import random
        
        if template:
            # 替换模板变量
            comment = template.replace('{name}', post.user_name)
            comment = comment.replace('{content}', post.content[:20])
            return comment
        
        return random.choice(self.comment_templates)
    
    def mark_interacted(self, post_id: str):
        """标记为已互动"""
        with self._lock:
            self._interacted.add(post_id)
    
    def clear_history(self, days: int = 30):
        """清理历史记录"""
        # 这里可以扩展为持久化存储
        pass


class MomentsMonitor:
    """朋友圈监控器"""
    
    def __init__(self):
        self._watched_users: Set[str] = set()
        self._watched_keywords: Set[str] = set()
        self._post_history: deque = deque(maxlen=1000)
        self._user_posts: Dict[str, List[MomentsPost]] = defaultdict(list)
        
        self._handlers: List[Callable] = []
        self._lock = threading.Lock()
        
        # 监控线程
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def watch_user(self, user_id: str):
        """关注用户"""
        with self._lock:
            self._watched_users.add(user_id)
            logger.info(f"开始监控用户: {user_id}")
    
    def unwatch_user(self, user_id: str):
        """取消关注用户"""
        with self._lock:
            self._watched_users.discard(user_id)
            logger.info(f"停止监控用户: {user_id}")
    
    def watch_keyword(self, keyword: str):
        """关注关键词"""
        with self._lock:
            self._watched_keywords.add(keyword.lower())
            logger.info(f"开始监控关键词: {keyword}")
    
    def unwatch_keyword(self, keyword: str):
        """取消关注关键词"""
        with self._lock:
            self._watched_keywords.discard(keyword.lower())
    
    def add_post(self, post: MomentsPost):
        """添加帖子"""
        with self._lock:
            self._post_history.append(post)
            self._user_posts[post.user_id].append(post)
            
            # 限制每个用户的帖子数量
            if len(self._user_posts[post.user_id]) > 50:
                self._user_posts[post.user_id] = self._user_posts[post.user_id][-50:]
        
        # 检查是否需要通知
        self._check_and_notify(post)
    
    def _check_and_notify(self, post: MomentsPost):
        """检查并通知"""
        should_notify = False
        reason = []
        
        with self._lock:
            # 检查是否是关注的用户
            if post.user_id in self._watched_users:
                should_notify = True
                reason.append(f"关注用户: {post.user_name}")
            
            # 检查是否包含关键词
            content_lower = post.content.lower()
            for keyword in self._watched_keywords:
                if keyword in content_lower:
                    should_notify = True
                    reason.append(f"关键词: {keyword}")
        
        if should_notify:
            self._notify_handlers(post, reason)
    
    def register_handler(self, handler: Callable):
        """注册处理器"""
        self._handlers.append(handler)
    
    def unregister_handler(self, handler: Callable):
        """取消注册处理器"""
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    def _notify_handlers(self, post: MomentsPost, reason: List[str]):
        """通知处理器"""
        for handler in self._handlers:
            try:
                handler(post, reason)
            except Exception as e:
                logger.error(f"监控处理器执行失败: {e}")
    
    def get_user_posts(self, 
                       user_id: str,
                       limit: int = 20) -> List[MomentsPost]:
        """获取用户帖子"""
        with self._lock:
            return self._user_posts.get(user_id, [])[-limit:]
    
    def get_recent_posts(self, limit: int = 50) -> List[MomentsPost]:
        """获取最近帖子"""
        with self._lock:
            return list(self._post_history)[-limit:]
    
    def search_posts(self, keyword: str) -> List[MomentsPost]:
        """搜索帖子"""
        keyword_lower = keyword.lower()
        with self._lock:
            return [
                post for post in self._post_history
                if keyword_lower in post.content.lower()
            ]


class MomentsStats:
    """朋友圈统计器"""
    
    def __init__(self):
        self._user_stats: Dict[str, Dict] = defaultdict(lambda: {
            'post_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'received_likes': 0,
            'received_comments': 0,
            'first_post': None,
            'last_post': None
        })
        
        self._daily_stats: Dict[str, Counter] = defaultdict(Counter)
        self._lock = threading.Lock()
    
    def record_post(self, post: MomentsPost):
        """记录帖子"""
        with self._lock:
            stats = self._user_stats[post.user_id]
            stats['post_count'] += 1
            stats['received_likes'] = len(post.likes)
            stats['received_comments'] = len(post.comments)
            stats['last_post'] = post.created_at
            
            if stats['first_post'] is None:
                stats['first_post'] = post.created_at
            
            # 记录每日统计
            date_str = post.created_at.strftime('%Y-%m-%d')
            self._daily_stats[post.user_id][date_str] += 1
    
    def record_interaction(self,
                           user_id: str,
                           interaction_type: InteractionType):
        """记录互动"""
        with self._lock:
            stats = self._user_stats[user_id]
            if interaction_type == InteractionType.LIKE:
                stats['like_count'] += 1
            elif interaction_type == InteractionType.COMMENT:
                stats['comment_count'] += 1
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计"""
        with self._lock:
            return dict(self._user_stats.get(user_id, {}))
    
    def get_leaderboard(self,
                        by: str = 'post_count',
                        limit: int = 10) -> List[Dict]:
        """获取排行榜"""
        with self._lock:
            users = [
                {'user_id': uid, **stats}
                for uid, stats in self._user_stats.items()
            ]
            
            users.sort(key=lambda x: x.get(by, 0), reverse=True)
            return users[:limit]


class MomentsManager:
    """朋友圈管理器（整合所有功能）"""
    
    def __init__(self,
                 bot_user_id: str = None,
                 auto_like_probability: float = 0.3):
        self.bot_user_id = bot_user_id
        self.content_parser = ContentParser()
        self.auto_interaction = AutoInteraction(auto_like_probability)
        self.monitor = MomentsMonitor()
        self.stats = MomentsStats()
        
        self._users: Dict[str, MomentsUser] = {}
        self._posts: Dict[str, MomentsPost] = {}
        self._lock = threading.Lock()
    
    def add_user(self, user: MomentsUser):
        """添加用户"""
        with self._lock:
            self._users[user.user_id] = user
    
    def get_user(self, user_id: str) -> Optional[MomentsUser]:
        """获取用户"""
        return self._users.get(user_id)
    
    def add_post(self, post: MomentsPost):
        """添加帖子"""
        with self._lock:
            self._posts[post.post_id] = post
        
        # 记录统计
        self.stats.record_post(post)
        
        # 监控检查
        self.monitor.add_post(post)
    
    def get_post(self, post_id: str) -> Optional[MomentsPost]:
        """获取帖子"""
        return self._posts.get(post_id)
    
    def process_new_post(self, post: MomentsPost) -> Dict[str, Any]:
        """处理新帖子"""
        # 1. 解析内容
        parsed = self.content_parser.parse_content(post.content)
        post.metadata['parsed'] = parsed
        
        # 2. 添加到管理器
        self.add_post(post)
        
        # 3. 检查自动互动
        interaction = self.auto_interaction.should_interact(post)
        
        result = {
            'post': post,
            'parsed': parsed,
            'auto_interaction': interaction
        }
        
        return result
    
    def like_post(self, post_id: str) -> InteractionRecord:
        """点赞帖子"""
        post = self.get_post(post_id)
        if not post:
            return InteractionRecord(
                post_id=post_id,
                user_id=self.bot_user_id or '',
                interaction_type=InteractionType.LIKE,
                success=False,
                error_message="帖子不存在"
            )
        
        # 检查是否已点赞
        if self.bot_user_id in post.likes:
            return InteractionRecord(
                post_id=post_id,
                user_id=self.bot_user_id or '',
                interaction_type=InteractionType.LIKE,
                success=False,
                error_message="已点赞"
            )
        
        # 执行点赞
        post.likes.append(self.bot_user_id)
        self.auto_interaction.mark_interacted(post_id)
        
        if self.bot_user_id:
            self.stats.record_interaction(self.bot_user_id, InteractionType.LIKE)
        
        return InteractionRecord(
            post_id=post_id,
            user_id=self.bot_user_id or '',
            interaction_type=InteractionType.LIKE,
            success=True
        )
    
    def comment_post(self,
                     post_id: str,
                     comment: str) -> InteractionRecord:
        """评论帖子"""
        post = self.get_post(post_id)
        if not post:
            return InteractionRecord(
                post_id=post_id,
                user_id=self.bot_user_id or '',
                interaction_type=InteractionType.COMMENT,
                content=comment,
                success=False,
                error_message="帖子不存在"
            )
        
        # 添加评论
        post.comments.append({
            'user_id': self.bot_user_id,
            'content': comment,
            'timestamp': datetime.now()
        })
        self.auto_interaction.mark_interacted(post_id)
        
        if self.bot_user_id:
            self.stats.record_interaction(self.bot_user_id, InteractionType.COMMENT)
        
        return InteractionRecord(
            post_id=post_id,
            user_id=self.bot_user_id or '',
            interaction_type=InteractionType.COMMENT,
            content=comment,
            success=True
        )
    
    def get_user_timeline(self,
                          user_id: str = None,
                          limit: int = 20) -> List[MomentsPost]:
        """获取用户时间线"""
        with self._lock:
            posts = list(self._posts.values())
            
            if user_id:
                posts = [p for p in posts if p.user_id == user_id]
            
            posts.sort(key=lambda p: p.created_at, reverse=True)
            return posts[:limit]