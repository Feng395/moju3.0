# Agent 输入/输出 - 快速参考卡片

> 一页纸速查表，打印后可贴在工位

---

## 📥 Agent 输入格式（context 参数）

```python
context = {
    # 必填字段
    "job_id": str,                    # Job UUID
    "session_id": str,                # 会话 ID
    "agent_execution_id": str,        # 执行 ID
    
    # 上游依赖
    "upstream_outputs": {
        "AgentName": {
            "status": "ok",
            "data": {...},
            ...
        }
    },
    
    # 快照引用
    "snapshot_refs": {
        "price_version_locked": str,
        "process_version_locked": str
    },
    
    # Job 元信息
    "job_metadata": {
        "dwg_file_path": str,
        "prt_file_path": str,
        ...
    },
    
    # 业务数据（可选）
    "subgraphs": [...],
    "features": [...],
    
    # Agent 参数
    "agent_parameters": {...},
    
    # 控制指令
    "directives": {
        "timeout_at": str,
        "priority": int,
        "retry_attempt": int
    }
}
```

---

## 📤 Agent 输出格式（OpResult）

```python
return OpResult(
    # 必填字段
    status="ok",              # "ok" | "warning" | "error" | "skipped"
    data={...},               # 业务结果数据
    message="处理成功",
    
    # 标准字段
    agent_name=self.name,
    agent_version="1.0.0",
    execution_id=context["agent_execution_id"],
    started_at=started_at,
    completed_at=datetime.utcnow(),
    
    # 质量指标
    confidence_score=0.95,    # 0.0-1.0
    warnings=[...],           # 警告列表
    
    # 错误信息（失败时）
    error_code="FILE_NOT_FOUND",
    error_details="文件不存在",
    is_retryable=False,
    
    # 生成的文件
    artifacts=[...]
)
```

---

## 🔍 标准错误码

| 错误码 | 可重试 | 说明 |
|--------|--------|------|
| `TIMEOUT` | ✅ | 执行超时 |
| `MCP_SERVICE_UNAVAILABLE` | ✅ | MCP服务不可用 |
| `DATABASE_ERROR` | ✅ | 数据库错误 |
| `FILE_NOT_FOUND` | ❌ | 文件不存在 |
| `FILE_PARSE_ERROR` | ❌ | 文件解析失败 |
| `INVALID_INPUT` | ❌ | 输入参数无效 |
| `SNAPSHOT_NOT_FOUND` | ❌ | 快照不存在 |

---

## 🛠️ Agent 实现模板（复制使用）

```python
from typing import Dict, Any
from datetime import datetime
from .base_agent import BaseAgent, OpResult
from ..shared.agent_types import ErrorCode

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("MyAgent")
        self.version = "1.0.0"
    
    async def process(self, context: Dict[str, Any]) -> OpResult:
        started_at = datetime.utcnow()
        
        try:
            # 1. 验证输入
            if not self.validate_context(context):
                return self.build_error_result(
                    context, "INVALID_INPUT", "缺少必填字段", started_at
                )
            
            # 2. 执行业务逻辑
            result_data = await self._do_work(context)
            
            # 3. 返回成功结果
            return OpResult(
                status="ok",
                data=result_data,
                message="处理成功",
                agent_name=self.name,
                agent_version=self.version,
                execution_id=context["agent_execution_id"],
                started_at=started_at,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"执行失败: {e}", exc_info=True)
            return self.build_error_result(
                context, "INTERNAL_ERROR", str(e), started_at, is_retryable=True
            )
    
    async def _do_work(self, context: Dict[str, Any]) -> Dict:
        # TODO: 实现业务逻辑
        return {"result": "success"}
```

---

## 📋 常用代码片段

### 读取上游 Agent 输出

```python
from shared.agent_types import extract_upstream_output

# 方式 1：提取整个输出
cad_output = extract_upstream_output(context, "CADAgent")

# 方式 2：提取特定字段
subgraphs = extract_upstream_output(context, "CADAgent", "subgraphs")
```

---

### 读取快照表

```python
from sqlalchemy import select
from shared.models import JobPriceSnapshot
from shared.database import get_db

async def _load_snapshots(self, context):
    async with get_db() as db:
        result = await db.execute(
            select(JobPriceSnapshot).where(
                JobPriceSnapshot.job_id == context["job_id"],
                JobPriceSnapshot.version_id == context["snapshot_refs"]["price_version_locked"]
            )
        )
        return result.scalars().all()
```

---

### 构造错误结果（快捷方法）

```python
# 使用基类的辅助方法
return self.build_error_result(
    context,
    error_code="FILE_NOT_FOUND",
    error_message="文件不存在",
    started_at=started_at,
    is_retryable=False
)
```

---

### 返回警告（部分成功）

```python
return OpResult(
    status="warning",  # 注意使用 warning
    data=result_data,
    message="部分成功",
    warnings=["子图 3 解析失败"],
    agent_name=self.name,
    agent_version=self.version,
    execution_id=context["agent_execution_id"],
    confidence_score=0.75  # 降低置信度
)
```

---

## 🧪 单元测试模板

```python
import pytest
from agents.my_agent import MyAgent
from shared.agent_types import build_execution_id

@pytest.mark.asyncio
async def test_my_agent_success():
    agent = MyAgent()
    
    context = {
        "job_id": "test-job-123",
        "session_id": "sess_test_001",
        "agent_execution_id": build_execution_id("MyAgent"),
        "upstream_outputs": {},
        "snapshot_refs": {},
        "job_metadata": {},
        "subgraphs": None,
        "features": None,
        "agent_parameters": {},
        "directives": {}
    }
    
    result = await agent.process(context)
    
    assert result.status == "ok"
    assert result.agent_name == "MyAgent"
```

---

## 📊 各 Agent 输出 data 字段速查

### CADAgent
```python
data = {
    "subgraphs": [
        {
            "subgraph_id": str,
            "part_name": str,
            "geometry": {...},
            ...
        }
    ],
    "total_subgraphs": int
}
```

### FeatureExtractionAgent
```python
data = {
    "features": [
        {
            "subgraph_id": str,
            "feature_id": str,
            "length_mm": float,
            "material": str,
            "wire_lengths": {...},
            ...
        }
    ]
}
```

### DecisionAgent
```python
data = {
    "process_decisions": [
        {
            "subgraph_id": str,
            "selected_processes": [...],
            "matched_rules": [...],
            "output_params": {...}
        }
    ]
}
```

### PricingAgent
```python
data = {
    "subgraph_pricing": [
        {
            "subgraph_id": str,
            "cost_breakdown": {...},
            "matched_price_items": [...]
        }
    ],
    "job_total_cost": float,
    "currency": "CNY"
}
```

---

## ⚠️ 注意事项

1. ✅ **永远不要直接读主表**（price_items, process_rules）  
   ❌ 错误：`select * from price_items`  
   ✅ 正确：`select * from job_price_snapshots where job_id=...`

2. ✅ **检查上游 Agent 状态**  
   ```python
   if upstream["status"] != "ok":
       return self.build_error_result(...)
   ```

3. ✅ **记录关键日志**  
   ```python
   self.logger.info(f"处理 {len(subgraphs)} 个子图")
   ```

4. ✅ **使用类型提示**  
   ```python
   from shared.agent_types import AgentContext, SubgraphData
   ```

---

## 📞 联系人

- **架构问题**: 架构组
- **Agent 开发**: 各 Agent 负责人（见代码注释）
- **文档问题**: 查看 `docs/agent-io-specification.md`

---

**快速参考卡片 v1.0 | 2026-01-12**
