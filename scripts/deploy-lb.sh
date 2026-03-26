#!/bin/bash
# ============================================
# jz-wxbot 部署脚本（负载均衡版本）
# 用法: ./scripts/deploy-lb.sh [环境] [选项]
# 注意：微信GUI自动化需要Windows桌面环境
# ============================================

set -e

# ==================== 配置 ====================
ENVIRONMENT="${1:-development}"
OPTIONS="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
COMPOSE_LB_FILE="$PROJECT_DIR/docker-compose.lb.yml"

# 负载均衡配置
DEFAULT_WORKERS=2
MAX_WORKERS=10
WORKERS="${WORKERS:-$DEFAULT_WORKERS}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
log_lb() { echo -e "${CYAN}[LB]${NC} $1"; }

# ==================== 环境配置 ====================
declare -A ENV_CONFIG=(
    ["development"]="dev"
    ["staging"]="staging"
    ["production"]="production"
)

PROFILE="${ENV_CONFIG[$ENVIRONMENT]:-dev}"

# ==================== 检查依赖 ====================
check_dependencies() {
    log_step "检查依赖..."
    
    local missing=()
    
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing+=("docker-compose")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "缺少依赖: ${missing[*]}"
        exit 1
    fi
    
    log_info "依赖检查完成 ✅"
}

# ==================== 验证配置 ====================
validate_config() {
    log_step "验证配置..."
    
    # 检查SSL证书
    if [ ! -f "$PROJECT_DIR/config/ssl/cert.pem" ]; then
        log_warn "SSL证书未找到，生成自签名证书..."
        mkdir -p "$PROJECT_DIR/config/ssl"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$PROJECT_DIR/config/ssl/key.pem" \
            -out "$PROJECT_DIR/config/ssl/cert.pem" \
            -subj "/CN=localhost/O=jz-wxbot/C=US"
        log_info "自签名证书已生成 ⚠️ (仅用于开发/测试)"
    fi
    
    # 检查环境变量
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_warn ".env 文件未找到，创建默认配置..."
        cat > "$PROJECT_DIR/.env" << EOF
# jz-wxbot 环境配置
ROLE=coordinator
LOG_LEVEL=INFO

# OpenClaw 连接
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:3100

# Redis
REDIS_URL=redis://redis:6379

# 人性化操作
HUMAN_LIKE_ENABLED=true
EOF
        log_info ".env 文件已创建"
    fi
    
    log_info "配置验证完成 ✅"
}

# ==================== 构建镜像 ====================
build_image() {
    log_step "构建Docker镜像..."
    
    cd "$PROJECT_DIR"
    
    docker compose -f "$COMPOSE_LB_FILE" build coordinator
    docker compose -f "$COMPOSE_LB_FILE" build wxbot-worker
    
    log_info "镜像构建完成 ✅"
}

# ==================== 部署负载均衡 ====================
deploy_load_balanced() {
    log_step "部署负载均衡服务到 $ENVIRONMENT 环境..."
    log_lb "Worker数量: $WORKERS"
    
    cd "$PROJECT_DIR"
    
    # 停止现有服务
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" --profile "$PROFILE" down
    
    # 拉取基础镜像
    log_info "拉取基础镜像..."
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" pull nginx-lb redis 2>/dev/null || true
    
    # 启动服务
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" \
        --profile "$PROFILE" \
        up -d \
        --scale wxbot-worker="$WORKERS"
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 15
    
    # 健康检查
    check_lb_health
    
    log_info "负载均衡部署完成 ✅"
}

# ==================== 扩缩容 ====================
scale_workers() {
    local target_workers="$1"
    
    if [ -z "$target_workers" ]; then
        log_error "请指定目标Worker数量"
        echo "用法: $0 scale <数量>"
        exit 1
    fi
    
    if [ "$target_workers" -gt "$MAX_WORKERS" ]; then
        log_error "Worker数量不能超过 $MAX_WORKERS"
        exit 1
    fi
    
    log_step "扩缩容Worker: $WORKERS -> $target_workers"
    
    cd "$PROJECT_DIR"
    
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" \
        --profile "$PROFILE" \
        up -d \
        --scale wxbot-worker="$target_workers" \
        --no-deps \
        wxbot-worker
    
    WORKERS="$target_workers"
    
    check_lb_health
    
    log_info "扩缩容完成 ✅"
}

# ==================== 健康检查 ====================
check_lb_health() {
    log_lb "检查负载均衡健康状态..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # 检查NGINX
        if curl -sf "http://localhost/health" > /dev/null 2>&1; then
            log_lb "NGINX负载均衡器: 健康 ✅"
            
            # 检查协调器
            if curl -sf "http://localhost:9000/health" > /dev/null 2>&1; then
                log_lb "协调器服务: 健康 ✅"
            fi
            
            # 检查Worker
            local healthy_workers=0
            for container in $(docker ps --filter "name=jzwxbot-wxbot-worker" --format "{{.Names}}"); do
                ((healthy_workers++))
            done
            
            log_lb "活跃Worker实例: $healthy_workers"
            
            log_lb "负载均衡健康检查通过 ✅"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo ""
    log_warn "负载均衡健康检查超时，请检查日志"
    return 1
}

