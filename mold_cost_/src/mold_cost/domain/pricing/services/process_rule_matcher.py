"""Process rule matcher domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ....infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)


async def match_and_update_process_rules(job_id: str, subgraph_ids: list[str]) -> dict[str, Any]:
    """Match process rules by part name and update empty wire process fields."""
    logger.info("[工艺规则匹配] 开始: job_id=%s, 子图数量=%s", job_id, len(subgraph_ids))

    try:
        subgraphs = await _fetch_subgraphs(job_id, subgraph_ids)
        if not subgraphs:
            logger.warning("[工艺规则匹配] 未找到子图数据")
            return {"status": "ok"}

        rules_map = await _fetch_process_rules()
        await asyncio.gather(*(_process_single_subgraph(item, rules_map) for item in subgraphs), return_exceptions=True)

        logger.info("[工艺规则匹配] 完成")
        return {"status": "ok"}
    except Exception as exc:
        logger.error("[工艺规则匹配] 失败: %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


async def _fetch_subgraphs(job_id: str, subgraph_ids: list[str]) -> list[dict[str, Any]]:
    sql = """
        SELECT subgraph_id, part_name, wire_process_note, wire_process
        FROM subgraphs
        WHERE job_id = $1::uuid AND subgraph_id = ANY($2)
    """
    rows = await db.fetch_all(sql, job_id, subgraph_ids)
    return [dict(row) for row in rows]


async def _fetch_process_rules() -> dict[str, dict[str, Any]]:
    sql = """
        SELECT name, description, conditions
        FROM process_rules
    """
    rows = await db.fetch_all(sql)
    return {
        row["name"]: {
            "description": row["description"],
            "conditions": row["conditions"],
        }
        for row in rows
    }


async def _process_single_subgraph(subgraph: dict[str, Any], rules_map: dict[str, dict[str, Any]]) -> None:
    if subgraph.get("wire_process_note") or subgraph.get("wire_process"):
        logger.debug("[跳过] %s: 已有工艺信息", subgraph.get("part_name"))
        return

    rule = rules_map.get(subgraph.get("part_name"))
    if not rule:
        logger.debug("[未匹配] %s: 未找到规则", subgraph.get("part_name"))
        return

    await _update_subgraph_process(
        subgraph_id=subgraph["subgraph_id"],
        wire_process_note=rule.get("description"),
        wire_process=rule.get("conditions"),
    )
    logger.info(
        "[更新成功] %s -> note=%s, process=%s",
        subgraph.get("part_name"),
        rule.get("description"),
        rule.get("conditions"),
    )


async def _update_subgraph_process(
    *,
    subgraph_id: str,
    wire_process_note: str | None,
    wire_process: str | None,
) -> None:
    sql = """
        UPDATE subgraphs
        SET wire_process_note = $1, wire_process = $2, updated_at = NOW()
        WHERE subgraph_id = $3
    """
    await db.execute(sql, wire_process_note, wire_process, subgraph_id)


__all__ = ["match_and_update_process_rules"]
