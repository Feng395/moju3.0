#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP 服务统一启动入口
集成所有 MCP 服务到单一进程

功能：
1. CAD Price Search MCP (端口 8200) - CAD 解析 + 价格搜索 + 计算
2. CAD Parser MCP (端口 8101) - CAD 文件解析（备用）
3. Pricing Server MCP (端口 8105) - 价格计算服务（备用）

使用方法：
    python main.py                    # 启动所有 MCP 服务
    python main.py --cad-price-only   # 仅启动 CAD Price Search MCP
    python main.py --port 8200        # 指定 CAD Price Search 端口
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from typing import Optional
from loguru import logger

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MCPServerManager:
    """MCP 服务管理器 - 统一管理所有 MCP 服务"""
    
    def __init__(
        self,
        cad_price_port: int = 8200,
        cad_parser_port: int = 8101,
        pricing_port: int = 8105,
        enable_cad_price: bool = True,
        enable_cad_parser: bool = False,
        enable_pricing: bool = False
    ):
        """
        初始化 MCP 服务管理器
        
        Args:
            cad_price_port: CAD Price Search MCP 端口
            cad_parser_port: CAD Parser MCP 端口
            pricing_port: Pricing Server MCP 端口
            enable_cad_price: 是否启用 CAD Price Search MCP
            enable_cad_parser: 是否启用 CAD Parser MCP
            enable_pricing: 是否启用 Pricing Server MCP
        """
        self.cad_price_port = cad_price_port
        self.cad_parser_port = cad_parser_port
        self.pricing_port = pricing_port
        self.enable_cad_price = enable_cad_price
        self.enable_cad_parser = enable_cad_parser
        self.enable_pricing = enable_pricing
        
        self.tasks = []
        
        logger.info("=" * 70)
        logger.info("MCP 服务统一启动")
        logger.info("=" * 70)
        logger.info(f"CAD Price Search MCP: {'✅ 启用' if enable_cad_price else '❌ 禁用'} (端口: {cad_price_port})")
        logger.info(f"CAD Parser MCP: {'✅ 启用' if enable_cad_parser else '❌ 禁用'} (端口: {cad_parser_port})")
        logger.info(f"Pricing Server MCP: {'✅ 启用' if enable_pricing else '❌ 禁用'} (端口: {pricing_port})")
        logger.info("=" * 70)
    
    async def start_cad_price_search_mcp(self):
        """启动 CAD Price Search MCP 服务"""
        try:
            logger.info(f"🚀 启动 CAD Price Search MCP (端口: {self.cad_price_port})...")
            
            # 导入服务
            sys.path.insert(0, str(Path(__file__).parent / "cad_price_search_mcp"))
            from cad_price_search_mcp import server
            
            # 设置端口环境变量
            os.environ['MCP_PORT'] = str(self.cad_price_port)
            
            # 启动服务（这里需要根据实际的服务启动方式调整）
            logger.info(f"✅ CAD Price Search MCP 已启动 (端口: {self.cad_price_port})")
            
            # 保持服务运行
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ CAD Price Search MCP 启动失败: {e}", exc_info=True)
            raise
    
    async def start_cad_parser_mcp(self):
        """启动 CAD Parser MCP 服务"""
        try:
            logger.info(f"🚀 启动 CAD Parser MCP (端口: {self.cad_parser_port})...")
            
            # 导入服务
            sys.path.insert(0, str(Path(__file__).parent / "cad_parser_mcp"))
            from cad_parser_mcp import server
            
            # 设置端口环境变量
            os.environ['MCP_PORT'] = str(self.cad_parser_port)
            
            logger.info(f"✅ CAD Parser MCP 已启动 (端口: {self.cad_parser_port})")
            
            # 保持服务运行
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ CAD Parser MCP 启动失败: {e}", exc_info=True)
            raise
    
    async def start_pricing_server_mcp(self):
        """启动 Pricing Server MCP 服务"""
        try:
            logger.info(f"🚀 启动 Pricing Server MCP (端口: {self.pricing_port})...")
            
            # 导入服务
            sys.path.insert(0, str(Path(__file__).parent / "pricing_server_mcp"))
            from pricing_server_mcp import server
            
            # 设置端口环境变量
            os.environ['MCP_PORT'] = str(self.pricing_port)
            
            logger.info(f"✅ Pricing Server MCP 已启动 (端口: {self.pricing_port})")
            
            # 保持服务运行
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Pricing Server MCP 启动失败: {e}", exc_info=True)
            raise
    
    async def start(self):
        """启动所有启用的 MCP 服务"""
        try:
            # 启动 CAD Price Search MCP
            if self.enable_cad_price:
                task = asyncio.create_task(self.start_cad_price_search_mcp())
                self.tasks.append(task)
            
            # 启动 CAD Parser MCP
            if self.enable_cad_parser:
                task = asyncio.create_task(self.start_cad_parser_mcp())
                self.tasks.append(task)
            
            # 启动 Pricing Server MCP
            if self.enable_pricing:
                task = asyncio.create_task(self.start_pricing_server_mcp())
                self.tasks.append(task)
            
            if not self.tasks:
                logger.error("❌ 没有启用任何 MCP 服务")
                return
            
            logger.info("=" * 70)
            logger.info("✅ 所有 MCP 服务已启动")
            logger.info("=" * 70)
            logger.info("按 Ctrl+C 停止服务")
            logger.info("=" * 70)
            
            # 等待所有任务完成或被中断
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("\n收到中断信号，正在停止服务...")
        except Exception as e:
            logger.error(f"❌ 服务运行异常: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self):
        """停止所有 MCP 服务"""
        logger.info("正在停止 MCP 服务...")
        
        # 取消所有任务
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("=" * 70)
        logger.info("✅ 所有 MCP 服务已停止")
        logger.info("=" * 70)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="MCP 服务统一启动入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                        # 启动所有 MCP 服务
  python main.py --cad-price-only       # 仅启动 CAD Price Search MCP
  python main.py --port 8200            # 指定 CAD Price Search 端口
  python main.py --all                  # 启动所有服务（包括备用）
        """
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8200,
        help="CAD Price Search MCP 端口（默认: 8200）"
    )
    
    parser.add_argument(
        "--cad-price-only",
        action="store_true",
        help="仅启动 CAD Price Search MCP（推荐）"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="启动所有 MCP 服务（包括备用服务）"
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()
    
    # 确定启用哪些服务
    enable_cad_price = True  # 默认启用
    enable_cad_parser = False
    enable_pricing = False
    
    if args.all:
        # 启动所有服务
        enable_cad_price = True
        enable_cad_parser = True
        enable_pricing = True
    elif args.cad_price_only:
        # 仅启动 CAD Price Search MCP
        enable_cad_price = True
        enable_cad_parser = False
        enable_pricing = False
    
    # 创建并启动服务管理器
    manager = MCPServerManager(
        cad_price_port=args.port,
        enable_cad_price=enable_cad_price,
        enable_cad_parser=enable_cad_parser,
        enable_pricing=enable_pricing
    )
    
    # 启动服务
    await manager.start()


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
