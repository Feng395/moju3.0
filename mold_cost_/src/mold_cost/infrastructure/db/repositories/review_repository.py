"""Src-owned repository for review workflow data access."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Feature, JobPriceSnapshot, ProcessingCostCalculationDetail, Subgraph
from shared.timezone_utils import now_shanghai

from ....core.logging import get_logger

logger = get_logger(__name__)


class SrcReviewRepository:
    """Read and update the review workflow's four-table payload."""

    async def get_features(self, db: AsyncSession, job_id: str) -> list[dict[str, Any]]:
        logger.info("Querying review features: job_id=%s", job_id)
        query = (
            select(Feature, Subgraph.part_code, Subgraph.part_name)
            .join(Subgraph, Feature.subgraph_id == Subgraph.subgraph_id)
            .where(Feature.job_id == job_id)
        )
        result = await db.execute(query)
        rows = result.all()

        data: list[dict[str, Any]] = []
        for feature, part_code, part_name in rows:
            feature_dict = self._feature_to_dict(feature)
            feature_dict["part_code"] = part_code
            feature_dict["part_name"] = part_name
            data.append(feature_dict)
        return data

    async def get_price_snapshots(self, db: AsyncSession, job_id: str) -> list[dict[str, Any]]:
        logger.info("Querying review price snapshots: job_id=%s", job_id)
        result = await db.execute(select(JobPriceSnapshot).where(JobPriceSnapshot.job_id == job_id))
        return [self._price_snapshot_to_dict(snapshot) for snapshot in result.scalars().all()]

    async def get_subgraphs(self, db: AsyncSession, job_id: str) -> list[dict[str, Any]]:
        logger.info("Querying review subgraphs: job_id=%s", job_id)
        result = await db.execute(select(Subgraph).where(Subgraph.job_id == job_id))
        return [self._subgraph_to_dict(subgraph) for subgraph in result.scalars().all()]

    async def get_processing_cost_details(self, db: AsyncSession, job_id: str) -> list[dict[str, Any]]:
        logger.info("Querying review processing cost details: job_id=%s", job_id)
        result = await db.execute(
            select(ProcessingCostCalculationDetail).where(ProcessingCostCalculationDetail.job_id == job_id)
        )
        return [self._processing_cost_detail_to_dict(detail) for detail in result.scalars().all()]

    async def update_features(self, db: AsyncSession, job_id: str, features_data: list[dict[str, Any]]) -> None:
        allowed_fields = {
            "subgraph_id",
            "version",
            "length_mm",
            "width_mm",
            "thickness_mm",
            "quantity",
            "material",
            "heat_treatment",
            "calculated_weight_kg",
            "top_view_wire_length",
            "front_view_wire_length",
            "side_view_wire_length",
            "has_auto_material",
            "needs_heat_treatment",
            "boring_length_mm",
            "processing_instructions",
            "is_complete",
            "missing_params",
            "abnormal_situation",
            "created_by",
            "meta_data",
        }
        for feature_data in features_data:
            feature_id = feature_data.get("feature_id")
            update_data = {key: value for key, value in feature_data.items() if key in allowed_fields}
            update_data = self._convert_feature_types(update_data)
            await db.execute(
                update(Feature)
                .where(Feature.feature_id == feature_id, Feature.job_id == job_id)
                .values(**update_data)
            )

    async def update_price_snapshots(
        self,
        db: AsyncSession,
        job_id: str,
        snapshots_data: list[dict[str, Any]],
    ) -> None:
        for snapshot_data in snapshots_data:
            snapshot_id = snapshot_data.get("snapshot_id")
            update_data = {
                key: value
                for key, value in snapshot_data.items()
                if key not in {"snapshot_id", "job_id", "snapshot_created_at"}
            }
            await db.execute(
                update(JobPriceSnapshot)
                .where(JobPriceSnapshot.snapshot_id == snapshot_id, JobPriceSnapshot.job_id == job_id)
                .values(**update_data)
            )

    async def update_subgraphs(self, db: AsyncSession, job_id: str, subgraphs_data: list[dict[str, Any]]) -> None:
        allowed_fields = {
            "part_name",
            "part_code",
            "subgraph_file_url",
            "weight_kg",
            "material_unit_price",
            "material_cost",
            "heat_treatment_unit_price",
            "heat_treatment_cost",
            "process_description",
            "nc_roughing_time",
            "nc_milling_time",
            "drilling_time",
            "milling_machine_time",
            "large_grinding_time",
            "small_grinding_time",
            "edm_time",
            "engraving_time",
            "slow_wire_length",
            "slow_wire_side_length",
            "mid_wire_length",
            "fast_wire_length",
            "separate_item",
            "total_cost",
            "wire_process_note",
            "nc_roughing_cost",
            "nc_milling_cost",
            "drilling_cost",
            "milling_machine_cost",
            "large_grinding_cost",
            "small_grinding_cost",
            "slow_wire_cost",
            "slow_wire_side_cost",
            "mid_wire_cost",
            "fast_wire_cost",
            "edm_cost",
            "engraving_cost",
            "separate_item_cost",
            "processing_cost_total",
            "applied_snapshot_ids",
            "rule_reason",
            "override_by_user",
            "cost_calculation_method",
            "has_sheet_line",
            "sheet_area_mm2",
            "sheet_perimeter_mm",
            "sheet_line_data",
            "has_single_nc_calc",
            "single_prt_file",
            "process_changed",
            "wire_process",
            "original_process",
            "prt_3d_file",
            "recalc_count",
            "last_recalc_at",
            "last_recalc_by",
            "status",
            "meta_data",
        }
        for subgraph_data in subgraphs_data:
            subgraph_id = subgraph_data.get("subgraph_id")
            update_data = {key: value for key, value in subgraph_data.items() if key in allowed_fields}
            update_data = self._convert_subgraph_types(update_data)
            update_data["updated_at"] = now_shanghai()
            await db.execute(
                update(Subgraph)
                .where(Subgraph.subgraph_id == subgraph_id, Subgraph.job_id == job_id)
                .values(**update_data)
            )

    async def get_all_review_data(self, db: AsyncSession, job_id: str) -> dict[str, list[dict[str, Any]]]:
        features = await self.get_features(db, job_id)
        price_snapshots = await self.get_price_snapshots(db, job_id)
        subgraphs = await self.get_subgraphs(db, job_id)
        processing_cost_details = await self.get_processing_cost_details(db, job_id)
        return {
            "features": features,
            "job_price_snapshots": price_snapshots,
            "subgraphs": subgraphs,
            "processing_cost_calculation_details": processing_cost_details,
        }

    async def update_all_review_data(
        self,
        db: AsyncSession,
        job_id: str,
        data: dict[str, list[dict[str, Any]]],
    ) -> None:
        if "features" in data:
            await self.update_features(db, job_id, data["features"])

        # 中文注释：兼容旧键名 `price_snapshots`，避免重构期间测试夹具或外部调用一起失效。
        if "job_price_snapshots" in data:
            await self.update_price_snapshots(db, job_id, data["job_price_snapshots"])
        elif "price_snapshots" in data:
            await self.update_price_snapshots(db, job_id, data["price_snapshots"])

        if "subgraphs" in data:
            await self.update_subgraphs(db, job_id, data["subgraphs"])

    @staticmethod
    def _convert_feature_types(data: dict[str, Any]) -> dict[str, Any]:
        converted = dict(data)
        for field in ("version", "quantity"):
            converted = SrcReviewRepository._convert_int_field(converted, field)
        for field in (
            "length_mm",
            "width_mm",
            "thickness_mm",
            "calculated_weight_kg",
            "top_view_wire_length",
            "front_view_wire_length",
            "side_view_wire_length",
            "boring_length_mm",
        ):
            converted = SrcReviewRepository._convert_float_field(converted, field)
        for field in ("has_auto_material", "needs_heat_treatment", "is_complete"):
            converted = SrcReviewRepository._convert_bool_field(converted, field)
        return converted

    @staticmethod
    def _convert_subgraph_types(data: dict[str, Any]) -> dict[str, Any]:
        converted = dict(data)
        converted = SrcReviewRepository._convert_int_field(converted, "recalc_count")
        for field in (
            "weight_kg",
            "material_unit_price",
            "material_cost",
            "heat_treatment_unit_price",
            "heat_treatment_cost",
            "nc_roughing_time",
            "nc_milling_time",
            "drilling_time",
            "milling_machine_time",
            "large_grinding_time",
            "small_grinding_time",
            "edm_time",
            "engraving_time",
            "slow_wire_length",
            "slow_wire_side_length",
            "mid_wire_length",
            "fast_wire_length",
            "total_cost",
            "nc_roughing_cost",
            "nc_milling_cost",
            "drilling_cost",
            "milling_machine_cost",
            "large_grinding_cost",
            "small_grinding_cost",
            "slow_wire_cost",
            "slow_wire_side_cost",
            "mid_wire_cost",
            "fast_wire_cost",
            "edm_cost",
            "engraving_cost",
            "separate_item_cost",
            "processing_cost_total",
            "sheet_area_mm2",
            "sheet_perimeter_mm",
        ):
            converted = SrcReviewRepository._convert_float_field(converted, field)
        for field in ("override_by_user", "has_sheet_line", "has_single_nc_calc", "process_changed"):
            converted = SrcReviewRepository._convert_bool_field(converted, field)
        return converted

    @staticmethod
    def _convert_int_field(data: dict[str, Any], field: str) -> dict[str, Any]:
        if field in data and data[field] is not None:
            try:
                data[field] = int(data[field])
            except (TypeError, ValueError):
                logger.warning("Failed to convert %s to int: %s", field, data[field])
        return data

    @staticmethod
    def _convert_float_field(data: dict[str, Any], field: str) -> dict[str, Any]:
        if field in data and data[field] is not None:
            try:
                data[field] = float(data[field])
            except (TypeError, ValueError):
                logger.warning("Failed to convert %s to float: %s", field, data[field])
        return data

    @staticmethod
    def _convert_bool_field(data: dict[str, Any], field: str) -> dict[str, Any]:
        if field in data and data[field] is not None:
            if isinstance(data[field], str):
                data[field] = data[field].lower() in ("true", "1", "yes")
            else:
                data[field] = bool(data[field])
        return data

    @staticmethod
    def _feature_to_dict(feature: Feature) -> dict[str, Any]:
        return {
            "feature_id": feature.feature_id,
            "subgraph_id": feature.subgraph_id,
            "job_id": str(feature.job_id),
            "version": feature.version,
            "length_mm": float(feature.length_mm) if feature.length_mm else None,
            "width_mm": float(feature.width_mm) if feature.width_mm else None,
            "thickness_mm": float(feature.thickness_mm) if feature.thickness_mm else None,
            "quantity": feature.quantity,
            "material": feature.material,
            "heat_treatment": feature.heat_treatment,
            "calculated_weight_kg": float(feature.calculated_weight_kg) if feature.calculated_weight_kg else None,
            "top_view_wire_length": float(feature.top_view_wire_length) if feature.top_view_wire_length else None,
            "front_view_wire_length": float(feature.front_view_wire_length) if feature.front_view_wire_length else None,
            "side_view_wire_length": float(feature.side_view_wire_length) if feature.side_view_wire_length else None,
            "has_auto_material": feature.has_auto_material,
            "needs_heat_treatment": feature.needs_heat_treatment,
            "boring_length_mm": float(feature.boring_length_mm) if feature.boring_length_mm else None,
            "processing_instructions": feature.processing_instructions,
            "is_complete": feature.is_complete,
            "missing_params": feature.missing_params,
            "abnormal_situation": feature.abnormal_situation,
            "created_by": feature.created_by,
            "created_at": feature.created_at.isoformat() if feature.created_at else None,
            "meta_data": feature.meta_data,
        }

    @staticmethod
    def _price_snapshot_to_dict(snapshot: JobPriceSnapshot) -> dict[str, Any]:
        return {
            "snapshot_id": snapshot.snapshot_id,
            "job_id": str(snapshot.job_id),
            "original_price_id": snapshot.original_price_id,
            "version_id": snapshot.version_id,
            "category": snapshot.category,
            "sub_category": snapshot.sub_category,
            "price": snapshot.price,
            "unit": snapshot.unit,
            "work_hours": snapshot.work_hours,
            "min_num": snapshot.min_num,
            "add_price": snapshot.add_price,
            "weight_num": snapshot.weight_num,
            "note": snapshot.note,
            "instruction": snapshot.instruction,
            "is_modified": snapshot.is_modified,
            "modified_by": snapshot.modified_by,
            "modified_at": snapshot.modified_at.isoformat() if snapshot.modified_at else None,
            "modification_reason": snapshot.modification_reason,
            "snapshot_created_at": snapshot.snapshot_created_at.isoformat() if snapshot.snapshot_created_at else None,
            "meta_data": snapshot.meta_data,
        }

    @staticmethod
    def _subgraph_to_dict(subgraph: Subgraph) -> dict[str, Any]:
        return {
            "subgraph_id": subgraph.subgraph_id,
            "job_id": str(subgraph.job_id),
            "part_name": subgraph.part_name,
            "part_code": subgraph.part_code,
            "subgraph_file_url": subgraph.subgraph_file_url,
            "weight_kg": float(subgraph.weight_kg) if subgraph.weight_kg else None,
            "material_unit_price": float(subgraph.material_unit_price) if subgraph.material_unit_price else None,
            "material_cost": float(subgraph.material_cost) if subgraph.material_cost else None,
            "heat_treatment_unit_price": float(subgraph.heat_treatment_unit_price) if subgraph.heat_treatment_unit_price else None,
            "heat_treatment_cost": float(subgraph.heat_treatment_cost) if subgraph.heat_treatment_cost else None,
            "process_description": subgraph.process_description,
            "nc_roughing_time": float(subgraph.nc_roughing_time) if subgraph.nc_roughing_time else None,
            "nc_milling_time": float(subgraph.nc_milling_time) if subgraph.nc_milling_time else None,
            "drilling_time": float(subgraph.drilling_time) if subgraph.drilling_time else None,
            "milling_machine_time": float(subgraph.milling_machine_time) if subgraph.milling_machine_time else None,
            "large_grinding_time": float(subgraph.large_grinding_time) if subgraph.large_grinding_time else None,
            "small_grinding_time": float(subgraph.small_grinding_time) if subgraph.small_grinding_time else None,
            "edm_time": float(subgraph.edm_time) if subgraph.edm_time else None,
            "engraving_time": float(subgraph.engraving_time) if subgraph.engraving_time else None,
            "slow_wire_length": float(subgraph.slow_wire_length) if subgraph.slow_wire_length else None,
            "slow_wire_side_length": float(subgraph.slow_wire_side_length) if subgraph.slow_wire_side_length else None,
            "mid_wire_length": float(subgraph.mid_wire_length) if subgraph.mid_wire_length else None,
            "fast_wire_length": float(subgraph.fast_wire_length) if subgraph.fast_wire_length else None,
            "separate_item": subgraph.separate_item,
            "total_cost": float(subgraph.total_cost) if subgraph.total_cost else None,
            "wire_process": subgraph.wire_process,
            "wire_process_note": subgraph.wire_process_note,
            "nc_roughing_cost": float(subgraph.nc_roughing_cost) if subgraph.nc_roughing_cost else None,
            "nc_milling_cost": float(subgraph.nc_milling_cost) if subgraph.nc_milling_cost else None,
            "drilling_cost": float(subgraph.drilling_cost) if subgraph.drilling_cost else None,
            "milling_machine_cost": float(subgraph.milling_machine_cost) if subgraph.milling_machine_cost else None,
            "large_grinding_cost": float(subgraph.large_grinding_cost) if subgraph.large_grinding_cost else None,
            "small_grinding_cost": float(subgraph.small_grinding_cost) if subgraph.small_grinding_cost else None,
            "slow_wire_cost": float(subgraph.slow_wire_cost) if subgraph.slow_wire_cost else None,
            "slow_wire_side_cost": float(subgraph.slow_wire_side_cost) if subgraph.slow_wire_side_cost else None,
            "mid_wire_cost": float(subgraph.mid_wire_cost) if subgraph.mid_wire_cost else None,
            "fast_wire_cost": float(subgraph.fast_wire_cost) if subgraph.fast_wire_cost else None,
            "edm_cost": float(subgraph.edm_cost) if subgraph.edm_cost else None,
            "engraving_cost": float(subgraph.engraving_cost) if subgraph.engraving_cost else None,
            "separate_item_cost": float(subgraph.separate_item_cost) if subgraph.separate_item_cost else None,
            "processing_cost_total": float(subgraph.processing_cost_total) if subgraph.processing_cost_total else None,
            "applied_snapshot_ids": subgraph.applied_snapshot_ids,
            "rule_reason": subgraph.rule_reason,
            "override_by_user": subgraph.override_by_user,
            "cost_calculation_method": subgraph.cost_calculation_method,
            "has_sheet_line": subgraph.has_sheet_line,
            "sheet_area_mm2": float(subgraph.sheet_area_mm2) if subgraph.sheet_area_mm2 else None,
            "sheet_perimeter_mm": float(subgraph.sheet_perimeter_mm) if subgraph.sheet_perimeter_mm else None,
            "sheet_line_data": subgraph.sheet_line_data,
            "has_single_nc_calc": subgraph.has_single_nc_calc,
            "single_prt_file": subgraph.single_prt_file,
            "process_changed": subgraph.process_changed,
            "original_process": subgraph.original_process,
            "prt_3d_file": subgraph.prt_3d_file,
            "recalc_count": subgraph.recalc_count,
            "last_recalc_at": subgraph.last_recalc_at.isoformat() if subgraph.last_recalc_at else None,
            "last_recalc_by": subgraph.last_recalc_by,
            "status": subgraph.status,
            "created_at": subgraph.created_at.isoformat() if subgraph.created_at else None,
            "updated_at": subgraph.updated_at.isoformat() if subgraph.updated_at else None,
            "meta_data": subgraph.meta_data,
        }

    @staticmethod
    def _processing_cost_detail_to_dict(detail: ProcessingCostCalculationDetail) -> dict[str, Any]:
        return {
            "detail_id": detail.detail_id,
            "job_id": str(detail.job_id),
            "subgraph_id": detail.subgraph_id,
            "weight": float(detail.weight) if detail.weight else None,
            "created_at": detail.created_at.isoformat() if detail.created_at else None,
        }
