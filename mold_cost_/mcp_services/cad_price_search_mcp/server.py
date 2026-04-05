"""
CAD 鍜屼环鏍兼悳绱?MCP 鏈嶅姟鍣?(SSE妯″紡)
鏁村悎 CAD 瑙ｆ瀽鍜屼环鏍艰绠楀姛鑳?绔彛锛?200

鑱岃矗锛?1. CAD 澶勭悊锛欴WG 鎷嗗浘銆佺壒寰佽瘑鍒?2. 浠锋牸鎼滅储锛氶浂浠朵俊鎭€佷环鏍间俊鎭绱?3. 浠锋牸璁＄畻锛氭潗鏂欒垂銆佸姞宸ヨ垂绛夎绠?"""
from shared.unified_logging import init_logging, get_logger
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.responses import JSONResponse
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn
import json
import sys
import os
from pathlib import Path
import asyncio
from dotenv import load_dotenv
import logging
from decimal import Decimal

# 鑷畾涔?JSON 缂栫爜鍣紝澶勭悊 Decimal 绫诲瀷
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# 鍔犺浇鐜鍙橀噺
load_dotenv()

# 娣诲姞椤圭洰鏍圭洰褰曞埌 Python 璺緞
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts" / "cad_chaitu"))
sys.path.insert(0, str(project_root / "scripts" / "recognition"))
sys.path.insert(0, str(project_root / "scripts"))

from refactor_bootstrap import ensure_src_path

ensure_src_path()

# 鍒濆鍖栫粺涓€鏃ュ織绯荤粺锛堢粺涓€鍒伴」鐩牴鐩綍鐨?logs 鏂囦欢澶癸級
init_logging(log_dir=str(project_root / "logs"))

# 浣跨敤鍥哄畾鐨勬ā鍧楀悕绉帮紝鑰屼笉鏄?__name__
# 杩欐牱鍗充娇浣滀负涓荤▼搴忚繍琛岋紝涔熻兘姝ｇ‘鍒嗙被鍒?mcp_services.log
logger = get_logger("mcp_services.cad_price_search_mcp.server")

# ============================================================================
# 瀵煎叆 CAD 澶勭悊妯″潡锛堝彲閫夛級
# ============================================================================
try:
    from mold_cost.domain.cad.services import cad_split_service
    from mold_cost.domain.features.services import feature_recognition_service
    # 中文说明：MCP 入口只持有领域服务，不再直接依赖 CAD/feature 脚本入口。
    CAD_AVAILABLE = True
    logger.info("[OK] CAD 澶勭悊妯″潡瀵煎叆鎴愬姛")
except ImportError as e:
    CAD_AVAILABLE = False
    logger.warning(f"[WARN] CAD 澶勭悊妯″潡瀵煎叆澶辫触: {e}")
    logger.warning("       CAD 鍔熻兘灏嗕笉鍙敤锛屼絾浠锋牸璁＄畻鍔熻兘浠嶅彲姝ｅ父浣跨敤")
    cad_split_service = None
    feature_recognition_service = None

# 瀵煎叆杩涘害鍙戝竷鍣?from shared.progress_publisher import ProgressPublisher
from shared.progress_stages import ProgressStage, ProgressPercent

