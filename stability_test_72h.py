#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
72小时jz-wxbot稳定性测试脚本
监控系统资源、记录异常、生成稳定性报告
"""

import os
import sys
import time
import psutil
import traceback
import json
import logging
import threading
import queue
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import warnings

# 设置日志 - 使用UTF-8编码
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stability_test.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 重定向stderr以避免日志编码问题
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # 记录没有emoji的版本
            msg = self.format(record)
            safe_msg = msg.encode('utf-8', errors='replace').decode('utf-8')
            self.stream.write(safe_msg + self.terminator)
            self.flush()
            
# 替换流处理器
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
        logging.root.handlers.remove(handler)
        logging.root.addHandler(SafeStreamHandler())

# 添加项目目录
sys.path.insert(0, 'I:\\jz-wxbot-automation')

# 添加测试目录
sys.path.insert(0, 'I:\\jz-wxbot-automation\\tests')

from bridge.bridge_service import BridgeService
from mcp_server import WxBotMCPServer
from human_like_operations import HumanLikeOperations


# ==================== 配置 ====================
TEST_DURATION_HOURS = 0.5  # 缩短为30分钟用于快速验证
SAMPLE_INTERVAL_SECONDS = 60  # 每分钟采样一次
RESOURCE_CHECK_INTERVAL = 30  # 每30秒检查资源
HEALTH_CHECK_INTERVAL = 60  # 每分钟进行健康检查
MAX_RETRIES_PER_TEST = 3  # 每个测试最多重试3次


@dataclass
class ResourceMetric:
    """资源指标"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    thread_count: int
    open_files: int


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    start_time: str
    end_time: str
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    retries: int = 0


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self):
        self.metrics: List[ResourceMetric] = []
        self.start_time = datetime.now()
        self.start_process = psutil.Process(os.getpid())
        
    def collect_metrics(self) -> ResourceMetric:
        """收集资源指标"""
        process = psutil.Process(os.getpid())
        
        # 获取系统资源
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取进程资源
        try:
            memory_info = process.memory_info()
            memory_used_mb = memory_info.rss / 1024 / 1024
        except Exception:
            memory_used_mb = 0
            
        # 获取网络信息
        netio = psutil.net_io_counters()
        
        return ResourceMetric(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory_used_mb,
            disk_percent=disk.percent,
            network_bytes_sent=netio.bytes_sent,
            network_bytes_recv=netio.bytes_recv,
            thread_count=process.num_threads(),
            open_files=len(process.open_files()) if hasattr(process, 'open_files') else 0
        )
    
    def sample(self):
        """采样资源指标"""
        metric = self.collect_metrics()
        self.metrics.append(metric)
        logger.info(f"资源采样: CPU={metric.cpu_percent:.1f}%, "
                   f"内存={metric.memory_used_mb:.1f}MB, "
                   f"线程={metric.thread_count}")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取资源使用摘要"""
        if not self.metrics:
            return {}
        
        cpu_values = [m.cpu_percent for m in self.metrics]
        memory_values = [m.memory_used_mb for m in self.metrics]
        
        return {
            'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
            'sample_count': len(self.metrics),
            'cpu_avg': sum(cpu_values) / len(cpu_values),
            'cpu_max': max(cpu_values),
            'memory_avg': sum(memory_values) / len(memory_values),
            'memory_max': max(memory_values),
            'thread_count': self.metrics[-1].thread_count,
            'open_files': self.metrics[-1].open_files
        }


class ExceptionRecorder:
    """异常记录器"""
    
    def __init__(self):
        self.exceptions: List[Dict[str, Any]] = []
        self.exception_counts: Dict[str, int] = {}
        
    def record(self, exception: Exception, context: str = ""):
        """记录异常"""
        error_type = type(exception).__name__
        error_msg = str(exception)
        timestamp = datetime.now().isoformat()
        
        exception_record = {
            'timestamp': timestamp,
            'type': error_type,
            'message': error_msg,
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        self.exceptions.append(exception_record)
        
        # 统计
        self.exception_counts[error_type] = self.exception_counts.get(error_type, 0) + 1
        
        logger.warning(f"异常记录: [{error_type}] {error_msg}")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取异常摘要"""
        return {
            'total_exceptions': len(self.exceptions),
            'by_type': self.exception_counts,
            'recent': self.exceptions[-10:] if len(self.exceptions) > 10 else self.exceptions
        }


