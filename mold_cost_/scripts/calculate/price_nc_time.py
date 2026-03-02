"""
NC时间费用计算脚本
负责人：李志鹏

计算流程：
1. 调用 base_itemcode_search 获取零件基础信息（length_mm, width_mm, thickness_mm, nc_time_cost, quantity）
2. 调用 nc_search 获取NC工时价格信息（work_hour: 60/80/100元/小时）
3. 检查 nc_time_cost 是否为空，为空则跳过计算返回0
4. 根据尺寸判断使用哪个工时单价：
   - 最长边 < 1500 且 最短边 < 800：60元/小时
   - 最长边 [1500~2000) 或 最短边 [800~1200)：80元/小时
   - 最长边 >= 2000 或 最短边 >= 1200：100元/小时
5. 解析 nc_time_cost.nc_details，将时间从分钟转换为小时
6. 分类统计：
   - "精铣"、"半精"、"全精" -> nc_milling_cost（精铣费用）
   - "开粗" -> nc_roughing_cost（开粗费用）
   - 其他所有code -> nc_drilling_cost（钻床费用），包括：M、ZXZ、M1、M-1、ABC等
7. 计算费用：时间（小时）× 工时单价 × 数量
8. 更新 processing_cost_calculation_details 表的 nc_roughing_cost、nc_milling_cost、nc_drilling_cost 字段和步骤字段
"""
from shared.unified_logging import get_logger
from typing import List, Dict, Any, Tuple
import logging
import asyncio

from api_gateway.database import db
from ._batch_update_helper import batch_upsert_with_steps

logger = get_logger(__name__)

# MCP 工具元数据
MCP_TOOL_META = {
    "name": "calculate_nc_time_cost",
    "description": "计算NC时间费用：根据零件尺寸和nc_time_cost数据计算精铣、开粗、钻床费用",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "检索数据，包含 base_itemcode 和 nc"
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
    "needs": ["base_itemcode", "nc"]
}


async def calculate(
    search_data: Dict[str, Any],
    job_id: str = None,
    subgraph_ids: List[str] = None
) -> Dict[str, Any]:
    """
    计算NC时间费用
    
    Args:
        search_data: 检索数据，包含 base_itemcode 和 nc
        job_id: 任务ID（可选，用于日志和数据库更新）
        subgraph_ids: 子图ID列表（可选，用于过滤）
        
    Returns:
        Dict: 计算结果
    """
    # 获取检索数据
    base_data = search_data["base_itemcode"]
    nc_data = search_data["nc"]
    
    # 提取 job_id（如果未传入）
    if not job_id:
        job_id = base_data.get("job_id")
    
    logger.info(f"Calculating NC time cost for job_id: {job_id}, parts count: {len(base_data.get('parts', []))}")
    
    # Step 1: 构建工时价格映射
    work_hour_prices = _build_work_hour_price_map(nc_data.get("nc_prices", []))
    
    if not work_hour_prices:
        logger.warning("No work_hour prices found in nc_data")
        return {
            "job_id": job_id,
            "results": [],
            "message": "未找到NC工时价格数据"
        }
    
    # Step 2: 计算每个零件的NC时间费用
    results = []
    db_updates = []
    
    for part in base_data["parts"]:
        result, db_data = await _calculate_part_nc_time_cost(
            job_id, part, work_hour_prices
        )
        results.append(result)
        if db_data:
            db_updates.append(db_data)
    
    # Step 3: 批量写入数据库（分别更新三个字段）
    if db_updates:
        # 更新 nc_roughing_cost（开粗费用）
        roughing_updates = [
            {
                "job_id": d["job_id"],
                "subgraph_id": d["subgraph_id"],
                "value": d["nc_roughing_cost"],
                "steps": d["calculation_steps"]
            }
            for d in db_updates
        ]
        await batch_upsert_with_steps(roughing_updates, "nc_roughing", "nc_roughing_cost")
        
        # 更新 nc_milling_cost（精铣费用）
        milling_updates = [
            {
                "job_id": d["job_id"],
                "subgraph_id": d["subgraph_id"],
                "value": d["nc_milling_cost"],
                "steps": d["calculation_steps"]
            }
            for d in db_updates
        ]
        await batch_upsert_with_steps(milling_updates, "nc_milling", "nc_milling_cost")
        
        # 更新 nc_drilling_cost（钻床费用）
        drilling_updates = [
            {
                "job_id": d["job_id"],
                "subgraph_id": d["subgraph_id"],
                "value": d["nc_drilling_cost"],
                "steps": d["calculation_steps"]
            }
            for d in db_updates
        ]
        await batch_upsert_with_steps(drilling_updates, "nc_drilling", "nc_drilling_cost")
    
    logger.info(f"Completed NC time cost calculation for {len(results)} parts")
    
    return {
        "job_id": job_id,
        "results": results
    }


