"""
IntentRecognizer - 意图识别器
负责人：人员B2

职责：
1. 识别用户的意图类型
2. 提取意图相关的参数
3. 支持 LLM 识别和规则识别（Fallback）
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

from .intent_types import IntentResult, IntentType, INTENT_KEYWORDS

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """
    意图识别器
    
    支持两种识别模式：
    1. LLM 识别（主要方式）：智能、准确
    2. 规则识别（Fallback）：快速、有限
    """
    
    def __init__(self, use_llm: bool = True, use_chat_history: bool = True):
        """
        初始化意图识别器
        
        Args:
            use_llm: 是否使用 LLM（默认 True）
            use_chat_history: 是否使用聊天历史（默认 True）
        """
        self.use_llm = use_llm
        self.use_chat_history = use_chat_history
        
        # LLM 配置
        self.llm_base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
        self.llm_api_key = os.getenv("OPENAI_API_KEY", "sk-xxx")
        self.llm_model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "30"))
        
        # 聊天历史配置
        self.max_history_messages = int(os.getenv("MAX_HISTORY_MESSAGES", "5"))
        
        # HTTP 客户端（设置 User-Agent 以绕过 403 错误）
        self.http_client = httpx.AsyncClient(
            timeout=self.llm_timeout,
            headers={
                "User-Agent": "curl/8.0"
            }
        )
        
        # 懒加载 ChatHistoryRepository
        self._chat_history_repo = None
        
        logger.info(f"✅ IntentRecognizer 初始化完成 (use_llm={use_llm}, use_chat_history={use_chat_history}, timeout={self.llm_timeout}s)")
    
    @property
    def chat_history_repo(self):
        """懒加载 ChatHistoryRepository"""
        if self._chat_history_repo is None:
            from api_gateway.repositories.chat_history_repository import ChatHistoryRepository
            self._chat_history_repo = ChatHistoryRepository()
        return self._chat_history_repo
    
    async def recognize(
        self,
        message: str,
        context: Dict[str, Any],
        job_id: str = None,
        db_session = None
    ) -> IntentResult:
        """
        识别用户意图
        
        Args:
            message: 用户输入的自然语言
            context: 当前审核数据上下文
            job_id: 任务ID（可选，用于加载聊天历史）
            db_session: 数据库会话（可选，用于加载聊天历史）
        
        Returns:
            IntentResult: 意图识别结果
        """
        logger.info(f"🔍 开始识别意图: {message}")
        
        try:
            # 🆕 1. 加载聊天历史
            chat_history = []
            if self.use_chat_history and job_id and db_session:
                chat_history = await self._load_chat_history(job_id, db_session)
            
            # 2. 优先使用 LLM 识别
            if self.use_llm:
                try:
                    result = await self._recognize_with_llm(message, context, chat_history)
                    if result and result.confidence >= 0.5:
                        # 🆕 根据上下文调整置信度
                        result = self._adjust_confidence_by_context(result, chat_history)
                        
                        logger.info(f"✅ LLM 识别成功: {result.intent_type} (confidence={result.confidence})")
                        logger.info(f"📋 识别参数: {result.parameters}")
                        return result
                    else:
                        logger.warning("⚠️  LLM 识别置信度过低，降级到规则识别")
                except Exception as e:
                    logger.error(f"❌ LLM 识别失败: {e}，降级到规则识别")
            
            # 3. Fallback: 规则识别
            result = self._recognize_with_rules(message, context)
            logger.info(f"✅ 规则识别完成: {result.intent_type}")
            return result
        
        except Exception as e:
            logger.error(f"❌ 意图识别失败: {e}", exc_info=True)
            # 返回未知意图
            return IntentResult(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                raw_message=message
            )
    
    async def _recognize_with_llm(
        self,
        message: str,
        context: Dict[str, Any],
        chat_history: List[Dict[str, str]] = None
    ) -> Optional[IntentResult]:
        """
        使用 LLM 识别意图
        
        Args:
            message: 用户输入
            context: 数据上下文
            chat_history: 聊天历史（可选）
        
        Returns:
            IntentResult 或 None
        """
        logger.info("🤖 使用 LLM 识别意图...")
        
        # 构建 Prompt
        prompt = self._build_llm_prompt(message, context, chat_history)
        
        # 调用 LLM API
        try:
            response = await self.http_client.post(
                f"{self.llm_base_url}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个意图识别助手。你的任务是识别用户在模具审核系统中的意图，并提取相关参数。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,  # 低温度，更确定性
                    "max_tokens": 500
                },
                headers={
                    "Authorization": f"Bearer {self.llm_api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取 LLM 响应
            content = result["choices"][0]["message"]["content"]
            logger.debug(f"LLM 响应: {content}")
            
            # 解析 JSON 响应
            intent_data = self._extract_json_from_response(content)
            
            if intent_data:
                return IntentResult(
                    intent_type=intent_data.get("intent_type", IntentType.UNKNOWN),
                    confidence=intent_data.get("confidence", 0.0),
                    parameters=intent_data.get("parameters", {}),
                    raw_message=message,
                    reasoning=intent_data.get("reasoning")
                )
            else:
                logger.warning("⚠️  LLM 未返回有效的意图识别结果")
                return None
        
        except httpx.HTTPError as e:
            logger.error(f"❌ LLM API 请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ LLM 识别异常: {e}")
            raise
    
    def _build_llm_prompt(self, message: str, context: Dict[str, Any], chat_history: List[Dict[str, str]] = None) -> str:
        """
        构建 LLM Prompt
        
        Args:
            message: 用户输入
            context: 数据上下文
            chat_history: 聊天历史（可选）
        
        Returns:
            完整的 Prompt
        """
        # 提取子图信息
        subgraphs_info = self._extract_subgraphs_info(context)
        
        # 🆕 构建历史消息部分
        history_section = ""
        if chat_history:
            history_section = "\n## 历史对话（最近 {} 条）\n".format(len(chat_history))
            for msg in chat_history:
                role_name = "用户" if msg["role"] == "user" else "助手"
                content = msg["content"][:100]  # 限制长度
                history_section += f"{role_name}: {content}\n"
            history_section += "\n"
        
        prompt = f"""请识别以下用户消息的意图，并提取相关参数。

