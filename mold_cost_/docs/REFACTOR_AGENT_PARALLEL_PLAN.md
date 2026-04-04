# 重构并行协作参考文档

本文档用于给并行执行的 agent 分发任务。目标不是让每个 agent 自己做架构设计，而是在当前仓库真实进度基础上，按清晰边界并行推进，减少互相覆盖和返工。

## 1. 当前状态快照

截至 2026-04-04，仓库内已经落地的事实如下：

- `src/mold_cost` 新骨架已建立，`core / application / domain / infrastructure / interfaces` 都已存在。
- 配置、数据库、MinIO、RabbitMQ、Redis 已有统一入口，旧路径仍通过兼容包装可用。
- `application/use_cases` 已承接任务创建、查询、继续执行、审核聊天等主链路入口。
- `job_graph.py` 与 `review_graph.py` 已成为 workflow 外壳，但内部仍主要复用 legacy orchestrator / `InteractionAgent`。
- `domain.features` 已建立桥接入口，`features` 路由已开始走应用层。
- `domain.pricing` 已完成第一轮 bridge 收口，`pricing_agent_local.py` 和 MCP server 已改走 `mold_cost.domain.pricing.*`。
- 第一批重构基线测试通过：`pytest tests/unit/test_refactor_smoke.py tests/unit/test_feature_refactor.py tests/golden/test_pricing_bridge_golden.py -q`，结果为 `8 passed`。

当前仍明确未完成的部分：

- `job_graph` 还不是真正的 LangGraph 节点图，仍是 facade。
- `review_graph` 仍直接复用 `agents/interaction_agent.py`，尚未拆成 review session service + chat agent + tool set。
- `scripts/search/*` 和 `scripts/calculate/*` 仍是算法本体，`domain.pricing` 目前主要是桥接层。
- `scripts/cad_chaitu/main.py` 与 `scripts/feature_recognition/feature_recognition.py` 仍是核心 legacy 实现。
- `scripts/* -> api_gateway.*` 的反向依赖还没有系统清理完。
- 真实业务样本级 golden 回归尚未建立，目前 golden 主要覆盖 bridge 结构。

当前 worktree 里已有一批未提交改动，默认视为“正在进行中的 pricing bridge 任务”，其他 agent 不要覆盖：

- `src/mold_cost/domain/pricing/search/*`
- `src/mold_cost/domain/pricing/calculators/*`
- `src/mold_cost/domain/pricing/search/__init__.py`
- `src/mold_cost/domain/pricing/calculators/__init__.py`
- `tests/golden/test_pricing_bridge_golden.py`
- `tests/golden/pricing_bridge_inventory.json`
- `docs/REFACTOR_PROGRESS.md`

## 2. 协作总原则

- 先解耦，再图化，再智能化。不要先重写算法。
- 一个 agent 只拥有一个清晰写入范围，避免多人同时编辑同一目录。
- `interfaces -> application -> domain -> infrastructure` 只能单向依赖。
- 除“集成人”外，其他 agent 默认不要修改：
  - `src/mold_cost/core/*`
  - `pyproject.toml`
  - `docs/REFACTOR_PROGRESS.md`
  - 任何与自己任务无关的 `__init__.py`
- 所有 agent 都要保留旧入口兼容，不允许直接删除仍在运行链上的 legacy 文件。
- 每个 agent 完成后必须提交：
  - 修改文件清单
  - 影响的入口与调用链
  - 新增/更新测试
  - 未解决风险

## 3. 推荐分工

建议采用 `1 个集成人 + 5 个执行 agent`。这样写入面基本可以隔离，且依赖关系清楚。

### Agent 0: 集成人 / 架构守门人

职责：

- 维护总体边界、合并顺序、接口契约。
- 统一处理跨目录冲突和共享契约文件变更。
- 最终更新 `docs/REFACTOR_PROGRESS.md`。

允许修改：

- `docs/REFACTOR_PROGRESS.md`
- 少量共享契约文件，如 `ports.py`、跨层 `__init__.py`
- 必要的集成修补

不要主动做：

- 大规模搬迁算法文件
- 深入某个执行 agent 的模块实现细节

交付标准：

