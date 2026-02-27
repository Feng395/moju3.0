"""
DataModificationHandler - 数据修改处理器
负责人：人员B2

处理数据修改意图，复用现有的 NLPParser 和 ModificationValidator
"""
import logging
import copy
import uuid
from typing import Dict, Any
from datetime import datetime
from shared.timezone_utils import now_shanghai

from .base_handler import BaseActionHandler
from agents.intent_types import IntentResult, ActionResult

logger = logging.getLogger(__name__)


class DataModificationHandler(BaseActionHandler):
    """
    数据修改处理器
    
    功能：
    1. 使用 NLPParser 解析自然语言修改指令
    2. 使用 ModificationValidator 验证修改
    3. 应用修改到临时数据（不直接写数据库）
    4. 保存 pending_action 到 Redis
    5. 返回确认消息
    """
    
    def __init__(self):
        """初始化 Handler"""
        super().__init__()
        self._nlp_parser = None
        self._chat_history_repo = None
        logger.info("✅ DataModificationHandler 初始化完成")
    
    @property
    def nlp_parser(self):
        """懒加载 NLP Parser"""
        if self._nlp_parser is None:
            from agents.nlp_parser import NLPParser
            self._nlp_parser = NLPParser(use_llm=True)
        return self._nlp_parser
    
    @property
    def chat_history_repo(self):
        """懒加载 ChatHistoryRepository"""
        if self._chat_history_repo is None:
            from api_gateway.repositories.chat_history_repository import ChatHistoryRepository
            self._chat_history_repo = ChatHistoryRepository()
        return self._chat_history_repo
    
    async def handle(
        self,
        intent_result: IntentResult,
        job_id: str,
        context: Dict[str, Any],
        db_session
    ) -> ActionResult:
        """
        处理数据修改请求
        
        Args:
            intent_result: 意图识别结果
            job_id: 任务ID
            context: 当前审核数据上下文（包含 raw_data 和 display_view）
            db_session: 数据库会话
        
        Returns:
            ActionResult: 处理结果
        """
        logger.info(f"🔧 处理数据修改: {intent_result.raw_message}")
        
        try:
            # 🆕 获取 raw_data（向后兼容）
            raw_data = context.get("raw_data") or context
            
            # 1. 解析自然语言（NLPParser 会自动使用 display_view）
            logger.info("🔍 解析自然语言...")
            
            # 🔑 传递 db_session 到 context（用于查询 process_rules）
            parse_context = {**context, "db_session": db_session}
            
            parsed_changes = await self.nlp_parser.parse(
                intent_result.raw_message,
                parse_context  # 传递包含 db_session 的上下文
            )
            
            if not parsed_changes:
                return ActionResult(
                    status="error",
                    message="无法解析修改指令，请换一种方式描述",
                    data={}
                )
            
            # 🆕 1.5. 智能推断：如果修改了所有记录，尝试从历史推断子图
            parsed_changes = await self._infer_target_from_history(
                parsed_changes,
                intent_result.raw_message,
                job_id,
                context,  # 🔑 传递完整的 context，而不是 raw_data
                db_session
            )
            
            # 🔑 检查推断后是否为空（说明推断的子图不存在）
            if not parsed_changes:
                return ActionResult(
                    status="error",
                    message="无法确定要修改的目标。请明确指定子图ID，例如：'PH2-04 材质改为 45#'",
                    data={}
                )
            
            # 2. 验证修改
            logger.info("✅ 验证修改...")
            from shared.validators import ModificationValidator
            
            validation_result = ModificationValidator.validate_changes(
                parsed_changes,
                raw_data  # 🔑 使用 raw_data 验证
            )
            
            if not validation_result.is_valid:
                logger.error(f"❌ 修改验证失败: {validation_result.error_message}")
                return ActionResult(
                    status="error",
                    message=f"修改验证失败: {validation_result.error_message}",
                    data={}
                )
            
            # 记录警告
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning(f"⚠️  {warning}")
            
            # 3. 应用修改到临时数据
            logger.info("🔧 应用修改到临时数据...")
            modified_data = self._apply_changes(
                raw_data, 
                parsed_changes,
                job_id,  # 🆕 传递 job_id
                context.get("user_id", "system")  # 🆕 传递 user_id
            )
            
            # 🆕 4. 重新构建展示视图（基于修改后的数据）
            logger.info("🔄 重新构建展示视图...")
            from agents.data_view_builder import DataViewBuilder
            modified_display_view = DataViewBuilder.build_display_view(modified_data)
            logger.info(f"✅ 修改后的展示视图: {len(modified_display_view)} 条记录")
            
            # 5. 生成修改记录
            modification_record = {
                "id": str(uuid.uuid4()),
                "text": intent_result.raw_message,
                "parsed": parsed_changes,
                "timestamp": now_shanghai().isoformat()
            }
            
            # 6. 保存 pending_action 到 Redis
            await self._save_pending_action(job_id, {
                "action_type": "DATA_MODIFICATION",
                "changes": parsed_changes,
                "modified_data": modified_data,
                "modified_display_view": modified_display_view,  # 🆕 保存修改后的展示视图
                "modification_record": modification_record
            })
            
            # 7. 格式化确认消息
            message = self._format_modification_message(parsed_changes)
            
            logger.info(f"✅ 数据修改处理完成")
            
            # 8. 返回确认消息（包含修改后的展示视图和原始数据）
            return ActionResult(
                status="ok",
                message=message,
                requires_confirmation=True,
                pending_action={
                    "action_type": "DATA_MODIFICATION",
                    "changes": parsed_changes
                },
                data={
                    "modification_id": modification_record["id"],
                    "parsed_changes": parsed_changes,
                    "modified_data": modified_data,  # 🆕 返回修改后的原始数据
                    "display_view": modified_display_view  # 🆕 返回修改后的完整展示视图
                }
            )
        
        except Exception as e:
            logger.error(f"❌ 处理数据修改失败: {e}", exc_info=True)
            return ActionResult(
                status="error",
                message=f"处理修改失败：{str(e)}",
                data={}
            )
    
    def _apply_changes(
        self,
        data: Dict[str, Any],
        changes: list,
        job_id: str,
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        应用修改到数据（支持 ID 匹配和过滤条件匹配）
        
        Args:
            data: 原始数据
            changes: 修改列表
            job_id: 任务ID（用于安全检查）
            user_id: 用户ID（用于审计）
        
        Returns:
            修改后的数据
        """
        logger.info(f"🔧 应用 {len(changes)} 个修改 (job_id={job_id})")
        
        # 深拷贝数据
        modified_data = copy.deepcopy(data)
        
        for change in changes:
            table = change.get("table")
            field = change.get("field")
            value = change.get("value")
            
            # 🆕 表名映射：支持向后兼容
            # 如果数据中使用旧键名 price_snapshots，映射到新键名 job_price_snapshots
            table_mapping = {
                "price_snapshots": "job_price_snapshots",  # 旧键名 → 新键名
                "process_snapshots": "job_process_snapshots"  # 旧键名 → 新键名
            }
            
            # 尝试使用原表名，如果不存在则尝试映射
            data_key = table
            if data_key not in modified_data:
                # 尝试反向映射（新键名 → 旧键名）
                reverse_mapping = {v: k for k, v in table_mapping.items()}
                data_key = reverse_mapping.get(table, table)
                
                # 如果还是不存在，尝试正向映射（旧键名 → 新键名）
                if data_key not in modified_data:
                    data_key = table_mapping.get(table, table)
            
            # 🆕 支持两种匹配方式
            record_id = change.get("id")  # ID 匹配（原有方式）
            filter_conditions = change.get("filter")  # 过滤条件匹配（新增）
            
            # 🔍 调试日志
            logger.info(f"🔍 处理修改: table={table} (data_key={data_key}), field={field}, value={value}")
            logger.info(f"🔍 匹配条件: id={record_id}, filter={filter_conditions}")
            
            if data_key in modified_data:
                matched_count = 0
                total_records = len(modified_data[data_key])
                logger.info(f"🔍 表 {data_key} 共有 {total_records} 条记录")
                
                for record in modified_data[data_key]:
                    # ✅ 安全检查：必须匹配 job_id
                    if record.get("job_id") != job_id:
                        continue
                    
                    # 判断是否匹配
                    is_match = False
                    
                    if record_id:
                        # ID 匹配
                        id_field = self._get_id_field(table)
                        is_match = (record.get(id_field) == record_id)
                    
                    elif filter_conditions:
                        # 🆕 过滤条件匹配
                        # 🔍 调试：显示记录的关键字段
                        logger.debug(f"🔍 检查记录: category={record.get('category')}, sub_category={record.get('sub_category')}")
                        is_match = self._match_filter(record, filter_conditions)
                    
                    if is_match:
                        # 🆕 标准化材质值（TOOLOX → T00L0X）
                        normalized_value = value
                        if field.lower() in ['material', '材质']:
                            normalized_value = self._normalize_material(value)
                            if normalized_value != value:
                                logger.info(f"🔄 材质标准化: {value} → {normalized_value}")
                        
                        # 更新字段值
                        record[field] = normalized_value
                        
                        # 🆕 更新审计字段（仅对快照表）
                        if table in ["job_price_snapshots", "job_process_snapshots"]:
                            record["is_modified"] = True
                            record["modified_by"] = user_id
                            record["modified_at"] = now_shanghai()  # 保持为 datetime 对象（Asia/Shanghai）
                        
                        matched_count += 1
                        
                        # 记录日志
                        if record_id:
                            id_field = self._get_id_field(table)
                            logger.info(f"✅ 修改: {data_key}.{id_field}={record_id}, {field}={value}")
                        else:
                            logger.info(f"✅ 修改: {data_key} (filter), {field}={value}")
                
                if matched_count > 0:
                    logger.info(f"✅ 批量修改完成: {matched_count} 条记录")
                elif record_id or filter_conditions:
                    logger.warning(f"⚠️  未找到匹配的记录: table={table}, data_key={data_key}, change={change}")
            else:
                logger.warning(f"⚠️  数据中不存在表: {data_key} (原表名: {table})")
        
        return modified_data
    
    def _match_filter(self, record: dict, filter_conditions: dict) -> bool:
        """
        检查记录是否匹配过滤条件
        
        Args:
            record: 数据记录
            filter_conditions: 过滤条件 {"category": "wire", "sub_category": "slow_and_one"}
        
        Returns:
            是否匹配
        """
        for key, value in filter_conditions.items():
            # 支持字符串比较（忽略大小写）
            record_value = record.get(key)
            
            # 🔍 调试日志
            logger.debug(f"🔍 匹配字段 {key}: record_value={record_value} (type={type(record_value).__name__}), filter_value={value} (type={type(value).__name__})")
            
            if isinstance(record_value, str) and isinstance(value, str):
                if record_value.lower() != value.lower():
                    logger.debug(f"❌ 字符串不匹配: '{record_value.lower()}' != '{value.lower()}'")
                    return False
            else:
                if record_value != value:
                    logger.debug(f"❌ 值不匹配: {record_value} != {value}")
                    return False
        
        logger.debug(f"✅ 记录匹配成功")
        return True
    
    def _get_id_field(self, table: str) -> str:
        """获取表的 ID 字段名"""
        id_fields = {
            "features": "feature_id",
            "job_price_snapshots": "snapshot_id",  # 数据库表名
            "price_snapshots": "snapshot_id",  # 数据键名
            "subgraphs": "subgraph_id"
        }
        return id_fields.get(table, "id")
    
    def _normalize_material(self, material: str) -> str:
        """
        标准化材质代码
        
        将 TOOLOX33/TOOLOX44 标准化为 T00L0X33/T00L0X44
        
        Args:
            material: 原始材质代码
        
        Returns:
            标准化后的材质代码
        """
        import re
        
        if not material or not isinstance(material, str):
            return material
        
        # 转换为大写
        normalized = material.upper().strip()
        
        # TOOLOX → T00L0X
        normalized = re.sub(r'TOOLOX(\d+)', r'T00L0X\1', normalized)
        
        return normalized
    
    def _format_modification_message(self, changes: list) -> str:
        """
        格式化修改消息
        
        Args:
            changes: 修改列表
        
        Returns:
            格式化后的消息
        """
        if not changes:
            return "未检测到有效的修改"
        
        if len(changes) == 1:
            change = changes[0]
            # return f"已将 {change.get('id')} 的 {change.get('field')} 修改为 {change.get('value')}，请确认"
            # return f"已应用 {len(changes)} 处修改 ，请确认"
            return f"已应用修改 ，请确认"
        else:
            # lines = [f"已应用 {len(changes)} 处修改，请确认："]
            lines = [f"已应用修改，请确认"]
            # for i, change in enumerate(changes[:5], 1):  # 只显示前5个
            #     lines.append(
            #         f"{i}. {change.get('id')} 的 {change.get('field')} → {change.get('value')}"
            #     )
            # if len(changes) > 5:
            #     lines.append(f"... 还有 {len(changes) - 5} 处修改")
            return "\n".join(lines)

    async def _infer_target_from_history(
        self,
        parsed_changes: list,
        user_message: str,
        job_id: str,
        context: Dict[str, Any],  # 🔑 改为 context
        db_session
    ) -> list:
        """
        从历史消息推断修改目标（使用 LLM）
        
        当用户没有明确指定子图时（如"材质改为Cr12mov"），使用 LLM 从历史推断最近讨论的子图
        
        Args:
            parsed_changes: 解析后的修改列表
            user_message: 用户的原始消息
            job_id: 任务ID
            context: 完整的上下文（包含 raw_data 和 display_view）
            db_session: 数据库会话
        
        Returns:
            优化后的修改列表
        """
        import os
        import httpx
        import json
        
        # 检查是否启用历史记忆
        use_chat_history = os.getenv("USE_CHAT_HISTORY", "true").lower() == "true"
        if not use_chat_history:
            return parsed_changes
        
        # 🆕 统计修改了多少个不同的零件
        unique_ids = set(change.get("id") for change in parsed_changes if change.get("id"))
        
        if len(unique_ids) <= 1:
            # 只修改了 1 个零件（或没有 ID），不需要推断
            logger.info(f"✅ 只修改了 1 个零件，不需要推断")
            return parsed_changes
        
        # 检查是否包含"全部"、"所有"等关键词
        if any(keyword in user_message for keyword in ["全部", "所有", "全体", "整体"]):
            logger.info(f"✅ 用户明确要求修改全部，不需要推断")
            return parsed_changes
        
        # 🆕 检查是否包含"类"、"类型"、"分类"等关键词（表示用户明确指定了范围）
        if any(keyword in user_message for keyword in ["类", "类型", "分类", "种类", "类别"]):
            logger.info(f"✅ 用户明确指定了类别/类型，不需要推断")
            return parsed_changes
        
        # 🆕 检查是否包含"开头"、"结尾"等范围关键词
        if any(keyword in user_message for keyword in ["开头", "结尾", "开始", "结束"]):
            logger.info(f"✅ 用户明确指定了范围（开头/结尾），不需要推断")
            return parsed_changes
        
        # 🆕 检查用户输入是否包含零件编码模式（如 UB-01, DIE-03, B1-01, UB开头）
        import re
        # 修复：支持 1 个或多个大写字母 + 连字符/数字
        if re.search(r'[A-Z]+[-\d]', user_message) or re.search(r'[A-Z]{2,}开头', user_message):
            logger.info(f"✅ 用户输入包含零件标识符，不需要推断")
            return parsed_changes
        
        # 🆕 检查是否为批量修改（包含"都"或"全部"）
        if '都' in user_message or '全部' in user_message or '所有' in user_message:
            logger.info(f"✅ 用户输入包含批量修改关键词（都/全部/所有），不需要推断")
            return parsed_changes
        
        # 尝试使用 LLM 从历史推断子图
        try:
            logger.info(f"🔍 检测到修改了 {len(parsed_changes)} 条记录，使用 LLM 从历史推断目标子图...")
            
            # 查询历史消息
            history = await self.chat_history_repo.get_session_history(
                db_session,
                session_id=job_id,
                limit=10  # 最近10条消息
            )
            
            logger.info(f"� 检查询到 {len(history)} 条历史消息")
            logger.info(f"📊 查询到 {len(history)} 条历史消息")
            if not history:
                logger.warning(f"📭 没有历史消息，保持原修改")
                return parsed_changes
            
            # 构建历史上下文
            history_context = []
            for msg in history[-5:]:  # 只使用最近5条
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role in ["user", "assistant"]:
                    history_context.append(f"{role}: {content}")
            
            # 🔍 打印历史上下文（调试用）
            logger.info(f"📚 历史上下文（最近5条）:")
            for i, ctx in enumerate(history_context):
                logger.info(f"  [{i}] {ctx[:100]}...")
            
            # 调用 LLM 推断子图 ID
            inferred_subgraph = await self._infer_subgraph_with_llm(
                user_message,
                history_context
            )
            
            if not inferred_subgraph:
                logger.warning(f"⚠️  LLM 未能推断出子图ID，保持原修改")
                return parsed_changes
            
            logger.info(f"✅ LLM 推断出目标子图: {inferred_subgraph}")
            
            # 过滤修改：只保留推断出的子图
            filtered_changes = []
            # 🔑 从 context 获取 display_view（而不是 raw_data）
            display_view = context.get("display_view", [])
            
            logger.info(f"🔍 开始过滤修改，目标子图: {inferred_subgraph}")
            logger.info(f"📊 display_view 共有 {len(display_view)} 条记录")
            
            # 🔍 调试：打印 display_view 的结构
            if display_view:
                sample = display_view[0]
                logger.info(f"📋 display_view 示例结构: keys={list(sample.keys())}")
                if "_source" in sample:
                    logger.info(f"📋 _source 结构: {sample['_source']}")
            
            for change in parsed_changes:
                record_id = change.get("id")
                table = change.get("table")
                
                # 🔑 根据表类型选择匹配字段
                if table == "subgraphs":
                    # subgraphs 表：通过 subgraph_id 匹配
                    target_record = None
                    for record in display_view:
                        source = record.get("_source", {})
                        if source.get("subgraph_id") == record_id:
                            target_record = record
                            break
                    
                    # 检查是否匹配推断的子图
                    if target_record:
                        part_code = target_record.get("part_code", "")
                        logger.info(f"🔍 检查记录: subgraph_id={record_id}, part_code={part_code}")
                        
                        if part_code == inferred_subgraph or part_code.endswith(f"_{inferred_subgraph}"):
                            filtered_changes.append(change)
                            logger.info(f"✅ 保留修改: {part_code} (匹配推断的子图)")
                        else:
                            logger.info(f"⏭️  跳过修改: {part_code} (不匹配推断的子图 {inferred_subgraph})")
                    else:
                        logger.warning(f"⚠️  未找到记录: subgraph_id={record_id}")
                        # 🔍 调试：打印所有 subgraph_id
                        all_subgraph_ids = [r.get("_source", {}).get("subgraph_id") for r in display_view]
                        logger.warning(f"📋 display_view 中的所有 subgraph_id: {all_subgraph_ids[:10]}...")
                
                elif table in ["job_price_snapshots", "price_snapshots"]:
                    # 价格快照表：通过 filter 条件匹配
                    # 🔑 价格修改通常使用 filter 而不是 id
                    filter_conditions = change.get("filter")
                    if filter_conditions:
                        # 价格修改：检查是否有任何记录匹配这个 filter
                        # 由于价格是全局的，不需要按子图过滤
                        filtered_changes.append(change)
                        logger.info(f"✅ 保留价格修改: filter={filter_conditions}")
                    else:
                        logger.warning(f"⚠️  价格修改缺少 filter 条件: {change}")
                
                else:
                    # 其他表：保持原样
                    filtered_changes.append(change)
                    logger.info(f"✅ 保留修改: table={table}, id={record_id}")
            
            if filtered_changes:
                logger.info(f"✅ 根据 LLM 推断，将修改范围从 {len(parsed_changes)} 条缩小到 {len(filtered_changes)} 条")
                return filtered_changes
            else:
                # 🔑 检查是否所有修改都是价格修改
                all_price_changes = all(
                    change.get("table") in ["job_price_snapshots", "price_snapshots"]
                    for change in parsed_changes
                )
                
                if all_price_changes:
                    # 价格修改不需要按子图过滤
                    logger.info(f"✅ 所有修改都是价格修改，保持原修改")
                    return parsed_changes
                else:
                    # 如果推断出了子图但没有匹配的记录，说明推断可能有误
                    # 为了安全起见，返回空列表，避免误修改所有记录
                    logger.warning(f"⚠️  推断的子图 {inferred_subgraph} 在当前数据中不存在")
                    logger.warning(f"⚠️  为避免误操作，不执行修改。请用户明确指定子图ID")
                    return []  # 🔑 返回空列表，而不是原修改
        
        except Exception as e:
            logger.error(f"❌ LLM 推断失败: {e}，保持原修改", exc_info=True)
            return parsed_changes
    
    async def _infer_subgraph_with_llm(
        self,
        user_message: str,
        history_context: list
    ) -> str:
        """
        使用 LLM 从历史上下文推断子图 ID
        
        Args:
            user_message: 用户当前消息
            history_context: 历史消息列表
        
        Returns:
            推断出的子图 ID，如果无法推断返回 None
        """
        import os
        import httpx
        import json
        
        llm_base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
        llm_api_key = os.getenv("OPENAI_API_KEY", "sk-xxx")
        llm_model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
        
        # 构建 Prompt
        history_text = "\n".join(history_context)
        
        prompt = f"""你是一个智能助手，需要从对话历史中推断用户当前想要操作的子图ID。

对话历史（按时间顺序，最新的在最后）：
{history_text}

用户当前消息：
{user_message}

任务：
1. 分析对话历史，找出**最近一次**明确讨论的子图ID（格式如：UP01, LP-02, PH2-04, DIE-03 等）
2. 如果用户当前消息没有明确指定子图，推断用户想要继续操作刚才讨论的那个子图
3. **重要**：优先选择最后一条消息中提到的子图ID
4. 只返回子图ID，不要其他解释

注意：
- 子图ID通常是2-4个大写字母 + 连字符/下划线（可选）+ 2位数字
- 例如：UP01, LP-02, PH2-04, DIE-03
- 不要把材料名称（如CR12, P20, 718, NAK80, Cr12mov, 45#）当作子图ID
- 如果历史中有多个子图ID，选择**最后出现**的那个
- 如果无法推断，返回 "NONE"

请只返回子图ID或"NONE"："""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{llm_base_url}/chat/completions",
                    json={
                        "model": llm_model,
                        "messages": [
                            {"role": "system", "content": "你是一个精确的子图ID识别助手。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 50
                    },
                    headers={
                        "Authorization": f"Bearer {llm_api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                llm_response = result["choices"][0]["message"]["content"].strip()
                logger.info(f"🤖 LLM 推断结果: {llm_response}")
                
                # 解析 LLM 响应
                if llm_response.upper() == "NONE" or not llm_response:
                    return None
                
                # 清理响应（去除可能的引号、空格等）
                subgraph_id = llm_response.strip().strip('"').strip("'").upper()
                
                # 验证格式（基本检查）
                if len(subgraph_id) >= 4 and len(subgraph_id) <= 8:
                    return subgraph_id
                else:
                    logger.warning(f"⚠️  LLM 返回的子图ID格式异常: {subgraph_id}")
                    return None
        
        except Exception as e:
            logger.error(f"❌ LLM 推断子图ID失败: {e}")
            return None
