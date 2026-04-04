# Agent 1 任务文档

角色：

- Job Workflow 深化

目标：

- 把当前 facade 型 `job_graph` 推进为显式状态流 workflow facade
- 统一任务开始和继续执行的控制流
- 为后续 LangGraph interrupt / resume 预留状态位和 checkpoint 接口

允许写入：

- `src/mold_cost/application/workflows/job_graph.py`
- `src/mold_cost/application/workflows/job_state.py`
- `src/mold_cost/application/use_cases/continue_job.py`
- `src/mold_cost/interfaces/worker/orchestrator_worker.py`
- `workers/orchestrator_worker.py`
- `workers/all_tasks_worker.py`

只读参考：

- `agents/orchestrator_agent.py`
- `agents/cad_agent.py`
- `agents/pricing_agent.py`

本轮必须完成：

- 将 `job_graph` 从 passthrough facade 提升为显式步骤式 facade
- 固化状态字段：
  - `job_id`
  - `dwg_path`
  - `prt_path`
  - `subgraph_ids`
  - `feature_summary`
  - `review_status`
  - `pricing_summary`
  - `errors`
  - `artifacts`
- 统一 `start_job` / `continue_job` 的 workflow 入口
- 为后续 LangGraph checkpoint 留出清晰接口

禁止事项：

- 不改 `review_graph`
- 不改 pricing 算法
- 不改 CAD 核心脚本

验收标准：

- worker 不再直接持有业务编排细节
- `ContinueJobUseCase` 和 worker 控制流更统一
- 至少新增一组 `job_graph` 状态推进测试

交付格式：

- 结果摘要
- 修改文件
- 关键决策
- 验证
- 风险与交接
