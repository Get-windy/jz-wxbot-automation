# jz-wxbot-automation 部署指南

**版本**: v1.0  
**创建日期**: 2026-03-16  
**项目**: jz-wxbot-automation  
**适用对象**: 运维人员、系统管理员

---

## 📋 目录

1. [部署概述](#部署概述)
2. [环境准备](#环境准备)
3. [本地部署](#本地部署)
4. [服务器部署](#服务器部署)
5. [Docker 部署](#docker 部署)
6. [配置说明](#配置说明)
7. [运维管理](#运维管理)
8. [故障排除](#故障排除)

---

## 部署概述

### 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户/管理员                           │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                  OpenClaw 智能助手                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  Agent Core │  │   MCP       │  │   Task      │      │
│  │             │  │   Client    │  │   Scheduler │      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
└─────────┼────────────────┼────────────────┼─────────────┘
          │         MCP Protocol            │
          │                                 │
          ▼                                 ▼
┌─────────────────────────────────────────────────────────┐
│               jz-wxbot-automation                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              MCP Server                          │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐     │   │
│  │  │  微信消息 │ │  朋友圈   │ │  好友管理 │     │   │
│  │  │  工具     │ │  工具     │ │  工具     │     │   │
│  │  └───────────┘ └───────────┘ └───────────┘     │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│                          │ UI Automation                │
└──────────────────────────┼──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Windows 微信客户端                       │
│         WeChat.exe / WXWork.exe                         │
└─────────────────────────────────────────────────────────┘
```

### 部署模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **本地部署** | 单用户桌面环境 | 个人使用、开发测试 |
| **服务器部署** | 专用服务器，24 小时运行 | 企业应用、生产环境 |
| **Docker 部署** | 容器化部署（需 Windows 容器） | 隔离环境、多实例 |

---

## 环境准备

### 系统要求

| 要求 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **操作系统** | Windows 10 (64 位) | Windows 11 (64 位) |
| **CPU** | 4 核心 | 8 核心+ |
| **内存** | 8GB | 16GB+ |
| **磁盘** | 50GB 可用空间 | 100GB+ SSD |
| **网络** | 稳定互联网连接 | 专线/固定 IP |

### 软件要求

| 软件 | 版本 | 下载链接 |
|------|------|---------|
| **Python** | 3.9 - 3.12 | https://python.org |
| **个人微信** | 3.9+ | https://weixin.qq.com |
| **企业微信** | 4.1+ | https://work.weixin.qq.com |
| **Git** | 2.0+ | https://git-scm.com |

### 环境检查脚本

```powershell
# check_environment.ps1

Write-Host "=== jz-wxbot-automation 环境检查 ===" -ForegroundColor Cyan

# 检查操作系统
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "操作系统：$($os.Caption) $($os.OSArchitecture)"

# 检查 Python
try {
    $python = python --version 2>&1
    Write-Host "Python: $python" -ForegroundColor Green
} catch {
    Write-Host "Python: 未安装" -ForegroundColor Red
}

# 检查微信
$wechat = Get-Process WeChat, Weixin -ErrorAction SilentlyContinue
if ($wechat) {
    Write-Host "个人微信：已安装" -ForegroundColor Green
} else {
    Write-Host "个人微信：未运行" -ForegroundColor Yellow
}

# 检查企业微信
|wxwork = Get-Process WXWork -ErrorAction SilentlyContinue
if ($wxwork) {
    Write-Host "企业微信：已安装" -ForegroundColor Green
} else {
    Write-Host "企业微信：未运行" -ForegroundColor Yellow
}

# 检查内存
$mem = Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum
$memGB = [math]::Round($mem.Sum / 1GB, 2)
Write-Host "内存：${memGB}GB"

Write-Host "`n环境检查完成！" -ForegroundColor Cyan
```

---

## 本地部署

### 步骤 1: 下载项目

```bash
# 方式 1: Git 克隆
git clone https://github.com/jxyk2007/jz-wxbot-automation.git
cd jz-wxbot-automation

# 方式 2: 下载 ZIP
# 访问 https://github.com/jxyk2007/jz-wxbot-automation/archive/refs/heads/main.zip
# 解压到本地目录
```

### 步骤 2: 安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# PowerShell
.\venv\Scripts\Activate.ps1
# CMD
venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt
```

### 步骤 3: 配置项目

```bash
# 复制配置文件模板
cp config/config.yaml.example config/config.yaml
cp config/mcp_config.json.example config/mcp_config.json

# 编辑配置文件
# config/config.yaml
```

**config.yaml 示例**：
```yaml
# 基本配置
app:
  name: jz-wxbot-automation
  version: 2.0.0
  debug: false

# 微信配置
wechat:
  enabled: true
  process_names:
    - WeChat.exe
    - Weixin.exe
  default_group: "技术交流群"

# 企业微信配置
wxwork:
  enabled: true
  process_names:
    - WXWork.exe
  default_group: "项目组"

# 发送器配置
sender:
  priority: ["wechat", "wxwork"]  # 优先级顺序
  fallback_enabled: true          # 启用回退
  human_like_enabled: true        # 启用人性格操作

# 日志配置
logging:
  level: INFO
  file: logs/wxbot.log
  max_size: 10MB
  backup_count: 5
```

### 步骤 4: 测试运行

```bash
# 测试窗口检测
python window_inspector.py findwechat

# 测试 MCP 服务器
python mcp_server.py --help

# 测试发送器
python auto_daily_report_v2.py test

# 查看状态
python auto_daily_report_v2.py status
```

### 步骤 5: 运行应用

```bash
# 方式 1: 直接运行主程序
python main.py

# 方式 2: 运行 MCP 服务器
python mcp_server.py

# 方式 3: 运行自动化系统
python auto_daily_report_v2.py run

# 方式 4: 使用批处理脚本（Windows）
run_daily_auto.bat
```

---

## 服务器部署

### 步骤 1: 准备服务器

**推荐配置**：
- CPU: 8 核心+
- 内存：16GB+
- 磁盘：100GB SSD
- 网络：固定 IP，带宽≥10Mbps

**系统优化**：
```powershell
# 禁用睡眠
powercfg -change -standby-timeout-ac 0

# 禁用屏幕保护
reg add "HKCU\Control Panel\Desktop" /v SCRNSAVE.EXE /t REG_SZ /d "" /f

# 设置高性能模式
powercfg -setactive SCHEME_MIN
```

### 步骤 2: 安装依赖

```bash
# 安装 Python
# 下载 https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
# 静默安装
python-3.11.0-amd64.exe /quiet InstallAllUsers=1 PrependPath=1

# 安装微信
# 下载 https://dldir1.qq.com/weixin/Windows/WeChatSetup.exe
# 手动安装

# 安装企业微信
# 下载 https://work.weixin.qq.com/wework_wx/wework-wx64.exe
# 手动安装
```

### 步骤 3: 配置服务

**创建 Windows 服务**：

```powershell
# 安装 NSSM (Non-Sucking Service Manager)
# 下载 https://nssm.cc/release/nssm-2.24.zip

# 创建服务
nssm install jz-wxbot-mcp "C:\Python311\python.exe" "-m jz_wxbot.mcp_server"

# 配置服务
nssm set jz-wxbot-mcp DisplayName "jz-wxbot MCP Server"
nssm set jz-wxbot-mcp Description "微信自动化 MCP 服务"
nssm set jz-wxbot-mcp Start SERVICE_AUTO_START
nssm set jz-wxbot-mcp AppDirectory "C:\jz-wxbot-automation"
nssm set jz-wxbot-mcp AppStdout "C:\jz-wxbot-automation\logs\service.log"
nssm set jz-wxbot-mcp AppStderr "C:\jz-wxbot-automation\logs\service-error.log"

# 启动服务
nssm start jz-wxbot-mcp
```

### 步骤 4: 配置开机启动

**方式 1: 任务计划程序**

```xml
<!-- wxbot_startup.xml -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </LogonTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\jz-wxbot-automation\run_daily_auto.bat</Command>
      <WorkingDirectory>C:\jz-wxbot-automation</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

```bash
# 导入任务
schtasks /Create /TN "jz-wxbot-Startup" /XML wxbot_startup.xml
```

**方式 2: 启动文件夹**

```bash
# 创建快捷方式
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\jz-wxbot.lnk")
$Shortcut.TargetPath = "C:\jz-wxbot-automation\run_daily_auto.bat"
$Shortcut.WorkingDirectory = "C:\jz-wxbot-automation"
$Shortcut.Save()
```

### 步骤 5: 监控和日志

**配置日志轮转**：

```yaml
# config.yaml
logging:
  level: INFO
  file: logs/wxbot.log
  rotation:
    max_size: 10MB
    backup_count: 10
    compression: true
```

**日志查看**：
```bash
# 实时查看日志
Get-Content logs\wxbot.log -Wait -Tail 50

# 查看错误日志
Get-Content logs\wxbot-error.log -Tail 100

# 搜索特定日志
Select-String -Path logs\*.log -Pattern "ERROR" -Context 2
```

---

## Docker 部署

> ⚠️ 注意：由于需要 GUI 自动化，Docker 部署需要 Windows 容器和桌面体验支持

### Dockerfile 示例

```dockerfile
# Dockerfile
FROM mcr.microsoft.com/windows:ltsc2022

# 安装 Python
RUN powershell -Command \
    $ProgressPreference = 'SilentlyContinue'; \
    Invoke-WebRequest https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe -OutFile python.exe; \
    .\python.exe /quiet InstallAllUsers=1 PrependPath=1; \
    Remove-Item python.exe

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install -r requirements.txt

# 暴露端口（如果需要）
EXPOSE 8765

# 启动命令
CMD ["python", "mcp_server.py", "--transport", "sse", "--port", "8765"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  wxbot-mcp:
    build: .
    container_name: jz-wxbot-mcp
    ports:
      - "8765:8765"
    volumes:
      - ./config:C:/app/config
      - ./logs:C:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
      - MCP_TRANSPORT=sse
      - MCP_PORT=8765
    restart: unless-stopped
```

### 构建和运行

```bash
# 构建镜像
docker build -t jz-wxbot-automation .

# 运行容器
docker run -d \
  --name wxbot-mcp \
  -p 8765:8765 \
  -v ${PWD}/config:C:/app/config \
  -v ${PWD}/logs:C:/app/logs \
  jz-wxbot-automation

# 查看日志
docker logs -f wxbot-mcp

# 停止容器
docker stop wxbot-mcp
```

---

## 配置说明

### 完整配置示例

```yaml
# config/config.yaml

# 应用配置
app:
  name: jz-wxbot-automation
  version: 2.0.0
  debug: false
  environment: production  # development, staging, production

# OpenClaw 配置
openclaw:
  enabled: true
  api_key: "your-api-key"
  workspace: "your-workspace"
  model: "qwen-portal/coder-model"

# MCP 服务器配置
mcp:
  enabled: true
  transport: stdio  # stdio, sse, websocket
  port: 8765
  host: "localhost"
  timeout: 30

# 微信配置
wechat:
  enabled: true
  process_names:
    - WeChat.exe
    - Weixin.exe
    - wechat.exe
  window_class: "WeChatChatWnd"
  default_group: "技术交流群"
  auto_login: false

# 企业微信配置
wxwork:
  enabled: true
  process_names:
    - WXWork.exe
    - wxwork.exe
  window_class: "WeWorkWindow"
  default_group: "项目组"
  auto_login: false

# 发送器配置
sender:
  priority: ["wechat", "wxwork"]  # 优先级顺序
  fallback_enabled: true          # 启用回退机制
  human_like_enabled: true        # 启用人性格操作
  
  # 反风控配置
  anti_detection:
    random_delay: true
    curve_movement: true
    reading_pause: true
    random_move_probability: 0.3
  
  # 频率限制
  rate_limits:
    message_interval_min: 2
    message_interval_max: 5
    mass_send_daily_limit: 200
    add_friend_daily_limit: 20

# 消息配置
message:
  add_timestamp: true
  add_sender_info: false
  format_style: "emoji"  # emoji, plain, markdown
  max_length: 2000

# 自动化配置
automation:
  enabled: true
  schedule:
    - time: "09:00"
      task: "morning_report"
      groups: ["公司群"]
    - time: "18:00"
      task: "evening_report"
      groups: ["公司群"]
    - time: "17:00"
      day: "friday"
      task: "weekly_report"
      groups: ["公司群"]

# 日志配置
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: logs/wxbot.log
  max_size: 10MB
  backup_count: 10
  compression: true
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 监控配置
monitoring:
  enabled: true
  health_check_interval: 60  # 秒
  alert:
    enabled: true
    channels: ["email", "webhook"]
    email:
      recipients: ["admin@example.com"]
      smtp_server: "smtp.example.com"
      smtp_port: 587
    webhook:
      url: "https://hooks.example.com/wxbot"
      method: "POST"

# 安全配置
security:
  api_key_required: false
  allowed_ips: ["127.0.0.1", "192.168.1.0/24"]
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

### 环境变量

```bash
# .env 文件示例

# OpenClaw 配置
OPENCLAW_API_KEY=your-api-key
OPENCLAW_WORKSPACE=your-workspace

# MCP 配置
MCP_TRANSPORT=stdio
MCP_PORT=8765

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/wxbot.log

# 微信配置
WECHAT_ENABLED=true
WXWORK_ENABLED=true

# 安全配置
API_KEY=your-secret-key
ALLOWED_IPS=127.0.0.1,192.168.1.0/24
```

---

## 运维管理

### 服务管理命令

```powershell
# 启动服务
nssm start jz-wxbot-mcp

# 停止服务
nssm stop jz-wxbot-mcp

# 重启服务
nssm restart jz-wxbot-mcp

# 查看状态
nssm status jz-wxbot-mcp

# 查看日志
Get-Content logs\service.log -Wait -Tail 100
```

### 健康检查

```bash
# 检查 MCP 服务器
python -c "
from mcp.client import Client
client = Client()
client.connect('stdio', 'python mcp_server.py')
tools = client.list_tools()
print(f'工具数量：{len(tools)}')
"

# 检查微信进程
tasklist | findstr "WeChat WXWork"

# 检查窗口
python window_inspector.py findwechat
```

### 性能监控

```python
# monitor.py
import psutil
import time

def monitor_system():
    """监控系统资源"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('C:')
    
    print(f"CPU: {cpu_percent}%")
    print(f"内存：{memory.percent}%")
    print(f"磁盘：{disk.percent}%")
    
    # 检查微信进程
    wechat_procs = [p for p in psutil.process_iter(['name']) 
                    if p.info['name'] in ['WeChat.exe', 'WXWork.exe']]
    print(f"微信进程数：{len(wechat_procs)}")

# 每 5 分钟检查一次
while True:
    monitor_system()
    time.sleep(300)
```

### 备份策略

```powershell
# backup.ps1

$backupDir = "D:\backups\wxbot"
$sourceDir = "C:\jz-wxbot-automation"
$date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupPath = "$backupDir\wxbot_$date"

# 创建备份目录
New-Item -ItemType Directory -Force -Path $backupPath

# 备份配置文件
Copy-Item "$sourceDir\config\*" "$backupPath\config\" -Recurse

# 备份日志（最近 7 天）
Get-ChildItem "$sourceDir\logs" | 
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) } |
    Copy-Item -Destination "$backupPath\logs\" -Recurse

# 压缩备份
Compress-Archive -Path $backupPath -DestinationPath "$backupPath.zip"

# 删除旧备份（保留 30 天）
Get-ChildItem $backupDir | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Recurse -Force

Write-Host "备份完成：$backupPath.zip"
```

**配置定时备份**：
```bash
# 每天凌晨 2 点备份
schtasks /Create /TN "jz-wxbot-Backup" /TR "powershell.exe -File C:\jz-wxbot-automation\backup.ps1" /SC DAILY /ST 02:00
```

---

## 故障排除

### 常见问题

#### 1. MCP 服务器无法启动

**症状**：
```
Error: Address already in use
```

**解决方案**：
```bash
# 检查端口占用
netstat -ano | findstr :8765

# 杀死占用端口的进程
taskkill /F /PID <PID>

# 或修改配置使用其他端口
# config.yaml
mcp:
  port: 8766
```

#### 2. 微信窗口找不到

**症状**：
```
Error: WeChat window not found
```

**解决方案**：
```bash
# 1. 确保微信已启动
# 2. 打开一个聊天窗口
# 3. 使用窗口检查器
python window_inspector.py click

# 4. 如果仍然找不到，更新窗口类名
# config.yaml
wechat:
  window_class: "WeChatWnd"  # 尝试不同的类名
```

#### 3. 消息发送失败

**症状**：
```
Error: Failed to send message
```

**解决方案**：
```bash
# 1. 检查窗口是否激活
# 2. 检查输入框是否可访问
# 3. 尝试手动发送测试
python wechat_sender_v3.py test

# 4. 查看详细日志
Get-Content logs\wxbot-error.log -Tail 50
```

#### 4. 内存占用过高

**症状**：
```
Memory usage > 1GB
```

**解决方案**：
```bash
# 1. 检查日志文件大小
# 2. 清理旧日志
Remove-Item logs\*.log.* -Force

# 3. 调整日志配置
# config.yaml
logging:
  max_size: 5MB
  backup_count: 3

# 4. 重启服务
nssm restart jz-wxbot-mcp
```

#### 5. 频繁触发风控

**症状**：
- 发送失败率突然上升
- 账号被限制功能

**解决方案**：
```yaml
# config.yaml
sender:
  anti_detection:
    random_delay: true
    curve_movement: true
    reading_pause: true
    random_move_probability: 0.5  # 提高概率
  
  rate_limits:
    message_interval_min: 5  # 增加间隔
    message_interval_max: 15
    mass_send_daily_limit: 100  # 降低限额
    add_friend_daily_limit: 10
```

### 日志分析

```powershell
# 统计错误数量
Select-String -Path logs\*.log -Pattern "ERROR" | Measure-Object | Select-Object Count

# 查看最常见的错误
Select-String -Path logs\*.log -Pattern "ERROR" | 
    ForEach-Object { $_.Line } | 
    Sort-Object | Get-Unique | 
    Select-Object -First 10

# 查看特定时间的日志
Get-Content logs\wxbot.log | 
    Where-Object { $_ -match "2026-03-16 09:" }
```

### 获取帮助

- **文档**: `I:\jz-wxbot-automation\docs\`
- **GitHub Issues**: https://github.com/jxyk2007/jz-wxbot-automation/issues
- **邮箱**: dev@jz-wxbot.local

---

## 相关文档

- [README](../README.md)
- [开发指南](./DEVELOPMENT_GUIDE.md)
- [API 使用指南](./API_USAGE_GUIDE.md)
- [MCP 集成指南](./MCP_INTEGRATION_GUIDE.md)

---

**文档维护**: jz-wxbot-automation 运维团队  
**反馈邮箱**: ops@jz-wxbot.local  
**最后更新**: 2026-03-16
