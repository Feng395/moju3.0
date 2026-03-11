#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP 服务统一启动入口

通过 uvicorn 启动 cad_price_search_mcp 服务。
业务逻辑全部在 cad_price_search_mcp/server.py 中，本文件只负责启动。

使用方法：
    python main.py                    # 启动 MCP 服务（默认端口 8200）
    python main.py --port 8201        # 指定端口
    python main.py --host 127.0.0.1   # 指定监听地址
"""

import sys
import os
import argparse
from pathlib import Path

import uvicorn

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
# 添加 cad_price_search_mcp 目录（server.py 内部需要）
sys.path.insert(0, str(Path(__file__).parent / "cad_price_search_mcp"))

# 使用统一日志系统
from shared.unified_logging import init_logging, get_logger

# 初始化日志系统（统一到项目根目录的 logs 文件夹）
init_logging(log_dir=str(project_root / "logs"))
logger = get_logger("mcp_services.main")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="MCP 服务统一启动入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                        # 默认端口 8200
  python main.py --port 8201            # 指定端口
  python main.py --host 127.0.0.1       # 仅本地访问
        """
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CAD_PRICE_SEARCH_MCP_PORT", "8200")),
        help="监听端口（默认: 8200，可通过 CAD_PRICE_SEARCH_MCP_PORT 环境变量设置）"
    )

    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("CAD_PRICE_SEARCH_MCP_HOST", "0.0.0.0"),
        help="监听地址（默认: 0.0.0.0）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 导入 server 模块并创建 ASGI 应用
    from cad_price_search_mcp.server import create_app, CAD_AVAILABLE

    logger.info("=" * 60)
    logger.info("MCP 服务统一启动")
    logger.info("=" * 60)
    logger.info(f"地址: http://{args.host}:{args.port}")
    logger.info(f"调用端点: http://{args.host}:{args.port}/call_tool")
    logger.info(f"健康检查: http://{args.host}:{args.port}/health")
    if CAD_AVAILABLE:
        logger.info("工具: 3 CAD + 12 搜索 + 23 计算 = 38 个")
    else:
        logger.info("工具: 12 搜索 + 23 计算 = 35 个（CAD 不可用）")
    logger.info("=" * 60)

    app = create_app(host=args.host, port=args.port)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    try:
        import asyncio
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        main()
    except KeyboardInterrupt:
        logger.info("\n程序已退出")
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}", exc_info=True)
        sys.exit(1)
