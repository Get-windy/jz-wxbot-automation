# jz-wxbot-automation 监控配置文档

**版本**: v1.0  
**创建时间**: 2026-03-23  
**适用对象**: 运维人员

---

## 📖 目录

1. [监控概述](#监控概述)
2. [健康检查端点](#健康检查端点)
3. [日志监控](#日志监控)
4. [性能监控](#性能监控)
5. [告警配置](#告警配置)
6. [监控仪表板](#监控仪表板)

---

## 监控概述

### 监控架构

```
┌─────────────────────────────────────────────────────────┐
│                    监控系统                              │
│                                                         │
│  ┌─────────────┐                                        │
│  │ jz-wxbot    │                                        │
│  │ Application │                                        │
│  └──────┬──────┘                                        │
│         │                                               │
│         │ HTTP /metrics                                 │
│         ▼                                               │
│  ┌─────────────┐     ┌─────────────┐                   │
│  │ Prometheus  │────▶│   Grafana   │                   │
│  │  (收集)     │     │  (展示)     │                   │
│  └──────┬──────┘     └─────────────┘                   │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐                                        │
│  │AlertManager │                                        │
│  │  (告警)     │                                        │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 监控指标

| 类别 | 指标 | 说明 |
|------|------|------|
| **应用指标** | 消息发送量、成功率、响应时间 | 业务监控 |
| **系统指标** | CPU、内存、磁盘、网络 | 资源监控 |
| **微信指标** | 客户端状态、窗口状态 | 组件监控 |
| **MCP指标** | 连接数、请求量、错误率 | 服务监控 |

---

## 健康检查端点

### MCP 健康检查

```python
# mcp_server.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0"
    }

@app.get("/health/ready")
async def readiness_check():
    """就绪检查"""
    checks = {
        "wechat": check_wechat_running(),
        "wxwork": check_wxwork_running(),
        "config": check_config_loaded()
    }
    
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks
    }

@app.get("/health/live")
async def liveness_check():
    """存活检查"""
    return {"alive": True}
```

### 健康检查脚本

```python
# scripts/health_check.py
import requests
import sys

def check_health():
    """检查服务健康状态"""
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务健康")
            return True
        else:
            print(f"❌ 服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接服务: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
```

---

## 日志监控

### 日志配置

```yaml
# config/logging.yaml
logging:
  version: 1
  formatters:
    json:
      class: pythonjsonlogger.jsonlogger.JsonFormatter
      format: "%(asctime)s %(name)s %(levelname)s %(message)s"
      
  handlers:
    file:
      class: logging.handlers.RotatingFileHandler
      formatter: json
      filename: logs/wxbot.log
      maxBytes: 10485760
      backupCount: 5
      
    # Elasticsearch 输出（可选）
    elasticsearch:
      class: logstash_logforwarder.LogstashHandler
      host: localhost
      port: 5000
      
  loggers:
    jz_wxbot:
      level: INFO
      handlers: [file]
```

### 日志分析脚本

```python
# scripts/log_analyzer.py
import re
from collections import Counter
from datetime import datetime, timedelta

def analyze_errors(log_file: str, hours: int = 24):
    """分析最近N小时的错误日志"""
    cutoff = datetime.now() - timedelta(hours=hours)
    errors = []
    
    with open(log_file) as f:
        for line in f:
            # 解析时间戳
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if match:
                log_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                if log_time > cutoff and 'ERROR' in line:
                    errors.append(line.strip())
    
    # 统计错误类型
    error_types = Counter()
    for error in errors:
        match = re.search(r'ERROR.*?(\w+Error)', error)
        if match:
            error_types[match.group(1)] += 1
    
    print(f"最近 {hours} 小时错误统计:")
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count} 次")
    
    return errors

if __name__ == "__main__":
    analyze_errors("logs/wxbot.log")
```

---

## 性能监控

### Prometheus 指标

```python
# jz_wxbot/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 消息指标
MESSAGES_SENT = Counter(
    'wxbot_messages_sent_total',
    'Total messages sent',
    ['sender_type', 'status']
)

MESSAGE_DURATION = Histogram(
    'wxbot_message_duration_seconds',
    'Time to send a message',
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

# 客户端状态
WECHAT_STATUS = Gauge(
    'wxbot_wechat_running',
    'WeChat client running status'
)

WXWORK_STATUS = Gauge(
    'wxbot_wxwork_running',
    'WXWork client running status'
)

# MCP 指标
MCP_REQUESTS = Counter(
    'wxbot_mcp_requests_total',
    'Total MCP requests',
    ['method', 'status']
)

# 启动指标服务器
def start_metrics_server(port=9090):
    start_http_server(port)
```

### 指标收集

```python
# 在发送器中收集指标
from jz_wxbot.metrics import MESSAGES_SENT, MESSAGE_DURATION

class WeChatSenderV3:
    def send_message(self, contact: str, message: str):
        start_time = time.time()
        try:
            # 发送消息
            self._do_send(contact, message)
            MESSAGES_SENT.labels(sender_type='wechat', status='success').inc()
        except Exception as e:
            MESSAGES_SENT.labels(sender_type='wechat', status='error').inc()
            raise
        finally:
            duration = time.time() - start_time
            MESSAGE_DURATION.observe(duration)
```

---

## 告警配置

### Prometheus 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: wxbot-alerts
    rules:
      - alert: WeChatNotRunning
        expr: wxbot_wechat_running == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "微信客户端未运行"
          description: "个人微信客户端已停止运行超过5分钟"

      - alert: HighErrorRate
        expr: rate(wxbot_messages_sent_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "消息发送错误率高"
          description: "消息发送错误率超过10%"

      - alert: SlowMessages
        expr: histogram_quantile(0.95, rate(wxbot_message_duration_seconds_bucket[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "消息发送延迟高"
          description: "95%分位消息发送时间超过5秒"

      - alert: ServiceDown
        expr: up{job="wxbot"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "wxbot服务不可用"
          description: "MCP服务已停止"
```

### AlertManager 配置

```yaml
# alertmanager/config.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@wxbot.local'

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@example.com'
        
  - name: 'critical'
    email_configs:
      - to: 'oncall@example.com'
    webhook_configs:
      - url: 'http://localhost:5001/webhook'
```

---

## 监控仪表板

### Grafana 仪表板配置

```json
{
  "dashboard": {
    "title": "jz-wxbot 监控",
    "panels": [
      {
        "title": "消息发送量",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(wxbot_messages_sent_total[5m])",
            "legendFormat": "{{sender_type}} - {{status}}"
          }
        ]
      },
      {
        "title": "消息发送延迟",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(wxbot_message_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(wxbot_message_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ]
      },
      {
        "title": "客户端状态",
        "type": "stat",
        "targets": [
          {
            "expr": "wxbot_wechat_running",
            "legendFormat": "微信"
          },
          {
            "expr": "wxbot_wxwork_running",
            "legendFormat": "企业微信"
          }
        ]
      },
      {
        "title": "错误率",
        "type": "gauge",
        "targets": [
          {
            "expr": "rate(wxbot_messages_sent_total{status=\"error\"}[5m]) / rate(wxbot_messages_sent_total[5m]) * 100",
            "legendFormat": "错误率%"
          }
        ],
        "thresholds": [
          {"value": 5, "color": "yellow"},
          {"value": 10, "color": "red"}
        ]
      }
    ]
  }
}
```

### Prometheus 配置

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'wxbot'
    static_configs:
      - targets: ['localhost:9090']
```

---

## 监控检查清单

| 配置项 | 状态 |
|--------|------|
| 健康检查端点 | □ |
| Prometheus 指标 | □ |
| 日志收集 | □ |
| 告警规则 | □ |
| Grafana 仪表板 | □ |
| 通知渠道 | □ |

---

**维护者**: jz-wxbot 开发团队  
**最后更新**: 2026-03-23