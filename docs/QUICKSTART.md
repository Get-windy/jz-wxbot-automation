# jz-wxbot-automation 快速入门指南

**版本**: v2.1  
**最后更新**: 2026-03-18  
**适用对象**: 新用户、初次使用者

---

## 🚀 5 分钟快速开始

### 第一步：环境准备（2 分钟）

#### 1. 确认系统要求

- ✅ Windows 10/11
- ✅ Python 3.7 或更高版本
- ✅ 个人微信 PC 版 **或** 企业微信 PC 版（至少安装一个）

#### 2. 安装依赖

打开 PowerShell 或命令提示符，执行：

```bash
cd I:\jz-wxbot-automation
pip install -r requirements.txt
```

依赖包括：
- `pyautogui` - GUI 自动化
- `pywin32` - Windows API 访问
- `psutil` - 进程管理
- `pyperclip` - 剪贴板操作

---

### 第二步：测试运行（1 分钟）

#### 快速测试发送器

```bash
# 测试个人微信发送器
python wechat_sender_v3.py test

# 测试企业微信发送器
python wxwork_sender.py test

# 查看双微信系统状态
python auto_daily_report_v2.py status
```

**预期输出**：
```
✅ 个人微信发送器初始化成功
✅ 企业微信发送器初始化成功
发送器状态：可用
```

---

### 第三步：发送第一条消息（2 分钟）

#### 方法 1：命令行发送（最简单）

```bash
# 发送消息到指定群聊
python wechat_sender_v3.py send "技术交流群"

# 发送自定义消息
python wxwork_sender.py send "项目组" "下午 3 点开会，请准时参加"
```

#### 方法 2：Python 脚本

创建 `test_send.py`：

```python
from wechat_sender_v3 import WeChatSenderV3

# 创建发送器
sender = WeChatSenderV3()

# 初始化
if sender.initialize():
    print("✅ 初始化成功")
    
    # 发送消息
    success = sender.send_message("大家好，这是测试消息！", "技术交流群")
    
    if success:
        print("✅ 消息发送成功")
    else:
        print("❌ 消息发送失败")
else:
    print("❌ 初始化失败，请检查微信是否运行")
```

运行：
```bash
python test_send.py
```

---

## 📋 常用场景速查

### 场景 1：定时发送日报

使用批处理文件（推荐）：

```bash
# 运行自动化日报系统
run_daily_auto.bat
```

或创建定时任务：

```python
import schedule
import time
from auto_daily_report_v2 import AutoReportSystemV2

system = AutoReportSystemV2()
system.initialize_senders()

# 每天早上 9 点发送
schedule.every().day.at("09:00").do(system.run_full_automation)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### 场景 2：批量发送通知

```python
from wxwork_sender import WXWorkSenderRobust

sender = WXWorkSenderRobust()
sender.find_wxwork_window()

# 群发通知
groups = ["技术交流群", "产品讨论群", "项目组"]
message = "本周五下午 3 点开例会，请大家准时参加"

for group in groups:
    sender.send_message(message, group)
    time.sleep(5)  # 避免发送过快
```

---

### 场景 3：通过 OpenClaw AI 助手发送

如果你使用 OpenClaw，可以直接对话：

> "帮我给技术交流群发一条消息：明天上午 10 点开会"

OpenClaw 会自动调用 MCP 工具 `wxbot_send_message` 执行发送。

---

## ⚙️ 基础配置

### 配置文件位置

`auto_report_config.json` - 主配置文件

### 配置示例

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
      "default_group": "技术交流群"
    },
    "wxwork": {
      "type": "wxwork",
      "enabled": true,
      "default_group": "项目组"
    }
  }
}
```

**关键配置说明**：
- `default_sender`: 默认使用的微信类型（`wechat` 或 `wxwork`）
- `sender_priority`: 发送器优先级顺序
- `fallback_enabled`: 启用自动回退（个人微信不可用时切换企业微信）

---

## 🛠️ 故障排查

### 问题 1：找不到微信进程

**症状**：
```
❌ 个人微信发送器初始化失败
⚠️ 未找到微信进程
```

**解决方案**：
1. 确保微信已启动并登录
2. 检查进程名称：
   - 个人微信：`WeChat.exe` 或 `Weixin.exe`
   - 企业微信：`WXWork.exe`
3. 尝试以管理员权限运行脚本

---

### 问题 2：消息发送失败

**症状**：
```
发送失败：无法激活窗口
```

**解决方案**：
1. 确保目标群聊窗口已打开
2. 使用窗口检查器获取正确句柄：
   ```bash
   python window_inspector.py click
   ```
3. 检查微信是否最小化，尝试恢复窗口

---

### 问题 3：编码错误

**症状**：
```
UnicodeEncodeError: 'gbk' codec can't encode character
```

**解决方案**：
1. 确保 Python 文件使用 UTF-8 编码保存
2. Windows 控制台设置：
   ```bash
   chcp 65001
   ```

---

## 📚 下一步学习

完成快速入门后，建议阅读：

1. **[API_USAGE_GUIDE.md](./API_USAGE_GUIDE.md)** - 完整的 API 接口文档
2. **[DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)** - 开发者指南
3. **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - 部署指南
4. **[README.md](../README.md)** - 项目总览

---

## 💡 最佳实践

### ✅ 推荐做法

1. **使用双微信回退机制** - 确保至少有一种微信可用
2. **保持人性化操作开启** - 避免风控检测
3. **适度使用频率** - 建议每条消息间隔 3-10 秒
4. **定期更新配置** - 及时更新群聊列表和窗口句柄

### ❌ 避免做法

1. **高频发送** - 避免短时间内发送大量消息
2. **固定时间间隔** - 使用随机延迟模拟真人操作
3. **发送测试内容** - 避免明显的自动化特征
4. **忽略错误日志** - 及时查看和处理异常

---

## 🆘 获取帮助

遇到问题？

- 📖 查看完整文档：`docs/` 目录
- 🐛 提交 Issue：GitHub 项目页面
- 📧 联系开发者：364345866@qq.com
- 💬 微信咨询：364345866

---

**祝你使用愉快！** 🎉

如果这个工具对你有帮助，请给项目一个 Star 支持！⭐
