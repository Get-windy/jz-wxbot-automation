# ==================== jz-wxbot 部署脚本 (PowerShell) ====================
# 用法: .\scripts\deploy.ps1 -Environment [环境] -Action [操作]
# 注意：微信GUI自动化需要Windows桌面环境
# ====================

param(
    [Parameter(Position=0)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "development",
    
    [Parameter(Position=1)]
    [ValidateSet("deploy", "start", "stop", "restart", "status", "scale", "logs", "backup", "clean", "build")]
    [string]$Action = "status",
    
    [Parameter(Position=2)]
    [int]$Replicas = 2
)

# ==================== 配置 ====================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $ProjectDir "docker-compose.yml"
$ComposeLbFile = Join-Path $ProjectDir "docker-compose.lb.yml"

$Config = @{
    MinWorkers = 2
    MaxWorkers = 8
    DefaultWorkers = 2
    HealthCheckTimeout = 120
    HealthCheckInterval = 5
}

# 颜色函数
function Write-ColorOutput {
    param([string]$Message, [string]$Type = "Info")
    
    $prefix = switch ($Type) {
        "Info"    { "[INFO] "; $color = "Green" }
        "Warn"    { "[WARN] "; $color = "Yellow" }
        "Error"   { "[ERROR] "; $color = "Red" }
        "Success" { "[OK] "; $color = "Green" }
        "Step"    { "[STEP] "; $color = "Cyan" }
        default   { ""; $color = "White" }
    }
    
    Write-Host $prefix -ForegroundColor $color -NoNewline
    Write-Host $Message
}

# ==================== 检查依赖 ====================

function Test-Dependencies {
    Write-ColorOutput "检查依赖..." "Step"
    
    $missing = @()
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $missing += "docker"
    }
    
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue) -and -not (docker compose version 2>$null)) {
        $missing += "docker-compose"
    }
    
    if ($missing.Count -gt 0) {
        Write-ColorOutput "缺少依赖: $($missing -join ', ')" "Error"
        exit 1
    }
    
    # 检查 Docker 是否运行
    try {
        docker info | Out-Null
    } catch {
        Write-ColorOutput "Docker 未运行，请启动 Docker Desktop" "Error"
        exit 1
    }
    
    Write-ColorOutput "依赖检查完成" "Success"
}

# ==================== 验证配置 ====================

function Test-Configuration {
    Write-ColorOutput "验证配置..." "Step"
    
    # 检查 .env 文件
    $envFile = Join-Path $ProjectDir ".env"
    if (-not (Test-Path $envFile)) {
        Write-ColorOutput ".env 文件未找到，创建默认配置..." "Warn"
        
        $envContent = @"
# jz-wxbot 环境配置
ROLE=coordinator
LOG_LEVEL=INFO

# OpenClaw 连接
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:3100

# Redis
REDIS_URL=redis://redis:6379

# 人性化操作
HUMAN_LIKE_ENABLED=true

# 监控
GRAFANA_PASSWORD=admin123
"@
        $envContent | Out-File -FilePath $envFile -Encoding UTF8
        Write-ColorOutput ".env 文件已创建" "Info"
    }
    
    # 创建必要目录
    $dirs = @("logs", "data", "plugins", "config/ssl", "config/nginx/conf.d", "config/monitoring")
    foreach ($dir in $dirs) {
        $fullPath = Join-Path $ProjectDir $dir
        if (-not (Test-Path $fullPath)) {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        }
    }
    
    # 检查 SSL 证书
    $sslCert = Join-Path $ProjectDir "config/ssl/cert.pem"
    if (-not (Test-Path $sslCert)) {
        Write-ColorOutput "SSL证书未找到，生成自签名证书..." "Warn"
        # 注意：Windows 需要 OpenSSL 或使用 PowerShell 生成
        Write-ColorOutput "请手动配置 SSL 证书" "Warn"
    }
    
    Write-ColorOutput "配置验证完成" "Success"
}

# ==================== 构建镜像 ====================

function Invoke-Build {
    Write-ColorOutput "构建 Docker 镜像..." "Step"
    
    Push-Location $ProjectDir
    
    try {
        docker compose -f $ComposeFile -f $ComposeLbFile build --no-cache
        Write-ColorOutput "镜像构建完成" "Success"
    } catch {
        Write-ColorOutput "镜像构建失败: $_" "Error"
        exit 1
    } finally {
        Pop-Location
    }
}

# ==================== 部署服务 ====================

