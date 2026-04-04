# Agent 3 提示词

你负责本仓库的 CAD + Features 领域收口，只在指定写入范围内工作。

项目约束：

- 当前项目采用兼容迁移，不允许一次性推倒重写。
- 保留 legacy 兼容入口，不要直接删除仍在运行链上的旧实现。
- 不要重写 CAD、feature、pricing 的核心算法。
- 除非确有必要，不要修改与任务无关的 `__init__.py`、`pyproject.toml`、`docs/REFACTOR_PROGRESS.md`。

你的写入范围：

- `src/mold_cost/domain/cad/services/*`
- `src/mold_cost/domain/cad/ports.py`
- `src/mold_cost/domain/features/services/*`
- `src/mold_cost/domain/features/ports.py`
- `src/mold_cost/application/use_cases/features.py`
- `src/mold_cost/infrastructure/cad/*`
- `src/mold_cost/interfaces/api/legacy_cad_api.py`
- `api_gateway/routers/features.py`
- `mcp_services/cad_price_search_mcp/server.py` 中仅 feature 相关部分

你的目标：

- 让 API / worker / MCP 对 CAD 与特征识别的调用收口到 `domain.*.services`
- 清理 domain 层对接口层或网关层的隐式依赖
- 为后续 `job_graph` 节点调用提供稳定 service API

不要做的事：

- 不重写 `scripts/cad_chaitu/main.py`
- 不重写 `scripts/feature_recognition/feature_recognition.py`
- 不改 review/chat

完成后请按以下格式回复：

1. 结果摘要
2. 修改文件
3. 关键决策
4. 验证
5. 风险与交接
