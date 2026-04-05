"""Src 侧的成本计算详情查询 handler。"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from sqlalchemy import select

from ...core.logging import get_logger
from ..db.repositories.chat_history_repository import ChatHistoryRepository
from .review_action_handlers import BaseReviewActionHandler, ReviewActionResult

logger = get_logger(__name__)


class QueryDetailsReviewActionHandler(BaseReviewActionHandler):
    """查询成本计算详情，并尽量保持与 legacy handler 一致的输出语义。"""

    _REFERENCE_PRONOUNS = ("它", "那个", "这个", "那", "这")
    _SUBGRAPH_PREFIXES = (
        r"UP_JIAT",
        r"PS_JIAT",
        r"LOW_JIAT",
        r"UP_ITEM",
        r"PSITEM",
        r"LOW_ITEM",
        r"DIE2_P",
        r"PS2_P",
        r"PPS2_P",
        r"PH2_P",
        r"LB2_P",
        r"UP_P",
        r"UB_P",
        r"PH_P",
        r"PU_P",
        r"PPS_P",
        r"PS_P",
        r"DIE_P",
        r"GU_P",
        r"LB_P",
        r"TEMP[12]",
        r"ST[123]",
        r"DIE2",
        r"PS2",
        r"PPS2",
        r"PH2",
        r"LB2",
        r"STRIP",
        r"PPS",
        r"DIE",
        r"CAM",
        r"BOL",
        r"UP",
        r"LP",
        r"PS",
        r"PH",
        r"UB",
        r"PU",
        r"LB",
        r"EB",
        r"EJ",
        r"CV",
        r"CJ",
        r"CB",
        r"GU",
        r"RP",
        r"CP",
        r"TP",
        r"BP",
        r"SP",
        r"MP",
        r"PP",
        r"U[12]",
        r"B[12]",
    )
    _SUBGRAPH_PATTERN = re.compile(
        rf"((?:{'|'.join(_SUBGRAPH_PREFIXES)})[-_]?(?:\d{{2}}|[A-Z]+\d+))",
        re.IGNORECASE,
    )
    _RESULT_KEYS = [
        "weight",
        "material_cost",
        "heat_treatment_cost",
        "basic_processing_cost",
        "special_base_cost",
        "material_additional_cost",
        "discharge_cost",
        "total_discharge_cost",
        "hole_cost",
        "standard_base_cost",
        "nc_roughing_cost",
        "nc_milling_cost",
        "nc_drilling_cost",
        "processing_cost_total",
        "total_cost",
        "wire_cost_base",
        "wire_cost_per_unit",
        "material_cost_total",
        "heat_treatment_cost_total",
        "thread_ends_cost",
        "hanging_table_cost",
        "total_chamfer_cost",
        "total_bevel_cost",
        "oil_tank_cost",
        "high_cost",
        "plate_cost",
        "long_strip_cost",
        "component_cost",
        "nc_base_cost",
        "total_hours",
        "nc_z_time",
        "nc_b_time",
        "nc_c_time",
        "nc_c_b_time",
        "nc_z_view_time",
        "nc_b_view_time",
        "nc_z_fee",
        "nc_b_fee",
        "nc_c_fee",
        "nc_c_b_fee",
        "nc_z_view_fee",
        "nc_b_view_fee",
        "weight_price",
    ]
    _KEY_TRANSLATIONS = {
        "weight": "重量(kg)",
        "material_cost": "材料费(元)",
        "heat_treatment_cost": "热处理费(元)",
        "basic_processing_cost": "基础加工费(元)",
        "special_base_cost": "特殊工艺费(元)",
        "material_additional_cost": "额外材料费(元)",
        "unit_price": "单价",
        "matched_sub_category": "匹配材料",
        "discharge_cost": "放电费用(元)",
        "hole_cost": "孔类费(元)",
        "perimeter": "周长(mm)",
        "total_discharge_cost": "总放电费用(元)",
        "nc_base_hours": "NC基本工时(小时)",
        "kai_cu_hours": "开粗工时(小时)",
        "jing_xi_hours": "精铣工时(小时)",
        "drill_hours": "钻床工时(小时)",
        "nc_roughing_cost": "NC开粗费用(元)",
        "nc_milling_cost": "NC精铣费用(元)",
        "nc_drilling_cost": "NC钻床费用(元)",
        "wire_process": "工艺代码",
        "boring_num": "孔数",
        "standard_base_cost": "标准基本费(元)",
        "total_length": "总线长(mm)",
        "dimension": "实际尺寸(mm)",
        "base_price": "基础价格(元)",
        "final_price": "最终价格(元)",
        "processing_cost_total": "加工成本总计(元)",
        "total_cost": "总价(元)",
        "part_type": "零件类型",
        "has_auto_material": "是否自找料",
        "has_side_cut": "是否有侧割",
        "material": "材料名称",
        "wire_type": "线割类型",
        "is_template": "是否为模板",
        "needs_heat_treatment": "是否需要热处理",
        "wire_cost_base": "线割基础费用(元)",
        "wire_cost_per_unit": "线割单价(元)",
        "wire_length": "线割总长度(mm)",
        "slow_wire_length": "慢丝长度(mm)",
        "mid_wire_length": "中丝长度(mm)",
        "fast_wire_length": "快丝长度(mm)",
        "material_unit_price": "材料单价(元/kg)",
        "heat_treatment_unit_price": "热处理单价(元/kg)",
        "weight_kg": "总重量(kg)",
        "material_cost_total": "材料费总价(元)",
        "heat_treatment_cost_total": "热处理费总价(元)",
        "selected": "选择的费用类型",
        "matched_material": "匹配到的材料名称",
        "density": "密度值",
        "thread_ends_count": "线头数量",
        "thread_ends_cost": "线头费用(元)",
        "hanging_table_count": "挂台数量",
        "hanging_table_cost": "挂台费用(元)",
        "chamfer_type": "倒角类型",
        "chamfer_costs": "各类倒角费用明细",
        "total_chamfer_cost": "倒角总费用(元)",
        "bevel_value": "斜面值",
        "price_rule": "价格规则",
        "bevel_details": "各个斜面的详情",
        "total_bevel_cost": "斜面总费用(元)",
        "oil_tank_count": "油槽数量",
        "oil_tank_cost": "油槽费用(元)",
        "material_part_code": "备料零件编号",
        "material_thickness": "备料零件厚度(mm)",
        "current_thickness": "当前零件厚度(mm)",
        "thickness_diff": "厚度差异(mm)",
        "high_cost": "高度费用(元)",
        "area": "面积(mm²)",
        "divisor": "除数(mm²)",
        "plate_cost": "板费用(元)",
        "price_type": "价格类型",
        "range": "价格区间",
        "long_strip_cost": "长条费用(小时/件)",
        "grinding": "研磨面数",
        "max_length_width": "长宽最大值(mm)",
        "component_cost": "零件费用(元)",
        "face_code": "面代码",
        "total_minutes": "总时间(分钟)",
        "total_hours": "总时间(小时)",
        "face_costs": "各面时间(小时)",
        "nc_base_cost": "NC基本时间(小时)",
        "comparisons": "时间比较结果",
        "final_times": "最终时间(小时)",
        "final_fees": "最终费用(元)",
        "nc_z_time": "Z面时间(小时)",
        "nc_b_time": "B面时间(小时)",
        "nc_c_time": "C面时间(小时)",
        "nc_c_b_time": "C_B面时间(小时)",
        "nc_z_view_time": "Z_VIEW面时间(小时)",
        "nc_b_view_time": "B_VIEW面时间(小时)",
        "nc_z_fee": "Z面费用(元)",
        "nc_b_fee": "B面费用(元)",
        "nc_c_fee": "C面费用(元)",
        "nc_c_b_fee": "C_B面费用(元)",
        "nc_z_view_fee": "Z_VIEW面费用(元)",
        "nc_b_view_fee": "B_VIEW面费用(元)",
        "weight_price": "加权价格(元)",
        "matched_range": "匹配的重量范围",
        "rule_price": "规则价格系数",
        "sub_category": "规则子类别",
        "status": "状态",
    }
    _DEFAULT_CATEGORY_MAP = {
        "weight": "重量计算",
        "material": "材料费计算",
        "heat": "热处理费计算",
        "wire_base": "线割基础加工费",
        "wire_special": "线割特殊工艺费",
        "wire_speci": "线割特殊工艺费",
        "add_auto_material": "自找料判断",
        "standard": "线割标准基本费计算",
        "tooth_hole_time": "牙孔时间费用",
        "wire_standard": "线割标准基本费",
        "total": "最终总价计算",
        "wire_total": "线割总价计算",
        "nc_base": "NC基本时间",
        "nc_z": "NC Z面时间",
        "nc_b": "NC B面时间",
        "nc_c": "NC C面时间",
        "nc_c_b": "NC C_B面时间",
        "nc_z_view": "NC Z_VIEW面时间",
        "nc_b_view": "NC B_VIEW面时间",
        "nc_total": "NC总费用计算",
        "nc_roughing": "NC开粗费用",
        "nc_milling": "NC精铣费用",
        "nc_drilling": "NC钻床费用",
        "water_mill_high": "水磨高度费",
        "water_mill_long_strip": "水磨长条费",
        "water_mill_chamfer": "水磨倒角费",
        "water_mill_thread_ends": "水磨螺纹端",
        "water_mill_hanging_table": "水磨挂台",
        "water_mill_bevel": "水磨斜面",
        "water_mill_oil_tank": "水磨油槽",
        "water_mill_high_cost": "水磨高费用",
        "water_mill_plate": "水磨板",
        "water_mill_component": "水磨零件",
        "water_mill_grinding": "水磨磨削",
        "weight_price": "价格加权计算",
    }
    _AGGREGATE_QUERY_PREFIXES = {
        "nc": ("nc_",),
        "wire": ("wire_",),
        "water_mill": ("water_mill_",),
    }
    _IMPORTANT_KEYS = [
        "weight",
        "material_cost",
        "heat_treatment_cost",
        "basic_processing_cost",
        "special_base_cost",
        "material_additional_cost",
        "unit_price",
        "matched_sub_category",
        "material",
        "wire_type",
        "is_template",
        "needs_heat_treatment",
        "discharge_cost",
        "hole_cost",
        "perimeter",
        "total_discharge_cost",
        "nc_base_hours",
        "kai_cu_hours",
        "jing_xi_hours",
        "drill_hours",
        "nc_roughing_cost",
        "nc_milling_cost",
        "nc_drilling_cost",
        "wire_process",
        "boring_num",
        "standard_base_cost",
        "total_length",
        "dimension",
        "base_price",
        "final_price",
        "processing_cost_total",
        "total_cost",
        "part_type",
        "has_auto_material",
        "has_side_cut",
        "wire_cost_base",
        "wire_cost_per_unit",
        "wire_length",
        "slow_wire_length",
        "mid_wire_length",
        "fast_wire_length",
        "material_unit_price",
        "heat_treatment_unit_price",
        "weight_kg",
        "material_cost_total",
        "heat_treatment_cost_total",
        "matched_material",
        "density",
        "thread_ends_count",
        "thread_ends_cost",
        "hanging_table_count",
        "hanging_table_cost",
        "total_chamfer_cost",
        "chamfer_type",
        "total_bevel_cost",
        "bevel_value",
        "oil_tank_count",
        "oil_tank_cost",
        "high_cost",
        "thickness_diff",
        "plate_cost",
        "area",
        "long_strip_cost",
        "max_length",
        "component_cost",
        "grinding",
        "mill_type",
        "has_material_preparation",
        "face_code",
        "total_minutes",
        "total_hours",
        "face_costs",
        "nc_base_cost",
        "comparisons",
        "final_times",
        "final_fees",
        "nc_z_time",
        "nc_b_time",
        "nc_c_time",
        "weight_price",
        "matched_range",
        "rule_price",
        "status",
    ]

    def __init__(
        self,
        *,
        chat_history_repository: ChatHistoryRepository | None = None,
        use_chat_history: bool | None = None,
        max_history_messages: int = 10,
    ) -> None:
        super().__init__(pending_action_store=None)
        self._chat_history_repository = chat_history_repository or ChatHistoryRepository()
        self._use_chat_history = (
            use_chat_history
            if use_chat_history is not None
            else os.getenv("USE_CHAT_HISTORY", "true").lower() == "true"
        )
        self._max_history_messages = max_history_messages

    async def handle(self, intent_result, job_id: str, context: dict[str, Any], db_session) -> ReviewActionResult:
        del context
        try:
            subgraph_id = await self._resolve_subgraph_id(
                intent_result=intent_result,
                job_id=job_id,
                db_session=db_session,
            )
            if not subgraph_id:
                return ReviewActionResult(
                    status="error",
                    message="请指定要查询的子图，例如：'UP01 的价格怎么算的？'",
                    requires_confirmation=False,
                    data={},
                )

            query_type = (getattr(intent_result, "parameters", {}) or {}).get("query_type")
            detail = await self._query_calculation_detail(
                db_session=db_session,
                job_id=job_id,
                subgraph_id=subgraph_id,
            )
            if detail is None:
                return ReviewActionResult(
                    status="ok",
                    message=(
                        f"{subgraph_id} 暂无计算详情。\n\n"
                        "可能原因：\n"
                        "1. 该子图还未进行价格计算\n"
                        "2. 计算详情尚未保存到数据库\n\n"
                        "建议：先执行价格计算，然后再查询详情。"
                    ),
                    requires_confirmation=False,
                    data={"subgraph_id": subgraph_id, "query_type": query_type},
                )

            formatted_message = self._format_response(
                subgraph_id=subgraph_id,
                calculation_steps=getattr(detail, "calculation_steps", None),
                query_type=query_type,
            )
            return ReviewActionResult(
                status="ok",
                message=formatted_message,
                requires_confirmation=False,
                data={
                    "subgraph_id": subgraph_id,
                    "query_type": query_type,
                    "calculation_steps": getattr(detail, "calculation_steps", None),
                    "processing_instructions": getattr(detail, "processing_instructions", None),
                },
            )
        except Exception as exc:
            logger.error("Query details review action failed", exc_info=True)
            return ReviewActionResult(
                status="error",
                message=f"查询详情失败：{exc}",
                requires_confirmation=False,
                data={},
            )

    async def _resolve_subgraph_id(self, *, intent_result, job_id: str, db_session) -> str | None:
        parameters = getattr(intent_result, "parameters", {}) or {}
        subgraph_id = parameters.get("subgraph_id")
        if not subgraph_id:
            subgraph_ids = parameters.get("subgraph_ids") or []
            if subgraph_ids:
                subgraph_id = subgraph_ids[0]

        if not self._use_chat_history:
            return subgraph_id

        history_subgraph_id = await self._infer_subgraph_from_history(db_session=db_session, job_id=job_id)
        if not subgraph_id:
            return history_subgraph_id

        raw_message = getattr(intent_result, "raw_message", "") or ""
        if raw_message and any(pronoun in raw_message for pronoun in self._REFERENCE_PRONOUNS):
            return history_subgraph_id or subgraph_id
        return subgraph_id

    async def _infer_subgraph_from_history(self, *, db_session, job_id: str) -> str | None:
        history = await self._chat_history_repository.get_recent_session_history(
            db_session,
            session_id=job_id,
            limit=max(self._max_history_messages, 50),
        )
        if not history:
            return None

        prioritized_messages = [
            *[message for message in reversed(history) if message.get("role") == "user"],
            *[message for message in reversed(history) if message.get("role") == "assistant"],
        ]
        for message in prioritized_messages:
            content = message.get("content", "")
            matches = self._SUBGRAPH_PATTERN.findall(content)
            if matches:
                return matches[0].upper()
        return None

    async def _query_calculation_detail(self, *, db_session, job_id: str, subgraph_id: str):
        from shared.models import Feature, ProcessingCostCalculationDetail

        result = await db_session.execute(
            select(ProcessingCostCalculationDetail).where(
                ProcessingCostCalculationDetail.subgraph_id == subgraph_id,
                ProcessingCostCalculationDetail.job_id == job_id,
            )
        )
        detail = result.scalar_one_or_none()

        if detail is None:
            result = await db_session.execute(
                select(ProcessingCostCalculationDetail).where(
                    ProcessingCostCalculationDetail.subgraph_id.like(f"%_{subgraph_id}"),
                    ProcessingCostCalculationDetail.job_id == job_id,
                )
            )
            matches = result.scalars().all()
            if not matches:
                return None
            detail = matches[0] if len(matches) == 1 else min(matches, key=lambda item: len(item.subgraph_id))

        # 中文注释：加工说明仍保留一并查询，后续如果要恢复更强解释能力可以直接复用。
        feature_result = await db_session.execute(
            select(Feature).where(
                Feature.subgraph_id == detail.subgraph_id,
                Feature.job_id == job_id,
            )
        )
        feature = feature_result.scalar_one_or_none()
        detail.processing_instructions = getattr(feature, "processing_instructions", None) if feature else None
        return detail

    def _format_response(self, *, subgraph_id: str, calculation_steps: Any, query_type: str | None) -> str:
        if query_type:
            return self._format_specific_category(subgraph_id=subgraph_id, calculation_steps=calculation_steps, query_type=query_type)
        return self._format_calculation_steps(subgraph_id=subgraph_id, calculation_steps=calculation_steps)

    def _format_calculation_steps(self, *, subgraph_id: str, calculation_steps: Any) -> str:
        try:
            steps = self._normalize_steps(calculation_steps)
            if not steps:
                return f"{subgraph_id} 暂无计算详情"

            lines = [f"{subgraph_id} 的成本计算详情：", ""]
            for item in steps:
                category = str(item.get("category", "unknown"))
                category_name = self._DEFAULT_CATEGORY_MAP.get(category, f"未知类型({category})")
                lines.append(f"【{category_name}】")
                for step in item.get("steps", []):
                    lines.extend(self._format_step_lines(step=step, query_type=category))
                lines.append("")
            return "\n".join(lines).rstrip()
        except Exception as exc:
            logger.error("Format calculation steps failed", exc_info=True)
            return f"{subgraph_id} 的计算详情格式化失败：{exc}"

    def _format_specific_category(self, *, subgraph_id: str, calculation_steps: Any, query_type: str) -> str:
        try:
            steps = self._normalize_steps(calculation_steps)
            if not steps:
                return f"{subgraph_id} 暂无计算详情数据"

            matched_items = [item for item in steps if self._matches_query_type(item.get("category"), query_type)]
            if not matched_items:
                return f"{subgraph_id} 没有 {query_type} 相关的计算详情"

            category_name = self._resolve_query_type_name(query_type)
            lines = [f"{subgraph_id} 的{category_name}详情：", ""]
            for item in matched_items:
                item_category = str(item.get("category", query_type))
                if len(matched_items) > 1:
                    lines.append(f"【{self._DEFAULT_CATEGORY_MAP.get(item_category, item_category)}】")
                for step in item.get("steps", []):
                    lines.extend(self._format_step_lines(step=step, query_type=query_type))
                lines.append("")
            return "\n".join(lines).rstrip()
        except Exception as exc:
            logger.error("Format specific category failed", exc_info=True)
            return f"{subgraph_id} 的 {query_type} 详情格式化失败：{exc}"

    def _format_step_lines(self, *, step: dict[str, Any], query_type: str) -> list[str]:
        step_desc = str(step.get("step", ""))
        lines: list[str] = []
        if "formula" in step:
            result_key = self._find_result_key(step)
            if result_key:
                lines.append(f"  {step_desc}: {step[result_key]}")
            else:
                lines.append(f"  {step_desc}")
            lines.append(f"    公式: {step['formula']}")
            return lines

        if "note" in step or "reason" in step:
            note = step.get("note") or step.get("reason")
            lines.append(f"  {step_desc}: {note}")
            return lines

        if query_type == "wire_base" and "code" in step:
            code = step.get("code")
            instruction = step.get("instruction", "")
            final_price = step.get("final_price", 0)
            lines.append(f"  [{code}] {instruction}")
            lines.append(f"    费用: {final_price:.2f} 元")
            complete_formula = step.get("complete_formula", "")
            if complete_formula:
                lines.append(f"    计算: {complete_formula}")
            return lines

        if step_desc:
            lines.append(f"  {step_desc}")
        for key in self._IMPORTANT_KEYS:
            if key in step:
                lines.append(f"    {self._translate_key(key)}: {self._stringify_value(step[key])}")
        return lines

    def _normalize_steps(self, calculation_steps: Any) -> list[dict[str, Any]]:
        if not calculation_steps:
            return []
        steps = calculation_steps
        if isinstance(steps, str):
            steps = json.loads(steps)
        if not isinstance(steps, list):
            return []
        return [item for item in steps if isinstance(item, dict)]

    def _matches_query_type(self, category: Any, query_type: str) -> bool:
        if category == query_type:
            return True
        if query_type in {"NC", "nc"} and isinstance(category, str):
            return category.startswith("nc_") or category == "nc"
        if query_type in {"水磨", "water_mill"} and isinstance(category, str):
            return category.startswith("water_mill_") or category == "water_mill"
        if query_type in {"线割", "wire"} and isinstance(category, str):
            return category.startswith("wire_") or category == "wire"
        prefixes = self._AGGREGATE_QUERY_PREFIXES.get(query_type)
        if prefixes and isinstance(category, str):
            return any(category.startswith(prefix) for prefix in prefixes)
        return False

    def _resolve_query_type_name(self, query_type: str) -> str:
        if query_type in {"NC", "nc"}:
            return "NC相关计算"
        if query_type in {"水磨", "water_mill"}:
            return "水磨相关计算"
        if query_type in {"线割", "wire"}:
            return "线割相关计算"
        return self._DEFAULT_CATEGORY_MAP.get(query_type, query_type)

    def _find_result_key(self, step: dict[str, Any]) -> str | None:
        for key in self._RESULT_KEYS:
            if key in step:
                return key
        return None

    def _translate_key(self, key: str) -> str:
        return self._KEY_TRANSLATIONS.get(key, key)

    @staticmethod
    def _stringify_value(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
