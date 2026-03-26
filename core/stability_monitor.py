# -*- coding: utf-8 -*-
"""
jz-wxbot 稳定性监控服务
集成微信控制监控、消息监控、错误收集、健康检查
版本: v1.0.0
"""

import os
import sys
import time
import json
import yaml
import psutil
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.enhanced_logging import get_logger, EnhancedLogger
from core.enhanced_error_handling import get_error_handler, ErrorSeverity, RecoveryStrategy


# ============================================================
# 枚举和类型
# ============================================================

class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AlertSeverity(Enum):
    """告警级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Metric:
    """监控指标"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
        }


@dataclass
class Alert:
    """告警"""
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================
# 进程监控器
# ============================================================

class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self, config: Dict, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        self._process_status: Dict[str, bool] = {}
        self._callbacks: List[Callable] = []
    
    def check_processes(self) -> Dict[str, bool]:
        """检查进程状态"""
        for proc_config in self.config.get('processes', []):
            name = proc_config['name']
            found = self._find_process(name)
            old_status = self._process_status.get(name, True)
            self._process_status[name] = found
            
            if old_status != found:
                self._notify_change(name, found, proc_config)
        
        return self._process_status.copy()
    
    def _find_process(self, name: str) -> bool:
        """查找进程"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == name:
                    return True
        except Exception:
            pass
        return False
    
    def _notify_change(self, name: str, running: bool, config: Dict):
        """通知状态变化"""
        self.logger.operation(
            "进程监控", 
            name, 
            running,
            {'critical': config.get('critical', False)}
        )
        
        for callback in self._callbacks:
            try:
                callback(name, running, config)
            except Exception as e:
                self.logger.error(f"回调执行失败: {e}")
    
    def register_callback(self, callback: Callable):
        """注册状态变化回调"""
        self._callbacks.append(callback)
    
    def get_status(self) -> Dict[str, bool]:
        """获取当前状态"""
        return self._process_status.copy()


# ============================================================
# 消息监控器
# ============================================================

class MessageMonitor:
    """消息监控器"""
    
    def __init__(self, config: Dict, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        
        # 发送统计
        self._sent_count = 0
        self._sent_success = 0
        self._sent_failed = 0
        self._sent_latencies: List[float] = []
        
        # 接收统计
        self._received_count = 0
        self._processing_times: List[float] = []
        
        # 队列统计
        self._queue_size = 0
        self._max_queue_size = config.get('queue_monitor', {}).get('max_queue_size', 1000)
        
        # 锁
        self._lock = threading.Lock()
    
    def record_send(self, success: bool, latency_ms: float, chat_type: str = "unknown"):
        """记录发送"""
        with self._lock:
            self._sent_count += 1
            if success:
                self._sent_success += 1
            else:
                self._sent_failed += 1
            self._sent_latencies.append(latency_ms)
            
            # 限制历史长度
            if len(self._sent_latencies) > 1000:
                self._sent_latencies = self._sent_latencies[-1000:]
    
    def record_receive(self, processing_time_ms: float, chat_type: str = "unknown"):
        """记录接收"""
        with self._lock:
            self._received_count += 1
            self._processing_times.append(processing_time_ms)
            
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]
    
    def update_queue_size(self, size: int):
        """更新队列大小"""
        with self._lock:
            self._queue_size = size
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        with self._lock:
            success_rate = self._sent_success / self._sent_count if self._sent_count > 0 else 1.0
            avg_latency = sum(self._sent_latencies) / len(self._sent_latencies) if self._sent_latencies else 0
            
            return {
                'send': {
                    'total': self._sent_count,
                    'success': self._sent_success,
                    'failed': self._sent_failed,
                    'success_rate': success_rate,
                    'avg_latency_ms': avg_latency,
                    'max_latency_ms': max(self._sent_latencies) if self._sent_latencies else 0,
                },
                'receive': {
                    'total': self._received_count,
                    'avg_processing_ms': sum(self._processing_times) / len(self._processing_times) if self._processing_times else 0,
                },
                'queue': {
                    'size': self._queue_size,
                    'max_size': self._max_queue_size,
                    'usage_percent': self._queue_size / self._max_queue_size * 100 if self._max_queue_size > 0 else 0,
                },
            }
    
    def check_thresholds(self) -> List[Alert]:
        """检查阈值"""
        alerts = []
        metrics = self.get_metrics()
        
        thresholds = self.config.get('send_monitor', {}).get('thresholds', {})
        
        # 检查成功率
        min_success_rate = thresholds.get('success_rate_min', 0.95)
        if metrics['send']['success_rate'] < min_success_rate:
            alerts.append(Alert(
                name="low_success_rate",
                severity=AlertSeverity.HIGH,
                message=f"消息发送成功率过低: {metrics['send']['success_rate']:.2%}",
                metadata={'current': metrics['send']['success_rate'], 'threshold': min_success_rate}
            ))
        
        # 检查延迟
        max_latency = thresholds.get('latency_max_ms', 5000)
        if metrics['send']['avg_latency_ms'] > max_latency:
            alerts.append(Alert(
                name="high_latency",
                severity=AlertSeverity.MEDIUM,
                message=f"消息发送延迟过高: {metrics['send']['avg_latency_ms']:.0f}ms",
                metadata={'current': metrics['send']['avg_latency_ms'], 'threshold': max_latency}
            ))
        
        # 检查队列
        queue_threshold = self._max_queue_size * 0.8
        if self._queue_size > queue_threshold:
            alerts.append(Alert(
                name="queue_near_full",
                severity=AlertSeverity.MEDIUM,
                message=f"消息队列接近满载: {self._queue_size}/{self._max_queue_size}",
                metadata={'current': self._queue_size, 'threshold': queue_threshold}
            ))
        
        return alerts


# ============================================================
# 资源监控器
# ============================================================

class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, config: Dict, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        self._metrics: List[Dict] = []
        self._max_metrics = 1000
    
    def collect(self) -> Dict[str, Any]:
        """收集资源指标"""
        process = psutil.Process(os.getpid())
        
        # CPU
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # 内存
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # 线程
        thread_count = process.num_threads()
        
        # 文件描述符
        try:
            open_files = len(process.open_files())
        except Exception:
            open_files = 0
        
        metric = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            'thread_count': thread_count,
            'open_files': open_files,
        }
        
        self._metrics.append(metric)
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics:]
        
        return metric
    
    def get_summary(self) -> Dict[str, Any]:
        """获取资源摘要"""
        if not self._metrics:
            return {}
        
        cpu_values = [m['cpu_percent'] for m in self._metrics]
        memory_values = [m['memory_mb'] for m in self._metrics]
        
        return {
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'current': cpu_values[-1],
            },
            'memory': {
                'avg_mb': sum(memory_values) / len(memory_values),
                'max_mb': max(memory_values),
                'min_mb': min(memory_values),
                'current_mb': memory_values[-1],
            },
            'thread_count': self._metrics[-1]['thread_count'],
            'open_files': self._metrics[-1]['open_files'],
        }
    
    def check_thresholds(self) -> List[Alert]:
        """检查阈值"""
        alerts = []
        summary = self.get_summary()
        
        if not summary:
            return alerts
        
        health_config = self.config.get('health_check', {}).get('checks', [])
        
        for check in health_config:
            if check['type'] != 'resource':
                continue
            
            name = check['name']
            
            if name == 'memory_usage':
                threshold = check.get('threshold_mb', 500)
                if summary['memory']['current_mb'] > threshold:
                    alerts.append(Alert(
                        name="high_memory",
                        severity=AlertSeverity.MEDIUM,
                        message=f"内存使用过高: {summary['memory']['current_mb']:.0f}MB",
                        metadata={'current': summary['memory']['current_mb'], 'threshold': threshold}
                    ))
            
            elif name == 'cpu_usage':
                threshold = check.get('threshold_percent', 80)
                if summary['cpu']['current'] > threshold:
                    alerts.append(Alert(
                        name="high_cpu",
                        severity=AlertSeverity.MEDIUM,
                        message=f"CPU使用过高: {summary['cpu']['current']:.0f}%",
                        metadata={'current': summary['cpu']['current'], 'threshold': threshold}
                    ))
        
        return alerts


# ============================================================
# 健康检查服务
# ============================================================

class HealthCheckService:
    """健康检查服务"""
    
    def __init__(self, config: Dict, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        self._checks: Dict[str, Callable] = {}
        self._results: Dict[str, Dict] = {}
    
    def register_check(self, name: str, check_func: Callable):
        """注册健康检查"""
        self._checks[name] = check_func
    
    def run_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        
        for name, check_func in self._checks.items():
            try:
                result = check_func()
                results[name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'result': result,
                    'timestamp': datetime.now().isoformat(),
                }
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                }
        
        self._results = results
        return results
    
    def get_overall_status(self) -> HealthStatus:
        """获取总体健康状态"""
        if not self._results:
            return HealthStatus.HEALTHY
        
        has_unhealthy = False
        for check_result in self._results.values():
            if check_result['status'] == 'unhealthy':
                has_unhealthy = True
        
        if has_unhealthy:
            return HealthStatus.UNHEALTHY
        
        return HealthStatus.HEALTHY
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        return {
            'status': self.get_overall_status().value,
            'checks': self._results,
            'timestamp': datetime.now().isoformat(),
        }


# ============================================================
# 稳定性监控服务
# ============================================================

class StabilityMonitorService:
    """稳定性监控服务"""
    
    def __init__(self, config_path: str = None):
        self.logger = get_logger('stability_monitor')
        self.error_handler = get_error_handler()
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化监控器
        self.process_monitor = ProcessMonitor(
            self.config.get('wechat_control', {}).get('process_monitor', {}),
            self.logger
        )
        
        self.message_monitor = MessageMonitor(
            self.config.get('message_monitor', {}),
            self.logger
        )
        
        self.resource_monitor = ResourceMonitor(
            self.config.get('health_check', {}),
            self.logger
        )
        
        self.health_service = HealthCheckService(
            self.config.get('health_check', {}),
            self.logger
        )
        
        # 注册健康检查
        self._register_health_checks()
        
        # 告警历史
        self._alerts: List[Alert] = []
        self._max_alerts = 100
        
        # 运行状态
        self._running = False
        self._start_time = None
    
    def _load_config(self, config_path: str = None) -> Dict:
        """加载配置"""
        if config_path is None:
            config_path = str(PROJECT_ROOT / "config" / "monitoring" / "stability_monitor.yaml")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.warning(f"加载监控配置失败: {e}，使用默认配置")
            return {}
    
    def _register_health_checks(self):
        """注册健康检查"""
        self.health_service.register_check(
            'wechat_process',
            lambda: any(self.process_monitor.get_status().values())
        )
        self.health_service.register_check(
            'message_queue',
            lambda: self.message_monitor._queue_size < self.message_monitor._max_queue_size * 0.9
        )
        self.health_service.register_check(
            'memory',
            lambda: self.resource_monitor.collect()['memory_mb'] < 500
        )
        self.health_service.register_check(
            'cpu',
            lambda: self.resource_monitor.collect()['cpu_percent'] < 80
        )
    
    def start(self):
        """启动监控"""
        self._running = True
        self._start_time = datetime.now()
        self.logger.info("稳定性监控服务启动")
    
    def stop(self):
        """停止监控"""
        self._running = False
        self.logger.info("稳定性监控服务停止")
    
    def check(self) -> Dict[str, Any]:
        """执行检查"""
        # 进程检查
        process_status = self.process_monitor.check_processes()
        
        # 资源收集
        resource_metrics = self.resource_monitor.collect()
        
        # 消息指标
        message_metrics = self.message_monitor.get_metrics()
        
        # 健康检查
        health_report = self.health_service.run_checks()
        
        # 收集告警
        alerts = []
        alerts.extend(self.message_monitor.check_thresholds())
        alerts.extend(self.resource_monitor.check_thresholds())
        
        # 记录告警
        for alert in alerts:
            self._alerts.append(alert)
            self.logger.warning(f"告警: {alert.message}")
        
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]
        
        return {
            'process_status': process_status,
            'resource': resource_metrics,
            'message': message_metrics,
            'health': health_report,
            'alerts': [a.to_dict() for a in alerts],
        }
    
    def get_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        now = datetime.now()
        duration = (now - self._start_time).total_seconds() if self._start_time else 0
        
        return {
            'generated_at': now.isoformat(),
            'monitoring_duration_seconds': duration,
            'overall_status': self.health_service.get_overall_status().value,
            'process_status': self.process_monitor.get_status(),
            'resource_summary': self.resource_monitor.get_summary(),
            'message_metrics': self.message_monitor.get_metrics(),
            'health_report': self.health_service.get_health_report(),
            'alerts': {
                'total': len(self._alerts),
                'recent': [a.to_dict() for a in self._alerts[-10:]],
            },
            'recommendations': self._generate_recommendations(),
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 检查资源使用
        resource_summary = self.resource_monitor.get_summary()
        if resource_summary:
            if resource_summary['memory']['current_mb'] > 400:
                recommendations.append("内存使用较高，建议检查内存泄漏或增加内存限制")
            
            if resource_summary['cpu']['current'] > 70:
                recommendations.append("CPU使用率较高，建议优化性能或增加资源")
        
        # 检查消息指标
        message_metrics = self.message_monitor.get_metrics()
        if message_metrics['send']['success_rate'] < 0.95:
            recommendations.append(f"消息发送成功率({message_metrics['send']['success_rate']:.0%})偏低，建议检查网络连接和微信状态")
        
        # 检查队列
        if message_metrics['queue']['usage_percent'] > 80:
            recommendations.append("消息队列接近满载，建议增加处理速度或队列大小")
        
        if not recommendations:
            recommendations.append("系统运行状态良好，继续保持")
        
        return recommendations
    
    def save_report(self, filepath: str = None):
        """保存报告"""
        if filepath is None:
            report_dir = PROJECT_ROOT / "docs" / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = str(report_dir / f"stability_report_{timestamp}.json")
        
        report = self.get_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"监控报告已保存: {filepath}")
        return filepath


# ============================================================
# 监控装饰器
# ============================================================

def monitor_send(monitor: MessageMonitor):
    """监控发送操作装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                monitor.record_send(True, duration)
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                monitor.record_send(False, duration)
                raise
        return wrapper
    return decorator


def monitor_receive(monitor: MessageMonitor):
    """监控接收操作装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                monitor.record_receive(duration)
                return result
            except Exception:
                raise
        return wrapper
    return decorator


# ============================================================
# 全局实例
# ============================================================

_global_monitor: Optional[StabilityMonitorService] = None


def get_stability_monitor() -> StabilityMonitorService:
    """获取全局监控实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = StabilityMonitorService()
    return _global_monitor


# ============================================================
# 导出
# ============================================================

__all__ = [
    'HealthStatus',
    'AlertSeverity',
    'Metric',
    'Alert',
    'ProcessMonitor',
    'MessageMonitor',
    'ResourceMonitor',
    'HealthCheckService',
    'StabilityMonitorService',
    'get_stability_monitor',
    'monitor_send',
    'monitor_receive',
]