# Agent 5 提示词

你负责本仓库的反向依赖清理和接口层瘦身，只在指定写入范围内工作。

项目约束：

- 当前项目采用兼容迁移，不允许一次性推倒重写。
- 保留 legacy 兼容入口，不要直接删除仍在运行链上的旧实现。
- 除非确有必要，不要修改与任务无关的 `__init__.py`、`pyproject.toml`、`docs/REFACTOR_PROGRESS.md`。

你的写入范围：

- `api_gateway/routers/jobs.py`
- `api_gateway/services/*`
- `api_gateway/repositories/*`
- `scripts/process_rule_matcher.py`
- `scripts/search/*` 中涉及 `api_gateway` import 的文件
- `scripts/calculate/*` 中涉及 `api_gateway` import 的文件
- 必要时新增 `src/mold_cost/infrastructure/db/repositories/*`

开始前先做：

- 用扫描命令列出 `scripts` 下所有 `api_gateway.` 反向依赖
- 按数据库访问、repository 访问、配置访问、消息访问分类
- 优先处理靠近 pricing 和 feature 主链路的反向依赖

你的目标：

- 用 infrastructure repository 或 domain port 替掉 `api_gateway.database` 等接口层依赖
- 让 `jobs.py` 继续减薄，只保留协议转换、鉴权、响应映射
- 输出剩余反向依赖清单

不要做的事：

- 不改 `src/mold_cost/domain/pricing/search/*`
- 不改 `src/mold_cost/domain/pricing/calculators/*`
- 不改 `review_graph`

完成后请按以下格式回复：

1. 结果摘要
2. 修改文件
3. 关键决策
4. 验证
5. 风险与交接