🔴 **重要提示**: 如果用户的当前消息中明确包含子图ID（如 UB-07, U2-04, PS-01），必须精确提取该ID，不要使用历史消息中的其他ID！

## 用户消息
{message}
{history_section}
## 当前数据上下文
{subgraphs_info}

## 意图类型

1. **DATA_MODIFICATION**: 修改数据（执行操作）
   - 用户目的：修改某个字段的值
   - 关键词：
     * 修改类：修改、改、更改、设置、调整、变更
     * 赋值类：改为、设置为、改成、换成、变成
   - 示例：
     * "将 UP01 的材质改为 718"
     * "修改材质为 S136"
     * "UP01 的宽度设置为 200"
     * "把长度改成 150"
   - ⚠️ 重要：
     * 必须包含明确的修改动作词（改、修改、设置等）
     * 必须包含字段名和新值
     * 如果只是询问字段值，应识别为 QUERY_DETAILS

2. **FEATURE_RECOGNITION**: 重新识别特征（执行操作）
   - 用户目的：要求系统重新执行特征识别
   - 关键词：识别、特征识别、重新识别、识别特征、跑特征
   - 示例：
     * "重新识别特征"
     * "重新识别 UP01"
     * "识别特征"
   - ⚠️ 重要：必须包含"识别"或"特征"关键词