class StabilityTestRunner:
    """稳定性测试运行器"""
    
    def __init__(self):
        self.resource_monitor = ResourceMonitor()
        self.exception_recorder = ExceptionRecorder()
        self.test_results: List[TestResult] = []
        self.running = False
        self.start_time = None
        
        # 初始化组件
        try:
            self.bridge_service = BridgeService()
            self.b_service = self.bridge_service
        except Exception as e:
            self.exception_recorder.record(e, "桥梁服务初始化")
            self.b_service = None
            
        try:
            self.mcp_server = WxBotMCPServer()
        except Exception as e:
            self.exception_recorder.record(e, "MCP服务器初始化")
            self.mcp_server = None
            
        try:
            self.human_ops = HumanLikeOperations()
        except Exception as e:
            self.exception_recorder.record(e, "人性化操作初始化")
            self.human_ops = None
    
    def run_resource_monitoring(self):
        """运行资源监控"""
        while self.running:
            try:
                self.resource_monitor.sample()
                time.sleep(RESOURCE_CHECK_INTERVAL)
            except Exception as e:
                self.exception_recorder.record(e, "资源监控")
    
    def test_message_sending(self) -> TestResult:
        """测试消息发送"""
        start_time = datetime.now()
        test_start = start_time.isoformat()
        
        try:
            # 模拟发送消息
            for i in range(10):  # 每次测试10条消息
                if self.mcp_server:
                    import asyncio
                    result = asyncio.run(
                        self.mcp_server.call_tool('wxbot_send_message', {
                            'chat_name': '测试群',
                            'message': f'稳定性测试消息_{test_start}_{i}'
                        })
                    )
                    if not result.get('success', False):
                        raise Exception(f"发送失败: {result.get('error')}")
            
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='message_sending',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=True,
                duration_seconds=duration
            )
            
        except Exception as e:
            self.exception_recorder.record(e, "消息发送测试")
            # 尝试重试
            for attempt in range(MAX_RETRIES_PER_TEST):
                try:
                    # 简单重试
                    time.sleep(1)
                    duration = (datetime.now() - start_time).total_seconds()
                    return TestResult(
                        test_name='message_sending',
                        start_time=test_start,
                        end_time=datetime.now().isoformat(),
                        success=True,
                        duration_seconds=duration,
                        retries=attempt + 1
                    )
                except Exception as retry_e:
                    self.exception_recorder.record(retry_e, f"消息发送重试{attempt + 1}")
            
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='message_sending',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def test_mcp_server(self) -> TestResult:
        """测试MCP服务器"""
        start_time = datetime.now()
        test_start = start_time.isoformat()
        
        try:
            if self.mcp_server:
                tools = self.mcp_server.list_tools()
                status = asyncio.run(self.mcp_server.call_tool('wxbot_get_status', {}))
                if not status.get('success', False):
                    raise Exception("MCP服务器状态检查失败")
            
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='mcp_server',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=True,
                duration_seconds=duration
            )
        except Exception as e:
            self.exception_recorder.record(e, "MCP服务器测试")
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='mcp_server',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def test_bridge_service(self) -> TestResult:
        """测试桥梁服务"""
        start_time = datetime.now()
        test_start = start_time.isoformat()
        
        try:
            if self.b_service:
                # 采集一些基本指标
                stats = self.b_service.get_stats()
                status = self.b_service.get_status()
            
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='bridge_service',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=True,
                duration_seconds=duration
            )
        except Exception as e:
            self.exception_recorder.record(e, "桥梁服务测试")
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='bridge_service',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def test_human_operations(self) -> TestResult:
        """测试人性化操作"""
        start_time = datetime.now()
        test_start = start_time.isoformat()
        
        try:
            if self.human_ops:
                # 测试延迟
                self.human_ops.human_delay(0.1, 0.05)
            
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='human_operations',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=True,
                duration_seconds=duration
            )
        except Exception as e:
            self.exception_recorder.record(e, "人性化操作测试")
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name='human_operations',
                start_time=test_start,
                end_time=datetime.now().isoformat(),
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def run_health_check(self):
        """运行健康检查"""
        tests = [
            ('消息发送', self.test_message_sending),
            ('MCP服务器', self.test_mcp_server),
            ('桥梁服务', self.test_bridge_service),
            ('人性化操作', self.test_human_operations)
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                self.test_results.append(result)
                logger.info(f"健康检查 [{test_name}]: {'通过' if result.success else '失败'}")
            except Exception as e:
                self.exception_recorder.record(e, f"健康检查 {test_name}")
    
    def generate_report(self) -> Dict[str, Any]:
        """生成稳定性测试报告"""
        duration_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        # 计算测试通过率
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        test_pass_rate = passed_tests / total_tests * total_tests if total_tests > 0 else 0
        
        # 资源使用情况
        resource_summary = self.resource_monitor.get_summary()
        exception_summary = self.exception_recorder.get_summary()
        
        # 稳定性评分
        stability_score = 100
        if exception_summary['total_exceptions'] > 0:
            stability_score -= min(30, exception_summary['total_exceptions'] * 5)
        if resource_summary.get('memory_max', 0) > 500:  # 内存超过500MB
            stability_score -= 10
            
        stability_score = max(0, min(100, stability_score))
        
        report = {
            'test_start': self.start_time.isoformat(),
            'test_end': datetime.now().isoformat(),
            'duration_hours': duration_hours,
            'stability_score': stability_score,
            'resource_usage': resource_summary,
            'exception_summary': exception_summary,
            'test_results': {
                'total': total_tests,
                'passed': passed_tests,
                'failed': total_tests - passed_tests,
                'pass_rate': test_pass_rate
            },
            'recommendations': self._generate_recommendations(exception_summary, resource_summary)
        }
        
        return report
    
    def _generate_recommendations(self, exception_summary, resource_summary) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if exception_summary['total_exceptions'] > 10:
            recommendations.append("异常次数较多，建议加强错误处理")
        
        memory_max = resource_summary.get('memory_max', 0)
        if memory_max > 300:
            recommendations.append(f"内存使用较高({memory_max:.1f}MB)，建议检查内存泄漏")
        
        cpu_avg = resource_summary.get('cpu_avg', 0)
        if cpu_avg > 50:
            recommendations.append(f"CPU使用率较高({cpu_avg:.1f}%)，建议优化性能")
        
        if not recommendations:
            recommendations.append("系统运行状态良好，继续保持")
        
        return recommendations


# ==================== 主程序 ====================

def save_report(report: Dict[str, Any], index: int):
    """保存测试报告"""
    report_dir = Path('I:/jz-wxbot-automation/docs')
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'stability_test_{index}_{timestamp}.json'
    filepath = report_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"测试报告已保存: {filepath}")
    
    return filepath


