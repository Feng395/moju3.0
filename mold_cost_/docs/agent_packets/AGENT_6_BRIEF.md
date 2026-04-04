# Agent 6 任务文档

角色：

- Golden / 集成测试与样本治理

目标：

- 把重构验证从 smoke test 推进到业务回归 test
- 建立第一版 golden 样本目录规范
- 为 workflow 暂停/恢复预留测试夹具

允许写入：

- `tests/golden/*`
- `tests/integration/*`
- `tests/e2e/*`
- `tools/diagnostics/*`

只读参考：

- `scripts/` 中现有样本和输出
- 当前 bridge 级 golden 测试

本轮必须完成：

- 设计第一版 golden 数据目录规范，覆盖“上传 -> 拆图 -> 特征识别 -> 审核 -> 计价”
- 把当前 bridge 级 golden 扩展为“样本清单 + 期望摘要 + 断言规则”
- 为 workflow 暂停/恢复设计最小测试夹具
- 将可复用的诊断逻辑沉到 `tools/diagnostics` 或 `tests/helpers`

禁止事项：

- 不大改业务代码
- 不改 domain bridge 实现

验收标准：

- 新增一份可复用的 golden 样本规范文档或夹具代码
- 至少有一组更接近真实业务的回归测试骨架

交付格式：

- 结果摘要
- 修改文件
- 关键决策
- 验证
- 风险与交接
