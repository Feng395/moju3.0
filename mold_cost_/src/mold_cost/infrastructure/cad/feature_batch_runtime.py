"""批量特征识别 runtime。"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Callable

from ...core.logging import get_logger
from .feature_analysis_runtime import analyze_dxf_features

logger = get_logger(__name__)


def batch_feature_recognition(
    job_id: str,
    subgraph_id: str | None = None,
    progress_callback=None,
    *,
    get_subgraphs: Callable[[str, str | None], list[dict[str, Any]]],
    save_features: Callable[[str, str, dict[str, Any]], bool],
    minio_client,
    slider_red_face_updater: Callable[..., Any] | None = None,
    db_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """执行批量特征识别，并把 legacy DB helper 保持为可注入依赖。"""

    try:
        # 中文说明：DB 查询与保存能力从外部注入，便于逐步替换掉 legacy helper。
        subgraphs = get_subgraphs(job_id, subgraph_id)
        if not subgraphs:
            return {
                "success": False,
                "message": f"未找到子图: job_id={job_id}, subgraph_id={subgraph_id}",
            }

        with tempfile.TemporaryDirectory(prefix="feature_batch_") as temp_dir:
            download_tasks = []
            subgraph_map: dict[str, dict[str, Any]] = {}
            for subgraph in subgraphs:
                sg_id = subgraph["subgraph_id"]
                file_url = subgraph["subgraph_file_url"]
                temp_dxf = os.path.join(temp_dir, f"{sg_id}.dxf")
                download_tasks.append((sg_id, file_url, temp_dxf))
                subgraph_map[sg_id] = {
                    "part_code": subgraph.get("part_code"),
                    "xt_file_url": subgraph.get("xt_file_url"),
                }

            max_workers = int(os.getenv("MINIO_DOWNLOAD_WORKERS", "5"))
            download_results = minio_client.batch_get_files(download_tasks, max_workers=max_workers)
            results = []
            success_count = 0
            failed_count = 0
            total_count = len(download_results)

            def _emit_progress() -> None:
                if progress_callback is None:
                    return
                try:
                    progress_callback(len(results), total_count, success_count, failed_count)
                except Exception as callback_error:
                    logger.warning("feature progress callback failed: %s", callback_error)

            for sg_id, download_result in download_results.items():
                part_code = subgraph_map.get(sg_id, {}).get("part_code")
                if not download_result.get("success"):
                    results.append(
                        {
                            "subgraph_id": sg_id,
                            "part_code": part_code,
                            "success": False,
                            "message": f"下载失败: {download_result.get('error', '未知错误')}",
                        }
                    )
                    failed_count += 1
                    _emit_progress()
                    continue

                try:
                    # 中文说明：单文件分析已经迁到 src runtime，批处理这里只负责编排与落库。
                    features = analyze_dxf_features(download_result["save_path"])
                    if features is None:
                        results.append(
                            {
                                "subgraph_id": sg_id,
                                "part_code": part_code,
                                "success": False,
                                "message": "特征识别失败",
                            }
                        )
                        failed_count += 1
                        _emit_progress()
                        continue

                    save_success = save_features(
                        sg_id,
                        job_id,
                        {
                            **features,
                            "part_code": part_code,
                        },
                    )
                    if save_success:
                        results.append(
                            {
                                "subgraph_id": sg_id,
                                "part_code": part_code,
                                "success": True,
                                "features": features,
                            }
                        )
                        success_count += 1
                        # 中文说明：滑块红面补偿仍沿用旧逻辑，但触发条件与入口已经收口到 src。
                        _maybe_update_slider_red_face(
                            subgraph_id=sg_id,
                            job_id=job_id,
                            features=features,
                            xt_file_url=subgraph_map.get(sg_id, {}).get("xt_file_url"),
                            minio_client=minio_client,
                            slider_red_face_updater=slider_red_face_updater,
                            db_config=db_config,
                        )
                    else:
                        results.append(
                            {
                                "subgraph_id": sg_id,
                                "part_code": part_code,
                                "success": False,
                                "message": "保存到数据库失败",
                            }
                        )
                        failed_count += 1
                except Exception as exc:
                    logger.error("feature batch item failed: subgraph_id=%s error=%s", sg_id, exc, exc_info=True)
                    results.append(
                        {
                            "subgraph_id": sg_id,
                            "part_code": part_code,
                            "success": False,
                            "message": str(exc),
                        }
                    )
                    failed_count += 1

                _emit_progress()

            return {
                "success": True,
                "data": {
                    "total": total_count,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "results": results,
                },
            }
    except Exception as exc:
        logger.error("feature batch runtime failed: %s", exc, exc_info=True)
        return {
            "success": False,
            "message": f"服务错误: {exc}",
        }


def _maybe_update_slider_red_face(
    *,
    subgraph_id: str,
    job_id: str,
    features: dict[str, Any],
    xt_file_url: str | None,
    minio_client,
    slider_red_face_updater: Callable[..., Any] | None,
    db_config: dict[str, Any] | None,
) -> None:
    """仅当识别到滑块红面且上下文完整时，补触发 legacy 后处理。"""
    if slider_red_face_updater is None or not xt_file_url or not db_config:
        return

    # 中文说明：只有识别结果中出现滑块相关线切割指令时，才触发额外红面修正。
    wire_cut_details = features.get("wire_cut_details") or []
    has_slider = any("滑" in str(detail.get("instruction", "")) for detail in wire_cut_details)
    if not has_slider:
        return

    try:
        slider_red_face_updater(
            subgraph_id=subgraph_id,
            job_id=job_id,
            xt_file_url=xt_file_url,
            db_config=db_config,
            minio_client=minio_client,
        )
    except Exception as exc:
        logger.warning("slider red-face update failed: subgraph_id=%s error=%s", subgraph_id, exc)
