#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模具成本核算系统 - 统一启动入口
集成所有服务到单一进程，统一端口管理

功能：
1. API Gateway (FastAPI) - 主要 HTTP 接口
2. Orchestrator Worker - 后台任务处理
3. WebSocket 服务 - 实时通信
4. 健康检查 - 服务状态监控

使用方法：
    python main.py                    # 启动所有服务
    python main.py --api-only         # 仅启动 API Gateway
    python main.py --worker-only      # 仅启动 Worker
    python main.py --port 8000        # 指定端口
"""

import asyncio
import sys
import os
import signal
import argparse
from pathlib import Path
from typing import Optional
import uvicorn
from loguru import logger

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入配置
from api_gateway.config import settings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class UnifiedServer:
    """统一服务器 - 集成所有服务"""
    
    def __init__(
        self,
        port: int = 8000,
        enable_worker: bool = True,
        enable_api: bool = True
    ):
        """
        初始化统一服务器
        
        Args:
            port: API Gateway 端口
            enable_worker: 是否启用 Worker
            enable_api: 是否启用 API Gateway
        """
        self.port = port
        self.enable_worker = enable_worker
        self.enable_api = enable_api
        self.worker_task: Optional[asyncio.Task] = None
        self.api_server: Optional[uvicorn.Server] = None
        self.shutdown_event = asyncio.Event()
        
        logger.info("=" * 70)
        logger.info("模具成本核算系统 - 统一启动")
        logger.info("=" * 70)
        logger.info(f"API Gateway: {'✅ 启用' if enable_api else '❌ 禁用'}")
        logger.info(f"Worker: {'✅ 启用' if enable_worker else '❌ 禁用'}")
        logger.info(f"端口: {port}")
        logger.info("=" * 70)
    
    async def start_worker(self):
        """启动 Orchestrator Worker"""
        try:
            from workers.orchestrator_worker import OrchestratorWorker
            
            logger.info("🚀 启动 Orchestrator Worker...")
            
            # 从环境变量读取是否启用重试
            enable_retry = os.getenv("ENABLE_MESSAGE_RETRY", "false").lower() == "true"
            
            worker = OrchestratorWorker(enable_retry=enable_retry)
            
            if enable_retry:
                logger.info("⚠️  消息重试已启用：系统异常时消息会重新入队")
            else:
                logger.info("✅ 消息重试已禁用：所有失败任务都会移到死信队列")
            
            await worker.start()
            
        except Exception as e:
            logger.error(f"❌ Worker 启动失败: {e}", exc_info=True)
            raise
    
    async def start_api(self):
        """启动 API Gateway"""
        try:
            from api_gateway.main import app
            
            logger.info(f"🚀 启动 API Gateway (端口: {self.port})...")
            
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=self.port,
                reload=False,  # 统一启动时禁用自动重载
                log_level="info",
                access_log=True
            )
            
            self.api_server = uvicorn.Server(config)
            
            logger.info(f"✅ API Gateway 已启动")
            logger.info(f"   访问地址: http://localhost:{self.port}")
            logger.info(f"   API 文档: http://localhost:{self.port}/docs")
            logger.info(f"   健康检查: http://localhost:{self.port}/health")
            
            await self.api_server.serve()
            
        except Exception as e:
            logger.error(f"❌ API Gateway 启动失败: {e}", exc_info=True)
            raise
    
    async def start(self):
        """启动所有服务"""
        tasks = []
        
        try:
            # 启动 Worker
            if self.enable_worker:
                self.worker_task = asyncio.create_task(self.start_worker())
                tasks.append(self.worker_task)
            
            # 启动 API Gateway
            if self.enable_api:
                api_task = asyncio.create_task(self.start_api())
                tasks.append(api_task)
            
            if not tasks:
                logger.error("❌ 没有启用任何服务")
                return
            
            logger.info("=" * 70)
            logger.info("✅ 所有服务已启动")
            logger.info("=" * 70)
            logger.info("按 Ctrl+C 停止服务")
            logger.info("=" * 70)
            
            # 等待所有任务完成或被中断
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("\n收到中断信号，正在停止服务...")
        except Exception as e:
            logger.error(f"❌ 服务运行异常: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self):
        """停止所有服务"""
        logger.info("正在停止服务...")
        
        # 停止 API Server
        if self.api_server:
            logger.info("停止 API Gateway...")
            self.api_server.should_exit = True
        
        # 停止 Worker
        if self.worker_task and not self.worker_task.done():
            logger.info("停止 Orchestrator Worker...")
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("=" * 70)
        logger.info("✅ 所有服务已停止")
        logger.info("=" * 70)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="模具成本核算系统 - 统一启动入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 启动所有服务（默认端口 8000）
  python main.py --port 8211        # 指定端口
  python main.py --api-only         # 仅启动 API Gateway
  python main.py --worker-only      # 仅启动 Worker
  python main.py --no-worker        # 启动 API，不启动 Worker
        """
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API Gateway 端口（默认: 8000）"
    )
    
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="仅启动 API Gateway"
    )
    
    parser.add_argument(
        "--worker-only",
        action="store_true",
        help="仅启动 Orchestrator Worker"
    )
    
    parser.add_argument(
        "--no-worker",
        action="store_true",
        help="不启动 Worker（仅启动 API）"
    )
    
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="不启动 API（仅启动 Worker）"
    )
    
    return parser.parse_args()


def setup_signal_handlers(server: UnifiedServer):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logger.info(f"\n收到信号 {signum}，正在停止服务...")
        # 创建新的事件循环来运行停止操作
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.stop())
        loop.close()
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主函数"""
    args = parse_args()
    
    # 确定启用哪些服务
    enable_api = True
    enable_worker = True
    
    if args.api_only:
        enable_worker = False
    elif args.worker_only:
        enable_api = False
    elif args.no_worker:
        enable_worker = False
    elif args.no_api:
        enable_api = False
    
    # 创建并启动服务器
    server = UnifiedServer(
        port=args.port,
        enable_worker=enable_worker,
        enable_api=enable_api
    )
    
    # 设置信号处理器
    # setup_signal_handlers(server)  # Windows 上可能不支持
    
    # 启动服务
    await server.start()


if __name__ == "__main__":
    try:
        # Windows 平台需要设置事件循环策略
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n程序已退出")
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}", exc_info=True)
        sys.exit(1)
