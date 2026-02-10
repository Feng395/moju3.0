# Pricing Agent 接口文档

## 📋 概述

Pricing Agent 负责计算子图的价格，支持：
- ✅ 并发处理多个子图
- ✅ 交互式重算（用户修改参数后重新计算）
- ✅ 与 pricing-server-mcp 对接

---

## 🎯 接口设计

### 1. 主方法：`process()` (供编排器调用)

**用途**: 首次计算所有子图的价格（并发处理）

**输入格式**:
```python
{
    "job_id": "xxx",                    # 任务ID（必填）
    "subgraph_ids": [                   # 子图ID列表（必填）
        "sub_001",
        "sub_002",
        "sub_003",
        "sub_004"
    ]
}
```

**返回格式**:
```python
{
    "status": "ok",                     # ok/error
    "message": "批量价格计算完成: 成功4个, 失败0个",
    "total": 4,                         # 总数
    "success": 4,                       # 成功数
    "failed": 0,                        # 失败数
    "total_cost": 420.0,                # 总价格
    "results": [                        # 每个子图的详细结果
        {
            "subgraph_id": "sub_001",
            "status": "success",
            "pricing": {
                "material_cost": 50.0,
                "nc_cost": 30.0,
                "wire_cost": 25.0,
                "total_cost": 105.0
            },
            "duration_ms": 1500
        },
        {
            "subgraph_id": "sub_002",
            "status": "success",
            "pricing": {
                "material_cost": 50.0,
                "nc_cost": 30.0,
                "wire_cost": 25.0,
                "total_cost": 105.0
            },
            "duration_ms": 1600
        }
        // ... 其他子图
    ]
}
```

**调用示例**:
```python
# 编排器调用
result = await pricing_agent.process({
    "job_id": "job_12345",
    "subgraph_ids": ["sub_001", "sub_002", "sub_003", "sub_004"]
})
```

---

### 2. 批量重算：`calculate_batch()` (供交互式重算)

**用途**: 用户修改参数后重新计算部分子图

**输入格式**:
```python
{
    "job_id": "xxx",                    # 任务ID（必填）
    "subgraph_ids": [                   # 要重算的子图ID列表（必填）
        "sub_001",
        "sub_002"
    ],
    "user_params": {                    # 用户自定义参数（可选）
        "material": "SKD11",            # 材料类型
        "material_price_override": 50.0,  # 材料价格覆盖
        "nc_rate_override": 30.0,       # NC加工费率覆盖
        "wire_rate_override": 25.0      # 线割费率覆盖
    }
}
```

**返回格式**: 与 `process()` 相同

**调用示例**:
```python
# API Gateway 调用（用户修改了材料类型）
result = await pricing_agent.calculate_batch({
    "job_id": "job_12345",
    "subgraph_ids": ["sub_001", "sub_002"],
    "user_params": {
        "material": "SKD11",
        "material_price_override": 60.0
    }
})
```

---

## 🔄 完整流程

