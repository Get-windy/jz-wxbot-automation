# jz-wxbot-automation 常见问题 (FAQ)

**版本**: v1.0  
**创建日期**: 2026-03-24  
**适用对象**: 所有用户

---

## 📋 目录

- [安装与配置](#安装与配置)
- [消息发送](#消息发送)
- [微信客户端](#微信客户端)
- [MCP服务](#mcp服务)
- [自动化功能](#自动化功能)
- [安全与风控](#安全与风控)
- [故障排查](#故障排查)

---

## 安装与配置

### Q1: 支持哪些操作系统？

**A**: 目前仅支持 **Windows 10/11**。

原因：
- 依赖 Windows API（win32gui, pywin32）
- 微信 PC 版仅支持 Windows

不支持：Linux、macOS

### Q2: 需要安装哪些依赖？

**A**: 运行以下命令安装所有依赖：

```bash
pip install -r requirements.txt
```

主要依赖：
| 包名 | 版本 | 用途 |
|------|------|------|
| pyautogui | >=0.9.53 | GUI自动化 |
| pywin32 | >=305 | Windows API |
| psutil | >=5.9.0 | 进程管理 |
| pyperclip | >=1.8.0 | 剪贴板操作 |
| schedule | >=1.2.0 | 定时任务 |

### Q3: Python 版本要求？

**A**: **Python 3.7 或更高版本**。

推荐使用 Python 3.9 或 3.10 以获得最佳兼容性。

### Q4: 需要安装微信吗？

**A**: 需要。至少安装以下之一：
- 个人微信 PC 版
- 企业微信 PC 版

两者都安装效果更好（支持双微信回退）。

### Q5: 如何验证安装成功？

**A**: 运行诊断命令：

```bash
python -c "import pyautogui; print('✅ 依赖安装成功')"
python wechat_sender_v3.py test
```

---

## 消息发送

### Q6: 如何发送消息到指定群聊？

**A**: 有三种方式：

**方式1：命令行**
```bash
python wechat_sender_v3.py send "群名称" "消息内容"
```

**方式2：Python脚本**
```python
from wechat_sender_v3 import WeChatSenderV3
sender = WeChatSenderV3()
sender.initialize()
sender.send_message("消息内容", "群名称")
```

**方式3：通过OpenClaw**
> "帮我给技术交流群发一条消息：明天开会"

### Q7: 群名称填错了会怎样？

**A**: 消息会发送失败。解决方法：

1. 确保群名称完全正确（包括特殊字符）
2. 确保该群聊在聊天列表中
3. 可以使用模糊匹配功能

### Q8: 如何发送图片？

**A**: 当前版本主要支持文字消息。图片发送功能：
- 朋友圈支持发送图片（最多9张）
- 聊天消息图片发送正在开发中

### Q9: 可以发送文件吗？

**A**: 暂不支持直接发送文件。临时解决方案：
1. 使用剪贴板复制粘贴
2. 使用微信文件传输助手

### Q10: 消息发送失败怎么办？

**A**: 常见原因及解决方案：

| 原因 | 解决方案 |
|------|---------|
| 微信未运行 | 启动微信客户端 |
| 群名称错误 | 检查群名称拼写 |
| 窗口最小化 | 恢复微信窗口 |
| 窗口无焦点 | 点击微信窗口 |
| 剪贴板被占用 | 等待后重试 |

---

## 微信客户端

### Q11: 支持哪些微信版本？

**A**: 
- 个人微信：PC版 3.x 及以上
- 企业微信：PC版 4.x 及以上

### Q12: 支持微信多开吗？

**A**: 不建议多开。原因：
- 窗口识别可能混乱
- 可能导致发送错误目标

如需多开，请使用不同微信类型（个人+企业）。

### Q13: 微信最小化到托盘还能发送吗？

**A**: 可以，但需要：
- 微信仍在运行（进程存在）
- 窗口句柄有效

建议：发送前恢复微信窗口。

### Q14: 企业微信和个人微信如何切换？

**A**: 系统自动切换。配置回退机制：

```json
{
  "default_sender": "wechat",
  "sender_priority": ["wechat", "wxwork"],
  "fallback_enabled": true
}
```

当个人微信不可用时，自动切换到企业微信。

### Q15: 如何获取窗口句柄？

**A**: 使用窗口检查器：

```bash
python window_inspector.py findwechat
python window_inspector.py listall
```

---

## MCP服务

### Q16: 什么是MCP服务？

**A**: MCP（Model Context Protocol）是OpenClaw的插件协议，让AI助手能够直接调用微信机器人功能。

### Q17: 如何配置MCP服务？

**A**: 在OpenClaw配置中添加：

```json
{
  "mcpServers": {
    "wxbot": {
      "command": "python",
      "args": ["I:\\jz-wxbot-automation\\mcp_server.py"]
    }
  }
}
```

### Q18: MCP有哪些可用工具？

**A**: 

| 工具名 | 功能 |
|--------|------|
| wxbot_send_message | 发送消息 |
| wxbot_read_messages | 读取消息 |
| wxbot_send_moments | 发送朋友圈 |
| wxbot_mass_send | 群发消息 |
| wxbot_add_friend | 添加好友 |
| wxbot_group_manage | 群管理 |
| wxbot_get_contacts | 获取联系人 |
| wxbot_get_status | 查看状态 |

### Q19: MCP服务启动失败怎么办？

**A**: 检查以下几点：

1. 端口是否被占用
```bash
netstat -ano | findstr :8080
```

2. 配置文件是否正确
```bash
python -c "import yaml; yaml.safe_load(open('config/mcp.yaml'))"
```

3. 直接启动调试
```bash
python mcp_server.py --debug
```

---

## 自动化功能

### Q20: 如何设置定时发送？

**A**: 使用Python schedule库：

```python
import schedule
import time
from auto_daily_report_v2 import AutoReportSystemV2

system = AutoReportSystemV2()
system.initialize_senders()

# 每天9点发送
schedule.every().day.at("09:00").do(system.run_full_automation)

while True:
    schedule.run_pending()
    time.sleep(60)
```

或使用Windows任务计划程序。

### Q21: 如何实现批量群发？

**A**: 

```python
from wxwork_sender import WXWorkSenderRobust
import time
import random

sender = WXWorkSenderRobust()
groups = ["群1", "群2", "群3"]
message = "通知内容"

for group in groups:
    sender.send_message(message, group)
    # 随机延迟，避免风控
    time.sleep(random.uniform(3, 10))
```

### Q22: 支持哪些自动化场景？

**A**: 

| 场景 | 支持 |
|------|------|
| 定时发送消息 | ✅ |
| 批量群发 | ✅ |
| 自动回复 | ✅ |
| 发送朋友圈 | ✅ |
| 添加好友 | ✅ |
| 群管理 | ✅ |
| 会议提醒 | ✅ |
| 数据同步 | 🚧 开发中 |

### Q23: 如何实现自动回复？

**A**: 使用消息处理器：

```python
from core.message_handler import MessageHandler
from wechat_sender_v3 import WeChatSenderV3

handler = MessageHandler()
sender = WeChatSenderV3()

# 注册回调
handler.register_callback(lambda msg: 
    sender.send_message(f"收到：{msg.content}", msg.chat_name)
)

handler.start_listening()
```

---

## 安全与风控

### Q24: 会被微信封号吗？

**A**: 存在一定风险。降低风险的方法：

1. **保持人性化操作**
   - 开启随机延迟
   - 避免固定时间间隔
   - 控制发送频率

2. **适度使用**
   - 每小时发送 < 100条
   - 避免发送明显测试内容
   - 模拟真人作息时间

3. **避免敏感内容**
   - 不发送违规内容
   - 不频繁添加陌生人
   - 不进行恶意营销

### Q25: 什么是反风控功能？

**A**: 系统内置的反检测机制：

| 功能 | 说明 |
|------|------|
| 随机延迟 | 操作间隔随机化 |
| 模拟阅读 | 发送前模拟阅读停顿 |
| 鼠标轨迹 | 人性化鼠标移动 |
| 错误重试 | 失败后随机等待重试 |

### Q26: 如何配置人性化参数？

**A**: 

```python
from human_like_operations import HumanLikeOperations

ops = HumanLikeOperations()
ops.config = {
    "delay_base": 1.0,
    "delay_variance": 0.3,
    "move_duration": 0.5,
    "random_move_chance": 0.3
}
```

### Q27: 使用频率建议？

**A**: 

| 场景 | 建议频率 |
|------|---------|
| 单次群发 | 间隔 3-10 秒 |
| 批量操作 | 每批 ≤ 20 个 |
| 每小时总量 | ≤ 100 条 |
| 每日总量 | ≤ 500 条 |

---

## 故障排查

### Q28: 报错"找不到微信窗口"？

**A**: 

1. 确认微信已启动并登录
2. 检查进程名：
```bash
Get-Process | Where-Object {$_.Name -like "*WeChat*"}
```
3. 手动指定窗口标题
4. 以管理员身份运行

### Q29: 报错"剪贴板操作失败"？

**A**: 

1. 检查剪贴板：
```python
import pyperclip
pyperclip.copy("测试")
print(pyperclip.paste())
```

2. 清空剪贴板后重试
3. 关闭可能占用剪贴板的程序

### Q30: 消息发送乱码？

**A**: 

1. 确保文件编码为 UTF-8
2. 设置控制台编码：
```bash
chcp 65001
```

### Q31: 程序卡住无响应？

**A**: 

1. 检查是否有死循环
2. 添加超时设置：
```python
import pyautogui
pyautogui.TIMEOUT = 30
```

3. 使用安全机制（移动鼠标到角落中断）

### Q32: 日志在哪里查看？

**A**: 

| 日志 | 位置 |
|------|------|
| 应用日志 | logs/wxbot.log |
| MCP日志 | logs/mcp.log |
| 错误日志 | logs/error.log |

查看最近错误：
```bash
Get-Content logs\wxbot.log -Tail 100 | Select-String "ERROR"
```

---

## 📞 没有找到答案？

- 📖 查看完整文档：[USER_MANUAL.md](./USER_MANUAL.md)
- 🔧 故障排查：[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- 📧 联系支持：364345866@qq.com
- 💬 微信咨询：364345866

---

**最后更新**: 2026-03-24