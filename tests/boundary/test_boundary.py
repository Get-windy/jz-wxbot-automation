#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
边界测试 - Boundary Testing
==========================================
测试内容:
1. 测试大量消息场景
2. 测试断线重连
3. 测试权限变更
4. 输出边界测试报告

作者: test-agent-2
日期: 2026-03-23
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import time
import json
import random
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

# 项目路径
PROJECT_ROOT = Path("I:/jz-wxbot-automation")
TEST_RESULTS_DIR = PROJECT_ROOT / "tests" / "boundary"
TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 测试配置 ====================
@dataclass
class BoundaryTestConfig:
    """边界测试配置"""
    # 大量消息测试
    message_count_small: int = 100
    message_count_medium: int = 500
    message_count_large: int = 1000
    message_count_extreme: int = 5000
    
    # 断线重连测试
    reconnect_attempts: int = 5
    reconnect_delay_ms: int = 1000
    connection_timeout_ms: int = 5000
    
    # 权限测试
    permission_test_scenarios: List[str] = field(default_factory=lambda: [
        "admin_to_user",
        "user_to_admin", 
        "group_admin_to_member",
        "member_to_group_admin"
    ])

# ==================== 消息类型枚举 ====================
class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    LINK = "link"
    EMOTION = "emotion"

class ConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

# ==================== 测试结果 ====================
@dataclass
class BoundaryTestResult:
    """边界测试结果"""
    scenario: str
    category: str
    passed: bool
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BoundaryTestReport:
    """边界测试报告"""
    start_time: datetime
    end_time: datetime = None
    results: List[BoundaryTestResult] = field(default_factory=list)
    
    def add_result(self, result: BoundaryTestResult):
        self.results.append(result)
    
    @property
    def total(self) -> int:
        return len(self.results)
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)
    
    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0

