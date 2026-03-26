# jz-wxbot-automation 错误处理参考手册

**版本**: v1.0  
**创建时间**: 2026-03-23  
**适用对象**: 开发人员、运维人员

---

## 📖 目录

1. [错误代码体系](#错误代码体系)
2. [常见错误场景](#常见错误场景)
3. [错误处理最佳实践](#错误处理最佳实践)
4. [异常类参考](#异常类参考)
5. [日志与诊断](#日志与诊断)
6. [恢复策略](#恢复策略)

---

## 错误代码体系

### 错误代码格式

```
[模块]-[类型]-[序号]
```

| 模块 | 代码 | 说明 |
|------|------|------|
| 核心模块 | WX | 微信核心操作 |
| 消息模块 | MSG | 消息收发 |
| 窗口模块 | WIN | 窗口操作 |
| 自动化模块 | AUTO | 自动化操作 |
| MCP模块 | MCP | MCP服务 |
| 配置模块 | CFG | 配置相关 |
| 网络模块 | NET | 网络通信 |

| 类型 | 代码 | 说明 |
|------|------|------|
| 运行时错误 | R | Runtime Error |
| 配置错误 | C | Configuration Error |
| 权限错误 | P | Permission Error |
| 超时错误 | T | Timeout Error |
| 连接错误 | N | Network/Connection Error |
| 资源错误 | S | Resource Error |

### 错误代码速查表

| 错误码 | 说明 | 严重级别 | 解决方案 |
|--------|------|---------|---------|
| WX-R-001 | 微信窗口未找到 | 高 | 启动微信客户端 |
| WX-R-002 | 微信进程不存在 | 高 | 启动微信客户端 |
| WX-R-003 | 微信窗口无响应 | 中 | 重启微信客户端 |
| WX-S-001 | 剪贴板操作失败 | 中 | 重试或清理剪贴板 |
| WX-P-001 | 窗口操作权限不足 | 高 | 以管理员身份运行 |
| MSG-R-001 | 消息发送失败 | 中 | 检查联系人名称 |
| MSG-R-002 | 消息发送超时 | 中 | 增加超时时间 |
| MSG-S-001 | 输入框未找到 | 中 | 检查微信窗口状态 |
| WIN-R-001 | 窗口句柄无效 | 中 | 重新获取窗口句柄 |
| WIN-R-002 | 窗口已关闭 | 高 | 重新初始化 |
| AUTO-R-001 | 自动化操作失败 | 中 | 检查操作序列 |
| AUTO-T-001 | 操作执行超时 | 中 | 增加超时设置 |
| MCP-N-001 | MCP连接失败 | 高 | 检查网络和端口 |
| MCP-T-001 | MCP请求超时 | 中 | 增加超时时间 |
| CFG-C-001 | 配置文件不存在 | 高 | 创建配置文件 |
| CFG-C-002 | 配置格式错误 | 高 | 修复YAML/JSON语法 |
| NET-N-001 | 网络连接失败 | 高 | 检查网络连接 |

---

## 常见错误场景

### 场景1：微信窗口检测失败

**错误代码**: WX-R-001 / WX-R-002

**典型错误信息**:
```
WeChatWindowNotFoundError: 未找到微信窗口
ProcessNotFoundError: 微信进程未运行
```

**触发条件**:
- 微信客户端未启动
- 微信最小化到系统托盘
- 微信窗口标题被修改
- 多开微信导致窗口识别混乱

**诊断代码**:
```python
import psutil
import win32gui

def diagnose_wechat_window():
    """诊断微信窗口问题"""
    
    # 1. 检查进程
    processes = [p.info['name'] for p in psutil.process_iter(['name'])]
    wechat_running = any(name in processes for name in ['WeChat.exe', 'Weixin.exe'])
    wxwork_running = 'WXWork.exe' in processes
    
    print(f"个人微信进程: {'✅ 运行中' if wechat_running else '❌ 未运行'}")
    print(f"企业微信进程: {'✅ 运行中' if wxwork_running else '❌ 未运行'}")
    
    # 2. 检查窗口
    def enum_windows_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if '微信' in title or 'WeChat' in title:
                windows.append((hwnd, title))
        return True
    
    windows = []
    win32gui.EnumWindows(enum_windows_callback, windows)
    
    print(f"\n找到的微信窗口:")
    for hwnd, title in windows:
        print(f"  - {title} (hwnd: {hwnd})")
    
    return {
        'wechat_running': wechat_running,
        'wxwork_running': wxwork_running,
        'windows': windows
    }

# 运行诊断
diagnose_wechat_window()
```

**解决方案**:
```python
from jz_wxbot.wechat_sender import WeChatSenderV3

# 方案1: 手动指定窗口标题
sender = WeChatSenderV3(window_title="你的微信窗口标题")

# 方案2: 使用进程名强制绑定
sender = WeChatSenderV3(process_name="WeChat.exe")

# 方案3: 启动微信客户端
import subprocess
subprocess.Popen(["C:\\Program Files\\Tencent\\WeChat\\WeChat.exe"])
```

---

### 场景2：消息发送失败

**错误代码**: MSG-R-001 / MSG-R-002 / MSG-S-001

**典型错误信息**:
```
MessageSendError: 消息发送失败
TimeoutError: 消息发送超时
InputBoxNotFoundError: 输入框未找到
```

**触发条件**:
- 联系人/群聊名称错误
- 微信窗口失去焦点
- 剪贴板被其他程序占用
- 发送快捷键配置错误
- 网络延迟导致超时

**诊断代码**:
```python
def diagnose_message_send(sender, target, message):
    """诊断消息发送问题"""
    
    # 1. 检查窗口状态
    if not sender.is_window_ready():
        print("❌ 窗口未就绪")
        return False
    
    # 2. 检查联系人
    if not sender.contact_exists(target):
        print(f"❌ 联系人不存在: {target}")
        return False
    
    # 3. 测试剪贴板
    import pyperclip
    test_text = "剪贴板测试"
    pyperclip.copy(test_text)
    if pyperclip.paste() != test_text:
        print("❌ 剪贴板异常")
        return False
    
    print("✅ 诊断通过")
    return True
```

**解决方案**:
```python
# 配置重试和超时
config = {
    'retry_count': 5,
    'retry_delay': 2.0,
    'timeout': 30.0,
    'clipboard_retry': 3
}

sender = WeChatSenderV3(config=config)

# 带重试的发送
def send_with_retry(sender, target, message, max_retries=5):
    """带重试的消息发送"""
    for attempt in range(max_retries):
        try:
            result = sender.send_message(target, message)
            if result:
                return {'success': True, 'attempts': attempt + 1}
        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
    
    return {'success': False, 'attempts': max_retries}
```

---

### 场景3：MCP服务连接失败

**错误代码**: MCP-N-001 / MCP-T-001

**典型错误信息**:
```
MCPConnectionError: MCP服务连接失败
MCPTimeoutError: MCP请求超时
```

**触发条件**:
- MCP服务未启动
- 端口被占用
- 防火墙阻止连接
- 配置文件错误

**诊断代码**:
```python
import socket
import requests

def diagnose_mcp_service(host='localhost', port=8080):
    """诊断MCP服务"""
    
    # 1. 检查端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    
    if result == 0:
        print(f"✅ 端口 {port} 可访问")
    else:
        print(f"❌ 端口 {port} 不可访问")
        return False
    
    # 2. 检查健康状态
    try:
        response = requests.get(f"http://{host}:{port}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务健康检查通过")
            return True
        else:
            print(f"❌ 服务返回异常状态: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 服务请求失败: {e}")
        return False

# 运行诊断
diagnose_mcp_service()
```

**解决方案**:
```bash
# 1. 检查并重启服务
net stop jz-wxbot-mcp
net start jz-wxbot-mcp

# 2. 检查端口占用
netstat -ano | findstr :8080

# 3. 直接启动调试
python mcp_server.py --debug --port 8081
```

---

### 场景4：剪贴板操作失败

**错误代码**: WX-S-001

**典型错误信息**:
```
ClipboardError: 剪贴板操作失败
ClipboardTimeoutError: 剪贴板访问超时
```

**触发条件**:
- 其他程序正在使用剪贴板
- 剪贴板服务异常
- 权限不足

**解决方案**:
```python
import pyperclip
import time

def safe_clipboard_copy(text, max_retries=3, delay=0.5):
    """安全的剪贴板复制"""
    for attempt in range(max_retries):
        try:
            pyperclip.copy(text)
            # 验证复制成功
            if pyperclip.paste() == text:
                return True
        except Exception as e:
            print(f"剪贴板操作失败 (尝试 {attempt + 1}): {e}")
            time.sleep(delay * (attempt + 1))
    
    # 最后尝试：清空剪贴板后重试
    try:
        pyperclip.copy('')
        time.sleep(0.1)
        pyperclip.copy(text)
        return pyperclip.paste() == text
    except:
        return False

# 使用示例
if safe_clipboard_copy("测试消息"):
    print("剪贴板就绪")
else:
    print("剪贴板异常，请手动处理")
```

---

### 场景5：自动化操作被中断

**错误代码**: AUTO-R-001 / AUTO-T-001

**典型错误信息**:
```
AutomationError: 自动化操作失败
pyautogui.FailSafeException: 操作被安全机制中断
```

**触发条件**:
- 鼠标移动到屏幕角落触发安全机制
- 用户手动干预操作
- 操作超时

**解决方案**:
```python
import pyautogui

# 1. 调整安全设置
pyautogui.FAILSAFE = True  # 保持启用（推荐）
pyautogui.PAUSE = 0.1      # 操作间隔
pyautogui.TIMEOUT = 30     # 超时时间

# 2. 安全操作包装器
def safe_automation(func, *args, **kwargs):
    """安全自动化操作包装器"""
    max_retries = kwargs.pop('max_retries', 3)
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except pyautogui.FailSafeException:
            print(f"⚠️ 操作被安全机制中断 (尝试 {attempt + 1})")
            print("请将鼠标移离屏幕角落")
            time.sleep(2)
        except pyautogui.TimeoutException:
            print(f"⚠️ 操作超时 (尝试 {attempt + 1})")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ 操作异常: {e}")
            raise
    
    raise AutomationError(f"自动化操作失败，已重试 {max_retries} 次")

# 使用示例
result = safe_automation(sender.send_message, "群名", "消息", max_retries=5)
```

---

## 错误处理最佳实践

### 1. 异常捕获模式

```python
from jz_wxbot.exceptions import (
    WeChatWindowNotFoundError,
    MessageSendError,
    TimeoutError,
    ClipboardError,
    ConfigurationError
)

def robust_send_message(sender, target, message):
    """健壮的消息发送函数"""
    
    try:
        result = sender.send_message(target, message)
        return {'success': True, 'result': result}
    
    except WeChatWindowNotFoundError as e:
        # 窗口问题：尝试重新初始化
        logger.warning(f"微信窗口未找到: {e}")
        sender.reinitialize()
        return {'success': False, 'error': 'window_not_found', 'retry': True}
    
    except MessageSendError as e:
        # 发送失败：记录错误
        logger.error(f"消息发送失败: {e}")
        return {'success': False, 'error': str(e), 'retry': False}
    
    except TimeoutError as e:
        # 超时：可以重试
        logger.warning(f"操作超时: {e}")
        return {'success': False, 'error': 'timeout', 'retry': True}
    
    except ClipboardError as e:
        # 剪贴板问题：等待后重试
        logger.warning(f"剪贴板错误: {e}")
        time.sleep(1)
        return {'success': False, 'error': 'clipboard', 'retry': True}
    
    except ConfigurationError as e:
        # 配置错误：需要用户干预
        logger.error(f"配置错误: {e}")
        return {'success': False, 'error': 'configuration', 'retry': False}
    
    except Exception as e:
        # 未知错误
        logger.exception(f"未知错误: {e}")
        return {'success': False, 'error': 'unknown', 'retry': False}
```

### 2. 重试策略

```python
import time
import random
from functools import wraps

def retry_on_error(max_retries=3, backoff_factor=2, jitter=True):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        # 计算延迟（指数退避 + 随机抖动）
                        delay = backoff_factor ** attempt
                        if jitter:
                            delay += random.uniform(0, 1)
                        
                        logger.warning(
                            f"第 {attempt + 1} 次尝试失败: {e}, "
                            f"{delay:.1f}秒后重试"
                        )
                        time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator

# 使用示例
@retry_on_error(max_retries=5, backoff_factor=2)
def send_message_with_retry(sender, target, message):
    return sender.send_message(target, message)
```

### 3. 优雅降级

```python
class GracefulDegradation:
    """优雅降级处理"""
    
    def __init__(self):
        self.primary_sender = None
        self.fallback_sender = None
        self.degraded_mode = False
    
    def send_message(self, target, message):
        """发送消息（带降级）"""
        
        # 正常模式
        if not self.degraded_mode:
            try:
                result = self.primary_sender.send_message(target, message)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"主发送器失败: {e}, 切换到降级模式")
                self.degraded_mode = True
        
        # 降级模式
        try:
            result = self.fallback_sender.send_message(target, message)
            return result
        except Exception as e:
            logger.error(f"备用发送器也失败: {e}")
            raise MessageSendError("所有发送器均不可用")
```

---

## 异常类参考

### 自定义异常类

```python
class WxBotBaseException(Exception):
    """基础异常类"""
    
    def __init__(self, message, error_code=None, details=None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self):
        return {
            'error': self.__class__.__name__,
            'message': str(self),
            'error_code': self.error_code,
            'details': self.details
        }


class WeChatWindowNotFoundError(WxBotBaseException):
    """微信窗口未找到"""
    def __init__(self, message="未找到微信窗口", window_type=None):
        super().__init__(
            message, 
            error_code="WX-R-001",
            details={'window_type': window_type}
        )


class ProcessNotFoundError(WxBotBaseException):
    """进程未找到"""
    def __init__(self, process_name):
        super().__init__(
            f"进程未找到: {process_name}",
            error_code="WX-R-002",
            details={'process_name': process_name}
        )


class MessageSendError(WxBotBaseException):
    """消息发送错误"""
    def __init__(self, message="消息发送失败", target=None, reason=None):
        super().__init__(
            message,
            error_code="MSG-R-001",
            details={'target': target, 'reason': reason}
        )


class TimeoutError(WxBotBaseException):
    """超时错误"""
    def __init__(self, operation, timeout_seconds):
        super().__init__(
            f"操作超时: {operation}",
            error_code="AUTO-T-001",
            details={'operation': operation, 'timeout': timeout_seconds}
        )


class ClipboardError(WxBotBaseException):
    """剪贴板错误"""
    def __init__(self, operation="copy"):
        super().__init__(
            f"剪贴板操作失败: {operation}",
            error_code="WX-S-001",
            details={'operation': operation}
        )


class ConfigurationError(WxBotBaseException):
    """配置错误"""
    def __init__(self, message, config_file=None, key=None):
        super().__init__(
            message,
            error_code="CFG-C-002",
            details={'config_file': config_file, 'key': key}
        )


class MCPConnectionError(WxBotBaseException):
    """MCP连接错误"""
    def __init__(self, host, port, reason=None):
        super().__init__(
            f"MCP连接失败: {host}:{port}",
            error_code="MCP-N-001",
            details={'host': host, 'port': port, 'reason': reason}
        )
```

---

## 日志与诊断

### 日志配置

```python
import logging
import logging.handlers
from pathlib import Path

def setup_logging(log_dir="logs", level=logging.INFO):
    """配置日志系统"""
    
    Path(log_dir).mkdir(exist_ok=True)
    
    # 根日志器
    logger = logging.getLogger('jz_wxbot')
    logger.setLevel(level)
    
    # 文件处理器（按日期滚动）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        f"{log_dir}/wxbot.log",
        when='midnight',
        backupCount=30
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # 错误日志处理器
    error_handler = logging.FileHandler(f"{log_dir}/error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
        'File: %(pathname)s:%(lineno)d\n'
    ))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger

# 使用
logger = setup_logging()
```

### 诊断工具

```python
class DiagnosticTool:
    """诊断工具集"""
    
    @staticmethod
    def check_environment():
        """检查运行环境"""
        import sys
        import platform
        
        results = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.architecture(),
            'checks': []
        }
        
        # 检查依赖
        dependencies = ['pyautogui', 'pyperclip', 'win32gui', 'psutil']
        for dep in dependencies:
            try:
                __import__(dep)
                results['checks'].append({'name': dep, 'status': 'ok'})
            except ImportError:
                results['checks'].append({'name': dep, 'status': 'missing'})
        
        return results
    
    @staticmethod
    def check_wechat():
        """检查微信状态"""
        import psutil
        import win32gui
        
        results = {
            'wechat': {'running': False, 'windows': []},
            'wxwork': {'running': False, 'windows': []}
        }
        
        # 检查进程
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] in ['WeChat.exe', 'Weixin.exe']:
                results['wechat']['running'] = True
            if proc.info['name'] == 'WXWork.exe':
                results['wxwork']['running'] = True
        
        # 检查窗口
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                if '微信' in title or 'WeChatMainWndForPC' in class_name:
                    results['wechat']['windows'].append({
                        'hwnd': hwnd, 'title': title, 'class': class_name
                    })
                if 'WeWorkWindow' in class_name:
                    results['wxwork']['windows'].append({
                        'hwnd': hwnd, 'title': title, 'class': class_name
                    })
            return True
        
        win32gui.EnumWindows(enum_callback, [])
        return results
    
    @staticmethod
    def generate_report():
        """生成诊断报告"""
        import json
        from datetime import datetime
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment': DiagnosticTool.check_environment(),
            'wechat': DiagnosticTool.check_wechat()
        }
        
        return json.dumps(report, indent=2, ensure_ascii=False)

# 使用
print(DiagnosticTool.generate_report())
```

---

## 恢复策略

### 自动恢复

```python
class AutoRecovery:
    """自动恢复机制"""
    
    def __init__(self, sender):
        self.sender = sender
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
    
    def recover_and_retry(self, operation, *args, **kwargs):
        """恢复并重试操作"""
        
        while self.recovery_attempts < self.max_recovery_attempts:
            try:
                return operation(*args, **kwargs)
            
            except WeChatWindowNotFoundError:
                logger.info("尝试恢复：重新初始化发送器")
                self.sender.reinitialize()
                self.recovery_attempts += 1
            
            except ProcessNotFoundError:
                logger.info("尝试恢复：启动微信进程")
                self._start_wechat()
                self.recovery_attempts += 1
            
            except TimeoutError:
                logger.info("尝试恢复：增加超时时间")
                kwargs['timeout'] = kwargs.get('timeout', 30) * 2
                self.recovery_attempts += 1
            
            time.sleep(2)
        
        raise RecoveryError(f"自动恢复失败，已尝试 {self.recovery_attempts} 次")
    
    def _start_wechat(self):
        """启动微信进程"""
        import subprocess
        wechat_paths = [
            r"C:\Program Files\Tencent\WeChat\WeChat.exe",
            r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
        ]
        
        for path in wechat_paths:
            if Path(path).exists():
                subprocess.Popen([path])
                time.sleep(10)  # 等待启动
                return True
        
        return False
```

### 手动恢复指南

| 问题 | 恢复步骤 |
|------|---------|
| 微信未响应 | 1. 任务管理器结束进程<br>2. 重新启动微信<br>3. 等待完全加载后重试 |
| 发送器失效 | 1. 调用 `sender.reinitialize()`<br>2. 检查窗口状态<br>3. 重新执行操作 |
| MCP服务异常 | 1. 停止服务<br>2. 检查端口占用<br>3. 重启服务 |
| 配置损坏 | 1. 备份当前配置<br>2. 恢复默认配置<br>3. 重新设置参数 |

---

## 附录

### A. 错误日志示例

```
2026-03-23 10:15:30,123 - jz_wxbot.sender - WARNING - 窗口未找到，尝试重新初始化
2026-03-23 10:15:32,456 - jz_wxbot.sender - INFO - 成功获取微信窗口句柄: 123456
2026-03-23 10:15:35,789 - jz_wxbot.sender - ERROR - 消息发送失败
File: wechat_sender_v3.py:245
Traceback (most recent call last):
  File "wechat_sender_v3.py", line 240, in send_message
    self._paste_and_send(content)
  File "wechat_sender_v3.py", line 180, in _paste_and_send
    raise MessageSendError("发送超时")
MessageSendError: 发送超时
```

### B. 相关文档

- [故障排查指南](./TROUBLESHOOTING.md)
- [用户使用手册](./USER_MANUAL.md)
- [API使用指南](./API_USAGE_GUIDE.md)
- [开发指南](./DEVELOPMENT_GUIDE.md)

---

**维护者**: jz-wxbot 开发团队  
**最后更新**: 2026-03-23