# ============================================================================
# 瀵煎叆浠锋牸鎼滅储鍜岃绠楁ā鍧?# ============================================================================
from mold_cost.domain.pricing.search import (
    base_itemcode_search,
    material_search,
    heat_search,
    tooth_hole_search,
    water_mill_search,
    wire_base_search,
    wire_special_search,
    wire_standard_search,
    wire_total_search,
    nc_search,
    total_search,
    search,
    density_search  # 鏂板锛氬瘑搴︽绱?)

from mold_cost.domain.pricing.calculators import (
    price_material,
    price_heat,
    price_weight,
    price_tooth_hole,
    price_wire_base,
    price_wire_special,
    price_wire_standard,
    price_add_auto_material,
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
    price_wire_total,
    price_nc_base,
    price_nc_time,
    price_nc_total,
    price_total,
    judgment
)
from mold_cost.domain.pricing.services.pricing_service import pricing_service

# 鍒涘缓杩涘害鍙戝竷鍣ㄥ疄渚?try:
    progress_publisher = ProgressPublisher()
    logger.info("[OK] 杩涘害鍙戝竷鍣ㄥ垵濮嬪寲鎴愬姛")
except Exception as e:
    logger.warning(f"[WARN] 杩涘害鍙戝竷鍣ㄥ垵濮嬪寲澶辫触: {e}")
    logger.warning("       MCP 鏈嶅姟灏嗙户缁繍琛岋紝浣嗕笉浼氬彂甯冭繘搴?)
    progress_publisher = None

# 鍒涘缓 MCP 鏈嶅姟鍣?mcp_server = Server("cad-price-search-mcp")

# ============================================================================
# 宸ュ叿瀹氫箟
# ============================================================================

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """鍒楀嚭鎵€鏈夊彲鐢ㄥ伐鍏?- CAD宸ュ叿 + 浠锋牸宸ュ叿 Wind"""
    tools = []
    
    # ========== CAD 澶勭悊宸ュ叿 ==========
    cad_tools = [
        Tool(
            name="process_cad_and_features",
            description="瀹屾暣鐨?CAD 澶勭悊娴佺▼锛氫笅杞?DWG 鈫?鎷嗗浘 鈫?鐗瑰緛璇嗗埆",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "浠诲姟ID锛堝繀濉紝UUID鏍煎紡锛?
                    },
                    "dwg_url": {
                        "type": "string",
                        "description": "DWG 鏂囦欢鐨?URL 鎴?MinIO 璺緞锛堝彲閫夛級"
                    }
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="cad_chaitu",
            description="鍗曠嫭鐨?CAD 鎷嗗浘鍔熻兘锛氫笅杞?DWG 鈫?鎷嗗浘 鈫?涓婁紶瀛愬浘鍒?MinIO",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "浠诲姟ID锛堝繀濉紝UUID鏍煎紡锛?
                    },
                    "dwg_url": {
                        "type": "string",
                        "description": "DWG 鏂囦欢鐨?URL 鎴?MinIO 璺緞锛堝彲閫夛級"
                    }
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="feature_recognition",
            description="鍗曠嫭鐨勭壒寰佽瘑鍒姛鑳斤細浠?MinIO 涓嬭浇瀛愬浘 DXF 鈫?鎻愬彇鐗瑰緛 鈫?淇濆瓨鍒版暟鎹簱",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "浠诲姟ID锛堝繀濉紝UUID鏍煎紡锛?
                    },
                    "subgraph_id": {
                        "type": "string",
                        "description": "瀛愬浘ID锛堝彲閫夛紝涓嶆彁渚涘垯澶勭悊鎵€鏈夊瓙鍥撅級"
                    }
                },
                "required": ["job_id"]
            }
        )
    ]
    
    # ========== 浠锋牸鎼滅储宸ュ叿 ==========
    search_tool_configs = [
        ("search_base_itemcode", base_itemcode_search.MCP_TOOL_META),
        ("search_material", material_search.MCP_TOOL_META),
        ("search_heat", heat_search.MCP_TOOL_META),
        ("search_tooth_hole", tooth_hole_search.MCP_TOOL_META),
        ("search_water_mill", water_mill_search.MCP_TOOL_META),
        ("search_wire_base", wire_base_search.MCP_TOOL_META),
        ("search_wire_special", wire_special_search.MCP_TOOL_META),
        ("search_wire_standard", wire_standard_search.MCP_TOOL_META),
        ("search_wire_total", wire_total_search.MCP_TOOL_META),
        ("search_nc", nc_search.MCP_TOOL_META),
        ("search_total", total_search.MCP_TOOL_META),
        ("search_subgraphs_cost", search.MCP_TOOL_META),
        ("search_density", density_search.MCP_TOOL_META),  # 鏂板锛氬瘑搴︽绱?    ]
    
    # ========== 浠锋牸璁＄畻宸ュ叿 ==========
    calculate_tool_configs = [
        ("calculate_material_cost", price_material.MCP_TOOL_META),
        ("calculate_heat_treatment_cost", price_heat.MCP_TOOL_META),
        ("calculate_weight", price_weight.MCP_TOOL_META),
        ("calculate_tooth_hole_cost", price_tooth_hole.MCP_TOOL_META),
        ("calculate_wire_base_price", price_wire_base.MCP_TOOL_META),
        ("calculate_wire_special_price", price_wire_special.MCP_TOOL_META),
        ("calculate_wire_standard_price", price_wire_standard.MCP_TOOL_META),
        ("calculate_add_auto_material_cost", price_add_auto_material.MCP_TOOL_META),
        ("calculate_water_mill_bevel_cost", price_water_mill_bevel_cost.MCP_TOOL_META),
        ("calculate_water_mill_chamfer_cost", price_water_mill_chamfer_cost.MCP_TOOL_META),
        ("calculate_water_mill_component_price", price_water_mill_component.MCP_TOOL_META),
        ("calculate_water_mill_hanging_table_price", price_water_mill_hanging_table.MCP_TOOL_META),
        ("calculate_water_mill_high_cost", price_water_mill_high_cost.MCP_TOOL_META),
        ("calculate_water_mill_long_strip_price", price_water_mill_long_strip.MCP_TOOL_META),
        ("calculate_water_mill_oil_tank_cost", price_water_mill_oil_tank.MCP_TOOL_META),
        ("calculate_water_mill_plate_price", price_water_mill_plate.MCP_TOOL_META),
        ("calculate_water_mill_thread_ends_price", price_water_mill_thread_ends.MCP_TOOL_META),
        ("calculate_water_mill_total_cost", price_water_mill_total.MCP_TOOL_META),
        ("calculate_wire_total_cost", price_wire_total.MCP_TOOL_META),
        ("calculate_nc_base_cost", price_nc_base.MCP_TOOL_META),
        ("calculate_nc_time_cost", price_nc_time.MCP_TOOL_META),
        ("calculate_nc_total_cost", price_nc_total.MCP_TOOL_META),
        ("calculate_final_total_cost", price_total.MCP_TOOL_META),
        ("judgment_cleanup", judgment.MCP_TOOL_META),
        ("update_job_total_cost_only", {
            "name": "update_job_total_cost_only",
            "description": "鍙洿鏂?jobs.total_cost锛堜粠鎵€鏈夊瓙鍥炬眹鎬伙級锛屼笉鏇存柊 subgraphs",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "浠诲姟ID (UUID)"
                    }
                },
                "required": ["job_id"]
            }
        }),
    ]
    
    # 娣诲姞 CAD 宸ュ叿
    tools.extend(cad_tools)
    
    # 鐢熸垚浠锋牸鎼滅储宸ュ叿
    for tool_name, meta in search_tool_configs:
        tools.append(Tool(
            name=tool_name,
            description=meta["description"],
            inputSchema=meta["inputSchema"]
        ))
    
    # 鐢熸垚浠锋牸璁＄畻宸ュ叿
    for tool_name, meta in calculate_tool_configs:
        tools.append(Tool(
            name=tool_name,
            description=meta["description"],
            inputSchema=meta["inputSchema"]
        ))
    
    return tools

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """璋冪敤宸ュ叿 - 缁熶竴璺敱"""
    try:
        # ========== CAD 澶勭悊宸ュ叿璺敱 ==========
        if name == "process_cad_and_features":
            return await handle_process_cad_and_features(arguments)
        elif name == "cad_chaitu":
            return await handle_cad_chaitu(arguments)
        elif name == "feature_recognition":
            return await handle_feature_recognition(arguments)
        
        # ========== 浠锋牸宸ュ叿璺敱 ==========
        else:
            return await handle_price_tool(name, arguments)
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"[ERROR] 宸ュ叿鎵ц寮傚父: {e}")
        logger.error(error_detail)
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": f"宸ュ叿鎵ц寮傚父: {str(e)}",
                "detail": error_detail
            }, ensure_ascii=False, cls=DecimalEncoder)
        )]