function Invoke-Deploy {
    Write-ColorOutput "部署 $Environment 环境服务..." "Step"
    Write-ColorOutput "Worker 实例数: $Replicas" "Info"
    
    Push-Location $ProjectDir
    
    try {
        # 停止现有服务
        Write-ColorOutput "停止现有服务..." "Info"
        docker compose -f $ComposeFile -f $ComposeLbFile down 2>$null
        
        # 拉取基础镜像
        Write-ColorOutput "拉取基础镜像..." "Info"
        docker compose -f $ComposeFile -f $ComposeLbFile pull nginx-lb redis 2>$null
        
        # 启动服务
        Write-ColorOutput "启动服务..." "Info"
        docker compose -f $ComposeFile -f $ComposeLbFile up -d --scale wxbot-worker=$Replicas
        
        # 等待服务启动
        Write-ColorOutput "等待服务启动..." "Info"
        Start-Sleep -Seconds 15
        
        # 健康检查
        Test-Health
        
        Write-ColorOutput "部署完成" "Success"
    } catch {
        Write-ColorOutput "部署失败: $_" "Error"
        exit 1
    } finally {
        Pop-Location
    }
}

# ==================== 启动服务 ====================

function Start-Services {
    Write-ColorOutput "启动服务..." "Step"
    
    Push-Location $ProjectDir
    
    try {
        docker compose -f $ComposeFile -f $ComposeLbFile up -d --scale wxbot-worker=$Replicas
        Write-ColorOutput "服务已启动" "Success"
    } catch {
        Write-ColorOutput "启动失败: $_" "Error"
        exit 1
    } finally {
        Pop-Location
    }
}

# ==================== 停止服务 ====================

function Stop-Services {
    Write-ColorOutput "停止服务..." "Step"
    
    Push-Location $ProjectDir
    
    try {
        docker compose -f $ComposeFile -f $ComposeLbFile down
        Write-ColorOutput "服务已停止" "Success"
    } catch {
        Write-ColorOutput "停止失败: $_" "Error"
    } finally {
        Pop-Location
    }
}

# ==================== 重启服务 ====================

function Restart-Services {
    Write-ColorOutput "重启服务..." "Step"
    
    Stop-Services
    Start-Sleep -Seconds 3
    Start-Services
}

# ==================== 扩缩容 ====================

function Invoke-Scale {
    param([int]$TargetReplicas)
    
    if ($TargetReplicas -lt $Config.MinWorkers -or $TargetReplicas -gt $Config.MaxWorkers) {
        Write-ColorOutput "Worker 数量必须在 $($Config.MinWorkers) 到 $($Config.MaxWorkers) 之间" "Error"
        exit 1
    }
    
    Write-ColorOutput "扩缩容 Worker: $Replicas -> $TargetReplicas" "Step"
    
    Push-Location $ProjectDir
    
    try {
        docker compose -f $ComposeFile -f $ComposeLbFile up -d --scale wxbot-worker=$TargetReplicas --no-deps wxbot-worker
        Write-ColorOutput "扩缩容完成" "Success"
        
        Test-Health
    } catch {
        Write-ColorOutput "扩缩容失败: $_" "Error"
    } finally {
        Pop-Location
    }
}

# ==================== 健康检查 ====================

function Test-Health {
    Write-ColorOutput "检查服务健康状态..." "Step"
    
    $elapsed = 0
    
    while ($elapsed -lt $Config.HealthCheckTimeout) {
        try {
            # 检查 Coordinator
            $coordinatorHealth = Invoke-RestMethod -Uri "http://localhost:9000/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($coordinatorHealth) {
                Write-ColorOutput "Coordinator: 健康" "Success"
            }
        } catch {
            Write-Host "." -NoNewline
        }
        
        # 检查 Redis
        try {
            $redisPing = docker exec jzwxbot-redis redis-cli ping 2>$null
            if ($redisPing -match "PONG") {
                Write-ColorOutput "Redis: 健康" "Success"
            }
        } catch {}
        
        # 检查 Worker
        $workers = docker ps --filter "name=jzwxbot-wxbot-worker" --filter "status=running" --format "{{.Names}}" 2>$null
        $workerCount = if ($workers) { ($workers | Measure-Object).Count } else { 0 }
        Write-ColorOutput "活跃 Worker: $workerCount" "Info"
        
        if ($coordinatorHealth -and $workerCount -ge $Config.MinWorkers) {
            Write-ColorOutput "健康检查通过" "Success"
            return $true
        }
        
        Start-Sleep -Seconds $Config.HealthCheckInterval
        $elapsed += $Config.HealthCheckInterval
    }
    
    Write-ColorOutput "健康检查超时" "Warn"
    return $false
}

# ==================== 查看状态 ====================

