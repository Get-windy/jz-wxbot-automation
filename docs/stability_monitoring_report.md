# jz-wxbot 稳定性监控配置报告

**配置日期**: 2026-03-25
**版本**: v1.0.0
**项目**: jz-wxbot-automation

---

## 📊 监控概览

| 监控模块 | 状态 | 功能 |
|----------|------|------|
| 微信控制监控 | ✅ 已配置 | 进程/窗口/UI元素监控 |
| 消息收发监控 | ✅ 已配置 | 发送/接收/队列监控 |
| 错误日志收集 | ✅ 已配置 | 日志轮转/错误追踪 |
| 健康检查 | ✅ 已配置 | 多维度健康状态检查 |
| Prometheus监控 | ✅ 已配置 | 自定义指标导出 |
| 告警系统 | ✅ 已配置 | 多渠道告警通知 |

---

## 🔧 监控配置详情

### 1. 微信控制稳定性监控

**进程监控**:
| 进程名 | 类型 | 关键级别 | 检查间隔 |
|--------|------|----------|----------|
| WeChat.exe | 个人微信 | 高 | 30秒 |
| Weixin.exe | 个人微信 | 高 | 30秒 |
| WXWork.exe | 企业微信 | 高 | 30秒 |

**自动恢复策略**:
- 进程未找到 → 告警 + 自动重启
- 窗口无响应 → 告警
- UI元素不可达 → 告警 + 重试

### 2. 消息收发监控

**发送监控**:
| 指标 | 阈值 | 说明 |
|------|------|------|
| 成功率 | ≥ 95% | 低于阈值触发告警 |
| 最大延迟 | ≤ 5000ms | 超过阈值触发告警 |
| 最大错误数 | ≤ 10次/周期 | 超过阈值触发告警 |

**队列监控**:
| 配置项 | 值 |
|--------|------|
| 最大队列大小 | 1000 |
| 检查间隔 | 30秒 |
| 陈旧消息超时 | 5分钟 |
| 溢出策略 | 丢弃最旧 |

### 3. 错误日志收集

**日志配置**:
| 配置项 | 值 |
|--------|------|
| 日志目录 | logs/ |
| 单文件最大 | 10MB |
| 备份文件数 | 10 |
| 压缩 | 启用 |

**错误级别处理**:
| 级别 | 处理方式 |
|------|----------|
| Low | 记录日志 |
| Medium | 日志 + 告警 |
| High | 告警 + 重试 |
| Critical | 告警 + 关闭 |

### 4. 健康检查

**检查项配置**:
| 检查项 | 类型 | 关键级别 | 间隔 | 阈值 |
|--------|------|----------|------|------|
| 微信进程 | 进程 | 高 | 30秒 | - |
| 桥接服务 | 服务 | 高 | 60秒 | - |
| 消息队列 | 队列 | 中 | 30秒 | - |
| 内存使用 | 资源 | 中 | 60秒 | 500MB |
| CPU使用 | 资源 | 中 | 60秒 | 80% |

**健康状态级别**:
- `healthy` - 所有检查通过
- `degraded` - 部分非关键检查失败
- `unhealthy` - 关键检查失败

### 5. Prometheus监控

**自定义指标**:
| 指标名 | 类型 | 说明 |
|--------|------|------|
| wxbot_messages_sent_total | Counter | 发送消息总数 |
| wxbot_messages_received_total | Counter | 接收消息总数 |
| wxbot_send_latency_seconds | Histogram | 发送延迟分布 |
| wxbot_errors_total | Counter | 错误总数 |
| wxbot_process_status | Gauge | 进程状态(0/1) |
| wxbot_queue_size | Gauge | 队列大小 |
| wxbot_memory_bytes | Gauge | 内存使用 |
| wxbot_cpu_percent | Gauge | CPU使用率 |

**配置**:
- 端口: 9090
- 路径: /metrics

### 6. 告警规则

