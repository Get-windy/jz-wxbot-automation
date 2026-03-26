# jz-wxbot

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/jz-wxbot/jz-wxbot/releases)

jz-wxbot是一个微信机器人框架，支持微信PC端自动化操作。

## ✨ 特性

- **微信自动化** - 发送消息、接收消息
- **群操作** - 群消息、群管理
- **扩展系统** - 插件机制
- **OpenClaw集成** - AI助手集成
- **消息记录** - 完整日志记录

## 📋 技术栈

| 层级 | 技术 |
|------|------|
| 核心 | Rust + WeChat API |
| 前端 | Flutter |
| 存储 | SQLite + SQLCipher |
| AI | OpenClaw Agent |

## 🚀 快速开始

### 安装

```bash
# 下载二进制
wget https://github.com/jz-wxbot/jz-wxbot/releases/latest/download/jz-wxbot.exe

# 运行
./jz-wxbot.exe
```

### 配置

```bash
# 初始化配置
jz-wxbot init

# 配置插件目录
jz-wxbot config set plugin.dir ./plugins
```

## 📦 项目结构

```
jz-wxbot/
├── src/
│   ├── backend/       # WeChat核心
│   ├── client/        # Flutter管理界面
│   └── plugins/       # 插件目录
├── docs/              # 文档
└── tests/             # 测试
```

## 🔧 开发

```bash
# 构建后端
cd src/backend
cargo build

# 构建前端
cd ../client
flutter pub get
flutter run
```

## 📚 文档

- [API使用指南](docs/API_USAGE_GUIDE.md)
- [部署指南](docs/DEPLOYMENT_GUIDE.md)
- [OpenClaw集成](docs/OPENCLAW_INTEGRATION.md)

## 🤝 贡献

欢迎提交Issue和PR！

1. Fork项目
2. 创建分支
3. 提交代码
4. 发起PR

## 📄 许可证

MIT License

---

## 📈 开发进度 (2026-03-26)

### 代码变更统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 新增文件 | 25+ | 监控、错误处理、日志系统 |
| 修改文件 | 20+ | 核心模块优化 |
| 新增代码行 | ~10,000 | Python |

### 任务完成进度

- ✅ 微信消息收发
- ✅ 群组管理
- ✅ OpenClaw集成
- ✅ 增强错误处理系统
- ✅ 增强日志系统
- ✅ 稳定性监控服务
- ✅ MCP Server
- 🔄 自动恢复机制 (测试中)
- ⏳ 多账号支持 (规划中)

### 代码审查结果 (2026-03-26)

| 维度 | 评分 | 说明 |
|------|------|------|
| 安全 | 7.0/10 | 需加强认证和日志脱敏 |
| 性能 | 8.0/10 | 监控完善 |
| 代码质量 | 8.5/10 | 架构清晰，测试覆盖好 |

### 发现问题

| 优先级 | 问题 | 状态 |
|--------|------|------|
| P0 | 日志可能泄露敏感信息 | **紧急修复** |
| P1 | MCP接口无认证 | 待添加Token验证 |
| P1 | 配置文件明文 | 待加密敏感配置 |

### 下一步计划

1. **紧急修复**: 日志敏感信息过滤
2. MCP接口认证
3. 自动恢复测试
4. 文档完善