# Agent 2 提示词

你负责本仓库的 Review Workflow 拆分，只在指定写入范围内工作。

项目约束：

- 当前项目采用兼容迁移，不允许一次性推倒重写。
- 保留 legacy 兼容入口，不要直接删除仍在运行链上的旧实现。
- 不要重写 CAD、feature、pricing 的核心算法。
- 除非确有必要，不要修改与任务无关的 `__init__.py`、`pyproject.toml`、`docs/REFACTOR_PROGRESS.md`。

你的写入范围：

- `src/mold_cost/application/workflows/review_graph.py`
- `src/mold_cost/application/workflows/review_state.py`
- `src/mold_cost/application/use_cases/review.py`
- `src/mold_cost/application/use_cases/start_review.py`
- `src/mold_cost/application/use_cases/handle_review_message.py`
- `src/mold_cost/domain/review/services/*`
- `src/mold_cost/domain/review/ports.py`
- `src/mold_cost/interfaces/worker/review_worker.py`
- `workers/review_worker.py`

你的目标：

- 把 `review_graph` 从对 `InteractionAgent` 的封装推进成可拆分 workflow
- 拆出 review session service、review state adapter、chat execution adapter
- 明确节点边界：`load_review_data`、`check_completeness`、`generate_review_prompt_or_suggestion`、`wait_user_message`、`apply_review_change`、`confirm_and_resume`
- 保持现有 review/chat 路由协议兼容

不要做的事：

- 不改前端协议
- 不直接重写 `InteractionAgent` 全量逻辑
- 不碰 pricing bridge

完成后请按以下格式回复：

1. 结果摘要
2. 修改文件
3. 关键决策
4. 验证
5. 风险与交接
