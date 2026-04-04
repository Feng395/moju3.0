# Integration Tests

该目录现在包含第一版 workflow 回归骨架，目标不是替代真实外部集成，而是把测试粒度从 smoke 提升到“业务阶段合同”。

当前约定：

- `fixtures/workflow_pause_resume_fixture.json`
  workflow 在 review 阶段暂停后的最小恢复夹具。
- `test_workflow_regression_scaffold.py`
  验证 pause/resume 夹具可序列化为 `JobState` / `ReviewState`，并可驱动 `ContinueJobUseCase` 的恢复入口。
