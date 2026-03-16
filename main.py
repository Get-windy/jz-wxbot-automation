# -*- coding: utf-8 -*-
"""
jz-wxbot 主程序入口
版本: v2.1.0
功能: 微信自动化核心功能 - 消息发送、接收、群管理
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bridge.bridge_service import BridgeService
from bridge.openclaw_client import get_openclaw_client

# 配置日志
def setup_logging():
    """配置日志系统"""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "wxbot.log", encoding='utf-8')
        ]
    )


async def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("jz-wxbot 微信自动化系统启动")
    logger.info("=" * 60)
    
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
        bridge = BridgeService(config)
        
        # 启动服务
        success = await bridge.start()
        
        if success:
            logger.info("✅ 桥接服务启动成功")
            logger.info("按 Ctrl+C 停止服务")
            
            # 保持运行
            while True:
                await asyncio.sleep(1)
        else:
            logger.error("❌ 桥接服务启动失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n收到停止信号，正在关闭...")
        await bridge.stop()
        logger.info("✅ 服务已停止")
        return 0
        
    except Exception as e:
        logger.error(f"运行时错误: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
