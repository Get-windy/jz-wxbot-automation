# jz-wxbot-automation OpenClaw 集成架构设计

## 📋 项目概述

### 项目目标
1. 学习 pywechat 项目优秀代码并集成
2. 合法合规控制个人微信和企业微信服务客户
3. 研究 Windows 版微信版本更新保持兼容
4. 提高使用过程的准确性和可靠性
5. 调用 OpenClaw 助手实现消息控制、群消息、朋友圈、群发、添加好友

### 核心价值
- **智能化**: 通过 OpenClaw AI 助手实现智能消息处理和自动回复
- **可扩展**: 插件化架构支持多种功能扩展
- **安全性**: 人性化操作模块降低风控风险
- **双微信**: 同时支持个人微信和企业微信

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenClaw 平台                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ AI 助手服务  │  │  会话管理   │  │  插件系统    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OpenClaw 微信桥接层                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Bridge Service                          │   │
│  │  • 消息路由        • 命令解析        • 状态同步           │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 消息监听服务 │  │ 命令执行服务 │  │ 事件通知服务 │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     微信自动化核心层                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               MessageSenderInterface                      │   │
│  │         (统一消息发送器抽象接口)                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ WeChatSender │  │ WXWorkSender │  │HumanLikeOps  │          │
│  │  (个人微信)  │  │ (企业微信)   │  │ (人性化操作) │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
└─────────┼──────────────────┼────────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│   个人微信进程   │  │  企业微信进程    │
│  (WeChat.exe)   │  │  (WXWork.exe)   │
└─────────────────┘  └─────────────────┘
```

### 分层说明

| 层级 | 职责 | 关键组件 |
|------|------|----------|
| **OpenClaw 平台层** | AI 能力、会话管理、插件扩展 | AI 助手、Session Manager、Plugin System |
| **桥接层** | 协议转换、消息路由、命令执行 | Bridge Service、Message Listener、Command Executor |
| **自动化核心层** | 微信操作、人性化模拟 | Sender Interface、HumanLike Operations |
| **微信客户端层** | 实际微信进程操作 | WeChat.exe、WXWork.exe |

---

## 🔌 OpenClaw 集成接口设计

### 1. 消息读取接口 (MessageReader)

```python
class MessageReaderInterface(ABC):
    """消息读取接口 - 接收微信消息"""
    
    @abstractmethod
    def start_listening(self, callback: Callable[[WeChatMessage], None]) -> bool:
        """启动消息监听"""
        pass
    
    @abstractmethod
    def stop_listening(self) -> bool:
        """停止消息监听"""
        pass
    
    @abstractmethod
    def get_unread_messages(self, count: int = 10) -> List[WeChatMessage]:
        """获取未读消息"""
        pass

class WeChatMessage:
    """微信消息数据结构"""
    message_id: str
    sender_id: str
    sender_name: str
    chat_id: str
    chat_name: str
    chat_type: str  # 'private' | 'group'
    content: str
    message_type: str  # 'text' | 'image' | 'file' | 'link'
    timestamp: datetime
    is_mentioned: bool
```

### 2. 消息回复接口 (MessageReplier)

```python
class MessageReplierInterface(ABC):
    """消息回复接口 - 发送消息到微信"""
    
    @abstractmethod
    def send_text(self, chat_id: str, message: str) -> SendResult:
        """发送文本消息"""
        pass
    
    @abstractmethod
    def send_image(self, chat_id: str, image_path: str) -> SendResult:
        """发送图片消息"""
        pass
    
    @abstractmethod
    def send_file(self, chat_id: str, file_path: str) -> SendResult:
        """发送文件"""
        pass
    
    @abstractmethod
    def reply_message(self, message_id: str, content: str) -> SendResult:
        """回复指定消息"""
        pass
```

### 3. 群消息管理接口 (GroupManager)

```python
class GroupManagerInterface(ABC):
    """群消息管理接口"""
    
    @abstractmethod
    def get_group_list(self) -> List[GroupInfo]:
        """获取群聊列表"""
        pass
    
    @abstractmethod
    def get_group_members(self, group_id: str) -> List[MemberInfo]:
        """获取群成员列表"""
        pass
    
    @abstractmethod
    def send_group_message(self, group_id: str, message: str) -> SendResult:
        """发送群消息"""
        pass
    
    @abstractmethod
    def at_members(self, group_id: str, member_ids: List[str], message: str) -> SendResult:
        """@群成员"""
        pass
    
    @abstractmethod
    def set_group_announcement(self, group_id: str, content: str) -> bool:
        """设置群公告"""
        pass
