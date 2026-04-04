# Agent 4 任务文档

角色：

- Pricing Bridge 到模块级迁移

目标：

- 稳定当前 `domain.pricing` bridge
- 继续把包级 bridge 推进到模块级 bridge
- 排查 bridge 内部仍残留的反向依赖

允许写入：

- `src/mold_cost/domain/pricing/search/*`
- `src/mold_cost/domain/pricing/calculators/*`
- `src/mold_cost/domain/pricing/services/*`
- `src/mold_cost/domain/pricing/ports.py`
- `agents/pricing_agent_local.py`
- `mcp_services/cad_price_search_mcp/server.py` 中仅 pricing 相关部分
- `tests/golden/test_pricing_bridge_golden.py`
- `tests/golden/pricing_bridge_inventory.json`

本轮特别注意：

- 该目录当前 worktree 已存在未提交改动
- 优先延续现有 bridge 风格
- 不要覆盖他人正在进行中的 pricing bridge 变更

本轮必须完成：

- 把包级 bridge 推进到模块级 bridge，并保持导出稳定
- 排查 `scripts/* -> api_gateway.*` 在 pricing bridge 内的残留引用
- 识别下一批最适合真正迁出的 3 到 5 个 pricing 模块
- 补充 golden inventory，保证桥接清单可回归

禁止事项：

- 不改 `job_graph`
- 不改 review/chat
- 不做跨目录大规模引用替换

验收标准：

- 外部入口不再新增对 `scripts.search` / `scripts.calculate` 的直接 import
- pricing bridge golden 测试继续通过
- 输出下一批 pricing 模块迁移候选名单

交付格式：

- 结果摘要
- 修改文件
- 关键决策
- 验证
- 风险与交接
