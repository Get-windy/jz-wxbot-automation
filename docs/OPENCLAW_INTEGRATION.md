# OpenClaw 微信自动化 MCP 集成

## 📋 架构概述

### MCP (Model Context Protocol) 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenClaw 助手系统                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  AI 模型    │  │  MCP 客户端  │  │  会话管理    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
└─────────┼──────────────────┼─────────────────────────────────────┘
          │                  │ MCP Protocol
          └──────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────┐
│              jz-wxbot MCP Server (工具提供者)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   MCP Tool Registry                       │   │
│  │  • wxbot_send_message     • wxbot_read_messages          │   │
│  │  • wxbot_send_moments     • wxbot_mass_send              │   │
│  │  • wxbot_add_friend       • wxbot_group_manage           │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 消息发送器   │  │ 消息读取器   │  │ 人性化操作   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
└─────────┼──────────────────┼─────────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│   个人微信进程   │  │  企业微信进程    │
│  (WeChat.exe)   │  │  (WXWork.exe)   │
└─────────────────┘  └─────────────────┘
```

---

## 🔧 MCP 工具定义

### 1. wxbot_send_message - 发送消息

```json
{
  "name": "wxbot_send_message",
  "description": "发送微信消息到指定聊天（私聊或群聊）",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "string",
        "description": "聊天ID（用户wxid或群chatroom_id）"
      },
      "chat_name": {
        "type": "string",
        "description": "聊天名称（用于搜索定位）"
      },
      "message": {
        "type": "string",
        "description": "要发送的消息内容"
      },
      "message_type": {
        "type": "string",
        "enum": ["text", "image", "file"],
        "default": "text",
        "description": "消息类型"
      },
      "wechat_type": {
        "type": "string",
        "enum": ["personal", "work", "auto"],
        "default": "auto",
        "description": "微信类型：personal=个人微信，work=企业微信，auto=自动选择"
      },
      "at_users": {
        "type": "array",
        "items": { "type": "string" },
        "description": "@的用户ID列表（群聊有效）"
      }
    },
    "required": ["message"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "message_id": { "type": "string" },
      "timestamp": { "type": "string" },
      "error": { "type": "string" }
    }
  }
}
```

**示例调用**:
```json
{
  "tool": "wxbot_send_message",
  "arguments": {
    "chat_name": "技术交流群",
    "message": "大家好，这是测试消息",
    "wechat_type": "auto"
  }
}
```

---

### 2. wxbot_read_messages - 读取消息

```json
{
  "name": "wxbot_read_messages",
  "description": "读取微信聊天消息（未读消息或历史消息）",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "string",
        "description": "聊天ID（可选，不指定则读取所有未读）"
      },
      "chat_name": {
        "type": "string",
        "description": "聊天名称"
      },
      "count": {
        "type": "integer",
        "default": 10,
        "description": "读取消息数量"
      },
      "include_read": {
        "type": "boolean",
        "default": false,
        "description": "是否包含已读消息"
      },
      "mark_as_read": {
        "type": "boolean",
        "default": true,
        "description": "是否标记为已读"
      }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "messages": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "message_id": { "type": "string" },
            "sender_id": { "type": "string" },
            "sender_name": { "type": "string" },
            "chat_id": { "type": "string" },
            "chat_name": { "type": "string" },
            "content": { "type": "string" },
            "timestamp": { "type": "string" },
            "is_mentioned": { "type": "boolean" }
          }
        }
      },
      "total": { "type": "integer" }
    }
  }
}
```

**示例调用**:
```json
{
  "tool": "wxbot_read_messages",
  "arguments": {
    "count": 20,
    "mark_as_read": true
  }
}
```

---

### 3. wxbot_send_moments - 发送朋友圈

```json
{
  "name": "wxbot_send_moments",
  "description": "发送微信朋友圈动态",
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "朋友圈文字内容"
      },
      "images": {
        "type": "array",
        "items": { "type": "string" },
        "description": "图片路径列表（最多9张）"
      },
      "visibility": {
        "type": "string",
        "enum": ["public", "private", "friends", "specified"],
        "default": "public",
        "description": "可见范围：public=公开，private=私密，friends=好友可见，specified=指定人可见"
      },
      "visible_to": {
        "type": "array",
        "items": { "type": "string" },
        "description": "可见用户ID列表（visibility=specified时有效）"
      },
      "location": {
        "type": "string",
        "description": "位置信息"
      }
    },
    "required": ["content"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "moment_id": { "type": "string" },
      "error": { "type": "string" }
    }
  }
}
```

**示例调用**:
```json
{
  "tool": "wxbot_send_moments",
  "arguments": {
    "content": "今天天气真好！",
    "images": ["C:/photos/sky.jpg"],
    "location": "北京"
  }
}
```

---

### 4. wxbot_mass_send - 群发消息

```json
{
  "name": "wxbot_mass_send",
  "description": "群发消息给多个联系人或群聊",
  "inputSchema": {
    "type": "object",
    "properties": {
      "targets": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "type": { "type": "string", "enum": ["contact", "group"] },
            "id": { "type": "string" },
            "name": { "type": "string" }
          }
        },
        "description": "群发目标列表"
      },
      "message": {
        "type": "string",
        "description": "群发消息内容"
      },
      "interval": {
        "type": "integer",
        "default": 3,
        "description": "发送间隔（秒）"
      },
      "random_interval": {
        "type": "boolean",
        "default": true,
        "description": "是否随机化间隔"
      },
      "personalize": {
        "type": "boolean",
        "default": false,
        "description": "是否个性化（插入对方昵称）"
      }
    },
    "required": ["targets", "message"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "total": { "type": "integer" },
      "sent": { "type": "integer" },
      "failed": { "type": "integer" },
      "failed_targets": { "type": "array" }
    }
  }
}
```

**示例调用**:
```json
{
  "tool": "wxbot_mass_send",
  "arguments": {
    "targets": [
      { "type": "group", "name": "技术交流群" },
      { "type": "group", "name": "产品讨论群" }
    ],
    "message": "大家好，本周五下午3点开例会",
    "interval": 5,
    "random_interval": true
  }
}
```

---

### 5. wxbot_add_friend - 添加好友

```json
{
  "name": "wxbot_add_friend",
  "description": "添加微信好友",
  "inputSchema": {
    "type": "object",
    "properties": {
      "user_id": {
        "type": "string",
        "description": "用户微信ID"
      },
      "phone": {
        "type": "string",
        "description": "手机号（用于搜索）"
      },
      "wechat_id": {
        "type": "string",
        "description": "微信号（用于搜索）"
      },
      "message": {
        "type": "string",
        "default": "你好，我是通过微信搜索添加的",
        "description": "好友申请消息"
      },
      "remark": {
        "type": "string",
        "description": "备注名"
      }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "status": {
        "type": "string",
        "enum": ["sent", "accepted", "already_friend", "not_found", "failed"]
      },
      "error": { "type": "string" }
    }
  }
}
```

**示例调用**:
```json
{
  "tool": "wxbot_add_friend",
  "arguments": {
    "phone": "13800138000",
    "message": "你好，我是老王的朋友",
    "remark": "老王朋友-小李"
  }
}
```

---

### 6. wxbot_group_manage - 群管理

```json
{
  "name": "wxbot_group_manage",
  "description": "微信群管理操作",
  "inputSchema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": [
          "create",
          "get_members",
          "add_members",
          "remove_members",
          "set_announcement",
          "set_name",
          "dissolve",
          "get_qrcode"
        ],
        "description": "群管理操作类型"
      },
      "group_id": {
        "type": "string",
        "description": "群ID"
      },
      "group_name": {
        "type": "string",
        "description": "群名称"
      },
      "members": {
        "type": "array",
        "items": { "type": "string" },
        "description": "成员ID列表"
      },
      "announcement": {
        "type": "string",
        "description": "群公告内容"
      },
      "new_name": {
        "type": "string",
        "description": "新群名"
      }
    },
    "required": ["action"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "data": { "type": "object" },
      "error": { "type": "string" }
    }
  }
}
```

**示例调用**:
```json
{
  "tool": "wxbot_group_manage",
  "arguments": {
    "action": "set_announcement",
    "group_name": "技术交流群",
    "announcement": "本周五下午3点开会，请大家准时参加"
  }
}
```

---

### 7. wxbot_get_contacts - 获取联系人

```json
{
  "name": "wxbot_get_contacts",
  "description": "获取微信联系人列表",
  "inputSchema": {
    "type": "object",
    "properties": {
      "type": {
        "type": "string",
        "enum": ["all", "friends", "groups", "official"],
        "default": "all",
        "description": "联系人类型"
      },
      "search": {
        "type": "string",
        "description": "搜索关键词"
      },
      "page": {
        "type": "integer",
        "default": 1
      },
      "page_size": {
        "type": "integer",
        "default": 50
      }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "contacts": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": { "type": "string" },
            "name": { "type": "string" },
            "remark": { "type": "string" },
            "type": { "type": "string" },
            "avatar": { "type": "string" }
          }
        }
      },
      "total": { "type": "integer" }
    }
  }
}
```

---

### 8. wxbot_get_status - 获取状态

```json
{
  "name": "wxbot_get_status",
  "description": "获取微信自动化服务状态",
  "inputSchema": {
    "type": "object",
    "properties": {}
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "wechat": {
        "type": "object",
        "properties": {
          "personal": {
            "type": "object",
            "properties": {
              "connected": { "type": "boolean" },
              "user_id": { "type": "string" },
              "nickname": { "type": "string" }
            }
          },
          "work": {
            "type": "object",
            "properties": {
              "connected": { "type": "boolean" },
              "user_id": { "type": "string" },
              "nickname": { "type": "string" }
            }
          }
        }
      },
      "stats": {
        "type": "object",
        "properties": {
          "messages_sent": { "type": "integer" },
          "messages_received": { "type": "integer" },
          "uptime": { "type": "integer" }
        }
      }
    }
  }
}
```

---

## 🚀 MCP Server 实现

### Python MCP Server 框架

```python
# mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent

