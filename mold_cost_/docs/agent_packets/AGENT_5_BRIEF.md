# Agent 5 任务文档

角色：

- 反向依赖清理 + 接口层瘦身

目标：

- 定点清理 `scripts/* -> api_gateway.*` 反向依赖
- 继续把接口层压回 adapter
- 输出剩余反向依赖清单

允许写入：

- `api_gateway/routers/jobs.py`
- `api_gateway/services/*`
- `api_gateway/repositories/*`
- `scripts/process_rule_matcher.py`
- `scripts/search/*` 中涉及 `api_gateway` import 的文件
- `scripts/calculate/*` 中涉及 `api_gateway` import 的文件
- 必要时新增 `src/mold_cost/infrastructure/db/repositories/*`

开始前必须先做：

- 扫描 `scripts` 下所有 `api_gateway.` 引用
- 按数据库访问、repository 访问、配置访问、消息访问分类
- 优先处理靠近 pricing 和 feature 主链路的反向依赖

本轮必须完成：

- 用 infrastructure repository 或 domain port 替掉 `api_gateway.database` 等接口层依赖
- 让 `jobs.py` 继续减薄，只保留协议转换、鉴权、响应映射
- 输出剩余反向依赖清单

禁止事项：

- 不改 `src/mold_cost/domain/pricing/search/*`
- 不改 `src/mold_cost/domain/pricing/calculators/*`
- 不改 `review_graph`

验收标准：

- 至少消掉一批确定的 `scripts/* -> api_gateway.*` 依赖
- `jobs.py` 中 legacy 控制流进一步减少
- 新增一份依赖扫描结果或测试保障

交付格式：

- 结果摘要
- 修改文件
- 关键决策
- 验证
- 风险与交接