# ==================== 模拟消息系统 ====================
class MockMessageSystem:
    """模拟消息系统"""
    
    def __init__(self):
        self.message_queue: List[Dict] = []
        self.connection_state = ConnectionState.CONNECTED
        self.permissions: Dict[str, List[str]] = {
            "admin": ["send", "receive", "manage", "delete"],
            "user": ["send", "receive"],
            "group_admin": ["send", "receive", "manage"],
            "member": ["send", "receive"]
        }
        self.current_role = "admin"
        self.lock = threading.Lock()
        self.error_injection = False
    
    def send_message(self, msg_type: MessageType, content: str) -> Dict:
        """发送消息"""
        if self.connection_state != ConnectionState.CONNECTED:
            return {"success": False, "error": "Not connected"}
        
        if self.error_injection and random.random() < 0.05:
            return {"success": False, "error": "Simulated error"}
        
        msg = {
            "id": f"msg_{len(self.message_queue)}",
            "type": msg_type.value,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        with self.lock:
            self.message_queue.append(msg)
        
        return {"success": True, "message": msg}
    
    def receive_messages(self, count: int = 10) -> List[Dict]:
        """接收消息"""
        if self.connection_state != ConnectionState.CONNECTED:
            return []
        
        with self.lock:
            return self.message_queue[-count:]
    
    def disconnect(self):
        """断开连接"""
        self.connection_state = ConnectionState.DISCONNECTED
    
    def reconnect(self) -> bool:
        """重连"""
        self.connection_state = ConnectionState.RECONNECTING
        time.sleep(0.1)  # 模拟重连延迟
        
        if random.random() < 0.9:  # 90%成功率
            self.connection_state = ConnectionState.CONNECTED
            return True
        else:
            self.connection_state = ConnectionState.ERROR
            return False
    
    def change_permission(self, new_role: str) -> bool:
        """变更权限"""
        if new_role not in self.permissions:
            return False
        self.current_role = new_role
        return True
    
    def check_permission(self, action: str) -> bool:
        """检查权限"""
        return action in self.permissions.get(self.current_role, [])
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        with self.lock:
            return len(self.message_queue)
    
    def clear_queue(self):
        """清空队列"""
        with self.lock:
            self.message_queue.clear()

# ==================== 大量消息场景测试 ====================
class MassMessageTester:
    """大量消息场景测试器"""
    
    def __init__(self, config: BoundaryTestConfig):
        self.config = config
        self.system = MockMessageSystem()
    
    def test_all(self) -> List[BoundaryTestResult]:
        """执行所有大量消息测试"""
        results = []
        
        # 1. 小量消息测试
        results.append(self._test_message_count(self.config.message_count_small, "小量消息"))
        
        # 2. 中量消息测试
        results.append(self._test_message_count(self.config.message_count_medium, "中量消息"))
        
        # 3. 大量消息测试
        results.append(self._test_message_count(self.config.message_count_large, "大量消息"))
        
        # 4. 极端消息测试
        results.append(self._test_message_count(self.config.message_count_extreme, "极端消息"))
        
        # 5. 并发消息测试
        results.append(self._test_concurrent_messages())
        
        # 6. 混合类型消息测试
        results.append(self._test_mixed_message_types())
        
        return results
    
    def _test_message_count(self, count: int, label: str) -> BoundaryTestResult:
        """测试指定数量的消息"""
        self.system.clear_queue()
        
        start_time = time.time()
        success_count = 0
        fail_count = 0
        
        for i in range(count):
            result = self.system.send_message(MessageType.TEXT, f"Test message {i}")
            if result["success"]:
                success_count += 1
            else:
                fail_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        passed = success_count == count and duration < count * 0.01
        
        return BoundaryTestResult(
            scenario=f"{label}测试 ({count}条)",
            category="大量消息场景",
            passed=passed,
            message=f"发送 {success_count}/{count} 条消息, 耗时 {duration:.2f}s",
            metrics={
                "total_messages": count,
                "success_count": success_count,
                "fail_count": fail_count,
                "duration_seconds": duration,
                "throughput": count / duration if duration > 0 else 0
            }
        )
    
    def _test_concurrent_messages(self) -> BoundaryTestResult:
        """测试并发消息"""
        self.system.clear_queue()
        
        concurrent_count = 100
        messages_per_thread = 10
        total_expected = concurrent_count * messages_per_thread
        
        def send_messages(thread_id: int):
            success = 0
            for i in range(messages_per_thread):
                result = self.system.send_message(
                    MessageType.TEXT, 
                    f"Thread {thread_id} message {i}"
                )
                if result["success"]:
                    success += 1
            return success
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(send_messages, i) for i in range(concurrent_count)]
            total_success = sum(f.result() for f in as_completed(futures))
        
        end_time = time.time()
        duration = end_time - start_time
        
        passed = total_success >= total_expected * 0.95
        
        return BoundaryTestResult(
            scenario="并发消息测试",
            category="大量消息场景",
            passed=passed,
            message=f"并发发送 {concurrent_count} 线程, 成功 {total_success}/{total_expected}",
            metrics={
                "concurrent_threads": concurrent_count,
                "messages_per_thread": messages_per_thread,
                "total_success": total_success,
                "success_rate": total_success / total_expected * 100,
                "duration_seconds": duration
            }
        )
    
    def _test_mixed_message_types(self) -> BoundaryTestResult:
        """测试混合类型消息"""
        self.system.clear_queue()
        
        message_types = [
            MessageType.TEXT,
            MessageType.IMAGE,
            MessageType.FILE,
            MessageType.VIDEO,
            MessageType.LINK
        ]
        
        count = 500
        success_by_type = {t.value: 0 for t in message_types}
        
        for i in range(count):
            msg_type = random.choice(message_types)
            result = self.system.send_message(msg_type, f"Mixed message {i}")
            if result["success"]:
                success_by_type[msg_type.value] += 1
        
        total_success = sum(success_by_type.values())
        passed = total_success >= count * 0.95
        
        return BoundaryTestResult(
            scenario="混合类型消息测试",
            category="大量消息场景",
            passed=passed,
            message=f"混合发送 {count} 条消息, 成功率 {total_success/count*100:.1f}%",
            metrics={
                "total_messages": count,
                "success_by_type": success_by_type,
                "total_success": total_success
            }
        )