# ============================================================================
# CAD 宸ュ叿澶勭悊鍑芥暟
# ============================================================================

async def handle_process_cad_and_features(arguments: dict) -> list[TextContent]:
    """瀹屾暣娴佺▼锛氭媶鍥?+ 鐗瑰緛璇嗗埆"""
    if not CAD_AVAILABLE:
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": "CAD 澶勭悊鍔熻兘涓嶅彲鐢紝璇峰畨瑁?ezdxf 鍜?minio 渚濊禆鍖?
            }, ensure_ascii=False)
        )]
    
    job_id = arguments.get("job_id")
    dwg_url = arguments.get("dwg_url")
    
    if not job_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": "job_id 鍙傛暟蹇呭～"
            }, ensure_ascii=False)
        )]
    
    logger.info(f">> 寮€濮嬪鐞?CAD 浠诲姟: {job_id}")
    
    # 姝ラ1: CAD 鎷嗗浘
    logger.info(f"[姝ラ1] 寮€濮?CAD 鎷嗗浘...")
    chaitu_result = await cad_split_service.split(dwg_url=dwg_url, job_id=job_id)
    
    if chaitu_result.get("status") != "ok":
        logger.error(f"[ERROR] CAD 鎷嗗浘澶辫触: {chaitu_result.get('message')}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": f"CAD 鎷嗗浘澶辫触: {chaitu_result.get('message')}",
                "chaitu_result": chaitu_result
            }, ensure_ascii=False)
        )]
    
    logger.info(f"[OK] CAD 鎷嗗浘瀹屾垚: {chaitu_result.get('message')}")
    
    # 姝ラ2: 鐗瑰緛璇嗗埆
    logger.info(f"[姝ラ2] 寮€濮嬬壒寰佽瘑鍒?..")
    # 中文说明：特征识别仍复用 legacy 实现，但必须经由 domain service 收口。
    feature_result = await asyncio.to_thread(
        feature_recognition_service.batch_recognize,
        job_id,
        None,
    )
    
    if not feature_result.get("success"):
        logger.error(f"[ERROR] 鐗瑰緛璇嗗埆澶辫触: {feature_result.get('message')}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": f"鐗瑰緛璇嗗埆澶辫触: {feature_result.get('message')}",
                "chaitu_result": chaitu_result,
                "feature_result": feature_result
            }, ensure_ascii=False)
        )]
    
    logger.info(f"[OK] 鐗瑰緛璇嗗埆瀹屾垚: {feature_result.get('message')}")
    
    # 杩斿洖瀹屾暣缁撴灉
    result = {
        "status": "ok",
        "message": "CAD 澶勭悊鍜岀壒寰佽瘑鍒畬鎴?,
        "job_id": job_id,
        "chaitu": chaitu_result,
        "features": feature_result
    }
    
    logger.info(f"[COMPLETE] 鎵€鏈夊鐞嗗畬鎴?")
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

