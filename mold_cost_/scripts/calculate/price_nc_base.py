"""
NC基本费用计算脚本
负责人：李志鹏

计算流程：
1. 调用 base_itemcode_search 获取零件基础信息（length_mm, width_mm, thickness_mm, nc_time_cost, quantity）
2. 调用 nc_search 获取NC基本费用配置（nc_base: 模板1小时/零件0.5小时）和工时单价（work_hour: 60/80/100元/小时）
3. 调用 wire_base_search 获取模板零件判断标准（template_component: 默认400mm）
4. 检查 nc_time_cost 是否为空，为空则跳过计算返回0
5. 检查 nc_details 中是否有实际的加工数据（非0值），全为0则跳过计算
6. 根据尺寸判断是模板还是零件：
   - 任意尺寸 > 400mm：模板（nc_base = 1小时）
   - 所有尺寸 <= 400mm：零件（nc_base = 0.5小时）
7. 根据尺寸判断使用哪个工时单价：
   - 最长边 < 1500 且 最短边 < 800：60元/小时
   - 最长边 [1500~2000) 或 最短边 [800~1200)：80元/小时
   - 最长边 >= 2000 或 最短边 >= 1200：100元/小时
8. 根据 nc_details 分类判断哪些工序有数据：
   - "精铣"、"半精"、"全精" -> 计算 nc_base_milling_cost
   - "开粗" -> 计算 nc_base_roughing_cost
   - 其他所有code -> 计算 nc_base_drilling_cost
9. 计算公式：nc_base_xxx_cost = nc_base时间 × 工时单价 × 数量（仅对有数据的工序计算）
10. 更新 processing_cost_calculation_details 表的 nc_base_roughing_cost、nc_base_milling_cost、nc_base_drilling_cost 字段和步骤字段
"""
from shared.unified_logging import get_logger
from typing import List, Dict, Any, Tuple
import logging
import asyncio

from refactor_bootstrap import ensure_src_path

# 中文注释：脚本直接依赖 infrastructure，避免再穿过 api_gateway 兼容层。
ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db
from ._batch_update_helper import batch_upsert_with_steps

logger = get_logger(__name__)

# MCP 工具元数据
MCP_TOOL_META = {
    "name": "calculate_nc_base_cost",
    "description": "计算NC基本费用：根据零件尺寸判断是模板还是零件，然后计算基本费用",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "检索数据，包含 base_itemcode、nc 和 wire_base"
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
    "needs": ["base_itemcode", "nc", "wire_base"]
}


