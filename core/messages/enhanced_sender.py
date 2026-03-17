# -*- coding: utf-8 -*-
"""
增强版消息发送器
版本: v1.0.0
功能: 提供批量发送、发送状态追踪、发送队列管理
"""

import time
import threading
import logging
import random
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import queue

logger = logging.getLogger(__name__)


class SendStatus(Enum):
    """发送状态"""
    PENDING = "pending"        # 待发送
    SENDING = "sending"        # 发送中
    SUCCESS = "success"        # 成功
    FAILED = "failed"          # 失败
    RETRYING = "retrying"      # 重试中
    CANCELLED = "cancelled"    # 已取消


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    LINK = "link"
    AT = "at"


@dataclass
class SendTask:
    """发送任务"""
    task_id: str
    chat_id: str
    chat_name: str
    content: str
    message_type: MessageType = MessageType.TEXT
    at_users: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, 1最高
    retry_count: int = 0
    max_retries: int = 3
    status: SendStatus = SendStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    """发送结果"""
    task_id: str
    success: bool
    chat_id: str
    chat_name: str
    sent_at: datetime
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_ms: int = 0


class SendQueue:
    """发送队列管理"""
    
    def __init__(self, max_size: int = 1000):
        self._queue = queue.PriorityQueue(maxsize=max_size)
        self._tasks: Dict[str, SendTask] = {}
        self._lock = threading.Lock()
        self._counter = 0
    
    def put(self, task: SendTask) -> bool:
        """添加发送任务"""
        try:
            with self._lock:
                self._tasks[task.task_id] = task
                # 优先级队列：(priority, counter, task)
                # counter用于保证同优先级的FIFO顺序
                self._counter += 1
                self._queue.put((task.priority, self._counter, task))
            logger.debug(f"添加发送任务: {task.task_id}")
            return True
        except queue.Full:
            logger.error("发送队列已满")
            return False
    
    def get(self, timeout: float = None) -> Optional[SendTask]:
        """获取发送任务"""
        try:
            priority, counter, task = self._queue.get(timeout=timeout)
            return task
        except queue.Empty:
            return None
    
    def task_done(self):
        """标记任务完成"""
        self._queue.task_done()
    
    def get_task(self, task_id: str) -> Optional[SendTask]:
        """获取指定任务"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task(self, task: SendTask):
        """更新任务状态"""
        with self._lock:
            if task.task_id in self._tasks:
                self._tasks[task.task_id] = task
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()
    
    def get_pending_count(self) -> int:
        """获取待处理任务数"""
        with self._lock:
            return sum(1 for t in self._tasks.values() 
                      if t.status == SendStatus.PENDING)
    
    def clear(self):
        """清空队列"""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._tasks.clear()


class BatchSender:
    """批量发送器"""
    
    def __init__(self, sender_instance, max_concurrent: int = 5):
        """
        初始化批量发送器
        
        Args:
            sender_instance: 实际的发送器实例
            max_concurrent: 最大并发数
        """
        self.sender = sender_instance
        self.max_concurrent = max_concurrent
        
        self.queue = SendQueue()
        self.results: deque = deque(maxlen=1000)
        
        self._running = False
        self._workers: List[threading.Thread] = []
        self._stop_event = threading.Event()
        
        # 发送统计
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'total_retries': 0,
            'avg_duration_ms': 0
        }
        self._stats_lock = threading.Lock()
    
    def add_task(self, task: SendTask) -> bool:
        """添加发送任务"""
        task.status = SendStatus.PENDING
        task.task_id = task.task_id or self._generate_task_id()
        return self.queue.put(task)
    
    def add_tasks(self, tasks: List[SendTask]) -> int:
        """批量添加任务"""
        success_count = 0
        for task in tasks:
            task.task_id = task.task_id or self._generate_task_id()
            if self.add_task(task):
                success_count += 1
        return success_count
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        return f"task_{int(time.time()*1000)}_{random.randint(1000, 9999)}"
    
    def start(self):
        """启动发送器"""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        
        # 创建工作线程
        for i in range(self.max_concurrent):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"SenderWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"批量发送器启动，{self.max_concurrent}个工作线程")
    
    def stop(self):
        """停止发送器"""
        self._running = False
        self._stop_event.set()
        
        for worker in self._workers:
            worker.join(timeout=5)
        
        self._workers.clear()
        logger.info("批量发送器已停止")
    
    def _worker_loop(self):
        """工作线程循环"""
        while self._running and not self._stop_event.is_set():
            task = self.queue.get(timeout=1)
            if task is None:
                continue
            
            self._process_task(task)
            self.queue.task_done()
    
    def _process_task(self, task: SendTask):
        """处理发送任务"""
        start_time = time.time()
        task.status = SendStatus.SENDING
        
        try:
            # 执行发送
            success = self._send_message(task)
            
            if success:
                task.status = SendStatus.SUCCESS
                task.sent_at = datetime.now()
            else:
                # 发送失败，检查是否重试
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = SendStatus.RETRYING
                    # 重新入队
                    time.sleep(random.uniform(1, 3))  # 随机延迟
                    self.queue.put(task)
                    return
                else:
                    task.status = SendStatus.FAILED
            
            # 记录结果
            duration_ms = int((time.time() - start_time) * 1000)
            result = SendResult(
                task_id=task.task_id,
                success=task.status == SendStatus.SUCCESS,
                chat_id=task.chat_id,
                chat_name=task.chat_name,
                sent_at=datetime.now(),
                error_message=task.error_message,
                retry_count=task.retry_count,
                duration_ms=duration_ms
            )
            self.results.append(result)
            self._update_stats(result)
            
        except Exception as e:
            logger.error(f"发送任务处理失败: {e}")
            task.status = SendStatus.FAILED
            task.error_message = str(e)
    
    def _send_message(self, task: SendTask) -> bool:
        """执行发送"""
        try:
            # 检查发送器是否有对应方法
            if task.message_type == MessageType.TEXT:
                if hasattr(self.sender, 'send_message'):
                    return self.sender.send_message(task.content, task.chat_name)
            elif task.message_type == MessageType.IMAGE:
                if hasattr(self.sender, 'send_image'):
                    return self.sender.send_image(task.content, task.chat_name)
            elif task.message_type == MessageType.FILE:
                if hasattr(self.sender, 'send_file'):
                    return self.sender.send_file(task.content, task.chat_name)
            elif task.message_type == MessageType.AT:
                if hasattr(self.sender, 'send_at_message'):
                    return self.sender.send_at_message(
                        task.content, 
                        task.at_users, 
                        task.chat_name
                    )
            
            # 默认使用send_message
            if hasattr(self.sender, 'send_message'):
                return self.sender.send_message(task.content, task.chat_name)
            
            logger.error("发送器没有可用的发送方法")
            return False
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            task.error_message = str(e)
            return False
    
    def _update_stats(self, result: SendResult):
        """更新统计"""
        with self._stats_lock:
            if result.success:
                self.stats['total_sent'] += 1
            else:
                self.stats['total_failed'] += 1
            
            self.stats['total_retries'] += result.retry_count
            
            # 计算平均耗时
            total = self.stats['total_sent'] + self.stats['total_failed']
            if total > 0:
                old_avg = self.stats['avg_duration_ms']
                self.stats['avg_duration_ms'] = int(
                    (old_avg * (total - 1) + result.duration_ms) / total
                )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            return dict(self.stats)
    
    def get_results(self, limit: int = 100) -> List[SendResult]:
        """获取发送结果"""
        return list(self.results)[-limit:]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            'queue_size': self.queue.get_queue_size(),
            'pending_count': self.queue.get_pending_count(),
            'running': self._running,
            'workers': len(self._workers)
        }


class SendScheduler:
    """发送调度器"""
    
    def __init__(self, batch_sender: BatchSender):
        self.sender = batch_sender
        self._scheduled_tasks: Dict[str, Dict] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
    
    def schedule_send(self, 
                      task: SendTask, 
                      scheduled_time: datetime) -> str:
        """安排定时发送"""
        schedule_id = f"schedule_{int(time.time()*1000)}_{random.randint(1000, 9999)}"
        
        self._scheduled_tasks[schedule_id] = {
            'task': task,
            'scheduled_time': scheduled_time,
            'created_at': datetime.now()
        }
        
        logger.info(f"安排定时发送: {schedule_id}, 时间: {scheduled_time}")
        return schedule_id
    
    def cancel_schedule(self, schedule_id: str) -> bool:
        """取消定时发送"""
        if schedule_id in self._scheduled_tasks:
            del self._scheduled_tasks[schedule_id]
            logger.info(f"取消定时发送: {schedule_id}")
            return True
        return False
    
    def start(self):
        """启动调度器"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self._scheduler_thread.start()
        logger.info("发送调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("发送调度器已停止")
    
    def _scheduler_loop(self):
        """调度器循环"""
        while self._running:
            now = datetime.now()
            
            # 检查是否有到期的任务
            to_send = []
            for schedule_id, schedule in list(self._scheduled_tasks.items()):
                if schedule['scheduled_time'] <= now:
                    to_send.append((schedule_id, schedule['task']))
            
            # 发送到期任务
            for schedule_id, task in to_send:
                self.sender.add_task(task)
                del self._scheduled_tasks[schedule_id]
                logger.info(f"定时任务已发送: {schedule_id}")
            
            time.sleep(1)  # 每秒检查一次


class SendTracker:
    """发送状态追踪器"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self._history: deque = deque(maxlen=max_history)
        self._by_chat: Dict[str, List[SendResult]] = {}
        self._lock = threading.Lock()
    
    def track(self, result: SendResult):
        """追踪发送结果"""
        with self._lock:
            self._history.append(result)
            
            if result.chat_id not in self._by_chat:
                self._by_chat[result.chat_id] = []
            self._by_chat[result.chat_id].append(result)
            
            # 限制每个聊天的历史记录
            if len(self._by_chat[result.chat_id]) > 100:
                self._by_chat[result.chat_id] = self._by_chat[result.chat_id][-100:]
    
    def get_history(self, 
                    chat_id: Optional[str] = None,
                    limit: int = 100) -> List[SendResult]:
        """获取发送历史"""
        with self._lock:
            if chat_id:
                return (self._by_chat.get(chat_id, []))[-limit:]
            return list(self._history)[-limit:]
    
    def get_success_rate(self, 
                         chat_id: Optional[str] = None) -> float:
        """获取成功率"""
        history = self.get_history(chat_id, limit=1000)
        if not history:
            return 0.0
        
        success = sum(1 for r in history if r.success)
        return success / len(history)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            history = list(self._history)
            
            if not history:
                return {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'success_rate': 0,
                    'avg_duration_ms': 0
                }
            
            success = sum(1 for r in history if r.success)
            total = len(history)
            avg_duration = sum(r.duration_ms for r in history) // total if total > 0 else 0
            
            return {
                'total': total,
                'success': success,
                'failed': total - success,
                'success_rate': round(success / total * 100, 2) if total > 0 else 0,
                'avg_duration_ms': avg_duration
            }