async def handle_cad_chaitu(arguments: dict) -> list[TextContent]:
    """鍗曠嫭鐨勬媶鍥惧姛鑳?""
    if not CAD_AVAILABLE:
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": "CAD 澶勭悊鍔熻兘涓嶅彲鐢紝璇峰畨瑁?ezdxf 鍜?minio 渚濊禆鍖?
            }, ensure_ascii=False)
        )]
    
    job_id = arguments.get("job_id")
    dwg_url = arguments.get("dwg_url")
    
    if not job_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": "job_id 鍙傛暟蹇呭～"
            }, ensure_ascii=False)
        )]
    
    # 鍙戝竷杩涘害锛氭媶鍥惧紑濮?    if progress_publisher:
        logger.info(f"[DEBUG] 鍑嗗鍙戝竷鎷嗗浘寮€濮嬭繘搴? job_id={job_id}")
        progress_publisher.publish_progress(
            job_id=job_id,
            stage=ProgressStage.CAD_SPLIT_STARTED,
            progress=ProgressPercent.CAD_SPLIT_STARTED,
            message="姝ｅ湪鎷嗗浘...",
            details={"source": "mcp_service"}
        )
        logger.info(f"[SEND] 鍙戝竷杩涘害: 鎷嗗浘寮€濮?(job_id={job_id})")
    
    result = await cad_split_service.split(dwg_url=dwg_url, job_id=job_id)
    
    # 鍙戝竷杩涘害锛氭媶鍥惧畬鎴愭垨澶辫触
    if progress_publisher:
        if result.get("status") == "ok":
            data = result.get("data", {})
            total_count = data.get("total_count", 0)
            
            progress_publisher.publish_progress(
                job_id=job_id,
                stage=ProgressStage.CAD_SPLIT_COMPLETED,
                progress=ProgressPercent.CAD_SPLIT_COMPLETED,
                message=f"鎷嗗浘瀹屾垚锛岀敓鎴恵total_count}涓瓙鍥?,
                details={
                    "source": "mcp_service",
                    "subgraph_count": total_count
                }
            )
            logger.info(f"[SEND] 鍙戝竷杩涘害: 鎷嗗浘瀹屾垚 (job_id={job_id}, 瀛愬浘鏁?{total_count})")
        else:
            progress_publisher.publish_progress(
                job_id=job_id,
                stage=ProgressStage.CAD_SPLIT_FAILED,
                progress=ProgressPercent.CAD_SPLIT_STARTED,
                message=f"鎷嗗浘澶辫触: {result.get('message', '鏈煡閿欒')}",
                details={
                    "source": "mcp_service",
                    "error": result.get("message")
                }
            )
            logger.info(f"[SEND] 鍙戝竷杩涘害: 鎷嗗浘澶辫触 (job_id={job_id})")
    
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

async def handle_feature_recognition(arguments: dict) -> list[TextContent]:
    """鍗曠嫭鐨勭壒寰佽瘑鍒姛鑳?""
    if not CAD_AVAILABLE:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "message": "CAD 澶勭悊鍔熻兘涓嶅彲鐢紝璇峰畨瑁?ezdxf 鍜?minio 渚濊禆鍖?
            }, ensure_ascii=False)
        )]
    
    job_id = arguments.get("job_id")
    subgraph_id = arguments.get("subgraph_id")
    
    if not job_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "message": "job_id 鍙傛暟蹇呭～"
            }, ensure_ascii=False)
        )]

    # 中文说明：MCP 的单独 feature 工具也统一经过领域服务，避免外层散落脚本调用。
    result = await asyncio.to_thread(
        feature_recognition_service.batch_recognize,
        job_id,
        subgraph_id,
    )

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

