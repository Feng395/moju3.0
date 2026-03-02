"""
MinIO客户端工具类
处理文件上传、下载、删除等操作

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost_/api_gateway/utils/minio_client.py + mold_cost-main/api_gateway/utils/minio_client.py
- 合并策略：使用 mold_cost_ 为基础，补充 mold_cost-main 的便捷函数
- 主要功能：
  1. 文件上传、下载、删除
  2. 预签名URL生成
  3. 支持外部访问地址配置
  4. 提供便捷函数供其他模块使用
"""
from shared.unified_logging import get_logger
import uuid
from datetime import datetime, timedelta
from typing import BinaryIO, Dict, Optional
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile
import logging

from ..config import settings

logger = get_logger(__name__)


class MinIOClient:
    """MinIO客户端封装"""
    
    def __init__(self):
        """初始化MinIO客户端"""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_HTTPS,
            region=settings.MINIO_REGION
        )
        
        # 如果配置了外部访问地址，创建一个用于生成预签名URL的客户端
        if settings.MINIO_EXTERNAL_ENDPOINT and settings.MINIO_EXTERNAL_ENDPOINT != settings.MINIO_ENDPOINT:
            self.presigned_client = Minio(
                endpoint=settings.MINIO_EXTERNAL_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_HTTPS,
                region=settings.MINIO_REGION
            )
            logger.info(f"✅ MinIO外部访问地址: {settings.MINIO_EXTERNAL_ENDPOINT}")
        else:
            self.presigned_client = self.client
        
        self.bucket_files = settings.MINIO_BUCKET_FILES
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """确保必要的bucket存在"""
        try:
            if not self.client.bucket_exists(self.bucket_files):
                self.client.make_bucket(self.bucket_files)
                logger.info(f"✅ 创建MinIO bucket: {self.bucket_files}")
        except S3Error as e:
            logger.error(f"❌ 创建MinIO bucket失败: {e}")
            raise
    
    async def upload_file(
        self,
        file: UploadFile,
        prefix: str = "files"
    ) -> Dict[str, str]:
        """
        上传文件到MinIO
        
        Args:
            file: FastAPI UploadFile对象
            prefix: 文件路径前缀（如 "dwg", "prt"）
        
        Returns:
            包含文件信息的字典：
            {
                "file_id": "uuid",
                "object_name": "dwg/2026/01/xxx.dwg",
                "file_size": 12345678,
                "etag": "abc123...",
                "bucket": "files"
            }
        """
        try:
            # 1. 生成唯一文件ID和路径
            file_id = str(uuid.uuid4())
            now = datetime.now()
            file_extension = Path(file.filename).suffix.lower()
            
            # 构造object_name: prefix/year/month/file_id.ext
            object_name = f"{prefix}/{now.year}/{now.month:02d}/{file_id}{file_extension}"
            
            # 2. 获取文件大小
            file.file.seek(0, 2)  # 移动到文件末尾
            file_size = file.file.tell()
            file.file.seek(0)  # 重置到文件开头
            
            # 3. 上传到MinIO（流式上传）
            result = self.client.put_object(
                bucket_name=self.bucket_files,
                object_name=object_name,
                data=file.file,
                length=file_size,
                content_type=file.content_type or "application/octet-stream"
            )
            
            logger.info(f"✅ 文件上传成功: {object_name} ({file_size} bytes)")
            
            # 4. 返回文件信息
            return {
                "file_id": file_id,
                "object_name": object_name,
                "file_path": object_name,  # 别名，方便使用
                "file_size": file_size,
                "etag": result.etag,
                "bucket": self.bucket_files,
                "original_filename": file.filename
            }
        
        except S3Error as e:
            logger.error(f"❌ MinIO上传失败: {e}")
            raise Exception(f"文件上传失败: {str(e)}")
        except Exception as e:
            logger.error(f"❌ 文件上传异常: {e}")
            raise
    
    def get_file(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        """
        从MinIO读取文件
        
        Args:
            object_name: 对象名称/路径
            bucket: bucket名称，默认使用files bucket
        
        Returns:
            文件内容（字节）
        """
        try:
            bucket = bucket or self.bucket_files
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"❌ MinIO读取文件失败: {e}")
            raise Exception(f"文件读取失败: {str(e)}")
    
    def delete_file(self, object_name: str, bucket: Optional[str] = None):
        """
        删除MinIO中的文件
        
        Args:
            object_name: 对象名称/路径
            bucket: bucket名称
        """
        try:
            bucket = bucket or self.bucket_files
            self.client.remove_object(bucket, object_name)
            logger.info(f"✅ 文件删除成功: {object_name}")
        except S3Error as e:
            logger.error(f"❌ MinIO删除文件失败: {e}")
            raise Exception(f"文件删除失败: {str(e)}")
    
    def generate_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=24),
        bucket: Optional[str] = None
    ) -> str:
        """
        生成预签名下载URL
        
        Args:
            object_name: 对象名称/路径
            expires: 过期时间
            bucket: bucket名称
        
        Returns:
            预签名URL
        """
        try:
            bucket = bucket or self.bucket_files
            # 使用专门的预签名客户端（可能使用外部地址）
            url = self.presigned_client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"❌ 生成预签名URL失败: {e}")
            raise Exception(f"生成下载链接失败: {str(e)}")
    
    # 🆕 补充来自 mold_cost-main 的方法
    
    def get_file_stream(self, object_name: str, bucket: Optional[str] = None):
        """
        获取文件流（用于大文件）
        
        Args:
            object_name: 对象名称/路径
            bucket: bucket名称
        
        Returns:
            文件流对象
        """
        try:
            bucket = bucket or self.bucket_files
            return self.client.get_object(bucket, object_name)
        except S3Error as e:
            logger.error(f"❌ 获取文件流失败 [{object_name}]: {e}")
            return None
    
    def download_file(self, object_name: str, local_path: str, bucket: Optional[str] = None) -> bool:
        """
        下载文件到本地
        
        Args:
            object_name: MinIO 中的文件路径
            local_path: 本地保存路径
            bucket: bucket名称
        
        Returns:
            是否成功
        """
        try:
            bucket = bucket or self.bucket_files
            self.client.fget_object(bucket, object_name, local_path)
            logger.info(f"✅ 文件已下载: {local_path}")
            return True
        except S3Error as e:
            logger.error(f"❌ 下载文件失败 [{object_name}]: {e}")
            return False
    
    def upload_file_from_path(self, object_name: str, local_path: str, content_type: str = None, bucket: Optional[str] = None) -> bool:
        """
        上传本地文件到 MinIO
        
        Args:
            object_name: MinIO 中的目标路径
            local_path: 本地文件路径
            content_type: 文件类型
            bucket: bucket名称
        
        Returns:
            是否成功
        """
        try:
            import os
            bucket = bucket or self.bucket_files
            file_size = os.path.getsize(local_path)
            self.client.fput_object(
                bucket,
                object_name,
                local_path,
                content_type=content_type
            )
            logger.info(f"✅ 文件已上传: {object_name} ({file_size} bytes)")
            return True
        except S3Error as e:
            logger.error(f"❌ 上传文件失败 [{object_name}]: {e}")
            return False
    
    def upload_bytes(self, object_name: str, file_content: bytes, content_type: str = None, bucket: Optional[str] = None) -> bool:
        """
        上传字节内容到 MinIO
        
        Args:
            object_name: MinIO 中的目标路径
            file_content: 文件内容（字节）
            content_type: 文件类型
            bucket: bucket名称
        
        Returns:
            是否成功
        """
        try:
            import io
            bucket = bucket or self.bucket_files
            file_stream = io.BytesIO(file_content)
            file_size = len(file_content)
            self.client.put_object(
                bucket,
                object_name,
                file_stream,
                length=file_size,
                content_type=content_type
            )
            logger.info(f"✅ 内容已上传: {object_name} ({file_size} bytes)")
            return True
        except S3Error as e:
            logger.error(f"❌ 上传内容失败 [{object_name}]: {e}")
            return False
    
    def file_exists(self, object_name: str, bucket: Optional[str] = None) -> bool:
        """
        检查文件是否存在
        
        Args:
            object_name: MinIO 中的文件路径
            bucket: bucket名称
        
        Returns:
            是否存在
        """
        try:
            bucket = bucket or self.bucket_files
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False
    
    def get_file_info(self, object_name: str, bucket: Optional[str] = None) -> Optional[dict]:
        """
        获取文件信息
        
        Args:
            object_name: MinIO 中的文件路径
            bucket: bucket名称
        
        Returns:
            文件信息字典
        """
        try:
            bucket = bucket or self.bucket_files
            stat = self.client.stat_object(bucket, object_name)
            return {
                "size": stat.size,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "etag": stat.etag,
                "bucket": bucket,
                "object_name": object_name
            }
        except S3Error as e:
            logger.error(f"❌ 获取文件信息失败 [{object_name}]: {e}")
            return None
    
    def list_files(self, prefix: str = "", recursive: bool = False, bucket: Optional[str] = None) -> list:
        """
        列出文件
        
        Args:
            prefix: 前缀过滤
            recursive: 是否递归
            bucket: bucket名称
        
        Returns:
            文件列表
        """
        try:
            bucket = bucket or self.bucket_files
            objects = self.client.list_objects(
                bucket,
                prefix=prefix,
                recursive=recursive
            )
            return [
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"❌ 列出文件失败: {e}")
            return []


