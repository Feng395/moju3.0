"""
最终总价计算脚本（阶段 8）
负责人：李志鹏

计算流程：
1. 从 search.py (subgraphs_cost_search) 获取各项成本
2. 计算加工成本总计：large_grinding_cost + small_grinding_cost + slow_wire_cost + 
                    slow_wire_side_cost + mid_wire_cost + fast_wire_cost + edm_cost +
                    nc_roughing_cost + nc_milling_cost + drilling_cost
3. 计算总价：material_cost + heat_treatment_cost + processing_cost_total
4. 更新 subgraphs 表的 total_cost 和 processing_cost_total 字段
5. 生成并更新工艺描述（process_description）
6. 累加所有 subgraph 的 total_cost，更新 jobs 表的 total_cost 字段
"""
from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
import logging
import asyncio

from api_gateway.database import db

logger = logging.getLogger(__name__)

# MCP 工具元数据
MCP_TOOL_META = {
    "name": "calculate_final_total_cost",
    "description": "计算最终总价和加工成本总计：汇总所有成本项，更新 subgraphs 表和 jobs 表",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "检索数据，包含 subgraphs_cost"
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
    "needs": ["subgraphs_cost"],
    "depends_on": ["search_subgraphs_cost_by_job_id"]
}


async def calculate(
    search_data: Dict[str, Any],
    job_id: str = None,
    subgraph_ids: List[str] = None
) -> Dict[str, Any]:
    """
    计算最终总价并更新 subgraphs 表，然后累加更新 jobs 表
    
    Args:
        search_data: 检索数据，包含 subgraphs_cost
        job_id: 任务ID（可选）
        subgraph_ids: 子图ID列表（可选）
        
    Returns:
        Dict: 计算结果
    """
    # 获取检索数据
    subgraphs_cost_data = search_data.get("subgraphs_cost")
    
    if not subgraphs_cost_data:
        logger.warning("Missing subgraphs_cost data, skipping final total cost calculation")
        return {
            "job_id": job_id if job_id else "unknown",
            "job_total_cost": 0.0,
            "parts_count": 0,
            "results": [],
            "note": "缺少 subgraphs_cost 数据，跳过最终总价计算"
        }
    
    # 提取 job_id（如果未传入）
    if not job_id:
        job_id = subgraphs_cost_data.get("job_id")
    
    cost_summary = subgraphs_cost_data.get("cost_summary", [])
    
    logger.info(f"Calculating final total cost for job_id: {job_id}, parts count: {len(cost_summary)}")
    
    # 计算每个零件的总价
    results = []
    db_updates = []
    job_total_cost = Decimal("0")  # 累加所有零件的总价
    
    for summary in cost_summary:
        result, db_data = _calculate_part_total(summary)
        results.append(result)
        if db_data:
            db_updates.append(db_data)
            job_total_cost += Decimal(str(db_data["total_cost"]))
    
    # 批量更新 subgraphs 表
    if db_updates:
        await _batch_update_subgraphs(job_id, db_updates)
    
    # 生成并更新工艺描述
    await _update_process_descriptions(job_id, [data["subgraph_id"] for data in db_updates])
    
    # 更新 jobs 表的 total_cost
    job_total_cost_float = float(job_total_cost)
    await _update_job_total_cost(job_id, job_total_cost_float)
    
    logger.info(f"Completed calculation for {len(results)} parts, job total_cost: {job_total_cost_float:.2f}")
    
    return {
        "job_id": job_id,
        "job_total_cost": job_total_cost_float,
        "parts_count": len(results),
        "results": results
    }


