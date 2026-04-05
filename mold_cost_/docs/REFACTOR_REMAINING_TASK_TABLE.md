# 剩余阶段任务对照表

更新时间：2026-04-05（Wave B 第三波 calculator 已完成）

基线提交：`ec149e5 feat(refactor): 落地 durable checkpoint、review 去 agent 化与第二批 pricing search 迁移`

说明：
- 本表用于承接 [REFACTOR_PROGRESS.md](/d:/workspace/project/python/mold3.0/mold_cost_/docs/REFACTOR_PROGRESS.md) 已完成阶段后的剩余工作。
- 状态定义：`已落地` 表示已有真实承接路径；`桥接中` 表示新边界已建立但仍复用 legacy；`未开始` 表示尚未形成稳定新实现。
- 优先级按当前风险和依赖顺序排序，默认先做“去依赖 + 稳定边界”，再做“算法本体迁移”。

| 阶段 | 优先级 | 目标 | 当前状态 | 主要残留问题 | 下一步动作 | 验收标准 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 应用层去 `api_gateway` 依赖 | P0 | 让 `application/use_cases` 只依赖 `src/mold_cost` 内部仓储/服务 | 已落地 | 仍需观察旧 service 外壳是否还有隐性回流 | 继续在新增 use case 中保持新依赖方向 | `src/mold_cost/application/*` 不再直接 import `api_gateway.*` |
| R2 接口层真实翻面 | P0 | 让 `interfaces/api` 成为主入口，而不是旧路由包装层 | 已落地 | 仍有部分非 jobs/files 路由继续复用 legacy router 模块 | 逐步把剩余 API 路由向 `src/mold_cost/interfaces/api` 收口 | `src/mold_cost/interfaces/api/*` 成为主入口，旧 `api_gateway` 仅作兼容导出 |
| R3 Review 数据访问去 legacy 化 | P0 | 把 review 数据加载、修改应用、状态管理完整收口到新层 | 桥接中 | `review_change_applier` 已通过 infrastructure adapter 去掉对 `agents.action_handlers`、`agents.confirm_handler` 的直连，但 `review_data_loader` / `review_notifier` 仍复用部分 legacy helper，默认 state/session 仍是 Redis 适配器 | 继续把 `review_data_loader`、`review_notifier` 剩余 legacy helper 收口到新适配层，并评估 Redis 默认装配的替代方案 | `review_graph` 默认装配只依赖 `src/mold_cost` 内部对象 |
| R4 Pricing 主链迁移收尾 | P1 | 完成 search、process matcher 与 calculator 的迁移 | 桥接中 | `domain.pricing.search`、`process_rule_matcher` 与 `domain.pricing.calculators` 已全部去掉 `scripts.calculate/*` 直连，`pricing_service.calculate` 与 `pricing_service.update_job_total_cost` 也已下沉到 `src/mold_cost`；当前残留桥接已收敛到 `agents/__init__.py` 的 pricing agent 工厂、`agents/pricing_agent.py`、`agents/pricing_agent_local.py` 以及 MCP 兼容路由 | 优先缩减 `agents/__init__.py` 的 mode switch，再收口 `agents/pricing_agent.py`、`agents/pricing_agent_local.py` 与 `mcp_services/cad_price_search_mcp/server.py` | `domain/pricing` 主链与外部入口不再依赖旧 pricing agent 工厂和 MCP router 作为运行时桥接 |
| R5 Workflow durable backend 共享化 | P1 | 将 job/review 的 checkpoint 从本地 fallback 推进到可共享持久化后端 | 桥接中 | `job_graph` 目前是本地文件 fallback；`review_graph` 默认仍是内存 checkpointer | 引入共享 durable store 适配层，统一 job/review checkpoint backend 配置 | 多实例或 worker 重启后，job/review 都可恢复同一 thread |
| R6 CAD / Feature 算法本体迁移 | P2 | 让 CAD 拆图与特征识别算法从 `scripts/*` 迁到稳定 domain/infrastructure 结构 | 桥接中 | `LegacyCadSplitGateway`、`LegacyFeatureRecognitionGateway` 仍直接调用 `scripts.cad_chaitu` 与 `scripts.feature_recognition` | 先梳理算法模块边界，再逐步迁核心入口和公用依赖 | `domain.cad`、`domain.features` 主链不再直接 import `scripts.*` |
| R7 Golden 样本扩展 | P2 | 增强 workflow/pricing 回归覆盖面 | 已落地但不足 | 目前 golden 样本仍偏少，定价分支覆盖不足 | 增加 2 到 3 组不同零件类型、工艺组合、价格分支样本 | `tests/golden` 能覆盖多零件、多分支，不再依赖单样本基线 |
| R8 兼容入口与诊断脚本清理 | P2 | 压缩 legacy 包装层，减少双入口长期并存 | 桥接中 | `workers/`、`api_gateway/`、`scripts/` 中仍有不少兼容入口与诊断脚本 | 建立保留清单，逐步删除无效兼容入口和历史诊断脚本 | legacy 目录只保留明确需要的兼容入口，职责清晰 |

## 建议执行顺序

| 波次 | 范围 | 目的 | 说明 |
| --- | --- | --- | --- |
| Wave A | R1 + R2 | 先理顺应用层与接口层依赖方向 | 这是后续 review/pricing 继续迁移的地基 |
| Wave B | R3 + R4 | 继续缩小 review/pricing 的 legacy 面积 | 这两块是当前主链最集中的遗留耦合 |
| Wave C | R5 + R7 | 加强恢复能力和回归基线 | 降低切换风险，支撑后续算法迁移 |
| Wave D | R6 + R8 | 清理算法本体与兼容尾项 | 风险更高，放在边界稳定后推进 |

## 当前建议认领

| 任务 | 建议负责人 | 范围 | 预期产出 |
| --- | --- | --- | --- |
| A1 | 子 agent 1 | `src/mold_cost/application/use_cases/*`、新增 infrastructure adapter | 去掉 use case 对 `api_gateway.repositories/utils` 的直接依赖 |
| A2 | 子 agent 2 | `src/mold_cost/interfaces/api/*`、旧 `api_gateway` 薄包装 | 让新接口层成为真实主入口 |
| A3 | 主 agent / 后续波次 | `src/mold_cost/domain/review/*`、`src/mold_cost/domain/pricing/*` | 在 A1/A2 完成后继续推进 review handler 与 pricing calculator 主链迁移 |
## 2026-04-05 增量更新（Pricing Service 下沉完成）

R4 最新状态：
- `pricing_service.calculate` 已落到 `src/mold_cost/domain/pricing/services/pricing_service.py`，不再反调 `get_pricing_agent()`。
- `agents/pricing_agent_local.py` 已缩成兼容包装层，当前仅保留进度发布注入与 `pricing_service.calculate(...)` 委托。
- `mcp_services/cad_price_search_mcp/server.py` 仍是 pricing 兼容路由主残留，当前与 `src/mold_cost` 的耦合已经收敛到工具级路由编排。

R4 下一步：
- 继续压缩 `mcp_services/cad_price_search_mcp/server.py` 的搜索/计算分支路由，减少逐工具硬编码装配。
- 评估将直接调用 pricing 的 worker / router 逐步切到 `pricing_service` 或新的 application use case，最终移除 `PricingAgent` / `PricingAgentLocal` 包装层。

当前回归基线：
- `pytest tests/unit tests/integration tests/golden -q` => `123 passed`
