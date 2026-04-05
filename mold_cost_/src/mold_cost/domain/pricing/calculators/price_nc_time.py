"""NC time pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "calculate_nc_time_cost",
    "description": "Calculate NC time costs from part geometry and NC work-hour price rules.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode and nc results",
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
    "needs": ["base_itemcode", "nc"],
}

_RANGE_PATTERN = re.compile(
    r"(?P<label>[SL])\s*:\s*(?P<left>[\[\(])\s*(?P<min>[\d.]+)\s*,\s*(?P<max>[\d.+∞infINF无穷無窮]+)\s*(?P<right>[\]\)])"
)

_NC_TIME_UPSERT_SQL = {
    "nc_roughing_cost": """
        INSERT INTO processing_cost_calculation_details
            (job_id, subgraph_id, nc_roughing_cost, calculation_steps)
        VALUES
            ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
        ON CONFLICT (job_id, subgraph_id)
        DO UPDATE SET
            nc_roughing_cost = EXCLUDED.nc_roughing_cost,
            calculation_steps = (
                SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
                FROM jsonb_array_elements(
                    COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
                ) AS elem
                WHERE elem->>'category' != $4::text
            ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
    """,
    "nc_milling_cost": """
        INSERT INTO processing_cost_calculation_details
            (job_id, subgraph_id, nc_milling_cost, calculation_steps)
        VALUES
            ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
        ON CONFLICT (job_id, subgraph_id)
        DO UPDATE SET
            nc_milling_cost = EXCLUDED.nc_milling_cost,
            calculation_steps = (
                SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
                FROM jsonb_array_elements(
                    COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
                ) AS elem
                WHERE elem->>'category' != $4::text
            ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
    """,
    "nc_drilling_cost": """
        INSERT INTO processing_cost_calculation_details
            (job_id, subgraph_id, nc_drilling_cost, calculation_steps)
        VALUES
            ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
        ON CONFLICT (job_id, subgraph_id)
        DO UPDATE SET
            nc_drilling_cost = EXCLUDED.nc_drilling_cost,
            calculation_steps = (
                SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
                FROM jsonb_array_elements(
                    COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
                ) AS elem
                WHERE elem->>'category' != $4::text
            ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
    """,
}


def _parse_range(text: str) -> dict[str, Any] | None:
    match = _RANGE_PATTERN.search(text or "")
    if not match:
        return None

    max_text = match.group("max").strip()
    if any(token in max_text for token in ("+", "∞", "inf", "INF", "无穷", "無窮")):
        max_value = float("inf")
    else:
        max_value = float(max_text)

    return {
        "min": float(match.group("min")),
        "max": max_value,
        "min_inclusive": match.group("left") == "[",
        "max_inclusive": match.group("right") == "]",
    }


def _build_work_hour_price_map(nc_prices: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    work_hour_prices: list[dict[str, Any]] = []

    for item in nc_prices:
        if item.get("sub_category") != "work_hour":
            continue

        min_num = str(item.get("min_num", "") or "")
        s_range = None
        l_range = None
        for range_match in _RANGE_PATTERN.finditer(min_num):
            parsed = _parse_range(range_match.group(0))
            if not parsed:
                continue
            if range_match.group("label") == "S":
                s_range = parsed
            elif range_match.group("label") == "L":
                l_range = parsed

        work_hour_prices.append(
            {
                "price": float(item.get("price", 0) or 0),
                "unit": item.get("unit", "元/小时"),
                "s_range": s_range,
                "l_range": l_range,
                "min_num": min_num,
            }
        )

    work_hour_prices.sort(key=lambda row: row["price"])
    return work_hour_prices


def _in_range(value: float, range_info: Mapping[str, Any] | None) -> bool:
    if not range_info:
        return False

    min_value = float(range_info["min"])
    max_value = float(range_info["max"])
    if range_info["min_inclusive"]:
        if value < min_value:
            return False
    elif value <= min_value:
        return False

    if max_value == float("inf"):
        return True

    if range_info["max_inclusive"]:
        return value <= max_value
    return value < max_value


def _determine_work_hour_price(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    work_hour_prices: Sequence[Mapping[str, Any]],
) -> tuple[float, str]:
    if not work_hour_prices:
        return 0.0, "No NC work hour price data"

    dimensions = sorted([length_mm or 0, width_mm or 0, thickness_mm or 0], reverse=True)
    longest = dimensions[0]
    shortest = dimensions[2]

    matched_prices = []
    for price_info in work_hour_prices:
        s_match = _in_range(shortest, price_info.get("s_range")) if price_info.get("s_range") else True
        l_match = _in_range(longest, price_info.get("l_range")) if price_info.get("l_range") else True
        if s_match and l_match:
            matched_prices.append(price_info)

    if matched_prices:
        selected = sorted(matched_prices, key=lambda item: item["price"], reverse=True)[0]
        return float(selected["price"]), f"Matched NC work hour price {selected['price']}"

    default_price = float(work_hour_prices[0]["price"])
    return default_price, f"No price range matched; using default {default_price}"


def _classify_nc_code(code: str) -> str:
    if code in {"精铣", "半精", "全精"}:
        return "nc_milling_cost"
    if code == "开粗":
        return "nc_roughing_cost"
    return "nc_drilling_cost"


async def _calculate_part_nc_time_cost(
    job_id: str,
    part: Mapping[str, Any],
    work_hour_prices: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    quantity = float(part.get("quantity", 1) or 1)
    length_mm = float(part.get("length_mm", 0) or 0)
    width_mm = float(part.get("width_mm", 0) or 0)
    thickness_mm = float(part.get("thickness_mm", 0) or 0)
    nc_time_cost_data = part.get("nc_time_cost")

    if not nc_time_cost_data:
        calculation_steps = [
            {
                "step": "check_nc_time_cost",
                "note": "nc_time_cost data is empty, skip NC time calculation",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "quantity": quantity,
                "nc_milling_cost": 0.0,
                "nc_roughing_cost": 0.0,
                "nc_drilling_cost": 0.0,
                "total_cost": 0.0,
                "note": "nc_time_cost data is empty, skipped calculation",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_milling_cost": 0.0,
                "nc_roughing_cost": 0.0,
                "nc_drilling_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    if isinstance(nc_time_cost_data, str):
        try:
            nc_time_cost_data = json.loads(nc_time_cost_data)
        except Exception as exc:
            calculation_steps = [
                {
                    "step": "parse_nc_time_cost",
                    "status": "failed",
                    "reason": f"JSON parse failed: {exc}",
                }
            ]
            return (
                {
                    "subgraph_id": subgraph_id,
                    "part_name": part_name,
                    "quantity": quantity,
                    "nc_milling_cost": 0.0,
                    "nc_roughing_cost": 0.0,
                    "nc_drilling_cost": 0.0,
                    "total_cost": 0.0,
                    "note": f"nc_time_cost JSON parse failed: {exc}",
                },
                {
                    "job_id": job_id,
                    "subgraph_id": subgraph_id,
                    "nc_milling_cost": 0.0,
                    "nc_roughing_cost": 0.0,
                    "nc_drilling_cost": 0.0,
                    "calculation_steps": calculation_steps,
                },
            )

    nc_details = nc_time_cost_data.get("nc_details", [])
    if not nc_details:
        calculation_steps = [
            {
                "step": "check_nc_details",
                "note": "nc_details is empty, skip NC time calculation",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "quantity": quantity,
                "nc_milling_cost": 0.0,
                "nc_roughing_cost": 0.0,
                "nc_drilling_cost": 0.0,
                "total_cost": 0.0,
                "note": "nc_details is empty, skipped calculation",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_milling_cost": 0.0,
                "nc_roughing_cost": 0.0,
                "nc_drilling_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    unit_price, price_reason = _determine_work_hour_price(
        length_mm, width_mm, thickness_mm, work_hour_prices
    )

    milling_hours = 0.0
    roughing_hours = 0.0
    drilling_hours = 0.0
    detail_steps: list[dict[str, Any]] = []

    for detail in nc_details:
        code = str(detail.get("code", "") or "")
        value = detail.get("value", 0)
        try:
            minutes = float(value)
        except (TypeError, ValueError):
            logger.warning("Invalid NC value for %s: %s", code, value)
            continue

        hours = minutes / 60.0
        category_field = _classify_nc_code(code)
        if category_field == "nc_milling_cost":
            milling_hours += hours
        elif category_field == "nc_roughing_cost":
            roughing_hours += hours
        else:
            drilling_hours += hours

        detail_steps.append(
            {
                "code": code,
                "minutes": minutes,
                "hours": round(hours, 4),
                "category": category_field,
            }
        )

    nc_milling_cost = milling_hours * unit_price * quantity
    nc_roughing_cost = roughing_hours * unit_price * quantity
    nc_drilling_cost = drilling_hours * unit_price * quantity
    total_cost = nc_milling_cost + nc_roughing_cost + nc_drilling_cost

    calculation_steps = [
        {
            "step": "determine_nc_work_hour_price",
            "dimensions": {
                "length_mm": length_mm,
                "width_mm": width_mm,
                "thickness_mm": thickness_mm,
            },
            "unit_price": unit_price,
            "reason": price_reason,
        },
        {
            "step": "classify_nc_details",
            "details": detail_steps,
            "summary": {
                "milling_hours": round(milling_hours, 4),
                "roughing_hours": round(roughing_hours, 4),
                "drilling_hours": round(drilling_hours, 4),
            },
        },
        {
            "step": "calculate_nc_time_cost",
            "quantity": quantity,
            "unit_price": unit_price,
            "formula": f"({round(milling_hours, 4)} + {round(roughing_hours, 4)} + {round(drilling_hours, 4)}) * {quantity} * {unit_price}",
            "nc_milling_cost": round(nc_milling_cost, 4),
            "nc_roughing_cost": round(nc_roughing_cost, 4),
            "nc_drilling_cost": round(nc_drilling_cost, 4),
            "total_cost": round(total_cost, 4),
        },
    ]

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "quantity": quantity,
        "nc_milling_cost": round(nc_milling_cost, 4),
        "nc_roughing_cost": round(nc_roughing_cost, 4),
        "nc_drilling_cost": round(nc_drilling_cost, 4),
        "total_cost": round(total_cost, 4),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "nc_milling_cost": nc_milling_cost,
        "nc_roughing_cost": nc_roughing_cost,
        "nc_drilling_cost": nc_drilling_cost,
        "calculation_steps": calculation_steps,
    }

    logger.info(
        "[%s] %s: unit_price=%.2f, milling=%.2f, roughing=%.2f, drilling=%.2f",
        subgraph_id,
        part_name,
        unit_price,
        nc_milling_cost,
        nc_roughing_cost,
        nc_drilling_cost,
    )
    return result, db_data


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return

    if field_name not in _NC_TIME_UPSERT_SQL:
        raise ValueError(f"Unsupported field_name for nc time calculator: {field_name}")

    tasks = [
        _upsert_single_record(
            update["job_id"],
            update["subgraph_id"],
            update["value"],
            category,
            update["steps"],
            field_name,
        )
        for update in updates
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failures = [result for result in results if isinstance(result, Exception)]
    if failures:
        raise failures[0]


async def _upsert_single_record(
    job_id: str,
    subgraph_id: str,
    field_value: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
    field_name: str,
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(_NC_TIME_UPSERT_SQL[field_name], job_id, subgraph_id, field_value, category, steps_json)
    return True


async def _batch_update_subgraphs(job_id: str, updates: Sequence[Mapping[str, Any]]) -> None:
    sql = """
        UPDATE subgraphs
        SET
            nc_milling_cost = $3,
            nc_roughing_cost = $4,
            drilling_cost = $5,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """

    tasks = [
        db.execute(
            sql,
            job_id,
            data["subgraph_id"],
            data["nc_milling_cost"],
            data["nc_roughing_cost"],
            data["nc_drilling_cost"],
        )
        for data in updates
    ]
    if tasks:
        await asyncio.gather(*tasks)


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    nc_data = search_data["nc"]

    if not job_id:
        job_id = base_data.get("job_id")

    parts = list(base_data.get("parts", []))
    if subgraph_ids:
        allowed = set(subgraph_ids)
        parts = [part for part in parts if part.get("subgraph_id") in allowed]

    work_hour_prices = _build_work_hour_price_map(nc_data.get("nc_prices", []))
    if not work_hour_prices:
        return {
            "job_id": job_id,
            "results": [],
            "message": "Missing NC work hour price data",
        }

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []
    for part in parts:
        result, db_data = await _calculate_part_nc_time_cost(job_id, part, work_hour_prices)
        results.append(result)
        db_updates.append(db_data)

    if db_updates:
        roughing_updates = [
            {
                "job_id": item["job_id"],
                "subgraph_id": item["subgraph_id"],
                "value": item["nc_roughing_cost"],
                "steps": item["calculation_steps"],
            }
            for item in db_updates
        ]
        milling_updates = [
            {
                "job_id": item["job_id"],
                "subgraph_id": item["subgraph_id"],
                "value": item["nc_milling_cost"],
                "steps": item["calculation_steps"],
            }
            for item in db_updates
        ]
        drilling_updates = [
            {
                "job_id": item["job_id"],
                "subgraph_id": item["subgraph_id"],
                "value": item["nc_drilling_cost"],
                "steps": item["calculation_steps"],
            }
            for item in db_updates
        ]

        await batch_upsert_with_steps(roughing_updates, "nc_roughing", "nc_roughing_cost")
        await batch_upsert_with_steps(milling_updates, "nc_milling", "nc_milling_cost")
        await batch_upsert_with_steps(drilling_updates, "nc_drilling", "nc_drilling_cost")
        await _batch_update_subgraphs(job_id, db_updates)

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


__all__ = ["MCP_TOOL_META", "batch_upsert_with_steps", "calculate", "calculate_sync"]