async def calculate(
    search_data: Dict[str, Any],
    job_id: str = None,
    subgraph_ids: List[str] = None
) -> Dict[str, Any]:
    """
    计算NC基本费用
    
    Args:
        search_data: 检索数据，包含 base_itemcode、nc 和 wire_base
        job_id: 任务ID（可选，用于日志和数据库更新）
        subgraph_ids: 子图ID列表（可选，用于过滤）
        
    Returns:
        Dict: 计算结果
    """
    # 获取检索数据
    base_data = search_data["base_itemcode"]
    nc_data = search_data["nc"]
    wire_base_data = search_data["wire_base"]
    
    # 提取 job_id（如果未传入）
    if not job_id:
        job_id = base_data.get("job_id")
    
    logger.info(f"Calculating NC base cost for job_id: {job_id}, parts count: {len(base_data.get('parts', []))}")
    
    # Step 1: 构建NC基本费用配置
    nc_base_config = _build_nc_base_config(nc_data.get("nc_prices", []))
    
    if not nc_base_config:
        logger.warning("No nc_base configuration found in nc_data")
        return {
            "job_id": job_id,
            "results": [],
            "message": "未找到NC基本费用配置"
        }
    
    # Step 2: 获取模板零件判断标准
    template_threshold = _get_template_threshold(wire_base_data.get("rule_prices", []))
    
    logger.info(f"Template threshold: {template_threshold} mm")
    
    # Step 3: 计算每个零件的NC基本费用
    results = []
    db_updates = []
    
    for part in base_data["parts"]:
        result, db_data = await _calculate_part_nc_base_cost(
            job_id, part, nc_base_config, template_threshold
        )
        results.append(result)
        if db_data:
            db_updates.append(db_data)
    
    # Step 4: 批量写入数据库（分别更新三个字段）
    if db_updates:
        # 更新 nc_base_roughing_cost（开粗基本费用）
        roughing_updates = [
            {
                "job_id": d["job_id"],
                "subgraph_id": d["subgraph_id"],
                "value": d["nc_base_roughing_cost"],
                "steps": d["calculation_steps"]
            }
            for d in db_updates
        ]
        await batch_upsert_with_steps(roughing_updates, "nc_base_roughing", "nc_base_roughing_cost")
        
        # 更新 nc_base_milling_cost（精铣基本费用）
        milling_updates = [
            {
                "job_id": d["job_id"],
                "subgraph_id": d["subgraph_id"],
                "value": d["nc_base_milling_cost"],
                "steps": d["calculation_steps"]
            }
            for d in db_updates
        ]
        await batch_upsert_with_steps(milling_updates, "nc_base_milling", "nc_base_milling_cost")
        
        # 更新 nc_base_drilling_cost（钻床基本费用）
        drilling_updates = [
            {
                "job_id": d["job_id"],
                "subgraph_id": d["subgraph_id"],
                "value": d["nc_base_drilling_cost"],
                "steps": d["calculation_steps"]
            }
            for d in db_updates
        ]
        await batch_upsert_with_steps(drilling_updates, "nc_base_drilling", "nc_base_drilling_cost")
    
    logger.info(f"Completed NC base cost calculation for {len(results)} parts")
    
    return {
        "job_id": job_id,
        "results": results
    }


def _build_nc_base_config(nc_prices: List[Dict]) -> Dict[str, Any]:
    """
    构建NC基本费用配置
    
    Returns:
        {
            "nc_base_hours": {
                "template": 1.0,    # 模板的nc_base时间
                "component": 0.5    # 零件的nc_base时间
            },
            "work_hour_prices": [
                {"price": 60, "unit": "元/小时"},
                {"price": 80, "unit": "元/小时"},
                {"price": 100, "unit": "元/小时"}
            ]
        }
    """
    nc_base_hours = {}
    work_hour_prices = []
    
    for item in nc_prices:
        sub_category = item.get("sub_category")
        
        if sub_category == "nc_base":
            # nc_base 的 price 就是时间（小时）
            hours = float(item.get("price", 0))
            if hours == 1.0:
                nc_base_hours["template"] = hours
            elif hours == 0.5:
                nc_base_hours["component"] = hours
        
        elif sub_category == "work_hour":
            work_hour_prices.append({
                "price": float(item["price"]),
                "unit": item.get("unit", "元/小时")
            })
    
    # 按价格排序（从低到高）
    work_hour_prices.sort(key=lambda x: x["price"])
    
    logger.info(f"NC base hours: {nc_base_hours}")
    logger.info(f"Work hour prices: {[p['price'] for p in work_hour_prices]}")
    
    return {
        "nc_base_hours": nc_base_hours,
        "work_hour_prices": work_hour_prices
    }


def _get_template_threshold(rule_prices: List[Dict]) -> float:
    """
    获取模板零件判断标准（template_component）
    
    Returns:
        float: 阈值（mm），默认400
    """
    for item in rule_prices:
        if item.get("sub_category") == "template_component":
            return float(item.get("price", 400))
    
    return 400.0  # 默认值


