"""CAD 拆图输入文件准备 runtime。"""

from __future__ import annotations

import os
from typing import Any, Callable

from ...core.logging import get_logger

logger = get_logger(__name__)

ConverterFactory = Callable[[str | None], Any]


async def prepare_dxf_input(
    *,
    dwg_source: str,
    use_minio: bool,
    temp_dir: str,
    storage_manager,
    converter_factory: ConverterFactory,
    oda_converter_path: str | None,
) -> dict[str, Any]:
    """下载 DWG 并转换为 DXF，供后续拆图分析阶段使用。"""

    temp_dwg = os.path.join(temp_dir, "input.dwg")
    temp_dxf = os.path.join(temp_dir, "input.dxf")

    # 中文说明：文件获取与格式转换属于稳定准备阶段，单独抽成 runtime 便于后续继续替换 storage/converter。
    if not await storage_manager.get_file(dwg_source, temp_dwg, use_minio=use_minio):
        return {
            "success": False,
            "message": "获取 DWG 文件失败",
            "temp_dwg": temp_dwg,
            "temp_dxf": temp_dxf,
        }

    converter = converter_factory(oda_converter_path)
    if not converter.convert_dwg_to_dxf(temp_dwg, temp_dxf):
        return {
            "success": False,
            "message": "DWG -> DXF 转换失败",
            "temp_dwg": temp_dwg,
            "temp_dxf": temp_dxf,
        }

    logger.info("CAD prepare runtime finished: dwg_source=%s temp_dxf=%s", dwg_source, temp_dxf)
    return {
        "success": True,
        "temp_dwg": temp_dwg,
        "temp_dxf": temp_dxf,
    }
