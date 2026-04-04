# Agent 2 任务文档

角色：

- Review Workflow 拆分

目标：

- 把 `review_graph` 从“包一层 InteractionAgent”推进为可拆分 workflow
- 将审核会话、状态适配、聊天执行边界分清
- 保持现有 HTTP 路由兼容

允许写入：

- `src/mold_cost/application/workflows/review_graph.py`
- `src/mold_cost/application/workflows/review_state.py`
- `src/mold_cost/application/use_cases/review.py`
- `src/mold_cost/application/use_cases/start_review.py`
- `src/mold_cost/application/use_cases/handle_review_message.py`
- `src/mold_cost/domain/review/services/*`
- `src/mold_cost/domain/review/ports.py`
- `src/mold_cost/interfaces/worker/review_worker.py`
- `workers/review_worker.py`

只读参考：

- `agents/interaction_agent.py`
- `api_gateway/routers/review_router.py`
- `api_gateway/routers/chat_router.py`

本轮必须完成：

- 拆出 review session service、review state adapter、chat execution adapter
- 在 `review_graph` 明确以下节点边界：
  - `load_review_data`
  - `check_completeness`
  - `generate_review_prompt_or_suggestion`
  - `wait_user_message`
  - `apply_review_change`
  - `confirm_and_resume`
- 保持 review/chat 路由协议兼容

禁止事项：

- 不改前端协议
- 不直接重写 `InteractionAgent` 全量逻辑
- 不碰 pricing bridge

验收标准：

- `review_graph` 不再只是方法转发器
- review use case 可清晰描述状态推进
- 至少新增一组 review workflow 行为测试

交付格式：

- 结果摘要
- 修改文件
- 关键决策
- 验证
- 风险与交接
