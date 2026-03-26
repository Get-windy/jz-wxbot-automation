# jz-wxbot-automation 故障排查指南

**版本**: v1.0  
**创建时间**: 2026-03-23  
**适用对象**: 运维人员、开发人员

---

## 📖 目录

1. [快速诊断](#快速诊断)
2. [微信客户端问题](#微信客户端问题)
3. [消息发送问题](#消息发送问题)
4. [MCP服务问题](#mcp服务问题)
5. [自动化问题](#自动化问题)
6. [性能问题](#性能问题)
7. [日志分析](#日志分析)

---

## 快速诊断

### 诊断脚本

```python
# scripts/diagnose.py
"""一键诊断脚本"""
import subprocess
import sys

def diagnose():
    print("=" * 50)
    print("jz-wxbot-automation 诊断报告")
    print("=" * 50)
    
    # 检查 Python 版本
    print(f"\nPython 版本: {sys.version}")
    
    # 检查依赖
    print("\n依赖检查:")
    required = ["pyautogui", "pywin32", "psutil", "pyperclip"]
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} - 未安装")
    
    # 检查微信客户端
    print("\n微信客户端检查:")
    import psutil
    processes = [p.info['name'] for p in psutil.process_iter(['name'])]
    if "WeChat.exe" in processes:
        print("  ✅ 个人微信已运行")
    else:
        print("  ⚠️ 个人微信未运行")
    if "WXWork.exe" in processes:
        print("  ✅ 企业微信已运行")
    else:
        print("  ⚠️ 企业微信未运行")
    
    # 检查配置
    print("\n配置检查:")
    from pathlib import Path
    config_files = ["config/default.yaml", "config/mcp.yaml"]
    for f in config_files:
        if Path(f).exists():
            print(f"  ✅ {f}")
        else:
            print(f"  ❌ {f} - 不存在")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    diagnose()
```

### 诊断检查清单

| 检查项 | 命令 | 期望结果 |
|--------|------|---------|
| Python版本 | `python --version` | >= 3.7 |
| 微信运行 | 任务管理器 | WeChat.exe/WXWork.exe |
| 窗口检测 | `python window_inspector.py findwechat` | 找到窗口 |
| 依赖完整 | `pip list` | 所有依赖已安装 |
| 配置正确 | `python -c "import yaml; yaml.safe_load(open('config/default.yaml'))"` | 无错误 |

---

## 微信客户端问题

### 问题：微信窗口无法检测

**症状**: 报错"未找到微信窗口"

**排查步骤**:

```python
# 检查窗口
python window_inspector.py findwechat

# 查看所有窗口
python window_inspector.py listall
```

**常见原因**:

| 原因 | 解决方法 |
|------|---------|
| 微信未启动 | 启动微信客户端 |
| 窗口标题不匹配 | 检查窗口标题配置 |
| 微信最小化到托盘 | 恢复微信窗口 |
| 多开微信 | 关闭多余实例 |

**解决方案**:

```python
# 手动指定窗口标题
from jz_wxbot.wechat_sender import WeChatSenderV3

sender = WeChatSenderV3(window_title="你的微信窗口标题")
```

---

### 问题：微信客户端闪退

**症状**: 微信自动关闭

**排查步骤**:

```powershell
# 查看事件日志
Get-EventLog -LogName Application -Source "Application Error" -Newest 10

# 检查内存使用
Get-Process WeChat | Select-Object Name, WorkingSet, VirtualMemorySize
```

**常见原因**:

| 原因 | 解决方法 |
|------|---------|
| 内存不足 | 关闭其他程序 |
| 版本不兼容 | 更新微信版本 |
| 配置损坏 | 重装微信 |

---

## 消息发送问题

### 问题：消息发送失败

**症状**: 消息未成功发送

**排查步骤**:

```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# 测试发送
from jz_wxbot.wechat_sender import WeChatSenderV3
sender = WeChatSenderV3()
sender.send_message("文件传输助手", "测试消息")
```

**常见原因**:

| 原因 | 解决方法 |
|------|---------|
| 联系人不存在 | 检查联系人名称 |
| 输入框未获取焦点 | 增加等待时间 |
| 发送键快捷键错误 | 检查 send_shortcut 配置 |
| 剪贴板被占用 | 重试或清除剪贴板 |

**解决方案**:

```yaml
# 调整配置
sender:
  human_like:
    min_delay_ms: 1000   # 增加延迟
    max_delay_ms: 3000
  retry_count: 5         # 增加重试次数
```

---

### 问题：消息发送乱码

**症状**: 发送的消息显示乱码

**排查步骤**:

```python
# 检查编码
import sys
print(f"系统编码: {sys.getdefaultencoding()}")

# 测试剪贴板
import pyperclip
pyperclip.copy("测试中文")
print(pyperclip.paste())
```

**解决方案**:

```python
# 确保使用 UTF-8 编码
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

### 问题：群消息发送失败

**症状**: 群聊消息无法发送

**排查步骤**:

```python
# 列出所有群聊
sender = WeChatSenderV3()
groups = sender.get_groups()
for g in groups:
    print(g)
```

**常见原因**:

| 原因 | 解决方法 |
|------|---------|
| 群名称错误 | 使用完整群名称 |
| 未加入该群 | 先加入群聊 |
| 群已解散 | 确认群状态 |

---

## MCP服务问题

### 问题：MCP服务无法启动

**症状**: 服务启动失败

**排查步骤**:

```bash
# 检查端口占用
netstat -ano | findstr :8080

# 检查配置
python -c "import yaml; print(yaml.safe_load(open('config/mcp.yaml')))"

# 直接启动测试
python mcp_server.py --debug
```

**常见原因**:

| 原因 | 解决方法 |
|------|---------|
| 端口被占用 | 更换端口或停止占用进程 |
| 配置错误 | 检查 YAML 语法 |
| 依赖缺失 | pip install -r requirements.txt |

---

### 问题：MCP连接超时

**症状**: 客户端连接超时

**排查步骤**:

```bash
# 测试连接
curl http://localhost:8080/health

# 检查防火墙
netsh advfirewall firewall show rule name=all | findstr 8080
```

**解决方案**:

```yaml
# 增加超时时间
mcp:
  timeout:
    connect_ms: 10000
    read_ms: 60000
```

---

## 自动化问题

### 问题：定时任务不执行

**症状**: 计划任务未触发

**排查步骤**:

```python
# 检查任务调度器
from jz_wxbot.scheduler import TaskScheduler
scheduler = TaskScheduler()
print(scheduler.list_tasks())
```

**常见原因**:

| 原因 | 解决方法 |
|------|---------|
| 系统时间错误 | 检查系统时间 |
| 任务被禁用 | 启用任务 |
| cron 表达式错误 | 验证表达式 |

---

### 问题：自动化操作卡住

**症状**: 操作无响应

**排查步骤**:

```python
# 检查当前操作
import pyautogui
pyautogui.position()  # 获取鼠标位置

# 截图当前状态
pyautogui.screenshot("debug.png")
```

**解决方案**:

```python
# 设置超时
import pyautogui
pyautogui.TIMEOUT = 10  # 10秒超时

# 添加异常处理
try:
    sender.send_message("联系人", "消息")
except pyautogui.FailSafeException:
    print("操作被中断")
```

---

## 性能问题

### 问题：CPU占用过高

**症状**: 系统变慢

**排查步骤**:

```powershell
# 查看进程CPU
Get-Process python | Sort-Object CPU -Descending | Select-Object -First 5

# 查看线程
Get-Process python | Select-Object -ExpandProperty Threads
```

**解决方案**:

```python
# 降低轮询频率
import time
while True:
    check_messages()
    time.sleep(5)  # 增加间隔
```

---

### 问题：内存泄漏

**症状**: 内存持续增长

**排查步骤**:

```python
# 内存分析
import tracemalloc
tracemalloc.start()

# 运行代码
run_automation()

# 查看内存快照
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

---

## 日志分析

### 日志位置

| 日志 | 路径 |
|------|------|
| 应用日志 | logs/wxbot.log |
| MCP日志 | logs/mcp.log |
| 错误日志 | logs/error.log |

### 日志分析命令

```powershell
# 查看最近错误
Get-Content logs\wxbot.log -Tail 100 | Select-String "ERROR"

# 统计错误类型
Get-Content logs\wxbot.log | Select-String "ERROR" | Group-Object

# 查找特定时间段日志
Get-Content logs\wxbot.log | Select-String "2026-03-23 10:"
```

---

## 常见错误代码

| 错误码 | 说明 | 解决方法 |
|--------|------|---------|
| E001 | 微信窗口未找到 | 启动微信客户端 |
| E002 | 联系人不存在 | 检查联系人名称 |
| E003 | 消息发送超时 | 增加超时时间 |
| E004 | 剪贴板操作失败 | 重试或重启应用 |
| E005 | MCP连接失败 | 检查网络和端口 |
| E006 | 配置文件错误 | 检查 YAML 语法 |
| E007 | 权限不足 | 以管理员身份运行 |

---

## 紧急恢复

### 服务恢复

```bash
# 重启 MCP 服务
net stop jz-wxbot-mcp
net start jz-wxbot-mcp

# 或使用脚本
python scripts/restart_service.py
```

### 配置恢复

```bash
# 恢复默认配置
git checkout config/

# 重新生成配置
python scripts/generate_config.py
```

---

**维护者**: jz-wxbot 开发团队  
**最后更新**: 2026-03-23