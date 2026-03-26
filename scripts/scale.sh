#!/bin/bash
# jz-wxbot 自动扩展脚本

COMPOSE_FILE="deploy/docker-compose.lb.yml"
MIN_INSTANCES=2
MAX_INSTANCES=8

get_instances() {
    docker ps --filter "name=jz-wxbot-" --filter "status=running" -q | wc -l
}

scale_up() {
    local current=$(get_instances)
    local new=$((current + 1))
    [ $new -gt $MAX_INSTANCES ] && { echo "[WARN] Max: $MAX_INSTANCES"; return 1; }
    echo "[INFO] Scale up: $current -> $new"
    docker-compose -f $COMPOSE_FILE up -d --scale wxbot=$new
}

scale_down() {
    local current=$(get_instances)
    local new=$((current - 1))
    [ $new -lt $MIN_INSTANCES ] && { echo "[WARN] Min: $MIN_INSTANCES"; return 1; }
    echo "[INFO] Scale down: $current -> $new"
    docker-compose -f $COMPOSE_FILE up -d --scale wxbot=$new
}

show_status() {
    echo "=== jz-wxbot 集群状态 ==="
    echo "实例: $(get_instances) / $MAX_INSTANCES"
    docker ps --filter "name=jz-wxbot-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

case "$1" in
    up) scale_up ;;
    down) scale_down ;;
    status) show_status ;;
    *) echo "Usage: $0 {up|down|status}" ;;
esac