```

### 4. 朋友圈操作接口 (MomentsManager)

```python
class MomentsManagerInterface(ABC):
    """朋友圈操作接口"""
    
    @abstractmethod
    def get_moments(self, count: int = 20) -> List[MomentInfo]:
        """获取朋友圈动态"""
        pass
    
    @abstractmethod
    def post_text(self, content: str, visible_to: str = 'all') -> bool:
        """发文字朋友圈"""
        pass
    
    @abstractmethod
    def post_images(self, image_paths: List[str], content: str = '') -> bool:
        """发图片朋友圈"""
        pass
    
    @abstractmethod
    def like_moment(self, moment_id: str) -> bool:
        """点赞朋友圈"""
        pass
    
    @abstractmethod
    def comment_moment(self, moment_id: str, content: str) -> bool:
        """评论朋友圈"""
        pass
```

### 5. 群发信息接口 (MassSender)

```python
class MassSenderInterface(ABC):
    """群发信息接口"""
    
    @abstractmethod
    def send_to_contacts(self, contact_ids: List[str], message: str) -> MassSendResult:
        """群发给指定联系人"""
        pass
    
    @abstractmethod
    def send_to_groups(self, group_ids: List[str], message: str) -> MassSendResult:
        """群发给指定群聊"""
        pass
    
    @abstractmethod
    def send_to_tags(self, tags: List[str], message: str) -> MassSendResult:
        """按标签群发"""
        pass

class MassSendResult:
    """群发结果"""
    total: int
    success: int
    failed: int
    failed_list: List[str]
```

### 6. 添加好友接口 (ContactManager)

```python
class ContactManagerInterface(ABC):
    """联系人管理接口"""
    
    @abstractmethod
    def get_contact_list(self) -> List[ContactInfo]:
        """获取联系人列表"""
        pass
    
    @abstractmethod
    def search_contact(self, keyword: str) -> List[ContactInfo]:
        """搜索联系人"""
        pass
    
    @abstractmethod
    def add_friend(self, user_id: str, message: str = '') -> AddFriendResult:
        """添加好友"""
        pass
    
    @abstractmethod
    def accept_friend_request(self, request_id: str) -> bool:
        """接受好友请求"""
        pass
    
    @abstractmethod
    def delete_friend(self, user_id: str) -> bool:
        """删除好友"""
        pass
    
    @abstractmethod
    def set_remark(self, user_id: str, remark: str) -> bool:
        """设置备注"""
        pass
```

---

## 🔄 OpenClaw Bridge Service 设计

### 架构设计

```python
class OpenClawBridgeService:
    """OpenClaw 微信桥接服务"""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.message_reader: MessageReaderInterface
        self.message_replier: MessageReplierInterface
        self.group_manager: GroupManagerInterface
        self.moments_manager: MomentsManagerInterface
        self.mass_sender: MassSenderInterface
        self.contact_manager: ContactManagerInterface
        
        # OpenClaw 连接
        self.openclaw_client: OpenClawClient
        
    async def start(self):
        """启动桥接服务"""
        # 1. 初始化微信发送器
        await self._initialize_wechat_senders()
        
        # 2. 连接到 OpenClaw
        await self._connect_to_openclaw()
        
        # 3. 启动消息监听
        await self._start_message_listening()
        
        # 4. 注册 OpenClaw 命令处理器
        await self._register_command_handlers()
    
    async def _on_message_received(self, message: WeChatMessage):
        """消息接收回调"""
        # 转发到 OpenClaw 进行 AI 处理
        response = await self.openclaw_client.send_message(
            session_id=message.chat_id,
            message=message.content,
            context={
                'sender_name': message.sender_name,
                'chat_type': message.chat_type,
                'is_mentioned': message.is_mentioned
            }
        )
        
        # 如果有回复，发送回微信
        if response and response.should_reply:
            await self.message_replier.send_text(
                message.chat_id, 
                response.content
            )
```

### OpenClaw 客户端集成

```python
class OpenClawClient:
    """OpenClaw 客户端"""
    
    def __init__(self, gateway_url: str, agent_id: str):
        self.gateway_url = gateway_url
        self.agent_id = agent_id
        self.ws_connection: WebSocket
        
    async def send_message(
        self, 
        session_id: str, 
        message: str,
        context: dict = None
    ) -> OpenClawResponse:
        """发送消息到 OpenClaw"""
        payload = {
            'type': 'message',
            'session_id': session_id,
            'agent_id': self.agent_id,
            'content': message,
            'context': context or {}
        }
        
        async with self.ws_connection as ws:
            await ws.send(json.dumps(payload))
            response = await ws.recv()
            return OpenClawResponse.from_json(response)
    
    async def register_command_handler(
        self, 
        command: str, 
        handler: Callable
    ):
        """注册命令处理器"""
        self.command_handlers[command] = handler
