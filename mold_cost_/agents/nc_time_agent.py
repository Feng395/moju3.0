"""
NCTimeAgent - NC时间计算Agent
负责人：人员B1
版本：v2.0

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/nc_time_agent.py
- 合并策略：使用 mold_cost-main 版本（功能更完整）
- 主要功能：
  1. 调用外部 NC Agent 获取每个子图的 NC 时间数据
  2. 解析 NC 返回的 JSON 数据
  3. 将时间数据写入 subgraphs 表
  4. 将详细时间数据写入 features 表
  5. 支持 MinIO 文件自动下载
  6. 支持进度发布

职责：
1. 调用外部 NC Agent 获取每个子图的 NC 时间数据
2. 解析 NC 返回的 JSON 数据
3. 将时间数据写入 subgraphs 表（nc_roughing_time, nc_milling_time, drilling_time）
4. 将详细时间数据写入 features 表（nc_time_cost 字段）
"""
from typing import Dict, Any, List
import httpx
import re
import os
from decimal import Decimal
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import select, update
from .base_agent import BaseAgent
from shared.database import get_db
from shared.models import Subgraph, Feature

class NCTimeAgent(BaseAgent):
    """
    NC时间计算Agent
    调用外部统一NC Agent计算钻孔、开粗、精铣时间
    """
    
    def __init__(self, nc_agent_url: str = None, progress_publisher=None):
        super().__init__("NCTimeAgent")
        # 从环境变量或配置文件读取配置
        import os
        from api_gateway.config import settings
        self.nc_agent_url = nc_agent_url or os.getenv("NC_AGENT_URL", settings.NC_AGENT_URL)
        self.timeout = int(os.getenv("NC_AGENT_TIMEOUT", str(settings.NC_AGENT_TIMEOUT)))
        self.progress_publisher = progress_publisher
        self.logger.info(f"[NCTimeAgent] 初始化完成: url={self.nc_agent_url}, timeout={self.timeout}秒")
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理NC时间计算
        
        Args:
            context: {
                "job_id": "任务ID",
                "dwg_file_path": "DWG文件路径（MinIO路径或本地路径）",
                "prt_file_path": "PRT文件路径（MinIO路径或本地路径）"
            }
        
        Returns:
            {
                "status": "ok" | "error",
                "message": "消息",
                "summary": {
                    "total_subgraphs": 总子图数,
                    "success_count": 成功数,
                    "failed_count": 失败数
                }
            }
        """
        job_id = context.get("job_id")
        if not job_id:
            return {"status": "error", "message": "缺少 job_id 参数"}
        
        self.logger.info(f"[NCTimeAgent] 开始处理 NC 时间计算: job_id={job_id}")
        
        # 发布进度：NC 时间计算开始
        if self.progress_publisher:
            from shared.progress_stages import ProgressStage, ProgressPercent
            self.progress_publisher.publish_progress(
                job_id=job_id,
                stage=ProgressStage.NC_CALCULATION_STARTED,
                progress=ProgressPercent.NC_CALCULATION_STARTED,
                message="NC 时间计算开始",
                details={"nc_agent_url": self.nc_agent_url}
            )
        
        # 临时文件列表（用于清理）
        temp_files = []
        
        try:
            # 1. 获取文件路径（如果是 MinIO 路径，需要先下载）
            dwg_file_path = context.get("dwg_file_path")
            prt_file_path = context.get("prt_file_path")
            
            if not dwg_file_path or not prt_file_path:
                return {"status": "error", "message": "缺少 dwg_file_path 或 prt_file_path 参数"}
            
            # 检查是否为 MinIO 路径（不以 / 或盘符开头）
            dwg_local_path = await self._ensure_local_file(dwg_file_path, job_id, "dwg")
            prt_local_path = await self._ensure_local_file(prt_file_path, job_id, "prt")
            
            if dwg_local_path != dwg_file_path:
                temp_files.append(dwg_local_path)
            if prt_local_path != prt_file_path:
                temp_files.append(prt_local_path)
            
            # 2. 调用外部 NC Agent
            nc_result = await self.call_nc_agent(
                job_id=job_id,
                dwg_file=dwg_local_path,
                prt_file=prt_local_path
            )
            
            if nc_result.get("code") != 200:
                error_msg = nc_result.get("message", "NC Agent 调用失败")
                self.logger.error(f"[NCTimeAgent] NC Agent 返回错误: {error_msg}")
                return {"status": "error", "message": error_msg}
            
            # 3. 解析 NC 返回的数据
            json_output = nc_result.get("data", {}).get("json_output", {})
            if not json_output:
                self.logger.warning(f"[NCTimeAgent] NC Agent 返回空数据")
                return {"status": "error", "message": "NC Agent 返回空数据"}
            
            # ========== 打印 NC Agent 返回的原始数据 ==========
            self.logger.info(f"[NCTimeAgent] ========================================")
            self.logger.info(f"[NCTimeAgent] NC Agent 返回数据（原始）")
            self.logger.info(f"[NCTimeAgent] 子图总数: {len(json_output)}")
            self.logger.info(f"[NCTimeAgent] ========================================")
            
            for subgraph_name, subgraph_data in json_output.items():
                self.logger.info(f"[NCTimeAgent] ")
                self.logger.info(f"[NCTimeAgent] 子图: {subgraph_name}")
                operations = subgraph_data.get("operations", [])
                self.logger.info(f"[NCTimeAgent] 操作数量: {len(operations)}")
                
                for op in operations:
                    op_name = op.get("operation_name", "")
                    params = op.get("parameters", [])
                    
                    # 查找 id=124 的参数（Toolpath Time）
                    time_param = next((p for p in params if p.get("id") == 124), None)
                    
                    if time_param:
                        time_value = time_param.get("value", 0)
                        display_name = time_param.get("display_name", "")
                        self.logger.info(
                            f"[NCTimeAgent]   操作: {op_name} | "
                            f"时间: {time_value} | "
                            f"参数: id={time_param.get('id')}, {display_name}"
                        )
                    else:
                        self.logger.warning(f"[NCTimeAgent]   操作: {op_name} | 未找到 id=124 的时间参数")
            
            self.logger.info(f"[NCTimeAgent] ========================================")
            
            # 4. 处理每个子图的数据
            success_count = 0
            failed_count = 0
            
            for subgraph_name, subgraph_data in json_output.items():
                try:
                    # 提取子图 ID（例如：PH-01-M250297-P5.json -> PH-01）
                    subgraph_short_id = self._extract_subgraph_id(subgraph_name)
                    
                    # 查找对应的 subgraph_id（完整ID）
                    subgraph_id = await self._find_subgraph_id(job_id, subgraph_short_id)
                    
                    if not subgraph_id:
                        self.logger.warning(
                            f"[NCTimeAgent] 未找到子图映射: {subgraph_name} -> {subgraph_short_id}"
                        )
                        failed_count += 1
                        continue
                    
                    # ========== 保存子图的原始响应数据 ==========
                    await self._save_subgraph_response(job_id, subgraph_id, subgraph_name, subgraph_data)
                    
                    # 解析操作数据
                    operations = subgraph_data.get("operations", [])
                    time_data = self._parse_operations(operations)
                    
                    # 写入数据库
                    await self._save_nc_time_data(subgraph_id, time_data)
                    
                    success_count += 1
                    self.logger.info(
                        f"[NCTimeAgent] 成功处理子图: {subgraph_name} -> {subgraph_id}"
                    )
                    
                except Exception as e:
                    self.logger.error(
                        f"[NCTimeAgent] 处理子图失败: {subgraph_name}, error={e}",
                        exc_info=True
                    )
                    failed_count += 1
            
            # 5. 返回结果
            total_count = success_count + failed_count
            self.logger.info(
                f"[NCTimeAgent] NC 时间计算完成: "
                f"total={total_count}, success={success_count}, failed={failed_count}"
            )
            
            # 发布进度：NC 时间计算完成
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.NC_CALCULATION_COMPLETED,
                    progress=ProgressPercent.NC_CALCULATION_COMPLETED,
                    message=f"NC 时间计算完成，成功 {success_count}/{total_count}",
                    details={
                        "total_subgraphs": total_count,
                        "success_count": success_count,
                        "failed_count": failed_count
                    }
                )
            
            return {
                "status": "ok",
                "message": f"NC 时间计算完成，成功 {success_count}/{total_count}",
                "summary": {
                    "total_subgraphs": total_count,
                    "success_count": success_count,
                    "failed_count": failed_count
                }
            }
            
        except Exception as e:
            self.logger.error(f"[NCTimeAgent] NC 时间计算失败: {e}", exc_info=True)
            
            # 发布进度：NC 时间计算失败
            if self.progress_publisher:
                from shared.progress_stages import ProgressStage, ProgressPercent
                self.progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.NC_CALCULATION_FAILED,
                    progress=ProgressPercent.NC_CALCULATION_STARTED,
                    message=f"NC 时间计算失败: {str(e)}",
                    details={"error": str(e)}
                )
            
            return {"status": "error", "message": f"NC 时间计算失败: {str(e)}"}
        
        finally:
            # 清理临时文件
            await self._cleanup_temp_files(temp_files)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def call_nc_agent(
        self,
        job_id: str,
        dwg_file: str = None,
        prt_file: str = None
    ) -> Dict[str, Any]:
        """
        调用外部 NC Agent (NC 3D Workflow API)
        
        Args:
            job_id: 任务ID
            dwg_file: DWG文件路径（保持原始格式）
            prt_file: PRT文件路径
        
        Returns:
            NC Agent 返回的 JSON 数据
        """
        self.logger.info(f"[NCTimeAgent] 调用 NC Agent: {self.nc_agent_url}")
        
        if not prt_file or not dwg_file:
            raise ValueError("必须提供 prt_file 和 dwg_file 路径")
        
        # 准备文件上传
        files = {}
        try:
            # 获取原始文件扩展名
            import os
            dwg_ext = os.path.splitext(dwg_file)[1]  # .dwg 或 .dxf
            prt_ext = os.path.splitext(prt_file)[1]  # .prt
            
            # 使用原始文件名和扩展名
            files['prt_file'] = (f'model{prt_ext}', open(prt_file, 'rb'), 'application/octet-stream')
            files['dxf_file'] = (f'drawing{dwg_ext}', open(dwg_file, 'rb'), 'application/octet-stream')
            
            # 准备表单数据
            data = {
                'skip_approval': 'true',
                'auto_continue': 'true'
            }
            
            self.logger.info(f"[NCTimeAgent] 上传文件: prt={prt_file}, dwg={dwg_file}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.nc_agent_url}/api/v1/workflow/3d/run",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                return response.json()
                
        finally:
            # 关闭文件句柄
            for file_tuple in files.values():
                if len(file_tuple) > 1 and hasattr(file_tuple[1], 'close'):
                    file_tuple[1].close()
    
    def _extract_subgraph_id(self, subgraph_name: str) -> str:
        """
        从子图名称中提取短ID
        
        例如：
        - PH-01-M250297-P5.json -> PH-01
        - PU-06-M250297-P5.json -> PU-06
        
        Args:
            subgraph_name: 子图名称
        
        Returns:
            短ID（如 PH-01）
        """
        # 移除 .json 后缀
        name = subgraph_name.replace(".json", "")
        
        # 提取前两段（例如：PH-01）
        parts = name.split("-")
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        
        return name
    
    async def _find_subgraph_id(self, job_id: str, short_id: str) -> str:
        """
        根据短ID查找完整的 subgraph_id
        
        Args:
            job_id: 任务ID
            short_id: 短ID（如 PH-01）
        
        Returns:
            完整的 subgraph_id（如 2cd0b581-f2b9-481d-a2fd-33074f57ebd4_PH-01）
        """
        import uuid
        job_uuid = uuid.UUID(job_id)
        
        async for db in get_db():
            # 查询所有子图
            result = await db.execute(
                select(Subgraph.subgraph_id)
                .where(Subgraph.job_id == job_uuid)
            )
            subgraph_ids = [row[0] for row in result.fetchall()]
            
            # 查找匹配的子图ID（以 short_id 结尾）
            for subgraph_id in subgraph_ids:
                if subgraph_id.endswith(f"_{short_id}") or subgraph_id == short_id:
                    return subgraph_id
            
            break
        
        return None
    
    async def _ensure_local_file(self, file_path: str, job_id: str, file_type: str) -> str:
        """
        确保文件在本地文件系统中
        
        如果是 MinIO 路径，下载到临时目录
        如果是本地路径，直接返回
        
        Args:
            file_path: 文件路径（MinIO 或本地）
            job_id: 任务ID
            file_type: 文件类型（dwg 或 prt）
        
        Returns:
            本地文件路径
        """
        import tempfile
        from pathlib import Path
        
        # 判断是否为本地路径（以 / 或盘符开头，如 C:）
        if file_path.startswith('/') or (len(file_path) > 1 and file_path[1] == ':'):
            # 本地路径，检查文件是否存在
            if Path(file_path).exists():
                self.logger.info(f"[NCTimeAgent] 使用本地文件: {file_path}")
                return file_path
            else:
                raise FileNotFoundError(f"本地文件不存在: {file_path}")
        
        # MinIO 路径，需要下载
        self.logger.info(f"[NCTimeAgent] 检测到 MinIO 路径，开始下载: {file_path}")
        
        try:
            from scripts.minio_client import MinIOClient
            
            # 创建 MinIO 客户端
            minio_client = MinIOClient()
            
            # 创建临时目录
            temp_dir = Path(tempfile.gettempdir()) / "nc_agent" / job_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成本地文件名
            file_ext = Path(file_path).suffix
            local_file = temp_dir / f"{file_type}{file_ext}"
            
            # 下载文件（使用正确的方法名 get_file）
            success = minio_client.get_file(file_path, str(local_file))
            
            if not success:
                raise Exception(f"从 MinIO 下载文件失败: {file_path}")
            
            self.logger.info(f"[NCTimeAgent] 文件下载成功: {file_path} -> {local_file}")
            return str(local_file)
            
        except Exception as e:
            self.logger.error(f"[NCTimeAgent] 处理文件失败: {file_path}, error={e}")
            raise
    
    async def _cleanup_temp_files(self, temp_files: List[str]):
        """
        清理临时文件
        
        Args:
            temp_files: 临时文件路径列表
        """
        if not temp_files:
            return
        
        import os
        from pathlib import Path
        
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"[NCTimeAgent] 已删除临时文件: {file_path}")
                    
                    # 尝试删除空的临时目录
                    parent_dir = Path(file_path).parent
                    if parent_dir.exists() and not list(parent_dir.iterdir()):
                        parent_dir.rmdir()
                        self.logger.debug(f"[NCTimeAgent] 已删除空目录: {parent_dir}")
                        
            except Exception as e:
                self.logger.warning(f"[NCTimeAgent] 清理临时文件失败: {file_path}, error={e}")
    
    async def _save_subgraph_response(
        self, 
        job_id: str, 
        subgraph_id: str, 
        subgraph_name: str, 
        subgraph_data: Dict[str, Any]
    ):
        """
        保存单个子图的 NC Agent 响应数据到本地文件
        
        Args:
            job_id: 任务ID
            subgraph_id: 子图完整ID（如 2cd0b581-f2b9-481d-a2fd-33074f57ebd4_PH-01）
            subgraph_name: 子图文件名（如 PH-01-M250297-P5.json）
            subgraph_data: 子图的 NC 数据
        """
        import json
        from pathlib import Path
        from datetime import datetime
        
        try:
            # 创建保存目录：logs/nc_responses/job_id/subgraphs/
            save_dir = Path("logs") / "nc_responses" / job_id / "subgraphs"
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 提取子图短ID（如 PH-01）
            subgraph_short_id = self._extract_subgraph_id(subgraph_name)
            
            # 构建子图数据结构
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            data = {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "subgraph_short_id": subgraph_short_id,
                "file_name": subgraph_name,
                "timestamp": timestamp,
                "meta_data": subgraph_data.get("meta_data", {}),
                "operations": subgraph_data.get("operations", [])
            }
            
            # 保存为单独的 JSON 文件
            filename = f"{subgraph_short_id}_{timestamp}.json"
            filepath = save_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(
                f"[NCTimeAgent] 保存子图数据: {subgraph_short_id} -> {filepath}"
            )
            
        except Exception as e:
            self.logger.error(
                f"[NCTimeAgent] 保存子图数据失败: {subgraph_name}, error={e}", 
                exc_info=True
            )
    
    async def _save_raw_response(self, job_id: str, nc_result: Dict[str, Any]):
        """
        保存 NC Agent 原始响应到本地文件（按子图保存）
        
        Args:
            job_id: 任务ID
            nc_result: NC Agent 返回的完整响应
        """
        import json
        from pathlib import Path
        from datetime import datetime
        
        try:
            # 创建保存目录：logs/nc_responses/job_id/
            save_dir = Path("logs") / "nc_responses" / job_id
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 提取 json_output（包含所有子图数据）
            json_output = nc_result.get("data", {}).get("json_output", {})
            
            if not json_output:
                self.logger.warning(f"[NCTimeAgent] NC Agent 返回空数据，无法保存")
                return
            
            # 构建完整的数据结构（包含所有子图）
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            complete_data = {
                "job_id": job_id,
                "timestamp": timestamp,
                "task_id": nc_result.get("data", {}).get("task_id"),
                "execution_time": nc_result.get("data", {}).get("execution_time"),
                "total_subgraphs": len(json_output),
                "subgraphs": {}
            }
            
            # 遍历每个子图，保存详细数据
            for subgraph_name, subgraph_data in json_output.items():
                # 提取子图短ID（如 PH-01）
                subgraph_short_id = self._extract_subgraph_id(subgraph_name)
                
                # 保存子图数据
                complete_data["subgraphs"][subgraph_short_id] = {
                    "file_name": subgraph_name,
                    "meta_data": subgraph_data.get("meta_data", {}),
                    "operations": subgraph_data.get("operations", [])
                }
            
            # 保存为一个完整的 JSON 文件
            filename = f"nc_data_{job_id}_{timestamp}.json"
            filepath = save_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(complete_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(
                f"[NCTimeAgent] ✅ NC 数据已保存: {filepath} "
                f"(包含 {len(json_output)} 个子图)"
            )
            
        except Exception as e:
            self.logger.error(f"[NCTimeAgent] 保存 NC 数据失败: {e}", exc_info=True)
    
    def _parse_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        解析操作数据，提取时间信息
        
        分类规则：
        1. 操作名称包含"粗"字（一般开头两个字是"开粗"）-> nc_roughing_time（开粗）
        2. 操作名称包含"精"字（一般开头两个字是"半精"或"全精"）-> nc_milling_time（精铣）
        3. XX_XX_XX 格式（如 Z_M_A14）提取中间部分 -> drilling_time（钻孔）
        4. XX_ZXZ 格式（如 Z_ZXZ）提取 ZXZ -> drilling_time（钻孔）
        
        Args:
            operations: 操作列表
        
        Returns:
            {
                "nc_roughing_time": Decimal,  # 开粗时间（分钟）
                "nc_milling_time": Decimal,   # 精铣时间（分钟）
                "drilling_time": Decimal,     # 钻孔时间（分钟）
                "nc_details": [               # 详细数据（按类型汇总）
                    {"code": "M", "value": "1.2"},
                    {"code": "L", "value": "3.5"},
                    {"code": "M1", "value": "2.0"},
                    {"code": "ZXZ", "value": "2.1"},
                    {"code": "开粗", "value": "150.0"},
                    {"code": "半精", "value": "80.0"},
                    {"code": "全精", "value": "75.0"}
                ]
            }
        """
        nc_roughing_time = Decimal("0")  # 开粗（分钟）
        nc_milling_time = Decimal("0")   # 精铣（分钟）
        drilling_time = Decimal("0")     # 钻孔（分钟）
        
        # 用于汇总各类型的时间
        code_totals = {}  # {code: total_time}
        
        for operation in operations:
            operation_name = operation.get("operation_name", "")
            
            # 提取 Toolpath Time（取 parameters 里面的第一个 value）
            time_value = self._extract_toolpath_time(operation)
            if time_value is None:
                continue
            
            # 分类判断（按优先级）
            code = None
            
            # 1. 检查是否包含"粗"字（开粗）
            if "粗" in operation_name:
                nc_roughing_time += time_value
                code = "开粗"
            
            # 2. 检查是否包含"精"字（半精、全精）
            elif "精" in operation_name:
                nc_milling_time += time_value
                # 区分半精和全精
                if operation_name.startswith("半精"):
                    code = "半精"
                elif operation_name.startswith("全精"):
                    code = "全精"
                else:
                    code = "精铣"  # 其他包含"精"的操作
            
            # 3. 检查是否为钻孔操作（XX_XX_XX 或 XX_ZXZ 格式）
            # 包括 Z_、B_、X_ 等前缀
            elif self._is_drilling_operation(operation_name):
                drilling_time += time_value
                # 提取操作代码（如 M, L, M1, C, ZXZ）
                code = self._extract_operation_code(operation_name)
            
            # 如果没有匹配到任何类型，跳过
            else:
                self.logger.warning(f"[NCTimeAgent] 无法分类操作: {operation_name}")
                continue
            
            # 汇总到对应的 code
            if code not in code_totals:
                code_totals[code] = Decimal("0")
            code_totals[code] += time_value
        
        # 构建 nc_details（按固定顺序，包含所有可能的类型）
        nc_details = []
        
        # 定义所有可能的钻孔类型（按字母顺序）
        all_drilling_codes = ["C", "L", "M", "M1", "M2", "ZXZ"]
        
        # 先输出钻孔类型
        for code in all_drilling_codes:
            value = code_totals.get(code, Decimal("0"))
            nc_details.append({
                "code": code,
                "value": str(round(value, 2)) if value > 0 else "0"
            })
        
        # 再输出加工类型（开粗、半精、全精）
        for code in ["开粗", "半精", "全精"]:
            value = code_totals.get(code, Decimal("0"))
            nc_details.append({
                "code": code,
                "value": str(round(value, 2)) if value > 0 else "0"
            })
        
        return {
            "nc_roughing_time": round(nc_roughing_time, 2),
            "nc_milling_time": round(nc_milling_time, 2),
            "drilling_time": round(drilling_time, 2),
            "nc_details": nc_details
        }
    
    def _extract_toolpath_time(self, operation: Dict[str, Any]) -> Decimal:
        """
        从操作中提取 Toolpath Time（取 parameters 里面的第一个 value）
        
        Args:
            operation: 操作数据
        
        Returns:
            时间值（分钟），如果未找到返回 None
        """
        parameters = operation.get("parameters", [])
        
        # 取第一个参数的 value（通常是 id=124 的 Toolpath Time）
        if parameters and len(parameters) > 0:
            first_param = parameters[0]
            value = first_param.get("value")
            if value is not None:
                return Decimal(str(value))
        
        return None
    
    def _is_drilling_operation(self, operation_name: str) -> bool:
        """
        判断是否为钻孔操作
        
        规则：
        1. XX_ZXZ 格式（如 Z_ZXZ）
        2. XX_XX_XX 格式（如 Z_M_A14, Z_L_A3, B_M1_A9, X_C_D17.0）
        
        Args:
            operation_name: 操作名称
        
        Returns:
            是否为钻孔操作
        """
        # 检查是否为 XX_ZXZ 格式
        if re.match(r"^[A-Z]+_ZXZ$", operation_name):
            return True
        
        # 检查是否为 XX_XX_XX 格式（中间部分是字母+可选数字的组合）
        # 例如：Z_M_A14, Z_L_A3, B_M1_A9, Z_C_A18, X_C_D17.0
        if re.match(r"^[A-Z]+_[A-Z]\d*_", operation_name):
            return True
        
        return False
    
    def _extract_operation_code(self, operation_name: str) -> str:
        """
        从操作名称中提取代码
        
        规则：
        1. 对于 XX_XX_XX 格式，提取中间的 XX（可能是字母+数字，如 M, L, M1, C）
        2. 对于 XX_ZXZ 格式，提取 ZXZ
        
        例如：
        - Z_M_A14 -> M
        - Z_L_A3 -> L
        - B_M1_A9 -> M1
        - Z_ZXZ -> ZXZ
        - Z_C_A18 -> C
        - X_C_D17.0 -> C
        
        Args:
            operation_name: 操作名称
        
        Returns:
            操作代码（如 M, L, M1, C, ZXZ）
        """
        # 检查是否为 XX_ZXZ 格式
        if re.match(r"^[A-Z]+_ZXZ$", operation_name):
            return "ZXZ"
        
        # 提取 XX_XX_XX 格式中间的 XX（字母+可选数字）
        # 例如：Z_M_A14 -> M, Z_M1_A18 -> M1, Z_C_A18 -> C, X_C_D17.0 -> C
        match = re.search(r"^[A-Z]+_([A-Z]\d*)_", operation_name)
        if match:
            return match.group(1)
        
        # 如果无法匹配，返回原始名称
        self.logger.warning(f"[NCTimeAgent] 无法提取操作代码: {operation_name}")
        return operation_name
    
    async def _save_nc_time_data(self, subgraph_id: str, time_data: Dict[str, Any]):
        """
        保存 NC 时间数据到数据库
        
        Args:
            subgraph_id: 子图ID
            time_data: 时间数据
        """
        async for db in get_db():
            # 1. 更新 subgraphs 表
            await db.execute(
                update(Subgraph)
                .where(Subgraph.subgraph_id == subgraph_id)
                .values(
                    nc_roughing_time=time_data["nc_roughing_time"],
                    nc_milling_time=time_data["nc_milling_time"],
                    drilling_time=time_data["drilling_time"],
                    updated_at=datetime.utcnow()
                )
            )
            
            # 2. 更新 features 表（nc_time_cost 字段）
            await db.execute(
                update(Feature)
                .where(Feature.subgraph_id == subgraph_id)
                .values(
                    nc_time_cost={"nc_details": time_data["nc_details"]},
                    created_at=datetime.utcnow()
                )
            )
            
            await db.commit()
            
            self.logger.debug(
                f"[NCTimeAgent] 保存 NC 时间数据: subgraph_id={subgraph_id}, "
                f"roughing={time_data['nc_roughing_time']}分, "
                f"milling={time_data['nc_milling_time']}分, "
                f"drilling={time_data['drilling_time']}分"
            )
            
            break
