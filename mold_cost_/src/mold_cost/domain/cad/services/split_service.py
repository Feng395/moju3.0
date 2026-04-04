"""CAD 拆图领域服务。"""

from __future__ import annotations

from typing import Any

from ..ports import (
    CadSplitGateway,
    CadSplitResult,
    CadSplitSubgraphRecord,
    ServiceArtifactRef,
    ServiceError,
    ServiceSummary,
)


class LegacyCadSplitService:
    """兼容迁移期的 CAD 拆图服务。

    中文说明：当前仍复用 legacy 脚本能力，但由 service 统一收口，
    这样 API / workflow 只依赖稳定的领域契约，不再感知脚本返回差异。
    """

    def __init__(self, gateway: CadSplitGateway):
        self._gateway = gateway

    async def split(
        self,
        dwg_url: str | None,
        job_id: str,
        minio_client: Any | None = None,
    ) -> CadSplitResult:
        if not job_id:
            return self._build_error_result(
                job_id=None,
                code="MISSING_JOB_ID",
                message="缺少 job_id",
                details={"operation": "cad_split"},
            )

        try:
            raw_result = await self._gateway.split(
                dwg_url=dwg_url,
                job_id=job_id,
                minio_client=minio_client,
            )
        except Exception as exc:
            return self._build_error_result(
                job_id=job_id,
                code="CAD_SPLIT_GATEWAY_ERROR",
                message=f"CAD 拆图调用异常: {exc}",
                retryable=True,
                details={"dwg_url": dwg_url},
            )

        if raw_result.get("status") != "ok":
            return self._build_error_result(
                job_id=job_id,
                code=raw_result.get("error_code", "CAD_SPLIT_FAILED"),
                message=raw_result.get("message", "CAD 拆图失败"),
                details={"dwg_url": dwg_url},
            )

        subgraphs = await self._safe_list_subgraphs(job_id)
        raw_data = raw_result.get("data") or {}
        raw_files = self._coerce_result_files(raw_data.get("result_files"))
        artifacts = self._build_artifacts(job_id, subgraphs, raw_files)
        total_count = self._resolve_total_count(raw_data, artifacts, raw_files)
        summary = self._build_summary(
            job_id=job_id,
            total_count=total_count,
            success_count=total_count,
            failed_count=0,
            artifact_count=len(artifacts),
        )

        data = {
            "total_count": total_count,
            "result_files": raw_files or [artifact["locator"].get("filename") for artifact in artifacts if artifact.get("locator")],
            "subgraphs": subgraphs,
        }
        if raw_data:
            # 中文注释：保留 legacy data 字段，避免兼容调用方被破坏。
            data.update(raw_data)
            data["total_count"] = total_count
            data["result_files"] = raw_files or data.get("result_files", [])
            data["subgraphs"] = subgraphs

        return {
            "status": "ok",
            "success": True,
            "message": raw_result.get("message", f"CAD 拆图完成，共生成 {total_count} 个子图"),
            "job_id": job_id,
            "operation": "cad_split",
            "data": data,
            "summary": summary,
            "artifacts": artifacts,
            "error": None,
        }

    async def _safe_list_subgraphs(self, job_id: str) -> list[CadSplitSubgraphRecord]:
        try:
            return await self._gateway.list_subgraphs(job_id)
        except Exception:
            # 中文注释：artifact 回查失败不阻断主流程，仍保留 legacy result_files 兜底。
            return []

    @staticmethod
    def _coerce_result_files(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item]

    @staticmethod
    def _resolve_total_count(
        raw_data: dict[str, Any],
        artifacts: list[ServiceArtifactRef],
        raw_files: list[str],
    ) -> int:
        raw_total = raw_data.get("total_count")
        if isinstance(raw_total, int):
            return raw_total
        if artifacts:
            return len(artifacts)
        return len(raw_files)

    def _build_artifacts(
        self,
        job_id: str,
        subgraphs: list[CadSplitSubgraphRecord],
        raw_files: list[str],
    ) -> list[ServiceArtifactRef]:
        artifacts: list[ServiceArtifactRef] = []
        for item in subgraphs:
            file_url = item.get("subgraph_file_url")
            filename = file_url.rsplit("/", 1)[-1] if file_url else f"{item.get('subgraph_id', 'unknown')}.dxf"
            locator = {
                "job_id": job_id,
                "subgraph_id": item.get("subgraph_id"),
                "part_code": item.get("part_code"),
                "part_name": item.get("part_name"),
                "filename": filename,
            }
            if file_url:
                locator["path"] = file_url

            artifacts.append(
                {
                    "artifact_type": "cad_subgraph_dxf",
                    "ref": self._build_storage_ref(file_url) if file_url else f"result://cad_split/{job_id}/{filename}",
                    "storage": "minio" if file_url else "inline",
                    "locator": locator,
                    "metadata": {
                        "operation": "cad_split",
                        "job_id": job_id,
                    },
                }
            )

        if artifacts:
            return artifacts

        for filename in raw_files:
            artifacts.append(
                {
                    "artifact_type": "cad_subgraph_dxf",
                    "ref": f"result://cad_split/{job_id}/{filename}",
                    "storage": "inline",
                    "locator": {
                        "job_id": job_id,
                        "filename": filename,
                    },
                    "metadata": {
                        "operation": "cad_split",
                        "job_id": job_id,
                    },
                }
            )
        return artifacts

    @staticmethod
    def _build_storage_ref(path: str | None) -> str:
        if not path:
            return "unknown://cad_split"
        normalized = path.replace("\\", "/").lstrip("/")
        return f"minio://{normalized}"

    @staticmethod
    def _build_summary(
        job_id: str,
        total_count: int,
        success_count: int,
        failed_count: int,
        artifact_count: int,
    ) -> ServiceSummary:
        return {
            "operation": "cad_split",
            "job_id": job_id,
            "status": "success" if failed_count == 0 else "partial",
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "requested_count": total_count,
            "artifact_count": artifact_count,
            "failed_ids": [],
        }

    def _build_error_result(
        self,
        job_id: str | None,
        code: str,
        message: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> CadSplitResult:
        error: ServiceError = {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details or {},
        }
        summary: ServiceSummary = {
            "operation": "cad_split",
            "job_id": job_id,
            "status": "failed",
            "total_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "requested_count": 0,
            "artifact_count": 0,
            "failed_ids": [],
        }
        result: CadSplitResult = {
            "status": "error",
            "success": False,
            "message": message,
            "operation": "cad_split",
            "data": {
                "total_count": 0,
                "result_files": [],
                "subgraphs": [],
            },
            "summary": summary,
            "artifacts": [],
            "error": error,
        }
        if job_id is not None:
            result["job_id"] = job_id
        return result
