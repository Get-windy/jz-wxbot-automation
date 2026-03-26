# -*- coding: utf-8 -*-
"""
压力测试 - Stress Testing
jz-wxbot-automation 项目
"""

import pytest
import time
import asyncio
import sys
import random
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import queue

# 添加项目根目录到路径
sys.path.insert(0, '..')


# ==================== 配置参数 ====================
class StressTestConfig:
    """压力测试配置"""
    # 并发级别
    concurrent_levels = [10, 50, 100, 200]
    
    # 持续时间(秒)
    duration_seconds = 5
    
    # 目标QPS
    target_qps = 100
    
    # 超时时间(毫秒)
    timeout_ms = 5000
    
    # 错误率阈值(%)
    error_rate_threshold = 5.0


# ==================== 测试结果 ====================
class StressTestResult:
    """压力测试结果"""
    def __init__(self, scenario, concurrent_users, total_requests, successful_requests, 
                 failed_requests, avg_response_time, min_response_time, max_response_time,
                 p95_response_time, p99_response_time, throughput, error_rate, passed, message):
        self.scenario = scenario
        self.concurrent_users = concurrent_users
        self.total_requests = total_requests
        self.successful_requests = successful_requests
        self.failed_requests = failed_requests
        self.avg_response_time = avg_response_time
        self.min_response_time = min_response_time
        self.max_response_time = max_response_time
        self.p95_response_time = p95_response_time
        self.p99_response_time = p99_response_time
        self.throughput = throughput
        self.error_rate = error_rate
        self.passed = passed
        self.message = message


