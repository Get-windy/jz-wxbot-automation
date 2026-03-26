# jz-wxbot 负载均衡配置

## 部署
```bash
docker-compose -f deploy/docker-compose.lb.yml up -d
```

## 扩展
```bash
./scripts/scale.sh status
./scripts/scale.sh up
./scripts/scale.sh down
```

## 架构
- 3个wxbot实例（可扩展到8个）
- least_conn负载均衡
- ip_hash用于WebSocket会话保持
- Redis共享状态

## 端点
- `/health` - 健康检查
- `/metrics` - Prometheus指标
- `/ws` - WebSocket连接