- 合并各 agent 产物后，基线测试仍通过。
- 冲突点有明确决议，文档状态同步更新。

### Agent 1: Job Workflow 深化

目标：

- 把当前 facade 型 `job_graph` 往“真实状态流”推进一层，但不强行重写 CAD/计价算法。

拥有写入范围：

- `src/mold_cost/application/workflows/job_graph.py`
- `src/mold_cost/application/workflows/job_state.py`
- `src/mold_cost/application/use_cases/continue_job.py`
- `src/mold_cost/interfaces/worker/orchestrator_worker.py`
- `workers/orchestrator_worker.py`
- `workers/all_tasks_worker.py`

可以协同读取但不修改：

- `agents/orchestrator_agent.py`
- `agents/cad_agent.py`
- `agents/pricing_agent.py`

本轮任务：

- 把 `job_graph` 从纯 passthrough facade 提升为显式步骤式 workflow facade。
- 明确并固化状态字段，至少围绕：
  - `job_id`
  - `dwg_path`
  - `prt_path`
  - `subgraph_ids`
  - `feature_summary`
  - `review_status`
  - `pricing_summary`
  - `errors`
  - `artifacts`
- 明确 `start_job` / `continue_job` 的 workflow 入口边界。
- 为后续 LangGraph `interrupt/resume` 预留状态位和 checkpoint 接口。

明确不做：

- 不改 `review_graph`
- 不改 pricing 算法
- 不改 CAD 核心脚本

验收：

- worker 不再直接持有业务编排细节。
- `ContinueJobUseCase` 和 worker 的控制流更加统一。
- 新增针对 `job_graph` 状态推进的单测。

### Agent 2: Review Workflow 拆分

目标：

- 把 `review_graph` 从“包一层 InteractionAgent”推进到可拆分的应用编排层。

拥有写入范围：

- `src/mold_cost/application/workflows/review_graph.py`
- `src/mold_cost/application/workflows/review_state.py`
- `src/mold_cost/application/use_cases/review.py`
- `src/mold_cost/application/use_cases/start_review.py`
- `src/mold_cost/application/use_cases/handle_review_message.py`
- `src/mold_cost/domain/review/services/*`
- `src/mold_cost/domain/review/ports.py`
- `src/mold_cost/interfaces/worker/review_worker.py`
- `workers/review_worker.py`

可以协同读取但不修改：

- `agents/interaction_agent.py`
- `api_gateway/routers/review_router.py`
- `api_gateway/routers/chat_router.py`

本轮任务：

- 拆出 review session service、review state adapter、chat execution adapter。
- 在 `review_graph` 中明确以下节点边界：
  - `load_review_data`
  - `check_completeness`
  - `generate_review_prompt_or_suggestion`
  - `wait_user_message`
  - `apply_review_change`
  - `confirm_and_resume`
- 保持现有 HTTP 路由返回兼容。
- 为后续把聊天 agent/tool 中的具体实现从 `InteractionAgent` 中拔出来做准备。

明确不做：

- 不改前端协议
- 不直接重写 `InteractionAgent` 全量逻辑
- 不碰 pricing bridge

验收：

- `review_graph` 不再只是方法转发器。
- review use case 能独立描述状态推进。
- 新增 review workflow 行为测试，至少覆盖 `start / modify / confirm / check_lock / chat`。

### Agent 3: CAD + Features 领域收口

目标：

- 继续推动 CAD/特征识别入口从 legacy 脚本向 domain/application 层收口，但暂不动算法本体。

拥有写入范围：

- `src/mold_cost/domain/cad/services/*`
- `src/mold_cost/domain/cad/ports.py`
- `src/mold_cost/domain/features/services/*`
- `src/mold_cost/domain/features/ports.py`
- `src/mold_cost/application/use_cases/features.py`
- `src/mold_cost/infrastructure/cad/*`
- `src/mold_cost/interfaces/api/legacy_cad_api.py`
- `api_gateway/routers/features.py`
- `mcp_services/cad_price_search_mcp/server.py` 中仅 feature 相关部分

可以协同读取但不修改：

- `scripts/cad_chaitu/*`
- `scripts/feature_recognition/*`

