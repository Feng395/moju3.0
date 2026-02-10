"""
NLP Parser - 自然语言解析器
负责人：人员B2

职责：
1. 解析用户的自然语言修改指令
2. 识别修改的表、记录ID、字段和值
3. 支持规则解析（快速）和 LLM 解析（智能）
4. 返回结构化的修改指令

架构：
- 规则解析：基于正则表达式，快速但有限
- LLM 解析：使用本地 Qwen，智能但较慢
- Fallback 机制：LLM 失败时降级到规则解析
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class NLPParser:
    """
    自然语言解析器
    
    支持两种解析模式：
    1. 规则解析（rule-based）：快速，适合简单指令
    2. LLM 解析（llm-based）：智能，适合复杂指令
    """
    
    def __init__(self, use_llm: bool = True):
        """
        初始化 NLP Parser
        
        Args:
            use_llm: 是否使用 LLM（默认 True）
        """
        self.use_llm = use_llm
        
        # LLM 配置
        self.llm_base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
        self.llm_api_key = os.getenv("OPENAI_API_KEY", "sk-xxx")
        self.llm_model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "30"))
        
        # HTTP 客户端（设置 User-Agent 以绕过 403 错误）
        self.http_client = httpx.AsyncClient(
            timeout=self.llm_timeout,
            headers={
                "User-Agent": "curl/8.0"
            }
        )
        
        logger.info(f"✅ NLPParser 初始化完成 (use_llm={use_llm}, timeout={self.llm_timeout}s)")
        if use_llm:
            logger.info(f"🤖 LLM: {self.llm_model} @ {self.llm_base_url}")
    
    async def parse(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        解析自然语言指令
        
        Args:
            text: 用户输入的自然语言
            context: 当前数据上下文（可能包含 raw_data 和 display_view）
        
        Returns:
            解析后的修改列表，格式：
            [
                {
                    "table": "subgraphs",
                    "id": "UP01",
                    "field": "material",
                    "value": "718",
                    "original_text": "将 UP01 的材质改为 718"
                }
            ]
        """
        logger.info(f"🔍 开始解析: {text}")
        
        try:
            # 🆕 检查是否有 display_view
            if "display_view" in context and context.get("display_view"):
                logger.info("🔧 使用展示视图解析")
                return await self._parse_with_display_view(text, context)
            else:
                logger.info("🔧 使用原始数据解析")
                return await self._parse_with_raw_data(text, context)
        
        except Exception as e:
            logger.error(f"❌ 解析失败: {e}", exc_info=True)
            return []
    
    async def _parse_with_raw_data(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        使用原始数据解析（原有逻辑）
        
        Args:
            text: 用户输入
            context: 原始数据上下文
        
        Returns:
            修改列表
        """
        # 获取 raw_data（向后兼容）
        raw_data = context.get("raw_data") or context
        
        try:
            # 优先使用 LLM 解析
            if self.use_llm:
                try:
                    # 🆕 将 user_input 添加到 context
                    context_with_input = {**raw_data, "user_input": text}
                    changes = await self._parse_with_llm(text, context_with_input)
                    if changes:
                        logger.info(f"✅ LLM 解析成功: {len(changes)} 个修改")
                        return changes
                    else:
                        logger.warning("⚠️  LLM 解析返回空结果，降级到规则解析")
                except Exception as e:
                    logger.error(f"❌ LLM 解析失败: {e}，降级到规则解析")
            
            # Fallback: 规则解析
            changes = self._parse_with_rules(text, context)
            logger.info(f"✅ 规则解析完成: {len(changes)} 个修改")
            return changes
        
        except Exception as e:
            logger.error(f"❌ 解析失败: {e}", exc_info=True)
            return []
    
    async def _parse_with_llm(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        使用 LLM 解析自然语言
        
        Args:
            text: 用户输入
            context: 数据上下文
        
        Returns:
            解析后的修改列表
        """
        logger.info("🤖 使用 LLM 解析...")
        
        # 构建 Prompt
        prompt = self._build_prompt(text, context)
        
        # 调用 LLM API
        try:
            response = await self.http_client.post(
                f"{self.llm_base_url}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个数据修改指令解析助手。你的任务是将用户的自然语言指令解析为结构化的数据修改操作。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,  # 低温度，更确定性
                    "max_tokens": 2000  # 增加 token 限制，确保响应完整
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
            logger.debug(f"🤖 LLM 完整响应: {content}")
            
            # 解析 JSON 响应
            changes = self._extract_json_from_llm_response(content)
            
            # 验证结果
            if changes:
                # 🆕 将用户输入添加到 context，用于自动修复
                context_with_input = {**context, "user_input": text}
                validated_changes = self._validate_changes(changes, context_with_input)
                return validated_changes
            else:
                logger.warning("⚠️  LLM 未返回有效的修改指令")
                return []
        
        except httpx.TimeoutException as e:
            logger.error(f"❌ LLM API 请求超时: {e}", exc_info=True)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ LLM API 返回错误状态: {e.response.status_code} - {e.response.text}", exc_info=True)
            raise
        except httpx.HTTPError as e:
            logger.error(f"❌ LLM API 请求失败: {type(e).__name__} - {str(e)}", exc_info=True)
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ LLM 响应 JSON 解析失败: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"❌ LLM 解析异常: {type(e).__name__} - {str(e)}", exc_info=True)
            raise
    
    def _build_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """
        构建 LLM Prompt
        
        Args:
            text: 用户输入
            context: 数据上下文
        
        Returns:
            完整的 Prompt
        """
        # 提取数据结构信息
        tables_info = self._extract_tables_info(context)
        
        prompt = f"""请解析以下用户指令，并返回结构化的修改操作。

## 用户指令
{text}

## 当前数据结构
{tables_info}

## 输出格式
请以 JSON 数组格式返回，每个修改操作包含以下字段：
- table: 表名（features/price_snapshots/subgraphs）⚠️ 注意：不要使用 process_snapshots 表
- id: 记录ID（可以是 part_code、part_name 或实际的 ID，系统会自动映射）
- field: 要修改的字段名（必须是数据库中实际存在的字段）
- value: 新的值
- original_text: 原始指令文本

⚠️ 重要：
1. 必须返回有效的 JSON 格式
2. 字符串值中不要包含未转义的换行符、制表符等控制字符
3. 如果需要包含特殊字符，请使用 JSON 转义（如 \\n, \\t）
4. 确保 JSON 完整，不要截断

## 示例

### 示例1：修改材质（⚠️ 注意：material 字段在 features 表）
用户指令: "将 UP01 的材质改为 718"
输出:
```json
[
  {{
    "table": "features",
    "id": "UP01",
    "field": "material",
    "value": "718",
    "original_text": "将 UP01 的材质改为 718"
  }}
]
```

### 示例2：通过零件名称修改材质
用户指令: "请把上模板的材料换成 718"
输出:
```json
[
  {{
    "table": "features",
    "id": "上模板",
    "field": "material",
    "value": "718",
    "original_text": "请把上模板的材料换成 718"
  }}
]
```

### 示例3：修改工艺信息
用户指令: "上夹板工艺改为快丝割一刀"
（⚠️ 注意：工艺修改应该修改 subgraphs 表的 wire_process 和 wire_process_note 字段）
输出:
```json
[
  {{
    "table": "subgraphs",
    "id": "上夹板",
    "field": "wire_process",
    "value": "fast_cut",
    "original_text": "上夹板工艺改为快丝割一刀"
  }},
  {{
    "table": "subgraphs",
    "id": "上夹板",
    "field": "wire_process_note",
    "value": "快丝割一刀",
    "original_text": "上夹板工艺改为快丝割一刀"
  }}
]
```

### 示例3.5：修改工艺为慢丝割一修三
用户指令: "上垫脚类工艺为慢丝割一修三"
（⚠️ 重要：慢丝割一修三的代码是 slow_and_three，不是 slow_cut_and_three！）
输出:
```json
[
  {{
    "table": "subgraphs",
    "id": "上垫脚类",
    "field": "wire_process",
    "value": "slow_and_three",
    "original_text": "上垫脚类工艺为慢丝割一修三"
  }},
  {{
    "table": "subgraphs",
    "id": "上垫脚类",
    "field": "wire_process_note",
    "value": "慢丝割一修三",
    "original_text": "上垫脚类工艺为慢丝割一修三"
  }}
]
```

### 示例4：批量修改特征
用户指令: "LP-02长度改为80，PH2-04宽度改为90"
输出:
```json
[
  {{
    "table": "features",
    "id": "LP-02",
    "field": "length_mm",
    "value": "80",
    "original_text": "LP-02长度改为80"
  }},
  {{
    "table": "features",
    "id": "PH2-04",
    "field": "width_mm",
    "value": "90",
    "original_text": "PH2-04宽度改为90"
  }}
]
```

### 示例5：全部修改（⚠️ 重要：使用特殊标识 "ALL"）
用户指令: "全部材质修改为45#"
输出:
```json
[
  {{
    "table": "features",
    "id": "ALL",
    "field": "material",
    "value": "45#",
    "original_text": "全部材质修改为45#"
  }}
]
```

### 示例6：全部工艺修改（⚠️ 特殊：工艺修改需要两个字段）
用户指令: "全部工艺改为快丝割一刀"
输出:
```json
[
  {{
    "table": "subgraphs",
    "id": "ALL",
    "field": "wire_process",
    "value": "fast_cut",
    "original_text": "全部工艺改为快丝割一刀"
  }},
  {{
    "table": "subgraphs",
    "id": "ALL",
    "field": "wire_process_note",
    "value": "快丝割一刀",
    "original_text": "全部工艺改为快丝割一刀"
  }}
]
```

### 示例7：批量修改价格（⚠️ 新增：基于过滤条件的批量修改）
用户指令: "将这套的线割割一修一的单价改成0.0018"
输出:
```json
[
  {{
    "table": "job_price_snapshots",
    "filter": {{
      "category": "wire",
      "sub_category": "slow_and_one"
    }},
    "field": "price",
    "value": "0.0018",
    "original_text": "将这套的线割割一修一的单价改成0.0018"
  }}
]
```

### 示例8：批量修改价格（通过工艺名称）
用户指令: "慢丝割一修一的价格改为0.002"
输出:
```json
[
  {{
    "table": "job_price_snapshots",
    "filter": {{
      "category": "wire",
      "sub_category": "slow_and_one",
      "note": "慢丝割一修一"
    }},
    "field": "price",
    "value": "0.002",
    "original_text": "慢丝割一修一的价格改为0.002"
  }}
]
```

### 示例9：批量修改材质价格（⚠️ 新增：材质价格修改）
用户指令: "45#价格改成6块"
输出:
```json
[
  {{
    "table": "job_price_snapshots",
    "filter": {{
      "category": "material",
      "sub_category": "45#"
    }},
    "field": "price",
    "value": "6",
    "original_text": "45#价格改成6块"
  }}
]
```

### 示例10：批量修改材质价格（完整表达）
用户指令: "将CR12的价格改为11.8"
输出:
```json
[
  {{
    "table": "job_price_snapshots",
    "filter": {{
      "category": "material",
      "sub_category": "CR12"
    }},
    "field": "price",
    "value": "11.8",
    "original_text": "将CR12的价格改为11.8"
  }}
]
```

## 重要规则
1. **ID 可以灵活使用**: 可以使用 part_code（如 LP-02）、part_name（如"上夹板"）、实际的 ID（如 UP01），或特殊标识 "ALL"（表示全部记录），系统会自动映射
2. **字段名映射**:
   - 材质/材料 → material (⚠️ features 表)
   - 长度 → length_mm (features 表)
   - 宽度 → width_mm (features 表)
   - 厚度 → thickness_mm (features 表)
   - 数量 → quantity (features 表)
   - 工艺代码 → wire_process (subgraphs 表)
   - 工艺说明 → wire_process_note (subgraphs 表)
   - 价格/单价 → price (job_price_snapshots 表)
3. **表名判断（重要！）**:
   - 修改材质、尺寸（长宽厚）、数量 → features 表
   - 修改工艺、加工方式 → subgraphs 表 (wire_process, wire_process_note)
   - 修改价格、成本 → job_price_snapshots 表
   - 修改零件名称、零件编码 → subgraphs 表
4. **支持批量修改**: 如果用户一次修改多个字段或多个记录，返回多个修改操作
5. **全部修改**: 如果用户说"全部"、"所有"等，使用 id="ALL"，系统会自动展开为所有记录
6. **🆕 过滤条件修改**: 如果用户说"将这套的线割割一修一的单价改成X"或"45#价格改成X"，使用 filter 字段：
   - **线割工艺**（⚠️ 重要：必须使用以下精确的代码，不要自己创造）:
     * "线割割一修三" → filter: {{"category": "wire", "sub_category": "slow_and_three"}}
     * "线割割一修二" → filter: {{"category": "wire", "sub_category": "slow_and_two"}}
     * "线割割一修一" → filter: {{"category": "wire", "sub_category": "slow_and_one"}}
     * "线割割一刀" → filter: {{"category": "wire", "sub_category": "slow_cut"}}
     * "慢丝割一修三" → sub_category="slow_and_three" (不是 slow_cut_and_three!)
     * "慢丝割一修二" → sub_category="slow_and_two"
     * "慢丝割一修一" → sub_category="slow_and_one"
     * "慢丝割一刀" → sub_category="slow_cut"
     * "中丝割一修一" → sub_category="middle_and_one"
     * "快丝割一刀" → sub_category="fast_cut"
   - **材质**:
     * "45#" → filter: {{"category": "material", "sub_category": "45#"}}
     * "CR12" → filter: {{"category": "material", "sub_category": "CR12"}}
     * "SKD11" → filter: {{"category": "material", "sub_category": "SKD11"}}
     * "CR12MOV" → filter: {{"category": "material", "sub_category": "CR12MOV"}}
     * "SKH-51" → filter: {{"category": "material", "sub_category": "SKH-51"}}
     * "SKH-9" → filter: {{"category": "material", "sub_category": "SKH-9"}}
     * "T00L0X33" 或 "TOOLOX33" → filter: {{"category": "material", "sub_category": "T00L0X33"}}
     * "T00L0X44" 或 "TOOLOX44" → filter: {{"category": "material", "sub_category": "T00L0X44"}}
     * "P20" → filter: {{"category": "material", "sub_category": "P20"}}
     * "DC53" → filter: {{"category": "material", "sub_category": "DC53"}}
7. **只返回 JSON**: 不要有其他解释文字
8. **如果无法解析**: 返回空数组 []
9. **⚠️ 重要**: 不要使用 process_snapshots 表，工艺信息存储在 subgraphs 表中

请开始解析："""
        
        return prompt
    
    def _extract_tables_info(self, context: Dict[str, Any]) -> str:
        """
        提取数据表信息（用于 Prompt）
        
        Args:
            context: 数据上下文
        
        Returns:
            表信息的文本描述
        """
        info_lines = []
        
        # Features 表
        if context.get("features"):
            features = context["features"]
            info_lines.append(f"### features 表 ({len(features)} 条记录)")
            if features:
                sample = features[0]
                fields = list(sample.keys())
                info_lines.append(f"字段: {', '.join(fields[:10])}")  # 只显示前10个字段
                info_lines.append(f"示例 ID: {sample.get('feature_id', 'N/A')}")
        
        # Subgraphs 表（重点）
        if context.get("subgraphs"):
            subgraphs = context["subgraphs"]
            info_lines.append(f"\n### subgraphs 表 ({len(subgraphs)} 条记录)")
            if subgraphs:
                sample = subgraphs[0]
                fields = list(sample.keys())
                info_lines.append(f"字段: {', '.join(fields[:10])}")
                
                # 列出所有记录的 ID 和名称映射（重要！）
                info_lines.append("\n**ID 和名称映射**:")
                for s in subgraphs:
                    sg_id = s.get('subgraph_id', 'N/A')
                    part_name = s.get('part_name', 'N/A')
                    info_lines.append(f"  - {sg_id}: {part_name}")
        
        # Price Snapshots 表
        if context.get("job_price_snapshots"):
            snapshots = context["job_price_snapshots"]
            info_lines.append(f"\n### job_price_snapshots 表 ({len(snapshots)} 条记录)")
            if snapshots:
                sample = snapshots[0]
                fields = list(sample.keys())
                info_lines.append(f"字段: {', '.join(fields[:10])}")
        
        # ⚠️ 不再显示 process_snapshots 表（已移除）
        
        return "\n".join(info_lines) if info_lines else "（当前无数据）"
    
    def _extract_json_from_llm_response(self, content: str) -> List[Dict[str, Any]]:
        """
        从 LLM 响应中提取 JSON
        
        Args:
            content: LLM 响应内容
        
        Returns:
            解析后的 JSON 列表
        """
        # 🆕 预处理：移除或转义无效的控制字符
        def clean_json_string(s: str) -> str:
            """清理 JSON 字符串中的无效控制字符"""
            # 移除常见的控制字符（保留 \n, \r, \t）
            import string
            # 允许的控制字符：换行、回车、制表符
            allowed_controls = {'\n', '\r', '\t'}
            cleaned = ''.join(
                char if char not in string.whitespace or char in allowed_controls or ord(char) >= 32
                else ' '
                for char in s
            )
            return cleaned
        
        # 清理输入
        content = clean_json_string(content)
        
        try:
            # 尝试直接解析
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  JSON 代码块解析失败: {e}")
                logger.debug(f"📋 提取的 JSON 字符串: {json_str[:500]}")
        
        # 尝试提取数组（更宽松的匹配）
        array_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
        if array_match:
            try:
                json_str = array_match.group(0)
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  数组解析失败: {e}")
                logger.debug(f"📋 提取的数组字符串: {json_str[:500]}")
        
        # 🆕 尝试修复常见的 JSON 错误
        # 1. 移除 ```json 标记
        cleaned = re.sub(r'```json\s*', '', content)
        cleaned = re.sub(r'\s*```', '', cleaned)
        
        # 2. 尝试找到第一个 [ 和最后一个 ]
        start_idx = cleaned.find('[')
        end_idx = cleaned.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                json_str = cleaned[start_idx:end_idx+1]
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  修复后的 JSON 解析失败: {e}")
                logger.debug(f"📋 修复后的 JSON: {json_str[:500]}")
                
                # 🆕 尝试使用 strict=False（允许控制字符）
                try:
                    return json.loads(json_str, strict=False)
                except json.JSONDecodeError as e2:
                    logger.warning(f"⚠️  宽松模式解析也失败: {e2}")
        
        logger.warning(f"⚠️  无法从 LLM 响应中提取 JSON")
        logger.debug(f"📋 完整响应内容: {content}")
        return []
    
    def _validate_changes(
        self,
        changes: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        验证修改指令的有效性
        
        Args:
            changes: 待验证的修改列表
            context: 数据上下文
        
        Returns:
            验证后的修改列表
        """
        validated = []
        
        for change in changes:
            # 检查必需字段
            if not all(k in change for k in ["table", "field", "value"]):
                logger.warning(f"⚠️  修改指令缺少必需字段: {change}")
                continue
            
            # 🆕 智能修复：如果缺少 id 和 filter，尝试从 original_text 提取
            if "id" not in change and "filter" not in change:
                logger.warning(f"⚠️  修改指令缺少 id 或 filter，尝试自动修复: {change}")
                
                # 尝试从 original_text 提取材质或工艺信息
                original_text = change.get("original_text", "")
                
                # 🆕 如果 change 中没有 original_text，尝试从 context 获取
                if not original_text and "user_input" in context:
                    original_text = context.get("user_input", "")
                    logger.info(f"📝 使用 context 中的 user_input: {original_text}")
                
                if original_text:
                    from shared.process_code_mapping import extract_process_from_text
                    
                    process_code = extract_process_from_text(original_text)
                    if process_code:
                        # 找到了材质或工艺代码，添加 filter
                        change["filter"] = {
                            "category": process_code.get("category"),
                            "sub_category": process_code.get("sub_category")
                        }
                        # 同时添加 original_text
                        if "original_text" not in change:
                            change["original_text"] = original_text
                        logger.info(f"✅ 自动添加 filter: {change['filter']}")
                    else:
                        logger.warning(f"⚠️  无法自动修复，跳过此修改")
                        continue
                else:
                    logger.warning(f"⚠️  无 original_text，无法自动修复，跳过此修改")
                    continue
            
            # 🆕 智能字段映射：自动修正错误的表名
            change = self._auto_correct_table_mapping(change)
            
            # 检查表名
            if change["table"] not in ["features", "job_price_snapshots", "subgraphs"]:
                logger.warning(f"⚠️  无效的表名: {change['table']}, 只支持 features/job_price_snapshots/subgraphs")
                continue
            
            # 🆕 处理工艺代码映射（针对 filter 中的中文工艺名称）
            if "filter" in change:
                change = self._resolve_process_filter(change)
            
            # 🆕 处理 "ALL" 标识：展开为所有记录
            if change.get("id") == "ALL":
                expanded_changes = self._expand_all_modification(change, context)
                validated.extend(expanded_changes)
                continue
            
            # 🆕 ID 映射：如果 ID 看起来像 part_code，尝试映射到实际的 ID
            # 🔑 支持多个匹配：如果有多个相同的零件编号，展开为多个修改
            if "id" in change:
                matched_ids = self._map_identifier_to_ids(
                    change["id"],
                    change["table"],
                    context
                )
                
                if len(matched_ids) == 0:
                    # 没有找到匹配，使用原始标识符
                    logger.warning(f"⚠️  未找到 {change['id']} 的映射，使用原始值")
                    validated.append(change)
                elif len(matched_ids) == 1:
                    # 只有一个匹配，直接使用
                    change["id"] = matched_ids[0]
                    validated.append(change)
                else:
                    # 多个匹配，展开为多个修改
                    logger.info(f"✅ 找到 {len(matched_ids)} 个匹配的 {change['id']}，展开为多个修改")
                    for matched_id in matched_ids:
                        expanded_change = change.copy()
                        expanded_change["id"] = matched_id
                        validated.append(expanded_change)
                
                continue  # 已处理，跳过后续逻辑
            
            # 添加原始文本（如果缺失）
            if "original_text" not in change:
                if "id" in change:
                    change["original_text"] = f"修改 {change['table']}.{change['id']}.{change['field']} = {change['value']}"
                else:
                    change["original_text"] = f"批量修改 {change['table']}.{change['field']} = {change['value']}"
            
            validated.append(change)
        
        return validated
    
    def _expand_all_modification(
        self,
        change: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        展开 "ALL" 修改为所有记录
        
        Args:
            change: 包含 id="ALL" 的修改指令
            context: 数据上下文
        
        Returns:
            展开后的修改列表
        """
        table = change["table"]
        field = change["field"]
        value = change["value"]
        original_text = change.get("original_text", "")
        
        expanded = []
        raw_data = context.get("raw_data") or context
        
        if table == "features":
            # 修改所有 features 记录
            features = raw_data.get("features", [])
            for feature in features:
                feature_id = feature.get("feature_id")
                if feature_id:
                    expanded.append({
                        "table": "features",
                        "id": feature_id,
                        "field": field,
                        "value": value,
                        "original_text": original_text
                    })
            logger.info(f"✅ 展开 ALL 修改: features 表 {len(expanded)} 条记录")
        
        elif table == "subgraphs":
            # 修改所有 subgraphs 记录
            subgraphs = raw_data.get("subgraphs", [])
            for subgraph in subgraphs:
                subgraph_id = subgraph.get("subgraph_id")
                if subgraph_id:
                    expanded.append({
                        "table": "subgraphs",
                        "id": subgraph_id,
                        "field": field,
                        "value": value,
                        "original_text": original_text
                    })
            logger.info(f"✅ 展开 ALL 修改: subgraphs 表 {len(expanded)} 条记录")
        
        elif table == "job_price_snapshots":
            # 修改所有 job_price_snapshots 记录
            price_snapshots = raw_data.get("job_price_snapshots", [])
            for snapshot in price_snapshots:
                snapshot_id = snapshot.get("snapshot_id")
                if snapshot_id:
                    expanded.append({
                        "table": "job_price_snapshots",
                        "id": snapshot_id,
                        "field": field,
                        "value": value,
                        "original_text": original_text
                    })
            logger.info(f"✅ 展开 ALL 修改: job_price_snapshots 表 {len(expanded)} 条记录")
        
        return expanded
    
    def _resolve_process_filter(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析过滤条件中的工艺代码
        
        Args:
            change: 修改指令
        
        Returns:
            解析后的修改指令
        """
        from shared.process_code_mapping import extract_process_from_text
        
        filter_conditions = change.get("filter", {})
        
        # 如果 filter 中有 process_name 字段，尝试解析
        if "process_name" in filter_conditions:
            process_name = filter_conditions.pop("process_name")
            process_code = extract_process_from_text(process_name)
            
            if process_code:
                # 合并工艺代码到 filter
                filter_conditions.update(process_code)
                logger.info(f"✅ 工艺代码解析: {process_name} → {process_code}")
            else:
                logger.warning(f"⚠️  无法解析工艺代码: {process_name}")
        
        # 检查 original_text 中是否包含工艺名称
        original_text = change.get("original_text", "")
        if original_text and not filter_conditions:
            process_code = extract_process_from_text(original_text)
            if process_code:
                filter_conditions.update(process_code)
                logger.info(f"✅ 从原始文本解析工艺代码: {original_text} → {process_code}")
        
        change["filter"] = filter_conditions
        return change
    
    def _auto_correct_table_mapping(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动修正字段到表的映射
        
        Args:
            change: 修改指令
        
        Returns:
            修正后的修改指令
        """
        field = change.get("field")
        table = change.get("table")
        
        # 定义字段到表的正确映射
        field_to_table = {
            # Features 表字段
            "material": "features",
            "length_mm": "features",
            "width_mm": "features",
            "thickness_mm": "features",
            "quantity": "features",
            "heat_treatment": "features",
            "calculated_weight_kg": "features",
            
            # Subgraphs 表字段
            "wire_process": "subgraphs",
            "wire_process_note": "subgraphs",
            "part_name": "subgraphs",
            "part_code": "subgraphs",
            "weight_kg": "subgraphs",
            "total_cost": "subgraphs",
            
            # Price Snapshots 表字段
            "price": "job_price_snapshots",
            "unit_price": "job_price_snapshots"
        }
        
        correct_table = field_to_table.get(field)
        
        if correct_table and correct_table != table:
            logger.warning(f"⚠️  字段 {field} 应该在 {correct_table} 表，而不是 {table} 表，已自动修正")
            change["table"] = correct_table
        
        return change
    
    def _map_identifier_to_id(
        self,
        identifier: str,
        table: str,
        context: Dict[str, Any]
    ) -> str:
        """
        将标识符映射到实际的 ID（单个）
        
        ⚠️ 注意：如果有多个匹配，只返回第一个
        如果需要返回所有匹配，请使用 _map_identifier_to_ids
        
        Args:
            identifier: 标识符（可能是 part_code、subgraph_id 或其他）
            table: 表名
            context: 数据上下文
        
        Returns:
            实际的 ID
        """
        ids = self._map_identifier_to_ids(identifier, table, context)
        if ids:
            if len(ids) > 1:
                logger.warning(f"⚠️  找到 {len(ids)} 个匹配的 {identifier}，只返回第一个")
            return ids[0]
        
        # 如果没有找到映射，返回原始标识符
        logger.warning(f"⚠️  未找到 {identifier} 的映射，使用原始值")
        return identifier
    
    def _map_identifier_to_ids(
        self,
        identifier: str,
        table: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        将标识符映射到实际的 ID 列表（支持多个匹配）
        
        Args:
            identifier: 标识符（可能是 part_code、subgraph_id 或其他）
            table: 表名
            context: 数据上下文
        
        Returns:
            实际的 ID 列表
        """
        # 如果标识符包含下划线且看起来像 job_id_part_code 格式，提取 part_code
        if "_" in identifier and len(identifier) > 36:  # UUID 长度是 36
            # 可能是 "job_id_part_code" 格式，提取最后一部分
            parts = identifier.split("_")
            if len(parts) >= 2:
                potential_part_code = "_".join(parts[-1:])  # 取最后一部分
                logger.info(f"🔍 检测到复合 ID，提取 part_code: {potential_part_code}")
                identifier = potential_part_code
        
        # 获取原始数据
        raw_data = context.get("raw_data") or context
        matched_ids = []
        
        # 根据表名进行映射
        if table == "features":
            # 尝试通过 subgraph_id 或 part_code 查找 feature_id
            features = raw_data.get("features", [])
            subgraphs = raw_data.get("subgraphs", [])
            
            # 先尝试直接匹配 feature_id
            for feature in features:
                if feature.get("feature_id") == identifier:
                    matched_ids.append(identifier)
            
            if matched_ids:
                return matched_ids
            
            # 尝试通过 part_code 查找（可能有多个）
            for subgraph in subgraphs:
                if subgraph.get("part_code") == identifier or subgraph.get("part_name") == identifier:
                    subgraph_id = subgraph.get("subgraph_id")
                    # 查找对应的 feature
                    for feature in features:
                        if feature.get("subgraph_id") == subgraph_id:
                            feature_id = feature.get("feature_id")
                            if feature_id not in matched_ids:
                                matched_ids.append(feature_id)
                                logger.info(f"✅ 映射 {identifier} → {feature_id}")
            
            if matched_ids:
                return matched_ids
            
            # 尝试通过 subgraph_id 查找
            for feature in features:
                if feature.get("subgraph_id") == identifier:
                    feature_id = feature.get("feature_id")
                    if feature_id not in matched_ids:
                        matched_ids.append(feature_id)
                        logger.info(f"✅ 通过 subgraph_id 找到 feature: {feature_id}")
        
        elif table == "subgraphs":
            # 尝试通过 part_code 查找 subgraph_id（可能有多个）
            subgraphs = raw_data.get("subgraphs", [])
            
            # 先尝试直接匹配 subgraph_id
            for subgraph in subgraphs:
                if subgraph.get("subgraph_id") == identifier:
                    matched_ids.append(identifier)
            
            if matched_ids:
                return matched_ids
            
            # 尝试通过 part_code 查找（可能有多个）
            for subgraph in subgraphs:
                if subgraph.get("part_code") == identifier or subgraph.get("part_name") == identifier:
                    subgraph_id = subgraph.get("subgraph_id")
                    if subgraph_id not in matched_ids:
                        matched_ids.append(subgraph_id)
                        logger.info(f"✅ 映射 {identifier} → {subgraph_id}")
        
        # ⚠️ 不再支持 process_snapshots 表
        
        elif table == "job_price_snapshots":
            # 尝试通过 part_code 或其他标识符查找 snapshot_id
            price_snapshots = raw_data.get("job_price_snapshots", [])
            
            # 先尝试直接匹配 snapshot_id
            for price in price_snapshots:
                if price.get("snapshot_id") == identifier:
                    matched_ids.append(identifier)
            
            # 可以根据需要添加更多映射逻辑
        
        return matched_ids
    
    def _parse_with_rules(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        使用规则解析自然语言（Fallback）
        
        支持的模式：
        1. "将 X 的 Y 改为 Z"
        2. "修改 X 的 Y 为 Z"
        3. "把 X 的 Y 设置为 Z"
        4. "X 的 Y 改成 Z"
        
        Args:
            text: 用户输入
            context: 数据上下文
        
        Returns:
            解析后的修改列表
        """
        logger.info("📋 使用规则解析...")
        
        changes = []
        
        # 模式1: "将 X 的 Y 改为 Z"
        pattern1 = r'将\s*([^\s的]+)\s*的\s*([^\s改]+)\s*改为\s*(.+)'
        matches = re.finditer(pattern1, text)
        for match in matches:
            record_id = match.group(1).strip()
            field = match.group(2).strip()
            value = match.group(3).strip()
            
            # 推断表名
            table = self._infer_table(record_id, field, context)
            
            changes.append({
                "table": table,
                "id": record_id,
                "field": self._normalize_field_name(field),
                "value": value,
                "original_text": match.group(0)
            })
        
        # 模式2: "修改 X 的 Y 为 Z"
        pattern2 = r'修改\s*([^\s的]+)\s*的\s*([^\s为]+)\s*为\s*(.+)'
        matches = re.finditer(pattern2, text)
        for match in matches:
            record_id = match.group(1).strip()
            field = match.group(2).strip()
            value = match.group(3).strip()
            
            table = self._infer_table(record_id, field, context)
            
            changes.append({
                "table": table,
                "id": record_id,
                "field": self._normalize_field_name(field),
                "value": value,
                "original_text": match.group(0)
            })
        
        # 模式3: "把 X 的 Y 设置为 Z"
        pattern3 = r'把\s*([^\s的]+)\s*的\s*([^\s设]+)\s*设置为\s*(.+)'
        matches = re.finditer(pattern3, text)
        for match in matches:
            record_id = match.group(1).strip()
            field = match.group(2).strip()
            value = match.group(3).strip()
            
            table = self._infer_table(record_id, field, context)
            
            changes.append({
                "table": table,
                "id": record_id,
                "field": self._normalize_field_name(field),
                "value": value,
                "original_text": match.group(0)
            })
        
        # 模式4: "X 的 Y 改成 Z"
        pattern4 = r'([^\s的]+)\s*的\s*([^\s改]+)\s*改成\s*(.+)'
        matches = re.finditer(pattern4, text)
        for match in matches:
            record_id = match.group(1).strip()
            field = match.group(2).strip()
            value = match.group(3).strip()
            
            table = self._infer_table(record_id, field, context)
            
            changes.append({
                "table": table,
                "id": record_id,
                "field": self._normalize_field_name(field),
                "value": value,
                "original_text": match.group(0)
            })
        
        return changes
    
    def _infer_table(
        self,
        record_id: str,
        field: str,
        context: Dict[str, Any]
    ) -> str:
        """
        推断记录所属的表
        
        Args:
            record_id: 记录ID
            field: 字段名
            context: 数据上下文
        
        Returns:
            表名
        """
        # 检查 subgraphs（最常见）
        if context.get("subgraphs"):
            for subgraph in context["subgraphs"]:
                if subgraph.get("subgraph_id") == record_id:
                    return "subgraphs"
        
        # 检查 features
        if context.get("features"):
            for feature in context["features"]:
                if str(feature.get("feature_id")) == record_id:
                    return "features"
        
        # 检查 job_price_snapshots
        if context.get("job_price_snapshots"):
            for snapshot in context["job_price_snapshots"]:
                if str(snapshot.get("snapshot_id")) == record_id:
                    return "job_price_snapshots"
        
        # ⚠️ 不再检查 process_snapshots（已移除）
        
        # 默认返回 subgraphs（最常用）
        logger.warning(f"⚠️  无法推断 {record_id} 的表，默认使用 subgraphs")
        return "subgraphs"
    
    def _normalize_field_name(self, field: str) -> str:
        """
        标准化字段名（中文 -> 英文）
        
        Args:
            field: 中文字段名
        
        Returns:
            英文字段名
        """
        field_mapping = {
            # Subgraphs 常用字段
            "材质": "material",
            "材料": "material",
            "重量": "weight_kg",
            "总成本": "total_cost",
            "成本": "total_cost",
            "工艺说明": "process_description",
            "说明": "process_description",
            
            # Features 常用字段
            "长度": "length_mm",
            "宽度": "width_mm",
            "厚度": "thickness_mm",
            "数量": "quantity",
            "热处理": "heat_treatment",
            
            # Price Snapshots 常用字段
            "价格": "price",
            "单价": "unit_price",
            "单位": "unit",
            
            # Process Snapshots 常用字段
            "名称": "name",
            "描述": "description",
            "优先级": "priority"
        }
        
        return field_mapping.get(field, field)
    
    async def _parse_with_display_view(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        使用展示视图解析（支持 part_code）
        
        Args:
            text: 用户输入
            context: 包含 raw_data 和 display_view 的上下文
        
        Returns:
            存储层修改列表
        """
        from agents.data_view_builder import DataViewBuilder
        
        logger.info("🔧 使用展示视图解析...")
        
        # 🆕 检测是否为工艺修改（包含"工艺"关键词）
        is_process_modification = any(keyword in text for keyword in ['工艺', 'process', '快丝', '慢丝', '割'])
        
        if is_process_modification:
            logger.info("🔍 检测到工艺修改，使用特殊处理...")
            return await self._parse_process_modification(text, context)
        
        # 🆕 检测是否为批量修改（包含逗号、顿号或"和"）
        is_batch = any(sep in text for sep in ['，', ',', '、', '和'])
        
        if is_batch:
            # 批量修改：直接使用 LLM 解析
            logger.info("🔍 检测到批量修改，使用 LLM 解析...")
            raw_data = context.get("raw_data") or context
            
            if self.use_llm:
                try:
                    # 🆕 将 user_input 添加到 context
                    context_with_input = {**raw_data, "user_input": text}
                    changes = await self._parse_with_llm(text, context_with_input)
                    if changes:
                        logger.info(f"✅ LLM 解析成功: {len(changes)} 个修改")
                        return changes
                except httpx.TimeoutException as e:
                    logger.error(f"❌ LLM 解析超时（{self.llm_timeout}秒）: {str(e)}", exc_info=True)
                except Exception as e:
                    logger.error(f"❌ LLM 解析失败: {type(e).__name__} - {str(e)}", exc_info=True)
            
            # 回退到规则解析
            logger.warning("⚠️  回退到规则解析")
            return self._parse_with_rules(text, context)
        
        # 单个修改：尝试快速实体提取
        entities = await self._extract_entities_from_text(text)
        
        if entities:
            display_view = context.get("display_view", [])
            identifier = entities.get("identifier")
            
            # 先尝试 part_code
            display_item = DataViewBuilder.find_by_part_code(display_view, identifier)
            
            # 如果没找到，尝试 subgraph_id
            if not display_item:
                display_item = DataViewBuilder.find_by_subgraph_id(display_view, identifier)
            
            if display_item:
                logger.info(f"✅ 找到记录: part_code={display_item.get('part_code')}")
                
                # 构建展示层修改
                display_changes = [{
                    "part_code": display_item["part_code"],
                    "field": entities["field"],
                    "value": entities["value"]
                }]
                
                # 反向映射到存储层
                raw_data = context.get("raw_data") or context
                table_changes = DataViewBuilder.map_display_to_tables(
                    display_changes,
                    raw_data
                )
                
                logger.info(f"✅ 反向映射完成: {len(table_changes)} 个表修改")
                return table_changes
        
        # 回退到 LLM 解析
        logger.info("🤖 回退到 LLM 解析...")
        raw_data = context.get("raw_data") or context
        
        if self.use_llm:
            try:
                # 🆕 将 user_input 添加到 context
                context_with_input = {**raw_data, "user_input": text}
                changes = await self._parse_with_llm(text, context_with_input)
                if changes:
                    logger.info(f"✅ LLM 解析成功: {len(changes)} 个修改")
                    return changes
            except httpx.TimeoutException as e:
                logger.error(f"❌ LLM 解析超时（{self.llm_timeout}秒）: {str(e)}", exc_info=True)
            except Exception as e:
                logger.error(f"❌ LLM 解析失败: {type(e).__name__} - {str(e)}", exc_info=True)
        
        # 最后回退到规则解析
        logger.warning("⚠️  回退到规则解析")
        return self._parse_with_rules(text, context)
    
    async def _extract_entities_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取实体
        
        Args:
            text: 用户输入
        
        Returns:
            实体字典 {"identifier": "LP-02", "field": "length_mm", "value": "100"}
        """
        # 🆕 识别更多 part_code 模式
        # 支持: P001, P-001, LP-02, PART001, 零件01 等
        part_code_patterns = [
            r'[Ll][Pp][-_]?\d{2,}',      # LP-02, lp02, LP_02
            r'[Pp][-_]?\d{3,}',          # P001, P-001, p_001
            r'PART[-_]?\d{3,}',          # PART001, PART-001
            r'零件[-_]?\d{2,}'            # 零件01, 零件-01
        ]
        
        identifier = None
        for pattern in part_code_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                identifier = match.group()
                logger.info(f"🔍 提取到标识符: {identifier}")
                break
        
        # 如果没找到 part_code，尝试 subgraph_id
        if not identifier:
            subgraph_id_pattern = r'subgraph[_-]?\d+'
            subgraph_id_match = re.search(subgraph_id_pattern, text, re.IGNORECASE)
            if subgraph_id_match:
                identifier = subgraph_id_match.group()
                logger.info(f"🔍 提取到 subgraph_id: {identifier}")
        
        if not identifier:
            logger.warning(f"⚠️  未能提取标识符: {text}")
            return None
        
        # 🆕 改进字段识别（支持更多模式）
        # ⚠️ 重要：复合词必须放在前面，避免被部分匹配
        field_patterns = {
            r'材质价格|材质单价|材料价格|材料单价|material[_\s]?price|material[_\s]?unit[_\s]?price': 'material_unit_price',  # 材质价格/单价（复合词优先）
            r'工艺价格|工艺单价|process[_\s]?price|process[_\s]?unit[_\s]?price': 'process_unit_price',    # 工艺价格/单价（复合词优先）
            r'材料|材质|material': 'material',
            r'长度|length': 'length_mm',
            r'宽度|width': 'width_mm',
            r'厚度|thickness': 'thickness_mm',
            r'数量|quantity|qty': 'quantity',
            r'工艺|process': 'process_code',
            r'重量|weight': 'weight_kg',
            r'价格|单价|price': 'price'
        }
        
        field = None
        for pattern, field_name in field_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                field = field_name
                logger.info(f"🔍 识别到字段: {field}")
                break
        
        if not field:
            logger.warning(f"⚠️  未能识别字段: {text}")
            return None
        
        # 🆕 改进值提取（支持更多模式）
        # 模式1: "改为/改成/修改为/设置为 XXX"
        value_patterns = [
            r'(?:改为|改成|修改为|设置为|变为|换成)\s*([^\s，。、]+)',
            r'(?:为|是)\s*([^\s，。、]+)',  # "长度为100"
            r'=\s*([^\s，。、]+)'            # "长度=100"
        ]
        
        value = None
        for pattern in value_patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                logger.info(f"🔍 提取到值: {value}")
                break
        
        # 如果还没找到，尝试提取数字（针对尺寸字段）
        if not value and field in ['length_mm', 'width_mm', 'thickness_mm', 'quantity', 'weight_kg']:
            number_match = re.search(r'\d+(?:\.\d+)?', text)
            if number_match:
                value = number_match.group()
                logger.info(f"🔍 提取到数字值: {value}")
        
        if not value:
            logger.warning(f"⚠️  未能提取值: {text}")
            return None
        
        logger.info(f"✅ 实体提取成功: identifier={identifier}, field={field}, value={value}")
        return {
            "identifier": identifier,
            "field": field,
            "value": value
        }
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()
        logger.info("✅ NLPParser 已关闭")
    
    async def _parse_process_modification(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        解析工艺修改（特殊处理）
        
        策略：
        - 简单场景（复杂度 < 5）：正则解析（快速，~5ms）
        - 复杂场景（复杂度 >= 5）：LLM解析（准确，~3s）
        
        支持:
        1. 查询 process_rules 表获取工艺代码
        2. 批量修改同名零件
        3. 同时更新 wire_process 和 wire_process_note
        
        Args:
            text: 用户输入（如"上夹板工艺改为快丝割一刀"）
            context: 上下文
        
        Returns:
            修改列表
        """
        from agents.data_view_builder import DataViewBuilder
        
        logger.info(f"🔧 解析工艺修改: {text}")
        
        try:
            # 🆕 Step 1: 计算句子复杂度
            complexity = self._calculate_complexity(text)
            logger.info(f"📊 句子复杂度: {complexity}")
            
            # 🆕 Step 2: 复杂场景直接使用 LLM
            if complexity >= 5:
                logger.info(f"🤖 检测到复杂句式（复杂度={complexity}），直接使用 LLM 解析")
                raw_data = context.get("raw_data") or context
                context_with_input = {**raw_data, "user_input": text}
                return await self._parse_with_llm(text, context_with_input)
            
            # Step 3: 简单场景，尝试正则解析
            logger.info(f"📋 简单句式（复杂度={complexity}），使用正则解析")
            part_names_str, process_desc = self._extract_process_modification_entities(text)
            
            if not part_names_str or not process_desc:
                logger.warning("⚠️  无法提取零件名称或工艺描述，回退到 LLM")
                raw_data = context.get("raw_data") or context
                # 🆕 将 user_input 添加到 context
                context_with_input = {**raw_data, "user_input": text}
                return await self._parse_with_llm(text, context_with_input)
            
            logger.info(f"📋 零件名称: {part_names_str}, 工艺描述: {process_desc}")
            
            # 🆕 验证零件名称是否包含工艺关键词（可能是正则匹配错误）
            if self._contains_process_keywords(part_names_str):
                logger.warning(f"⚠️  零件名称包含工艺关键词，可能是正则匹配错误: {part_names_str}，回退到 LLM")
                raw_data = context.get("raw_data") or context
                context_with_input = {**raw_data, "user_input": text}
                return await self._parse_with_llm(text, context_with_input)
            
            # 2. 查询 process_rules 表
            process_rule = await self._query_process_rules(process_desc, context)
            
            # 3. 确定要更新的值
            if process_rule:
                # 找到匹配的工艺规则
                wire_process = process_rule.get("process_code")
                wire_process_note = process_rule.get("description") or process_desc
                logger.info(f"✅ 找到工艺规则: code={wire_process}, note={wire_process_note}")
            else:
                # 未找到匹配的工艺规则
                wire_process = None
                wire_process_note = process_desc
                logger.warning(f"⚠️  未找到工艺规则，使用原始描述: {process_desc}")
            
            # 4. 查找所有匹配的零件
            display_view = context.get("display_view", [])
            
            # 🆕 处理 "ALL" 标识
            if part_names_str == "ALL":
                matched_items = display_view  # 所有零件
                logger.info(f"✅ 全部修改: {len(matched_items)} 个零件")
            # 🆕 处理类型筛选（如"下模板类"）
            elif part_names_str.endswith("类"):
                part_type = part_names_str[:-1]  # 去掉"类"字，得到"下模板"
                logger.info(f"🔍 按类型筛选: {part_type}")
                
                # 筛选包含该类型的零件
                matched_items = []
                for item in display_view:
                    part_name = item.get("part_name", "")
                    part_code = item.get("part_code", "")
                    
                    # 检查零件名称或编码是否包含类型关键词
                    if part_type in part_name or part_type in part_code:
                        matched_items.append(item)
                        logger.info(f"✅ 匹配: {part_name} ({part_code})")
                
                logger.info(f"✅ 按类型筛选到 {len(matched_items)} 个零件")
            else:
                # 🆕 处理多个零件名称（用逗号、顿号、空格或"和"字分隔）
                # 支持: "DIE-03, DIE-04" 或 "DIE-03，DIE-04" 或 "DIE-03 DIE-04" 或 "DIE-03和DIE-04"
                part_names = re.split(r'[,，、\s和]+', part_names_str)
                part_names = [name.strip() for name in part_names if name.strip()]
                
                logger.info(f"📋 解析出 {len(part_names)} 个零件: {part_names}")
                
                # 查找所有匹配的零件
                matched_items = []
                for part_name in part_names:
                    items = DataViewBuilder.find_all_by_identifier(display_view, part_name)
                    matched_items.extend(items)
                    logger.info(f"✅ {part_name}: 找到 {len(items)} 个匹配")
                
                logger.info(f"✅ 总共找到 {len(matched_items)} 个匹配的零件")
            
            if not matched_items:
                logger.warning(f"⚠️  未找到零件: {part_names_str}")
                return []
            
            # 5. 生成修改列表（批量修改）
            changes = []
            raw_data = context.get("raw_data") or context
            
            for item in matched_items:
                source = item.get("_source", {})
                subgraph_id = source.get("subgraph_id")
                
                if not subgraph_id:
                    continue
                
                # 🔑 同时修改两个字段
                # 注意：即使 wire_process 为 None，也要生成修改（清空旧值）
                changes.append({
                    "table": "subgraphs",
                    "id": subgraph_id,
                    "field": "wire_process",
                    "value": wire_process if wire_process else "",  # None 转为空字符串
                    "original_text": text
                })
                
                changes.append({
                    "table": "subgraphs",
                    "id": subgraph_id,
                    "field": "wire_process_note",
                    "value": wire_process_note,
                    "original_text": text
                })
            
            logger.info(f"✅ 生成 {len(changes)} 个修改操作")
            return changes
        
        except Exception as e:
            logger.error(f"❌ 解析工艺修改失败: {e}", exc_info=True)
            # 回退到 LLM
            raw_data = context.get("raw_data") or context
            # 🆕 将 user_input 添加到 context
            context_with_input = {**raw_data, "user_input": text}
            return await self._parse_with_llm(text, context_with_input)
    
    def _calculate_complexity(self, text: str) -> int:
        """
        计算句子复杂度
        
        复杂度指标：
        - 多个"把"字（复合句式）：+5 分（强信号）
        - 🆕 筛选条件关键词（如"开头"、"结尾"、"包含"）：+5 分（需要语义理解）
        - 多个逗号/顿号（复合句式）：+4 分（2个及以上）
        - 多个"和"字（多个零件）：+2 分（3个及以上）
        - 多个"类"字（多个类型）：+2 分（3个及以上）
        - 零件编号列举（如"DIE-04、DIE-03、PH2-04"）：+2 分（3个及以上）
        - 组合加分：同时有多个"和"字(>=3)和多个"类"字(>=4)：+1 分
        - 长度超过40字符：+1 分
        
        阈值：
        - < 5: 简单句式，使用正则
        - >= 5: 复杂句式，使用 LLM
        
        Args:
            text: 用户输入
        
        Returns:
            复杂度分数
        """
        score = 0
        
        # 检查1：多个"把"字（最强信号）
        ba_count = text.count('把')
        if ba_count > 1:
            score += 5
            logger.debug(f"🔍 检测到 {ba_count} 个'把'字，+5 分")
        
        # 🆕 检查1.5：筛选条件关键词（需要语义理解）
        # 如："UB开头"、"以UP结尾"、"包含DIE"、"不包含"等
        # ⚠️ 注意："XX类的零件"不算筛选条件，这是正常的类型修改
        filter_keywords = ['开头', '结尾', '包含', '不包含', '以']
        has_filter = any(keyword in text for keyword in filter_keywords)
        
        # 🆕 特殊检测："这些零件"、"那些零件"（但不包括"XX类的零件"）
        if not has_filter:
            # 检查是否有"这些零件"或"那些零件"
            if ('这些' in text or '那些' in text) and '零件' in text:
                has_filter = True
            # 检查是否有"XX的零件"但不是"XX类的零件"
            elif '的零件' in text and '类的零件' not in text:
                has_filter = True
        
        if has_filter:
            score += 5
            logger.debug(f"🔍 检测到筛选条件关键词，+5 分")
        
        # 检查2：多个逗号/顿号（支持中英文逗号和顿号）
        comma_count = text.count('，') + text.count(',') + text.count('、')
        if comma_count >= 2:
            score += 4
            logger.debug(f"🔍 检测到 {comma_count} 个逗号/顿号，+4 分")
        
        # 检查3：多个"和"字（3个及以上才算复杂）
        and_count = text.count('和')
        if and_count >= 3:
            score += 2
            logger.debug(f"🔍 检测到 {and_count} 个'和'字，+2 分")
        
        # 检查4：多个"类"字（3个及以上才算复杂）
        type_count = text.count('类')
        if type_count >= 3:
            score += 2
            logger.debug(f"🔍 检测到 {type_count} 个'类'字，+2 分")
        
        # 🆕 检查4.5：零件编号列举（如"DIE-04、DIE-03、PH2-04"）
        # 匹配模式：字母+数字+连字符+数字（如 DIE-04, LP-02, PH2-04）
        import re
        part_code_pattern = r'[A-Z]+[-_]?\d+'
        part_codes = re.findall(part_code_pattern, text, re.IGNORECASE)
        if len(part_codes) >= 3:
            score += 2
            logger.debug(f"🔍 检测到 {len(part_codes)} 个零件编号列举，+2 分")
        
        # 检查5：组合加分（多个"和"字 + 多个"类"字）
        # 这种组合通常表示"A类和B类和C类和D类"，是复杂句式
        if and_count >= 3 and type_count >= 4:
            score += 1
            logger.debug(f"🔍 检测到多个'和'字({and_count})和多个'类'字({type_count})的组合，+1 分")
        
        # 检查6：长度（超过40字符）
        if len(text) > 40:
            score += 1
            logger.debug(f"🔍 文本长度 {len(text)} > 40，+1 分")
        
        return score
    
    def _contains_process_keywords(self, part_name: str) -> bool:
        """
        检查零件名称是否包含工艺关键词
        
        如果包含，说明正则匹配可能有误（把工艺关键词包含在零件名称中了）
        
        Args:
            part_name: 零件名称
        
        Returns:
            是否包含工艺关键词
        """
        # 工艺关键词列表
        process_keywords = [
            '线割', '工艺', '方式',
            '慢丝', '快丝', '中丝',
            '割一', '修一', '修二', '修三',
            '热处理', '磨削', '铣削'
        ]
        
        # 检查是否以工艺关键词结尾（最常见的错误）
        for keyword in process_keywords:
            if part_name.endswith(keyword):
                logger.debug(f"🔍 零件名称以工艺关键词结尾: {part_name} (关键词: {keyword})")
                return True
        
        return False
    
    def _extract_process_modification_entities(self, text: str) -> tuple:
        """
        从文本中提取零件名称和工艺描述
        
        Args:
            text: 用户输入
        
        Returns:
            (part_names, process_desc) 元组
            - part_names: 可以是单个字符串、"ALL"、或逗号分隔的多个零件名
            - process_desc: 工艺描述
        """
        # 🆕 模式0.5: "XX类的零件全部改成 工艺描述"（批量修改特定类型）
        # ⚠️ 优先级最高！必须在模式0之前匹配
        # 匹配: "下模板类的零件全部改成中丝割一修一"
        pattern0_5 = r'(.+?类)(?:的)?零件\s*全部\s*(?:改为|改成|修改为|设置为)\s*(.+)'
        match = re.search(pattern0_5, text)
        if match:
            part_type = match.group(1).strip()  # "下模板类"
            process_desc = match.group(2).strip()
            # 返回类型标识，后续会根据类型筛选零件
            logger.info(f"🔍 匹配到类型筛选模式: {part_type}")
            return (part_type, process_desc)
        
        # 🆕 模式0: "全部工艺改为 工艺描述"（真正的全部修改）
        # ⚠️ 必须在开头匹配"全部/所有/全体"，避免误匹配
        pattern0 = r'^(?:全部|所有|全体|这套)\s*(?:的)?(?:线割工艺|工艺|线割方式)?\s*(?:改为|改成|修改为|设置为|都改成)\s*(.+)'
        match = re.search(pattern0, text)
        if match:
            process_desc = match.group(1).strip()
            logger.info(f"🔍 匹配到全部修改模式")
            return ("ALL", process_desc)
        
        # 🆕 模式0.8: "把 零件名 的工艺改成 工艺描述"（口语化句式）
        # ⚠️ 优先级高于模式1，避免"把"字被包含在零件名中
        # 匹配: "把LP-02的工艺改成慢丝割一修一" 或 "把LP-02，PH2-04的工艺改成慢丝割一修一"
         # 匹配: "把所有的工艺改为慢丝割一修一"
        pattern0_8 = r'把\s*(.+?)\s*(?:的)?(?:线割工艺|工艺|线割方式)\s*(?:改为|改成|修改为|设置为)\s*(.+)'
        match = re.search(pattern0_8, text)
        if match:
            part_names_str = match.group(1).strip()
            process_desc = match.group(2).strip()
            logger.info(f"🔍 匹配到口语化模式（把...）")
            
            # 🆕 检查是否为"全部"关键词
            if part_names_str in ['全部', '所有', '全体', '这套', '所有的', '全部的', '全体的', '这套的']:
                logger.info(f"🔍 识别到全部关键词: {part_names_str} → ALL")
                return ("ALL", process_desc)
            
            return (part_names_str, process_desc)
        
        # 🆕 模式1: "零件名1, 零件名2 工艺改为 工艺描述"（支持多个零件）
        # 匹配: DIE-03, DIE-04工艺改为中丝割一修一
        # 匹配: 上垫脚类工艺为慢丝割一修三
        # 匹配: 上插刀类线割工艺改为慢丝割一修二
        # ⚠️ 修复：使用更精确的匹配，避免在"工艺"的"工"字处截断
        pattern1 = r'(.+?)\s*(?:的)?(?:线割工艺|工艺|线割方式)\s*(?:改为|改成|修改为|设置为|为)\s*(.+)'
        match = re.search(pattern1, text)
        if match:
            part_names_str = match.group(1).strip()
            process_desc = match.group(2).strip()
            # 排除"全部"、"所有"等关键词（已在模式0处理）
            if part_names_str not in ['全部', '所有', '全体', '这套']:
                return (part_names_str, process_desc)
        
        # 模式2: "将 零件名 的工艺改为 工艺描述"
        # ⚠️ 修复：使用非捕获组 (?:将\s+) 来匹配"将"字，但不包含在捕获组中
        pattern2 = r'(?:将\s+)(.+?)\s*(?:的)?(?:线割工艺|工艺|线割方式)\s*(?:改为|改成)\s*(.+)'
        match = re.search(pattern2, text)
        if match:
            part_names_str = match.group(1).strip()
            process_desc = match.group(2).strip()
            
            # 🆕 检查是否为"全部"关键词
            if part_names_str in ['全部', '所有', '全体', '这套', '所有的', '全部的', '全体的', '这套的']:
                logger.info(f"🔍 识别到全部关键词: {part_names_str} → ALL")
                return ("ALL", process_desc)
            
            return (part_names_str, process_desc)
        
        # 模式3: "修改 零件名 工艺为 工艺描述"
        # ⚠️ 修复：使用非捕获组 (?:修改\s+) 来匹配"修改"字，但不包含在捕获组中
        pattern3 = r'(?:修改\s+)(.+?)\s*(?:的)?(?:线割工艺|工艺|线割方式)\s*为\s*(.+)'
        match = re.search(pattern3, text)
        if match:
            part_names_str = match.group(1).strip()
            process_desc = match.group(2).strip()
            
            # 🆕 检查是否为"全部"关键词
            if part_names_str in ['全部', '所有', '全体', '这套', '所有的', '全部的', '全体的', '这套的']:
                logger.info(f"🔍 识别到全部关键词: {part_names_str} → ALL")
                return ("ALL", process_desc)
            
            return (part_names_str, process_desc)
        
        return (None, None)
    
    async def _query_process_rules(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        查询 process_rules 表
        
        Args:
            description: 工艺描述
            context: 上下文（需要包含 db_session）
        
        Returns:
            工艺规则字典，如果没找到返回 None
        """
        try:
            # 从上下文获取 db_session
            db_session = context.get("db_session")
            
            if not db_session:
                logger.warning("⚠️  上下文中没有 db_session，无法查询 process_rules")
                return None
            
            # 使用 ProcessRulesRepository 查询
            from api_gateway.repositories.process_rules_repository import ProcessRulesRepository
            
            repo = ProcessRulesRepository()
            rule = await repo.find_wire_process_by_description(db_session, description)
            
            return rule
        
        except Exception as e:
            logger.error(f"❌ 查询 process_rules 失败: {e}", exc_info=True)
            return None

