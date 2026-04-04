"""特征识别领域服务。"""

from __future__ import annotations

import asyncio
import csv
import glob
import os
import time
from collections.abc import Sequence
from typing import Any

from ...cad.ports import ServiceArtifactRef, ServiceError, ServiceSummary
from ..ports import FeatureRecognitionGateway, FeatureRecognitionItem, FeatureRecognitionResult, ProgressCallback


class LegacyFeatureRecognitionService:
    """统一承接 feature 外部入口的领域服务。

    中文说明：API、workflow、worker 优先调用这里，
    而不是继续直接依赖 scripts 或其它接口层对象。
    """

    def __init__(self, gateway: FeatureRecognitionGateway):
        self._gateway = gateway

    async def recognize(self, context: dict[str, Any]) -> FeatureRecognitionResult:
        """兼容旧调用方的异步入口。"""
        if not context.get("job_id"):
            return self._build_error_result(
                job_id=None,
                code="MISSING_JOB_ID",
                message="缺少 job_id",
                requested_subgraph_id=context.get("subgraph_id"),
            )

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
    ) -> FeatureRecognitionResult:
        """按稳定 service API 重新执行特征识别。"""
        if not job_id:
            return self._build_error_result(
                job_id=None,
                code="MISSING_JOB_ID",
                message="缺少 job_id",
            )

        # 中文说明：如果外层没传 subgraph_ids，则由领域服务自行解析目标子图。
        target_ids = list(dict.fromkeys(subgraph_ids or self._resolve_subgraph_ids(job_id)))
        if not target_ids:
            return self._build_error_result(
                job_id=job_id,
                code="MISSING_SUBGRAPH_IDS",
                message="缺少 subgraph_ids",
            )

        tasks = [self._reprocess_single(job_id, subgraph_id) for subgraph_id in target_ids]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[FeatureRecognitionItem] = []
        success_count = 0
        failed_count = 0
        artifacts: list[ServiceArtifactRef] = []
        failed_ids: list[str] = []

        for subgraph_id, item in zip(target_ids, raw_results):
            if isinstance(item, Exception):
                normalized: FeatureRecognitionItem = {
                    "subgraph_id": subgraph_id,
                    "success": False,
                    "status": "failed",
                    "message": f"特征识别调用异常: {item}",
                    "error": str(item),
                    "duration_ms": 0,
                }
            else:
                normalized = item

            if normalized.get("success"):
                success_count += 1
                artifact = normalized.get("artifact")
                if artifact:
                    artifacts.append(artifact)
            else:
                failed_count += 1
                if normalized.get("subgraph_id"):
                    failed_ids.append(normalized["subgraph_id"])
            results.append(normalized)

        summary = self._build_summary(
            operation="feature_recognition",
            job_id=job_id,
            requested_count=len(target_ids),
            total_count=len(target_ids),
            success_count=success_count,
            failed_count=failed_count,
            artifact_count=len(artifacts),
            failed_ids=failed_ids,
            mode="reprocess",
        )

        return {
            "status": "ok",
            "success": failed_count == 0,
            "message": f"批量特征识别完成: 成功 {success_count} 个, 失败 {failed_count} 个",
            "job_id": job_id,
            "operation": "feature_recognition",
            "requested_subgraph_id": None,
            "data": {
                "total": len(target_ids),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
                "force_reprocess": force_reprocess,
            },
            "summary": summary,
            "artifacts": artifacts,
            "error": None,
        }

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> FeatureRecognitionResult:
        """通过注入的 gateway 执行 legacy 批量识别，并归一化返回结构。"""
        if not job_id:
            return self._build_error_result(
                job_id=None,
                code="MISSING_JOB_ID",
                message="缺少 job_id",
                requested_subgraph_id=subgraph_id,
            )

        try:
            raw_result = self._gateway.batch_recognize(job_id, subgraph_id, progress_callback)
        except Exception as exc:
            return self._build_error_result(
                job_id=job_id,
                code="FEATURE_RECOGNITION_GATEWAY_ERROR",
                message=f"特征识别调用异常: {exc}",
                requested_subgraph_id=subgraph_id,
                retryable=True,
            )

        if not raw_result.get("success"):
            message = raw_result.get("message", "特征识别失败")
            return self._build_error_result(
                job_id=job_id,
                code=self._resolve_error_code(message),
                message=message,
                requested_subgraph_id=subgraph_id,
            )

        raw_data = raw_result.get("data") or {}
        raw_items = raw_data.get("results", [])
        source_map = self._build_subgraph_source_map(job_id, subgraph_id) if raw_items else {}
        results = [self._normalize_batch_item(job_id, item, source_map.get(item.get("subgraph_id"))) for item in raw_items]

        success_count = raw_data.get("success_count")
        if not isinstance(success_count, int):
            success_count = sum(1 for item in results if item.get("success"))

        failed_count = raw_data.get("failed_count")
        if not isinstance(failed_count, int):
            failed_count = sum(1 for item in results if not item.get("success"))

        total_count = raw_data.get("total")
        if not isinstance(total_count, int):
            total_count = len(results) or success_count + failed_count

        artifacts = [item["artifact"] for item in results if item.get("artifact")]
        failed_ids = [item["subgraph_id"] for item in results if not item.get("success") and item.get("subgraph_id")]
        summary = self._build_summary(
            operation="feature_recognition",
            job_id=job_id,
            requested_count=1 if subgraph_id else total_count,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            artifact_count=len(artifacts),
            failed_ids=failed_ids,
            mode="batch",
        )

        return {
            "status": "ok",
            "success": True,
            "message": raw_result.get("message", "特征识别完成"),
            "job_id": job_id,
            "operation": "feature_recognition",
            "requested_subgraph_id": subgraph_id,
            "data": {
                "total": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
            },
            "summary": summary,
            "artifacts": artifacts,
            "error": None,
        }

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

        artifact = self._build_feature_db_artifact(target_path, len(database))
        return {
            "success": True,
            "status": "ok",
            "message": f"上传成功，共 {len(database)} 条记录",
            "minio_path": target_path,
            "csv_source": csv_path,
            "summary": {
                "operation": "feature_database_upload",
                "job_id": None,
                "status": "success",
                "total_count": len(database),
                "success_count": len(database),
                "failed_count": 0,
                "requested_count": len(database),
                "artifact_count": 1,
                "failed_ids": [],
                "mode": "upload",
            },
            "artifacts": [artifact],
            "error": None,
        }

    async def _reprocess_single(self, job_id: str, subgraph_id: str) -> FeatureRecognitionItem:
        # 中文说明：单子图仍复用 batch 接口，只在 service 内规范结果结构。
        started_at = time.perf_counter()
        normalized_result = await asyncio.to_thread(self.batch_recognize, job_id, subgraph_id)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        return self._normalize_reprocess_result(subgraph_id, normalized_result, duration_ms)

    def _normalize_reprocess_result(
        self,
        subgraph_id: str,
        normalized_result: FeatureRecognitionResult,
        duration_ms: int,
    ) -> FeatureRecognitionItem:
        batch_results = normalized_result.get("data", {}).get("results", [])
        matched = next(
            (item for item in batch_results if item.get("subgraph_id") == subgraph_id),
            None,
        )
        if matched is None:
            if normalized_result.get("status") == "error":
                return {
                    "subgraph_id": subgraph_id,
                    "success": False,
                    "status": "failed",
                    "message": normalized_result.get("message", "特征识别失败"),
                    "error": normalized_result.get("error", {}).get("message", "特征识别失败"),
                    "duration_ms": duration_ms,
                }
            return {
                "subgraph_id": subgraph_id,
                "success": True,
                "status": "success",
                "message": normalized_result.get("message", "特征识别完成"),
                "duration_ms": duration_ms,
            }

        payload: FeatureRecognitionItem = {
            **matched,
            "duration_ms": duration_ms,
        }
        return payload

    def _build_subgraph_source_map(self, job_id: str, subgraph_id: str | None) -> dict[str, dict[str, Any]]:
        try:
            subgraphs = self.get_subgraphs(job_id, subgraph_id)
        except Exception:
            return {}

        return {
            item.get("subgraph_id"): item
            for item in subgraphs
            if item.get("subgraph_id")
        }

    def _normalize_batch_item(
        self,
        job_id: str,
        item: dict[str, Any],
        source: dict[str, Any] | None,
    ) -> FeatureRecognitionItem:
        subgraph_id = item.get("subgraph_id")
        success = bool(item.get("success"))
        message = item.get("message", "特征识别完成" if success else "特征识别失败")
        normalized: FeatureRecognitionItem = {
            "subgraph_id": subgraph_id,
            "part_code": item.get("part_code") or (source or {}).get("part_code"),
            "success": success,
            "status": "success" if success else "failed",
            "message": message,
        }

        if success and isinstance(item.get("features"), dict):
            normalized["features"] = item["features"]
            normalized["artifact"] = self._build_feature_artifact(
                job_id=job_id,
                subgraph_id=subgraph_id,
                part_code=normalized.get("part_code"),
                features=item["features"],
                source=source,
            )
        else:
            normalized["error"] = message

        return normalized

    def _build_feature_artifact(
        self,
        job_id: str,
        subgraph_id: str | None,
        part_code: str | None,
        features: dict[str, Any],
        source: dict[str, Any] | None,
    ) -> ServiceArtifactRef:
        source_url = (source or {}).get("subgraph_file_url")
        metadata = {
            "operation": "feature_recognition",
            "feature_keys": sorted(features.keys()),
        }
        if source_url:
            metadata["source_ref"] = self._build_storage_ref(source_url)

        return {
            "artifact_type": "feature_record",
            "ref": f"db://features/{job_id}/{subgraph_id or 'unknown'}",
            "storage": "database",
            "locator": {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "part_code": part_code,
                "source_path": source_url,
            },
            "metadata": metadata,
        }

    @staticmethod
    def _build_feature_db_artifact(minio_path: str, entry_count: int) -> ServiceArtifactRef:
        return {
            "artifact_type": "feature_database",
            "ref": f"minio://{minio_path.replace('\\', '/').lstrip('/')}",
            "storage": "minio",
            "locator": {
                "path": minio_path,
            },
            "metadata": {
                "entry_count": entry_count,
                "operation": "feature_database_upload",
            },
        }

    @staticmethod
    def _build_summary(
        operation: str,
        job_id: str | None,
        requested_count: int,
        total_count: int,
        success_count: int,
        failed_count: int,
        artifact_count: int,
        failed_ids: list[str],
        mode: str,
    ) -> ServiceSummary:
        if failed_count == 0:
            status = "success"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial"

        return {
            "operation": operation,
            "job_id": job_id,
            "status": status,
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "requested_count": requested_count,
            "artifact_count": artifact_count,
            "failed_ids": failed_ids,
            "mode": mode,
        }

    def _build_error_result(
        self,
        job_id: str | None,
        code: str,
        message: str,
        requested_subgraph_id: str | None = None,
        retryable: bool = False,
    ) -> FeatureRecognitionResult:
        error: ServiceError = {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": {
                "requested_subgraph_id": requested_subgraph_id,
            },
        }
        summary: ServiceSummary = {
            "operation": "feature_recognition",
            "job_id": job_id,
            "status": "failed",
            "total_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "requested_count": 1 if requested_subgraph_id else 0,
            "artifact_count": 0,
            "failed_ids": [requested_subgraph_id] if requested_subgraph_id else [],
            "mode": "batch",
        }
        result: FeatureRecognitionResult = {
            "status": "error",
            "success": False,
            "message": message,
            "operation": "feature_recognition",
            "requested_subgraph_id": requested_subgraph_id,
            "data": {
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "results": [],
            },
            "summary": summary,
            "artifacts": [],
            "error": error,
        }
        if job_id is not None:
            result["job_id"] = job_id
        return result

    @staticmethod
    def _resolve_error_code(message: str) -> str:
        if "未找到子图" in message:
            return "SUBGRAPHS_NOT_FOUND"
        return "FEATURE_RECOGNITION_FAILED"

    def _resolve_subgraph_ids(self, job_id: str) -> list[str]:
        # 中文说明：统一从 gateway 查询待处理子图，避免上层自己碰数据库脚本逻辑。
        subgraphs = self.get_subgraphs(job_id)
        return [item["subgraph_id"] for item in subgraphs if item.get("subgraph_id")]

    @staticmethod
    def _build_storage_ref(path: str | None) -> str:
        if not path:
            return "unknown://feature"
        return f"minio://{path.replace('\\', '/').lstrip('/')}"

    @staticmethod
    def _find_latest_feature_csv(folder: str) -> str | None:
        pattern = os.path.join(folder, "特征面识别报告_增强版*.csv")
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
