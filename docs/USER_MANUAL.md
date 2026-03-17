# jz-wxbot-automation 用户使用手册

**版本**: v2.1  
**创建日期**: 2026-03-18  
**项目**: jz-wxbot-automation  

---

## 📖 目录

1. [产品概述](#产品概述)
2. [安装与配置](#安装与配置)
3. [基础功能使用](#基础功能使用)
4. [高级功能使用](#高级功能使用)
5. [典型应用场景](#典型应用场景)
6. [常见问题解答](#常见问题解答)
7. [安全与注意事项](#安全与注意事项)

---

## 产品概述

### 什么是 jz-wxbot-automation？

jz-wxbot-automation 是一个**微信自动化助手**，通过 UI 自动化技术模拟真人操作，帮助你：

- 📨 自动发送消息到个人微信和企业微信
- 🤖 智能客服自动回复
- 📢 批量发送通知和公告
- ⏰ 定时发送日报、周报
- 🌐 发送朋友圈动态
- 👥 管理微信群聊
- 🔌 与 OpenClaw AI 助手集成

### 核心特点

| 特点 | 说明 |
|------|------|
| 🎯 **双微信支持** | 同时支持个人微信和企业微信，智能回退 |
| 🛡️ **反风控系统** | 人性化操作模拟，避免机器特征检测 |
| 🔄 **零缓存重启检测** | 微信重启后自动重新连接 |
| 🤖 **AI 集成** | 通过 MCP 协议与 OpenClaw 无缝集成 |
| 📊 **详细日志** | 完整的操作记录和错误追踪 |

---

## 安装与配置

### 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.7 或更高版本
- **微信**: 个人微信 PC 版 和/或 企业微信 PC 版

### 安装步骤

#### 1. 克隆或下载项目

```bash
# 如果从 Git 仓库获取
git clone <repository-url>
cd jz-wxbot-automation
```

或直接解压项目到 `I:\jz-wxbot-automation`

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖清单**：
```
pyautogui>=0.9.53
pyperclip>=1.8.0
pywin32>=305
psutil>=5.9.0
schedule>=1.2.0
```

#### 3. 验证安装

```bash
python -c "import pyautogui; print('✅ 依赖安装成功')"
```

---

### 配置文件说明

#### 主配置文件：`auto_report_config.json`

```json
{
  "version": "2.0",
  "default_sender": "wechat",
  "sender_priority": ["wechat", "wxwork"],
  "fallback_enabled": true,
  
  "senders": {
    "wechat": {
      "type": "wechat",
      "enabled": true,
      "process_names": ["WeChat.exe", "Weixin.exe", "wechat.exe"],
      "default_group": "存储统计报告群",
      "target_groups": [
        {
          "name": "技术交流群",
          "hwnd": null,
          "enabled": true
        },
        {
          "name": "产品讨论群",
          "hwnd": null,
          "enabled": true
        }
      ]
    },
    "wxwork": {
      "type": "wxwork",
      "enabled": true,
      "process_names": ["WXWork.exe", "wxwork.exe"],
      "default_group": "蓝光统计",
      "target_groups": [
        {
          "name": "项目组",
          "hwnd": null,
          "enabled": true
        }
      ]
    }
  },
  
  "message_settings": {
    "add_timestamp": true,
    "add_sender_info": false,
    "format_style": "emoji"
  }
}
```

**配置项详解**：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `version` | string | "2.0" | 配置文件版本 |
| `default_sender` | string | "wechat" | 默认发送器：`wechat` 或 `wxwork` |
| `sender_priority` | array | ["wechat", "wxwork"] | 发送器优先级顺序 |
| `fallback_enabled` | boolean | true | 启用自动回退机制 |
| `senders.wechat.enabled` | boolean | true | 启用个人微信发送器 |
| `senders.wxwork.enabled` | boolean | true | 启用企业微信发送器 |
| `target_groups` | array | [] | 目标群聊列表 |
| `message_settings.add_timestamp` | boolean | true | 消息添加时间戳 |

---

## 基础功能使用

### 1. 发送消息

#### 方法 1：命令行发送

```bash
# 使用个人微信发送
python wechat_sender_v3.py send "群名" "消息内容"

# 使用企业微信发送
python wxwork_sender.py send "群名" "消息内容"

# 自动选择可用微信
python auto_daily_report_v2.py send "群名" "消息内容"
```

#### 方法 2：Python 脚本

```python
from wechat_sender_v3 import WeChatSenderV3

# 创建发送器实例
sender = WeChatSenderV3()

# 初始化（查找微信窗口）
if sender.initialize():
    # 发送消息
    success = sender.send_message("大家好！", "技术交流群")
    
    if success:
        print("✅ 发送成功")
    else:
        print("❌ 发送失败")
else:
    print("❌ 初始化失败，请检查微信是否运行")
```

#### 方法 3：双微信系统（推荐）

```python
from auto_daily_report_v2 import AutoReportSystemV2

# 创建自动化系统
system = AutoReportSystemV2()

# 初始化所有发送器
system.initialize_senders()

# 查看状态
system.print_status()

# 执行完整自动化（智能选择最佳发送器）
result = system.run_full_automation()

print(f"发送成功：{result['success']}")
print(f"使用发送器：{result['sender_used']}")
```

---

### 2. 读取消息

```python
from core.messages.enhanced_receiver import EnhancedMessageReceiver

# 创建接收器
receiver = EnhancedMessageReceiver()

# 读取新消息
messages = receiver.read_new_messages(limit=10)

for msg in messages:
    print(f"{msg.sender_name}: {msg.content}")
    print(f"时间：{msg.timestamp}")
    print(f"类型：{msg.chat_type}")
    print("---")
```

---

### 3. 发送朋友圈

```python
from wxwork_sender import WXWorkSenderRobust

sender = WXWorkSenderRobust()

# 发送纯文字朋友圈
sender.send_moments("今天天气真好！")

# 发送带图片的朋友圈
sender.send_moments(
    content="美丽的风景",
    images=["C:/photos/sky.jpg", "C:/photos/park.jpg"],
    visibility="public"  # public: 公开，private: 私密，friends: 好友可见
)
```

---

### 4. 群发消息

```python
from wxwork_sender import WXWorkSenderRobust
import time

sender = WXWorkSenderRobust()

# 群发通知
targets = ["技术交流群", "产品讨论群", "项目组"]
message = "本周五下午 3 点开例会，请大家准时参加"

success_count = 0
fail_count = 0

for target in targets:
    success = sender.send_message(message, target)
    
    if success:
        success_count += 1
        print(f"✅ 发送到 {target} 成功")
    else:
        fail_count += 1
        print(f"❌ 发送到 {target} 失败")
    
    # 人性化延迟（3-8 秒随机）
    time.sleep(3 + random.uniform(0, 5))

print(f"\n发送完成：成功 {success_count}, 失败 {fail_count}")
```

---

## 高级功能使用

### 1. OpenClaw AI 集成

#### 配置 MCP Server

在 OpenClaw 配置中添加：

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

#### 通过 AI 助手发送消息

直接对 OpenClaw 说：

> "帮我给技术交流群发一条消息：明天上午 10 点开会"

AI 会自动调用 MCP 工具 `wxbot_send_message` 执行。

#### 可用的 MCP 工具

| 工具名称 | 功能 | 示例 |
|---------|------|------|
| `wxbot_send_message` | 发送消息 | "给张三发消息：你好" |
| `wxbot_read_messages` | 读取消息 | "查看未读消息" |
| `wxbot_send_moments` | 发送朋友圈 | "发朋友圈：今天心情不错" |
| `wxbot_mass_send` | 群发消息 | "群发通知给所有群" |
| `wxbot_add_friend` | 添加好友 | "添加好友：13800138000" |
| `wxbot_group_manage` | 群管理 | "设置技术交流群公告" |
| `wxbot_get_contacts` | 获取联系人 | "查看我的联系人列表" |
| `wxbot_get_status` | 查看状态 | "查看微信连接状态" |

---

### 2. 定时任务

#### 使用 Windows 任务计划程序

1. 打开"任务计划程序"
2. 点击"创建基本任务"
3. 设置任务名称（如"微信日报发送"）
4. 设置触发器（每天 9:00）
5. 操作选择"启动程序"
6. 程序/脚本：`I:\jz-wxbot-automation\run_daily_auto.bat`
7. 完成创建

#### 使用 Python schedule 库

```python
import schedule
import time
from auto_daily_report_v2 import AutoReportSystemV2

system = AutoReportSystemV2()
system.initialize_senders()

# 每天早上 9 点发送日报
schedule.every().day.at("09:00").do(system.run_full_automation)

# 每天下午 6 点发送晚报
schedule.every().day.at("18:00").do(
    lambda: system.run_full_automation("晚报内容")
)

# 每周五发送周报
schedule.every().friday.at("17:00").do(
    lambda: system.run_full_automation("周报内容")
)

print("定时任务已启动...")

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### 3. 智能客服自动回复

```python
from core.message_handler import MessageHandler
from core.messages.enhanced_receiver import EnhancedMessageReceiver
from wechat_sender_v3 import WeChatSenderV3
import time

class SmartCustomerService:
    """智能客服系统"""
    
    def __init__(self):
        self.sender = WeChatSenderV3()
        self.receiver = EnhancedMessageReceiver()
        self.handler = MessageHandler()
        
        # 注册消息回调
        self.handler.register_callback(self.on_message)
        
        # 关键词回复规则
        self.replies = {
            "价格": "我们的产品价格是 99 元，具体规格请看官网",
            "联系": "联系方式：电话 12345678，微信 xxx",
            "地址": "公司地址：xxx 省 xxx 市 xxx 区",
            "帮助": "请问有什么可以帮助您的？",
            "你好": "您好！有什么可以帮到您？"
        }
    
    def on_message(self, message):
        """消息处理回调"""
        print(f"收到消息：{message.content}")
        
        # 检查是否包含关键词
        for keyword, reply in self.replies.items():
            if keyword in message.content:
                print(f"匹配关键词：{keyword}")
                self.sender.send_message(reply, message.chat_name)
                break
    
    def run(self):
        """运行客服系统"""
        print("智能客服系统已启动...")
        self.handler.start_listening()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("停止客服系统...")
            self.handler.stop_listening()

# 运行
service = SmartCustomerService()
service.run()
```

---

### 4. 人性化操作配置

```python
from human_like_operations import HumanLikeOperations

human_ops = HumanLikeOperations()

# 配置人性化参数
human_ops.config = {
    "delay_base": 1.0,        # 基础延迟（秒）
    "delay_variance": 0.3,    # 延迟波动范围
    "move_duration": 0.5,     # 鼠标移动时长
    "click_pause": 0.2,       # 点击前停顿
    "reading_pause": 1.0,     # 阅读停顿时长
    "random_move_chance": 0.3 # 无意识移动概率
}

# 使用人性化操作
human_ops.human_delay(1.0, 0.3)      # 人性化延迟
human_ops.human_move_to(500, 300)    # 人性化鼠标移动
human_ops.human_click(500, 300)      # 人性化点击
human_ops.simulate_reading_pause()   # 模拟阅读停顿
```

---

## 典型应用场景

### 场景 1：自动日报系统

**需求**：每天早上 9 点自动发送存储统计报告到指定群聊

**实现**：

```python
# auto_daily_report.py
from auto_daily_report_v2 import AutoReportSystemV2
import schedule
import time

def generate_report():
    """生成日报内容"""
    return """
📊 存储统计日报

📅 日期：2026-03-18

✅ 今日完成：
- 系统运行正常
- 存储空间使用率：65%
- 新增数据：1.2GB

⚠️ 提醒：
- A 区存储即将满载（85%）
- 建议清理过期数据

📈 趋势：平稳
    """

def send_daily_report():
    """发送日报"""
    system = AutoReportSystemV2()
    system.initialize_senders()
    
    report = generate_report()
    result = system.run_full_automation(report)
    
    if result['success']:
        print(f"✅ 日报发送成功（{result['sender_used']}）")
    else:
        print(f"❌ 日报发送失败：{result.get('error')}")

# 设置定时任务
schedule.every().day.at("09:00").do(send_daily_report)

print("🤖 自动日报系统已启动")
print("每天 09:00 自动发送存储统计报告")

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### 场景 2：群消息监控与自动回复

**需求**：监控客户咨询群，自动回复常见问题

**实现**：

```python
from core.messages.enhanced_receiver import EnhancedMessageReceiver
from wechat_sender_v3 import WeChatSenderV3
import time

class GroupMonitor:
    """群消息监控器"""
    
    def __init__(self, group_name, keywords):
        self.group_name = group_name
        self.keywords = keywords
        self.receiver = EnhancedMessageReceiver()
        self.sender = WeChatSenderV3()
        self.last_message_time = 0
    
    def check_messages(self):
        """检查新消息"""
        messages = self.receiver.read_new_messages(limit=10)
        
        for msg in messages:
            # 检查是否是指定群聊
            if msg.chat_name != self.group_name:
                continue
            
            # 检查是否是新消息（避免重复处理）
            msg_time = msg.timestamp.timestamp()
            if msg_time <= self.last_message_time:
                continue
            
            self.last_message_time = msg_time
            
            # 检查关键词
            for keyword, reply in self.keywords.items():
                if keyword in msg.content:
                    print(f"检测到关键词 '{keyword}'")
                    
                    # 发送回复（@发送者）
                    at_message = f"@{msg.sender_name} {reply}"
                    self.sender.send_message(at_message, self.group_name)
                    break
    
    def run(self):
        """运行监控"""
        print(f"开始监控群聊：{self.group_name}")
        
        while True:
            try:
                self.check_messages()
                time.sleep(3)  # 每 3 秒检查一次
            except Exception as e:
                print(f"监控出错：{e}")
                time.sleep(10)

# 配置关键词回复
keywords = {
    "价格": "我们的产品价格是 99 元，具体规格请看官网",
    "多少钱": "产品价格 99 元，包邮",
    "联系": "联系方式：电话 12345678",
    "地址": "公司地址：xxx 省 xxx 市",
    "帮助": "请问有什么可以帮助您的？"
}

# 启动监控
monitor = GroupMonitor("客户咨询群", keywords)
monitor.run()
```

---

### 场景 3：批量添加好友

**需求**：从手机号列表批量添加微信好友

**实现**：

```python
from wxwork_sender import WXWorkSenderRobust
import time
import random

def add_friends_from_list(phone_list, verify_message="你好，我是通过搜索添加的"):
    """批量添加好友"""
    sender = WXWorkSenderRobust()
    
    if not sender.find_wxwork_window():
        print("❌ 企业微信未运行")
        return
    
    success_count = 0
    fail_count = 0
    
    for phone in phone_list:
        print(f"正在添加：{phone}")
        
        try:
            # 调用添加好友功能
            result = sender.add_friend_by_phone(phone, verify_message)
            
            if result:
                success_count += 1
                print(f"✅ 添加成功：{phone}")
            else:
                fail_count += 1
                print(f"❌ 添加失败：{phone}")
            
            # 随机延迟（避免风控）
            delay = random.uniform(60, 120)  # 1-2 分钟
            print(f"等待 {delay:.0f} 秒...")
            time.sleep(delay)
            
        except Exception as e:
            fail_count += 1
            print(f"❌ 异常：{e}")
    
    print(f"\n添加完成：成功 {success_count}, 失败 {fail_count}")

# 使用示例
phone_list = [
    "13800138000",
    "13900139000",
    "13700137000"
]

add_friends_from_list(phone_list)
```

---

### 场景 4：会议提醒系统

**需求**：会议前 15 分钟自动提醒参会人员

**实现**：

```python
import schedule
import time
from datetime import datetime
from auto_daily_report_v2 import AutoReportSystemV2

class MeetingReminder:
    """会议提醒系统"""
    
    def __init__(self):
        self.system = AutoReportSystemV2()
        self.system.initialize_senders()
        
        self.meetings = [
            {
                "name": "周一例会",
                "time": "10:00",
                "day": "monday",
                "groups": ["技术交流群", "项目组"],
                "message": "📢 会议提醒\n\n各位同事，{meeting_name}将于{time}开始，请准时参加。\n\n会议内容：\n1. 项目进度汇报\n2. 问题讨论\n3. 下周计划"
            },
            {
                "name": "周五总结会",
                "time": "17:00",
                "day": "friday",
                "groups": ["技术交流群"],
                "message": "📢 会议提醒\n\n{meeting_name}将于{time}开始，请准备好本周工作总结。"
            }
        ]
    
    def send_reminder(self, meeting):
        """发送会议提醒"""
        message = meeting["message"].format(
            meeting_name=meeting["name"],
            time=meeting["time"]
        )
        
        for group in meeting["groups"]:
            result = self.system.send_to_group(group, message)
            print(f"发送到 {group}: {'✅' if result else '❌'}")
    
    def setup_schedule(self):
        """设置定时任务"""
        for meeting in self.meetings:
            # 会议前 15 分钟提醒
            if meeting["day"] == "monday":
                schedule.every().monday.at("09:45").do(
                    self.send_reminder, meeting
                )
            elif meeting["day"] == "friday":
                schedule.every().friday.at("16:45").do(
                    self.send_reminder, meeting
                )
    
    def run(self):
        """运行提醒系统"""
        self.setup_schedule()
        print("🤖 会议提醒系统已启动")
        
        while True:
            schedule.run_pending()
            time.sleep(60)

# 运行
reminder = MeetingReminder()
reminder.run()
```

---

## 常见问题解答

### Q1: 为什么找不到微信进程？

**A**: 可能的原因：
1. 微信未启动或未登录
2. 微信版本不兼容
3. 权限不足

**解决方案**：
- 确保微信已启动并登录
- 检查进程名称（WeChat.exe/Weixin.exe/WXWork.exe）
- 尝试以管理员权限运行脚本

---

### Q2: 消息发送失败怎么办？

**A**: 检查以下几点：
1. 微信窗口是否打开
2. 目标群聊是否在聊天列表中
3. 窗口是否被最小化
4. 查看错误日志获取详细信息

使用调试工具：
```bash
python window_inspector.py click
```

---

### Q3: 如何避免被微信风控？

**A**: 遵循以下建议：
1. ✅ 保持人性化操作开启
2. ✅ 使用随机延迟（3-10 秒）
3. ✅ 避免高频发送（每小时<100 条）
4. ✅ 模拟真人作息时间
5. ✅ 不要发送明显的测试内容

---

### Q4: 支持发送图片和文件吗？

**A**: 
- 朋友圈支持发送图片（最多 9 张）
- 聊天消息的图片/文件发送功能正在开发中
- 当前可以通过剪贴板手动发送

---

### Q5: 如何在后台运行？

**A**: 使用以下方法：
1. 使用批处理文件 + Windows 任务计划程序
2. 使用 `pythonw.exe` 运行（无控制台窗口）
3. 使用第三方工具如 NSSM 创建 Windows 服务

---

### Q6: 支持 Linux 或 macOS 吗？

**A**: 
- ❌ 当前仅支持 Windows
- 原因是依赖 Windows API（win32gui, pywin32）
- 未来可能通过 OCR 方案实现跨平台

---

## 安全与注意事项

### ⚠️ 使用风险

1. **封号风险**: 自动化操作可能违反微信使用条款
2. **法律风险**: 不得用于非法用途（诈骗、骚扰等）
3. **隐私风险**: 妥善保管配置文件和聊天记录

### 🛡️ 安全建议

1. **适度使用**: 保持合理的使用频率
2. **内容合规**: 不发送违规内容
3. **权限控制**: 限制脚本访问权限
4. **日志审计**: 定期检查操作日志
5. **备份配置**: 定期备份重要配置

### 📋 最佳实践

1. **双微信策略**: 同时配置个人微信和企业微信
2. **人性化设置**: 保持反风控功能开启
3. **错误处理**: 完善的异常捕获和重试机制
4. **定期更新**: 及时更新适配新版本微信
5. **测试验证**: 重要操作前先小范围测试

---

## 附录

### A. 快捷键参考

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+V` | 粘贴内容 |
| `Ctrl+A` | 全选 |
| `Enter` | 发送消息 |
| `Esc` | 返回/取消 |

### B. 窗口类名

| 微信类型 | 窗口类名 |
|---------|---------|
| 个人微信 | `WeChatMainWndForPC` |
| 企业微信 | `WeWorkWindow` |

### C. 相关文档

- [快速入门](./QUICKSTART.md)
- [API 使用指南](./API_USAGE_GUIDE.md)
- [开发指南](./DEVELOPMENT_GUIDE.md)
- [部署指南](./DEPLOYMENT_GUIDE.md)
- [项目 README](../README.md)

---

**文档维护**: jz-wxbot-automation 开发团队  
**反馈邮箱**: 364345866@qq.com  
**最后更新**: 2026-03-18