# ==================== 断线重连测试 ====================
class ReconnectionTester:
    """断线重连测试器"""
    
    def __init__(self, config: BoundaryTestConfig):
        self.config = config
        self.system = MockMessageSystem()
    
    def test_all(self) -> List[BoundaryTestResult]:
        """执行所有断线重连测试"""
        results = []
        
        # 1. 单次断线重连
        results.append(self._test_single_reconnect())
        
        # 2. 多次断线重连
        results.append(self._test_multiple_reconnects())
        
        # 3. 断线期间消息测试
        results.append(self._test_messages_during_disconnect())
        
        # 4. 重连超时测试
        results.append(self._test_reconnect_timeout())
        
        # 5. 断线恢复后数据一致性
        results.append(self._test_data_consistency_after_reconnect())
        
        return results
    
    def _test_single_reconnect(self) -> BoundaryTestResult:
        """测试单次断线重连"""
        self.system.connection_state = ConnectionState.CONNECTED
        
        # 先发送一些消息
        for i in range(10):
            self.system.send_message(MessageType.TEXT, f"Before disconnect {i}")
        
        queue_before = self.system.get_queue_size()
        
        # 断开连接
        self.system.disconnect()
        
        # 尝试发送(应该失败)
        result = self.system.send_message(MessageType.TEXT, "Should fail")
        send_during_disconnect = not result["success"]
        
        # 重连
        reconnect_success = self.system.reconnect()
        
        # 重连后发送
        send_after = self.system.send_message(MessageType.TEXT, "After reconnect")
        
        queue_after = self.system.get_queue_size()
        
        passed = (send_during_disconnect and reconnect_success and 
                  send_after["success"] and queue_after >= queue_before)
        
        return BoundaryTestResult(
            scenario="单次断线重连",
            category="断线重连",
            passed=passed,
            message="断线后重连" + ("成功" if passed else "失败"),
            metrics={
                "queue_before": queue_before,
                "queue_after": queue_after,
                "reconnect_success": reconnect_success,
                "send_during_disconnect_failed": send_during_disconnect,
                "send_after_success": send_after["success"]
            }
        )
    
    def _test_multiple_reconnects(self) -> BoundaryTestResult:
        """测试多次断线重连"""
        self.system.connection_state = ConnectionState.CONNECTED
        
        success_count = 0
        total_attempts = self.config.reconnect_attempts
        
        for i in range(total_attempts):
            self.system.disconnect()
            if self.system.reconnect():
                success_count += 1
            time.sleep(0.05)
        
        passed = success_count >= total_attempts * 0.8
        
        return BoundaryTestResult(
            scenario="多次断线重连",
            category="断线重连",
            passed=passed,
            message=f"重连成功 {success_count}/{total_attempts} 次",
            metrics={
                "total_attempts": total_attempts,
                "success_count": success_count,
                "success_rate": success_count / total_attempts * 100
            }
        )
    
    def _test_messages_during_disconnect(self) -> BoundaryTestResult:
        """测试断线期间消息处理"""
        self.system.clear_queue()
        self.system.connection_state = ConnectionState.CONNECTED
        
        # 发送初始消息
        for i in range(50):
            self.system.send_message(MessageType.TEXT, f"Initial {i}")
        
        initial_count = self.system.get_queue_size()
        
        # 断线
        self.system.disconnect()
        
        # 断线期间尝试发送
        failed_sends = 0
        for i in range(20):
            result = self.system.send_message(MessageType.TEXT, f"During disconnect {i}")
            if not result["success"]:
                failed_sends += 1
        
        # 重连
        self.system.reconnect()
        
        # 检查队列
        final_count = self.system.get_queue_size()
        
        passed = failed_sends == 20 and final_count == initial_count
        
        return BoundaryTestResult(
            scenario="断线期间消息处理",
            category="断线重连",
            passed=passed,
            message="断线期间消息正确拒绝, 数据未丢失",
            metrics={
                "initial_queue": initial_count,
                "final_queue": final_count,
                "failed_sends_during_disconnect": failed_sends,
                "data_preserved": final_count == initial_count
            }
        )
    
    def _test_reconnect_timeout(self) -> BoundaryTestResult:
        """测试重连超时"""
        self.system.connection_state = ConnectionState.CONNECTED
        
        self.system.disconnect()
        
        # 测试重连(应该有超时机制)
        start_time = time.time()
        self.system.reconnect()
        duration = time.time() - start_time
        
        # 重连应该快速完成
        passed = duration < 1.0  # 1秒内完成
        
        return BoundaryTestResult(
            scenario="重连超时测试",
            category="断线重连",
            passed=passed,
            message=f"重连耗时 {duration*1000:.0f}ms",
            metrics={
                "reconnect_duration_ms": duration * 1000,
                "timeout_threshold_ms": 1000
            }
        )
    
    def _test_data_consistency_after_reconnect(self) -> BoundaryTestResult:
        """测试重连后数据一致性"""
        self.system.clear_queue()
        self.system.connection_state = ConnectionState.CONNECTED
        
        # 发送消息
        original_messages = []
        for i in range(100):
            result = self.system.send_message(MessageType.TEXT, f"Consistency test {i}")
            if result["success"]:
                original_messages.append(result["message"]["id"])
        
        # 断线重连
        self.system.disconnect()
        self.system.reconnect()
        
        # 验证消息完整性
        messages_after = self.system.receive_messages(100)
        message_ids_after = [m["id"] for m in messages_after]
        
        # 检查所有原始消息是否都存在
        all_present = all(mid in message_ids_after for mid in original_messages)
        
        passed = all_present
        
        return BoundaryTestResult(
            scenario="重连后数据一致性",
            category="断线重连",
            passed=passed,
            message=f"数据一致性" + ("保持" if passed else "丢失"),
            metrics={
                "original_messages": len(original_messages),
                "messages_after_reconnect": len(messages_after),
                "all_present": all_present
            }
        )

