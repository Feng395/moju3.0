"""
NC总费用计算脚本
负责人：李志鹏

计算流程：
1. 从 total_search 获取 nc_roughing_cost、nc_milling_cost、nc_drilling_cost、nc_base_roughing_cost、nc_base_milling_cost、nc_base_drilling_cost
2. 每个NC费用项单独与对应的基本费用比较，取较大值：
   - final_nc_roughing_cost = max(nc_roughing_cost, nc_base_roughing_cost) if nc_roughing_cost > 0 else 0
   - final_nc_milling_cost = max(nc_milling_cost, nc_base_milling_cost) if nc_milling_cost > 0 else 0
   - final_nc_drilling_cost = max(nc_drilling_cost, nc_base_drilling_cost) if nc_drilling_cost > 0 else 0
3. 更新 subgraphs 表的 nc_roughing_cost、nc_milling_cost、drilling_cost 字段

示例：
  nc_roughing_cost = 100, nc_base_roughing_cost = 80
  nc_milling_cost = 0, nc_base_milling_cost = 60
  nc_drilling_cost = 30, nc_base_drilling_cost = 80
  结果：
  - final_nc_roughing_cost = max(100, 80) = 100（使用原值）
  - final_nc_milling_cost = 0（无精铣数据，不使用基本费）
  - final_nc_drilling_cost = max(30, 80) = 80（使用基本费）
"""
from shared.unified_logging import get_logger
from typing import List, Dict, Any, Tuple
from decimal import Decimal
import logging
import asyncio

from refactor_bootstrap import ensure_src_path

# 中文注释：脚本直接依赖 infrastructure，避免再穿过 api_gateway 兼容层。
ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

# MCP 工具元数据
MCP_TOOL_META = {
    "name": "calculate_nc_total_cost",
    "description": "计算NC总费用：比较nc_sum和nc_base_cost，更新subgraphs表",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "检索数据，包含 total"
            },
            "job_id": {
                "type": "string",
                "description": "任务ID (UUID)"
            },
            "subgraph_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "子图ID列表"
            }
        },
        "required": ["search_data"]
    },
    "handler": "calculate",
    "needs": ["total"]
}


async def calculate(
    search_data: Dict[str, Any],
    job_id: str = None,
    subgraph_ids: List[str] = None
) -> Dict[str, Any]:
    """
    计算NC总费用并更新 subgraphs 表
    
    Args:
        search_data: 检索数据，包含 total
        job_id: 任务ID（可选）
        subgraph_ids: 子图ID列表（可选）
        
    Returns:
        Dict: 计算结果
    """
    # 获取检索数据
    total_data = search_data.get("total")
    
    if not total_data:
        logger.warning("Missing total data, skipping NC total cost calculation")
        return {
            "job_id": job_id if job_id else "unknown",
            "results": [],
            "note": "缺少 total 数据，跳过NC总费用计算"
        }
    
    # 提取 job_id（如果未传入）
    if not job_id:
        job_id = total_data.get("job_id")
    
    cost_details = total_data.get("cost_details", [])
    
    logger.info(f"Calculating NC total cost for job_id: {job_id}, parts count: {len(cost_details)}")
    
    # 计算每个零件的NC费用
    results = []
    db_updates = []
    
    for detail in cost_details:
        result, db_data = _calculate_part_nc_total(detail)
        results.append(result)
        if db_data:
            db_updates.append(db_data)
    
    # 批量更新 subgraphs 表
    if db_updates:
        await _batch_update_subgraphs(job_id, db_updates)
        
        # 使用标准方法批量更新 calculation_steps
        from ._batch_update_helper import batch_upsert_with_steps
        updates_for_batch = [
            {
                "job_id": job_id,
                "subgraph_id": d["subgraph_id"],
                "value": None,  # nc_total 不需要更新字段值
                "steps": d["calculation_steps"]
            }
            for d in db_updates
        ]
        await batch_upsert_with_steps(updates_for_batch, "nc_total", None)
    
    logger.info(f"Completed NC total cost calculation for {len(results)} parts")
    
    return {
        "job_id": job_id,
        "results": results
    }