本轮任务：

- 把 CAD 拆图和特征识别的“外部调用入口”彻底收口到 domain service。
- 清理 domain 层对接口层或网关层的隐式依赖。
- 为后续 `job_graph` 节点调用提供稳定 service API。

明确不做：

- 不重写 `scripts/cad_chaitu/main.py`
- 不重写 `scripts/feature_recognition/feature_recognition.py`
- 不改 review/chat

验收：

- API / MCP / worker 对 CAD 与 feature 的调用都优先经过 `domain.*.services`。
- 至少补充一组 feature 入口回归测试。

### Agent 4: Pricing Bridge 到模块级迁移

目标：

- 在当前已落地的 pricing bridge 基础上，继续做“桥接稳定化 + 反向依赖排查”，暂不直接大规模改算法。

拥有写入范围：

- `src/mold_cost/domain/pricing/search/*`
- `src/mold_cost/domain/pricing/calculators/*`
- `src/mold_cost/domain/pricing/services/*`
- `src/mold_cost/domain/pricing/ports.py`
- `agents/pricing_agent_local.py`
- `mcp_services/cad_price_search_mcp/server.py` 中仅 pricing 相关部分
- `tests/golden/test_pricing_bridge_golden.py`
- `tests/golden/pricing_bridge_inventory.json`

本轮任务：

- 继续把包级 bridge 推进到模块级 bridge，并保持导出稳定。
- 排查 bridge 文件里仍然可能存在的 `scripts/* -> api_gateway.*` 反向引用。
- 识别最适合下一批真正迁出的 3 到 5 个 pricing 模块。
- 补充 golden inventory，保证桥接清单可回归。

明确不做：

- 不直接改 `job_graph`
- 不动 review/chat
- 不做跨目录大规模引用替换

验收：

- `pricing_agent_local.py`、MCP、其它外部入口不再新增对 `scripts.search` / `scripts.calculate` 的直接 import。
- golden bridge 测试继续通过。
- 输出“下一批真正迁移的 pricing 模块候选名单”。

注意：

- 当前 worktree 已经有人在这个范围内工作，如果要继续并行，优先由同一个 agent 接手，不建议拆给第二个人。

### Agent 5: 反向依赖清理 + 接口层瘦身

目标：

- 定点清理 `scripts/* -> api_gateway.*` 的反向依赖，并继续把接口层压回 adapter。

拥有写入范围：

- `api_gateway/routers/jobs.py`
- `api_gateway/services/*`
- `api_gateway/repositories/*`
- `scripts/process_rule_matcher.py`
- `scripts/search/*` 中涉及 `api_gateway` import 的文件
- `scripts/calculate/*` 中涉及 `api_gateway` import 的文件
- 必要时新增 `src/mold_cost/infrastructure/db/repositories/*`

先做什么：

- 先用 `rg "api_gateway\\." scripts` 列出所有反向依赖点。
- 按“数据库访问 / repository 访问 / 配置访问 / 消息访问”分类。
- 优先处理最靠近 pricing 与 feature 主链路的反向依赖。

本轮任务：

- 用 infrastructure repository 或 domain port 替掉 `api_gateway.database` 等接口层依赖。
- 让 `jobs.py` 继续减薄，只保留协议转换、鉴权、响应映射。
- 输出一份“剩余反向依赖清单”。

明确不做：

- 不改 `src/mold_cost/domain/pricing/search/*`
- 不改 `src/mold_cost/domain/pricing/calculators/*`
- 不改 `review_graph`

验收：

- 至少消掉一批确定的 `scripts/* -> api_gateway.*` 依赖。
- `jobs.py` 中 legacy 控制流进一步减少。
- 新增一份依赖扫描结果或测试保障。

### Agent 6: Golden / 集成测试与样本治理

目标：

- 让重构从“结构 smoke test”走向“业务回归 test”。

拥有写入范围：

- `tests/golden/*`
- `tests/integration/*`
- `tests/e2e/*`
- `tools/diagnostics/*`
- 只读使用 `scripts/` 中样本或现有输出，不修改核心业务实现

本轮任务：