function Show-Status {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  jz-wxbot 服务状态" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    Push-Location $ProjectDir
    
    try {
        docker compose -f $ComposeFile -f $ComposeLbFile ps
    } catch {
        Write-ColorOutput "无法获取服务状态" "Error"
    } finally {
        Pop-Location
    }
    
    Write-Host ""
    Write-Host "服务健康状态:" -ForegroundColor Cyan
    
    # Coordinator 状态
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:9000/health" -TimeoutSec 5
        Write-ColorOutput "Coordinator: 健康" "Success"
    } catch {
        Write-ColorOutput "Coordinator: 异常" "Error"
    }
    
    # Redis 状态
    try {
        $ping = docker exec jzwxbot-redis redis-cli ping 2>$null
        if ($ping -match "PONG") {
            Write-ColorOutput "Redis: 健康" "Success"
        } else {
            Write-ColorOutput "Redis: 异常" "Error"
        }
    } catch {
        Write-ColorOutput "Redis: 未运行" "Warn"
    }
    
    # Worker 状态
    Write-Host ""
    Write-Host "Worker 实例:" -ForegroundColor Cyan
    $workers = docker ps --filter "name=jzwxbot-wxbot-worker" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}" 2>$null
    if ($workers) {
        $workers
    } else {
        Write-ColorOutput "没有活跃的 Worker 实例" "Warn"
    }
    
    # 队列状态
    Write-Host ""
    Write-Host "任务队列:" -ForegroundColor Cyan
    try {
        $queueLen = docker exec jzwxbot-redis redis-cli LLEN wxbot:task_queue 2>$null
        Write-Host "待处理任务: $queueLen"
    } catch {
        Write-Host "待处理任务: N/A"
    }
    
    Write-Host ""
}

# ==================== 查看日志 ====================

function Show-Logs {
    param([string]$Service = "")
    
    Push-Location $ProjectDir
    
    try {
        if ($Service) {
            docker compose -f $ComposeFile -f $ComposeLbFile logs -f $Service
        } else {
            docker compose -f $ComposeFile -f $ComposeLbFile logs -f --tail=100
        }
    } catch {
        Write-ColorOutput "无法获取日志" "Error"
    } finally {
        Pop-Location
    }
}

# ==================== 备份 ====================

function Invoke-Backup {
    $BackupDir = "C:\Backups\jz-wxbot"
    $Date = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupFile = "$BackupDir\wxbot_$Date.zip"
    
    Write-ColorOutput "备份数据..." "Step"
    
    # 创建备份目录
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    
    # 备份数据目录
    $tempDir = "$BackupDir\temp_$Date"
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    
    # 复制数据
    if (Test-Path "$ProjectDir\data") {
        Copy-Item -Path "$ProjectDir\data" -Destination "$tempDir\data" -Recurse
    }
    
    # 复制配置
    if (Test-Path "$ProjectDir\config") {
        Copy-Item -Path "$ProjectDir\config" -Destination "$tempDir\config" -Recurse
    }
    
    # Redis 备份
    try {
        docker exec jzwxbot-redis redis-cli BGSAVE 2>$null
        Start-Sleep -Seconds 2
        docker cp jzwxbot-redis:/data/dump.rdb "$tempDir\redis_dump.rdb" 2>$null
    } catch {}
    
    # 压缩备份
    Compress-Archive -Path $tempDir -DestinationPath $BackupFile
    Remove-Item -Path $tempDir -Recurse -Force
    
    # 清理旧备份（保留7天）
    Get-ChildItem $BackupDir -Filter "*.zip" | 
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | 
        Remove-Item -Force
    
    Write-ColorOutput "备份完成: $BackupFile" "Success"
}

# ==================== 清理 ====================

function Invoke-Clean {
    Write-ColorOutput "清理资源..." "Step"
    
    Push-Location $ProjectDir
    
    try {
        docker compose -f $ComposeFile -f $ComposeLbFile down -v --rmi local
        docker system prune -f
        Write-ColorOutput "清理完成" "Success"
    } catch {
        Write-ColorOutput "清理失败: $_" "Error"
    } finally {
        Pop-Location
    }
}

# ==================== 主逻辑 ====================

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  jz-wxbot 部署工具 v1.0.0" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

switch ($Action) {
    "build" {
        Test-Dependencies
        Invoke-Build
    }
    "deploy" {
        Test-Dependencies
        Test-Configuration
        Invoke-Build
        Invoke-Deploy
    }
    "start" {
        Test-Dependencies
        Start-Services
    }
    "stop" {
        Stop-Services
    }
    "restart" {
        Restart-Services
    }
    "status" {
        Show-Status
    }
    "scale" {
        Invoke-Scale -TargetReplicas $Replicas
    }
    "logs" {
        Show-Logs
    }
    "backup" {
        Invoke-Backup
    }
    "clean" {
        Invoke-Clean
    }
}

Write-Host ""