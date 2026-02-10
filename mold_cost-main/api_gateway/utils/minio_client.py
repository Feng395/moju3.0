"""
MinIO 客户端工具
负责文件的上传、下载、删除等操作
"""
import os
from minio import Minio
from minio.error import S3Error
from typing import Optional
import io


class MinIOClient:
    """MinIO 客户端封装类"""
    
    def __init__(self):
        # 从环境变量读取配置
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.use_https = os.getenv("MINIO_USE_HTTPS", "false").lower() == "true"
        self.bucket = os.getenv("MINIO_BUCKET_FILES", "files")
        
        # 初始化 Minio 客户端
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.use_https
        )
        
        # 确保 bucket 存在
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在，不存在则创建"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"✅ 创建存储桶: {self.bucket}")
        except S3Error as e:
            print(f"❌ 检查/创建存储桶失败: {e}")
    
    def get_file(self, file_path: str) -> Optional[bytes]:
        """
        获取文件内容
        
        Args:
            file_path: MinIO 中的文件路径（如 "dwg/2026/01/file.dwg"）
        
        Returns:
            文件内容（字节），失败返回 None
        """
        try:
            response = self.client.get_object(self.bucket, file_path)
            file_content = response.read()
            response.close()
            response.release_conn()
            return file_content
        except S3Error as e:
            print(f"❌ 获取文件失败 [{file_path}]: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取文件异常 [{file_path}]: {e}")
            return None
    
    def get_file_stream(self, file_path: str):
        """
        获取文件流（用于大文件）
        
        Args:
            file_path: MinIO 中的文件路径
        
        Returns:
            文件流对象
        """
        try:
            return self.client.get_object(self.bucket, file_path)
        except S3Error as e:
            print(f"❌ 获取文件流失败 [{file_path}]: {e}")
            return None
    
    def download_file(self, file_path: str, local_path: str) -> bool:
        """
        下载文件到本地
        
        Args:
            file_path: MinIO 中的文件路径
            local_path: 本地保存路径
        
        Returns:
            是否成功
        """
        try:
            self.client.fget_object(self.bucket, file_path, local_path)
            print(f"✅ 文件已下载: {local_path}")
            return True
        except S3Error as e:
            print(f"❌ 下载文件失败 [{file_path}]: {e}")
            return False
    
    def upload_file(self, file_path: str, local_path: str, content_type: str = None) -> bool:
        """
        上传本地文件到 MinIO
        
        Args:
            file_path: MinIO 中的目标路径
            local_path: 本地文件路径
            content_type: 文件类型
        
        Returns:
            是否成功
        """
        try:
            file_size = os.path.getsize(local_path)
            self.client.fput_object(
                self.bucket,
                file_path,
                local_path,
                content_type=content_type
            )
            print(f"✅ 文件已上传: {file_path} ({file_size} bytes)")
            return True
        except S3Error as e:
            print(f"❌ 上传文件失败 [{file_path}]: {e}")
            return False
    
    def upload_bytes(self, file_path: str, file_content: bytes, content_type: str = None) -> bool:
        """
        上传字节内容到 MinIO
        
        Args:
            file_path: MinIO 中的目标路径
            file_content: 文件内容（字节）
            content_type: 文件类型
        
        Returns:
            是否成功
        """
        try:
            file_stream = io.BytesIO(file_content)
            file_size = len(file_content)
            self.client.put_object(
                self.bucket,
                file_path,
                file_stream,
                length=file_size,
                content_type=content_type
            )
            print(f"✅ 内容已上传: {file_path} ({file_size} bytes)")
            return True
        except S3Error as e:
            print(f"❌ 上传内容失败 [{file_path}]: {e}")
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: MinIO 中的文件路径
        
        Returns:
            是否成功
        """
        try:
            self.client.remove_object(self.bucket, file_path)
            print(f"✅ 文件已删除: {file_path}")
            return True
        except S3Error as e:
            print(f"❌ 删除文件失败 [{file_path}]: {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: MinIO 中的文件路径
        
        Returns:
            是否存在
        """
        try:
            self.client.stat_object(self.bucket, file_path)
            return True
        except S3Error:
            return False
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        获取文件信息
        
        Args:
            file_path: MinIO 中的文件路径
        
        Returns:
            文件信息字典
        """
        try:
            stat = self.client.stat_object(self.bucket, file_path)
            return {
                "size": stat.size,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "etag": stat.etag,
                "bucket": self.bucket,
                "object_name": file_path
            }
        except S3Error as e:
            print(f"❌ 获取文件信息失败 [{file_path}]: {e}")
            return None
    
    def get_presigned_url(self, file_path: str, expires_seconds: int = 3600) -> Optional[str]:
        """
        生成预签名下载 URL
        
        Args:
            file_path: MinIO 中的文件路径
            expires_seconds: 过期时间（秒），默认 1 小时
        
        Returns:
            预签名 URL
        """
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket,
                file_path,
                expires=timedelta(seconds=expires_seconds)
            )
            return url
        except S3Error as e:
            print(f"❌ 生成预签名 URL 失败 [{file_path}]: {e}")
            return None
    
    def list_files(self, prefix: str = "", recursive: bool = False) -> list:
        """
        列出文件
        
        Args:
            prefix: 前缀过滤
            recursive: 是否递归
        
        Returns:
            文件列表
        """
        try:
            objects = self.client.list_objects(
                self.bucket,
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
            print(f"❌ 列出文件失败: {e}")
            return []


# 全局单例
minio_client = MinIOClient()


# 便捷函数
def upload_file_to_minio(bucket_name: str, object_name: str, file_data, content_type: str = None) -> bool:
    """
    上传文件到MinIO
    
    Args:
        bucket_name: 存储桶名称
        object_name: 对象名称（文件路径）
        file_data: 文件数据（可以是BytesIO或bytes）
        content_type: 内容类型
        
    Returns:
        是否成功
    """
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
        
        print(f"✅ 文件已上传到MinIO: {bucket_name}/{object_name} ({file_size} bytes)")
        return True
        
    except Exception as e:
        print(f"❌ 上传文件到MinIO失败: {e}")
        return False


def get_file_url(bucket_name: str, object_name: str, expires: int = 3600) -> Optional[str]:
    """
    获取文件的预签名URL
    
    Args:
        bucket_name: 存储桶名称
        object_name: 对象名称（文件路径）
        expires: 过期时间（秒）
        
    Returns:
        预签名URL
    """
    try:
        from datetime import timedelta
        url = minio_client.client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(seconds=expires)
        )
        return url
    except Exception as e:
        print(f"❌ 获取文件URL失败: {e}")
        return None
