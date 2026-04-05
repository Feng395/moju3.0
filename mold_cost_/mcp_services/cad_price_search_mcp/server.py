"""Unified CAD and pricing MCP server."""

from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from shared.unified_logging import get_logger, init_logging


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


load_dotenv()

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))
sys.path.insert(0, str(project_root / "scripts" / "cad_chaitu"))
sys.path.insert(0, str(project_root / "scripts" / "recognition"))

from refactor_bootstrap import ensure_src_path

ensure_src_path()
init_logging(log_dir=str(project_root / "logs"))
logger = get_logger("mcp_services.cad_price_search_mcp.server")

try:
    from mold_cost.domain.cad.services import cad_split_service
    from mold_cost.domain.features.services import feature_recognition_service

    CAD_AVAILABLE = True
except ImportError as exc:
    CAD_AVAILABLE = False
    cad_split_service = None
    feature_recognition_service = None
    logger.warning("CAD services unavailable: %s", exc)

from mold_cost.domain.pricing.calculators import (
    judgment,
    price_add_auto_material,
    price_heat,
    price_material,
    price_nc_base,
    price_nc_time,
    price_nc_total,
    price_tooth_hole,
    price_total,
    price_water_mill_bevel_cost,
    price_water_mill_chamfer_cost,
    price_water_mill_component,
    price_water_mill_hanging_table,
    price_water_mill_high_cost,
    price_water_mill_long_strip,
    price_water_mill_oil_tank,
    price_water_mill_plate,
    price_water_mill_thread_ends,
    price_water_mill_total,
    price_weight,
    price_wire_base,
    price_wire_special,
    price_wire_standard,
    price_wire_total,
)
from mold_cost.domain.pricing.search import (
    base_itemcode_search,
    density_search,
    heat_search,
    material_search,
    nc_search,
    search,
    tooth_hole_search,
    total_search,
    water_mill_search,
    wire_base_search,
    wire_special_search,
    wire_standard_search,
    wire_total_search,
)
from mold_cost.domain.pricing.services.pricing_service import pricing_service

mcp_server = Server("cad-price-search-mcp")

CAD_TOOL_METAS = [
    {
        "name": "process_cad_and_features",
        "description": "Run CAD split and feature recognition for one job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID"},
                "dwg_url": {"type": "string", "description": "Optional DWG URL or object path"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "cad_chaitu",
        "description": "Run CAD split only for one job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID"},
                "dwg_url": {"type": "string", "description": "Optional DWG URL or object path"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "feature_recognition",
        "description": "Run feature recognition for one job or one subgraph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID"},
                "subgraph_id": {"type": "string", "description": "Optional subgraph ID"},
            },
            "required": ["job_id"],
        },
    },
]

PRICING_SEARCH_LOADERS = {
    "base_itemcode": base_itemcode_search.search_by_job_id,
    "material": material_search.search_by_job_id,
    "heat": heat_search.search_by_job_id,
    "tooth_hole": tooth_hole_search.search_by_job_id,
    "water_mill": water_mill_search.search_by_job_id,
    "wire_base": wire_base_search.search_by_job_id,
    "wire_special": wire_special_search.search_by_job_id,
    "wire_standard": wire_standard_search.search_by_job_id,
    "wire_total": wire_total_search.search_by_job_id,
    "nc": nc_search.search_by_job_id,
    "total": total_search.search_by_job_id,
    "subgraphs_cost": search.search_by_job_id,
    "density": density_search.search_by_job_id,
}

PRICING_SEARCH_TOOLS = {
    "search_base_itemcode": ("base_itemcode", base_itemcode_search.MCP_TOOL_META),
    "search_material": ("material", material_search.MCP_TOOL_META),
    "search_heat": ("heat", heat_search.MCP_TOOL_META),
    "search_tooth_hole": ("tooth_hole", tooth_hole_search.MCP_TOOL_META),
    "search_water_mill": ("water_mill", water_mill_search.MCP_TOOL_META),
    "search_wire_base": ("wire_base", wire_base_search.MCP_TOOL_META),
    "search_wire_special": ("wire_special", wire_special_search.MCP_TOOL_META),
    "search_wire_standard": ("wire_standard", wire_standard_search.MCP_TOOL_META),
    "search_wire_total": ("wire_total", wire_total_search.MCP_TOOL_META),
    "search_nc": ("nc", nc_search.MCP_TOOL_META),
    "search_total": ("total", total_search.MCP_TOOL_META),
    "search_subgraphs_cost": ("subgraphs_cost", search.MCP_TOOL_META),
    "search_density": ("density", density_search.MCP_TOOL_META),
}

