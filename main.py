# -*- coding: utf-8 -*-
"""
jz-wxbot-automation 主程序入口
版本: v2.0.0
功能: OpenClaw 微信自动化桥接服务
"""

import os
import sys
import json
import yaml
import argparse
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from bridge import BridgeService, get_bridge_service

# 配置日志
def setup_logging(config: dict):
    """配置日志"""
    log_config = config.get('logging', {})
    
    level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/wxbot.log')
    
    # 确保日志目录存在
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # 配置日志格式
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )


def load_config(config_path: str = None) -> dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 配置字典
    """
    if config_path is None:
        config_path = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')
    
    if not os.path.exists(config_path):
        logging.warning(f"配置文件不存在: {config_path}，使用默认配置")
        return get_default_config()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config or get_default_config()


def get_default_config() -> dict:
    """获取默认配置"""
    return {
        'version': '2.0',
        'wechat': {
            'personal': {
                'enabled': True,
                'process_names': ['WeChat.exe', 'Weixin.exe'],
                'auto_reconnect': True
            },
            'work': {
                'enabled': True,
                'process_names': ['WXWork.exe'],
                'auto_reconnect': True
            }
        },
        'human_like': {
            'enabled': True,
            'random_delay': True,
            'curve_movement': True,
            'reading_pause': True,
            'small_moves': True
        },
        'bridge': {
            'host': '127.0.0.1',
            'port': 8080,
            'debug': False
        },
        'openclaw': {
            'gateway_url': 'ws://127.0.0.1:3100',
            'agent_id': 'wxbot-agent',
            'message': {
                'private_chat': {
                    'enabled': True
                },
                'group_chat': {
                    'enabled': True,
                    'mention_only': True
                }
            }
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/wxbot.log'
        }
    }


async def run_service(config: dict):
    """
    运行桥接服务
    
    Args:
        config: 配置字典
    """
    bridge = get_bridge_service(config)
    
    try:
        await bridge.start()
        
        print("\n" + "=" * 50)
        print("🤖 jz-wxbot-automation 桥接服务运行中")
        print("=" * 50)
        print(f"OpenClaw Gateway: {config['openclaw']['gateway_url']}")
        print(f"Agent ID: {config['openclaw']['agent_id']}")
        print("\n按 Ctrl+C 停止服务...\n")
        
        # 保持运行
        while bridge.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到停止信号...")
    finally:
        await bridge.stop()
        print("服务已停止")


def show_status(config: dict):
    """显示服务状态"""
    print("\n" + "=" * 50)
    print("📊 jz-wxbot-automation 状态")
    print("=" * 50)
    
    # 检查微信进程
    import psutil
    
    wechat_running = False
    wxwork_running = False
    
    for proc in psutil.process_iter(['name']):
        try:
            proc_name = proc.info['name'].lower()
            if 'wechat' in proc_name or 'weixin' in proc_name:
                wechat_running = True
            if 'wxwork' in proc_name:
                wxwork_running = True
        except:
            pass
    
    print(f"个人微信: {'✅ 运行中' if wechat_running else '❌ 未运行'}")
    print(f"企业微信: {'✅ 运行中' if wxwork_running else '❌ 未运行'}")
    
    # 检查 OpenClaw 连接
    print(f"OpenClaw Gateway: {config['openclaw']['gateway_url']}")
    print(f"Agent ID: {config['openclaw']['agent_id']}")
    
    print("\n")


def test_connection(config: dict):
    """测试连接"""
    print("\n" + "=" * 50)
    print("🧪 测试连接")
    print("=" * 50)
    
    # 测试微信进程
    import psutil
    
    print("\n1. 检查微信进程...")
    wechat_found = False
    wxwork_found = False
    
    for proc in psutil.process_iter(['name', 'pid', 'memory_info']):
        try:
            proc_name = proc.info['name']
            if 'wechat' in proc_name.lower() or 'weixin' in proc_name.lower():
                memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                print(f"   ✅ 个人微信: PID {proc.info['pid']} ({memory_mb:.0f}MB)")
                wechat_found = True
            if 'wxwork' in proc_name.lower():
                memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                print(f"   ✅ 企业微信: PID {proc.info['pid']} ({memory_mb:.0f}MB)")
                wxwork_found = True
        except:
            pass
    
    if not wechat_found:
        print("   ❌ 未找到个人微信进程")
    if not wxwork_found:
        print("   ❌ 未找到企业微信进程")
    
    # 测试 OpenClaw 连接
    print("\n2. 测试 OpenClaw 连接...")
    try:
        import websockets
        
        async def test_openclaw():
            gateway_url = config['openclaw']['gateway_url']
            try:
                ws = await websockets.connect(gateway_url, timeout=5)
                await ws.close()
                return True
            except:
                return False
        
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        result = asyncio.run(test_openclaw())
        if result:
            print(f"   ✅ OpenClaw Gateway 可连接")
        else:
            print(f"   ❌ OpenClaw Gateway 连接失败")
    except ImportError:
        print("   ⚠️ websockets 未安装，跳过测试")
    
    print("\n测试完成\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='jz-wxbot-automation - OpenClaw 微信自动化桥接服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py start              # 启动服务
  python main.py status             # 查看状态
  python main.py test               # 测试连接
  python main.py start -c config/custom.yaml  # 使用自定义配置
        """
    )
    
    parser.add_argument('command', choices=['start', 'status', 'test', 'help'],
                        help='命令: start(启动), status(状态), test(测试), help(帮助)')
    parser.add_argument('-c', '--config', help='配置文件路径')
    parser.add_argument('-d', '--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    if args.debug:
        config['logging']['level'] = 'DEBUG'
    
    # 配置日志
    setup_logging(config)
    
    if args.command == 'start':
        # 启动服务
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_service(config))
    
    elif args.command == 'status':
        # 显示状态
        show_status(config)
    
    elif args.command == 'test':
        # 测试连接
        test_connection(config)
    
    elif args.command == 'help':
        parser.print_help()


if __name__ == "__main__":
    main()