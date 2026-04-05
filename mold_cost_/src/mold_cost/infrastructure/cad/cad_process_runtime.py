"""CAD 拆图主流程编排 runtime。"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Awaitable, Callable

from ...core.logging import get_logger
from .cad_analysis_runtime import analyze_and_export_subgraphs
from .cad_material_line_runtime import process_material_lines
from .cad_prepare_runtime import prepare_dxf_input
from .cad_source_runtime import resolve_dwg_source
from .cad_split_persistence_runtime import persist_split_results
from .cad_upload_runtime import upload_split_files
from .cad_xt_export_runtime import export_xt_files

logger = get_logger(__name__)

NowFactory = Callable[[], datetime]
AnalyzeAndExport = Callable[..., dict[str, Any]]
ProcessMaterialLines = Callable[..., dict[str, Any]]
UploadSplitFiles = Callable[..., dict[str, Any]]
ExportXtFiles = Callable[..., Awaitable[dict[str, str]]]
PersistSplitResults = Callable[..., dict[str, Any]]


async def run_cad_process_pipeline(
    *,
    job_id: str,
    temp_dxf: str,
    temp_dir: str,
    minio_base_path: str,
    source_filename: str,
    minio_client,
    db_manager,
    storage_manager,
    analysis_system_factory,
    material_line_available: bool,
    integrator_factory,
    resolve_subgraph_lwt,
    save_debug_files,
    export_xt_from_prt,
    analyze_and_export: AnalyzeAndExport,
    process_material_lines_fn: ProcessMaterialLines,
    upload_split_files_fn: UploadSplitFiles,
    export_xt_files_fn: ExportXtFiles,
    persist_split_results_fn: PersistSplitResults,
    now_factory: NowFactory = datetime.now,
) -> dict[str, Any]:
    """组织 CAD 主流程中稳定的识别、板料线、上传与落库编排。"""

    analysis_system = analysis_system_factory()
    analysis_time = 0.0
    export_time = 0.0
    material_line_time = 0.0
    upload_time = 0.0
    db_time = 0.0
    total_start = now_factory()

    try:
        analysis_result = analyze_and_export(
            analysis_system=analysis_system,
            temp_dxf=temp_dxf,
            temp_dir=temp_dir,
            minio_base_path=minio_base_path,
        )
        analysis_time = analysis_result.get("analysis_time", 0.0)
        export_time = analysis_result.get("export_time", 0.0)
        if not analysis_result["success"]:
            return {"success": False, "message": analysis_result["message"]}

        all_regions = analysis_result["all_regions"]
        region_info_list = analysis_result["region_info_list"]
        region_info_map = analysis_result["region_info_map"]
        failed_recognition_count = analysis_result["failed_recognition_count"]
        failed_export_count = analysis_result["failed_export_count"]
        export_files = analysis_result["export_files"]

        material_line_start = now_factory()
        material_line_result = process_material_lines_fn(
            job_id=job_id,
            export_files=export_files,
            region_info_map=region_info_map,
            material_line_available=material_line_available,
            integrator_factory=integrator_factory,
            resolve_subgraph_lwt=resolve_subgraph_lwt,
            save_debug_files=save_debug_files,
        )
        material_line_time = (
            (now_factory() - material_line_start).total_seconds() if material_line_result["processed"] else 0.0
        )

        upload_start = now_factory()
        upload_results = upload_split_files_fn(
            export_files=export_files,
            minio_client=minio_client,
        )
        upload_time = (now_factory() - upload_start).total_seconds()

        db_start = now_factory()
        try:
            # 中文说明：.x_t 导出 runtime 已下沉到 src，这里仍允许注入 legacy exporter 本体。
            xt_url_map = await export_xt_files_fn(
                job_id=job_id,
                temp_dir=temp_dir,
                export_files=export_files,
                storage_manager=storage_manager,
                db_manager=db_manager,
                minio_client=minio_client,
                export_xt_from_prt=export_xt_from_prt,
            )
        except Exception as exc:
            logger.warning("步骤6 .x_t 导出异常（不影响主流程）: %s", exc)
            xt_url_map = {}

        persistence_result = persist_split_results_fn(
            export_files=export_files,
            upload_results=upload_results,
            db_manager=db_manager,
            source_filename=source_filename,
            job_id=job_id,
            xt_url_map=xt_url_map,
        )
        result_files = persistence_result["result_files"]
        db_success_count = persistence_result["db_success_count"]
        failed_upload_count = persistence_result["failed_upload_count"]
        failed_db_count = persistence_result["failed_db_count"]
        db_time = (now_factory() - db_start).total_seconds()

        total_time = (now_factory() - total_start).total_seconds()
        avg_time = total_time / len(result_files) if result_files else 0.0
        return {
            "success": True,
            "all_regions": all_regions,
            "region_info_list": region_info_list,
            "export_files": export_files,
            "failed_recognition_count": failed_recognition_count,
            "failed_export_count": failed_export_count,
            "result_files": result_files,
            "db_success_count": db_success_count,
            "failed_upload_count": failed_upload_count,
            "failed_db_count": failed_db_count,
            "analysis_time": analysis_time,
            "export_time": export_time,
            "material_line_time": material_line_time,
            "upload_time": upload_time,
            "db_time": db_time,
            "total_time": total_time,
            "avg_time": avg_time,
        }
    except Exception as exc:
        logger.error("CAD process pipeline failed: job_id=%s error=%s", job_id, exc, exc_info=True)
        return {"success": False, "message": f"处理失败: {exc}"}
    finally:
        try:
            analysis_system.clear_cache()
        except Exception as exc:
            logger.warning("清理 CAD analysis cache 失败: %s", exc)


async def execute_cad_split_process(
    *,
    dwg_url: str | None,
    job_id: str,
    db_manager,
    storage_manager,
    minio_client,
    extract_model_code_from_source,
    converter_factory,
    oda_converter_path: str | None,
    analysis_system_factory,
    material_line_available: bool,
    integrator_factory,
    resolve_subgraph_lwt,
    save_debug_files,
    export_xt_from_prt,
    now_factory: NowFactory = datetime.now,
) -> dict[str, Any]:
    """衔接 legacy 入口与 src pipeline，统一处理来源解析、准备与临时目录清理。"""

    source_resolution = resolve_dwg_source(
        dwg_url=dwg_url,
        job_id=job_id,
        db_manager=db_manager,
        extract_model_code_from_source=extract_model_code_from_source,
    )
    if not source_resolution:
        return {"status": "error", "message": f"未找到 job_id={job_id} 对应的 dwg_file_path"}

    temp_dir = tempfile.mkdtemp(prefix="chaidan_cad_")
    try:
        prepare_result = await prepare_dxf_input(
            dwg_source=source_resolution["dwg_source"],
            use_minio=source_resolution["use_minio"],
            temp_dir=temp_dir,
            storage_manager=storage_manager,
            converter_factory=converter_factory,
            oda_converter_path=oda_converter_path,
        )
        if not prepare_result["success"]:
            return {"status": "error", "message": prepare_result["message"]}

        current_time = now_factory()
        pipeline_result = await run_cad_process_pipeline(
            job_id=job_id,
            temp_dxf=prepare_result["temp_dxf"],
            temp_dir=temp_dir,
            minio_base_path=f"dxf/{current_time:%Y}/{current_time:%m}/{job_id}",
            source_filename=source_resolution["source_filename"],
            minio_client=minio_client,
            db_manager=db_manager,
            storage_manager=storage_manager,
            analysis_system_factory=analysis_system_factory,
            material_line_available=material_line_available,
            integrator_factory=integrator_factory,
            resolve_subgraph_lwt=resolve_subgraph_lwt,
            save_debug_files=save_debug_files,
            export_xt_from_prt=export_xt_from_prt,
            analyze_and_export=analyze_and_export_subgraphs,
            process_material_lines_fn=process_material_lines,
            upload_split_files_fn=upload_split_files,
            export_xt_files_fn=export_xt_files,
            persist_split_results_fn=persist_split_results,
            now_factory=now_factory,
        )
        if not pipeline_result["success"]:
            return {"status": "error", "message": pipeline_result["message"]}

        result_files = pipeline_result["result_files"]
        return {
            "status": "ok",
            "data": {
                "total_count": len(result_files),
                "result_files": [item["filename"] for item in result_files],
            },
        }
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as exc:
                logger.warning("清理 CAD 临时目录失败: %s", exc)