# ============================================================================
# 浠锋牸宸ュ叿澶勭悊鍑芥暟
# ============================================================================

async def handle_price_tool(name: str, arguments: dict) -> list[TextContent]:
    """澶勭悊浠锋牸鐩稿叧宸ュ叿"""
    job_id = arguments.get("job_id")
    subgraph_ids = arguments.get("subgraph_ids", [])
    
    if not job_id:
        return [TextContent(
            type="text",
            text=json.dumps({"status": "error", "message": "job_id 鍙傛暟蹇呭～"}, ensure_ascii=False)
        )]
    
    logger.info(f"[OK] 璋冪敤宸ュ叿: {name}, job_id={job_id}, subgraph_ids={subgraph_ids}")
    
    # ========== 鎼滅储宸ュ叿璺敱 ==========
    if name == "search_base_itemcode":
        result = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_material":
        result = await material_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_heat":
        result = await heat_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_tooth_hole":
        result = await tooth_hole_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_water_mill":
        result = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_wire_base":
        result = await wire_base_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_wire_special":
        result = await wire_special_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_wire_standard":
        result = await wire_standard_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_wire_total":
        result = await wire_total_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_nc":
        result = await nc_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_total":
        result = await total_search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_subgraphs_cost":
        result = await search.search_by_job_id(job_id, subgraph_ids)
    elif name == "search_density":
        result = await density_search.search_by_job_id(job_id, subgraph_ids)
    
    # ========== 璁＄畻宸ュ叿璺敱 ==========
    elif name == "calculate_material_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        material_data = await material_search.search_by_job_id(job_id, subgraph_ids)
        density_data = await density_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "material": material_data, "density": density_data}
        result = await price_material.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_heat_treatment_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        heat_data = await heat_search.search_by_job_id(job_id, subgraph_ids)
        density_data = await density_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "heat": heat_data, "density": density_data}
        result = await price_heat.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_weight":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        density_data = await density_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "density": density_data}
        result = await price_weight.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_tooth_hole_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        tooth_hole_data = await tooth_hole_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "tooth_hole": tooth_hole_data}
        result = await price_tooth_hole.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_wire_base_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        wire_base_data = await wire_base_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "wire_base": wire_base_data}
        result = await price_wire_base.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_wire_special_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        wire_special_data = await wire_special_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "wire_special": wire_special_data}
        result = await price_wire_special.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_wire_standard_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        wire_standard_data = await wire_standard_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "wire_standard": wire_standard_data}
        result = await price_wire_standard.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_add_auto_material_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        material_data = await material_search.search_by_job_id(job_id, subgraph_ids)
        density_data = await density_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "material": material_data, "density": density_data}
        result = await price_add_auto_material.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_bevel_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_bevel_cost.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_chamfer_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_chamfer_cost.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_component_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_component.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_hanging_table_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_hanging_table.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_high_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_high_cost.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_long_strip_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_long_strip.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_oil_tank_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_oil_tank.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_plate_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_plate.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_thread_ends_price":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "water_mill": water_mill_data}
        result = await price_water_mill_thread_ends.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_water_mill_total_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        total_data = await total_search.search_by_job_id(job_id, subgraph_ids)
        water_mill_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "total": total_data, "water_mill": water_mill_data}
        result = await price_water_mill_total.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_wire_total_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        total_data = await total_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "total": total_data}
        result = await price_wire_total.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_nc_base_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        nc_data = await nc_search.search_by_job_id(job_id, subgraph_ids)
        wire_base_data = await wire_base_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "nc": nc_data, "wire_base": wire_base_data}
        result = await price_nc_base.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_nc_time_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        nc_data = await nc_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "nc": nc_data}
        result = await price_nc_time.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_nc_total_cost":
        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        total_data = await total_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data, "total": total_data}
        result = await price_nc_total.calculate(search_data, job_id, subgraph_ids)
        
    elif name == "calculate_final_total_cost":
        subgraphs_cost_data = await search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"subgraphs_cost": subgraphs_cost_data}
        logger.info(f"[MCP] calculate_final_total_cost: job_id={job_id}")
        result = await price_total.calculate(search_data, job_id, subgraph_ids)
        logger.info(f"[MCP] calculate_final_total_cost completed")
    
    elif name == "judgment_cleanup":
        # 鏁版嵁娓呯悊鍜屾牎楠?        base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
        search_data = {"base_itemcode": base_data}
        logger.info(f"[MCP] judgment_cleanup: job_id={job_id}")
        result = await judgment.calculate(search_data, job_id, subgraph_ids)
        logger.info(f"[MCP] judgment_cleanup completed")
    
    elif name == "update_job_total_cost_only":
        logger.info(f"[MCP] update_job_total_cost_only: job_id={job_id}")
        total_cost = await pricing_service.update_job_total_cost(job_id)
        result = {"status": "ok", "job_id": job_id, "total_cost": total_cost}
        logger.info(f"[MCP] update_job_total_cost_only completed: {total_cost:.2f}")
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, cls=DecimalEncoder))]
        
    else:
        return [TextContent(
            type="text",
            text=json.dumps({"status": "error", "message": f"鏈煡宸ュ叿: {name}"}, ensure_ascii=False)
        )]
    
    # 娣诲姞鐘舵€佸瓧娈?    if "status" not in result:
        result["status"] = "ok"
    
    logger.info(f"[OK] 宸ュ叿鎵ц瀹屾垚: {name}")
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, cls=DecimalEncoder))]