PRICING_CALCULATOR_TOOLS = {
    "calculate_material_cost": (price_material.calculate, ("base_itemcode", "material", "density"), price_material.MCP_TOOL_META),
    "calculate_heat_treatment_cost": (price_heat.calculate, ("base_itemcode", "heat", "density"), price_heat.MCP_TOOL_META),
    "calculate_weight": (price_weight.calculate, ("base_itemcode", "density"), price_weight.MCP_TOOL_META),
    "calculate_tooth_hole_cost": (price_tooth_hole.calculate, ("base_itemcode", "tooth_hole"), price_tooth_hole.MCP_TOOL_META),
    "calculate_wire_base_price": (price_wire_base.calculate, ("base_itemcode", "wire_base"), price_wire_base.MCP_TOOL_META),
    "calculate_wire_special_price": (price_wire_special.calculate, ("base_itemcode", "wire_special"), price_wire_special.MCP_TOOL_META),
    "calculate_wire_standard_price": (price_wire_standard.calculate, ("base_itemcode", "wire_standard"), price_wire_standard.MCP_TOOL_META),
    "calculate_add_auto_material_cost": (price_add_auto_material.calculate, ("base_itemcode", "material", "density"), price_add_auto_material.MCP_TOOL_META),
    "calculate_water_mill_bevel_cost": (price_water_mill_bevel_cost.calculate, ("base_itemcode", "water_mill"), price_water_mill_bevel_cost.MCP_TOOL_META),
    "calculate_water_mill_chamfer_cost": (price_water_mill_chamfer_cost.calculate, ("base_itemcode", "water_mill"), price_water_mill_chamfer_cost.MCP_TOOL_META),
    "calculate_water_mill_component_price": (price_water_mill_component.calculate, ("base_itemcode", "water_mill"), price_water_mill_component.MCP_TOOL_META),
    "calculate_water_mill_hanging_table_price": (price_water_mill_hanging_table.calculate, ("base_itemcode", "water_mill"), price_water_mill_hanging_table.MCP_TOOL_META),
    "calculate_water_mill_high_cost": (price_water_mill_high_cost.calculate, ("base_itemcode", "water_mill"), price_water_mill_high_cost.MCP_TOOL_META),
    "calculate_water_mill_long_strip_price": (price_water_mill_long_strip.calculate, ("base_itemcode", "water_mill"), price_water_mill_long_strip.MCP_TOOL_META),
    "calculate_water_mill_oil_tank_cost": (price_water_mill_oil_tank.calculate, ("base_itemcode", "water_mill"), price_water_mill_oil_tank.MCP_TOOL_META),
    "calculate_water_mill_plate_price": (price_water_mill_plate.calculate, ("base_itemcode", "water_mill"), price_water_mill_plate.MCP_TOOL_META),
    "calculate_water_mill_thread_ends_price": (price_water_mill_thread_ends.calculate, ("base_itemcode", "water_mill"), price_water_mill_thread_ends.MCP_TOOL_META),
    "calculate_water_mill_total_cost": (price_water_mill_total.calculate, ("base_itemcode", "total", "water_mill"), price_water_mill_total.MCP_TOOL_META),
    "calculate_wire_total_cost": (price_wire_total.calculate, ("base_itemcode", "total"), price_wire_total.MCP_TOOL_META),
    "calculate_nc_base_cost": (price_nc_base.calculate, ("base_itemcode", "nc", "wire_base"), price_nc_base.MCP_TOOL_META),
    "calculate_nc_time_cost": (price_nc_time.calculate, ("base_itemcode", "nc"), price_nc_time.MCP_TOOL_META),
    "calculate_nc_total_cost": (price_nc_total.calculate, ("base_itemcode", "total"), price_nc_total.MCP_TOOL_META),
    "calculate_final_total_cost": (price_total.calculate, ("subgraphs_cost",), price_total.MCP_TOOL_META),
    "judgment_cleanup": (judgment.calculate, ("base_itemcode",), judgment.MCP_TOOL_META),
    "update_job_total_cost_only": (
        None,
        (),
        {
            "description": "Update jobs.total_cost from aggregated subgraph totals.",
            "inputSchema": {
                "type": "object",
                "properties": {"job_id": {"type": "string", "description": "Job ID"}},
                "required": ["job_id"],
            },
        },
    ),
}