def _build_work_hour_price_map(nc_prices: List[Dict]) -> List[Dict]:
    """
    构建工时价格列表，包含价格和区间信息
    
    Returns:
        [
            {
                "price": 60, 
                "unit": "元/小时",
                "s_range": {"min": 0, "max": 800, "min_inclusive": False, "max_inclusive": False},
                "l_range": {"min": 0, "max": 1500, "min_inclusive": False, "max_inclusive": False}
            },
            ...
        ]
    """
    import re
    work_hour_prices = []
    
    for item in nc_prices:
        if item.get("sub_category") == "work_hour":
            price_value = float(item["price"])
            unit = item.get("unit", "元/小时")
            min_num = item.get("min_num", "")
            
            # 解析 min_num 字段，格式如: "S:[1200,9999), L:[2000,9999)"
            s_range = None
            l_range = None
            
            if min_num:
                # 提取 S 和 L 的区间
                s_match = re.search(r'S:\s*([\[\(])(\d+),\s*(\d+|[+∞∞]+)([\]\)])', str(min_num))
                l_match = re.search(r'L:\s*([\[\(])(\d+),\s*(\d+|[+∞∞]+)([\]\)])', str(min_num))
                
                if s_match:
                    s_min_bracket = s_match.group(1)
                    s_min = float(s_match.group(2))
                    s_max_str = s_match.group(3)
                    s_max_bracket = s_match.group(4)
                    
                    s_max = float('inf') if '+' in s_max_str or '∞' in s_max_str else float(s_max_str)
                    s_range = {
                        "min": s_min,
                        "max": s_max,
                        "min_inclusive": s_min_bracket == '[',
                        "max_inclusive": s_max_bracket == ']'
                    }
                
                if l_match:
                    l_min_bracket = l_match.group(1)
                    l_min = float(l_match.group(2))
                    l_max_str = l_match.group(3)
                    l_max_bracket = l_match.group(4)
                    
                    l_max = float('inf') if '+' in l_max_str or '∞' in l_max_str else float(l_max_str)
                    l_range = {
                        "min": l_min,
                        "max": l_max,
                        "min_inclusive": l_min_bracket == '[',
                        "max_inclusive": l_max_bracket == ']'
                    }
            
            work_hour_prices.append({
                "price": price_value,
                "unit": unit,
                "s_range": s_range,
                "l_range": l_range,
                "min_num": min_num
            })
    
    # 按价格排序（从低到高）
    work_hour_prices.sort(key=lambda x: x["price"])
    
    logger.info(f"Found {len(work_hour_prices)} work_hour prices: {[p['price'] for p in work_hour_prices]}")
    
    return work_hour_prices