# ============================================================================
# 搴旂敤鍒涘缓鍑芥暟锛堜緵 mcp_services/main.py 璋冪敤锛?# ============================================================================

def create_app(host: str = "0.0.0.0", port: int = 8200):
    """
    鍒涘缓 MCP ASGI 搴旂敤
    
    Args:
        host: 鐩戝惉鍦板潃
        port: 鐩戝惉绔彛
    
    Returns:
        ASGI 搴旂敤锛堜緵 uvicorn 浣跨敤锛?    """
    # 鍒涘缓 SSE 浼犺緭灞?    sse = SseServerTransport("/messages")
    
    # 鍋ュ悍妫€鏌ョ鐐?    async def health_check(request):
        return JSONResponse({
            "status": "healthy",
            "service": "cad-price-search-mcp",
            "port": port,
            "features": {
                "cad": CAD_AVAILABLE,
                "pricing": True
            },
            "tools": {
                "cad": 3 if CAD_AVAILABLE else 0,
                "search": 12,
                "calculate": 23,
                "total": (3 if CAD_AVAILABLE else 0) + 35
            }
        })
    
    # 鐩存帴璋冪敤宸ュ叿鐨?HTTP 绔偣
    async def call_tool_http(request):
        try:
            body = await request.json()
            tool_name = body.get("tool_name")
            arguments = body.get("arguments", {})
            
            if not tool_name:
                return JSONResponse({"status": "error", "message": "缂哄皯 tool_name 鍙傛暟"}, status_code=400)
            
            logger.info(f"[HTTP] 璋冪敤宸ュ叿: {tool_name}")
            
            result_list = await call_tool(tool_name, arguments)
            
            if result_list and len(result_list) > 0:
                result_text = result_list[0].text
                result = json.loads(result_text)
            else:
                result = {"status": "error", "message": "宸ュ叿鏈繑鍥炵粨鏋?}
            
            logger.info(f"[HTTP] 宸ュ叿鎵ц瀹屾垚: {tool_name}")
            return JSONResponse(result)
        except Exception as e:
            import traceback
            logger.error(f"[HTTP] 宸ュ叿鎵ц澶辫触: {tool_name}, error={e}")
            return JSONResponse({
                "status": "error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }, status_code=500)
    
    # Starlette 璺敱
    starlette_app = Starlette(
        routes=[
            Route("/health", health_check),
            Route("/call_tool", call_tool_http, methods=["POST"]),
        ]
    )
    
    # 涓?ASGI 搴旂敤锛堝悎骞?SSE 鍜?HTTP 绔偣锛?    async def main_app(scope, receive, send):
        path = scope.get("path", "")
        
        if path in ["/health", "/call_tool"]:
            await starlette_app(scope, receive, send)
        elif path.startswith("/messages") or path.startswith("/sse"):
            if scope.get("method") == "GET":
                async with sse.connect_sse(scope, receive, send) as streams:
                    read_stream, write_stream = streams
                    await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())
            else:
                await sse.handle_post_message(scope, receive, send)
        else:
            await send({"type": "http.response.start", "status": 404, "headers": [[b"content-type", b"text/plain"]]})
            await send({"type": "http.response.body", "body": b"Not Found"})
    
    return main_app


