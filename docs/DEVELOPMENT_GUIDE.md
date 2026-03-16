# jz-wxbot-automation 开发指南

**版本**: v1.0  
**创建日期**: 2026-03-16  
**项目**: jz-wxbot-automation  
**适用对象**: 开发者、贡献者

---

## 📋 目录

1. [开发环境搭建](#开发环境搭建)
2. [项目结构详解](#项目结构详解)
3. [核心模块说明](#核心模块说明)
4. [开发规范](#开发规范)
5. [调试技巧](#调试技巧)
6. [测试指南](#测试指南)
7. [贡献流程](#贡献流程)

---

## 开发环境搭建

### 系统要求

| 要求 | 说明 |
|------|------|
| **操作系统** | Windows 10/11 (64 位) |
| **Python 版本** | 3.9 - 3.12 |
| **微信版本** | 个人微信 PC 版 3.9+ / 企业微信 4.1+ |
| **内存** | ≥ 8GB |
| **磁盘空间** | ≥ 1GB |

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/jxyk2007/jz-wxbot-automation.git
cd jz-wxbot-automation
```

#### 2. 创建虚拟环境（推荐）

```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows CMD
python -m venv venv
venv\Scripts\activate.bat
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**requirements.txt 内容**：
```txt
pyautogui>=0.9.54
pyperclip>=1.8.0
pywin32>=306
psutil>=5.9.0
pillow>=10.0.0
mcp>=1.0.0
pyyaml>=6.0
```

#### 4. 验证安装

```bash
# 运行窗口检查器
python window_inspector.py findwechat

# 测试 MCP 服务器
python mcp_server.py --help
```

### 开发工具推荐

| 工具 | 用途 | 下载链接 |
|------|------|---------|
| **VS Code** | 代码编辑器 | https://code.visualstudio.com |
| **Python 扩展** | Python 开发支持 | VS Code 市场 |
| **Git** | 版本控制 | https://git-scm.com |
| **Postman** | API 测试 | https://postman.com |

---

## 项目结构详解

```
jz-wxbot-automation/
├── 📁 bridge/                    # OpenClaw 桥接服务
│   ├── bridge_service.py         # 桥接服务核心
│   ├── openclaw_client.py        # OpenClaw 客户端
│   └── __init__.py               # 包初始化
│
├── 📁 config/                    # 配置文件
│   ├── config.yaml               # 主配置文件
│   └── mcp_config.json           # MCP 配置
│
├── 📁 docs/                      # 项目文档
│   ├── ARCHITECTURE.md           # 架构文档
│   ├── OPENCLAW_INTEGRATION.md   # OpenClaw 集成指南
│   ├── DEVELOPMENT_GUIDE.md      # 开发指南（本文件）
│   ├── API_USAGE_GUIDE.md        # API 使用指南
│   └── DEPLOYMENT_GUIDE.md       # 部署指南
│
├── 📁 examples/                  # 使用示例
│   ├── basic_usage.py            # 基础用法示例
│   └── scheduled_messages.py     # 定时消息示例
│
├── 📁 tests/                     # 测试代码
│   ├── test_mcp_server.py        # MCP 服务器测试
│   └── test_senders.py           # 发送器测试
│
├── main.py                       # 主程序入口 ⭐
├── mcp_server.py                 # MCP 服务器 ⭐
├── message_sender_interface.py   # 消息发送器接口 ⭐
│
├── wechat_sender_v3.py           # 个人微信发送器
├── wxwork_sender_robust.py       # 企业微信发送器（推荐）
├── human_like_operations.py      # 人性化操作模块 ⭐
│
├── auto_daily_report_v2.py       # 自动化系统 v2.0
├── direct_sender.py              # 传统发送器（兼容）
├── window_inspector.py           # 窗口检查器
│
├── requirements.txt              # Python 依赖
├── README.md                     # 项目说明
├── LICENSE                       # 许可证
└── .gitignore                    # Git 忽略文件
```

---

## 核心模块说明

### 1. MCP 服务器 (mcp_server.py)

**职责**: 实现 MCP 协议，向 OpenClaw 提供微信操作工具

**核心功能**：
- MCP 工具注册和暴露
- 工具调用处理
- 资源管理
- 提示词模板

**关键代码**：
```python
from mcp.server import Server

app = Server("jz-wxbot")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """返回可用的微信工具列表"""
    return [
        Tool(
            name="wxbot_send_message",
            description="发送微信消息",
            inputSchema={...}
        ),
        # ... 其他工具
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """调用微信工具"""
    if name == "wxbot_send_message":
        return await handle_send_message(arguments)
    # ... 其他工具处理
```

**开发要点**：
- 工具定义要清晰描述功能和参数
- 错误处理要完善，返回有意义的错误信息
- 输入验证要严格，防止无效参数

---

### 2. 消息发送器接口 (message_sender_interface.py)

**职责**: 定义统一的微信发送器接口，支持多实现

**接口定义**：
```python
from abc import ABC, abstractmethod

class MessageSenderInterface(ABC):
    """消息发送器抽象基类"""
    
    @abstractmethod
    def send_message(self, target: str, message: str) -> bool:
        """发送消息"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查发送器是否可用"""
        pass
    
    @abstractmethod
    def get_info(self) -> dict:
        """获取发送器信息"""
        pass
```

**实现类**：
- `WeChatSenderV3` - 个人微信实现
- `WXWorkSenderRobust` - 企业微信实现

---

### 3. 人性化操作模块 (human_like_operations.py)

**职责**: 模拟真人操作行为，避免风控检测

**核心功能**：
```python
class HumanLikeOperations:
    """人性化操作类"""
    
    def human_delay(self, base_time: float = 1.0, variance: float = 0.3):
        """人性化延迟 - 正态分布随机延迟"""
        delay = random.gauss(base_time, variance)
        time.sleep(max(0.1, delay))
    
    def human_move_to(self, x: int, y: int, duration: float = None):
        """人性化鼠标移动 - 曲线轨迹"""
        # 使用缓动函数模拟真实轨迹
        # 添加随机抖动
        pass
    
    def simulate_reading_pause(self):
        """模拟阅读停顿"""
        pause_time = random.uniform(0.5, 2.5)
        time.sleep(pause_time)
    
    def random_small_move(self, probability: float = 0.3):
        """无意识小移动（30% 概率）"""
        if random.random() < probability:
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
            pyautogui.moveRel(offset_x, offset_y, duration=0.1)
```

**反风控原理**：
| 检测点 | 对策 |
|--------|------|
| 规律性时间间隔 | 正态分布随机延迟 |
| 直线鼠标轨迹 | 缓动曲线 + 随机抖动 |
| 机械点击模式 | 随机小幅移动 + 自然停顿 |
| 固定操作顺序 | 思考停顿 + 操作随机化 |

---

### 4. 桥接服务 (bridge/bridge_service.py)

**职责**: OpenClaw 与微信自动化之间的桥接

**核心功能**：
```python
class BridgeService:
    """桥接服务类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.openclaw_client = None
        self.mcp_server = None
    
    async def start(self):
        """启动桥接服务"""
        # 1. 连接 OpenClaw
        # 2. 启动 MCP 服务器
        # 3. 建立消息通道
    
    async def process_message(self, message: dict):
        """处理消息"""
        # 1. 接收微信消息
        # 2. 转发到 OpenClaw
        # 3. 获取 AI 回复
        # 4. 发送回复到微信
```

---

### 5. 自动化系统 (auto_daily_report_v2.py)

**职责**: 完整的自动化报告发送系统

**核心特点**：
- 智能发送器选择
- 自动回退机制
- 统一配置管理
- 详细状态报告

**使用示例**：
```python
from auto_daily_report_v2 import AutoReportSystemV2

system = AutoReportSystemV2()

# 初始化
system.initialize_senders()

# 查看状态
system.print_status()

# 执行自动化
system.run_full_automation()
```

---

## 开发规范

### 代码风格

遵循 **PEP 8** Python 代码风格指南：

```python
# ✅ 好的命名
def send_message_to_group(group_name: str, content: str) -> bool:
    """发送消息到群聊"""
    pass

# ❌ 避免的命名
def sendMsg(gn, c):  # 命名不清晰
    pass
```

**关键规则**：
1. 函数和变量使用 `snake_case`
2. 类名使用 `PascalCase`
3. 常量使用 `UPPER_CASE`
4. 私有成员使用 `_prefix`
5. 函数添加文档字符串

### 类型注解

使用 Python 类型注解提高代码可读性：

```python
from typing import Optional, List, Dict, Any

def process_messages(
    messages: List[dict],
    limit: int = 10,
    filter_type: Optional[str] = None
) -> Dict[str, Any]:
    """处理消息列表"""
    pass
```

### 错误处理

使用异常处理保证程序稳定性：

```python
try:
    result = await send_message(target, content)
    if not result:
        logger.warning("消息发送失败")
except WeChatNotRunningError as e:
    logger.error(f"微信未运行：{e}")
    raise
except Exception as e:
    logger.exception(f"未知错误：{e}")
    raise
```

### 日志规范

```python
import logging

logger = logging.getLogger(__name__)

# 不同级别的使用场景
logger.debug("调试信息 - 详细执行过程")
logger.info("普通信息 - 正常流程")
logger.warning("警告信息 - 不影响继续执行")
logger.error("错误信息 - 某个操作失败")
logger.critical("严重错误 - 程序无法继续")
```

### Git 提交规范

```bash
# 格式：<type>(<scope>): <subject>

# 示例
feat(mcp): 添加朋友圈发送工具
fix(sender): 修复企业微信窗口激活问题
docs(readme): 更新快速开始指南
test(mcp): 添加 MCP 服务器单元测试
refactor(core): 重构消息发送逻辑
```

**提交类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具

---

## 调试技巧

### 1. 使用窗口检查器

```bash
# 交互式获取窗口信息
python window_inspector.py click

# 操作步骤：
# 1. 运行命令
# 2. 将鼠标移到目标微信窗口
# 3. 按 Ctrl+Alt+I
# 4. 查看输出的窗口信息
```

**输出示例**：
```
窗口句柄：12345678
窗口标题：技术交流群 - 微信
窗口类名：WeChatChatWnd
窗口位置：(100, 200) - (600, 800)
进程 ID: 9876
```

### 2. 启用调试日志

```python
# 在代码中设置调试级别
import logging
logging.basicConfig(level=logging.DEBUG)

# 或在配置文件中
# config.yaml
logging:
  level: DEBUG
  file: logs/wxbot_debug.log
```

### 3. 测试单个发送器

```bash
# 测试个人微信发送器
python wechat_sender_v3.py test

# 测试企业微信发送器
python wxwork_sender_robust.py test

# 手动选择窗口测试
python wxwork_sender_robust.py manual
```

### 4. MCP 服务器调试

```bash
# 启动 MCP 服务器（stdio 模式）
python mcp_server.py

# 测试工具调用
python -c "
from mcp.client import Client
client = Client()
client.connect('stdio', 'python mcp_server.py')
tools = client.list_tools()
print(tools)
"
```

### 5. 使用调试器

```bash
# VS Code 调试配置
# .vscode/launch.json
{
    "name": "Python: 当前文件",
    "type": "python",
    "request": "launch",
    "program": "${file}",
    "console": "integratedTerminal",
    "justMyCode": false
}
```

---

## 测试指南

### 单元测试

```python
# tests/test_mcp_server.py
import pytest
from mcp_server import handle_send_message

@pytest.mark.asyncio
async def test_send_message_success():
    """测试消息发送成功"""
    result = await handle_send_message({
        "target": "测试群",
        "message": "测试消息",
        "chat_type": "group"
    })
    
    assert result[0].text is not None
    assert "success" in result[0].text

@pytest.mark.asyncio
async def test_send_message_invalid_target():
    """测试无效目标"""
    with pytest.raises(ValueError):
        await handle_send_message({
            "target": "",
            "message": "测试消息"
        })
```

**运行测试**：
```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_mcp_server.py -v

# 查看测试覆盖率
pytest --cov=jz_wxbot tests/
```

### 集成测试

```python
# tests/test_integration.py
import pytest
from auto_daily_report_v2 import AutoReportSystemV2

@pytest.mark.skip(reason="需要微信运行")
def test_full_automation():
    """测试完整自动化流程"""
    system = AutoReportSystemV2()
    system.initialize_senders()
    
    # 执行自动化（需要人工确认）
    result = system.run_full_automation()
    
    assert result["success"] is True
```

### 手动测试清单

| 测试项 | 测试步骤 | 预期结果 |
|--------|---------|---------|
| 个人微信发送 | 运行 `wechat_sender_v3.py test` | 成功发送测试消息 |
| 企业微信发送 | 运行 `wxwork_sender_robust.py test` | 成功发送测试消息 |
| MCP 工具调用 | 通过 OpenClaw 调用工具 | 工具正常响应 |
| 窗口检测 | 运行 `window_inspector.py` | 正确识别微信窗口 |
| 人性化操作 | 观察鼠标移动 | 曲线移动，有随机延迟 |

---

## 贡献流程

### 1. Fork 项目

在 GitHub 上点击 Fork 按钮创建自己的副本

### 2. 克隆到本地

```bash
git clone https://github.com/YOUR_USERNAME/jz-wxbot-automation.git
cd jz-wxbot-automation
```

### 3. 创建特性分支

```bash
git checkout -b feature/your-feature-name
```

### 4. 开发和测试

```bash
# 编写代码
# 添加测试
# 运行测试
pytest tests/
```

### 5. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能"
```

### 6. 推送分支

```bash
git push origin feature/your-feature-name
```

### 7. 创建 Pull Request

在 GitHub 上提交 PR，描述你的更改

### 8. 代码审查

等待维护者审查，根据反馈修改

---

## 常见问题

### Q1: 如何添加新的 MCP 工具？

**A**: 在 `mcp_server.py` 中添加：

```python
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... 现有工具
        Tool(
            name="wxbot_new_tool",
            description="新工具描述",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "wxbot_new_tool":
        return await handle_new_tool(arguments)
```

### Q2: 如何支持新的微信版本？

**A**: 修改窗口识别逻辑：

```python
# 在 window_inspector.py 中
WECHAT_WINDOW_CLASSES = [
    "WeChatChatWnd",      # 旧版本
    "WeChatWnd",          # 新版本
    "WXWorkWindow",       # 企业微信
]
```

### Q3: 如何调试窗口激活问题？

**A**: 使用窗口检查器：

```bash
python window_inspector.py findwechat
```

检查输出中的窗口状态，确保窗口未最小化。

---

## 相关资源

- [MCP 官方文档](https://modelcontextprotocol.io)
- [Python 类型注解指南](https://docs.python.org/3/library/typing.html)
- [PEP 8 代码风格指南](https://pep8.org)
- [pyautogui 文档](https://pyautogui.readthedocs.io)
- [pywin32 文档](https://mhammond.github.io/pywin32)

---

**文档维护**: jz-wxbot-automation 开发团队  
**反馈邮箱**: dev@jz-wxbot.local  
**最后更新**: 2026-03-16