3. **PRICE_CALCULATION**: 重新计算价格（执行操作）
   - 用户目的：要求系统重新执行价格计算
   - 关键词：重新计算、重算、算一下、更新价格、计价
   - 示例：
     * "重新计算价格"
     * "重新计算 UP01 的价格"
     * "帮我算一下价格"
   - ⚠️ 重要：
     * 只有用户**明确要求执行计算**时才识别为此意图
     * 必须包含"重新"、"重算"等明确的操作词
     * 如果用户只是询问"怎么算"或"对吗"，应识别为 QUERY_DETAILS

4. **QUERY_DETAILS**: 查询计算详情或验证结果（不执行操作）
   - 用户目的：了解计算过程、验证结果正确性
   - 关键词：
     * 查询类：怎么算、为什么、详情、明细、计算过程、成本构成
     * 验证类：对吗、正确吗、是否正确、这样对吗、有问题吗、是不是
   - 示例：
     * "UP01 的价格怎么算的？"
     * "为什么这么贵？"
     * "费用为 90 元，这样对吗？"
     * "大水磨长条加工耗时 1.5 小时，按 60元/小时计算，费用为 90.00 元 这样对吗？"
   - 🆕 支持查询具体类型：
     * 重量: "UP01 的重量是多少"
     * 材料费: "UP01 的材料费怎么算的"
     * 热处理费: "UP01 的热处理费是多少"
     * 线割费: "UP01 的线割费用"
     * 特殊工艺费: "UP01 的特殊工艺费"
     * 自找料: "UP01 是自找料吗"
     * 牙孔费用: "UP01 的牙孔费用怎么算"
     * 线割标准费: "UP01 的线割标准基本费"
     * NC费用: "UP01 的NC开粗费用"、"UP01 的NC精铣费用"、"UP01 的NC钻床费用"
     * 总价: "UP01 的总价是多少"
     * 🆕 线割总价: "UP01 的线割总价是多少"
   - ⚠️ 重要：
     * 如果用户在**询问或验证**计算结果，识别为此意图
     * 如果用户给出了具体计算过程并询问"对吗"，识别为此意图

5. **GENERAL_CHAT**: 普通聊天
   - 关键词：你好、谢谢、帮助
   - 示例：你好、这个系统怎么用？

## 参数提取规则
- **DATA_MODIFICATION**: 提取 table, id, field, value
  * table: 表名（subgraphs, features, job_price_snapshots, processing_cost_calculation_details）
  * id: 记录ID（如 UP01, LP-02, B2-03）
  * field: 字段名（如 material, width, length）
  * value: 新值（如 718, 200, 150）
  
- **FEATURE_RECOGNITION**: 提取 subgraph_ids（如果未指定，则为所有子图）
  * 如果用户说"重新识别特征"（未指定子图），返回空数组 []
  * 如果用户说"重新识别 UP01"，返回 ["UP01"]
  
- **PRICE_CALCULATION**: 提取 subgraph_ids（如果未指定，则为所有子图）
  * 如果用户说"重新计算价格"（未指定子图），返回空数组 []
  * 如果用户说"重新计算 UP01 的价格"，返回 ["UP01"]
  
- **QUERY_DETAILS**: 提取 subgraph_id 和 query_type（可选）
  * query_type 可选值: weight, material, heat, wire_base, wire_special, wire_speci, add_auto_material, standard, tooth_hole_time, wire_standard, nc_base, nc_roughing, nc_milling, nc_drilling, total, wire_total
  * 如果用户问"重量"，则 query_type = "weight"
  * 如果用户问"材料费"，则 query_type = "material"
  * 如果用户问"热处理"，则 query_type = "heat"
  * 如果用户问"线割基础"或"线割费用"，则 query_type = "wire_base"
  * 如果用户问"线割特殊"或"特殊工艺"，则 query_type = "wire_special"
  * 如果用户问"牙孔"，则 query_type = "tooth_hole_time"
  * 如果用户问"线割标准"，则 query_type = "wire_standard"
  * 如果用户问"NC开粗"，则 query_type = "nc_roughing"
  * 如果用户问"NC精铣"，则 query_type = "nc_milling"
  * 如果用户问"NC钻床"或"钻床"，则 query_type = "nc_drilling"
  * 如果用户问"总价"或"总费用"，则 query_type = "total"
  * 🆕 如果用户问"线割总价"或"线割总费用"，则 query_type = "wire_total"
  * 如果用户问整体价格或验证计算，则 query_type = null（返回所有）
  