def _in_range(value: float, range_info: dict) -> bool:
    """
    判断值是否在区间内
    
    Args:
        value: 要判断的值
        range_info: 区间信息 {"min": 0, "max": 800, "min_inclusive": False, "max_inclusive": False}
    
    Returns:
        bool: 是否在区间内
    """
    if not range_info:
        return False
    
    min_val = range_info["min"]
    max_val = range_info["max"]
    min_inclusive = range_info["min_inclusive"]
    max_inclusive = range_info["max_inclusive"]
    
    # 检查最小值
    if min_inclusive:
        if value < min_val:
            return False
    else:
        if value <= min_val:
            return False
    
    # 检查最大值
    if max_val == float('inf'):
        return True
    
    if max_inclusive:
        if value > max_val:
            return False
    else:
        if value >= max_val:
            return False
    
    return True


def _determine_work_hour_price(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    work_hour_prices: List[Dict]
) -> Tuple[float, str]:
    """
    根据尺寸动态判断使用哪个工时单价
    
    规则：
    - 尺寸排序后得到最长边(L)和最短边(S)
    - 遍历价格列表，找到同时满足 S 和 L 区间的价格
    - 如果多个价格都满足，使用价格最高的（优先级最高）
    
    Returns:
        (price, description)
    """
    # 处理空值：将 None 转换为 0
    length_mm = length_mm or 0
    width_mm = width_mm or 0
    thickness_mm = thickness_mm or 0
    
    # 排序尺寸
    dimensions = sorted([length_mm, width_mm, thickness_mm], reverse=True)
    longest = dimensions[0]
    shortest = dimensions[2]
    
    logger.info(f"Dimensions sorted: longest={longest}, shortest={shortest}")
    
    if not work_hour_prices:
        logger.error("No work_hour prices available")
        return 0, "无工时价格数据"
    
    # 从高价到低价遍历（因为已经按价格从低到高排序，所以反向遍历）
    matched_prices = []
    
    for price_info in work_hour_prices:
        s_range = price_info.get("s_range")
        l_range = price_info.get("l_range")
        
        # 检查是否同时满足 S 和 L 的区间条件
        s_match = _in_range(shortest, s_range) if s_range else True
        l_match = _in_range(longest, l_range) if l_range else True
        
        if s_match and l_match:
            matched_prices.append(price_info)
    
    # 如果有匹配的价格，使用价格最高的
    if matched_prices:
        # 按价格从高到低排序，取第一个
        matched_prices.sort(key=lambda x: x["price"], reverse=True)
        selected = matched_prices[0]
        
        price = selected["price"]
        s_range = selected.get("s_range")
        l_range = selected.get("l_range")
        
        # 构建描述
        reason_parts = []
        if s_range:
            s_bracket_left = '[' if s_range["min_inclusive"] else '('
            s_bracket_right = ']' if s_range["max_inclusive"] else ')'
            s_max_str = '+∞' if s_range["max"] == float('inf') else str(s_range["max"])
            reason_parts.append(f"最短边{shortest}mm在{s_bracket_left}{s_range['min']},{s_max_str}{s_bracket_right}")
        
        if l_range:
            l_bracket_left = '[' if l_range["min_inclusive"] else '('
            l_bracket_right = ']' if l_range["max_inclusive"] else ')'
            l_max_str = '+∞' if l_range["max"] == float('inf') else str(l_range["max"])
            reason_parts.append(f"最长边{longest}mm在{l_bracket_left}{l_range['min']},{l_max_str}{l_bracket_right}")
        
        reason = "，".join(reason_parts) if reason_parts else f"匹配到价格{price}"
        
        return price, f"{reason}，使用{price}元/小时"
    
    # 如果没有匹配的，使用最低价格作为默认值
    default_price = work_hour_prices[0]["price"]
    logger.warning(f"No matching price range for longest={longest}, shortest={shortest}, using default {default_price}")
    return default_price, f"未匹配到区间，使用默认{default_price}元/小时"


