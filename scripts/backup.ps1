# ==================== jz-wxbot 备份脚本 ====================
# 用法: .\scripts\backup.ps1 -BackupDir "C:\Backups" -KeepDays 7
# ====================

param(
    [string]$BackupDir = "C:\Backups\jz-wxbot",
    [int]$KeepDays = 7,
    [ValidateSet("full", "data", "config")]
    [string]$Type = "full"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$Date = Get-Date -Format "yyyyMMdd_HHmmss"

# 颜色输出
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "INFO" { "Green" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] " -ForegroundColor $color -NoNewline
    Write-Host $Message
}

# 创建备份目录
function Initialize-BackupDir {
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        Write-Log "创建备份目录: $BackupDir"
    }
    
    $tempDir = Join-Path $BackupDir "temp_$Date"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    return $tempDir
}

# 备份数据
function Backup-Data {
    param([string]$TempDir)
    
    Write-Log "备份数据文件..."
    
    $dataDir = Join-Path $ProjectDir "data"
    if (Test-Path $dataDir) {
        $destDir = Join-Path $TempDir "data"
        Copy-Item -Path $dataDir -Destination $destDir -Recurse
        Write-Log "数据文件备份完成"
    } else {
        Write-Log "数据目录不存在，跳过" "WARN"
    }
    
    # 备份数据库
    $dbFiles = Get-ChildItem -Path $ProjectDir -Filter "*.db" -Recurse
    if ($dbFiles) {
        $dbDir = Join-Path $TempDir "databases"
        New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
        foreach ($db in $dbFiles) {
            Copy-Item -Path $db.FullName -Destination $dbDir
        }
        Write-Log "数据库文件备份完成: $($dbFiles.Count) 个文件"
    }
}

# 备份配置
function Backup-Config {
    param([string]$TempDir)
    
    Write-Log "备份配置文件..."
    
    $configDir = Join-Path $ProjectDir "config"
    if (Test-Path $configDir) {
        $destDir = Join-Path $TempDir "config"
        Copy-Item -Path $configDir -Destination $destDir -Recurse
        Write-Log "配置文件备份完成"
    }
    
    # 备份 .env 文件
    $envFile = Join-Path $ProjectDir ".env"
    if (Test-Path $envFile) {
        Copy-Item -Path $envFile -Destination $TempDir
        Write-Log ".env 文件备份完成"
    }
}

# 备份 Redis
function Backup-Redis {
    param([string]$TempDir)
    
    Write-Log "备份 Redis 数据..."
    
    try {
        # 触发 Redis BGSAVE
        docker exec jzwxbot-redis redis-cli BGSAVE 2>$null
        Start-Sleep -Seconds 3
        
        # 复制 RDB 文件
        docker cp jzwxbot-redis:/data/dump.rdb (Join-Path $TempDir "redis_dump.rdb") 2>$null
        Write-Log "Redis 数据备份完成"
    } catch {
        Write-Log "Redis 备份失败: $_" "WARN"
    }
}

# 备份日志
function Backup-Logs {
    param([string]$TempDir)
    
    Write-Log "备份日志文件..."
    
    $logsDir = Join-Path $ProjectDir "logs"
    if (Test-Path $logsDir) {
        $destDir = Join-Path $TempDir "logs"
        Copy-Item -Path $logsDir -Destination $destDir -Recurse
        Write-Log "日志文件备份完成"
    }
}

# 创建压缩包
function Compress-Backup {
    param([string]$TempDir)
    
    $backupFile = Join-Path $BackupDir "wxbot_$Date.zip"
    
    Write-Log "创建压缩包..."
    Compress-Archive -Path "$TempDir\*" -DestinationPath $backupFile -CompressionLevel Optimal
    
    # 清理临时目录
    Remove-Item -Path $TempDir -Recurse -Force
    
    $fileSize = (Get-Item $backupFile).Length / 1MB
    Write-Log "备份文件: $backupFile ($([math]::Round($fileSize, 2)) MB)"
    
    return $backupFile
}

# 清理旧备份
function Remove-OldBackups {
    Write-Log "清理旧备份文件 (保留 $KeepDays 天)..."
    
    $oldBackups = Get-ChildItem -Path $BackupDir -Filter "wxbot_*.zip" | 
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) }
    
    if ($oldBackups) {
        foreach ($backup in $oldBackups) {
            Remove-Item -Path $backup.FullName -Force
            Write-Log "删除旧备份: $($backup.Name)"
        }
    } else {
        Write-Log "没有需要清理的旧备份"
    }
}

# 验证备份
function Test-Backup {
    param([string]$BackupFile)
    
    Write-Log "验证备份完整性..."
    
    try {
        # 检查压缩包是否有效
        $archive = [System.IO.Compression.ZipFile]::OpenRead($BackupFile)
        $fileCount = $archive.Entries.Count
        $archive.Dispose()
        
        Write-Log "备份验证通过: $fileCount 个文件"
        return $true
    } catch {
        Write-Log "备份验证失败: $_" "ERROR"
        return $false
    }
}

# 主函数
function Main {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  jz-wxbot 备份工具" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $startTime = Get-Date
    
    try {
        # 创建目录
        $tempDir = Initialize-BackupDir
        
        # 执行备份
        switch ($Type) {
            "full" {
                Backup-Data -TempDir $tempDir
                Backup-Config -TempDir $tempDir
                Backup-Redis -TempDir $tempDir
                Backup-Logs -TempDir $tempDir
            }
            "data" {
                Backup-Data -TempDir $tempDir
                Backup-Redis -TempDir $tempDir
            }
            "config" {
                Backup-Config -TempDir $tempDir
            }
        }
        
        # 压缩
        $backupFile = Compress-Backup -TempDir $tempDir
        
        # 验证
        Test-Backup -BackupFile $backupFile
        
        # 清理旧备份
        Remove-OldBackups
        
        $duration = (Get-Date) - $startTime
        Write-Log "备份完成，耗时: $($duration.TotalSeconds.ToString('F2')) 秒"
        
    } catch {
        Write-Log "备份失败: $_" "ERROR"
        exit 1
    }
    
    Write-Host ""
}

# 执行
Main