def _json_response(payload: dict[str, Any]) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, cls=DecimalEncoder))]


async def _load_pricing_search_data(
    job_id: str,
    subgraph_ids: list[str],
    search_keys: tuple[str, ...],
) -> dict[str, Any]:
    search_data: dict[str, Any] = {}
    for search_key in search_keys:
        search_data[search_key] = await PRICING_SEARCH_LOADERS[search_key](job_id, subgraph_ids)
    return search_data


async def _execute_pricing_calculator(
    tool_name: str,
    job_id: str,
    subgraph_ids: list[str],
) -> dict[str, Any]:
    calculator, search_keys, _meta = PRICING_CALCULATOR_TOOLS[tool_name]
    if tool_name == "update_job_total_cost_only":
        total_cost = await pricing_service.update_job_total_cost(job_id)
        return {"status": "ok", "job_id": job_id, "total_cost": total_cost}
    search_data = await _load_pricing_search_data(job_id, subgraph_ids, search_keys)
    return await calculator(search_data, job_id, subgraph_ids)


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    tools: list[Tool] = []
    if CAD_AVAILABLE:
        for meta in CAD_TOOL_METAS:
            tools.append(Tool(name=meta["name"], description=meta["description"], inputSchema=meta["inputSchema"]))
    for tool_name, (_search_key, meta) in PRICING_SEARCH_TOOLS.items():
        tools.append(Tool(name=tool_name, description=meta["description"], inputSchema=meta["inputSchema"]))
    for tool_name, (_calculator, _search_keys, meta) in PRICING_CALCULATOR_TOOLS.items():
        tools.append(Tool(name=tool_name, description=meta["description"], inputSchema=meta["inputSchema"]))
    return tools


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "process_cad_and_features":
            return await handle_process_cad_and_features(arguments)
        if name == "cad_chaitu":
            return await handle_cad_chaitu(arguments)
        if name == "feature_recognition":
            return await handle_feature_recognition(arguments)
        return await handle_price_tool(name, arguments)
    except Exception as exc:
        import traceback

        logger.error("Tool execution failed: %s", exc, exc_info=True)
        return _json_response(
            {
                "status": "error",
                "message": f"Tool execution failed: {exc}",
                "detail": traceback.format_exc(),
            }
        )


async def handle_process_cad_and_features(arguments: dict) -> list[TextContent]:
    if not CAD_AVAILABLE:
        return _json_response({"status": "error", "message": "CAD processing is unavailable"})

    job_id = arguments.get("job_id")
    dwg_url = arguments.get("dwg_url")
    if not job_id:
        return _json_response({"status": "error", "message": "job_id is required"})

    split_result = await cad_split_service.split(dwg_url=dwg_url, job_id=job_id)
    if split_result.get("status") != "ok":
        return _json_response(split_result)

    feature_result = await asyncio.to_thread(feature_recognition_service.batch_recognize, job_id, None)
    return _json_response(
        {
            "status": "ok" if feature_result.get("status") == "ok" else "partial",
            "job_id": job_id,
            "cad_split": split_result,
            "feature_recognition": feature_result,
        }
    )


