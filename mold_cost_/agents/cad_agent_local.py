"""
CADAgent Local - CAD拆图与特征识别Agent (本地脚本模式)
负责人：架构组
版本：v1.0

功能：
- 当 MCP 服务不可用时，使用本地脚本处理 CAD 任务
- 直接调用 scripts/cad_chaitu 和 scripts/feature_recognition
- 提供与 MCP 模式相同的接口

使用场景：
- MCP 服务未启动
- 开发环境快速测试
- 降级备用方案
"""

from typing import Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)


class CADAgentLocal:
    """
    CAD Agent 本地脚本模式
    
    当 MCP 服务不可用时，直接调用本地脚本处理任务
    """
    
    def __init__(self, progress_publisher=None):
        """
        初始化本地脚本模式的 CAD Agent
        
        Args:
            progress_publisher: 进度发布器（可选）
        """
        self.name = "CADAgentLocal"
        self.logger = logging.getLogger(f"Agent.{self.name}")
        self.progress_publisher = progress_publisher
        
        self.logger.info("CAD Agent 初始化（本地脚本模式）")
    
    async def split(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        拆图方法（本地脚本模式）
        
        Args:
            context: {"job_id": "xxx", "dwg_url": "xxx"(可选)}
        
        Returns:
            {"status": "ok", "message": "...", "summary": {"subgraph_count": N}}
        """
        job_id = context.get("job_id")
        if not job_id:
            return {"status": "error", "message": "缺少 job_id", "error_code": "MISSING_JOB_ID"}
        
        try:
            self.logger.info(f"[本地脚本模式] 调用 cad_chaitu 脚本")
            
            # 发布拆图开始进度
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.CAD_SPLIT_STARTED,
                    progress=ProgressPercent.CAD_SPLIT_STARTED,
                    message="正在拆图...（本地脚本模式）",
                    details={"source": "local_script"}
                )
            
            # 导入本地脚本
            from scripts.cad_chaitu.main import chaitu_process
            
            # 获取参数
            dwg_url = context.get("dwg_url") or context.get("dwg_file_path")
            
            # 调用本地脚本（positional args: dwg_url, job_id, minio_client=None）
            result = await chaitu_process(dwg_url, job_id)
            
            if result.get("status") != "ok":
                # 发布拆图失败进度
                if self.progress_publisher:
                    from shared.progress_stages import ProgressStage, ProgressPercent
                    self.progress_publisher.publish_progress(
                        job_id=job_id,
                        stage=ProgressStage.CAD_SPLIT_FAILED,
                        progress=ProgressPercent.CAD_SPLIT_STARTED,
                        message=f"拆图失败: {result.get('message', '未知错误')}",
                        details={"source": "local_script"}
                    )
                return {
                    "status": "error",
                    "message": f"拆图失败: {result.get('message', '未知错误')}",
                    "error_code": "CHAITU_FAILED"
                }
            
            # 提取子图数量
            data = result.get("data", {})
            subgraph_count = data.get("total_count", 0)
            
            # 发布拆图完成进度
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.CAD_SPLIT_COMPLETED,
                    progress=ProgressPercent.CAD_SPLIT_COMPLETED,
                    message=f"拆图完成，生成{subgraph_count}个子图",
                    details={"source": "local_script", "subgraph_count": subgraph_count}
                )
            
            return {
                "status": "ok",
                "message": f"成功拆分 {subgraph_count} 个子图",
                "summary": {"subgraph_count": subgraph_count}
            }
                
        except Exception as e:
            self.logger.error(f"拆图失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"拆图失败: {str(e)}",
                "error_code": "SPLIT_ERROR"
            }
    
    async def recognize_features(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        特征识别方法（本地脚本模式）
        
        Args:
            context: {"job_id": "xxx"}
        
        Returns:
            {"status": "ok", "message": "...", "summary": {"success_count": N, "failed_count": M}}
        """
        job_id = context.get("job_id")
        if not job_id:
            return {"status": "error", "message": "缺少 job_id", "error_code": "MISSING_JOB_ID"}
        
        try:
            self.logger.info(f"[本地脚本模式] 调用 feature_recognition 脚本")
            
            # 导入本地脚本
            from scripts.feature_recognition.feature_recognition import batch_feature_recognition_process
            
            # 发布开始进度
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.FEATURE_RECOGNITION_STARTED,
                    progress=ProgressPercent.FEATURE_RECOGNITION_STARTED,
                    message="开始特征识别（本地脚本模式）",
                    details={"source": "local_script"}
                )
            
            # 调用本地脚本（同步函数，positional args: job_id, subgraph_id=None）
            result = await asyncio.to_thread(
                batch_feature_recognition_process,
                job_id, None
            )
            
            # batch_feature_recognition_process 返回格式:
            # {"success": True/False, "message": "...", "data": {"results": [...], "success_count": N, "failed_count": M}}
            if not result.get("success"):
                return {
                    "status": "error",
                    "message": f"特征识别失败: {result.get('message', '未知错误')}",
                    "error_code": "RECOGNITION_FAILED"
                }
            
            # 提取统计信息
            data = result.get("data", {})
            success_count = data.get("success_count", 0)
            failed_count = data.get("failed_count", 0)
            
            # 发布完成进度
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.FEATURE_RECOGNITION_COMPLETED,
                    progress=ProgressPercent.FEATURE_RECOGNITION_COMPLETED,
                    message=f"特征识别完成: 成功 {success_count} 个，失败 {failed_count} 个",
                    details={
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "source": "local_script"
                    }
                )
            
            # 执行工艺规则匹配
            try:
                from scripts.process_rule_matcher import match_and_update_process_rules
                # 查询所有子图ID
                subgraph_ids = await self._get_subgraph_ids(job_id)
                if subgraph_ids:
                    await match_and_update_process_rules(job_id, subgraph_ids)
                    self.logger.info(f"工艺规则匹配完成")
            except Exception as e:
                self.logger.warning(f"工艺规则匹配失败: {e}")
            
            return {
                "status": "ok",
                "message": f"特征识别完成: 成功 {success_count} 个，失败 {failed_count} 个",
                "summary": {
                    "success_count": success_count,
                    "failed_count": failed_count
                }
            }
                
        except Exception as e:
            self.logger.error(f"特征识别失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"特征识别失败: {str(e)}",
                "error_code": "RECOGNITION_ERROR"
            }
    
    async def _get_subgraph_ids(self, job_id: str):
        """查询任务的所有子图ID"""
        from shared.models import Subgraph
        from shared.database import get_db
        from sqlalchemy import select
        
        async for db in get_db():
            result = await db.execute(
                select(Subgraph.subgraph_id).where(Subgraph.job_id == job_id)
            )
            subgraph_ids = [row[0] for row in result.fetchall()]
            break
        
        return subgraph_ids
