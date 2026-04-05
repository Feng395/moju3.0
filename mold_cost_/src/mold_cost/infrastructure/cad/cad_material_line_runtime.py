"""CAD 板料线后处理 runtime。"""

from __future__ import annotations

import os
from typing import Any, Callable

from ...core.logging import get_logger

logger = get_logger(__name__)

LwtResolver = Callable[[str, dict[str, Any] | None], tuple[dict[str, float] | None, str]]
DebugSaver = Callable[[str, list[dict[str, Any]]], str | None]
IntegratorFactory = Callable[..., Any]


def _env_flag(name: str, default: str) -> bool:
    value = os.getenv(name, default)
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def _build_part_info(file_info: dict[str, Any], lwt_source: str) -> dict[str, Any]:
    return {
        "part_name": file_info.get("part_name"),
        "part_code": file_info.get("part_code"),
        "lwt_source": lwt_source,
    }


def process_material_lines(
    *,
    job_id: str,
    export_files: list[dict[str, Any]],
    region_info_map: dict[str, dict[str, Any]],
    material_line_available: bool,
    integrator_factory: IntegratorFactory,
    resolve_subgraph_lwt: LwtResolver,
    save_debug_files: DebugSaver | None = None,
) -> dict[str, Any]:
    """为导出的子图补板料线，并在需要时保存调试副本。"""

    if not export_files:
        return {"processed": False, "debug_output_dir": None}

    enable_material_lines = _env_flag("ENABLE_MATERIAL_LINES", "true")
    if not enable_material_lines:
        logger.info("CAD material-line runtime skipped: ENABLE_MATERIAL_LINES=false")
        return {"processed": False, "debug_output_dir": None}
    if not material_line_available:
        logger.warning("CAD material-line runtime skipped: integrator unavailable")
        return {"processed": False, "debug_output_dir": None}

    try:
        integrator = integrator_factory(enable=True)
        for file_info in export_files:
            try:
                region_info = region_info_map.get(file_info["sub_code"], {})
                region = region_info.get("region")
                lwt, lwt_source = resolve_subgraph_lwt(file_info["local_path"], region)
                if not lwt:
                    logger.debug("CAD material-line runtime missing lwt: sub_code=%s", file_info["sub_code"])
                    continue

                integrator.add_material_lines_to_subgraph(
                    dxf_path=file_info["local_path"],
                    lwt=lwt,
                    sub_code=file_info["sub_code"],
                    part_info=_build_part_info(file_info, lwt_source),
                )
            except Exception as exc:
                logger.warning("CAD material-line item failed: sub_code=%s error=%s", file_info.get("sub_code"), exc)

        integrator.print_stats()
    except Exception as exc:
        logger.warning("CAD material-line runtime failed: %s", exc)
        return {"processed": False, "debug_output_dir": None}

    debug_output_dir = None
    if save_debug_files is not None and _env_flag("SAVE_MATERIAL_LINE_DEBUG_FILES", "true"):
        try:
            debug_output_dir = save_debug_files(job_id, export_files)
        except Exception as exc:
            logger.warning("CAD material-line debug save failed: %s", exc)

    return {
        "processed": True,
        "debug_output_dir": debug_output_dir,
    }