### 编排器调用流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Orchestrator 调用                                         │
│    pricing_agent.process({                                  │
│        "job_id": "xxx",                                     │
│        "subgraph_ids": ["sub_001", "sub_002", ...]         │
│    })                                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Pricing Agent 并发处理每个子图                            │
│    ├─ 子图1: 查询特征 → 调用 MCP → 保存结果                  │
│    ├─ 子图2: 查询特征 → 调用 MCP → 保存结果                  │
│    ├─ 子图3: 查询特征 → 调用 MCP → 保存结果                  │
│    └─ 子图4: 查询特征 → 调用 MCP → 保存结果                  │
│                                                             │
│    每个子图调用:                                             │
│    pricing_mcp_client.call_tool(                           │
│        "pricing-server-mcp",                               │
│        "calculate_price",                                  │
│        {                                                   │
│            "job_id": "xxx",                                │
│            "subgraph_id": "sub_001",                       │
│            "features": {...}                               │
│        }                                                   │
│    )                                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 返回汇总结果                                              │
│    {                                                        │
│        "status": "ok",                                      │
│        "total": 4,                                          │
│        "success": 4,                                        │
│        "failed": 0,                                         │
│        "total_cost": 420.0,                                 │
│        "results": [...]                                     │
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Pricing MCP Server 需要实现的工具

### 工具：`calculate_price`

**用途**: 计算单个子图的价格

**输入参数**:
```python
{
    "job_id": "xxx",                    # 任务ID
    "subgraph_id": "sub_001",           # 子图ID
    "features": {                       # 特征数据（从数据库查询）
        "length_mm": 100.0,
        "width_mm": 50.0,
        "thickness_mm": 10.0,
        "top_view_wire_length": 200.0
    },
    # 以下为用户自定义参数（可选）
    "material": "SKD11",                # 材料类型
    "material_price_override": 50.0,    # 材料价格覆盖
    "nc_rate_override": 30.0,           # NC加工费率覆盖
    "wire_rate_override": 25.0          # 线割费率覆盖
}
```

**返回格式**:
```python
{
    "status": "ok",                     # ok/error
    "message": "价格计算成功",
    "pricing": {
        "material_cost": 50.0,          # 材料成本
        "nc_cost": 30.0,                # NC加工成本
        "wire_cost": 25.0,              # 线割成本
        "total_cost": 105.0             # 总成本
    }
}
```

**MCP Server 职责**:
1. ✅ 根据特征数据计算价格
2. ✅ 支持用户自定义参数覆盖
3. ✅ 将结果保存到数据库（subgraphs 表）
4. ✅ 返回计算结果

---

## 📊 与 CAD Agent 的对比

| 特性 | CAD Agent | Pricing Agent |
|------|-----------|---------------|
| **输入格式** | `{"job_id": "xxx"}` | `{"job_id": "xxx", "subgraph_ids": [...]}` |
| **并发处理** | ✅ 特征识别并发 | ✅ 价格计算并发 |
| **批量重算** | `recognize_features_batch()` | `calculate_batch()` |
| **MCP 工具** | `feature_recognition` | `calculate_price` |
| **返回格式** | 统计信息 + 详细结果 | 统计信息 + 详细结果 + 总价格 |

---

## 🧪 测试示例

### 测试 1: 编排器调用（首次计算）

```python
# 模拟编排器调用
context = {
    "job_id": "job_12345",
    "subgraph_ids": ["sub_001", "sub_002", "sub_003", "sub_004"]
}

result = await pricing_agent.process(context)

# 预期返回
assert result["status"] == "ok"
assert result["total"] == 4
assert result["success"] == 4
assert result["total_cost"] > 0
```

### 测试 2: 交互式重算（用户修改参数）

```python
# 用户修改了材料类型，重新计算 2 个子图
context = {
    "job_id": "job_12345",
    "subgraph_ids": ["sub_001", "sub_002"],
    "user_params": {
        "material": "SKD11",
        "material_price_override": 60.0
    }
}

result = await pricing_agent.calculate_batch(context)

# 预期返回
assert result["status"] == "ok"
assert result["total"] == 2
assert result["success"] == 2
```

---

## ✅ 实现清单

### Pricing Agent (已完成)
- [x] `process()` 方法 - 接收 `job_id` + `subgraph_ids`
- [x] `calculate_batch()` 方法 - 支持用户参数
- [x] `_process_single_subgraph_pricing()` - 单个子图处理
- [x] `_get_features_from_db()` - 从数据库查询特征
- [x] 并发处理逻辑（asyncio.gather）
- [x] 错误处理和日志记录

### Pricing MCP Server (待实现)
- [ ] `calculate_price` 工具
- [ ] 价格计算逻辑
- [ ] 数据库更新逻辑
- [ ] 用户参数覆盖支持
- [ ] 错误处理

---

## 📝 注意事项

1. **并发安全**: 每个子图独立处理，无共享状态
2. **错误隔离**: 单个子图失败不影响其他子图
3. **性能优化**: 使用 `asyncio.gather` 并发执行
4. **日志记录**: 记录每个子图的处理时间和结果
5. **用户参数**: 支持覆盖默认价格参数

---

## 🔗 相关文档

- [CAD Agent 接口文档](./cad-agent-interface.md)
- [并发处理升级方案](../CONCURRENT_UPGRADE_FINAL.md)
- [Agent 交互规范](./agent-interaction-spec.md)
