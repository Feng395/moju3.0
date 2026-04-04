"""
统一日志初始化模块
负责人：系统架构

功能：
1. 统一所有模块的日志配置
2. 确保日志同时输出到控制台和文件
3. 提供简单的初始化接口
4. 支持不同模块的日志级别配置

使用方法：
    # 方式1：在应用启动时初始化（推荐）
    from shared.unified_logging import init_logging, get_logger
    
    init_logging()  # 初始化日志系统
    logger = get_logger(__name__)
    logger.info("应用启动")
    
    # 方式2：快速初始化（用于脚本）
    from shared.unified_logging import quick_init_logging
    
    logger = quick_init_logging(__name__)
    logger.info("脚本开始")
"""

import logging
import logging.handlers
import sys
import os
import zipfile
from pathlib import Path
from typing import Optional
from datetime import datetime


# ========== 全局配置 ==========

# 日志目录
DEFAULT_LOG_DIR = "logs"

# 日志格式
CONSOLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志文件配置
MAX_BYTES = 10 * 1024 * 1024  # reserved for compatibility
BACKUP_COUNT = 30  # 保留30天备份

# 是否已初始化
_initialized = False


class DailyZipTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Rotate at midnight, retain daily archives, and compress to zip."""

    def __init__(self, filename: Path, backup_count: int, encoding: str = "utf-8"):
        super().__init__(
            filename=str(filename),
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding=encoding,
        )
        self.namer = lambda default_name: f"{default_name}.zip"
        self.rotator = self._zip_rotator

    @staticmethod
    def _zip_rotator(source: str, dest: str):
        with zipfile.ZipFile(dest, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(source, arcname=os.path.basename(source))
        os.remove(source)

    def getFilesToDelete(self):
        """Include .zip archives in retention cleanup."""
        dir_name, base_name = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        result = []
        prefix = base_name + "."
        plen = len(prefix)

        for file_name in file_names:
            if not file_name.startswith(prefix):
                continue
            suffix = file_name[plen:]
            if suffix.endswith(".zip"):
                suffix = suffix[:-4]
            if self.extMatch.match(suffix):
                result.append(os.path.join(dir_name, file_name))

        result.sort()
        if len(result) < self.backupCount:
            return []
        return result[: len(result) - self.backupCount]


# ========== 彩色控制台格式化器 ==========

class ModuleFilter(logging.Filter):
    """
    模块过滤器
    只允许特定模块的日志通过
    """
    
    def __init__(self, module_prefix: str):
        super().__init__()
        self.module_prefix = module_prefix
    
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith(self.module_prefix)


class ColoredConsoleFormatter(logging.Formatter):
    """
    彩色控制台格式化器
    为不同级别的日志添加颜色
    """
    
    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
        "RESET": "\033[0m"        # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录（带颜色）"""
        # 获取颜色
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        
        # 格式化时间
        timestamp = datetime.fromtimestamp(record.created).strftime(DATE_FORMAT)
        
        # 构建日志消息
        log_message = (
            f"{color}[{timestamp}] "
            f"{record.levelname:8s}{reset} "
            f"{record.name:30s} | "
            f"{record.getMessage()}"
        )
        
        # 添加异常信息
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"
        
        return log_message


# ========== 日志初始化函数 ==========

