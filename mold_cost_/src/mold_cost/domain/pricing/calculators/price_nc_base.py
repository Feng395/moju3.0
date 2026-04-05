"""NC base pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "calculate_nc_base_cost",
    "description": "Calculate NC base costs from part geometry, NC time data and wire base rules.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode, nc and wire_base results",
            },
            "job_id": {
                "type": "string",
                "description": "Job ID (UUID)",
            },
            "subgraph_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subgraph ID list",
            },
        },
        "required": ["search_data"],
    },
    "handler": "calculate",
    "needs": ["base_itemcode", "nc", "wire_base"],
}

_NC_BASE_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, {field_name}, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        {field_name} = EXCLUDED.{field_name},
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""

_NC_BASE_FIELD_TO_CATEGORY = {
    "nc_base_roughing_cost": "nc_base_roughing",
    "nc_base_milling_cost": "nc_base_milling",
    "nc_base_drilling_cost": "nc_base_drilling",
}


def _build_nc_base_config(nc_prices: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    nc_base_hours: dict[str, float] = {}
    work_hour_prices: list[dict[str, Any]] = []

    for item in nc_prices:
        sub_category = item.get("sub_category")
        if sub_category == "nc_base":
            hours = float(item.get("price", 0) or 0)
            if hours == 1.0:
                nc_base_hours["template"] = hours
            elif hours == 0.5:
                nc_base_hours["component"] = hours
        elif sub_category == "work_hour":
            work_hour_prices.append(
                {
                    "price": float(item.get("price", 0) or 0),
                    "unit": item.get("unit", "元/小时"),
                }
            )

    work_hour_prices.sort(key=lambda item: item["price"])
    return {
        "nc_base_hours": nc_base_hours,
        "work_hour_prices": work_hour_prices,
    }


def _get_template_threshold(rule_prices: Sequence[Mapping[str, Any]]) -> float:
    for item in rule_prices:
        if item.get("sub_category") == "template_component":
            return float(item.get("price", 400) or 400)
    return 400.0


def _determine_part_type(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    template_threshold: float,
) -> tuple[str, str]:
    max_dimension = max(length_mm, width_mm, thickness_mm)
    if max_dimension > template_threshold:
        return "template", f"最大尺寸 {max_dimension}mm > {template_threshold}mm，判定为模板"
    return "component", f"最大尺寸 {max_dimension}mm <= {template_threshold}mm，判定为零件"


def _determine_work_hour_price(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    work_hour_prices: Sequence[Mapping[str, Any]],
) -> tuple[float, str]:
    dimensions = sorted([length_mm, width_mm, thickness_mm], reverse=True)
    longest = dimensions[0]
    shortest = dimensions[2]

    if len(work_hour_prices) < 3:
        price = float(work_hour_prices[0]["price"]) if work_hour_prices else 60.0
        return price, f"默认使用 {price} 元/小时（价格数据不足）"

    if longest >= 2000 or shortest >= 1200:
        price = float(work_hour_prices[2]["price"])
        return price, f"最长边 {longest}mm 或最短边 {shortest}mm 满足高档条件，使用 {price} 元/小时"

    if (1500 <= longest < 2000) or (800 <= shortest < 1200):
        price = float(work_hour_prices[1]["price"])
        return price, f"尺寸落入中档区间，使用 {price} 元/小时"

    price = float(work_hour_prices[0]["price"])
    return price, f"尺寸较小，使用 {price} 元/小时"


def _calculate_nc_base_costs(
    *,
    nc_base_hours: float,
    unit_price: float,
    quantity: float,
    has_roughing: bool,
    has_milling: bool,
    has_drilling: bool,
) -> tuple[float, float, float, float]:
    cost_single = nc_base_hours * unit_price
    roughing = cost_single * quantity if has_roughing else 0.0
    milling = cost_single * quantity if has_milling else 0.0
    drilling = cost_single * quantity if has_drilling else 0.0
    return cost_single, roughing, milling, drilling


def _build_calculation_steps(
    *,
    part_type: str,
    part_type_desc: str,
    nc_base_hours: float,
    unit_price: float,
    quantity: float,
    cost_single: float,
    has_roughing: bool,
    has_milling: bool,
    has_drilling: bool,
    nc_base_roughing_cost: float,
    nc_base_milling_cost: float,
    nc_base_drilling_cost: float,
) -> list[dict[str, Any]]:
    return [
        {
            "step": "判断零件类型",
            "part_type": part_type,
            "description": part_type_desc,
        },
        {
            "step": "获取nc_base时间",
            "part_type": part_type,
            "nc_base_hours": nc_base_hours,
        },
        {
            "step": "判断工时单价",
            "unit_price": unit_price,
        },
        {
            "step": "计算NC基础费用",
            "nc_base_hours": nc_base_hours,
            "unit_price": unit_price,
            "quantity": quantity,
            "cost_single": round(cost_single, 4),
            "roughing": {
                "has_data": has_roughing,
                "cost": round(nc_base_roughing_cost, 4),
            },
            "milling": {
                "has_data": has_milling,
                "cost": round(nc_base_milling_cost, 4),
            },
            "drilling": {
                "has_data": has_drilling,
                "cost": round(nc_base_drilling_cost, 4),
            },
        },
    ]


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return

    if field_name not in _NC_BASE_FIELD_TO_CATEGORY:
        raise ValueError(f"Unsupported field_name for nc_base calculator: {field_name}")

    sql = _NC_BASE_UPSERT_SQL.format(field_name=field_name)
    tasks = [
        _upsert_single_record(
            sql,
            update["job_id"],
            update["subgraph_id"],
            update["value"],
            category,
            update["steps"],
        )
        for update in updates
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failures = [result for result in results if isinstance(result, Exception)]
    if failures:
        raise failures[0]


async def _upsert_single_record(
    sql: str,
    job_id: str,
    subgraph_id: str,
    field_value: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(sql, job_id, subgraph_id, field_value, category, steps_json)
    return True


async def _calculate_part_nc_base_cost(
    job_id: str,
    part: Mapping[str, Any],
    nc_base_config: Mapping[str, Any],
    template_threshold: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    length_mm = part["length_mm"]
    width_mm = part["width_mm"]
    thickness_mm = part["thickness_mm"]
    quantity = float(part.get("quantity", 1) or 1)
    nc_time_cost_data = part.get("nc_time_cost")

    if not nc_time_cost_data:
        calculation_steps = [
            {
                "step": "检查nc_time_cost",
                "note": "nc_time_cost数据为空，跳过NC基础费用计算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "note": "nc_time_cost数据为空，跳过计算",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    if isinstance(nc_time_cost_data, str):
        try:
            nc_time_cost_data = json.loads(nc_time_cost_data)
        except Exception as exc:
            calculation_steps = [
                {
                    "step": "解析nc_time_cost",
                    "status": "failed",
                    "reason": f"JSON解析失败: {exc}",
                }
            ]
            return (
                {
                    "subgraph_id": subgraph_id,
                    "part_name": part_name,
                    "nc_base_roughing_cost": 0.0,
                    "nc_base_milling_cost": 0.0,
                    "nc_base_drilling_cost": 0.0,
                    "note": f"nc_time_cost JSON解析失败: {exc}",
                },
                {
                    "job_id": job_id,
                    "subgraph_id": subgraph_id,
                    "nc_base_roughing_cost": 0.0,
                    "nc_base_milling_cost": 0.0,
                    "nc_base_drilling_cost": 0.0,
                    "calculation_steps": calculation_steps,
                },
            )

    nc_details = nc_time_cost_data.get("nc_details", [])
    if not nc_details:
        calculation_steps = [
            {
                "step": "检查nc_details",
                "note": "nc_details为空，跳过NC基础费用计算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "note": "nc_details为空，跳过计算",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    has_roughing = False
    has_milling = False
    has_drilling = False
    for detail in nc_details:
        code = str(detail.get("code", ""))
        try:
            value = float(detail.get("value", 0) or 0)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        if code == "开粗":
            has_roughing = True
        elif code in {"精铣", "半精", "全精"}:
            has_milling = True
        else:
            has_drilling = True

    if not (has_roughing or has_milling or has_drilling):
        calculation_steps = [
            {
                "step": "检查nc_details数据",
                "note": "所有nc_details值都为0，跳过NC基础费用计算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "note": "所有nc_details值都为0，跳过计算",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    part_type, part_type_desc = _determine_part_type(
        float(length_mm),
        float(width_mm),
        float(thickness_mm),
        template_threshold,
    )
    nc_base_hours_value = nc_base_config["nc_base_hours"].get(part_type)
    if nc_base_hours_value is None:
        calculation_steps = [
            {
                "step": "判断零件类型",
                "part_type": part_type,
                "description": part_type_desc,
            },
            {
                "step": "获取nc_base时间",
                "status": "failed",
                "reason": f"未找到 {part_type} 对应的 nc_base 时间配置",
            },
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "part_type": part_type,
                "quantity": quantity,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "note": f"未找到 {part_type} 对应的 nc_base 时间配置",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_base_roughing_cost": 0.0,
                "nc_base_milling_cost": 0.0,
                "nc_base_drilling_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    nc_base_hours = float(nc_base_hours_value)
    unit_price, _price_reason = _determine_work_hour_price(
        float(length_mm),
        float(width_mm),
        float(thickness_mm),
        nc_base_config["work_hour_prices"],
    )

    cost_single, roughing_cost, milling_cost, drilling_cost = _calculate_nc_base_costs(
        nc_base_hours=nc_base_hours,
        unit_price=unit_price,
        quantity=quantity,
        has_roughing=has_roughing,
        has_milling=has_milling,
        has_drilling=has_drilling,
    )

    calculation_steps = _build_calculation_steps(
        part_type=part_type,
        part_type_desc=part_type_desc,
        nc_base_hours=nc_base_hours,
        unit_price=unit_price,
        quantity=quantity,
        cost_single=cost_single,
        has_roughing=has_roughing,
        has_milling=has_milling,
        has_drilling=has_drilling,
        nc_base_roughing_cost=roughing_cost,
        nc_base_milling_cost=milling_cost,
        nc_base_drilling_cost=drilling_cost,
    )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "part_type": part_type,
        "quantity": quantity,
        "nc_base_roughing_cost": round(roughing_cost, 4),
        "nc_base_milling_cost": round(milling_cost, 4),
        "nc_base_drilling_cost": round(drilling_cost, 4),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "nc_base_roughing_cost": roughing_cost,
        "nc_base_milling_cost": milling_cost,
        "nc_base_drilling_cost": drilling_cost,
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    nc_data = search_data["nc"]
    wire_base_data = search_data["wire_base"]

    if not job_id:
        job_id = base_data.get("job_id")

    nc_base_config = _build_nc_base_config(nc_data.get("nc_prices", []))
    if not nc_base_config["nc_base_hours"] or not nc_base_config["work_hour_prices"]:
        return {
            "job_id": job_id,
            "results": [],
            "message": "未找到NC基础费用配置",
        }

    template_threshold = _get_template_threshold(wire_base_data.get("rule_prices", []))

    parts = list(base_data.get("parts", []))
    if subgraph_ids:
        allowed = set(subgraph_ids)
        parts = [part for part in parts if part.get("subgraph_id") in allowed]

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []
    for part in parts:
        result, db_data = await _calculate_part_nc_base_cost(
            job_id, part, nc_base_config, template_threshold
        )
        results.append(result)
        db_updates.append(db_data)

    if db_updates:
        roughing_updates = [
            {
                "job_id": data["job_id"],
                "subgraph_id": data["subgraph_id"],
                "value": data["nc_base_roughing_cost"],
                "steps": data["calculation_steps"],
            }
            for data in db_updates
        ]
        milling_updates = [
            {
                "job_id": data["job_id"],
                "subgraph_id": data["subgraph_id"],
                "value": data["nc_base_milling_cost"],
                "steps": data["calculation_steps"],
            }
            for data in db_updates
        ]
        drilling_updates = [
            {
                "job_id": data["job_id"],
                "subgraph_id": data["subgraph_id"],
                "value": data["nc_base_drilling_cost"],
                "steps": data["calculation_steps"],
            }
            for data in db_updates
        ]
        await batch_upsert_with_steps(roughing_updates, "nc_base_roughing", "nc_base_roughing_cost")
        await batch_upsert_with_steps(milling_updates, "nc_base_milling", "nc_base_milling_cost")
        await batch_upsert_with_steps(drilling_updates, "nc_base_drilling", "nc_base_drilling_cost")

    return {
        "job_id": job_id,
        "results": results,
    }


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = [
    "MCP_TOOL_META",
    "batch_upsert_with_steps",
    "calculate",
    "calculate_sync",
]