# ==================== 查看日志 ====================
show_logs() {
    local service="${1:-}"
    
    cd "$PROJECT_DIR"
    
    if [ -n "$service" ]; then
        docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" logs -f "$service"
    else
        docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" logs -f
    fi
}

# ==================== 停止服务 ====================
stop_service() {
    log_step "停止负载均衡服务..."
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" --profile "$PROFILE" down
    log_info "服务已停止 ✅"
}

# ==================== 清理资源 ====================
cleanup() {
    log_step "清理资源..."
    cd "$PROJECT_DIR"
    
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" down -v --rmi local
    docker system prune -f
    
    log_info "清理完成 ✅"
}

# ==================== 显示状态 ====================
show_status() {
    echo ""
    echo "========================================"
    echo "  jz-wxbot 负载均衡服务状态"
    echo "========================================"
    echo ""
    
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" ps
    
    echo ""
    echo "服务状态:"
    
    # NGINX状态
    if curl -sf "http://localhost/health" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ NGINX负载均衡器正常${NC}"
    else
        echo -e "  ${RED}❌ NGINX负载均衡器异常${NC}"
    fi
    
    # 协调器状态
    if docker ps --filter "name=jzwxbot-coordinator" --format "{{.Names}}" | grep -q "coordinator"; then
        echo -e "  ${GREEN}✅ 协调器服务运行中${NC}"
    else
        echo -e "  ${RED}❌ 协调器服务未运行${NC}"
    fi
    
    # Worker状态
    echo ""
    echo "Worker实例状态:"
    local worker_count=0
    for container in $(docker ps --filter "name=jzwxbot-wxbot-worker" --format "{{.Names}}"); do
        echo -e "  ${GREEN}✅ $container${NC}"
        ((worker_count++))
    done
    
    if [ "$worker_count" -eq 0 ]; then
        echo -e "  ${YELLOW}⚠️ 没有活跃的Worker实例${NC}"
    fi
    
    echo ""
    echo "Worker统计: $worker_count 个实例"
    echo ""
    
    # Redis状态
    if docker exec jzwxbot-redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo -e "  ${GREEN}✅ Redis服务正常${NC}"
    else
        echo -e "  ${RED}❌ Redis服务异常${NC}"
    fi
    
    echo ""
    
    # 队列状态
    echo "任务队列状态:"
    local queue_len=$(docker exec jzwxbot-redis redis-cli LLEN wxbot:task_queue 2>/dev/null || echo "0")
    echo "  待处理任务: $queue_len"
    echo ""
}

# ==================== 显示帮助 ====================
show_help() {
    cat << EOF
jz-wxbot 负载均衡部署脚本

用法: $0 [环境] [选项]

环境:
  development    开发环境（默认）
  staging        测试环境
  production     生产环境

选项:
  --build        仅构建镜像
  --deploy       构建并部署负载均衡
  --scale N      扩缩容Worker到N个
  --logs [服务]  查看日志
  --stop         停止服务
  --status       查看状态
  --clean        清理资源
  --monitoring   启动监控服务
  --help         显示帮助

环境变量:
  WORKERS              Worker实例数量（默认: 2）
  OPENCLAW_GATEWAY_URL OpenClaw网关地址

示例:
  $0 development                    # 开发环境部署
  $0 production --deploy            # 生产环境部署
  $0 --scale 4                      # 扩容到4个Worker
  $0 --logs coordinator             # 查看协调器日志
  $0 --status                       # 查看状态
  $0 --monitoring                   # 启动监控

负载均衡架构:
  ┌─────────────┐
  │   Client    │
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │    NGINX    │  负载均衡器
  │  (LB + SSL) │
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │ Coordinator │  任务协调器
  │  Port: 9000 │
  └──────┬──────┘
         │
    ┌────┴────┬────────┐
    │         │        │
  ┌─▼──┐   ┌─▼──┐   ┌─▼──┐
  │ W1 │   │ W2 │   │ WN │  Worker实例
  └────┘   └────┘   └────┘  (GUI自动化)
         │
  ┌──────▼──────┐
  │    Redis    │  任务队列
  └─────────────┘

注意:
  - 每个Worker需要独立的微信桌面实例
  - GUI自动化在Windows环境运行最佳
  - 生产环境建议使用多机部署

EOF
}

# ==================== 主流程 ====================
main() {
    case "$OPTIONS" in
        --build)
            check_dependencies
            build_image
            ;;
        --deploy)
            check_dependencies
            validate_config
            build_image
            deploy_load_balanced
            ;;
        --scale*)
            local target="${OPTIONS#--scale }"
            scale_workers "$target"
            ;;
        --logs*)
            local service="${OPTIONS#--logs }"
            show_logs "$service"
            ;;
        --stop)
            stop_service
            ;;
        --status)
            show_status
            ;;
        --clean)
            cleanup
            ;;
        --monitoring)
            cd "$PROJECT_DIR"
            docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_LB_FILE" --profile monitoring up -d
            log_info "监控服务已启动"
            ;;
        --help|-h)
            show_help
            ;;
        *)
            check_dependencies
            validate_config
            build_image
            deploy_load_balanced
            ;;
    esac
}

main