def _calculate_part_nc_total(detail: Dict) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    计算单个零件的NC总费用
    
    逻辑：
    - 每个NC费用项与对应的基本费用比较：
      - 如果原始费用 > 0，则与对应的基本费用比较取较大值
      - 如果原始费用 = 0，说明没有该工序，直接使用 0
    
    Args:
        detail: 成本明细数据
        
    Returns:
        tuple: (result_dict, db_update_dict)
    """
    subgraph_id = detail["subgraph_id"]
    
    # 获取各项NC成本
    nc_roughing_cost = Decimal(str(detail.get("nc_roughing_cost", 0)))
    nc_milling_cost = Decimal(str(detail.get("nc_milling_cost", 0)))
    nc_drilling_cost = Decimal(str(detail.get("nc_drilling_cost", 0)))
    
    # 获取各项NC基本费用
    nc_base_roughing_cost = Decimal(str(detail.get("nc_base_roughing_cost", 0)))
    nc_base_milling_cost = Decimal(str(detail.get("nc_base_milling_cost", 0)))
    nc_base_drilling_cost = Decimal(str(detail.get("nc_base_drilling_cost", 0)))
    
    # 每个费用项的逻辑：
    # - 如果原始费用 > 0，则与对应的基本费用比较取较大值
    # - 如果原始费用 = 0，说明没有该工序，直接使用 0
    final_nc_roughing_cost = max(nc_roughing_cost, nc_base_roughing_cost) if nc_roughing_cost > 0 else Decimal(0)
    final_nc_milling_cost = max(nc_milling_cost, nc_base_milling_cost) if nc_milling_cost > 0 else Decimal(0)
    final_nc_drilling_cost = max(nc_drilling_cost, nc_base_drilling_cost) if nc_drilling_cost > 0 else Decimal(0)
    
    # 构建比较说明
    comparisons = []
    
    if nc_roughing_cost > 0:
        if nc_roughing_cost >= nc_base_roughing_cost:
            comparisons.append(f"开粗: {float(nc_roughing_cost):.2f} >= {float(nc_base_roughing_cost):.2f}，使用{float(nc_roughing_cost):.2f}")
        else:
            comparisons.append(f"开粗: {float(nc_roughing_cost):.2f} < {float(nc_base_roughing_cost):.2f}，使用{float(nc_base_roughing_cost):.2f}")
    else:
        comparisons.append(f"开粗: 无数据，使用0")
    
    if nc_milling_cost > 0:
        if nc_milling_cost >= nc_base_milling_cost:
            comparisons.append(f"精铣: {float(nc_milling_cost):.2f} >= {float(nc_base_milling_cost):.2f}，使用{float(nc_milling_cost):.2f}")
        else:
            comparisons.append(f"精铣: {float(nc_milling_cost):.2f} < {float(nc_base_milling_cost):.2f}，使用{float(nc_base_milling_cost):.2f}")
    else:
        comparisons.append(f"精铣: 无数据，使用0")
    
    if nc_drilling_cost > 0:
        if nc_drilling_cost >= nc_base_drilling_cost:
            comparisons.append(f"钻床: {float(nc_drilling_cost):.2f} >= {float(nc_base_drilling_cost):.2f}，使用{float(nc_drilling_cost):.2f}")
        else:
            comparisons.append(f"钻床: {float(nc_drilling_cost):.2f} < {float(nc_base_drilling_cost):.2f}，使用{float(nc_base_drilling_cost):.2f}")
    else:
        comparisons.append(f"钻床: 无数据，使用0")
    
    reason = "每项单独与对应基本费用比较取较大值，无数据的项目使用0：" + "；".join(comparisons)
    
    # 转换为 float
    final_nc_roughing_cost_float = float(final_nc_roughing_cost)
    final_nc_milling_cost_float = float(final_nc_milling_cost)
    final_nc_drilling_cost_float = float(final_nc_drilling_cost)
    
    logger.info(
        f"[{subgraph_id}] {reason} -> "
        f"nc_roughing_cost={final_nc_roughing_cost_float:.2f}, "
        f"nc_milling_cost={final_nc_milling_cost_float:.2f}, "
        f"drilling_cost={final_nc_drilling_cost_float:.2f}"
    )
    
    # 构建计算步骤
    nc_total_calculation_steps = [
        {
            "step": "获取原始NC费用",
            "nc_roughing_cost": float(nc_roughing_cost),
            "nc_milling_cost": float(nc_milling_cost),
            "nc_drilling_cost": float(nc_drilling_cost)
        },
        {
            "step": "获取NC基本费用",
            "nc_base_roughing_cost": float(nc_base_roughing_cost),
            "nc_base_milling_cost": float(nc_base_milling_cost),
            "nc_base_drilling_cost": float(nc_base_drilling_cost)
        },
        {
            "step": "比较并确定最终费用",
            "note": "有数据的工序与对应基本费用比较取较大值，无数据的工序使用0",
            "roughing": {
                "has_data": nc_roughing_cost > 0,
                "original": float(nc_roughing_cost),
                "base": float(nc_base_roughing_cost),
                "final": final_nc_roughing_cost_float,
                "formula": f"max({float(nc_roughing_cost):.2f}, {float(nc_base_roughing_cost):.2f}) = {final_nc_roughing_cost_float:.2f}" if nc_roughing_cost > 0 else "无数据，使用0"
            },
            "milling": {
                "has_data": nc_milling_cost > 0,
                "original": float(nc_milling_cost),
                "base": float(nc_base_milling_cost),
                "final": final_nc_milling_cost_float,
                "formula": f"max({float(nc_milling_cost):.2f}, {float(nc_base_milling_cost):.2f}) = {final_nc_milling_cost_float:.2f}" if nc_milling_cost > 0 else "无数据，使用0"
            },
            "drilling": {
                "has_data": nc_drilling_cost > 0,
                "original": float(nc_drilling_cost),
                "base": float(nc_base_drilling_cost),
                "final": final_nc_drilling_cost_float,
                "formula": f"max({float(nc_drilling_cost):.2f}, {float(nc_base_drilling_cost):.2f}) = {final_nc_drilling_cost_float:.2f}" if nc_drilling_cost > 0 else "无数据，使用0"
            }
        },
        {
            "step": "汇总最终NC费用",
            "nc_roughing_cost": final_nc_roughing_cost_float,
            "nc_milling_cost": final_nc_milling_cost_float,
            "drilling_cost": final_nc_drilling_cost_float,
            "formula": f"{final_nc_roughing_cost_float:.2f} + {final_nc_milling_cost_float:.2f} + {final_nc_drilling_cost_float:.2f} = {(final_nc_roughing_cost_float + final_nc_milling_cost_float + final_nc_drilling_cost_float):.2f}",
            "total": final_nc_roughing_cost_float + final_nc_milling_cost_float + final_nc_drilling_cost_float
        }
    ]
    
    # 返回结果
    result = {
        "subgraph_id": subgraph_id,
        "reason": reason,
        "original": {
            "nc_roughing_cost": float(nc_roughing_cost),
            "nc_milling_cost": float(nc_milling_cost),
            "nc_drilling_cost": float(nc_drilling_cost),
            "nc_base_roughing_cost": float(nc_base_roughing_cost),
            "nc_base_milling_cost": float(nc_base_milling_cost),
            "nc_base_drilling_cost": float(nc_base_drilling_cost)
        },
        "comparisons": {
            "roughing": {
                "original": float(nc_roughing_cost),
                "base": float(nc_base_roughing_cost),
                "final": final_nc_roughing_cost_float,
                "used": "original" if nc_roughing_cost > 0 and nc_roughing_cost >= nc_base_roughing_cost else ("base" if nc_roughing_cost > 0 else "none")
            },
            "milling": {
                "original": float(nc_milling_cost),
                "base": float(nc_base_milling_cost),
                "final": final_nc_milling_cost_float,
                "used": "original" if nc_milling_cost > 0 and nc_milling_cost >= nc_base_milling_cost else ("base" if nc_milling_cost > 0 else "none")
            },
            "drilling": {
                "original": float(nc_drilling_cost),
                "base": float(nc_base_drilling_cost),
                "final": final_nc_drilling_cost_float,
                "used": "original" if nc_drilling_cost > 0 and nc_drilling_cost >= nc_base_drilling_cost else ("base" if nc_drilling_cost > 0 else "none")
            }
        },
        "final": {
            "nc_roughing_cost": final_nc_roughing_cost_float,
            "nc_milling_cost": final_nc_milling_cost_float,
            "drilling_cost": final_nc_drilling_cost_float
        }
    }
    
    db_data = {
        "subgraph_id": subgraph_id,
        "nc_roughing_cost": str(final_nc_roughing_cost_float),  # 转换为字符串
        "nc_milling_cost": str(final_nc_milling_cost_float),    # 转换为字符串
        "drilling_cost": str(final_nc_drilling_cost_float),      # 转换为字符串
        "calculation_steps": nc_total_calculation_steps  # 新增：计算步骤
    }
    
    return result, db_data


async def _batch_update_subgraphs(job_id: str, updates: List[Dict]):
    """
    批量更新 subgraphs 表的 nc_roughing_cost、nc_milling_cost、drilling_cost 字段
    
    Args:
        job_id: 任务ID
        updates: 更新数据列表
    """
    logger.info(f"Batch updating {len(updates)} records to subgraphs table")
    
    # 构建批量更新 SQL
    sql = """
        UPDATE subgraphs
        SET 
            nc_roughing_cost = $3,
            nc_milling_cost = $4,
            drilling_cost = $5,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """
    
    try:
        # 并发执行所有更新
        tasks = []
        for data in updates:
            tasks.append(db.execute(
                sql,
                job_id,
                data["subgraph_id"],
                data["nc_roughing_cost"],
                data["nc_milling_cost"],
                data["drilling_cost"]
            ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有错误
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to update subgraph {updates[i]['subgraph_id']}: {result}")
            else:
                success_count += 1
        
        logger.info(f"Successfully updated {success_count}/{len(updates)} records")
        
        # 如果有失败的，抛出异常
        if success_count < len(updates):
            raise Exception(f"Only {success_count}/{len(updates)} records updated successfully")
    
    except Exception as e:
        logger.error(f"Failed to batch update subgraphs: {e}")
        raise


# 便捷同步调用接口
def calculate_sync(search_data: Dict[str, Any], job_id: str = None, subgraph_ids: List[str] = None) -> Dict[str, Any]:
    """同步版本的计算接口"""
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


# 测试入口
if __name__ == "__main__":
    import sys
    import os
    
    # 添加项目根目录到Python路径
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, project_root)
    
    # 日志已统一配置，无需重复初始化
# logging.basicConfig(...)
    
    if len(sys.argv) < 3:
        print("Usage: python price_nc_total.py <job_id> <subgraph_id1> [subgraph_id2 ...]")
        sys.exit(1)
    
    job_id = sys.argv[1]
    subgraph_ids = sys.argv[2:]
    
    # 这里需要先调用检索脚本获取数据
    print("请通过 MCP 服务或 API 调用此计算脚本")
    print(f"job_id: {job_id}")
    print(f"subgraph_ids: {subgraph_ids}")
