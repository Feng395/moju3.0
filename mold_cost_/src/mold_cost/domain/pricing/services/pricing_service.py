"""Pricing domain orchestration service."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from shared.unified_logging import get_logger

from mold_cost.core.settings import settings
from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)


class PricingService:
    """Own the local pricing orchestration inside src/mold_cost."""

    async def calculate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run pricing orchestration for a job or a batch of subgraphs."""
        job_id = context.get("job_id")
        subgraph_ids = list(context.get("subgraph_ids") or [])
        progress_publisher = context.get("_progress_publisher")

        if not job_id:
            return self._error_result("缺少job_id参数", "MISSING_JOB_ID")
        if not subgraph_ids:
            return self._error_result("缺少subgraph_ids参数", "MISSING_SUBGRAPH_IDS")

        batch_size = self._resolve_batch_size(context)
        logger.info(
            "[pricing_service] start job_id=%s, subgraph_count=%s, batch_size=%s",
            job_id,
            len(subgraph_ids),
            batch_size,
        )

        if len(subgraph_ids) <= batch_size:
            return await self._process_single_batch(
                job_id=job_id,
                subgraph_ids=subgraph_ids,
                progress_publisher=progress_publisher,
                publish_progress=True,
            )

        return await self._process_multiple_batches(
            job_id=job_id,
            subgraph_ids=subgraph_ids,
            batch_size=batch_size,
            progress_publisher=progress_publisher,
        )

    async def update_job_total_cost(self, job_id: str) -> float:
        """Aggregate `subgraphs.total_cost` and write back to `jobs.total_cost`."""
        query_sql = """
            SELECT COALESCE(SUM(total_cost), 0) AS total_cost
            FROM subgraphs
            WHERE job_id = $1::uuid
        """
        row = await db.fetch_one(query_sql, job_id)
        total_cost = float((row or {}).get("total_cost", 0) or 0)

        update_sql = """
            UPDATE jobs
            SET
                total_cost = $2,
                updated_at = NOW()
            WHERE job_id = $1::uuid
        """
        await db.execute(update_sql, job_id, total_cost)
        return total_cost

    def _resolve_batch_size(self, context: dict[str, Any]) -> int:
        configured = context.get("pricing_batch_size", settings.PRICING_BATCH_SIZE)
        try:
            return max(1, int(configured))
        except (TypeError, ValueError):
            logger.warning("Invalid pricing_batch_size=%r, fallback to settings", configured)
            return max(1, int(settings.PRICING_BATCH_SIZE))

    async def _process_single_batch(
        self,
        job_id: str,
        subgraph_ids: list[str],
        *,
        progress_publisher: Any = None,
        publish_progress: bool = True,
    ) -> dict[str, Any]:
        total_start = time.perf_counter()

        try:
            if publish_progress:
                self._publish_started(progress_publisher, job_id, len(subgraph_ids))
                self._publish_progress(progress_publisher, job_id, 77, "正在搜索价格数据...", "search")

            search_data = await self._concurrent_search(job_id, subgraph_ids)

            if publish_progress:
                self._publish_progress(progress_publisher, job_id, 80, "正在计算各项费用...", "calculate")

            await self._concurrent_calculate(search_data, job_id, subgraph_ids)

            if publish_progress:
                self._publish_progress(progress_publisher, job_id, 83, "正在刷新汇总搜索数据...", "total_search")

            from mold_cost.domain.pricing.search import total_search

            await total_search.search_by_job_id(job_id, subgraph_ids)

            if publish_progress:
                self._publish_progress(progress_publisher, job_id, 85, "正在计算线割和水磨总价...", "wire_watermill")

            from mold_cost.domain.pricing.calculators import price_water_mill_total, price_wire_total
            from mold_cost.domain.pricing.search import (
                base_itemcode_search,
                search as subgraphs_cost_search,
                total_search as total_search_module,
                water_mill_search,
            )

            base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
            total_data = await total_search_module.search_by_job_id(job_id, subgraph_ids)
            water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)

            stage_results = await asyncio.gather(
                price_wire_total.calculate(
                    {"base_itemcode": base_data, "total": total_data},
                    job_id,
                    subgraph_ids,
                ),
                price_water_mill_total.calculate(
                    {
                        "base_itemcode": base_data,
                        "total": total_data,
                        "water_mill": water_mill_data,
                    },
                    job_id,
                    subgraph_ids,
                ),
                subgraphs_cost_search.search_by_job_id(job_id, subgraph_ids),
                return_exceptions=True,
            )
            for stage_name, result in zip(
                ("wire_total", "water_mill_total", "subgraphs_cost"),
                stage_results,
                strict=True,
            ):
                if isinstance(result, Exception):
                    logger.error("Pricing stage %s failed: %s", stage_name, result)

            if publish_progress:
                self._publish_progress(progress_publisher, job_id, 87, "正在执行价格数据校验...", "judgment")

            from mold_cost.domain.pricing.calculators import judgment

            base_data_fresh = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
            try:
                await judgment.calculate({"base_itemcode": base_data_fresh}, job_id, subgraph_ids)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Pricing judgment cleanup failed but processing continues: %s", exc)

            if publish_progress:
                self._publish_progress(progress_publisher, job_id, 89, "正在计算最终总价...", "total_price")

            from mold_cost.domain.pricing.calculators import price_total

            subgraphs_cost_data = await subgraphs_cost_search.search_by_job_id(job_id, subgraph_ids)
            final_result = await price_total.calculate(
                {"subgraphs_cost": subgraphs_cost_data},
                job_id,
                subgraph_ids,
            )

            total_cost = float(final_result.get("job_total_cost", final_result.get("total_cost", 0) or 0))
            duration_ms = (time.perf_counter() - total_start) * 1000
            logger.info(
                "[pricing_service] completed job_id=%s, total_cost=%.2f, duration_ms=%.0f",
                job_id,
                total_cost,
                duration_ms,
            )

            if publish_progress:
                self._publish_completed(progress_publisher, job_id, total_cost)

            return {
                "status": "ok",
                "message": "价格计算完成",
                "total_cost": total_cost,
                "breakdown": {},
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("[pricing_service] pricing failed: %s", exc, exc_info=True)
            if publish_progress:
                self._publish_failed(progress_publisher, job_id, str(exc))
            return self._error_result(f"价格计算失败: {exc}", "PRICING_ERROR")

    async def _process_multiple_batches(
        self,
        job_id: str,
        subgraph_ids: list[str],
        *,
        batch_size: int,
        progress_publisher: Any = None,
    ) -> dict[str, Any]:
        total_start = time.perf_counter()
        total_batches = (len(subgraph_ids) + batch_size - 1) // batch_size

        logger.info(
            "[pricing_service] start batched job_id=%s, subgraph_count=%s, batch_size=%s, total_batches=%s",
            job_id,
            len(subgraph_ids),
            batch_size,
            total_batches,
        )

        try:
            self._publish_started(
                progress_publisher,
                job_id,
                len(subgraph_ids),
                batch_size=batch_size,
                total_batches=total_batches,
            )

            batch_results: list[dict[str, Any]] = []
            for index in range(0, len(subgraph_ids), batch_size):
                batch = subgraph_ids[index : index + batch_size]
                batch_num = index // batch_size + 1
                batch_start = time.perf_counter()

                logger.info(
                    "[pricing_service] batch %s/%s job_id=%s subgraph_count=%s",
                    batch_num,
                    total_batches,
                    job_id,
                    len(batch),
                )
                batch_result = await self._process_single_batch(
                    job_id=job_id,
                    subgraph_ids=batch,
                    progress_publisher=progress_publisher,
                    publish_progress=False,
                )
                if batch_result.get("status") == "error":
                    logger.error(
                        "[pricing_service] batch %s/%s failed: %s",
                        batch_num,
                        total_batches,
                        batch_result.get("message"),
                    )
                    return batch_result

                batch_results.append(batch_result)
                self._publish_batch_progress(
                    progress_publisher,
                    job_id,
                    batch_num=batch_num,
                    total_batches=total_batches,
                    batch_duration=time.perf_counter() - batch_start,
                )

            final_result = self._merge_batch_results(batch_results)
            total_cost = await self.update_job_total_cost(job_id)
            final_result["total_cost"] = total_cost

            total_duration = time.perf_counter() - total_start
            logger.info(
                "[pricing_service] completed batched job_id=%s, total_cost=%.2f, duration_s=%.2f",
                job_id,
                total_cost,
                total_duration,
            )
            self._publish_completed(
                progress_publisher,
                job_id,
                total_cost,
                subgraph_count=len(subgraph_ids),
                total_batches=total_batches,
                total_duration=round(total_duration, 2),
            )
            return final_result
        except Exception as exc:  # noqa: BLE001
            logger.error("[pricing_service] batched pricing failed: %s", exc, exc_info=True)
            self._publish_failed(progress_publisher, job_id, str(exc))
            return self._error_result(f"分批处理失败: {exc}", "BATCH_PROCESSING_ERROR")

    def _merge_batch_results(self, batch_results: list[dict[str, Any]]) -> dict[str, Any]:
        merged_breakdown: dict[str, dict[str, Any]] = {}
        all_errors: list[Any] = []

        for result in batch_results:
            for key, value in (result.get("breakdown") or {}).items():
                bucket = merged_breakdown.setdefault(
                    key,
                    {"status": value.get("status", "ok"), "cost": 0.0, "count": 0},
                )
                bucket["cost"] += value.get("cost", 0)
                bucket["count"] += value.get("count", 0)

            errors = result.get("errors")
            if errors:
                if isinstance(errors, list):
                    all_errors.extend(errors)
                else:
                    all_errors.append(errors)

        statuses = [result.get("status") for result in batch_results]
        if all(status == "ok" for status in statuses):
            status = "ok"
        elif any(status in {"ok", "partial"} for status in statuses):
            status = "partial"
        else:
            status = "error"

        return {
            "status": status,
            "message": f"价格计算完成（分{len(batch_results)}批处理）",
            "breakdown": merged_breakdown,
            "errors": all_errors or None,
            "batch_count": len(batch_results),
        }

    async def _concurrent_search(self, job_id: str, subgraph_ids: list[str]) -> dict[str, Any]:
        from mold_cost.domain.pricing.search import (
            base_itemcode_search,
            density_search,
            heat_search,
            material_search,
            nc_search,
            tooth_hole_search,
            water_mill_search,
            wire_base_search,
            wire_special_search,
            wire_standard_search,
        )

        tool_names = [
            "base_itemcode",
            "material",
            "density",
            "heat",
            "tooth_hole",
            "water_mill",
            "wire_base",
            "wire_special",
            "wire_standard",
            "nc",
        ]
        results = await asyncio.gather(
            base_itemcode_search.search_by_job_id(job_id, subgraph_ids),
            material_search.search_by_job_id(job_id, subgraph_ids),
            density_search.search_by_job_id(job_id, subgraph_ids),
            heat_search.search_by_job_id(job_id, subgraph_ids),
            tooth_hole_search.search_by_job_id(job_id, subgraph_ids),
            water_mill_search.search_by_job_id(job_id, subgraph_ids),
            wire_base_search.search_by_job_id(job_id, subgraph_ids),
            wire_special_search.search_by_job_id(job_id, subgraph_ids),
            wire_standard_search.search_by_job_id(job_id, subgraph_ids),
            nc_search.search_by_job_id(job_id, subgraph_ids),
            return_exceptions=True,
        )

        merged: dict[str, Any] = {"job_id": job_id}
        for name, result in zip(tool_names, results, strict=True):
            if isinstance(result, Exception):
                logger.error("Pricing search %s failed: %s", name, result)
                if name in {"base_itemcode", "material"}:
                    raise ValueError(f"关键价格搜索失败: {name}") from result
                merged[name] = {}
            else:
                merged[name] = result

        return merged

    async def _concurrent_calculate(
        self,
        search_data: dict[str, Any],
        job_id: str,
        subgraph_ids: list[str],
    ) -> list[Any]:
        from mold_cost.domain.pricing.calculators import (
            price_add_auto_material,
            price_heat,
            price_material,
            price_nc_base,
            price_nc_time,
            price_tooth_hole,
            price_water_mill_bevel_cost,
            price_water_mill_chamfer_cost,
            price_water_mill_component,
            price_water_mill_hanging_table,
            price_water_mill_high_cost,
            price_water_mill_long_strip,
            price_water_mill_oil_tank,
            price_water_mill_plate,
            price_water_mill_thread_ends,
            price_weight,
            price_wire_base,
            price_wire_special,
            price_wire_standard,
        )

        base_data = search_data.get("base_itemcode", {})
        material_data = search_data.get("material", {})
        density_data = search_data.get("density", {})
        heat_data = search_data.get("heat", {})
        tooth_hole_data = search_data.get("tooth_hole", {})
        water_mill_data = search_data.get("water_mill", {})
        wire_base_data = search_data.get("wire_base", {})
        wire_special_data = search_data.get("wire_special", {})
        wire_standard_data = search_data.get("wire_standard", {})
        nc_data = search_data.get("nc", {})

        calc_names = [
            "material",
            "heat",
            "weight",
            "tooth_hole",
            "wire_base",
            "wire_special",
            "wire_standard",
            "add_auto_material",
            "nc_base",
            "nc_time",
            "nc_total",
            "water_mill_bevel",
            "water_mill_chamfer",
            "water_mill_component",
            "water_mill_hanging_table",
            "water_mill_high",
            "water_mill_long_strip",
            "water_mill_oil_tank",
            "water_mill_plate",
            "water_mill_thread_ends",
        ]
        results = await asyncio.gather(
            price_material.calculate(
                {"base_itemcode": base_data, "material": material_data, "density": density_data},
                job_id,
                subgraph_ids,
            ),
            price_heat.calculate(
                {"base_itemcode": base_data, "heat": heat_data, "density": density_data},
                job_id,
                subgraph_ids,
            ),
            price_weight.calculate(
                {"base_itemcode": base_data, "density": density_data},
                job_id,
                subgraph_ids,
            ),
            price_tooth_hole.calculate(
                {"base_itemcode": base_data, "tooth_hole": tooth_hole_data},
                job_id,
                subgraph_ids,
            ),
            price_wire_base.calculate(
                {"base_itemcode": base_data, "wire_base": wire_base_data},
                job_id,
                subgraph_ids,
            ),
            price_wire_special.calculate(
                {"base_itemcode": base_data, "wire_special": wire_special_data},
                job_id,
                subgraph_ids,
            ),
            price_wire_standard.calculate(
                {"base_itemcode": base_data, "wire_standard": wire_standard_data},
                job_id,
                subgraph_ids,
            ),
            price_add_auto_material.calculate(
                {"base_itemcode": base_data, "material": material_data, "density": density_data},
                job_id,
                subgraph_ids,
            ),
            price_nc_base.calculate(
                {"base_itemcode": base_data, "nc": nc_data, "wire_base": wire_base_data},
                job_id,
                subgraph_ids,
            ),
            price_nc_time.calculate(
                {"base_itemcode": base_data, "nc": nc_data},
                job_id,
                subgraph_ids,
            ),
            self._calculate_nc_total(base_data, job_id, subgraph_ids),
            price_water_mill_bevel_cost.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_chamfer_cost.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_component.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_hanging_table.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_high_cost.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_long_strip.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_oil_tank.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_plate.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            price_water_mill_thread_ends.calculate(
                {"base_itemcode": base_data, "water_mill": water_mill_data},
                job_id,
                subgraph_ids,
            ),
            return_exceptions=True,
        )

        for name, result in zip(calc_names, results, strict=True):
            if isinstance(result, Exception):
                logger.error("Pricing calculator %s failed: %s", name, result)

        return results

    async def _calculate_nc_total(
        self,
        base_data: dict[str, Any],
        job_id: str,
        subgraph_ids: list[str],
    ) -> dict[str, Any]:
        from mold_cost.domain.pricing.calculators import price_nc_total
        from mold_cost.domain.pricing.search import total_search

        total_data = await total_search.search_by_job_id(job_id, subgraph_ids)
        return await price_nc_total.calculate(
            {"base_itemcode": base_data, "total": total_data},
            job_id,
            subgraph_ids,
        )

    def _publish_started(
        self,
        progress_publisher: Any,
        job_id: str,
        subgraph_count: int,
        **details: Any,
    ) -> None:
        from shared.progress_stages import ProgressPercent, ProgressStage

        self._safe_publish(
            progress_publisher,
            job_id=job_id,
            stage=ProgressStage.PRICING_STARTED,
            progress=ProgressPercent.PRICING_STARTED,
            message="正在计算价格...",
            details={"source": "pricing_service", "subgraph_count": subgraph_count, **details},
        )

    def _publish_progress(
        self,
        progress_publisher: Any,
        job_id: str,
        progress: int,
        message: str,
        phase: str,
        **details: Any,
    ) -> None:
        self._safe_publish(
            progress_publisher,
            job_id=job_id,
            stage="pricing_progress",
            progress=progress,
            message=message,
            details={"source": "pricing_service", "phase": phase, **details},
        )

    def _publish_batch_progress(
        self,
        progress_publisher: Any,
        job_id: str,
        *,
        batch_num: int,
        total_batches: int,
        batch_duration: float,
    ) -> None:
        from shared.progress_stages import ProgressPercent

        current_pct = ProgressPercent.PRICING_STARTED + int(
            (ProgressPercent.PRICING_COMPLETED - ProgressPercent.PRICING_STARTED) * batch_num / total_batches
        )
        self._publish_progress(
            progress_publisher,
            job_id,
            current_pct,
            f"价格计算中: 批次 {batch_num}/{total_batches} 完成",
            "batch",
            batch_num=batch_num,
            total_batches=total_batches,
            batch_duration=round(batch_duration, 2),
        )

    def _publish_completed(
        self,
        progress_publisher: Any,
        job_id: str,
        total_cost: float,
        **details: Any,
    ) -> None:
        from shared.progress_stages import ProgressPercent, ProgressStage

        self._safe_publish(
            progress_publisher,
            job_id=job_id,
            stage=ProgressStage.PRICING_COMPLETED,
            progress=ProgressPercent.PRICING_COMPLETED,
            message=f"价格计算完成，总成本 {total_cost} CNY",
            details={"source": "pricing_service", "total_cost": total_cost, **details},
        )

    def _publish_failed(
        self,
        progress_publisher: Any,
        job_id: str,
        error: str,
    ) -> None:
        from shared.progress_stages import ProgressPercent, ProgressStage

        self._safe_publish(
            progress_publisher,
            job_id=job_id,
            stage=ProgressStage.PRICING_FAILED,
            progress=ProgressPercent.PRICING_STARTED,
            message=f"价格计算失败: {error}",
            details={"source": "pricing_service", "error": error},
        )

    def _safe_publish(self, progress_publisher: Any, **payload: Any) -> None:
        if progress_publisher is None:
            return
        try:
            progress_publisher.publish_progress(**payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to publish pricing progress: %s", exc)

    def _error_result(self, message: str, error_code: str) -> dict[str, Any]:
        return {"status": "error", "message": message, "error_code": error_code}


pricing_service = PricingService()