def _determine_part_type(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    template_threshold: float
) -> Tuple[str, str]:
    """
    根据尺寸判断是模板还是零件
    
    规则：如果长宽厚任意一边大于阈值（默认400mm），则为模板
    
    Returns:
        (part_type, description)
        part_type: "template" 或 "component"
    """
    max_dimension = max(length_mm, width_mm, thickness_mm)
    
    if max_dimension > template_threshold:
        return "template", f"最大尺寸{max_dimension}mm > {template_threshold}mm，判定为模板"
    else:
        return "component", f"最大尺寸{max_dimension}mm <= {template_threshold}mm，判定为零件"


def _determine_work_hour_price(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    work_hour_prices: List[Dict]
) -> Tuple[float, str]:
    """
    根据尺寸判断使用哪个工时单价
    
    规则：
    - 尺寸排序后得到最长边和最短边
    - 如果最长边 < 1500 且 最短边 < 800，使用 60元/小时
    - 如果长边 [1500~2000) 或 短边 [800~1200)，使用 80元/小时
    - 如果长边 >= 2000 或 短边 >= 1200，使用 100元/小时
    - 注意：只要满足下一级一个条件就要用下一级的数据
    
    Returns:
        (price, description)
    """
    # 排序尺寸
    dimensions = sorted([length_mm, width_mm, thickness_mm], reverse=True)
    longest = dimensions[0]
    shortest = dimensions[2]
    
    logger.info(f"Dimensions sorted: longest={longest}, shortest={shortest}")
    
    # 默认使用最低价格
    if len(work_hour_prices) < 3:
        logger.warning(f"Expected 3 work_hour prices, got {len(work_hour_prices)}")
        price = work_hour_prices[0]["price"] if work_hour_prices else 60
        return price, f"默认使用{price}元/小时（价格数据不足）"
    
    # 判断使用哪个价格
    # 最高级：长边 >= 2000 或 短边 >= 1200
    if longest >= 2000 or shortest >= 1200:
        price = work_hour_prices[2]["price"]  # 100元/小时
        reason = f"最长边{longest}mm"
        if longest >= 2000:
            reason += f">=2000"
        if shortest >= 1200:
            if longest >= 2000:
                reason += f"，且最短边{shortest}mm>=1200"
            else:
                reason += f"最短边{shortest}mm>=1200"
        return price, f"{reason}，使用{price}元/小时"
    
    # 中级：长边 [1500~2000) 或 短边 [800~1200)
    if (1500 <= longest < 2000) or (800 <= shortest < 1200):
        price = work_hour_prices[1]["price"]  # 80元/小时
        reason = ""
        if 1500 <= longest < 2000:
            reason = f"最长边{longest}mm在[1500~2000)区间"
        if 800 <= shortest < 1200:
            if reason:
                reason += f"，且最短边{shortest}mm在[800~1200)区间"
            else:
                reason = f"最短边{shortest}mm在[800~1200)区间"
        return price, f"{reason}，使用{price}元/小时"
    
    # 最低级：长边 < 1500 且 短边 < 800
    price = work_hour_prices[0]["price"]  # 60元/小时
    return price, f"最长边{longest}mm<1500且最短边{shortest}mm<800，使用{price}元/小时"


