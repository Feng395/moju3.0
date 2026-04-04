"""特征识别领域服务。"""

from __future__ import annotations

import asyncio
import csv
import glob
import os
import time
from collections.abc import Sequence
from typing import Any

from ..ports import FeatureRecognitionGateway, ProgressCallback


class LegacyFeatureRecognitionService:
    """统一承接 feature 外部入口的领域服务。

    中文说明：API、MCP、worker 都应该优先调用这里，
    而不是继续直接依赖 scripts 或其他接口层对象。
    """

    def __init__(self, gateway: FeatureRecognitionGateway):
        self._gateway = gateway

    async def recognize(self, context: dict[str, Any]) -> dict[str, Any]:
        """兼容旧调用方的异步入口。"""
        # 中文说明：旧实现是同步批处理函数，这里统一包一层 async 适配。
        return await asyncio.to_thread(
            self.batch_recognize,
            context.get("job_id"),
            context.get("subgraph_id"),
            context.get("progress_callback"),
        )

    async def reprocess(
        self,
        job_id: str,
        subgraph_ids: Sequence[str] | None = None,
        force_reprocess: bool = True,
    ) -> dict[str, Any]:
        """按稳定 service API 重新执行特征识别。"""
        if not job_id:
            return {"status": "error", "message": "缺少 job_id", "error_code": "MISSING_JOB_ID"}

        # 中文说明：如果外层没传 subgraph_ids，则由领域服务自行解析目标子图。
        target_ids = list(dict.fromkeys(subgraph_ids or self._resolve_subgraph_ids(job_id)))
        if not target_ids:
            return {"status": "error", "message": "缺少 subgraph_ids", "error_code": "MISSING_SUBGRAPH_IDS"}

        tasks = [self._reprocess_single(job_id, subgraph_id) for subgraph_id in target_ids]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        failed_count = 0
        results: list[dict[str, Any]] = []

        for subgraph_id, item in zip(target_ids, raw_results):
            if isinstance(item, Exception):
                normalized = {
                    "subgraph_id": subgraph_id,
                    "status": "failed",
                    "error": str(item),
                    "duration_ms": 0,
                }
            else:
                normalized = item

            if normalized.get("status") == "success":
                success_count += 1
            else:
                failed_count += 1
            results.append(normalized)

        return {
            "status": "ok",
            "message": f"批量特征识别完成: 成功{success_count}个, 失败{failed_count}个",
            "total": len(target_ids),
            "success": success_count,
            "failed": failed_count,
            "results": results,
            "force_reprocess": force_reprocess,
        }

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """通过注入的 gateway 执行 legacy 批量识别。"""
        return self._gateway.batch_recognize(job_id, subgraph_id, progress_callback)

    def analyze_dxf(self, dxf_path: str) -> dict[str, Any] | None:
        return self._gateway.analyze_dxf(dxf_path)

    def get_subgraphs(self, job_id: str, subgraph_id: str | None = None) -> list[dict[str, Any]]:
        return self._gateway.get_subgraphs(job_id, subgraph_id)

    def save_features(self, subgraph_id: str, job_id: str, features: dict[str, Any]) -> bool:
        return self._gateway.save_features(subgraph_id, job_id, features)

    def upload_feature_database(self, csv_folder: str, minio_path: str | None = None) -> dict[str, Any]:
        """构建并上传滑块特征库。"""
        folder = os.path.abspath(csv_folder)
        if not os.path.isdir(folder):
            raise ValueError(f"文件夹不存在: {folder}")

        csv_path = self._find_latest_feature_csv(folder)
        if csv_path is None:
            raise FileNotFoundError(f"未找到识别报告 CSV: {folder}")

        database = self._build_feature_database(csv_path)
        if not database:
            raise ValueError("CSV 中没有有效的红色面数据")

        target_path = minio_path or os.getenv(
            "SLIDER_FEATURE_DB_MINIO_PATH",
            "slider/feature_database.json",
        )
        # 中文说明：真正上传交给 gateway，service 只负责校验与组装数据。
        self._gateway.upload_feature_database(database, target_path)
        return {
            "success": True,
            "message": f"上传成功，共 {len(database)} 条记录",
            "minio_path": target_path,
            "csv_source": csv_path,
        }

    async def _reprocess_single(self, job_id: str, subgraph_id: str) -> dict[str, Any]:
        # 中文说明：单子图仍复用 legacy batch 接口，只在 service 内规范结果结构。
        started_at = time.perf_counter()
        raw_result = await asyncio.to_thread(self.batch_recognize, job_id, subgraph_id)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        return self._normalize_reprocess_result(subgraph_id, raw_result, duration_ms)

    def _normalize_reprocess_result(
        self,
        subgraph_id: str,
        raw_result: dict[str, Any],
        duration_ms: int,
    ) -> dict[str, Any]:
        if not raw_result.get("success"):
            return {
                "subgraph_id": subgraph_id,
                "status": "failed",
                "error": raw_result.get("message", "特征识别失败"),
                "duration_ms": duration_ms,
            }

        result_items = raw_result.get("data", {}).get("results", [])
        if result_items:
            matched = next(
                (item for item in result_items if item.get("subgraph_id") == subgraph_id),
                result_items[0],
            )
            payload = {
                "subgraph_id": subgraph_id,
                "duration_ms": duration_ms,
            }
            if matched.get("success"):
                payload["status"] = "success"
                payload["features"] = matched.get("features", {})
            else:
                payload["status"] = "failed"
                payload["error"] = matched.get("message", "特征识别失败")
            if matched.get("part_code"):
                payload["part_code"] = matched["part_code"]
            return payload

        return {
            "subgraph_id": subgraph_id,
            "status": "success",
            "features": raw_result.get("data", {}),
            "duration_ms": duration_ms,
        }

    def _resolve_subgraph_ids(self, job_id: str) -> list[str]:
        # 中文说明：统一从 gateway 查询待处理子图，避免上层自己碰数据库脚本逻辑。
        subgraphs = self.get_subgraphs(job_id)
        return [item["subgraph_id"] for item in subgraphs if item.get("subgraph_id")]

    @staticmethod
    def _find_latest_feature_csv(folder: str) -> str | None:
        pattern = os.path.join(folder, "特征面识别报告_增强特*.csv")
        csv_files = sorted(glob.glob(pattern), key=os.path.getmtime)
        return csv_files[-1] if csv_files else None

    @staticmethod
    def _build_feature_database(csv_path: str) -> dict[str, Any]:
        # 中文说明：保留 legacy 上传格式，供旧滑块红色面查找逻辑继续复用。
        database: dict[str, Any] = {}
        with open(csv_path, "r", encoding="utf-8-sig") as file_obj:
            reader = csv.DictReader(file_obj)
            for row in reader:
                part_name = row.get("零件名", "").strip()
                if not part_name:
                    continue
                if any("\u4e00" <= char <= "\u9fff" for char in part_name):
                    continue

                red_count_str = row.get("红色面数量", "0").strip()
                area_str = row.get("总表面积(mm2)", "0").strip()
                red_count = int(red_count_str) if red_count_str.isdigit() else 0
                if red_count == 0:
                    continue

                try:
                    total_area = float(area_str)
                except ValueError:
                    total_area = 0.0

                slider_result = row.get("识别结果", "").strip()
                code = "滑块" if slider_result not in ("", "未识别") else "none"
                database[part_name] = {
                    "wire_cut_details": [
                        {
                            "code": code,
                            "cone": "f",
                            "view": "front_view",
                            "area_num": red_count,
                            "instruction": f"{red_count} -红色面",
                            "slider_angle": 0,
                            "total_length": round(total_area, 3),
                            "is_additional": False,
                            "matched_count": red_count,
                            "single_length": round(total_area / red_count, 3) if red_count else 0.0,
                            "expected_count": red_count,
                            "matched_line_ids": [],
                            "overlapping_length": 0.0,
                        }
                    ]
                }
        return database
