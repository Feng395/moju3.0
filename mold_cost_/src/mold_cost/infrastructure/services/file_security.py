"""文件校验与加密适配层。"""

from __future__ import annotations

from fastapi import UploadFile


async def validate_dwg_file(file: UploadFile | None):
    """校验 DWG 文件。"""
    from api_gateway.utils.validators import validate_dwg_file as legacy_validate_dwg_file

    return await legacy_validate_dwg_file(file)


async def validate_prt_file(file: UploadFile | None):
    """校验 PRT 文件。"""
    from api_gateway.utils.validators import validate_prt_file as legacy_validate_prt_file

    return await legacy_validate_prt_file(file)


async def process_file_encryption(file: UploadFile, encryption_key: str | None = None) -> UploadFile:
    """处理文件加密/解密。"""
    from api_gateway.utils.encryption import process_file_encryption as legacy_process_file_encryption

    return await legacy_process_file_encryption(file, encryption_key)