```

---

## 📁 目录结构设计

```
I:\jz-wxbot-automation/
├── core/                          # 核心模块
│   ├── __init__.py
│   ├── message_sender_interface.py  # 消息发送接口（已有）
│   ├── message_reader_interface.py  # 消息读取接口（新增）
│   ├── human_like_operations.py     # 人性化操作（已有）
│   └── exceptions.py                # 异常定义
│
├── senders/                       # 发送器实现
│   ├── __init__.py
│   ├── wechat_sender_v3.py        # 个人微信发送器（已有）
│   ├── wxwork_sender.py           # 企业微信发送器（已有）
│   └── sender_factory.py          # 发送器工厂
│
├── readers/                       # 消息读取器
│   ├── __init__.py
│   ├── wechat_reader.py           # 个人微信消息读取
│   └── wxwork_reader.py           # 企业微信消息读取
│
├── managers/                      # 管理器
│   ├── __init__.py
│   ├── group_manager.py           # 群管理
│   ├── contact_manager.py         # 联系人管理
│   ├── moments_manager.py         # 朋友圈管理
│   └── mass_sender.py             # 群发管理
│
├── bridge/                        # OpenClaw 桥接层
│   ├── __init__.py
│   ├── bridge_service.py          # 桥接服务主类
│   ├── openclaw_client.py         # OpenClaw 客户端
│   ├── message_router.py          # 消息路由
│   ├── command_executor.py        # 命令执行器
│   └── event_notifier.py          # 事件通知
│
├── plugins/                       # 插件系统
│   ├── __init__.py
│   ├── plugin_base.py             # 插件基类
│   ├── auto_reply_plugin.py       # 自动回复插件
│   ├── keyword_reply_plugin.py    # 关键词回复插件
│   ├── schedule_plugin.py         # 定时任务插件
│   └── ai_chat_plugin.py          # AI 聊天插件
│
├── api/                           # API 接口
│   ├── __init__.py
│   ├── rest_api.py                # REST API
│   └── websocket_api.py           # WebSocket API
│
├── config/                        # 配置文件
│   ├── config.yaml                # 主配置
│   ├── openclaw.yaml              # OpenClaw 配置
│   └── plugins.yaml               # 插件配置
│
├── utils/                         # 工具模块
│   ├── __init__.py
│   ├── logger.py                  # 日志工具
│   ├── crypto.py                  # 加密工具
│   └── helpers.py                 # 辅助函数
│
├── tests/                         # 测试用例
│   ├── test_senders.py
│   ├── test_readers.py
│   └── test_bridge.py
│
├── docs/                          # 文档
│   ├── ARCHITECTURE.md            # 架构文档
│   ├── API.md                     # API 文档
│   └── PLUGIN_DEVELOPMENT.md      # 插件开发指南
│
├── examples/                      # 示例代码
│   ├── basic_usage.py
│   ├── openclaw_integration.py
│   └── custom_plugin.py
│
├── main.py                        # 主程序入口
├── requirements.txt               # 依赖
└── README.md                      # 项目说明
```

---

## 🔧 配置文件设计

### 主配置 (config.yaml)

```yaml
# jz-wxbot-automation 主配置
version: "2.0"

# 微信配置
wechat:
  personal:
    enabled: true
    process_names: ["WeChat.exe", "Weixin.exe"]
    auto_reconnect: true
    reconnect_interval: 5
  
  work:
    enabled: true
    process_names: ["WXWork.exe"]
    auto_reconnect: true

# 人性化操作配置
human_like:
  enabled: true
  random_delay: true
  curve_movement: true
  reading_pause: true
  small_moves: true

# 桥接服务配置
bridge:
  host: "127.0.0.1"
  port: 8080
  debug: false

# 日志配置
logging:
  level: "INFO"
  file: "logs/wxbot.log"
  max_size: "10MB"
  backup_count: 5