async def _calculate_part_nc_time_cost(
    job_id: str,
    part: Dict,
    work_hour_prices: List[Dict]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    计算单个零件的NC时间费用
    
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
    
    logger.info(f"Calculating NC time cost for part: {part_name} ({subgraph_id})")
    
    # 检查 nc_time_cost 数据
    if not nc_time_cost_data:
        logger.info(f"No nc_time_cost data for {part_name}, skipping calculation")
        return {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "nc_milling_cost": 0,
            "nc_roughing_cost": 0,
            "nc_drilling_cost": 0,
            "note": "nc_time_cost数据为空，跳过计算"
        }, {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "nc_milling_cost": 0,
            "nc_roughing_cost": 0,
            "nc_drilling_cost": 0,
            "calculation_steps": [{
                "step": "检查nc_time_cost",
                "note": "nc_time_cost数据为空，跳过NC时间费用计算"
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
                "nc_milling_cost": 0,
                "nc_roughing_cost": 0,
                "nc_drilling_cost": 0,
                "note": f"nc_time_cost JSON解析失败: {e}"
            }, {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "nc_milling_cost": 0,
                "nc_roughing_cost": 0,
                "nc_drilling_cost": 0,
                "calculation_steps": [{
                    "step": "解析nc_time_cost",
                    "note": f"JSON解析失败: {e}，跳过NC时间费用计算"
                }]
            }
    
    # 获取 nc_details
    nc_details = nc_time_cost_data.get("nc_details", [])
    if not nc_details:
        logger.info(f"No nc_details in nc_time_cost for {part_name}, skipping calculation")
        return {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "nc_milling_cost": 0,
            "nc_roughing_cost": 0,
            "nc_drilling_cost": 0,
            "note": "nc_details为空，跳过计算"
        }, {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "nc_milling_cost": 0,
            "nc_roughing_cost": 0,
            "nc_drilling_cost": 0,
            "calculation_steps": [{
                "step": "检查nc_details",
                "note": "nc_details为空，跳过NC时间费用计算"
            }]
        }
    
    # 判断使用哪个工时单价
    unit_price, price_reason = _determine_work_hour_price(
        length_mm, width_mm, thickness_mm, work_hour_prices
    )
    
    calculation_steps = []
    
    # 添加尺寸和单价判断步骤
    calculation_steps.append({
        "step": "判断工时单价",
        "dimensions": {
            "length_mm": length_mm,
            "width_mm": width_mm,
            "thickness_mm": thickness_mm
        },
        "unit_price": unit_price,
        "reason": price_reason
    })
    
    # 分类统计：精铣、开粗、钻床
    # 注意：value的单位是分钟，需要转换为小时
    jing_xi_hours = 0  # 精铣（小时）
    kai_cu_hours = 0   # 开粗（小时）
    drill_hours = 0    # 钻床（小时）
    
    for detail in nc_details:
        code = detail.get("code", "")
        value = detail.get("value", "0")
        
        try:
            minutes = float(value)  # value的单位是分钟
            hours = minutes / 60.0  # 转换为小时
        except (ValueError, TypeError):
            logger.warning(f"Invalid value for code {code}: {value}, skipping")
            continue
        
        # 分类逻辑
        if code in ["精铣", "半精", "全精"]:
            # 精铣类：精铣、半精、全精
            jing_xi_hours += hours
        elif code == "开粗":
            # 开粗
            kai_cu_hours += hours
        else:
            # 其他所有code都归为钻床（包括纯字母、字母+数字、字母+特殊字符等）
            # 例如：M、ZXZ、M1、M-1、ABC等
            drill_hours += hours
    
    # 计算各项费用（单件）
    jing_xi_cost_single = jing_xi_hours * unit_price
    kai_cu_cost_single = kai_cu_hours * unit_price
    drill_cost_single = drill_hours * unit_price
    
    # 乘以数量得到总费用
    jing_xi_cost_total = jing_xi_cost_single * quantity
    kai_cu_cost_total = kai_cu_cost_single * quantity
    drill_cost_total = drill_cost_single * quantity
    total_cost = jing_xi_cost_total + kai_cu_cost_total + drill_cost_total
    
    # 添加计算步骤
    calculation_steps.append({
        "step": "统计各类工时（分钟转小时）",
        "details": nc_details,
        "note": "value单位为分钟，已转换为小时（除以60）",
        "classification_rules": {
            "精铣": "code为'精铣'、'半精'、'全精'",
            "开粗": "code为'开粗'",
            "钻床": "其他所有code（如M、ZXZ、M1、M-1等）"
        },
        "summary": {
            "jing_xi_hours": round(jing_xi_hours, 4),
            "kai_cu_hours": round(kai_cu_hours, 4),
            "drill_hours": round(drill_hours, 4)
        }
    })
    
    if jing_xi_hours > 0:
        calculation_steps.append({
            "step": "计算精铣费用",
            "note": "包含code: 精铣、半精、全精",
            "hours": jing_xi_hours,
            "unit_price": unit_price,
            "quantity": quantity,
            "formula_single": f"{jing_xi_hours} * {unit_price} = {round(jing_xi_cost_single, 4)}",
            "cost_single": round(jing_xi_cost_single, 4),
            "formula_total": f"{round(jing_xi_cost_single, 4)} * {quantity} = {round(jing_xi_cost_total, 4)}",
            "cost_total": round(jing_xi_cost_total, 4)
        })
    
    if kai_cu_hours > 0:
        calculation_steps.append({
            "step": "计算开粗费用",
            "note": "包含code: 开粗",
            "hours": kai_cu_hours,
            "unit_price": unit_price,
            "quantity": quantity,
            "formula_single": f"{kai_cu_hours} * {unit_price} = {round(kai_cu_cost_single, 4)}",
            "cost_single": round(kai_cu_cost_single, 4),
            "formula_total": f"{round(kai_cu_cost_single, 4)} * {quantity} = {round(kai_cu_cost_total, 4)}",
            "cost_total": round(kai_cu_cost_total, 4)
        })
    
    if drill_hours > 0:
        calculation_steps.append({
            "step": "计算钻床费用",
            "note": "包含其他所有code（如M、ZXZ、M1、M-1等）",
            "hours": drill_hours,
            "unit_price": unit_price,
            "quantity": quantity,
            "formula_single": f"{drill_hours} * {unit_price} = {round(drill_cost_single, 4)}",
            "cost_single": round(drill_cost_single, 4),
            "formula_total": f"{round(drill_cost_single, 4)} * {quantity} = {round(drill_cost_total, 4)}",
            "cost_total": round(drill_cost_total, 4)
        })
    
    calculation_steps.append({
        "step": "汇总NC时间费用",
        "nc_milling_cost": round(jing_xi_cost_total, 4),
        "nc_roughing_cost": round(kai_cu_cost_total, 4),
        "nc_drilling_cost": round(drill_cost_total, 4),
        "formula": f"{round(jing_xi_cost_total, 4)} + {round(kai_cu_cost_total, 4)} + {round(drill_cost_total, 4)} = {round(total_cost, 4)}",
        "total_cost": round(total_cost, 4)
    })
    
    # 返回结果和数据库更新数据
    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "quantity": quantity,
        "nc_milling_cost": round(jing_xi_cost_total, 4),
        "nc_roughing_cost": round(kai_cu_cost_total, 4),
        "nc_drilling_cost": round(drill_cost_total, 4),
        "total_cost": round(total_cost, 4)
    }
    
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "nc_milling_cost": jing_xi_cost_total,
        "nc_roughing_cost": kai_cu_cost_total,
        "nc_drilling_cost": drill_cost_total,
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
        print("Usage: python price_nc_time.py <job_id> <subgraph_id1> [subgraph_id2 ...]")
        sys.exit(1)
    
    job_id = sys.argv[1]
    subgraph_ids = sys.argv[2:]
    
    # 这里需要先调用检索脚本获取数据
    print("请通过 MCP 服务或 API 调用此计算脚本")
    print(f"job_id: {job_id}")
    print(f"subgraph_ids: {subgraph_ids}")
