#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件存储模块（MinIO/本地/HTTP）
"""

import os
import shutil
import httpx
from pathlib import Path
from typing import Optional
from loguru import logger


class FileStorageManager:
    """文件存储管理器"""
    
    def __init__(self, minio_client=None):
        self.minio_client = minio_client
    
    async def get_file(self, source: str, save_path: str, use_minio: bool = False) -> bool:
        """
        获取文件（支持本地路径、URL 和 MinIO）
        
        Args:
            source: 文件的路径、URL 或 MinIO 对象名称
            save_path: 保存路径
            use_minio: 是否从 MinIO 获取文件
        
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            if use_minio:
                if not self.minio_client:
                    logger.error("MinIO 客户端未初始化")
                    return False
                logger.info(f"从 MinIO 获取文件: {source}")
                # Support both MinIO client styles used in this repo:
                # 1. download_file(object_name, local_path) -> bool
                # 2. get_file(object_name) -> bytes
                download_method = getattr(self.minio_client, "download_file", None)
                if callable(download_method):
                    return bool(download_method(source, save_path))

                get_method = getattr(self.minio_client, "get_file", None)
                if callable(get_method):
                    try:
                        # scripts/minio_client.py style: get_file(object_name, save_path) -> bool
                        return bool(get_method(source, save_path))
                    except TypeError:
                        # api_gateway/utils/minio_client.py style: get_file(object_name) -> bytes
                        data = get_method(source)
                        if not data:
                            logger.error(f"MinIO 文件为空或读取失败: {source}")
                            return False

                        with open(save_path, 'wb') as f:
                            f.write(data)
                        return True

                logger.error("MinIO 客户端缺少可用的下载接口")
                return False
            
            if source.startswith(('http://', 'https://')):
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(source)
                    response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    return True
            else:
                source_path = Path(source)
                
                if not source_path.exists():
                    logger.error(f"本地文件不存在: {source}")
                    return False
                
                shutil.copyfile(source_path, save_path)
                return True
                
        except Exception as e:
            logger.error(f"❌ 获取文件失败: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str, show_progress: bool = False) -> bool:
        """上传文件到 MinIO"""
        if not self.minio_client:
            logger.error("MinIO 客户端未初始化")
            return False
        
        try:
            return self.minio_client.upload_file(local_path, remote_path, show_progress=show_progress)
        except Exception as e:
            logger.error(f"❌ 上传文件失败: {e}")
            return False
    
    def batch_upload_files(self, file_list, max_workers=None):
        """批量上传文件到 MinIO"""
        if not self.minio_client:
            logger.error("MinIO 客户端未初始化")
            return {}
        
        try:
            return self.minio_client.batch_upload_files(file_list, max_workers=max_workers)
        except Exception as e:
            logger.error(f"❌ 批量上传文件失败: {e}")
            return {}
