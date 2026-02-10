#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用启动入口
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, config, logger, db_manager

if __name__ == "__main__":
    # 启动时测试数据库连接
    if db_manager.test_connection():
        logger.info("数据库连接测试成功")
    else:
        logger.error("数据库连接测试失败，请检查配置")
    
    logger.info(f"启动 {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"数据库: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    logger.info(f"JWT过期时间: {config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES}分钟")
    
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
