# Agent 1 提示词

你负责本仓库的 Job Workflow 深化，只在指定写入范围内工作。

项目约束：

- 当前项目采用兼容迁移，不允许一次性推倒重写。
- 保留 legacy 兼容入口，不要直接删除仍在运行链上的旧实现。
- 不要重写 CAD、feature、pricing 的核心算法。
- 除非确有必要，不要修改与任务无关的 `__init__.py`、`pyproject.toml`、`docs/REFACTOR_PROGRESS.md`。

你的写入范围：

- `src/mold_cost/application/workflows/job_graph.py`
- `src/mold_cost/application/workflows/job_state.py`
- `src/mold_cost/application/use_cases/continue_job.py`
- `src/mold_cost/interfaces/worker/orchestrator_worker.py`
- `workers/orchestrator_worker.py`
- `workers/all_tasks_worker.py`

你的目标：

- 把当前 facade 型 `job_graph` 推进为显式状态流 workflow facade
- 固化状态字段：`job_id`、`dwg_path`、`prt_path`、`subgraph_ids`、`feature_summary`、`review_status`、`pricing_summary`、`errors`、`artifacts`
- 统一 `start_job` / `continue_job` 的 workflow 入口
- 为后续 LangGraph `interrupt/resume` 预留状态位和 checkpoint 接口

不要做的事：

- 不改 `review_graph`
- 不改 pricing 算法
- 不改 CAD 核心脚本

完成后请按以下格式回复：

1. 结果摘要
2. 修改文件
3. 关键决策
4. 验证
5. 风险与交接
