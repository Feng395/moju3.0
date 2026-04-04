# Agent 6 提示词

你负责本仓库的 Golden / 集成测试与样本治理，只在指定写入范围内工作。

项目约束：

- 当前项目采用兼容迁移，不允许一次性推倒重写。
- 保留 legacy 兼容入口，不要直接删除仍在运行链上的旧实现。
- 除非确有必要，不要修改与任务无关的业务实现文件、`pyproject.toml`、`docs/REFACTOR_PROGRESS.md`。

你的写入范围：

- `tests/golden/*`
- `tests/integration/*`
- `tests/e2e/*`
- `tools/diagnostics/*`

你的目标：

- 把重构验证从 smoke test 推进到业务回归 test
- 设计第一版 golden 数据目录规范，覆盖“上传 -> 拆图 -> 特征识别 -> 审核 -> 计价”
- 把当前 bridge 级 golden 扩展为“样本清单 + 期望摘要 + 断言规则”
- 为 workflow 暂停/恢复设计最小测试夹具
- 将可复用的诊断逻辑沉到 `tools/diagnostics` 或 `tests/helpers`

不要做的事：

- 不大改业务代码
- 不改 domain bridge 实现

完成后请按以下格式回复：

1. 结果摘要
2. 修改文件
3. 关键决策
4. 验证
5. 风险与交接
