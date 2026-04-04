# Agent 4 提示词

你负责本仓库的 Pricing Bridge 到模块级迁移，只在指定写入范围内工作。

项目约束：

- 当前项目采用兼容迁移，不允许一次性推倒重写。
- 保留 legacy 兼容入口，不要直接删除仍在运行链上的旧实现。
- 不要重写 pricing 核心算法。
- 除非确有必要，不要修改与任务无关的 `__init__.py`、`pyproject.toml`、`docs/REFACTOR_PROGRESS.md`。

你的写入范围：

- `src/mold_cost/domain/pricing/search/*`
- `src/mold_cost/domain/pricing/calculators/*`
- `src/mold_cost/domain/pricing/services/*`
- `src/mold_cost/domain/pricing/ports.py`
- `agents/pricing_agent_local.py`
- `mcp_services/cad_price_search_mcp/server.py` 中仅 pricing 相关部分
- `tests/golden/test_pricing_bridge_golden.py`
- `tests/golden/pricing_bridge_inventory.json`

特别注意：

- 当前这个范围内已经存在未提交改动
- 优先延续现有 bridge 风格，不要覆盖别人的改动

你的目标：

- 把包级 bridge 推进到模块级 bridge，并保持导出稳定
- 排查 pricing bridge 内部残留的 `scripts/* -> api_gateway.*` 反向依赖
- 输出下一批最适合真正迁出的 3 到 5 个 pricing 模块候选名单
- 补充 golden inventory，保证桥接清单可回归

不要做的事：

- 不改 `job_graph`
- 不改 review/chat
- 不做跨目录大规模引用替换

完成后请按以下格式回复：

1. 结果摘要
2. 修改文件
3. 关键决策
4. 验证
5. 风险与交接
