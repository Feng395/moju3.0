# 剩余阶段任务对照表

本文档统一使用 UTF-8 编码。  
更新时间：2026-04-05

## 状态说明
- `已落地`：主运行路径已经切到 `src/mold_cost`
- `收尾中`：主链完成，仍有少量 legacy 运行时或兼容入口
- `未完成`：尚未形成稳定的新实现

## 总览

| 编号 | 优先级 | 主题 | 当前状态 | 当前结论 |
| --- | --- | --- | --- | --- |
| R1 | P0 | application 去 `api_gateway` 依赖 | 已落地 | 主链 use case 已下沉到 `src/mold_cost` |
| R2 | P0 | interfaces/api 成为真实入口 | 已落地 | 新接口层已接管主入口 |
| R3 | P0 | review 去 legacy handler 运行时 | 收尾中 | `ConfirmHandler` 与 `ActionHandlerFactory` 已摘除，src-first recognizer 已落地，七类 review handlers 已迁入 `src`，常见 query/modification 识别已本地化，剩余复杂 recognizer fallback |
| R4 | P1 | pricing 主链与兼容层收尾 | 收尾中 | 主链已落地，剩余兼容类名与外部入口评估 |
| R5 | P1 | workflow durable backend 共享化 | 收尾中 | 已共享文件型 store，尚未升级为跨实例 backend |
| R6 | P1 | CAD / feature 算法本体迁移 | 收尾中 | feature 分析、batch 编排、持久化与红面查表入口已迁出，CAD split runtime、输入源解析、输入准备、子图编号编排、`.x_t` 导出准备与结果持久化边界已立，CAD 主流程与少量 feature 辅助仍在 legacy |
| R7 | P2 | golden 样本扩展 | 收尾中 | 基线已稳定，但覆盖面仍偏窄 |
| R8 | P2 | 兼容入口与诊断脚本清理 | 收尾中 | 仍有少量兼容入口可继续压缩 |

## 详细对照

| 编号 | 目标 | 当前已完成 | 主要残留 | 下一步动作 | 验收标准 |
| --- | --- | --- | --- | --- | --- |
| R3 | review 默认链只依赖 `src/mold_cost` | `review_data_loader`、`review_notifier`、默认确认执行器、src-first recognizer、handler runtime、`WEIGHT_PRICE_QUERY`、`QUERY_DETAILS` 与 `DATA_MODIFICATION` handlers 已收口到 `src`，且七类 review handlers 已下沉；常见 query/modification 规则识别也已迁入 `src` | 复杂 query / modification intent fallback 仍通过 `agents.intent_recognizer` 驱动 | 继续下沉 recognizer fallback，缩小 `legacy_review_handler_adapter` 到纯兼容壳 | review 修改/确认主链默认装配不再依赖 `agents.*` 运行时 |
| R4 | pricing 主链与外部入口彻底去 legacy agent 化 | `pricing_service` 已接管主链，worker/API fallback 已落地 | 兼容类名、MCP 外部入口仍需评估是否保留 | 盘点真实调用面，删除无效兼容壳或继续压缩职责 | pricing 主链与主入口不再需要 legacy agent 包装 |
| R5 | job/review 使用统一共享 durable backend | `FileCheckpointStore` 已被 job/review 共用 | 目前仍是本地文件型实现 | 设计并接入可跨实例恢复的 shared backend | 重启/跨实例后可从同一 backend 恢复相同 thread |
| R6 | CAD/feature 主链不再依赖 `scripts/*` | `feature_analysis_runtime.py`、`feature_batch_runtime.py`、`feature_persistence_runtime.py`、`slider_red_face_lookup_runtime.py`、`cad_split_runtime.py`、`cad_source_runtime.py`、`cad_prepare_runtime.py`、`cad_region_runtime.py`、`cad_split_persistence_runtime.py`、`cad_xt_export_runtime.py` 已落地 | `slider_red_face_updater`、`chaitu_process` 与相关 material line/converter/analyzer 主流程仍在 legacy | 优先继续拆 CAD split material line / analyzer 主流程，再评估 feature 滑块后处理是否继续下沉 | `domain.cad` 与 `domain.features` 主链不再依赖 legacy gateway 指向脚本 |
| R7 | 增强 workflow/pricing golden 覆盖 | 已有稳定 baseline | 样本数量与分支覆盖不足 | 新增 2 到 3 组不同零件与工艺样本 | `tests/golden` 覆盖多零件、多工艺、多价格分支 |
| R8 | 压缩兼容入口与诊断脚本 | 已清理一部分 worker / router / agent 包装 | 仍有可进一步删除的兼容壳 | 建立保留清单，逐步删除无效入口 | legacy 目录仅保留明确仍需的兼容入口 |

## 建议执行顺序
1. R3：继续拆 review recognizer / action handler 链
2. R6：继续拆 CAD split storage / db / algorithm runtime
3. R5：升级 shared durable backend
4. R7：补 golden 样本
5. R8：继续清理兼容入口

## 当前回归基线
- `pytest tests/unit tests/integration tests/golden -q`
- 结果：`176 passed`
