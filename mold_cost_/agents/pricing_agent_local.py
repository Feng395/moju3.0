"""
PricingAgent Local - 价格计算Agent (本地脚本模式)
负责人：架构组
版本：v2.0

功能：
- 当 MCP 服务不可用时，直接调用本地脚本处理价格计算任务
- 直接调用 scripts/search 和 scripts/calculate 的 async 函数
- 提供与 MCP 模式 PricingAgent 相同的接口（process 方法）

使用场景：
- MCP 服务未启动
- 开发环境快速测试
- 降级备用方案
"""

from typing import Dict, Any, List
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

# 从环境变量读取批次大小配置
PRICING_BATCH_SIZE = int(os.getenv('PRICING_BATCH_SIZE', '50'))


class PricingAgentLocal:
    """
    Pricing Agent 本地脚本模式
    
    当 MCP 服务不可用时，直接调用本地脚本处理价格计算任务。
    接口与 PricingAgent (MCP模式) 完全一致，编排器无需区分。
    """
    
    def __init__(self, progress_publisher=None):
        self.name = "PricingAgentLocal"
        self.logger = logging.getLogger(f"Agent.{self.name}")
        self.progress_publisher = progress_publisher
        self.logger.info("Pricing Agent 初始化（本地脚本模式）")

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理价格计算请求（供编排器调用，与 PricingAgent.process 接口一致）
        
        Args:
            context: {"job_id": str, "subgraph_ids": List[str]}
        
        Returns:
            {"status": "ok", "message": "...", "total_cost": float, "breakdown": {...}}
        """
        import time
        
        job_id = context.get("job_id")
        subgraph_ids = context.get("subgraph_ids", [])
        
        if not job_id:
            return {"status": "error", "message": "缺少job_id参数", "error_code": "MISSING_JOB_ID"}
        
        if not subgraph_ids:
            return {"status": "error", "message": "缺少subgraph_ids参数", "error_code": "MISSING_SUBGRAPH_IDS"}
        
        self.logger.info(f"[本地脚本模式] 开始价格计算: job_id={job_id}, 子图数量={len(subgraph_ids)}")
        total_start = time.time()
        
        try:
            # 发布开始进度
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.PRICING_STARTED,
                    progress=ProgressPercent.PRICING_STARTED,
                    message="正在计算价格（本地脚本模式）...",
                    details={"source": "local_script", "subgraph_count": len(subgraph_ids)}
                )
            
            # ========== 阶段1: 并发搜索所有数据 ==========
            self.logger.info("[阶段1] 并发搜索所有数据")
            search_data = await self._concurrent_search(job_id, subgraph_ids)
            
            # ========== 阶段2: 并发计算所有费用 ==========
            self.logger.info("[阶段2] 并发计算所有费用")
            calc_results = await self._concurrent_calculate(search_data, job_id, subgraph_ids)
            
            # ========== 阶段3: 汇总搜索 ==========
            self.logger.info("[阶段3] 汇总搜索")
            from scripts.search import total_search
            await total_search.search_by_job_id(job_id, subgraph_ids)
            
            # ========== 阶段4-5: 线割总价 + 水磨总价 ==========
            self.logger.info("[阶段4-5] 线割总价 + 水磨总价计算")
            from scripts.calculate import price_wire_total, price_water_mill_total
            from scripts.search import (
                base_itemcode_search, total_search as ts, water_mill_search
            )
            
            # 准备搜索数据
            base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
            total_data = await ts.search_by_job_id(job_id, subgraph_ids)
            wm_data = await water_mill_search.search_by_job_id(job_id, subgraph_ids)
            
            wire_total_task = price_wire_total.calculate(
                {"base_itemcode": base_data, "total": total_data}, job_id, subgraph_ids
            )
            water_mill_total_task = price_water_mill_total.calculate(
                {"base_itemcode": base_data, "total": total_data, "water_mill": wm_data}, job_id, subgraph_ids
            )
            await asyncio.gather(wire_total_task, water_mill_total_task)
            
            # ========== 阶段6: 成本汇总检索 ==========
            self.logger.info("[阶段6] 成本汇总检索")
            from scripts.search import search as subgraphs_cost_search
            await subgraphs_cost_search.search_by_job_id(job_id, subgraph_ids)
            
            # ========== 阶段7: 数据清理和校验 ==========
            self.logger.info("[阶段7] 数据清理和校验")
            from scripts.calculate import judgment
            base_data_fresh = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
            await judgment.calculate({"base_itemcode": base_data_fresh}, job_id, subgraph_ids)
            
            # ========== 阶段8: 最终总价计算 ==========
            self.logger.info("[阶段8] 最终总价计算")
            from scripts.calculate import price_total
            subgraphs_cost_data = await subgraphs_cost_search.search_by_job_id(job_id, subgraph_ids)
            final_result = await price_total.calculate(
                {"subgraphs_cost": subgraphs_cost_data}, job_id, subgraph_ids
            )
            
            # 提取总价
            total_cost = final_result.get("job_total_cost", final_result.get("total_cost", 0.0))
            
            total_duration = time.time() - total_start
            self.logger.info(f"[本地脚本模式] 价格计算完成: total_cost={total_cost:.2f}, 耗时={total_duration*1000:.0f}ms")
            
            # 发布完成进度
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.PRICING_COMPLETED,
                    progress=ProgressPercent.PRICING_COMPLETED,
                    message=f"价格计算完成，总成本: {total_cost} CNY",
                    details={"source": "local_script", "total_cost": total_cost}
                )
            
            return {
                "status": "ok",
                "message": "价格计算完成",
                "total_cost": total_cost,
                "breakdown": {}
            }
            
        except Exception as e:
            self.logger.error(f"价格计算失败: {e}", exc_info=True)
            
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.PRICING_FAILED,
                    progress=ProgressPercent.PRICING_STARTED,
                    message=f"价格计算失败: {str(e)}",
                    details={"source": "local_script", "error": str(e)}
                )
            
            return {
                "status": "error",
                "message": f"价格计算失败: {str(e)}",
                "error_code": "PRICING_ERROR"
            }

    async def _concurrent_search(self, job_id: str, subgraph_ids: List[str]) -> Dict[str, Any]:
        """阶段1: 并发调用所有搜索脚本"""
        from scripts.search import (
            base_itemcode_search, material_search, density_search,
            heat_search, tooth_hole_search, water_mill_search,
            wire_base_search, wire_special_search, wire_standard_search,
            nc_search
        )
        
        search_tasks = [
            base_itemcode_search.search_by_job_id(job_id, subgraph_ids),
            material_search.search_by_job_id(job_id, subgraph_ids),
            density_search.search_by_job_id(job_id, subgraph_ids),
            heat_search.search_by_job_id(job_id, subgraph_ids),
            tooth_hole_search.search_by_job_id(job_id, subgraph_ids),
            water_mill_search.search_by_job_id(job_id, subgraph_ids),
            wire_base_search.search_by_job_id(job_id, subgraph_ids),
            wire_special_search.search_by_job_id(job_id, subgraph_ids),
            wire_standard_search.search_by_job_id(job_id, subgraph_ids),
            nc_search.search_by_job_id(job_id, subgraph_ids),
        ]
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        tool_names = [
            "base_itemcode", "material", "density", "heat", "tooth_hole",
            "water_mill", "wire_base", "wire_special", "wire_standard", "nc"
        ]
        
        merged = {"job_id": job_id}
        for i, name in enumerate(tool_names):
            result = results[i]
            if isinstance(result, Exception):
                self.logger.error(f"[搜索失败] {name}: {result}")
                if name in ["base_itemcode", "material"]:
                    raise ValueError(f"关键数据 {name} 搜索失败: {result}")
                merged[name] = {}
            else:
                merged[name] = result
        
        self.logger.info("[并发搜索] 完成")
        return merged

    async def _concurrent_calculate(
        self, search_data: Dict[str, Any], job_id: str, subgraph_ids: List[str]
    ) -> List:
        """阶段2: 并发调用所有计算脚本"""
        from scripts.calculate import (
            price_material, price_heat, price_weight, price_tooth_hole,
            price_wire_base, price_wire_special, price_wire_standard,
            price_add_auto_material,
            price_nc_base, price_nc_time, price_nc_total,
            price_water_mill_bevel_cost, price_water_mill_chamfer_cost,
            price_water_mill_component, price_water_mill_hanging_table,
            price_water_mill_high_cost, price_water_mill_long_strip,
            price_water_mill_oil_tank, price_water_mill_plate,
            price_water_mill_thread_ends
        )
        from scripts.search import (
            base_itemcode_search, material_search, density_search,
            heat_search, tooth_hole_search, water_mill_search,
            wire_base_search, wire_special_search, wire_standard_search,
            nc_search
        )
        
        # 每个计算脚本的 calculate() 需要 search_data 参数
        # 这里直接传 job_id + subgraph_ids，让 MCP server.py 中的逻辑在本地复现
        # 即：先搜索对应数据，再调用 calculate
        
        base_data = search_data.get("base_itemcode", {})
        mat_data = search_data.get("material", {})
        den_data = search_data.get("density", {})
        heat_data = search_data.get("heat", {})
        th_data = search_data.get("tooth_hole", {})
        wm_data = search_data.get("water_mill", {})
        wb_data = search_data.get("wire_base", {})
        ws_data = search_data.get("wire_special", {})
        wstd_data = search_data.get("wire_standard", {})
        nc_data = search_data.get("nc", {})
        
        calc_tasks = [
            # 基础计算
            price_material.calculate(
                {"base_itemcode": base_data, "material": mat_data, "density": den_data},
                job_id, subgraph_ids
            ),
            price_heat.calculate(
                {"base_itemcode": base_data, "heat": heat_data, "density": den_data},
                job_id, subgraph_ids
            ),
            price_weight.calculate(
                {"base_itemcode": base_data, "density": den_data},
                job_id, subgraph_ids
            ),
            # 牙孔
            price_tooth_hole.calculate(
                {"base_itemcode": base_data, "tooth_hole": th_data},
                job_id, subgraph_ids
            ),
            # 线割
            price_wire_base.calculate(
                {"base_itemcode": base_data, "wire_base": wb_data},
                job_id, subgraph_ids
            ),
            price_wire_special.calculate(
                {"base_itemcode": base_data, "wire_special": ws_data},
                job_id, subgraph_ids
            ),
            price_wire_standard.calculate(
                {"base_itemcode": base_data, "wire_standard": wstd_data},
                job_id, subgraph_ids
            ),
            price_add_auto_material.calculate(
                {"base_itemcode": base_data, "material": mat_data, "density": den_data},
                job_id, subgraph_ids
            ),
            # NC
            price_nc_base.calculate(
                {"base_itemcode": base_data, "nc": nc_data, "wire_base": wb_data},
                job_id, subgraph_ids
            ),
            price_nc_time.calculate(
                {"base_itemcode": base_data, "nc": nc_data},
                job_id, subgraph_ids
            ),
            self._calculate_nc_total(base_data, job_id, subgraph_ids),
            # 水磨 (9个)
            price_water_mill_bevel_cost.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_chamfer_cost.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_component.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_hanging_table.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_high_cost.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_long_strip.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_oil_tank.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_plate.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
            price_water_mill_thread_ends.calculate(
                {"base_itemcode": base_data, "water_mill": wm_data},
                job_id, subgraph_ids
            ),
        ]
        
        results = await asyncio.gather(*calc_tasks, return_exceptions=True)
        
        # 记录失败的计算
        calc_names = [
            "material", "heat", "weight", "tooth_hole",
            "wire_base", "wire_special", "wire_standard", "add_auto_material",
            "nc_base", "nc_time", "nc_total",
            "wm_bevel", "wm_chamfer", "wm_component", "wm_hanging_table",
            "wm_high", "wm_long_strip", "wm_oil_tank", "wm_plate", "wm_thread_ends"
        ]
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"[计算失败] {calc_names[i]}: {result}")
        
        self.logger.info("[并发计算] 完成")
        return results

    async def _calculate_nc_total(self, base_data, job_id, subgraph_ids):
        """NC总费用计算（需要先获取 total_search 数据）"""
        from scripts.search import total_search
        from scripts.calculate import price_nc_total
        total_data = await total_search.search_by_job_id(job_id, subgraph_ids)
        return await price_nc_total.calculate(
            {"base_itemcode": base_data, "total": total_data},
            job_id, subgraph_ids
        )
