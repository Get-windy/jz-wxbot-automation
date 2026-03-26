# -*- coding: utf-8 -*-
"""
jz-wxbot 主程序入口
版本: v2.2.0
功能: 微信自动化核心功能 - 消息发送、接收、群管理
更新: 集成增强日志系统和错误处理
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bridge.bridge_service import BridgeService
from bridge.openclaw_client import get_openclaw_client

# 导入增强日志和错误处理
from core.enhanced_logging import (
    init_logging, 
    get_logger, 
    LogConfig,
    log_performance,
    async_log_performance,
)
from core.enhanced_error_handling import (
    init_error_handler,
    get_error_handler,
    ErrorSeverity,
    RecoveryStrategy,
    async_retry_on_error,
)


def setup_system():
    """初始化系统"""
    # 配置日志
    log_config = LogConfig(
        log_dir=str(project_root / "logs"),
        console_level=20,  # INFO
        file_level=10,     # DEBUG
        json_format=True,
        error_tracking_enabled=True,
    )
    logger = init_logging(log_config)
    
    # 初始化错误处理
    from core.enhanced_error_handling import ErrorHandlerConfig
    error_config = ErrorHandlerConfig(
        max_retries=3,
        retry_delay=1.0,
        auto_recovery=True,
    )
    error_handler = init_error_handler(error_config)
    
    return logger, error_handler


@async_retry_on_error(max_retries=3, delay=2.0, exceptions=(Exception,))
async def start_bridge(bridge: BridgeService) -> bool:
    """启动桥接服务（带重试）"""
    return await bridge.start()


async def main():
    """主函数"""
    logger, error_handler = setup_system()
    
    logger.info("=" * 60)
    logger.info("jz-wxbot 微信自动化系统启动 v2.2.0")
    logger.info("=" * 60)
    
    bridge = None
    
    try:
        # 加载配置
        config = {
            'openclaw': {
                'gateway_url': 'ws://127.0.0.1:3100',
                'agent_id': 'wxbot-agent',
                'reconnect': True,
                'heartbeat_interval': 30
            },
            'wechat': {
                'personal': {
                    'enabled': True,
                    'process_names': ['WeChat.exe', 'Weixin.exe']
                },
                'work': {
                    'enabled': True,
                    'process_names': ['WXWork.exe']
                }
            },
            'human_like': {
                'enabled': True,
                'random_delay': True,
                'curve_movement': True
            }
        }
        
        # 初始化桥接服务
        logger.operation("初始化", "BridgeService", True)
        bridge = BridgeService(config)
        
        # 启动服务（带重试）
        logger.info("正在启动桥接服务...")
        success = await start_bridge(bridge)
        
        if success:
            logger.operation("启动", "BridgeService", True)
            logger.info("按 Ctrl+C 停止服务")
            
            # 输出运行状态
            logger.info(f"错误统计: {error_handler.get_error_stats()}")
            
            # 保持运行
            while True:
                await asyncio.sleep(1)
        else:
            logger.operation("启动", "BridgeService", False)
            logger.error("桥接服务启动失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n收到停止信号，正在关闭...")
        if bridge:
            await bridge.stop()
        logger.operation("停止", "BridgeService", True)
        
        # 输出最终统计
        logger.info(f"最终错误统计: {error_handler.get_error_stats()}")
        logger.info(f"性能统计: {logger.get_performance_stats()}")
        
        return 0
        
    except Exception as e:
        logger.critical(f"运行时错误: {e}", exc_info=True)
        
        # 错误处理
        from core.enhanced_error_handling import ErrorContext
        context = ErrorContext(
            operation="main",
            component="main",
            severity=ErrorSeverity.CRITICAL,
            recovery=RecoveryStrategy.SHUTDOWN,
        )
        error_handler.handle(e, context)
        
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