class WxBotMCPServer:
    """微信自动化 MCP Server"""
    
    def __init__(self):
        self.server = Server("wxbot-mcp-server")
        self._register_tools()
    
    def _register_tools(self):
        """注册所有 MCP 工具"""
        
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="wxbot_send_message",
                    description="发送微信消息",
                    inputSchema={...}
                ),
                # ... 其他工具
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name == "wxbot_send_message":
                return await self._send_message(arguments)
            # ... 其他工具处理
    
    async def _send_message(self, args: dict) -> list[TextContent]:
        """发送消息实现"""
        chat_name = args.get("chat_name")
        message = args.get("message")
        
        # 调用微信发送器
        result = await self.sender.send_message(message, chat_name)
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": result.success,
                "message_id": result.message_id,
                "timestamp": datetime.now().isoformat()
            })
        )]

# 启动 MCP Server
if __name__ == "__main__":
    server = WxBotMCPServer()
    server.run()
```

### 配置 OpenClaw 连接

在 OpenClaw 配置中添加 MCP Server:

```json
{
  "mcpServers": {
    "wxbot": {
      "command": "python",
      "args": ["I:\\jz-wxbot-automation\\mcp_server.py"],
      "env": {}
    }
  }
}
```

---

## 📊 数据流程图

```
用户: "帮我给技术交流群发一条消息：明天开会"
          ↓