async def handle_cad_chaitu(arguments: dict) -> list[TextContent]:
    if not CAD_AVAILABLE:
        return _json_response({"status": "error", "message": "CAD processing is unavailable"})

    job_id = arguments.get("job_id")
    dwg_url = arguments.get("dwg_url")
    if not job_id:
        return _json_response({"status": "error", "message": "job_id is required"})

    result = await cad_split_service.split(dwg_url=dwg_url, job_id=job_id)
    return _json_response(result)


async def handle_feature_recognition(arguments: dict) -> list[TextContent]:
    if not CAD_AVAILABLE:
        return _json_response({"status": "error", "message": "CAD processing is unavailable"})

    job_id = arguments.get("job_id")
    subgraph_id = arguments.get("subgraph_id")
    if not job_id:
        return _json_response({"status": "error", "message": "job_id is required"})

    result = await asyncio.to_thread(feature_recognition_service.batch_recognize, job_id, subgraph_id)
    return _json_response(result)


async def handle_price_tool(name: str, arguments: dict) -> list[TextContent]:
    job_id = arguments.get("job_id")
    subgraph_ids = arguments.get("subgraph_ids", [])
    if not job_id:
        return _json_response({"status": "error", "message": "job_id is required"})

    logger.info("Pricing MCP tool called: %s job_id=%s subgraph_count=%s", name, job_id, len(subgraph_ids))

    if name in PRICING_SEARCH_TOOLS:
        search_key, _meta = PRICING_SEARCH_TOOLS[name]
        result = await PRICING_SEARCH_LOADERS[search_key](job_id, subgraph_ids)
    elif name in PRICING_CALCULATOR_TOOLS:
        result = await _execute_pricing_calculator(name, job_id, subgraph_ids)
    else:
        return _json_response({"status": "error", "message": f"Unknown tool: {name}"})

    if "status" not in result:
        result["status"] = "ok"
    return _json_response(result)


def create_app(host: str = "0.0.0.0", port: int = 8200):
    sse = SseServerTransport("/messages")

    async def health_check(request):
        return JSONResponse(
            {
                "status": "healthy",
                "service": "cad-price-search-mcp",
                "port": port,
                "features": {"cad": CAD_AVAILABLE, "pricing": True},
                "tools": {
                    "cad": len(CAD_TOOL_METAS) if CAD_AVAILABLE else 0,
                    "search": len(PRICING_SEARCH_TOOLS),
                    "calculate": len(PRICING_CALCULATOR_TOOLS),
                    "total": (len(CAD_TOOL_METAS) if CAD_AVAILABLE else 0)
                    + len(PRICING_SEARCH_TOOLS)
                    + len(PRICING_CALCULATOR_TOOLS),
                },
            }
        )

    async def call_tool_http(request):
        try:
            body = await request.json()
            tool_name = body.get("tool_name")
            arguments = body.get("arguments", {})
            if not tool_name:
                return JSONResponse({"status": "error", "message": "Missing tool_name"}, status_code=400)

            result_list = await call_tool(tool_name, arguments)
            if not result_list:
                return JSONResponse({"status": "error", "message": "Tool returned no result"}, status_code=500)
            return JSONResponse(json.loads(result_list[0].text))
        except Exception as exc:
            import traceback

            logger.error("HTTP tool execution failed: %s", exc, exc_info=True)
            return JSONResponse(
                {
                    "status": "error",
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
                status_code=500,
            )

    starlette_app = Starlette(
        routes=[
            Route("/health", health_check),
            Route("/call_tool", call_tool_http, methods=["POST"]),
        ]
    )

    async def main_app(scope, receive, send):
        path = scope.get("path", "")
        if path in {"/health", "/call_tool"}:
            await starlette_app(scope, receive, send)
            return
        if path.startswith("/messages") or path.startswith("/sse"):
            if scope.get("method") == "GET":
                async with sse.connect_sse(scope, receive, send) as streams:
                    read_stream, write_stream = streams
                    await mcp_server.run(
                        read_stream,
                        write_stream,
                        mcp_server.create_initialization_options(),
                    )
            else:
                await sse.handle_post_message(scope, receive, send)
            return
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Not Found"})

    return main_app


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8200
    app = create_app(port=port)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

