"""
应用日志初始化模块

在各个服务启动时调用此模块初始化日志系统

使用方法：
    # 在 main.py 或 server.py 的开头添加
    from shared.init_app_logging import init_app_logging
    
    init_app_logging(app_name="API Gateway")
"""

import os
from pathlib import Path
from shared.unified_logging import init_logging, get_logger


def init_app_logging(
    app_name: str = "Application",
    level: str = None,
    log_dir: str = None
):
    """
    初始化应用日志系统
    
    Args:
        app_name: 应用名称（用于日志记录）
        level: 日志级别（默认从环境变量读取）
        log_dir: 日志目录（默认从环境变量读取）
    
    Returns:
        logger: 应用的 logger 实例
    """
    # 从环境变量获取配置
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    if log_dir is None:
        # 默认日志目录
        log_dir = os.getenv("LOG_DIR", "logs")
        
        # 如果是相对路径，转换为绝对路径
        if not Path(log_dir).is_absolute():
            # 获取项目根目录
            current_file = Path(__file__)
            project_root = current_file.parent.parent
            log_dir = str(project_root / log_dir)
    
    # 初始化日志系统
    init_logging(
        level=level,
        log_dir=log_dir,
        enable_console=True,
        enable_file=True,
        colored_console=True
    )
    
    # 获取应用 logger
    logger = get_logger(app_name)
    
    # 记录启动信息
    logger.info("=" * 80)
    logger.info(f"🚀 {app_name} 启动")
    logger.info(f"📝 日志级别: {level}")
    logger.info(f"📁 日志目录: {log_dir}")
    logger.info("=" * 80)
    
    return logger


def init_worker_logging(worker_name: str = "Worker"):
    """
    初始化 Worker 日志系统
    
    Args:
        worker_name: Worker 名称
    
    Returns:
        logger: Worker 的 logger 实例
    """
    return init_app_logging(app_name=worker_name)


def init_mcp_logging(service_name: str = "MCP Service"):
    """
    初始化 MCP 服务日志系统
    
    Args:
        service_name: MCP 服务名称
    
    Returns:
        logger: MCP 服务的 logger 实例
    """
    return init_app_logging(app_name=service_name)


def init_script_logging(script_name: str = "Script"):
    """
    初始化脚本日志系统
    
    Args:
        script_name: 脚本名称
    
    Returns:
        logger: 脚本的 logger 实例
    """
    return init_app_logging(app_name=script_name)


# ========== 便捷函数 ==========

def get_app_logger(name: str):
    """
    获取应用 logger
    
    注意：在调用此函数之前，应该先调用 init_app_logging()
    
    Args:
        name: logger 名称
    
    Returns:
        logger: logger 实例
    """
    return get_logger(name)
