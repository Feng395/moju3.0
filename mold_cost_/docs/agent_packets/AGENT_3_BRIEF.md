# Agent 3 任务文档

角色：

- CAD + Features 领域收口

目标：

- 让 API / worker / MCP 对 CAD 与特征识别的调用收口到 domain service
- 清理 domain 层对接口层或网关层的隐式依赖
- 为后续 `job_graph` 节点调用提供稳定 service API

允许写入：

- `src/mold_cost/domain/cad/services/*`
- `src/mold_cost/domain/cad/ports.py`
- `src/mold_cost/domain/features/services/*`
- `src/mold_cost/domain/features/ports.py`
- `src/mold_cost/application/use_cases/features.py`
- `src/mold_cost/infrastructure/cad/*`
- `src/mold_cost/interfaces/api/legacy_cad_api.py`
- `api_gateway/routers/features.py`
- `mcp_services/cad_price_search_mcp/server.py` 中仅 feature 相关部分

只读参考：

- `scripts/cad_chaitu/*`
- `scripts/feature_recognition/*`

本轮必须完成：

- 把 CAD 拆图和特征识别的外部调用入口彻底收口到 domain service
- 清理 domain 层对接口层或网关层的隐式依赖
- 提供可供 workflow 调用的稳定服务接口

禁止事项：

- 不重写 `scripts/cad_chaitu/main.py`
- 不重写 `scripts/feature_recognition/feature_recognition.py`
- 不改 review/chat

验收标准：

- API / MCP / worker 对 CAD 与 feature 的调用都优先经过 `domain.*.services`
- 至少新增一组 feature 入口回归测试

交付格式：

- 结果摘要
- 修改文件
- 关键决策
- 验证
- 风险与交接