async def _calculate_part_nc_base_cost(
    job_id: str,
    part: Dict,
    nc_base_config: Dict,
    template_threshold: float
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    计算单个零件的NC基本费用
    
    Returns:
        tuple: (result_dict, db_update_dict)
    """
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    length_mm = part["length_mm"]
    width_mm = part["width_mm"]
    thickness_mm = part["thickness_mm"]
    quantity = part.get("quantity", 1)  # 获取数量，默认为1
    nc_time_cost_data = part.get("nc_time_cost")
    
    logger.info(f"Calculating NC base cost for part: {part_name} ({subgraph_id})")
    
    # 检查 nc_time_cost 数据
    if not nc_time_cost_data:
        logger.info(f"No nc_time_cost data for {part_name}, skipping NC base cost calculation")
        return {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "nc_base_roughing_cost": 0,
            "nc_base_milling_cost": 0,
            "nc_base_drilling_cost": 0,
            "note": "nc_time_cost数据为空，跳过计算"
        }, {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "nc_base_roughing_cost": 0,
            "nc_base_milling_cost": 0,
            "nc_base_drilling_cost": 0,
            "calculation_steps": [{
                "step": "检查nc_time_cost",
                "note": "nc_time_cost数据为空，跳过NC基本费用计算"
            }]
        }
    
    # 如果 nc_time_cost_data 是字符串，解析为 JSON
    if isinstance(nc_time_cost_data, str):
        try:
            import json
            nc_time_cost_data = json.loads(nc_time_cost_data)
            logger.info(f"Parsed nc_time_cost from JSON string for {part_name}")
        except Exception as e:
            logger.error(f"Failed to parse nc_time_cost JSON for {part_name}: {e}")
            return {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "nc_base_roughing_cost": 0,
                "nc_base_milling_cost": 0,
                "nc_base_drilling_cost": 0,
                "note": f"nc_time_cost JSON解析失败: {e}"
            }, {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_base_roughing_cost": 0,
                "nc_base_milling_cost": 0,
                "nc_base_drilling_cost": 0,
                "calculation_steps": [{
                    "step": "解析nc_time_cost",
                    "note": f"JSON解析失败: {e}，跳过NC基本费用计算"
                }]
            }
    
    # 检查 nc_details 是否有实际的加工数据（非0值）
    nc_details = nc_time_cost_data.get("nc_details", [])
    if not nc_details:
        logger.info(f"No nc_details in nc_time_cost for {part_name}, skipping NC base cost calculation")
        return {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "nc_base_roughing_cost": 0,
            "nc_base_milling_cost": 0,
            "nc_base_drilling_cost": 0,
            "note": "nc_details为空，跳过计算"
        }, {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "nc_base_roughing_cost": 0,
            "nc_base_milling_cost": 0,
            "nc_base_drilling_cost": 0,
            "calculation_steps": [{
                "step": "检查nc_details",
                "note": "nc_details为空，跳过NC基本费用计算"
            }]
        }
    
    # 分类检查哪些工序有数据（非0值）
    has_roughing = False  # 开粗
    has_milling = False   # 精铣
    has_drilling = False  # 钻床
    
    for detail in nc_details:
        code = detail.get("code", "")
        try:
            value = float(detail.get("value", 0))
            if value > 0:
                if code == "开粗":
                    has_roughing = True
                elif code in ["精铣", "半精", "全精"]:
                    has_milling = True
                else:
                    # 其他所有code都归为钻床
                    has_drilling = True
        except (ValueError, TypeError):
            continue
    
    # 如果所有工序都没有数据，跳过计算
    if not (has_roughing or has_milling or has_drilling):
        logger.info(f"All nc_details values are 0 for {part_name}, skipping NC base cost calculation")
        return {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "nc_base_roughing_cost": 0,
            "nc_base_milling_cost": 0,
            "nc_base_drilling_cost": 0,
            "note": "所有nc_details的value都为0，跳过计算"
        }, {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "nc_base_roughing_cost": 0,
            "nc_base_milling_cost": 0,
            "nc_base_drilling_cost": 0,
            "calculation_steps": [{
                "step": "检查nc_details数据",
                "note": "所有nc_details的value都为0，跳过NC基本费用计算"
            }]
        }
    
    calculation_steps = []
    
    # 添加工序数据检查步骤
    calculation_steps.append({
        "step": "检查各工序数据",
        "has_roughing": has_roughing,
        "has_milling": has_milling,
        "has_drilling": has_drilling,
        "note": "根据nc_details判断哪些工序有实际加工数据"
    })
    
    # Step 1: 判断是模板还是零件
    part_type, part_type_desc = _determine_part_type(
        length_mm, width_mm, thickness_mm, template_threshold
    )
    
    calculation_steps.append({
        "step": "判断零件类型",
        "dimensions": {
            "length_mm": length_mm,
            "width_mm": width_mm,
            "thickness_mm": thickness_mm
        },
        "template_threshold": template_threshold,
        "part_type": part_type,
        "description": part_type_desc
    })
    
    # Step 2: 获取对应的nc_base时间
    nc_base_hours = nc_base_config["nc_base_hours"].get(part_type)
    
    if nc_base_hours is None:
        logger.warning(f"No nc_base hours found for part_type: {part_type}")
        return {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "nc_base_cost": 0,
            "note": f"未找到{part_type}的nc_base时间配置"
        }, {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "nc_base_cost": 0,
            "calculation_steps": calculation_steps + [{
                "step": "错误",
                "note": f"未找到{part_type}的nc_base时间配置"
            }]
        }
    
    calculation_steps.append({
        "step": "获取nc_base时间",
        "part_type": part_type,
        "nc_base_hours": nc_base_hours
    })
    
    # Step 3: 判断工时单价
    unit_price, price_reason = _determine_work_hour_price(
        length_mm, width_mm, thickness_mm, nc_base_config["work_hour_prices"]
    )
    
    calculation_steps.append({
        "step": "判断工时单价",
        "unit_price": unit_price,
        "reason": price_reason
    })
    
    # Step 4: 分别计算各工序的基本费用
    # 单件费用 = nc_base时间 × 工时单价
    cost_single = nc_base_hours * unit_price
    
    # 根据工序数据情况，分别计算各项基本费用
    nc_base_roughing_cost = cost_single * quantity if has_roughing else 0
    nc_base_milling_cost = cost_single * quantity if has_milling else 0
    nc_base_drilling_cost = cost_single * quantity if has_drilling else 0
    
    calculation_steps.append({
        "step": "计算NC基本费用",
        "nc_base_hours": nc_base_hours,
        "unit_price": unit_price,
        "quantity": quantity,
        "formula_single": f"{nc_base_hours} * {unit_price} = {round(cost_single, 4)}",
        "cost_single": round(cost_single, 4),
        "roughing": {
            "has_data": has_roughing,
            "cost": round(nc_base_roughing_cost, 4) if has_roughing else 0,
            "formula": f"{round(cost_single, 4)} * {quantity} = {round(nc_base_roughing_cost, 4)}" if has_roughing else "无开粗数据，费用为0"
        },
        "milling": {
            "has_data": has_milling,
            "cost": round(nc_base_milling_cost, 4) if has_milling else 0,
            "formula": f"{round(cost_single, 4)} * {quantity} = {round(nc_base_milling_cost, 4)}" if has_milling else "无精铣数据，费用为0"
        },
        "drilling": {
            "has_data": has_drilling,
            "cost": round(nc_base_drilling_cost, 4) if has_drilling else 0,
            "formula": f"{round(cost_single, 4)} * {quantity} = {round(nc_base_drilling_cost, 4)}" if has_drilling else "无钻床数据，费用为0"
        }
    })
    
    # 返回结果和数据库更新数据
    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "part_type": part_type,
        "quantity": quantity,
        "nc_base_roughing_cost": round(nc_base_roughing_cost, 4),
        "nc_base_milling_cost": round(nc_base_milling_cost, 4),
        "nc_base_drilling_cost": round(nc_base_drilling_cost, 4)
    }
    
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "nc_base_roughing_cost": nc_base_roughing_cost,
        "nc_base_milling_cost": nc_base_milling_cost,
        "nc_base_drilling_cost": nc_base_drilling_cost,
        "calculation_steps": calculation_steps
    }
    
    return result, db_data


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
        print("Usage: python price_nc_base.py <job_id> <subgraph_id1> [subgraph_id2 ...]")
        sys.exit(1)
    
    job_id = sys.argv[1]
    subgraph_ids = sys.argv[2:]
    
    # 这里需要先调用检索脚本获取数据
    print("请通过 MCP 服务或 API 调用此计算脚本")
    print(f"job_id: {job_id}")
    print(f"subgraph_ids: {subgraph_ids}")
