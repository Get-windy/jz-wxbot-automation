# jz-wxbot-automation 环境配置说明

**版本**: v1.0  
**创建时间**: 2026-03-23  
**适用对象**: 开发者、运维人员

---

## 📖 目录

1. [环境变量概览](#环境变量概览)
2. [应用配置](#应用配置)
3. [微信客户端配置](#微信客户端配置)
4. [MCP服务配置](#mcp服务配置)
5. [日志配置](#日志配置)
6. [安全配置](#安全配置)

---

## 环境变量概览

### 配置文件结构

```
jz-wxbot-automation/
├── config/
│   ├── default.yaml         # 默认配置
│   ├── development.yaml     # 开发环境
│   ├── production.yaml      # 生产环境
│   └── .env                 # 环境变量（敏感信息）
├── .env.example             # 环境变量模板
└── requirements.txt         # Python 依赖
```

### 环境变量列表

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `WXBOT_ENV` | development | 运行环境 |
| `WXBOT_LOG_LEVEL` | INFO | 日志级别 |
| `WXBOT_CONFIG_PATH` | config/default.yaml | 配置文件路径 |
| `WECHAT_PATH` | 自动检测 | 微信安装路径 |
| `WXWORK_PATH` | 自动检测 | 企业微信安装路径 |
| `MCP_PORT` | 8080 | MCP 服务端口 |
| `MCP_HOST` | localhost | MCP 服务地址 |

---

## 应用配置

### 主配置文件 (config/default.yaml)

```yaml
# 应用配置
app:
  name: jz-wxbot-automation
  version: 2.1.0
  environment: ${WXBOT_ENV:development}
  
# 微信客户端配置
wechat:
  enabled: true
  auto_start: true
  window_title: "微信"
  exe_name: "WeChat.exe"
  
wxwork:
  enabled: true
  auto_start: true
  window_title: "企业微信"
  exe_name: "WXWork.exe"

# 发送器配置
sender:
  priority: ["wechat", "wxwork"]
  fallback_enabled: true
  human_like_enabled: true
  
  # 人格化操作参数
  human_like:
    min_delay_ms: 500
    max_delay_ms: 2000
    typing_speed_range: [50, 150]
    mistake_probability: 0.02

# 消息处理配置
message:
  max_length: 5000
  chunk_size: 2000
  retry_count: 3
  retry_delay_ms: 1000

# 日志配置
logging:
  level: ${WXBOT_LOG_LEVEL:INFO}
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file:
    path: logs/wxbot.log
    max_size: 10MB
    backup_count: 5
```

### 环境变量文件 (.env)

```bash
# .env
# 环境
WXBOT_ENV=production

# 日志
WXBOT_LOG_LEVEL=INFO

# 微信路径（可选，自动检测）
# WECHAT_PATH=C:\Program Files\Tencent\WeChat\WeChat.exe
# WXWORK_PATH=C:\Program Files (x86)\WXWork\WXWork.exe

# MCP 服务
MCP_HOST=0.0.0.0
MCP_PORT=8080

# 安全
API_KEY=your-api-key-here
```

---

## 微信客户端配置

### 个人微信配置

```yaml
# config/wechat.yaml
wechat:
  # 窗口配置
  window:
    title_patterns:
      - "微信"
      - "WeChat"
    class_name: "WeChatMainWndForPC"
    
  # 进程配置
  process:
    exe_name: "WeChat.exe"
    check_interval_ms: 5000
    restart_on_crash: true
    
  # 搜索配置
  search:
    shortcut: "^f"  # Ctrl+F
    clear_on_open: true
    wait_timeout_ms: 5000
    
  # 消息输入配置
  input:
    edit_class: "Edit"
    send_button_text: "发送"
    send_shortcut: "{ENTER}"
```

### 企业微信配置

```yaml
# config/wxwork.yaml
wxwork:
  # 窗口配置
  window:
    title_patterns:
      - "企业微信"
      - "WXWork"
    class_name: "WXWorkWindow"
    
  # 进程配置
  process:
    exe_name: "WXWork.exe"
    check_interval_ms: 5000
    restart_on_crash: true
    
  # 搜索配置
  search:
    shortcut: "^f"
    clear_on_open: true
    wait_timeout_ms: 5000
```

---

## MCP服务配置

### MCP服务器配置

```yaml
# config/mcp.yaml
mcp:
  # 服务器配置
  server:
    host: ${MCP_HOST:localhost}
    port: ${MCP_PORT:8080}
    workers: 4
    
  # 认证配置
  auth:
    enabled: true
    api_key: ${API_KEY}
    rate_limit: 100/min
    
  # 超时配置
  timeout:
    connect_ms: 5000
    read_ms: 30000
    write_ms: 30000
    
  # 工具注册
  tools:
    - name: send_message
      enabled: true
      description: "发送消息到微信联系人"
      
    - name: send_group_message
      enabled: true
      description: "发送消息到微信群聊"
      
    - name: get_contacts
      enabled: true
      description: "获取微信联系人列表"
      
    - name: get_chat_history
      enabled: true
      description: "获取聊天记录"
```

### OpenClaw 集成配置

```yaml
# config/openclaw.yaml
openclaw:
  # MCP 客户端配置
  mcp_client:
    server_url: "http://localhost:8080"
    reconnect_interval_ms: 5000
    max_retries: 3
    
  # 任务调度配置
  scheduler:
    enabled: true
    check_interval_ms: 60000
    
  # 任务队列
  queue:
    max_size: 100
    priority_levels: 3
```

---

## 日志配置

### Python logging 配置

```python
# config/logging_config.py
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": "logs/wxbot.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "jz_wxbot": {
            "level": "DEBUG",
            "handlers": ["console", "file"]
        }
    }
}
```

### 日志级别说明

| 级别 | 说明 | 使用场景 |
|------|------|---------|
| DEBUG | 调试信息 | 开发调试 |
| INFO | 运行信息 | 正常运行 |
| WARNING | 警告信息 | 潜在问题 |
| ERROR | 错误信息 | 需要处理的问题 |
| CRITICAL | 严重错误 | 系统崩溃 |

---

## 安全配置

### API 密钥管理

```yaml
# config/security.yaml
security:
  # API 密钥
  api_key: ${API_KEY}
  
  # 访问控制
  access_control:
    enabled: true
    allowed_ips:
      - "127.0.0.1"
      - "::1"
    # 允许所有本地访问
    allow_localhost: true
    
  # 敏感词过滤
  sensitive_words:
    enabled: true
    filter_char: "*"
    
  # 消息加密
  encryption:
    enabled: false
    algorithm: "AES-256-GCM"
```

### 权限配置

```yaml
# config/permissions.yaml
permissions:
  # 默认权限
  default:
    - send_message
    - get_contacts
    
  # 管理员权限
  admin:
    - send_message
    - get_contacts
    - get_chat_history
    - manage_contacts
    - system_control
```

---

## 配置验证

### 验证脚本

```python
# scripts/validate_config.py
import os
import yaml
from pathlib import Path

def validate_config():
    """验证配置文件"""
    config_dir = Path("config")
    
    # 检查必要文件
    required_files = ["default.yaml", "mcp.yaml"]
    for f in required_files:
        if not (config_dir / f).exists():
            print(f"❌ 缺少配置文件: {f}")
            return False
            
    # 检查环境变量
    required_env = ["WXBOT_ENV"]
    for env in required_env:
        if not os.getenv(env):
            print(f"⚠️ 未设置环境变量: {env}")
            
    # 加载配置验证格式
    try:
        with open(config_dir / "default.yaml") as f:
            config = yaml.safe_load(f)
        print("✅ 配置文件格式正确")
    except Exception as e:
        print(f"❌ 配置文件格式错误: {e}")
        return False
        
    print("✅ 配置验证通过")
    return True

if __name__ == "__main__":
    validate_config()
```

---

## 相关文档

- [快速启动指南](QUICKSTART.md)
- [部署指南](DEPLOYMENT_GUIDE.md)
- [故障排查指南](TROUBLESHOOTING.md)

---

**维护者**: jz-wxbot 开发团队  
**最后更新**: 2026-03-23