# MEMORY.md - jz-wxbot 项目记忆

## 2026-03-23 负载均衡部署配置

### 完成的工作

#### 1. Docker 镜像配置
- **Dockerfile** - Python 3.11 Windows 基础镜像
  - GUI 自动化环境
  - 健康检查支持

#### 2. 负载均衡部署配置
- **docker-compose.lb.yml** - 负载均衡 Docker Compose 配置
  - NGINX 负载均衡器（SSL 终止）
  - Coordinator 任务协调器
  - 可扩展 Worker 实例
  - Redis 任务队列
  - Prometheus + Grafana 监控（可选）

#### 3. NGINX 配置
- **config/nginx/nginx.conf** - NGINX 主配置
  - 上游服务器定义
  - 速率限制
  - 安全头配置

- **config/nginx/conf.d/jzwxbot.conf** - 站点配置
  - SSL 终止
  - API 路由规则
  - WebSocket 支持

#### 4. 任务协调器
- **core/coordinator.py** - 任务协调器模块
  - Worker 注册和心跳管理
  - 任务队列管理
  - 任务分发逻辑
  - HTTP API 接口

#### 5. 部署脚本
- **scripts/deploy-lb.sh** - 负载均衡部署脚本
  - 支持多 Worker 部署
  - 动态扩缩容
  - 健康检查
  - 状态监控

#### 6. 监控配置
- **config/monitoring/prometheus.yml** - Prometheus 配置
  - 协调器监控
  - Worker 监控
  - Redis 监控

#### 7. 文档
- **docs/load-balancing.md** - 负载均衡部署指南
  - 架构图
  - API 接口说明
  - 故障排查
  - 生产环境建议

### 使用方法

```bash
# 基础部署（2个Worker）
./scripts/deploy-lb.sh development

# 生产部署（4个Worker）
WORKERS=4 ./scripts/deploy-lb.sh production --deploy

# 扩缩容
./scripts/deploy-lb.sh --scale 4

# 启动监控
./scripts/deploy-lb.sh --monitoring

# 查看状态
./scripts/deploy-lb.sh --status
```

### 负载均衡架构

```
Client → NGINX (LB) → Coordinator → [Worker 1..N] → 微信GUI
                                    ↓
                                  Redis (队列)
```

### 特殊说明

- 微信 GUI 自动化需要 Windows 桌面环境
- 每个 Worker 需要独立的微信实例
- 生产环境建议多机部署

### 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Python + asyncio |
| GUI 自动化 | pyautogui + pywin32 |
| 任务队列 | Redis |
| 负载均衡 | NGINX |
| 容器化 | Docker + Docker Compose |

---
*创建时间: 2026-03-23 13:30*