# 全局MinIO客户端实例
minio_client = MinIOClient()



# 🆕 补充便捷函数（来自 mold_cost-main）
def upload_file_to_minio(bucket_name: str, object_name: str, file_data, content_type: str = None) -> bool:
    """
    上传文件到MinIO（便捷函数）
    
    Args:
        bucket_name: 存储桶名称
        object_name: 对象名称（文件路径）
        file_data: 文件数据（可以是BytesIO或bytes）
        content_type: 内容类型
        
    Returns:
        是否成功
    """
    import io
    
    try:
        # 确保bucket存在
        if not minio_client.client.bucket_exists(bucket_name):
            minio_client.client.make_bucket(bucket_name)
        
        # 处理不同类型的文件数据
        if isinstance(file_data, bytes):
            file_stream = io.BytesIO(file_data)
            file_size = len(file_data)
        elif hasattr(file_data, 'read'):
            # BytesIO或文件对象
            file_data.seek(0)
            file_content = file_data.read()
            file_stream = io.BytesIO(file_content)
            file_size = len(file_content)
        else:
            raise ValueError("file_data必须是bytes或文件对象")
        
        minio_client.client.put_object(
            bucket_name,
            object_name,
            file_stream,
            length=file_size,
            content_type=content_type
        )
        
        logger.info(f"✅ 文件已上传到MinIO: {bucket_name}/{object_name} ({file_size} bytes)")
        return True
        
    except Exception as e:
        logger.error(f"❌ 上传文件到MinIO失败: {e}")
        return False


def get_file_url(bucket_name: str, object_name: str, expires: int = 3600) -> Optional[str]:
    """
    获取文件的预签名URL（便捷函数）
    
    Args:
        bucket_name: 存储桶名称
        object_name: 对象名称（文件路径）
        expires: 过期时间（秒）
        
    Returns:
        预签名URL
    """
    try:
        url = minio_client.presigned_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(seconds=expires)
        )
        return url
    except Exception as e:
        logger.error(f"❌ 获取文件URL失败: {e}")
        return None