- **GENERAL_CHAT**: 无需提取参数

## 输出格式
请以 JSON 格式返回：
```json
{{
  "intent_type": "QUERY_DETAILS",
  "confidence": 0.95,
  "parameters": {{
    "subgraph_id": "UP01",
    "query_type": "material"
  }},
  "reasoning": "用户询问材料费的计算方式"
}}
```

## 意图识别优先级规则（重要！）

1. **验证性问题优先识别为 QUERY_DETAILS**
   - 如果用户使用"对吗"、"正确吗"、"是否正确"、"有问题吗"等词，**必须**识别为 QUERY_DETAILS
   - 即使包含"计算"关键词，也应识别为 QUERY_DETAILS
   - 示例："费用为 90 元，这样对吗？" → QUERY_DETAILS（不是 PRICE_CALCULATION）

2. **修改动作优先识别为 DATA_MODIFICATION**
   - 如果用户使用"改为"、"修改为"、"设置为"等词，优先识别为 DATA_MODIFICATION
   - 必须同时包含字段名和新值
   - 示例："将材质改为 718" → DATA_MODIFICATION

3. **明确的操作指令优先识别为对应意图**
   - "重新计算" → PRICE_CALCULATION
   - "重新识别" → FEATURE_RECOGNITION
   - "修改" → DATA_MODIFICATION

4. **模糊情况下的判断**
   - 如果用户只提到"计算"但没有"重新"、"重算"，优先考虑 QUERY_DETAILS
   - 如果用户给出了具体数值并询问，识别为 QUERY_DETAILS
   - 如果用户只是询问字段值，识别为 QUERY_DETAILS

## 上下文推断规则（如果有历史对话）

1. **精确匹配优先**（最高优先级）：
   - 如果当前消息中明确包含子图ID，**必须**使用当前消息中的ID，完全忽略历史推断
   - 示例：历史中查询"UP01"，当前说"B2-03 怎么算"，则 subgraph_id = "B2-03"（不是 UP01）

2. **代词推断**（需要时才使用）：
   - **仅当**用户使用"它"、"那个"、"这个"等代词，且当前消息中**没有明确的子图ID**时，才从历史中推断
   - **推断优先级**（重要！）：
     * 第一优先：从**最近的用户消息**中查找子图ID（最近1-2条用户消息）
     * 第二优先：从**最近的助手消息**中查找子图ID
     * 第三优先：从所有历史消息中查找
   - 示例：
     * 用户问"U2-04的计算过程是什么？"
     * 助手回答"U2-04 的总成本是..."
     * 用户问"它的重量是多少？"
     * → subgraph_id = "U2-04"（从最近的用户消息推断，不是从助手消息）

3. **延续性推断**：
   - 如果用户继续询问相关问题，保持相同的 subgraph_id
   - 示例：历史中查询"UP01 的价格"，当前说"那材料费呢"，则 subgraph_id = "UP01"

4. **意图延续**：
   - 如果历史中是查询意图，当前也是疑问句，优先识别为 QUERY_DETAILS
   - 如果历史中是修改意图，当前也是修改动作，优先识别为 DATA_MODIFICATION

## 参数提取规则