def _calculate_part_total(summary: Dict) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    计算单个零件的最终总价和加工成本总计
    
    Args:
        summary: 成本汇总数据
        
    Returns:
        tuple: (result_dict, db_update_dict)
    """
    subgraph_id = summary["subgraph_id"]
    
    # 获取各项成本，添加异常处理
    try:
        material_cost = Decimal(str(summary.get("material_cost", 0)))
        heat_treatment_cost = Decimal(str(summary.get("heat_treatment_cost", 0)))
        large_grinding_cost = Decimal(str(summary.get("large_grinding_cost", 0)))
        small_grinding_cost = Decimal(str(summary.get("small_grinding_cost", 0)))
        slow_wire_cost = Decimal(str(summary.get("slow_wire_cost", 0)))
        slow_wire_side_cost = Decimal(str(summary.get("slow_wire_side_cost", 0)))
        mid_wire_cost = Decimal(str(summary.get("mid_wire_cost", 0)))
        fast_wire_cost = Decimal(str(summary.get("fast_wire_cost", 0)))
        edm_cost = Decimal(str(summary.get("edm_cost", 0)))
        nc_roughing_cost = Decimal(str(summary.get("nc_roughing_cost", 0)))
        nc_milling_cost = Decimal(str(summary.get("nc_milling_cost", 0)))
        drilling_cost = Decimal(str(summary.get("drilling_cost", 0)))
    except (ValueError, TypeError, InvalidOperation) as e:
        logger.error(f"Failed to convert cost values to Decimal for {subgraph_id}: {e}")
        # 返回 0 并记录错误
        calculation_steps = [{
            "step": "数据转换",
            "status": "failed",
            "reason": f"成本数据转换失败: {str(e)}",
            "total_cost": 0.0,
            "processing_cost_total": 0.0
        }]
        
        return {
            "subgraph_id": subgraph_id,
            "total_cost": 0.0,
            "processing_cost_total": 0.0,
            "note": f"成本数据转换失败: {str(e)}"
        }, {
            "subgraph_id": subgraph_id,
            "total_cost": 0.0,
            "processing_cost_total": 0.0,
            "calculation_steps": calculation_steps
        }
    
    # 计算加工成本总计（不包含材料成本和热处理成本）
    processing_cost_total = (
        large_grinding_cost + 
        small_grinding_cost + 
        slow_wire_cost + 
        slow_wire_side_cost + 
        mid_wire_cost + 
        fast_wire_cost + 
        edm_cost +
        nc_roughing_cost +
        nc_milling_cost +
        drilling_cost
    )
    
    # 计算总价
    total_cost = (
        material_cost + 
        heat_treatment_cost + 
        processing_cost_total
    )
    
    total_cost_float = float(total_cost)
    processing_cost_total_float = float(processing_cost_total)
    
    logger.info(
        f"[{subgraph_id}] total_cost={total_cost_float:.2f}, processing_cost_total={processing_cost_total_float:.2f} "
        f"(material={float(material_cost):.2f} + heat={float(heat_treatment_cost):.2f} + "
        f"large_grinding={float(large_grinding_cost):.2f} + small_grinding={float(small_grinding_cost):.2f} + "
        f"slow_wire={float(slow_wire_cost):.2f} + slow_wire_side={float(slow_wire_side_cost):.2f} + "
        f"mid_wire={float(mid_wire_cost):.2f} + fast_wire={float(fast_wire_cost):.2f} + "
        f"edm={float(edm_cost):.2f} + nc_roughing={float(nc_roughing_cost):.2f} + "
        f"nc_milling={float(nc_milling_cost):.2f} + drilling={float(drilling_cost):.2f})"
    )
    
    # 构建计算步骤
    calculation_steps = []
    
    # 步骤1: 获取各项成本
    cost_items = {
        "material_cost": float(material_cost),
        "heat_treatment_cost": float(heat_treatment_cost),
        "large_grinding_cost": float(large_grinding_cost),
        "small_grinding_cost": float(small_grinding_cost),
        "slow_wire_cost": float(slow_wire_cost),
        "slow_wire_side_cost": float(slow_wire_side_cost),
        "mid_wire_cost": float(mid_wire_cost),
        "fast_wire_cost": float(fast_wire_cost),
        "edm_cost": float(edm_cost),
        "nc_roughing_cost": float(nc_roughing_cost),
        "nc_milling_cost": float(nc_milling_cost),
        "drilling_cost": float(drilling_cost)
    }
    
    calculation_steps.append({
        "step": "获取各项成本",
        **cost_items
    })
    
    # 步骤2: 计算加工成本总计
    processing_items = []
    processing_values = []
    
    if float(large_grinding_cost) > 0:
        processing_items.append("大水磨")
        processing_values.append(f"{float(large_grinding_cost):.2f}")
    if float(small_grinding_cost) > 0:
        processing_items.append("小水磨")
        processing_values.append(f"{float(small_grinding_cost):.2f}")
    if float(slow_wire_cost) > 0:
        processing_items.append("慢丝")
        processing_values.append(f"{float(slow_wire_cost):.2f}")
    if float(slow_wire_side_cost) > 0:
        processing_items.append("慢丝侧割")
        processing_values.append(f"{float(slow_wire_side_cost):.2f}")
    if float(mid_wire_cost) > 0:
        processing_items.append("中丝")
        processing_values.append(f"{float(mid_wire_cost):.2f}")
    if float(fast_wire_cost) > 0:
        processing_items.append("快丝")
        processing_values.append(f"{float(fast_wire_cost):.2f}")
    if float(edm_cost) > 0:
        processing_items.append("EDM")
        processing_values.append(f"{float(edm_cost):.2f}")
    if float(nc_roughing_cost) > 0:
        processing_items.append("NC开粗")
        processing_values.append(f"{float(nc_roughing_cost):.2f}")
    if float(nc_milling_cost) > 0:
        processing_items.append("NC精铣")
        processing_values.append(f"{float(nc_milling_cost):.2f}")
    if float(drilling_cost) > 0:
        processing_items.append("钻床")
        processing_values.append(f"{float(drilling_cost):.2f}")
    
    if processing_values:
        formula = " + ".join(processing_values) + f" = {processing_cost_total_float:.2f}"
    else:
        formula = "0（无加工费用）"
    
    calculation_steps.append({
        "step": "计算加工成本总计",
        "note": "不包含材料成本和热处理成本",
        "items": processing_items if processing_items else ["无"],
        "formula": formula,
        "processing_cost_total": processing_cost_total_float
    })
    
    # 步骤3: 计算总价
    total_items = []
    total_values = []
    
    if float(material_cost) > 0:
        total_items.append("材料费")
        total_values.append(f"{float(material_cost):.2f}")
    if float(heat_treatment_cost) > 0:
        total_items.append("热处理费")
        total_values.append(f"{float(heat_treatment_cost):.2f}")
    if processing_cost_total_float > 0:
        total_items.append("加工费")
        total_values.append(f"{processing_cost_total_float:.2f}")
    
    if total_values:
        total_formula = " + ".join(total_values) + f" = {total_cost_float:.2f}"
    else:
        total_formula = "0（无费用）"
    
    calculation_steps.append({
        "step": "计算总价",
        "items": total_items if total_items else ["无"],
        "formula": total_formula,
        "total_cost": total_cost_float
    })
    
    # 返回结果
    result = {
        "subgraph_id": subgraph_id,
        "total_cost": total_cost_float,
        "processing_cost_total": processing_cost_total_float,
        "breakdown": cost_items
    }
    
    db_data = {
        "subgraph_id": subgraph_id,
        "total_cost": total_cost_float,
        "processing_cost_total": processing_cost_total_float,
        "calculation_steps": calculation_steps
    }
    
    return result, db_data


async def _batch_update_subgraphs(job_id: str, updates: List[Dict]):
    """
    批量更新 subgraphs 表的 total_cost 和 processing_cost_total 字段
    同时更新 processing_cost_calculation_details 表的计算步骤
    
    Args:
        job_id: 任务ID
        updates: 更新数据列表（包含 calculation_steps）
    """
    logger.info(f"Batch updating {len(updates)} records to subgraphs table")
    
    # 1. 更新 subgraphs 表
    sql = """
        UPDATE subgraphs
        SET 
            total_cost = $3,
            processing_cost_total = $4,
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
                data["total_cost"],
                data["processing_cost_total"]
            ))
        
        await asyncio.gather(*tasks)
        logger.info(f"Successfully updated {len(updates)} records in subgraphs table")
    
    except Exception as e:
        logger.error(f"Failed to batch update subgraphs: {e}")
        raise
    
    # 2. 更新 processing_cost_calculation_details 表的计算步骤
    try:
        from ._batch_update_helper import batch_upsert_with_steps
        
        updates_for_batch = [
            {
                "job_id": job_id,
                "subgraph_id": d["subgraph_id"],
                "value": d["total_cost"],
                "steps": d["calculation_steps"]
            }
            for d in updates
        ]
        
        await batch_upsert_with_steps(updates_for_batch, "total", "total_cost")
        logger.info(f"Successfully updated calculation steps for {len(updates)} records")
    
    except Exception as e:
        logger.error(f"Failed to update calculation steps: {e}")
        # 不抛出异常，因为主要数据已经更新成功
        logger.warning("Calculation steps update failed, but main data is updated")


