#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一配置加载模块

职责：
1. 优先加载主配置 mold_cost_/.env
2. 然后加载 scripts 专用配置 scripts/.env（作为补充）
3. 提供配置访问接口

使用方法：
    from scripts.config_loader import load_config, get_config

    # 加载配置（通常在程序入口处调用一次）
    load_config()

    # 获取配置值
    config = get_config()
    db_host = config.get('DB_HOST')
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置加载器"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._config = {}

    def load(self) -> Dict[str, Any]:
        """
        加载配置

        加载顺序：
        1. 主配置 mold_cost_/.env（优先）
        2. scripts 专用配置 scripts/.env（补充，覆盖同名配置）

        Returns:
            配置字典
        """
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        scripts_dir = Path(__file__).parent

        # 1. 加载主配置（优先）
        main_env_path = project_root / '.env'
        if main_env_path.exists():
            load_dotenv(main_env_path)
            print(f"✅ 加载主配置: {main_env_path}")
        else:
            print(f"⚠️ 主配置文件不存在: {main_env_path}")

        # 2. 加载 scripts 专用配置（补充）
        scripts_env_path = scripts_dir / '.env'
        if scripts_env_path.exists():
            load_dotenv(scripts_env_path, override=True)  # override=True 允许覆盖同名配置
            print(f"✅ 加载 scripts 专用配置: {scripts_env_path}")
        else:
            print(f"⚠️ scripts 专用配置文件不存在: {scripts_env_path}")

        # 3. 收集所有配置
        self._collect_env_config()

        return self._config

    def _collect_env_config(self):
        """收集环境变量配置"""
        # 数据库配置
        self._config['DB_HOST'] = os.getenv('DB_HOST')
        self._config['DB_PORT'] = int(os.getenv('DB_PORT', 0)) if os.getenv('DB_PORT') else None
        self._config['DB_NAME'] = os.getenv('DB_NAME')
        self._config['DB_USER'] = os.getenv('DB_USER')
        self._config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

        # MinIO 配置
        self._config['MINIO_ENDPOINT'] = os.getenv('MINIO_ENDPOINT')
        self._config['MINIO_ACCESS_KEY'] = os.getenv('MINIO_ACCESS_KEY')
        self._config['MINIO_SECRET_KEY'] = os.getenv('MINIO_SECRET_KEY')
        self._config['MINIO_USE_HTTPS'] = os.getenv('MINIO_USE_HTTPS', 'false')
        self._config['MINIO_BUCKET'] = os.getenv('MINIO_BUCKET')
        self._config['MINIO_BUCKET_FILES'] = os.getenv('MINIO_BUCKET_FILES')
        self._config['MINIO_REGION'] = os.getenv('MINIO_REGION')
        self._config['MINIO_EXTERNAL_ENDPOINT'] = os.getenv('MINIO_EXTERNAL_ENDPOINT')

        # MinIO 性能配置
        self._config['MINIO_UPLOAD_PART_SIZE'] = int(os.getenv('MINIO_UPLOAD_PART_SIZE', str(10 * 1024 * 1024)))
        self._config['MINIO_UPLOAD_WORKERS'] = int(os.getenv('MINIO_UPLOAD_WORKERS', '5'))
        self._config['MINIO_DOWNLOAD_WORKERS'] = int(os.getenv('MINIO_DOWNLOAD_WORKERS', '5'))

        # ODA 配置
        self._config['ODA_FILE_CONVERTER_PATH'] = os.getenv('ODA_FILE_CONVERTER_PATH')

        # 服务器配置
        self._config['API_HOST'] = os.getenv('API_HOST', '0.0.0.0')
        self._config['API_PORT'] = int(os.getenv('API_PORT', '8000'))
        self._config['API_RELOAD'] = os.getenv('API_RELOAD', 'false')
        self._config['API_WORKERS'] = int(os.getenv('API_WORKERS', '1'))

        # CAD 服务器配置
        self._config['CAD_SERVER_HOST'] = os.getenv('CAD_SERVER_HOST', '0.0.0.0')
        self._config['CAD_SERVER_PORT'] = int(os.getenv('CAD_SERVER_PORT', '8200'))

        # 导出配置
        self._config['EXPORT_WORKERS'] = int(os.getenv('EXPORT_WORKERS', '5'))

        # Redis 配置
        self._config['REDIS_URL'] = os.getenv('REDIS_URL')

        # RabbitMQ 配置
        self._config['RABBITMQ_HOST'] = os.getenv('RABBITMQ_HOST')
        self._config['RABBITMQ_PORT'] = int(os.getenv('RABBITMQ_PORT', '5672'))
        self._config['RABBITMQ_USER'] = os.getenv('RABBITMQ_USER')
        self._config['RABBITMQ_PASSWORD'] = os.getenv('RABBITMQ_PASSWORD')

        # 日志配置
        self._config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')
        self._config['LOG_DIR'] = os.getenv('LOG_DIR', 'logs')

        # 其他配置
        self._config['DEBUG'] = os.getenv('DEBUG', 'false')
        self._config['RELOAD'] = os.getenv('RELOAD', 'true')

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()

    def reload(self):
        """重新加载配置"""
        self._config = {}
        self.load()


