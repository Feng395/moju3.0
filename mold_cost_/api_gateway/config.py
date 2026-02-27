"""
配置管理模块 - API Gateway
使用统一配置模块

更新日期：2026-02-27
更新内容：使用 shared.config 作为配置源，保持向后兼容
"""
from shared.config import settings, get_settings, Settings

# 导出配置实例和类，保持向后兼容
__all__ = ['settings', 'get_settings', 'Settings']