async def _update_job_total_cost(job_id: str, total_cost: float):
    """
    更新 jobs 表的 total_cost 字段
    
    Args:
        job_id: 任务ID
        total_cost: 累加后的总成本
    """
    logger.info(f"Updating jobs table for job_id: {job_id}, total_cost: {total_cost:.2f}")
    
    sql = """
        UPDATE jobs
        SET 
            total_cost = $2,
            updated_at = NOW()
        WHERE job_id = $1::uuid
    """
    
    try:
        await db.execute(sql, job_id, total_cost)
        logger.info(f"Successfully updated jobs table, job_id: {job_id}, total_cost: {total_cost:.2f}")
    
    except Exception as e:
        logger.error(f"Failed to update jobs table: {e}")
        raise


async def _update_process_descriptions(job_id: str, subgraph_ids: List[str]):
    """
    生成并更新工艺描述（process_description）
    
    工艺字段映射：
    - nc_roughing_time -> S
    - nc_milling_time -> SS
    - drilling_time -> Z
    - milling_machine_time -> X
    - large_grinding_time -> M
    - small_grinding_time -> YM
    - slow_wire_length -> WE
    - mid_wire_length -> WZ
    - fast_wire_length -> WC
    - edm_time -> EDM
    - engraving_cost -> DK
    
    最后固定添加 QC
    
    Args:
        job_id: 任务ID
        subgraph_ids: 子图ID列表
    """
    logger.info(f"Generating process descriptions for {len(subgraph_ids)} parts")
    
    # 工艺字段映射（按顺序）
    process_fields = [
        ("nc_roughing_time", "S"),
        ("nc_milling_time", "SS"),
        ("drilling_time", "Z"),
        ("milling_machine_time", "X"),
        ("large_grinding_time", "M"),
        ("small_grinding_time", "YM"),
        ("slow_wire_length", "WE"),
        ("mid_wire_length", "WZ"),
        ("fast_wire_length", "WC"),
        ("edm_time", "EDM"),
        ("engraving_cost", "DK")
    ]
    
    # 构建查询字段列表
    field_names = [field[0] for field in process_fields]
    field_list = ", ".join(field_names)
    
    # 查询所有零件的工艺字段值
    query_sql = f"""
        SELECT subgraph_id, {field_list}
        FROM subgraphs
        WHERE job_id = $1::uuid AND subgraph_id = ANY($2::text[])
    """
    
    try:
        rows = await db.fetch_all(query_sql, job_id, subgraph_ids)
        
        # 为每个零件生成工艺描述
        update_tasks = []
        for row in rows:
            subgraph_id = row["subgraph_id"]
            
            # 收集有值的工艺
            processes = []
            for field_name, abbr in process_fields:
                value = row.get(field_name)
                # 判断字段是否有值（不为 None 且不为 0）
                if value is not None and value != 0:
                    processes.append(abbr)
            
            # 添加固定的 QC
            processes.append("QC")
            
            # 生成工艺描述
            process_description = "-".join(processes)
            
            logger.info(f"[{subgraph_id}] process_description: {process_description}")
            
            # 准备更新任务
            update_tasks.append(_update_single_process_description(job_id, subgraph_id, process_description))
        
        # 并发执行所有更新
        if update_tasks:
            await asyncio.gather(*update_tasks)
            logger.info(f"Successfully updated process descriptions for {len(update_tasks)} parts")
    
    except Exception as e:
        logger.error(f"Failed to update process descriptions: {e}")
        raise


async def _update_single_process_description(job_id: str, subgraph_id: str, process_description: str):
    """
    更新单个零件的工艺描述
    
    Args:
        job_id: 任务ID
        subgraph_id: 子图ID
        process_description: 工艺描述
    """
    sql = """
        UPDATE subgraphs
        SET 
            process_description = $3,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """
    
    await db.execute(sql, job_id, subgraph_id, process_description)


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
    
    logging.basicConfig(level=logging.INFO)
    
    print("price_total.py - 最终总价计算脚本（阶段 7）")
    print("需要配合 search.py (subgraphs_cost_search) 使用")
    print("\n使用方式：")
    print("1. 先执行阶段 1-6 的所有脚本")
    print("2. 执行 search.py 获取成本汇总")
    print("3. 最后调用本脚本计算最终总价并更新 subgraphs 表和 jobs 表")