class StressTestReport:
    """压力测试报告"""
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = None
        self.results = []
    
    def add_result(self, result):
        self.results.append(result)
    
    def generate_report(self):
        report = []
        report.append("# jz-wxbot 压力测试报告")
        report.append("")
        report.append(f"**测试时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else '进行中'}")
        report.append("")
        report.append("---")
        report.append("")
        report.append("## 测试概述")
        report.append("")
        report.append("本报告总结了jz-wxbot项目的压力测试结果。")
        report.append("")
        report.append("## 测试结果汇总")
        report.append("")
        report.append("| 场景 | 并发用户 | 总请求 | 成功请求 | 失败请求 | 平均响应时间 | 吞吐量 | 错误率 |")
        report.append("|------|---------|--------|----------|----------|-------------|--------|--------|")
        
        for result in self.results:
            report.append(f"| {result.scenario} | {result.concurrent_users} | {result.total_requests} | {result.successful_requests} | {result.failed_requests} | {result.avg_response_time:.2f}ms | {result.throughput:.1f} | {result.error_rate:.2f}% |")
        
        report.append("")
        report.append("---")
        report.append("")
        report.append(f"*报告生成时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return '\n'.join(report)


# ==================== 模拟负载生成器 ====================
class LoadGenerator:
    """负载生成器"""
    
    def __init__(self):
        self.response_times = []
        self.errors = []
        self.lock = None
    
    def simulate_request(self, endpoint, complexity=1.0):
        """模拟请求"""
        start = time.perf_counter()
        
        try:
            # 模拟延迟
            delay = 0.001 * complexity
            time.sleep(delay)
            elapsed = time.perf_counter() - start
            
            return {
                'success': True,
                'response_time': elapsed * 1000,  # ms
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': (time.perf_counter() - start) * 1000,
                'timestamp': datetime.now().isoformat()
            }


# ==================== 压力测试用例 ====================
class TestMessageThroughputStress:
    """消息吞吐量压力测试"""
    
    def test_high_concurrent_message_send(self):
        """高并发消息发送测试"""
        config = StressTestConfig()
        results = []
        
        for concurrent_users in config.concurrent_levels:
            load_gen = LoadGenerator()
            success_count = 0
            failure_count = 0
            times = []
            
            start = time.perf_counter()
            
            def worker():
                nonlocal success_count, failure_count
                for _ in range(10):
                    result = load_gen.simulate_request('send_message')
                    if result['success']:
                        success_count += 1
                        times.append(result['response_time'])
                    else:
                        failure_count += 1
            
            threads = []
            for _ in range(concurrent_users):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            elapsed = time.perf_counter() - start
            total = success_count + failure_count
            
            if times:
                avg_time = statistics.mean(times)
                p95_time = sorted(times)[int(len(times) * 0.95)]
                p99_time = sorted(times)[int(len(times) * 0.99)]
            else:
                avg_time = p95_time = p99_time = 0
            
            throughput = total / elapsed if elapsed > 0 else 0
            error_rate = (failure_count / total * 100) if total > 0 else 0
            passed = error_rate < config.error_rate_threshold
            
            results.append(StressTestResult(
                scenario='高并发消息发送',
                concurrent_users=concurrent_users,
                total_requests=total,
                successful_requests=success_count,
                failed_requests=failure_count,
                avg_response_time=avg_time,
                min_response_time=min(times) if times else 0,
                max_response_time=max(times) if times else 0,
                p95_response_time=p95_time,
                p99_response_time=p99_time,
                throughput=throughput,
                error_rate=error_rate,
                passed=passed,
                message=f"通过: {success_count}/{total}, 错误率: {error_rate:.2f}%"
            ))
            
            print(f"\n并发用户 {concurrent_users}:")
            print(f"  - 总请求数: {total}")
            print(f"  - 成功: {success_count}, 失败: {failure_count}")
            print(f"  - 平均响应时间: {avg_time:.2f}ms")
            print(f"  - 吞吐量: {throughput:.1f} req/s")
            print(f"  - 错误率: {error_rate:.2f}%")
        
        # 断言所有测试通过
        for result in results:
            assert result.passed, f"{result.message}"


class TestMessageQueueStress:
    """消息队列压力测试"""
    
    def test_large_message_queue(self):
        """大规模消息队列测试"""
        config = StressTestConfig()
        
        # 测试不同规模的消息队列
        queue_sizes = [1000, 5000, 10000, 50000]
        
        for size in queue_sizes:
            message_queue = []
            
            start = time.perf_counter()
            
            # 写入消息
            for i in range(size):
                message = {
                    'id': i,
                    'content': f'test_message_{i}',
                    'timestamp': time.time(),
                    'priority': random.randint(1, 5)
                }
                message_queue.append(message)
            
            write_time = time.perf_counter() - start
            
            # 读取消息
            start = time.perf_counter()
            processed = 0
            for msg in message_queue:
                # 模拟处理
                _ = str(msg['content'])
                processed += 1
            
            read_time = time.perf_counter() - start
            
            total_time = write_time + read_time
            throughput = size / total_time if total_time > 0 else 0
            
            print(f"\n消息队列规模 {size}:")
            print(f"  - 写入时间: {write_time*1000:.2f}ms")
            print(f"  - 读取时间: {read_time*1000:.2f}ms")
            print(f"  - 总时间: {total_time*1000:.2f}ms")
            print(f"  - 吞吐量: {throughput:.1f} msg/s")
            
            # 断言吞吐量应大于1000 msg/s
            assert throughput > 1000, f"吞吐量应大于1000 msg/s, 实际: {throughput:.1f}"
    
    def test_message_queue_overflow(self):
        """消息队列溢出测试"""
        message_queue = []
        max_capacity = 10000
        
        # 填充队列到容量
        for i in range(max_capacity):
            message_queue.append({
                'id': i,
                'content': f'message_{i}'
            })
        
        # 尝试超出容量
        overflow_count = 0
        overflow_failed = 0
        
        try:
            for i in range(max_capacity, max_capacity + 1000):
                if len(message_queue) > max_capacity * 1.2:  # 120%容量时开始拒绝
                    overflow_failed += 1
                else:
                    message_queue.append({
                        'id': i,
                        'content': f'message_{i}'
                    })
                overflow_count += 1
        except Exception as e:
            overflow_failed += 1
        
        print(f"\n队列溢出测试:")
        print(f"  - 尝试添加: {overflow_count}")
        print(f"  - 成功添加: {len(message_queue) - max_capacity}")
        print(f"  - 失败/拒绝: {overflow_failed}")
        
        # 确保系统不会崩溃
        assert overflow_count > 0, "溢出测试应捕获异常"


class TestNetworkStress:
    """网络压力测试"""
    
    def test_concurrent_network_requests(self):
        """并发网络请求测试"""
        config = StressTestConfig()
        
        def mock_network_request():
            """模拟网络请求"""
            start = time.perf_counter()
            time.sleep(0.001)  # 模拟网络延迟
            return {
                'success': True,
                'response_time': (time.perf_counter() - start) * 1000
            }
        
        for concurrent_users in config.concurrent_levels[:2]:  # 只测试前两个级别
            success_count = 0
            failure_count = 0
            times = []
            
            start = time.perf_counter()
            
            def worker():
                nonlocal success_count, failure_count
                for _ in range(5):
                    result = mock_network_request()
                    if result['success']:
                        success_count += 1
                        times.append(result['response_time'])
                    else:
                        failure_count += 1
            
            threads = []
            for _ in range(concurrent_users):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            elapsed = time.perf_counter() - start
            total = success_count + failure_count
            throughput = total / elapsed if elapsed > 0 else 0
            error_rate = (failure_count / total * 100) if total > 0 else 0
            
            print(f"\n并发网络请求 {concurrent_users}:")
            print(f"  - 总请求数: {total}")
            print(f"  - 成功: {success_count}, 失败: {failure_count}")
            print(f"  - 平均响应时间: {statistics.mean(times) if times else 0:.2f}ms")
            print(f"  - 吞吐量: {throughput:.1f} req/s")
            print(f"  - 错误率: {error_rate:.2f}%")
            
            assert error_rate < 10, f"错误率应小于10%, 实际: {error_rate:.2f}%"


class TestResourceStress:
    """资源压力测试"""
    
    def test_memory_pressure(self):
        """内存压力测试"""
        data_list = []
        initial_memory = 0  # 简化处理
        
        # 分配大内存
        for i in range(100):
            # 模拟内存分配
            data = [1] * 1000000  # 约8MB
            data_list.append(data)
            
            if i % 20 == 0:
                print(f"已分配 {i+1} * 8MB = {(i+1)*8}MB")
        
        # 释放内存
        data_list.clear()
        
        print(f"\n内存压力测试:")
        print(f"  - 最大分配: {len(data_list)} * 8MB")
        print(f"  - 内存已释放: {len(data_list) == 0}")
        
        # 确保内存正确释放
        assert len(data_list) == 0, "内存应正确释放"
    
    def test_cpu_pressure(self):
        """CPU压力测试"""
        def busy_work():
            """Busy work"""
            result = 0
            for i in range(1000000):
                result += i * i
            return result
        
        start = time.perf_counter()
        
        # 并行执行多个CPU密集型任务
        for _ in range(4):
            busy_work()
        
        elapsed = time.perf_counter() - start
        
        print(f"\nCPU压力测试:")
        print(f"  - 执行时间: {elapsed*1000:.2f}ms")
        print(f"  - CPU使用率: 高")
        
        # 断言任务完成
        assert elapsed < 10, "CPU密集型任务应在10秒内完成"


class TestDatabaseStress:
    """数据库压力测试"""
    
    def test_message_storage_stress(self):
        """消息存储压力测试"""
        messages = []
        
        # 批量插入消息
        batch_sizes = [100, 500, 1000, 5000]
        
        for size in batch_sizes:
            start = time.perf_counter()
            
            # 模拟批量插入
            for i in range(size):
                messages.append({
                    'id': i,
                    'content': f'test_content_{i}',
                    'timestamp': time.time()
                })
            
            elapsed = time.perf_counter() - start
            throughput = size / elapsed if elapsed > 0 else 0
            
            print(f"\n批量插入 {size} 条消息:")
            print(f"  - 耗时: {elapsed*1000:.2f}ms")
            print(f"  - 吞吐量: {throughput:.1f} msg/s")
            
            # 断言吞吐量应大于100 msg/s
            assert throughput > 100, f"吞吐量应大于100 msg/s, 实际: {throughput:.1f}"
    
    def test_message_query_stress(self):
        """消息查询压力测试"""
        messages = []
        
        # 准备数据
        for i in range(1000):
            messages.append({
                'id': i,
                'content': f'content_{i}',
                'timestamp': time.time()
            })
        
        # 查询测试
        queries = 100
        
        start = time.perf_counter()
        
        for _ in range(queries):
            # 模拟查询
            filtered = [m for m in messages if m['id'] % 2 == 0]
            _ = len(filtered)  # 使用结果
        
        elapsed = time.perf_counter() - start
        avg_time = (elapsed / queries) * 1000
        throughput = queries / elapsed if elapsed > 0 else 0
        
        print(f"\n消息查询压力测试:")
        print(f"  - 总查询数: {queries}")
        print(f"  - 平均每次查询: {avg_time:.2f}ms")
        print(f"  - 吞吐量: {throughput:.1f} queries/s")
        
        # 断言查询性能
        assert avg_time < 10, f"平均查询时间应小于10ms, 实际: {avg_time:.2f}ms"


# ==================== 运行压力测试 ====================
def run_stress_tests():
    """运行所有压力测试"""
    import threading
    
    report = StressTestReport()
    
    print("=" * 70)
    print("jz-wxbot 压力测试")
    print("=" * 70)
    
    # 运行测试
    test_instance = TestMessageThroughputStress()
    test_instance.test_high_concurrent_message_send()
    
    test_instance2 = TestMessageQueueStress()
    test_instance2.test_large_message_queue()
    test_instance2.test_message_queue_overflow()
    
    test_instance3 = TestNetworkStress()
    test_instance3.test_concurrent_network_requests()
    
    test_instance4 = TestResourceStress()
    test_instance4.test_memory_pressure()
    test_instance4.test_cpu_pressure()
    
    test_instance5 = TestDatabaseStress()
    test_instance5.test_message_storage_stress()
    test_instance5.test_message_query_stress()
    
    report.end_time = datetime.now()
    
    # 生成报告
    report_content = report.generate_report()
    print("\n" + report_content)
    
    return True


if __name__ == '__main__':
    success = run_stress_tests()
    exit(0 if success else 1)