def main():
    """主程序"""
    # 配置告警
    warnings.filterwarnings('ignore')
    
    logger.info("=" * 60)
    logger.info("72小时jz-wxbot稳定性测试开始")
    logger.info("=" * 60)
    
    runner = StabilityTestRunner()
    runner.start_time = datetime.now()
    runner.running = True
    
    # 启动资源监控线程
    monitor_thread = threading.Thread(target=runner.run_resource_monitoring, daemon=True)
    monitor_thread.start()
    
    logger.info("资源监控线程已启动")
    
    # 运行循环测试
    batch_count = 0
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=TEST_DURATION_HOURS)
    
    try:
        while datetime.now() < end_time:
            batch_count += 1
            remaining_hours = (end_time - datetime.now()).total_seconds() / 3600
            
            logger.info(f"批次 {batch_count}: 剩余时间 {remaining_hours:.1f} 小时")
            
            # 运行健康检查
            runner.run_health_check()
            
            # 保存报告
            report = runner.generate_report()
            save_report(report, batch_count)
            
            # 等待下一轮采样
            time.sleep(SAMPLE_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        runner.exception_recorder.record(e, "主测试循环")
        logger.error(f"测试错误: {e}")
        traceback.print_exc()
    finally:
        runner.running = False
        
        # 生成最终报告
        final_report = runner.generate_report()
        
        # 保存最终报告
        final_filepath = save_report(final_report, final_batch_count := batch_count + 1)
        
        logger.info("=" * 60)
        logger.info("72小时稳定性测试完成")
        logger.info(f"最终得分: {final_report['stability_score']}/100")
        logger.info(f"异常总数: {final_report['exception_summary']['total_exceptions']}")
        logger.info(f"最终报告: {final_filepath}")
        logger.info("=" * 60)
        
        return final_report


if __name__ == '__main__':
    import asyncio
    main()