OpenClaw AI 理解意图
          ↓
调用 MCP 工具: wxbot_send_message
          ↓
{
  "chat_name": "技术交流群",
  "message": "明天开会",
  "wechat_type": "auto"
}
          ↓
WxBot MCP Server 处理
          ↓
调用 HumanLikeOperations (人性化操作)
          ↓
UI 自动化操作微信客户端
          ↓
发送消息成功
          ↓
返回结果给 OpenClaw
          ↓
OpenClaw 回复用户: "消息已发送到技术交流群"
```

---

## ⚠️ 注意事项

1. **安全性**: 所有敏感操作需要用户确认
2. **频率限制**: 遵守微信操作频率限制
3. **人性化**: 使用 HumanLikeOperations 模拟真人操作
4. **错误处理**: 完善的错误处理和重试机制
5. **日志记录**: 记录所有操作用于审计

---

## 📁 相关文件

- `mcp_server.py` - MCP Server 主程序
- `tools/` - 工具实现目录
- `config/mcp_config.json` - MCP 配置
- `docs/ARCHITECTURE.md` - 原架构文档

---

## 🆕 版本更新

### v2.1.0 (2026-03-16)
- ✅ 完善所有工具实现
- ✅ 添加朋友圈发送功能
- ✅ 添加添加好友功能
- ✅ 添加群管理功能
- ✅ 添加联系人获取功能
- ✅ 支持 HTTP 模式
- ✅ 添加完整测试用例

---

**更新时间**: 2026-03-16 08:00
**版本**: v2.1 (MCP 架构)