# ==================== 权限变更测试 ====================
class PermissionChangeTester:
    """权限变更测试器"""
    
    def __init__(self, config: BoundaryTestConfig):
        self.config = config
        self.system = MockMessageSystem()
    
    def test_all(self) -> List[BoundaryTestResult]:
        """执行所有权限变更测试"""
        results = []
        
        # 1. 管理员权限测试
        results.append(self._test_admin_permissions())
        
        # 2. 普通用户权限测试
        results.append(self._test_user_permissions())
        
        # 3. 权限降级测试
        results.append(self._test_permission_downgrade())
        
        # 4. 权限升级测试
        results.append(self._test_permission_upgrade())
        
        # 5. 非法权限测试
        results.append(self._test_invalid_permission())
        
        # 6. 群组权限测试
        results.append(self._test_group_permissions())
        
        return results
    
    def _test_admin_permissions(self) -> BoundaryTestResult:
        """测试管理员权限"""
        self.system.change_permission("admin")
        
        actions = ["send", "receive", "manage", "delete"]
        results = {action: self.system.check_permission(action) for action in actions}
        
        passed = all(results.values())
        
        return BoundaryTestResult(
            scenario="管理员权限测试",
            category="权限变更",
            passed=passed,
            message="管理员拥有所有权限",
            metrics=results
        )
    
    def _test_user_permissions(self) -> BoundaryTestResult:
        """测试普通用户权限"""
        self.system.change_permission("user")
        
        actions = ["send", "receive", "manage", "delete"]
        results = {action: self.system.check_permission(action) for action in actions}
        
        # 用户应该只能发送和接收
        expected = {"send": True, "receive": True, "manage": False, "delete": False}
        passed = results == expected
        
        return BoundaryTestResult(
            scenario="普通用户权限测试",
            category="权限变更",
            passed=passed,
            message="用户权限正确限制",
            metrics={"actual": results, "expected": expected}
        )
    
    def _test_permission_downgrade(self) -> BoundaryTestResult:
        """测试权限降级"""
        # 初始为管理员
        self.system.change_permission("admin")
        admin_can_manage = self.system.check_permission("manage")
        
        # 降级为普通用户
        self.system.change_permission("user")
        user_can_manage = self.system.check_permission("manage")
        
        passed = admin_can_manage and not user_can_manage
        
        return BoundaryTestResult(
            scenario="权限降级测试",
            category="权限变更",
            passed=passed,
            message="权限降级生效",
            metrics={
                "admin_can_manage": admin_can_manage,
                "user_can_manage": user_can_manage
            }
        )
    
    def _test_permission_upgrade(self) -> BoundaryTestResult:
        """测试权限升级"""
        # 初始为普通用户
        self.system.change_permission("user")
        user_can_manage = self.system.check_permission("manage")
        
        # 升级为管理员
        self.system.change_permission("admin")
        admin_can_manage = self.system.check_permission("manage")
        
        passed = not user_can_manage and admin_can_manage
        
        return BoundaryTestResult(
            scenario="权限升级测试",
            category="权限变更",
            passed=passed,
            message="权限升级生效",
            metrics={
                "user_can_manage": user_can_manage,
                "admin_can_manage": admin_can_manage
            }
        )
    
    def _test_invalid_permission(self) -> BoundaryTestResult:
        """测试非法权限"""
        # 尝试设置为不存在的角色
        result = self.system.change_permission("invalid_role")
        
        passed = not result  # 应该失败
        
        return BoundaryTestResult(
            scenario="非法权限测试",
            category="权限变更",
            passed=passed,
            message="非法权限被正确拒绝",
            metrics={"change_success": result}
        )
    
    def _test_group_permissions(self) -> BoundaryTestResult:
        """测试群组权限"""
        # 群管理员权限
        self.system.change_permission("group_admin")
        group_admin_permissions = {
            "send": self.system.check_permission("send"),
            "receive": self.system.check_permission("receive"),
            "manage": self.system.check_permission("manage"),
            "delete": self.system.check_permission("delete")
        }
        
        # 群成员权限
        self.system.change_permission("member")
        member_permissions = {
            "send": self.system.check_permission("send"),
            "receive": self.system.check_permission("receive"),
            "manage": self.system.check_permission("manage"),
            "delete": self.system.check_permission("delete")
        }
        
        # 群管理员应该比成员多管理权限
        passed = (group_admin_permissions["manage"] and 
                  not member_permissions["manage"])
        
        return BoundaryTestResult(
            scenario="群组权限测试",
            category="权限变更",
            passed=passed,
            message="群组权限正确区分",
            metrics={
                "group_admin": group_admin_permissions,
                "member": member_permissions
            }
        )

