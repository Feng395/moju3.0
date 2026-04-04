"""文件领域端口定义。"""

from __future__ import annotations

from typing import Optional, Protocol


class FileStorageService(Protocol):
    """文件存储服务协议。"""

    def get_file(self, object_name: str, bucket: Optional[str] = None) -> bytes: ...

    def get_file_info(self, object_name: str, bucket: Optional[str] = None) -> Optional[dict]: ...

    def generate_presigned_url(self, object_name: str, bucket: Optional[str] = None) -> str: ...