1. **confidence**: 置信度 (0-1)，表示识别的确定性
2. **subgraph_ids**: 如果用户说"重新识别特征"（未指定子图），则返回空数组 []，表示所有子图
3. **subgraph_ids**: 如果用户说"重新识别 UP01"，则返回 ["UP01"]
4. **query_type**: 如果用户询问具体的费用类型，提取对应的 query_type
5. **subgraph_id 提取规则**（🔴 最重要！必须严格遵守）：
   - **🔴 第一优先（绝对优先）**: 如果用户的**当前消息**中**明确包含子图ID**（如 UB-07, U2-04, PS-01, UP01, B2-03），则**必须精确提取该ID**，**完全忽略历史消息**
   - **⚠️ 重要排除规则**：
     * **单个字母不是子图ID**：如果用户说"L的线长"、"W的费用"、"M的时间"，这里的 L/W/M 是**加工代码**，不是子图ID
     * 子图ID必须是：**前缀 + 数字** 或 **前缀 + 字母+数字** 的组合
     * 正确格式：UP-01, DIE-03, PS-02, PU-BL2, UP-A1（有前缀+数字）
     * 错误格式：L, W, M, K（单个字母，这是加工代码）
     * 如果用户只提到单个字母，应该从历史推断子图ID
   - **示例（当前消息优先）**:
     * 用户说"UB-07的价格" → subgraph_id = "UB-07"（不是历史中的其他ID）
     * 用户说"U2-04是怎么算的？" → subgraph_id = "U2-04"（不是 U2-01）
     * 用户说"PS-01的价格" → subgraph_id = "PS-01"
     * 用户说"B2-03大水磨长条费用...这样对吗？" → subgraph_id = "B2-03"
     * 用户说"L的线长是多少？" → subgraph_id = None（L是加工代码，从历史推断）
   - **代词规则（仅当没有明确ID时）**: 如果用户使用代词（如"它"、"那个"、"这个"）或**单个字母**（如"L"、"W"、"M"），且当前消息中**没有明确的子图ID**，则从历史消息中推断：
     * **第一优先**：从最近的**用户消息**中查找（最近1-2条）
     * **第二优先**：从最近的**助手消息**中查找
     * **第三优先**：从所有历史消息中查找
   - **示例（代词推断）**:
     * 历史：用户问"U2-04的计算过程"，助手回答"U2-04的总成本..."，用户说"它的重量是多少？" → subgraph_id = "U2-04"（从最近的用户消息推断）
     * 历史：用户问"UB-07的价格"，用户说"它的重量是多少？" → subgraph_id = "UB-07"（从最近的用户消息推断）
     * 历史：用户问"DIE-05怎么算的？"，用户说"L的线长是多少？" → subgraph_id = "DIE-05"（L是加工代码，从历史推断子图）
   - 子图ID通常格式：UP01, LP-02, DIE-03, PS-01, U2-01, U2-04, B2-03, DIE2-07, UB-07, PU-BL2 等
   - **🔴 关键规则**: 当前消息中的ID **永远优先于** 历史消息中的ID，但**单个字母不是子图ID**
6. **只返回 JSON**: 不要有其他解释文字