```

### OpenClaw 配置 (openclaw.yaml)

```yaml
# OpenClaw 集成配置
openclaw:
  # Gateway 连接
  gateway:
    url: "ws://127.0.0.1:3100"
    agent_id: "wxbot-agent"
    reconnect: true
    heartbeat_interval: 30
  
  # 消息处理
  message:
    # 自动回复配置
    auto_reply:
      enabled: true
      # 私聊自动回复
      private_chat:
        enabled: true
        mention_only: false
      # 群聊自动回复
      group_chat:
        enabled: true
        mention_only: true  # 仅在被@时回复
        prefix: ""          # 触发前缀
    
    # AI 模型配置
    ai_model:
      provider: "openai"
      model: "gpt-4"
      temperature: 0.7
      max_tokens: 2000
  
  # 命令配置
  commands:
    prefix: "/"
    commands:
      - name: "help"
        description: "显示帮助信息"
      - name: "status"
        description: "查看机器人状态"
      - name: "send"
        description: "发送消息"
        admin_only: true
      - name: "group"
        description: "群管理命令"
        admin_only: true
  
  # 权限配置
  permissions:
    admin_users:
      - "wxid_xxxxx"
    admin_groups:
      - "xxxxx@chatroom"
```

---

## 🔐 安全与合规设计

### 安全措施

1. **数据加密**
   - 敏感配置加密存储
   - 通信数据 TLS 加密
   - 本地日志脱敏处理

2. **访问控制**
   - 基于 OpenClaw 的权限管理
   - 管理员白名单
   - 操作审计日志

3. **风控对抗**
   - 人性化操作模拟
   - 随机延迟和轨迹
   - 操作频率限制

### 合规要求

1. **使用限制**
   - 仅用于学习和研究目的
   - 不得用于商业用途
   - 遵守微信用户协议

2. **功能限制**
   - 不支持批量添加好友
   - 限制群发频率
   - 禁止恶意营销

3. **隐私保护**
   - 不存储聊天记录
   - 用户数据本地处理
   - 支持数据删除

---

## 📊 技术实现路线图

### Phase 1: 基础集成 (1-2周)

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 消息读取接口实现 | P0 | 待开发 |
| OpenClaw 客户端开发 | P0 | 待开发 |
| 基础桥接服务 | P0 | 待开发 |
| 配置系统完善 | P1 | 待开发 |

### Phase 2: 功能扩展 (2-3周)

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 群管理功能 | P0 | 待开发 |
| 联系人管理 | P1 | 待开发 |
| 自动回复插件 | P0 | 待开发 |
| AI 对话插件 | P1 | 待开发 |

### Phase 3: 高级功能 (3-4周)

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 朋友圈操作 | P1 | 待开发 |
| 群发功能 | P2 | 待开发 |
| 添加好友 | P2 | 待开发 |
| 定时任务 | P1 | 待开发 |

### Phase 4: 稳定性与优化 (持续)

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 单元测试覆盖 | P1 | 待开发 |
| 性能优化 | P1 | 待开发 |
| 文档完善 | P2 | 待开发 |
| 示例代码 | P2 | 待开发 |

---

## 🧪 测试策略

### 单元测试

```python
# tests/test_bridge.py
import pytest
from bridge import OpenClawBridgeService

class TestOpenClawBridge:
    
    @pytest.fixture
    def bridge_service(self):
        return OpenClawBridgeService(config=test_config)
    
    async def test_message_routing(self, bridge_service):
        """测试消息路由"""
        message = WeChatMessage(
            chat_id="test_chat",
            content="hello"
        )
        result = await bridge_service._on_message_received(message)
        assert result is not None
    
    async def test_command_execution(self, bridge_service):
        """测试命令执行"""
        command = "/status"
        result = await bridge_service.execute_command(command)
        assert result.success
```

### 集成测试

```python
# tests/test_integration.py
class TestIntegration:
    
    async def test_full_message_flow(self):
        """测试完整消息流程"""
        # 1. 启动桥接服务
        # 2. 发送测试消息
        # 3. 验证 OpenClaw 处理
        # 4. 验证回复发送
        pass
```

---

## 📝 开发规范

### 代码风格

- 遵循 PEP 8 规范
- 使用类型注解
- 编写文档字符串

### 提交规范

```
feat: 添加新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具链
```

### 分支策略

- `main`: 主分支，稳定版本
- `develop`: 开发分支
- `feature/*`: 功能分支
- `hotfix/*`: 紧急修复分支

---

## 📚 参考资源

1. [OpenClaw 文档](https://docs.openclaw.ai)
2. [pyautogui 文档](https://pyautogui.readthedocs.io)
3. [pywin32 文档](https://mhammond.github.io/pywin32.html)
4. [微信自动化最佳实践](./docs/best-practices.md)

---

## 📞 联系方式

- 项目负责人: devops-engineer
- 创建时间: 2026-03-16
- 版本: v1.0.0