- 为“上传 -> 拆图 -> 特征识别 -> 审核 -> 计价”设计第一版 golden 数据目录规范。
- 把当前 bridge 级 golden 扩展为“样本清单 + 期望摘要 + 断言规则”。
- 为 workflow 暂停/恢复设计最小测试夹具。
- 将现有诊断脚本中可复用的检查逻辑沉到 `tools/diagnostics` 或 `tests/helpers`。

明确不做：

- 不大改业务代码
- 不改 domain bridge 实现

验收：

- 新增一份可复用的 golden 样本规范文档或夹具代码。
- 至少有一组比当前 bridge inventory 更接近真实业务的回归测试骨架。

## 4. 推荐执行顺序

第一批可以立即并行：

- Agent 1: Job Workflow 深化
- Agent 2: Review Workflow 拆分
- Agent 3: CAD + Features 领域收口
- Agent 4: Pricing Bridge 到模块级迁移
- Agent 6: Golden / 集成测试与样本治理

第二批在第一批基础上推进：

- Agent 5: 反向依赖清理 + 接口层瘦身

原因：

- Agent 5 依赖前几条工作流和领域边界先更稳定，否则很容易在“替换依赖目标”上反复返工。

## 5. 合并顺序

建议按下面顺序合并：

1. Agent 4
2. Agent 3
3. Agent 1
4. Agent 2
5. Agent 5
6. Agent 6
7. Agent 0 做最终集成与进度文档更新

原因：

- pricing bridge 当前已在进行中，先收口可以减少冲突。
- CAD/features 服务稳定后，job workflow 更容易接正式 service。
- review 拆分和接口层瘦身都依赖边界更清楚。
- golden 与集成测试最好在主要接口趋稳后做最后校准。

## 6. 每个 Agent 的统一输出模板

每个 agent 结束时按下面格式交付：

### 结果摘要

- 本次完成的目标
- 未完成但已识别的后续项

### 修改文件

- 逐个列出改动文件

### 关键决策

- 说明做了哪些边界判断
- 说明哪些 legacy 逻辑被保留，哪些被转发

### 验证

- 运行了哪些测试/脚本
- 结果是什么

### 风险与交接

- 仍依赖哪些 legacy 实现
- 下一个 agent 接手时需要注意什么

## 7. 可直接分发的简版任务卡

给所有 agent 的统一前置说明：

> 当前项目采用兼容迁移，不允许一次性推倒重写。请只在分配给你的目录范围内工作，保持旧入口兼容，优先把边界收口到 `src/mold_cost`，不要重写 CAD / feature / pricing 的核心算法。完成后请按“结果摘要 / 修改文件 / 关键决策 / 验证 / 风险与交接”格式回报。

给 Agent 1：

> 你负责 `job_graph` 及任务执行 workflow 的深化。目标是把当前 facade 推进成显式状态流，但不要改 review 和算法实现。

给 Agent 2：

> 你负责 `review_graph` 和 review use cases 的拆分。目标是把审核链从 `InteractionAgent` 的直接封装推进成可拆分 workflow。

给 Agent 3：

> 你负责 CAD 与 feature 入口收口。目标是让 API / worker / MCP 对外只经过 domain service，不直接扩散到 legacy 脚本。

给 Agent 4：

> 你负责 pricing bridge 稳定化和模块级迁移。当前这个目录已经有人在改，优先延续现有做法，不要覆盖别人的 bridge 变更。

给 Agent 5：

> 你负责清理 `scripts/* -> api_gateway.*` 反向依赖和接口层瘦身。先出依赖扫描清单，再逐批替换。

给 Agent 6：

> 你负责 golden、integration、diagnostics 的治理。目标是把重构验证从 smoke test 推到业务样本回归。

## 8. 本轮最重要的成功标准

本轮并行协作的成功，不是“把 legacy 全删掉”，而是下面四件事：

- 新入口继续集中到 `src/mold_cost`
- workflow 不再只是空壳
- pricing / features / CAD 的外部入口继续收口
- 回归验证从结构检查推进到业务样本检查

如果这四点做到，下一轮再推进真正的 LangGraph 节点化、人审 interrupt/resume、以及算法逐模块迁移，风险会低很多。
