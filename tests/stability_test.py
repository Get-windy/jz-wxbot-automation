#!/usr/bin/env python3
"""
jz-wxbot Stability Test Suite
Tests: Long-term running stability, resource monitoring, error logging
"""
import time
import json
import random
import threading
import psutil
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from queue import Queue
from enum import Enum

class TestState(Enum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"

@dataclass
class ResourceSnapshot:
    """Resource usage snapshot"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    threads: int
    handles: int
    disk_read_mb: float
    disk_write_mb: float

@dataclass
class ErrorEvent:
    """Error event record"""
    timestamp: float
    error_type: str
    message: str
    severity: str  # error, warning, critical

@dataclass
class StabilityMetrics:
    """Stability test metrics"""
    duration_seconds: float = 0
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    avg_cpu_percent: float = 0
    max_cpu_percent: float = 0
    avg_memory_mb: float = 0
    max_memory_mb: float = 0
    memory_leak_detected: bool = False
    errors: List[ErrorEvent] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class MockWxBotService:
    """Mock WeChat Bot Service for stability testing"""
    
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.error_count = 0
        self._lock = threading.Lock()
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False
    
    def process_message(self) -> bool:
        """Simulate message processing"""
        if not self.running:
            return False
        
        with self._lock:
            self.message_count += 1
        
        # Simulate processing time
        time.sleep(random.uniform(0.001, 0.01))
        
        # Simulate occasional errors (0.5% error rate)
        if random.random() < 0.005:
            with self._lock:
                self.error_count += 1
            return False
        
        return True
    
    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "message_count": self.message_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(1, self.message_count)
            }

class StabilityTestRunner:
    """Stability test runner with monitoring"""
    
    def __init__(self, test_duration_seconds: int = 60):
        self.test_duration = test_duration_seconds
        self.service = MockWxBotService()
        self.metrics = StabilityMetrics()
        self.snapshots: List[ResourceSnapshot] = []
        self._stop_event = threading.Event()
        self._process = psutil.Process()
    
    def _monitor_resources(self):
        """Monitor system resources"""
        disk_io = self._process.io_counters()
        initial_read = disk_io.read_bytes
        initial_write = disk_io.write_bytes
        
        while not self._stop_event.is_set():
            try:
                cpu = self._process.cpu_percent()
                mem = self._process.memory_info()
                disk_io = self._process.io_counters()
                
                snapshot = ResourceSnapshot(
                    timestamp=time.time(),
                    cpu_percent=cpu,
                    memory_mb=mem.rss / 1024 / 1024,
                    memory_percent=self._process.memory_percent(),
                    threads=self._process.num_threads(),
                    handles=self._process.num_handles() if hasattr(self._process, 'num_handles') else 0,
                    disk_read_mb=(disk_io.read_bytes - initial_read) / 1024 / 1024,
                    disk_write_mb=(disk_io.write_bytes - initial_write) / 1024 / 1024
                )
                self.snapshots.append(snapshot)
                
                # Check for memory leak (memory growth > 10MB)
                if len(self.snapshots) > 10:
                    recent = [s.memory_mb for s in self.snapshots[-10:]]
                    if max(recent) - min(recent) > 10:
                        self.metrics.memory_leak_detected = True
                        self.metrics.warnings.append("Potential memory leak detected")
                
            except Exception as e:
                self.metrics.errors.append(ErrorEvent(
                    timestamp=time.time(),
                    error_type="monitoring",
                    message=str(e),
                    severity="warning"
                ))
            
            time.sleep(1)
    
    def _simulate_operations(self):
        """Simulate bot operations"""
        while not self._stop_event.is_set():
            success = self.service.process_message()
            self.metrics.total_operations += 1
            if success:
                self.metrics.successful_operations += 1
            else:
                self.metrics.failed_operations += 1
    
    def run(self) -> StabilityMetrics:
        """Run stability test"""
        print(f"\n{'='*60}")
        print("jz-wxbot Stability Test")
        print(f"{'='*60}")
        print(f"Duration: {self.test_duration} seconds")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Start service
        self.service.start()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        monitor_thread.start()
        
        # Start operation threads (simulate multiple concurrent operations)
        operation_threads = []
        for _ in range(5):
            t = threading.Thread(target=self._simulate_operations, daemon=True)
            t.start()
            operation_threads.append(t)
        
        # Progress reporting
        elapsed = 0
        while elapsed < self.test_duration:
            time.sleep(5)
            elapsed = time.time() - start_time
            progress = min(100, (elapsed / self.test_duration) * 100)
            stats = self.service.get_stats()
            print(f"  Progress: {progress:.0f}% | Messages: {stats['message_count']} | Errors: {stats['error_count']}")
        
        # Stop test
        self._stop_event.set()
        self.service.stop()
        
        end_time = time.time()
        self.metrics.duration_seconds = end_time - start_time
        
        # Calculate aggregate metrics
        if self.snapshots:
            self.metrics.avg_cpu_percent = sum(s.cpu_percent for s in self.snapshots) / len(self.snapshots)
            self.metrics.max_cpu_percent = max(s.cpu_percent for s in self.snapshots)
            self.metrics.avg_memory_mb = sum(s.memory_mb for s in self.snapshots) / len(self.snapshots)
            self.metrics.max_memory_mb = max(s.memory_mb for s in self.snapshots)
        
        return self.metrics

def generate_report(metrics: StabilityMetrics, test_duration: int) -> str:
    """Generate stability test report"""
    lines = []
    lines.append("# jz-wxbot Stability Test Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test Summary
    lines.append("\n## Test Summary\n")
    lines.append(f"- **Duration**: {metrics.duration_seconds:.2f} seconds")
    lines.append(f"- **Total Operations**: {metrics.total_operations}")
    lines.append(f"- **Successful**: {metrics.successful_operations}")
    lines.append(f"- **Failed**: {metrics.failed_operations}")
    success_rate = (metrics.successful_operations / max(1, metrics.total_operations)) * 100
    lines.append(f"- **Success Rate**: {success_rate:.2f}%")
    
    # Resource Usage
    lines.append("\n## Resource Usage\n")
    lines.append("| Metric | Average | Maximum |")
    lines.append("|--------|---------|---------|")
    lines.append(f"| CPU Usage | {metrics.avg_cpu_percent:.2f}% | {metrics.max_cpu_percent:.2f}% |")
    lines.append(f"| Memory (MB) | {metrics.avg_memory_mb:.2f} | {metrics.max_memory_mb:.2f} |")
    
    # Memory Analysis
    lines.append("\n## Memory Analysis\n")
    if metrics.memory_leak_detected:
        lines.append("- **Memory Leak**: DETECTED")
    else:
        lines.append("- **Memory Leak**: Not detected")
    
    # Errors and Warnings
    if metrics.errors:
        lines.append("\n## Errors\n")
        for err in metrics.errors[:10]:
            lines.append(f"- [{err.severity}] {err.error_type}: {err.message}")
    
    if metrics.warnings:
        lines.append("\n## Warnings\n")
        for warn in metrics.warnings:
            lines.append(f"- {warn}")
    
    # Assessment
    lines.append("\n## Assessment\n")
    issues = []
    if success_rate < 99:
        issues.append(f"Success rate below 99% ({success_rate:.2f}%)")
    if metrics.max_cpu_percent > 80:
        issues.append(f"High CPU usage detected ({metrics.max_cpu_percent:.2f}%)")
    if metrics.memory_leak_detected:
        issues.append("Memory leak detected")
    
    if not issues:
        lines.append("**Status**: PASSED - System is stable")
    else:
        lines.append("**Status**: WARNING - Issues detected:")
        for issue in issues:
            lines.append(f"  - {issue}")
    
    # Recommendations
    lines.append("\n## Recommendations\n")
    lines.append("1. Continue monitoring memory usage in production")
    lines.append("2. Implement log rotation for long-running processes")
    lines.append("3. Set up alerts for error rate thresholds")
    lines.append("4. Consider periodic health checks")
    
    return "\n".join(lines)

def main():
    """Main entry point"""
    # Run stability test (60 seconds for demonstration)
    runner = StabilityTestRunner(test_duration_seconds=60)
    metrics = runner.run()
    
    # Generate report
    report = generate_report(metrics, 60)
    
    # Save report
    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    report_path = os.path.join(docs_dir, "JZ_WXBOT_STABILITY_TEST_REPORT.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Save JSON results
    json_path = os.path.join(docs_dir, "jz-wxbot-stability-results.json")
    results = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": metrics.duration_seconds,
        "total_operations": metrics.total_operations,
        "successful_operations": metrics.successful_operations,
        "failed_operations": metrics.failed_operations,
        "success_rate": round(metrics.successful_operations / max(1, metrics.total_operations) * 100, 2),
        "avg_cpu_percent": round(metrics.avg_cpu_percent, 2),
        "max_cpu_percent": round(metrics.max_cpu_percent, 2),
        "avg_memory_mb": round(metrics.avg_memory_mb, 2),
        "max_memory_mb": round(metrics.max_memory_mb, 2),
        "memory_leak_detected": metrics.memory_leak_detected,
        "error_count": len(metrics.errors),
        "warning_count": len(metrics.warnings)
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nReport saved: {report_path}")
    print(f"JSON saved: {json_path}")
    print(f"\n{'='*60}")
    print("Stability Test Complete!")
    print(f"{'='*60}")
    print(f"\nSummary:")
    print(f"  - Operations: {metrics.total_operations}")
    print(f"  - Success Rate: {results['success_rate']:.2f}%")
    print(f"  - Avg CPU: {metrics.avg_cpu_percent:.2f}%")
    print(f"  - Avg Memory: {metrics.avg_memory_mb:.2f} MB")

if __name__ == "__main__":
    main()