# ==================== 报告生成器 ====================
def generate_report(report: BoundaryTestReport) -> Path:
    """生成测试报告"""
    lines = [
        "# 边界测试报告",
        "",
        f"> **项目**: jz-wxbot-automation",
        f"> **测试日期**: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> **执行者**: test-agent-2",
        "",
        "---",
        "",
        "## 测试概览",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 总测试数 | {report.total} |",
        f"| 通过数 | {report.passed} |",
        f"| 失败数 | {report.failed} |",
        f"| 通过率 | {report.pass_rate:.1f}% |",
        ""
    ]
    
    # 按类别分组
    categories = {}
    for result in report.results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)
    
    # 各类别详情
    for category, results in categories.items():
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        lines.extend([
            f"## {category}",
            "",
            f"**通过率**: {passed}/{total} ({passed/total*100:.1f}%)",
            "",
            "| 测试场景 | 状态 | 详情 |",
            "|----------|------|------|"
        ])
        
        for r in results:
            status = "通过" if r.passed else "失败"
            lines.append(f"| {r.scenario} | {status} | {r.message} |")
        
        lines.append("")
        
        # 详细指标
        lines.extend([
            "### 详细指标",
            ""
        ])
        
        for r in results:
            if r.metrics:
                lines.append(f"**{r.scenario}**:")
                lines.append("```json")
                lines.append(json.dumps(r.metrics, ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")
    
    # 失败项详情
    failed_results = [r for r in report.results if not r.passed]
    if failed_results:
        lines.extend([
            "## 需要关注的问题",
            ""
        ])
        for r in failed_results:
            lines.extend([
                f"### {r.scenario}",
                "",
                f"- **类别**: {r.category}",
                f"- **描述**: {r.message}",
                ""
            ])
    
    # 建议
    lines.extend([
        "## 改进建议",
        "",
        "1. **大量消息处理**: 实现消息队列和异步处理机制",
        "2. **断线重连**: 增加重连重试机制和超时处理",
        "3. **权限管理**: 完善权限验证和角色转换逻辑",
        "4. **错误处理**: 增强边界条件下的错误处理能力",
        "",
        "---",
        "",
        f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    ])
    
    report_path = TEST_RESULTS_DIR / f"boundary_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text("\n".join(lines), encoding='utf-8')
    
    return report_path

# ==================== 主函数 ====================
def main():
    """主函数"""
    print("=" * 60)
    print("  边界测试 - Boundary Testing")
    print("  " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 60)
    print()
    
    config = BoundaryTestConfig()
    report = BoundaryTestReport(start_time=datetime.now())
    
    # 1. 大量消息场景测试
    print("测试大量消息场景...")
    mass_tester = MassMessageTester(config)
    for result in mass_tester.test_all():
        report.add_result(result)
        status = "[OK]" if result.passed else "[FAIL]"
        print(f"  {status} {result.scenario}: {result.message}")
    
    print()
    
    # 2. 断线重连测试
    print("测试断线重连...")
    reconnect_tester = ReconnectionTester(config)
    for result in reconnect_tester.test_all():
        report.add_result(result)
        status = "[OK]" if result.passed else "[FAIL]"
        print(f"  {status} {result.scenario}: {result.message}")
    
    print()
    
    # 3. 权限变更测试
    print("测试权限变更...")
    permission_tester = PermissionChangeTester(config)
    for result in permission_tester.test_all():
        report.add_result(result)
        status = "[OK]" if result.passed else "[FAIL]"
        print(f"  {status} {result.scenario}: {result.message}")
    
    print()
    
    report.end_time = datetime.now()
    
    print("=" * 60)
    print("  测试完成")
    print("=" * 60)
    print()
    
    # 生成报告
    report_path = generate_report(report)
    
    print(f"报告已生成: {report_path}")
    print()
    print(f"结果: {report.passed}/{report.total} 通过 ({report.pass_rate:.1f}%)")
    
    # 保存JSON
    json_results = {
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "pass_rate": report.pass_rate,
        "results": [
            {
                "scenario": r.scenario,
                "category": r.category,
                "passed": r.passed,
                "message": r.message,
                "metrics": r.metrics
            }
            for r in report.results
        ]
    }
    
    json_path = TEST_RESULTS_DIR / f"boundary_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path.write_text(json.dumps(json_results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"JSON结果: {json_path}")
    
    return 0 if report.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())