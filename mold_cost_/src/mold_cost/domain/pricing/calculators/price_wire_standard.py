"""Wire standard pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any, Dict, List

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "calculate_wire_standard_price",
    "description": "Calculate wire standard base cost from part process data and standard pricing snapshots.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode and wire_standard results",
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
    "needs": ["base_itemcode", "wire_standard"],
}

_WIRE_STANDARD_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, standard_base_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        standard_base_cost = EXCLUDED.standard_base_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""

_WIRE_TYPE_ALIASES = {
    "slow_and_one": "slow",
    "slow_and_two": "slow",
    "slow": "slow",
    "middle": "middle",
    "medium": "middle",
    "fast": "fast",
    "慢丝": "slow",
    "中丝": "middle",
    "快丝": "fast",
}

_WIRE_TYPE_NOTE_ALIASES = {
    "慢丝": "slow",
    "中丝": "middle",
    "快丝": "fast",
}

_WIRE_STANDARD_KEYS = {
    "slow": {"slow", "slow_and_one", "slow_and_two"},
    "middle": {"middle", "medium"},
    "fast": {"fast"},
}


def _normalize_wire_type(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    if raw in _WIRE_TYPE_ALIASES:
        return _WIRE_TYPE_ALIASES[raw]
    lowered = raw.lower()
    return _WIRE_TYPE_ALIASES.get(lowered, lowered)


def _build_price_map(base_prices: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    price_map: dict[str, dict[str, Any]] = {}
    for price_item in base_prices:
        sub_category = price_item.get("sub_category")
        if not sub_category:
            continue
        key = str(sub_category).strip()
        payload = {
            "price": float(price_item.get("price", 0) or 0),
            "unit": price_item.get("unit", ""),
            "sub_category": key,
        }
        price_map[key] = payload
        price_map[key.lower()] = payload
    logger.info("Built wire standard price map with %s entries", len(price_map))
    return price_map


def _lookup_price_info(price_map: Mapping[str, Mapping[str, Any]], wire_process: str) -> dict[str, Any] | None:
    if not wire_process:
        return None

    candidates = [wire_process, wire_process.lower()]
    normalized_type = _normalize_wire_type(wire_process)
    if normalized_type:
        candidates.extend(_WIRE_STANDARD_KEYS.get(normalized_type, set()))

    for candidate in candidates:
        price_info = price_map.get(candidate)
        if price_info:
            return dict(price_info)
    return None


def _determine_wire_type(wire_process: str, wire_process_note: Any) -> str:
    normalized_process = _normalize_wire_type(wire_process)
    if normalized_process in {"slow", "middle", "fast"}:
        return normalized_process

    note = str(wire_process_note or "").strip()
    for hint, wire_type in _WIRE_TYPE_NOTE_ALIASES.items():
        if hint in note:
            return wire_type
    return normalized_process


def _resolve_base_fee(price_map: Mapping[str, Mapping[str, Any]], wire_type: str, quantity: float) -> tuple[float, str]:
    if wire_type == "middle":
        for key in ("中丝基本费", "middle_base_fee", "medium_base_fee"):
            price_info = price_map.get(key) or price_map.get(key.lower())
            if price_info:
                unit_price = float(price_info.get("price", 0) or 0)
                base_fee = quantity * unit_price
                return base_fee, f"中丝基本费: {quantity} * {unit_price} = {base_fee}"

    if wire_type == "fast":
        for key in ("快丝基本费", "fast_base_fee"):
            price_info = price_map.get(key) or price_map.get(key.lower())
            if price_info:
                unit_price = float(price_info.get("price", 0) or 0)
                base_fee = quantity * unit_price
                return base_fee, f"快丝基本费: {quantity} * {unit_price} = {base_fee}"

    return 0.0, ""


def _failure_result(
    *,
    job_id: str,
    subgraph_id: str,
    part_name: str,
    note: str,
    calculation_steps: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "standard_base_cost": 0.0,
            "note": note,
        },
        {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "standard_base_cost": 0.0,
            "calculation_steps": calculation_steps,
        },
    )


async def _calculate_part_price(
    job_id: str,
    part: Mapping[str, Any],
    price_map: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    wire_process_note = part.get("wire_process_note")
    wire_process = part.get("wire_process")
    boring_num = float(part.get("boring_num", 0) or 0)
    quantity = float(part.get("quantity", 1) or 1)
    metadata = part.get("metadata")

    logger.info(
        "Calculating wire standard for part: %s (%s), wire_process: %s, boring_num: %s",
        part_name,
        subgraph_id,
        wire_process,
        boring_num,
    )

    if not metadata:
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note="metadata涓虹┖锛岃烦杩囪绠?",
            calculation_steps=[
                {
                    "step": "妫€鏌etadata",
                    "note": "metadata涓虹┖锛岃烦杩囩嚎鍓叉爣鍑嗗熀鏈垂璁＄畻",
                }
            ],
        )

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception as exc:
            return _failure_result(
                job_id=job_id,
                subgraph_id=subgraph_id,
                part_name=part_name,
                note=f"metadata JSON瑙ｆ瀽澶辫触锛岃烦杩囪绠?",
                calculation_steps=[
                    {
                        "step": "瑙ｆ瀽metadata",
                        "status": "failed",
                        "reason": f"JSON瑙ｆ瀽澶辫触: {exc}",
                    }
                ],
            )

    if not isinstance(metadata, dict):
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note="metadata绫诲瀷閿欒锛岃烦杩囪绠?",
            calculation_steps=[
                {
                    "step": "妫€鏌etadata绫诲瀷",
                    "note": "metadata涓嶆槸瀛楀吀绫诲瀷锛岃烦杩囩嚎鍓叉爣鍑嗗熀鏈垂璁＄畻",
                }
            ],
        )

    if not wire_process:
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note="wire_process涓虹┖",
            calculation_steps=[
                {
                    "step": "鏁版嵁楠岃瘉",
                    "status": "failed",
                    "reason": "wire_process涓虹┖",
                    "standard_base_cost": 0.0,
                }
            ],
        )

    price_info = _lookup_price_info(price_map, str(wire_process))
    if not price_info:
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note=f"鏈壘鍒皐ire_process瀵瑰簲鐨勪环鏍? {wire_process}",
            calculation_steps=[
                {
                    "step": "鍖归厤宸ヨ壓",
                    "status": "failed",
                    "wire_process": wire_process,
                    "reason": f"鏈壘鍒皐ire_process瀵瑰簲鐨勪环鏍? {wire_process}",
                    "standard_base_cost": 0.0,
                }
            ],
        )

    unit_price = float(price_info["price"])
    unit = price_info["unit"]
    hole_cost = boring_num * unit_price
    wire_type = _determine_wire_type(str(wire_process), wire_process_note)
    base_fee, base_fee_desc = _resolve_base_fee(price_map, wire_type, quantity)
    standard_base_cost = hole_cost + base_fee

    calculation_steps = [
        {
            "step": "鍖归厤宸ヨ壓",
            "wire_process_note": wire_process_note,
            "wire_process": wire_process,
            "wire_type": wire_type,
            "matched_sub_category": price_info.get("sub_category", wire_process),
            "unit_price": unit_price,
            "unit": unit,
        },
        {
            "step": "璁＄畻瀛旂被璐?",
            "formula": f"{boring_num} * {unit_price}",
            "boring_num": boring_num,
            "unit_price": unit_price,
            "hole_cost": round(hole_cost, 4),
        },
    ]
    if base_fee > 0:
        calculation_steps.append(
            {
                "step": "璁＄畻鍩烘湰璐?",
                "description": base_fee_desc,
                "quantity": quantity,
                "base_fee": round(base_fee, 4),
            }
        )
    calculation_steps.append(
        {
            "step": "璁＄畻鎬昏垂鐢?",
            "formula": f"瀛旂被璐?+ 鍩烘湰璐?= {round(hole_cost, 4)} + {round(base_fee, 4)}",
            "standard_base_cost": round(standard_base_cost, 4),
        }
    )

    return (
        {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "wire_process_note": wire_process_note,
            "wire_process": wire_process,
            "wire_type": wire_type,
            "boring_num": boring_num,
            "quantity": quantity,
            "hole_cost": round(hole_cost, 4),
            "base_fee": round(base_fee, 4),
            "standard_base_cost": round(standard_base_cost, 4),
        },
        {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "standard_base_cost": standard_base_cost,
            "calculation_steps": calculation_steps,
        },
    )


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return
    if field_name != "standard_base_cost":
        raise ValueError(f"Unsupported field_name for wire standard calculator: {field_name}")

    logger.info("Batch updating %s records for category: %s", len(updates), category)
    tasks = [
        _upsert_single_record(
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
    job_id: str,
    subgraph_id: str,
    field_value: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    await db.execute(
        _WIRE_STANDARD_UPSERT_SQL,
        job_id,
        subgraph_id,
        field_value,
        category,
        json.dumps(list(steps), default=str),
    )
    return True


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    wire_standard_data = search_data["wire_standard"]

    if not job_id:
        job_id = base_data.get("job_id")

    logger.info(
        "Calculating wire standard for job_id: %s, parts count: %s",
        job_id,
        len(base_data.get("parts", [])),
    )

    price_map = _build_price_map(wire_standard_data.get("base_prices", []))

    parts = list(base_data.get("parts", []))
    if subgraph_ids:
        allowed = set(subgraph_ids)
        parts = [part for part in parts if part.get("subgraph_id") in allowed]

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []

    for part in parts:
        result, db_data = await _calculate_part_price(job_id, part, price_map)
        results.append(result)
        db_updates.append(db_data)

    if db_updates:
        await batch_upsert_with_steps(
            [
                {
                    "job_id": item["job_id"],
                    "subgraph_id": item["subgraph_id"],
                    "value": item["standard_base_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "wire_standard",
            "standard_base_cost",
        )

    logger.info("Completed calculation for %s parts", len(results))
    return {"job_id": job_id, "results": results}


def calculate_sync(
    search_data: Dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: List[str] | None = None,
) -> Dict[str, Any]:
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "batch_upsert_with_steps", "calculate", "calculate_sync"]
