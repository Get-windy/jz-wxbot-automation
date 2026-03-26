# -*- coding: utf-8 -*-
"""
jz-wxbot 任务协调器
版本: v1.0.0
功能: 分发任务到多个Worker实例
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

try:
    import redis.asyncio as redis
except ImportError:
    import redis

logger = logging.getLogger(__name__)


@dataclass
class WorkerInfo:
    """Worker实例信息"""
    worker_id: str
    status: str  # idle, busy, offline
    last_heartbeat: float
    current_task: Optional[str] = None
    completed_tasks: int = 0
    failed_tasks: int = 0


@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str  # send_message, batch_send, etc.
    payload: Dict[str, Any]
    priority: int = 0
    created_at: float = 0.0
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict] = None


class CoordinatorAPI(BaseHTTPRequestHandler):
    """协调器HTTP API"""
    
    coordinator = None  # 将在启动时设置
    
    def log_message(self, format, *args):
        """禁用默认日志"""
        pass
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/health':
            self._send_json(200, {"status": "healthy"})
        elif self.path == '/api/workers':
            workers = self.coordinator.get_workers_status()
            self._send_json(200, workers)
        elif self.path == '/api/queue':
            queue = self.coordinator.get_queue_status()
            self._send_json(200, queue)
        elif self.path == '/api/stats':
            stats = self.coordinator.get_stats()
            self._send_json(200, stats)
        else:
            self._send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return
        
        if self.path == '/api/send':
            # 创建发送任务
            result = asyncio.run(self.coordinator.create_task(
                task_type="send_message",
                payload=data
            ))
            self._send_json(200, result)
        elif self.path == '/api/queue/add':
            # 添加任务到队列
            result = asyncio.run(self.coordinator.create_task(
                task_type=data.get('task_type', 'generic'),
                payload=data.get('payload', {}),
                priority=data.get('priority', 0)
            ))
            self._send_json(200, result)
        elif self.path == '/api/heartbeat':
            # Worker心跳
            worker_id = data.get('worker_id')
            status = data.get('status', 'idle')
            result = asyncio.run(self.coordinator.update_worker_heartbeat(
                worker_id, status
            ))
            self._send_json(200, result)
        else:
            self._send_json(404, {"error": "Not found"})
    
    def _send_json(self, status_code: int, data: Dict):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))


class Coordinator:
    """
    任务协调器
    
    功能:
    1. 管理Worker注册和心跳
    2. 任务队列管理
    3. 任务分发到空闲Worker
    4. 状态监控和统计
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Redis连接
        self.redis_url = self.config.get('redis_url', 'redis://localhost:6379')
        self.redis: Optional[redis.Redis] = None
        
        # Worker管理
        self.workers: Dict[str, WorkerInfo] = {}
        self.worker_timeout = 60  # 心跳超时时间（秒）
        
        # 任务队列
        self.task_queue_key = "wxbot:task_queue"
        self.task_prefix = "wxbot:task:"
        
        # 统计
        self.stats = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'messages_sent': 0
        }
        
        # 运行状态
        self.running = False
    
    async def start(self) -> bool:
        """启动协调器"""
        try:
            logger.info("启动任务协调器...")
            
            # 连接Redis
            self.redis = redis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Redis连接成功 ✅")
            
            # 启动HTTP API
            self._start_api_server()
            
            # 启动任务分发循环
            self.running = True
            asyncio.create_task(self._dispatch_loop())
            asyncio.create_task(self._cleanup_loop())
            
            logger.info("协调器启动成功 ✅")
            return True
            
        except Exception as e:
            logger.error(f"协调器启动失败: {e}")
            return False
    
    async def stop(self):
        """停止协调器"""
        logger.info("停止协调器...")
        self.running = False
        if self.redis:
            await self.redis.close()
        logger.info("协调器已停止 ✅")
    
    def _start_api_server(self):
        """启动HTTP API服务器"""
        port = self.config.get('port', 9000)
        CoordinatorAPI.coordinator = self
        
        def run_server():
            server = HTTPServer(('0.0.0.0', port), CoordinatorAPI)
            server.serve_forever()
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        logger.info(f"API服务器启动在端口 {port}")
    
    async def _dispatch_loop(self):
        """任务分发循环"""
        while self.running:
            try:
                # 检查队列中的任务
                task_data = await self.redis.lpop(self.task_queue_key)
                
                if task_data:
                    task = json.loads(task_data)
                    
                    # 查找空闲Worker
                    worker = await self._find_idle_worker()
                    
                    if worker:
                        await self._assign_task(worker.worker_id, task)
                    else:
                        # 没有空闲Worker，放回队列
                        await self.redis.rpush(self.task_queue_key, task_data)
                        await asyncio.sleep(1)
                else:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"任务分发错误: {e}")
                await asyncio.sleep(1)
    
    async def _cleanup_loop(self):
        """清理超时Worker"""
        while self.running:
            try:
                current_time = time.time()
                offline_workers = []
                
                for worker_id, worker_info in self.workers.items():
                    if current_time - worker_info.last_heartbeat > self.worker_timeout:
                        worker_info.status = 'offline'
                        offline_workers.append(worker_id)
                
                for worker_id in offline_workers:
                    logger.warning(f"Worker {worker_id} 超时离线")
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"清理错误: {e}")
                await asyncio.sleep(10)
    
    async def _find_idle_worker(self) -> Optional[WorkerInfo]:
        """查找空闲Worker"""
        for worker in self.workers.values():
            if worker.status == 'idle':
                return worker
        return None
    
    async def _assign_task(self, worker_id: str, task: Dict):
        """分配任务到Worker"""
        task_id = task.get('task_id')
        
        # 更新Worker状态
        if worker_id in self.workers:
            self.workers[worker_id].status = 'busy'
            self.workers[worker_id].current_task = task_id
        
        # 存储任务状态
        task['status'] = 'running'
        task['assigned_to'] = worker_id
        await self.redis.set(
            f"{self.task_prefix}{task_id}",
            json.dumps(task),
            ex=3600
        )
        
        logger.info(f"任务 {task_id} 分配给 Worker {worker_id}")
    
    async def create_task(
        self,
        task_type: str,
        payload: Dict,
        priority: int = 0
    ) -> Dict:
        """创建新任务"""
        import uuid
        
        task_id = str(uuid.uuid4())
        task = {
            'task_id': task_id,
            'task_type': task_type,
            'payload': payload,
            'priority': priority,
            'created_at': time.time(),
            'status': 'pending'
        }
        
        # 添加到队列
        await self.redis.rpush(self.task_queue_key, json.dumps(task))
        
        self.stats['tasks_created'] += 1
        
        logger.info(f"创建任务 {task_id}: {task_type}")
        
        return {
            'task_id': task_id,
            'status': 'pending',
            'message': '任务已加入队列'
        }
    
    async def update_worker_heartbeat(
        self,
        worker_id: str,
        status: str = 'idle'
    ) -> Dict:
        """更新Worker心跳"""
        current_time = time.time()
        
        if worker_id not in self.workers:
            self.workers[worker_id] = WorkerInfo(
                worker_id=worker_id,
                status=status,
                last_heartbeat=current_time
            )
            logger.info(f"新Worker注册: {worker_id}")
        else:
            self.workers[worker_id].status = status
            self.workers[worker_id].last_heartbeat = current_time
            
            if status == 'idle':
                self.workers[worker_id].current_task = None
        
        return {
            'worker_id': worker_id,
            'status': 'acknowledged',
            'timestamp': current_time
        }
    
    def get_workers_status(self) -> Dict:
        """获取所有Worker状态"""
        return {
            'workers': {wid: asdict(w) for wid, w in self.workers.items()},
            'total': len(self.workers),
            'online': len([w for w in self.workers.values() if w.status != 'offline'])
        }
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            'pending_tasks': 'N/A',  # 需要异步获取
            'stats': self.stats
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'workers': {
                'total': len(self.workers),
                'online': len([w for w in self.workers.values() if w.status != 'offline']),
                'idle': len([w for w in self.workers.values() if w.status == 'idle']),
                'busy': len([w for w in self.workers.values() if w.status == 'busy'])
            },
            'tasks': self.stats
        }


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    config = {
        'redis_url': 'redis://localhost:6379',
        'port': 9000
    }
    
    coordinator = Coordinator(config)
    await coordinator.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await coordinator.stop()


if __name__ == '__main__':
    asyncio.run(main())