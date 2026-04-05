"""CAD 拆图 .x_t 导出 runtime。"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Any, Callable

from ...core.logging import get_logger
from .cad_source_runtime import resolve_prt_source

logger = get_logger(__name__)

XtExporter = Callable[..., dict[str, str]]
NxImporter = Callable[[], Any]


def _default_nx_importer():
    import NXOpen  # noqa: F401

    return NXOpen


def _build_component_map(assembly_part) -> dict[str, tuple[Any, Any]]:
    """把总装组件索引为 leaf_name -> (component, prototype)。"""

    component_map: dict[str, tuple[Any, Any]] = {}
    try:
        components = assembly_part.ComponentAssembly.GetComponents()
    except Exception as exc:
        logger.warning("步骤6: 遍历组件失败: %s", exc)
        return component_map

    for component in components:
        try:
            prototype = component.Prototype
            if prototype is None:
                continue
            leaf_name = Path(prototype.FullPath).stem.lower()
            component_map[leaf_name] = (component, prototype)
        except Exception:
            continue
    return component_map


def _match_component(
    component_map: dict[str, tuple[Any, Any]],
    part_code: str,
) -> tuple[Any, Any] | None:
    normalized_part_code = (part_code or "").lower()
    if not normalized_part_code:
        return None

    matched = component_map.get(normalized_part_code)
    if matched is not None:
        return matched

    for leaf_name, value in component_map.items():
        if leaf_name.startswith(normalized_part_code) or normalized_part_code.startswith(leaf_name):
            return value
    return None


def export_xt_from_prt_with_nxopen(
    *,
    prt_local: str,
    export_files: list[dict[str, Any]],
    temp_dir: str,
    xt_minio_base: str,
    minio_client,
    nx_importer: NxImporter | None = None,
) -> dict[str, str]:
    """从总装 PRT 中按 part_code 导出各子组件 .x_t 并上传到 MinIO。"""

    nxopen = (nx_importer or _default_nx_importer)()
    xt_url_map: dict[str, str] = {}
    session = nxopen.Session.GetSession()
    assembly_part = None

    try:
        opened = session.Parts.Open(prt_local)
        assembly_part = opened[0] if isinstance(opened, tuple) else opened
        session.Parts.SetDisplay(assembly_part, False, False)
        session.Parts.SetWork(assembly_part)
    except Exception as exc:
        logger.warning("步骤6: 打开 PRT 失败: %s", exc)
        return xt_url_map

    try:
        component_map = _build_component_map(assembly_part)
        logger.info("步骤6: 总装包含 %s 个子组件", len(component_map))

        for file_info in export_files:
            sub_code = file_info["sub_code"]
            export_code = file_info.get("part_code") or sub_code
            xt_local = os.path.join(temp_dir, f"{export_code}.x_t")
            xt_minio = f"{xt_minio_base}/{export_code}.x_t"

            matched = _match_component(component_map, export_code)
            if matched is None:
                logger.debug("[%s] 未找到匹配组件 '%s'，跳过", sub_code, export_code.lower())
                continue

            _component, prototype_part = matched
            try:
                exporter = session.DexManager.CreateParasolidExporter()
                exporter.ExportFrom = nxopen.ParasolidExporter.ExportFromOption.ExistingPart
                exporter.InputFile = prototype_part.FullPath
                exporter.OutputFile = xt_local
                exporter.FlattenAssembly = True
                exporter.Commit()
                exporter.Destroy()

                if os.path.exists(xt_local) and minio_client and minio_client.upload_file(xt_local, xt_minio):
                    xt_url_map[sub_code] = xt_minio
                    logger.info("[%s] .x_t 上传成功: %s", sub_code, xt_minio)
                else:
                    logger.warning("[%s] .x_t 文件不存在或上传失败", sub_code)
            except Exception as exc:
                logger.warning("[%s] .x_t 导出失败: %s", sub_code, exc)
    finally:
        try:
            if assembly_part is not None:
                assembly_part.Close(nxopen.BasePart.CloseWholeTree.TrueValue, None)
        except Exception:
            pass

    return xt_url_map


async def export_xt_files(
    *,
    job_id: str,
    temp_dir: str,
    export_files: list[dict[str, Any]],
    storage_manager,
    db_manager,
    minio_client,
    export_xt_from_prt: XtExporter,
    nx_importer: NxImporter | None = None,
) -> dict[str, str]:
    """在 NX 环境可用时，从 PRT 导出子图 .x_t 并上传。"""

    if not export_files or minio_client is None:
        return {}

    try:
        (nx_importer or _default_nx_importer)()
    except ImportError:
        logger.info("步骤6: 非 NX 环境，跳过 .x_t 导出")
        return {}
    except Exception as exc:
        logger.warning("步骤6 NX 环境检测异常（不影响主流程）: %s", exc)
        return {}

    prt_resolution = resolve_prt_source(job_id=job_id, db_manager=db_manager)
    if not prt_resolution:
        logger.info("步骤6: 未提供 PRT 文件，跳过 .x_t 导出")
        return {}

    prt_source = prt_resolution["prt_source"]
    should_use_minio = prt_resolution["use_minio"]
    prt_local = os.path.join(temp_dir, "source.prt")
    prt_ok = await storage_manager.get_file(prt_source, prt_local, use_minio=should_use_minio)
    if not prt_ok:
        logger.warning("步骤6: 下载 PRT 文件失败: %s，跳过 .x_t 导出", prt_source)
        return {}

    timestamp = datetime.now()
    xt_minio_base = f"xt/{timestamp:%Y}/{timestamp:%m}/{job_id}"
    logger.info("步骤6: 检测到 NX 环境，开始从 PRT 导出 .x_t 文件: %s", prt_source)
    return export_xt_from_prt(
        prt_local=prt_local,
        export_files=export_files,
        temp_dir=temp_dir,
        xt_minio_base=xt_minio_base,
        minio_client=minio_client,
    )