def init_logging(
    level: str = None,
    log_dir: str = None,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_module_logs: bool = True,  # 新增：启用模块分类日志
    colored_console: bool = True,
    force_reinit: bool = False
):
    """
    初始化统一日志系统
    
    Args:
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_dir: 日志文件目录（默认：logs）
        enable_console: 是否启用控制台输出（默认：True）
        enable_file: 是否启用文件输出（默认：True）
        enable_module_logs: 是否启用模块分类日志（默认：True）
        colored_console: 是否使用彩色控制台（默认：True）
        force_reinit: 是否强制重新初始化（默认：False）
    
    Returns:
        None
    """
    global _initialized
    
    # 如果已初始化且不强制重新初始化，则跳过
    if _initialized and not force_reinit:
        return
    
    # 从环境变量获取日志级别
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    # 从环境变量获取日志目录
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", DEFAULT_LOG_DIR)
    
    # 转换日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除已有的 handlers
    root_logger.handlers.clear()
    
    # ========== 1. 控制台输出 ==========
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # 选择格式化器
        if colored_console:
            console_formatter = ColoredConsoleFormatter()
        else:
            console_formatter = logging.Formatter(
                fmt=CONSOLE_FORMAT,
                datefmt=DATE_FORMAT
            )
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # ========== 2. 文件输出 ==========
    if enable_file:
        # 创建日志目录
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_formatter = logging.Formatter(
            fmt=FILE_FORMAT,
            datefmt=DATE_FORMAT
        )
        
        # 2.1 总日志文件（所有级别）
        file_handler = DailyZipTimedRotatingFileHandler(
            filename=log_path / "app.log",
            backup_count=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # 2.2 错误日志文件（仅ERROR及以上）
        error_handler = DailyZipTimedRotatingFileHandler(
            filename=log_path / "error.log",
            backup_count=BACKUP_COUNT,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
        
        # 2.3 模块分类日志
        if enable_module_logs:
            module_configs = [
                ("api_gateway", "api_gateway.log"),
                ("workers", "workers.log"),
                ("agents", "agents.log"),
                ("mcp_services", "mcp_services.log"),
                ("scripts", "scripts.log"),
                ("shared", "shared.log"),
            ]
            
            for module_prefix, filename in module_configs:
                module_handler = DailyZipTimedRotatingFileHandler(
                    filename=log_path / filename,
                    backup_count=BACKUP_COUNT,
                    encoding="utf-8",
                )
                module_handler.setLevel(log_level)
                module_handler.setFormatter(file_formatter)
                module_handler.addFilter(ModuleFilter(module_prefix))
                root_logger.addHandler(module_handler)
    
    # 标记为已初始化
    _initialized = True
    
    # 记录初始化信息
    root_logger.info(
        f"统一日志系统初始化完成: "
        f"level={level}, "
        f"console={enable_console}, "
        f"file={enable_file}, "
        f"module_logs={enable_module_logs}, "
        f"log_dir={log_dir}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取 logger 实例
    
    Args:
        name: logger 名称（通常使用 __name__）
    
    Returns:
        logging.Logger: logger 实例
    
    注意：
        在调用此函数之前，应该先调用 init_logging() 初始化日志系统
    """
    # 如果还未初始化，自动初始化
    if not _initialized:
        init_logging()
    
    return logging.getLogger(name)


def quick_init_logging(
    name: str,
    level: str = "INFO",
    log_dir: str = None
) -> logging.Logger:
    """
    快速初始化日志并返回 logger
    
    适用于脚本和简单应用，一行代码完成初始化
    
    Args:
        name: logger 名称（通常使用 __name__）
        level: 日志级别（默认：INFO）
        log_dir: 日志目录（默认：logs）
    
    Returns:
        logging.Logger: logger 实例
    
    使用示例：
        logger = quick_init_logging(__name__)
        logger.info("脚本开始")
    """
    init_logging(level=level, log_dir=log_dir)
    return get_logger(name)


# ========== 日志级别设置 ==========

def set_log_level(level: str, logger_name: str = None):
    """
    设置日志级别
    
    Args:
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        logger_name: logger 名称（None 表示根 logger）
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if logger_name:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
    else:
        logging.getLogger().setLevel(log_level)


# ========== 禁用特定模块的日志 ==========

def disable_logger(logger_name: str):
    """
    禁用特定模块的日志
    
    Args:
        logger_name: logger 名称
    """
    logging.getLogger(logger_name).setLevel(logging.CRITICAL + 1)


def enable_logger(logger_name: str, level: str = "INFO"):
    """
    启用特定模块的日志
    
    Args:
        logger_name: logger 名称
        level: 日志级别
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger(logger_name).setLevel(log_level)


# ========== 日志上下文 ==========

class LogContext:
    """
    日志上下文管理器
    
    用于在日志中添加额外的上下文信息
    
    使用方法：
        with LogContext(job_id="xxx", user_id="yyy"):
            logger.info("这条日志会包含 job_id 和 user_id")
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


# ========== 便捷函数 ==========

def log_function_call(func):
    """
    装饰器：记录函数调用
    
    使用方法：
        @log_function_call
        def my_function():
            pass
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        logger.debug(f"调用函数: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"函数完成: {func.__name__} (耗时: {elapsed:.3f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"函数失败: {func.__name__} (耗时: {elapsed:.3f}s)", exc_info=True)
            raise
    
    return wrapper


# ========== 测试函数 ==========

def test_logging():
    """测试日志系统"""
    # 初始化日志
    init_logging(level="DEBUG")
    
    # 获取 logger
    logger = get_logger(__name__)
    
    # 测试不同级别的日志
    logger.debug("这是一条 DEBUG 日志")
    logger.info("这是一条 INFO 日志")
    logger.warning("这是一条 WARNING 日志")
    logger.error("这是一条 ERROR 日志")
    logger.critical("这是一条 CRITICAL 日志")
    
    # 测试异常日志
    try:
        1 / 0
    except Exception as e:
        logger.error("捕获到异常", exc_info=True)
    
    print("\n✅ 日志测试完成！")
    print(f"请查看日志文件: {DEFAULT_LOG_DIR}/app.log")
    print(f"请查看错误日志: {DEFAULT_LOG_DIR}/error.log")


if __name__ == "__main__":
    test_logging()
