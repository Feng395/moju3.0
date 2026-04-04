# Golden Tests

`tests/golden` 用于保存第一版可复用业务回归样本。当前约定分为三层：

1. `pricing_bridge_inventory.json`
   pricing bridge 的模块清单，同时登记可执行的 golden 样本入口。
2. `samples/<sample_id>/manifest.json`
   样本清单，描述上传、拆图、特征识别、审核、计价五个阶段的输入、产物引用和阶段摘要。
3. `samples/<sample_id>/expected_summary.json` / `assertion_rules.json`
   期望摘要与断言规则，分别负责“看什么”和“怎么比”。

第一版样本目录规范：

```text
tests/golden/
├─ pricing_bridge_inventory.json
├─ test_pricing_bridge_golden.py
└─ samples/
   └─ workflow_pricing_m250286_p3/
      ├─ manifest.json
      ├─ expected_summary.json
      └─ assertion_rules.json
```

样本设计约束：

- `manifest.json` 必须覆盖 `upload -> cad_split -> feature_recognition -> review -> pricing` 顺序。
- 每个 stage 必须包含 `name`、`status`、`summary`。
- 可落库到仓库的产物用 `repo_path` 指向真实文件；无法入库的上传源文件只保留逻辑路径和元数据。
- `expected_summary.json` 只记录业务上稳定、值得回归的摘要，不记录高噪声细节。
- `assertion_rules.json` 只放可程序化执行的规则，例如阶段顺序、CSV 行数、关键字段、pricing bridge 模块数量。

`tools/diagnostics/golden_workflow.py` 提供样本加载、规则执行和 pause/resume 夹具组装能力，供 golden/integration 测试共享。
