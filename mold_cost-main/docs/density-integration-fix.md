# 密度数据集成修复

## 问题描述

用户报告重量字段（weight_kg）都是 0.00，没有进行计算。

## 根本原因

虽然 `density_search.py` 脚本已经实现并集成到 MCP 服务中，但在实际计算流程中**没有被调用**：

1. **pricing_agent.py** 的 `_concurrent_search` 方法中没有调用 `search_density`
2. **MCP 服务**中的 4 个计算器没有获取 density 数据：
   - `calculate_weight` - 重量计算
   - `calculate_material_cost` - 材料成本计算
   - `calculate_heat_treatment_cost` - 热处理成本计算
   - `calculate_add_auto_material_cost` - 自找料成本计算

## 受影响的计算脚本

以下脚本需要 `density` 数据但没有获取：

1. `scripts/calculate/price_weight.py` - 重量计算
   - 公式: `weight = density × length_mm × width_mm × thickness_mm`
   
2. `scripts/calculate/price_material.py` - 材料成本计算
   - 需要密度计算材料重量和成本
   
3. `scripts/calculate/price_heat.py` - 热处理成本计算
   - 需要密度计算热处理重量和成本
   
4. `scripts/calculate/price_add_auto_material.py` - 自找料成本计算
   - 需要密度计算自找料重量和成本

## 修复内容

### 1. 修改 `agents/pricing_agent.py`

在 `_concurrent_search` 方法中添加 `search_density` 调用：

```python
# 并发调用所有搜索工具
search_tasks = [
    self.price_search_mcp.call_tool("unified-mcp", "search_base_itemcode", ...),
    self.price_search_mcp.call_tool("unified-mcp", "search_material", ...),
    self.price_search_mcp.call_tool("unified-mcp", "search_density", ...),  # 新增
    self.price_search_mcp.call_tool("unified-mcp", "search_heat", ...),
    # ... 其他搜索工具
]
```

在 `_merge_search_results` 方法中添加 `density` 字段：

```python
merged = {
    "job_id": job_id,
    "base_itemcode": {},
    "material": {},
    "density": {},  # 新增
    "heat": {},
    # ... 其他字段
}

tool_names = [
    "base_itemcode", "material", "density", "heat", ...  # 新增 density
]
```

### 2. 修改 `mcp_services/cad_price_search_mcp/server.py`

为 4 个计算器添加 `density_data` 获取：

#### calculate_weight
```python
elif name == "calculate_weight":
    base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
    density_data = await density_search.search_by_job_id(job_id, subgraph_ids)  # 新增
    search_data = {"base_itemcode": base_data, "density": density_data}
    result = await price_weight.calculate(search_data, job_id, subgraph_ids)
```

#### calculate_material_cost
```python
elif name == "calculate_material_cost":
    base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
    material_data = await material_search.search_by_job_id(job_id, subgraph_ids)
    density_data = await density_search.search_by_job_id(job_id, subgraph_ids)  # 新增
    search_data = {"base_itemcode": base_data, "material": material_data, "density": density_data}
    result = await price_material.calculate(search_data, job_id, subgraph_ids)
```

#### calculate_heat_treatment_cost
```python
elif name == "calculate_heat_treatment_cost":
    base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
    heat_data = await heat_search.search_by_job_id(job_id, subgraph_ids)
    density_data = await density_search.search_by_job_id(job_id, subgraph_ids)  # 新增
    search_data = {"base_itemcode": base_data, "heat": heat_data, "density": density_data}
    result = await price_heat.calculate(search_data, job_id, subgraph_ids)
```

#### calculate_add_auto_material_cost
```python
elif name == "calculate_add_auto_material_cost":
    base_data = await base_itemcode_search.search_by_job_id(job_id, subgraph_ids)
    material_data = await material_search.search_by_job_id(job_id, subgraph_ids)
    density_data = await density_search.search_by_job_id(job_id, subgraph_ids)  # 新增
    search_data = {"base_itemcode": base_data, "material": material_data, "density": density_data}
    result = await price_add_auto_material.calculate(search_data, job_id, subgraph_ids)
```

## 测试验证

创建了测试脚本 `tests/infrastructure/test_density_integration.py`：

```bash
python tests/infrastructure/test_density_integration.py <job_id>
```

测试步骤：
1. 验证 `density_search` 能否正确查询密度数据
2. 验证 `base_itemcode_search` 能否正确查询零件信息
3. 验证 `price_weight.calculate` 能否正确计算重量
4. 验证数据库中的 `weight_kg` 字段是否已更新

## 部署步骤

1. **重启 MCP 服务**（必须）
   ```bash
   # 停止旧服务
   # 启动新服务
   python mcp_services/cad_price_search_mcp/server.py
   ```

2. **重启 pricing_agent worker**（必须）
   ```bash
   python workers/all_tasks_worker.py
   ```

3. **测试验证**
   ```bash
   # 使用现有 job_id 测试
   python tests/infrastructure/test_density_integration.py <job_id>
   ```

4. **重新计算现有任务**（可选）
   如果需要修复已有任务的重量数据：
   ```bash
   # 使用 pricing_recalculate_worker 重新计算
   python workers/pricing_recalculate_worker.py
   ```

## 影响范围

- ✅ 重量计算现在会正确使用密度数据
- ✅ 材料成本计算现在会正确使用密度数据
- ✅ 热处理成本计算现在会正确使用密度数据
- ✅ 自找料成本计算现在会正确使用密度数据
- ✅ 所有相关字段（weight_kg、material_cost、heat_treatment_cost 等）将正确计算

## 相关文件

- `agents/pricing_agent.py` - 价格计算 Agent（已修改）
- `mcp_services/cad_price_search_mcp/server.py` - MCP 服务（已修改）
- `scripts/search/density_search.py` - 密度检索脚本（无需修改）
- `scripts/calculate/price_weight.py` - 重量计算脚本（无需修改）
- `scripts/calculate/price_material.py` - 材料成本计算脚本（无需修改）
- `scripts/calculate/price_heat.py` - 热处理成本计算脚本（无需修改）
- `scripts/calculate/price_add_auto_material.py` - 自找料成本计算脚本（无需修改）
- `tests/infrastructure/test_density_integration.py` - 集成测试脚本（新增）

## 修复完成时间

2026-02-03

## 修复人员

Kiro AI Assistant