请开始识别："""
        
        return prompt
    
    def _extract_subgraphs_info(self, context: Dict[str, Any]) -> str:
        """
        提取子图信息（用于 Prompt）
        
        Args:
            context: 数据上下文
        
        Returns:
            子图信息的文本描述
        """
        subgraphs = context.get("subgraphs", [])
        
        if not subgraphs:
            return "（当前无子图数据）"
        
        lines = [f"共 {len(subgraphs)} 个子图："]
        for sg in subgraphs[:10]:  # 只显示前10个
            sg_id = sg.get('subgraph_id', 'N/A')
            part_name = sg.get('part_name', 'N/A')
            lines.append(f"  - {sg_id}: {part_name}")
        
        if len(subgraphs) > 10:
            lines.append(f"  ... 还有 {len(subgraphs) - 10} 个子图")
        
        return "\n".join(lines)
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 响应中提取 JSON
        
        Args:
            content: LLM 响应内容
        
        Returns:
            解析后的 JSON 字典
        """
        try:
            # 尝试直接解析
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取 JSON 代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 尝试提取对象
            obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if obj_match:
                try:
                    return json.loads(obj_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"⚠️  无法从 LLM 响应中提取 JSON: {content[:200]}")
            return None
    
    def _recognize_with_rules(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> IntentResult:
        """
        使用规则识别意图（Fallback）
        
        Args:
            message: 用户输入
            context: 数据上下文
        
        Returns:
            IntentResult
        """
        logger.info("📋 使用规则识别意图...")
        
        message_lower = message.lower()
        
        # 🆕 0. 优先检查验证性关键词（最高优先级）
        verification_keywords = ["对吗", "正确吗", "是否正确", "有问题吗", "是不是", "对不对"]
        if any(keyword in message for keyword in verification_keywords):
            subgraph_id = self._extract_single_subgraph_id(message, context)
            return IntentResult(
                intent_type=IntentType.QUERY_DETAILS,
                confidence=0.9,
                parameters={"subgraph_id": subgraph_id} if subgraph_id else {},
                raw_message=message
            )
        
        # 1. 检查查询详情关键词（提升优先级）
        if any(keyword in message for keyword in INTENT_KEYWORDS[IntentType.QUERY_DETAILS]):
            subgraph_id = self._extract_single_subgraph_id(message, context)
            return IntentResult(
                intent_type=IntentType.QUERY_DETAILS,
                confidence=0.8,
                parameters={"subgraph_id": subgraph_id} if subgraph_id else {},
                raw_message=message
            )
        
        # 2. 检查特征识别关键词
        if any(keyword in message for keyword in INTENT_KEYWORDS[IntentType.FEATURE_RECOGNITION]):
            subgraph_ids = self._extract_subgraph_ids_from_text(message, context)
            return IntentResult(
                intent_type=IntentType.FEATURE_RECOGNITION,
                confidence=0.8,
                parameters={"subgraph_ids": subgraph_ids},
                raw_message=message
            )
        
        # 3. 检查价格计算关键词
        if any(keyword in message for keyword in INTENT_KEYWORDS[IntentType.PRICE_CALCULATION]):
            subgraph_ids = self._extract_subgraph_ids_from_text(message, context)
            return IntentResult(
                intent_type=IntentType.PRICE_CALCULATION,
                confidence=0.8,
                parameters={"subgraph_ids": subgraph_ids},
                raw_message=message
            )
        
        # 4. 检查数据修改关键词
        if any(keyword in message for keyword in INTENT_KEYWORDS[IntentType.DATA_MODIFICATION]):
            return IntentResult(
                intent_type=IntentType.DATA_MODIFICATION,
                confidence=0.7,
                parameters={},
                raw_message=message
            )
        
        # 5. 默认：普通聊天
        return IntentResult(
            intent_type=IntentType.GENERAL_CHAT,
            confidence=0.6,
            parameters={},
            raw_message=message
        )
    
    def _extract_subgraph_ids_from_text(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        从文本中提取 subgraph_ids
        
        Args:
            text: 用户输入
            context: 数据上下文
        
        Returns:
            subgraph_ids 列表（空列表表示所有子图）
        """
        subgraphs = context.get("subgraphs", [])
        all_subgraph_ids = [sg.get("subgraph_id") for sg in subgraphs if sg.get("subgraph_id")]
        
        # 查找文本中提到的 subgraph_id
        mentioned_ids = []
        for sg_id in all_subgraph_ids:
            if sg_id in text:
                mentioned_ids.append(sg_id)
        
        # 如果没有提到具体的 subgraph_id，返回空列表（表示所有）
        return mentioned_ids if mentioned_ids else []
    
    def _extract_single_subgraph_id(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        从文本中提取单个 subgraph_id
        
        Args:
            text: 用户输入
            context: 数据上下文
        
        Returns:
            subgraph_id 或 None
        """
        subgraphs = context.get("subgraphs", [])
        all_subgraph_ids = [sg.get("subgraph_id") for sg in subgraphs if sg.get("subgraph_id")]
        
        # 查找文本中提到的第一个 subgraph_id
        for sg_id in all_subgraph_ids:
            if sg_id in text:
                return sg_id
        
        return None
    
    async def _load_chat_history(
        self,
        job_id: str,
        db_session
    ) -> List[Dict[str, str]]:
        """
        加载聊天历史
        
        Args:
            job_id: 任务ID
            db_session: 数据库会话
        
        Returns:
            历史消息列表 [{"role": "user", "content": "..."}, ...]
        """
        try:
            messages = await self.chat_history_repo.get_recent_session_history(
                db_session,
                session_id=job_id,
                limit=self.max_history_messages
            )
            
            # 转换为 LLM 格式
            history = []
            for msg in messages:
                history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            if history:
                logger.info(f"✅ 加载了 {len(history)} 条历史消息")
            return history
        
        except Exception as e:
            logger.warning(f"⚠️  加载历史消息失败: {e}")
            return []
    
    def _adjust_confidence_by_context(
        self,
        intent_result: IntentResult,
        chat_history: List[Dict[str, str]]
    ) -> IntentResult:
        """
        根据上下文调整置信度
        
        规则：
        1. 如果包含验证性关键词（"对吗"等），强制识别为 QUERY_DETAILS
        2. 如果历史中有相同意图，提升置信度 +0.1
        3. 如果历史中有相关子图ID，提升置信度 +0.05
        
        Args:
            intent_result: 原始识别结果
            chat_history: 聊天历史
        
        Returns:
            调整后的识别结果
        """
        if not chat_history:
            return intent_result
        
        # 规则 1：验证性问题强制识别为 QUERY_DETAILS
        verification_keywords = ["对吗", "正确吗", "是否正确", "有问题吗", "是不是", "对不对"]
        if any(keyword in intent_result.raw_message for keyword in verification_keywords):
            if intent_result.intent_type != IntentType.QUERY_DETAILS:
                logger.info(f"🔄 检测到验证性问题，强制调整为 QUERY_DETAILS（原意图: {intent_result.intent_type}）")
                intent_result.intent_type = IntentType.QUERY_DETAILS
                intent_result.confidence = max(intent_result.confidence, 0.9)
                # 如果原来识别为 PRICE_CALCULATION，清空 subgraph_ids，改为 subgraph_id
                if "subgraph_ids" in intent_result.parameters:
                    subgraph_ids = intent_result.parameters.pop("subgraph_ids", [])
                    if subgraph_ids:
                        intent_result.parameters["subgraph_id"] = subgraph_ids[0]
        
        # 规则 2：相同意图提升置信度
        recent_messages = [msg for msg in chat_history[-3:] if msg.get("role") == "user"]
        if recent_messages:
            # 简单判断：如果历史消息中有疑问句，当前也是疑问句，提升 QUERY_DETAILS 置信度
            if intent_result.intent_type == IntentType.QUERY_DETAILS:
                has_question_in_history = any("?" in msg.get("content", "") or "吗" in msg.get("content", "") for msg in recent_messages)
                if has_question_in_history:
                    intent_result.confidence = min(intent_result.confidence + 0.1, 1.0)
                    logger.info(f"✅ 历史中有疑问句，QUERY_DETAILS 置信度提升至 {intent_result.confidence}")
        
        # 规则 3：相关子图ID提升置信度
        subgraph_id = intent_result.parameters.get("subgraph_id")
        if subgraph_id:
            for msg in chat_history[-3:]:
                if subgraph_id in msg.get("content", ""):
                    intent_result.confidence = min(intent_result.confidence + 0.05, 1.0)
                    logger.info(f"✅ 历史中提到相同子图 {subgraph_id}，置信度提升至 {intent_result.confidence}")
                    break
        
        return intent_result
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()
        logger.info("✅ IntentRecognizer 已关闭")
