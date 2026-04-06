"""Src-owned review display-view builder."""

from __future__ import annotations

from typing import Any

from ...core.logging import get_logger

logger = get_logger(__name__)


class SrcReviewDisplayViewBuilder:
    """Build workflow-facing display rows from review raw data."""

    def build_display_view(self, raw_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        logger.info("Building review display view from src runtime")

        display_items: list[dict[str, Any]] = []
        subgraphs = raw_data.get("subgraphs", [])
        features = raw_data.get("features", [])
        price_snapshots = raw_data.get("job_price_snapshots") or raw_data.get("price_snapshots", [])
        cost_details = raw_data.get("processing_cost_calculation_details", [])

        for subgraph in subgraphs:
            job_id = subgraph.get("job_id")
            subgraph_id = subgraph.get("subgraph_id")

            feature = self._find_feature(features, job_id=job_id, subgraph_id=subgraph_id)
            wire_process_code = subgraph.get("wire_process")

            wire_price = None
            if wire_process_code:
                wire_price = self._find_price_snapshot(
                    price_snapshots,
                    job_id=job_id,
                    category="wire",
                    sub_category=wire_process_code,
                )

            material_price = None
            if feature:
                material_price = self._find_price_snapshot(
                    price_snapshots,
                    job_id=job_id,
                    category="material",
                    sub_category=feature.get("material"),
                )

            cost_detail = self._find_processing_cost_detail(
                cost_details,
                job_id=job_id,
                subgraph_id=subgraph_id,
            )

            display_items.append(
                {
                    "part_code": subgraph.get("part_code"),
                    "part_name": subgraph.get("part_name"),
                    "subgraph_file_url": subgraph.get("subgraph_file_url"),
                    "process_description": subgraph.get("process_description"),
                    "material": feature.get("material") if feature else None,
                    "length_mm": feature.get("length_mm") if feature else None,
                    "width_mm": feature.get("width_mm") if feature else None,
                    "thickness_mm": feature.get("thickness_mm") if feature else None,
                    "quantity": feature.get("quantity") if feature else None,
                    "heat_treatment": feature.get("heat_treatment") if feature else None,
                    "abnormal_situation": feature.get("abnormal_situation") if feature else None,
                    "drilling_time": subgraph.get("drilling_time"),
                    "nc_roughing_time": subgraph.get("nc_roughing_time"),
                    "nc_milling_time": subgraph.get("nc_milling_time"),
                    "edm_time": subgraph.get("edm_time"),
                    "wire_length": (
                        subgraph.get("slow_wire_length")
                        or subgraph.get("mid_wire_length")
                        or subgraph.get("fast_wire_length")
                    ),
                    "grinding_time": (
                        subgraph.get("large_grinding_time") or subgraph.get("small_grinding_time")
                    ),
                    "process_code": wire_process_code,
                    "process_note": subgraph.get("wire_process_note"),
                    "process_unit_price": wire_price.get("price") if wire_price else None,
                    "material_unit_price": material_price.get("price") if material_price else None,
                    "weight": cost_detail.get("weight") if cost_detail else None,
                    "_source": {
                        "job_id": job_id,
                        "subgraph_id": subgraph_id,
                        "feature_id": feature.get("feature_id") if feature else None,
                        "feature_version": feature.get("version") if feature else None,
                        "created_at": subgraph.get("created_at"),
                        "wire_price_snapshot_id": wire_price.get("snapshot_id") if wire_price else None,
                        "material_price_snapshot_id": material_price.get("snapshot_id") if material_price else None,
                        "processing_cost_detail_id": cost_detail.get("detail_id") if cost_detail else None,
                    },
                }
            )

        # 中文注释：沿用旧展示层的排序语义，避免 review 前端展示顺序在重构中漂移。
        display_items.sort(
            key=lambda item: (
                item.get("_source", {}).get("created_at") or "",
                item.get("_source", {}).get("subgraph_id") or "",
                item.get("_source", {}).get("feature_version") or 0,
            ),
            reverse=True,
        )
        return display_items

    @staticmethod
    def _find_feature(features: list[dict[str, Any]], job_id: Any, subgraph_id: Any) -> dict[str, Any] | None:
        for feature in features:
            if feature.get("job_id") == job_id and feature.get("subgraph_id") == subgraph_id:
                return feature
        return None

    @staticmethod
    def _find_price_snapshot(
        price_snapshots: list[dict[str, Any]],
        *,
        job_id: Any,
        category: str,
        sub_category: Any,
    ) -> dict[str, Any] | None:
        if not sub_category:
            return None

        expected_category = category.lower().strip()
        expected_sub_category = str(sub_category).lower().strip()
        for snapshot in price_snapshots:
            if snapshot.get("job_id") != job_id:
                continue
            snapshot_category = snapshot.get("category")
            snapshot_sub_category = snapshot.get("sub_category")
            if snapshot_category is None or snapshot_sub_category is None:
                continue
            if snapshot_category.lower().strip() != expected_category:
                continue
            if str(snapshot_sub_category).lower().strip() == expected_sub_category:
                return snapshot
        return None

    @staticmethod
    def _find_processing_cost_detail(
        details: list[dict[str, Any]],
        *,
        job_id: Any,
        subgraph_id: Any,
    ) -> dict[str, Any] | None:
        for detail in details:
            if detail.get("job_id") == job_id and detail.get("subgraph_id") == subgraph_id:
                return detail
        return None