# 全局配置加载器实例
_config_loader = ConfigLoader()


def load_config() -> Dict[str, Any]:
    """
    加载配置

    Returns:
        配置字典
    """
    return _config_loader.load()


def get_config() -> Dict[str, Any]:
    """
    获取配置字典

    Returns:
        配置字典
    """
    return _config_loader.get_all()


def get(key: str, default: Any = None) -> Any:
    """
    获取配置值

    Args:
        key: 配置键
        default: 默认值

    Returns:
        配置值
    """
    return _config_loader.get(key, default)


# 便捷函数：获取数据库配置
def get_db_config() -> Dict[str, Any]:
    """获取数据库配置"""
    return {
        'host': _config_loader.get('DB_HOST'),
        'port': _config_loader.get('DB_PORT'),
        'database': _config_loader.get('DB_NAME'),
        'user': _config_loader.get('DB_USER'),
        'password': _config_loader.get('DB_PASSWORD'),
    }


# 便捷函数：获取 MinIO 配置
def get_minio_config() -> Dict[str, Any]:
    """获取 MinIO 配置"""
    return {
        'endpoint': _config_loader.get('MINIO_ENDPOINT'),
        'access_key': _config_loader.get('MINIO_ACCESS_KEY'),
        'secret_key': _config_loader.get('MINIO_SECRET_KEY'),
        'use_https': _config_loader.get('MINIO_USE_HTTPS', 'false'),
        'bucket': _config_loader.get('MINIO_BUCKET'),
        'bucket_files': _config_loader.get('MINIO_BUCKET_FILES'),
        'region': _config_loader.get('MINIO_REGION'),
        'upload_part_size': _config_loader.get('MINIO_UPLOAD_PART_SIZE', 10 * 1024 * 1024),
        'upload_workers': _config_loader.get('MINIO_UPLOAD_WORKERS', 5),
        'download_workers': _config_loader.get('MINIO_DOWNLOAD_WORKERS', 5),
    }


# 便捷函数：获取 ODA 配置
def get_oda_config() -> Dict[str, Any]:
    """获取 ODA 配置"""
    return {
        'oda_file_converter_path': _config_loader.get('ODA_FILE_CONVERTER_PATH'),
    }


# 便捷函数：获取服务器配置
def get_server_config() -> Dict[str, Any]:
    """获取服务器配置"""
    return {
        'host': _config_loader.get('API_HOST', '0.0.0.0'),
        'port': _config_loader.get('API_PORT', 8000),
        'reload': _config_loader.get('API_RELOAD', 'false'),
        'workers': _config_loader.get('API_WORKERS', 1),
    }


# 便捷函数：获取 CAD 服务器配置
def get_cad_server_config() -> Dict[str, Any]:
    """获取 CAD 服务器配置"""
    return {
        'host': _config_loader.get('CAD_SERVER_HOST', '0.0.0.0'),
        'port': _config_loader.get('CAD_SERVER_PORT', 8200),
    }


# 便捷函数：获取导出配置
def get_export_config() -> Dict[str, Any]:
    """获取导出配置"""
    return {
        'export_workers': _config_loader.get('EXPORT_WORKERS', 5),
    }


if __name__ == '__main__':
    # 测试配置加载
    config = load_config()
    print("\n" + "=" * 60)
    print("配置加载测试")
    print("=" * 60)

    print("\n数据库配置:")
    db_config = get_db_config()
    for key, value in db_config.items():
        print(f"  {key}: {value}")

    print("\nMinIO 配置:")
    minio_config = get_minio_config()
    for key, value in minio_config.items():
        print(f"  {key}: {value}")

    print("\nODA 配置:")
    oda_config = get_oda_config()
    for key, value in oda_config.items():
        print(f"  {key}: {value}")

    print("\n服务器配置:")
    server_config = get_server_config()
    for key, value in server_config.items():
        print(f"  {key}: {value}")

    print("\nCAD 服务器配置:")
    cad_config = get_cad_server_config()
    for key, value in cad_config.items():
        print(f"  {key}: {value}")

    print("\n导出配置:")
    export_config = get_export_config()
    for key, value in export_config.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)