| 规则名 | 条件 | 严重级别 | 冷却时间 |
|--------|------|----------|----------|
| 微信未运行 | 进程状态=0 | Critical | 5分钟 |
| 高错误率 | 错误率>10% | High | 5分钟 |
| 队列满载 | 队列>800 | Medium | 2分钟 |
| 高内存 | 内存>400MB | Medium | 5分钟 |
| 高CPU | CPU>70% | Medium | 5分钟 |
| 高延迟 | 延迟>5秒 | Medium | 1分钟 |

---

## 📁 文件清单

### 新增文件

| 文件路径 | 说明 | 大小 |
|----------|------|------|
| `config/monitoring/stability_monitor.yaml` | 监控配置文件 | 7.4KB |
| `core/stability_monitor.py` | 稳定性监控服务 | 22KB |

### 已有相关文件

| 文件路径 | 说明 |
|----------|------|
| `stability_test_72h.py` | 72小时稳定性测试脚本 |
| `core/enhanced_logging.py` | 增强日志系统 |
| `core/enhanced_error_handling.py` | 增强错误处理 |
| `config/monitoring/prometheus.yml` | Prometheus配置 |

---

## 🚀 使用方法

### 启动监控服务

```python
from core.stability_monitor import get_stability_monitor

# 获取监控实例
monitor = get_stability_monitor()

# 启动监控
monitor.start()

# 执行检查
result = monitor.check()

# 获取报告
report = monitor.get_report()

# 保存报告
monitor.save_report()
```

### 集成到主程序

```python
# main.py 中添加
from core.stability_monitor import get_stability_monitor

# 启动后初始化监控
monitor = get_stability_monitor()
monitor.start()

# 定期执行检查
while running:
    result = monitor.check()
    await asyncio.sleep(60)
```

### 监控装饰器使用

```python
from core.stability_monitor import get_stability_monitor, monitor_send

monitor = get_stability_monitor()

@monitor_send(monitor.message_monitor)
def send_message(chat_name, message):
    # 发送消息逻辑
    pass
```

---

## 📈 监控指标示例

### 进程状态检查

```json
{
  "process_status": {
    "WeChat.exe": true,
    "Weixin.exe": false,
    "WXWork.exe": true
  }
}
```

### 资源指标

```json
{
  "resource": {
    "cpu_percent": 15.2,
    "memory_mb": 156.4,
    "thread_count": 12,
    "open_files": 45
  }
}
```

### 消息指标

```json
{
  "message": {
    "send": {
      "total": 1234,
      "success": 1220,
      "failed": 14,
      "success_rate": 0.989,
      "avg_latency_ms": 245.6
    },
    "receive": {
      "total": 5678,
      "avg_processing_ms": 12.3
    },
    "queue": {
      "size": 23,
      "max_size": 1000,
      "usage_percent": 2.3
    }
  }
}
```

### 健康报告

```json
{
  "health": {
    "status": "healthy",
    "checks": {
      "wechat_process": {"status": "healthy"},
      "message_queue": {"status": "healthy"},
      "memory": {"status": "healthy"},
      "cpu": {"status": "healthy"}
    }
  }
}
```

---

## ✅ 配置检查清单

- [x] 微信进程监控配置
- [x] 消息发送成功率阈值
- [x] 消息接收监控
- [x] 队列监控配置
- [x] 错误日志轮转
- [x] 错误追踪配置
- [x] 健康检查端点
- [x] Prometheus指标导出
- [x] 告警规则配置
- [x] 自动恢复策略
- [x] 报告生成配置

---

## 🔄 后续建议

### 短期改进
1. 添加Webhook告警通知
2. 集成OpenClaw消息通知
3. 添加监控Dashboard

### 中期改进
1. 历史数据持久化
2. 趋势分析和预测
3. 自动扩缩容支持

### 长期改进
1. 机器学习异常检测
2. 分布式监控支持
3. 自定义监控规则引擎

---

*配置人: team-member*
*配置时间: 2026-03-25 08:15*