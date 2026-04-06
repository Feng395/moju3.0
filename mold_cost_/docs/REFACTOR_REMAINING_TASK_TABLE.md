# 剩余阶段任务对照表

本文档统一使用 UTF-8 编码。  
更新时间：2026-04-06

## 状态说明
- `已落地`：主运行路径已经切到 `src/mold_cost`
- `收尾中`：主链完成，仍有少量 legacy 运行时或兼容入口
- `未完成`：尚未形成稳定的新实现

## 总览

| 编号 | 优先级 | 主题 | 当前状态 | 当前结论 |
| --- | --- | --- | --- | --- |
| R1 | P0 | application 去 `api_gateway` 依赖 | 已落地 | 主链 use case 已下沉到 `src/mold_cost` |
| R2 | P0 | interfaces/api 成为真实入口 | 已落地 | 新接口层已接管主入口，jobs/files 路由也已切到 src use case 与本地 auth dependency 包装 |
| R3 | P0 | review 去 legacy handler 运行时 | 收尾中 | `ConfirmHandler`、`ActionHandlerFactory` 与默认 change applier 装配都已摘除，src-first recognizer 已落地，七类 review handlers 已迁入 `src`，常见 query/modification、上下文指代类 query/modification、稳定 query_type、短追问查询、显式 ID 名词短语查询与高频修改同义词识别已本地化，`线割总价 / 牙孔费用 / 主视图 / 侧背 / 正面的背面`、`DIE-03 材料费 / 重量 / 线割基础费`、`把 DIE-03 的材质设为 S136 / 更改为 SKD11 / 长度调到 120` 以及 `那材料费呢 / 热处理呢 / 那主视图时间呢 / 那线割总价呢` 等查询/修改都已本地化，legacy recognizer fallback 已懒加载，剩余复杂 recognizer fallback |
| R4 | P1 | pricing 主链与兼容层收尾 | 收尾中 | 主链已落地，剩余兼容类名与外部入口评估 |
| R5 | P1 | workflow durable backend 共享化 | 收尾中 | 已共享文件型 store，并新增可按配置启用的 SQLite 共享 backend；默认兼容模式仍保留文件型 |
| R6 | P1 | CAD / feature 算法本体迁移 | 收尾中 | feature 分析、batch 编排、持久化、红面查表与红面写回入口已迁出，CAD split runtime、主流程编排、子图识别/导出编排、输入源解析、输入准备、子图编号编排、板料线后处理、板料线算法本体、`CADAnalysisSystem` 本体、`OptimizedCADBlockAnalyzer` 本体、图纸编号提取本体、deep analyzer helper、`.x_t` 导出准备、PRT 组件匹配与 Parasolid 导出、上传与结果持久化边界已立，算法本体层面已基本收口，剩余转入少量兼容入口清理 |
| R7 | P2 | golden 样本扩展 | 收尾中 | 基线已稳定，但覆盖面仍偏窄 |
| R8 | P2 | 兼容入口与诊断脚本清理 | 收尾中 | `scripts/cad_chaitu/__init__.py` 已惰性化，src API jobs/files 路由也已摘掉对 `api_gateway.services.*` / `api_gateway.auth` 的直接依赖，`job/snapshot/audit/chat_history` repository 默认实现也已迁入 `src`，其中 legacy `chat_history_repository` 也已退化为 compat 壳，仍有少量兼容入口可继续压缩 |

## 详细对照

| 编号 | 目标 | 当前已完成 | 主要残留 | 下一步动作 | 验收标准 |
| --- | --- | --- | --- | --- | --- |
| R3 | review 默认链只依赖 `src/mold_cost` | `review_data_loader`、`review_notifier`、默认确认执行器、默认 change applier 装配、src-first recognizer、handler runtime、`WEIGHT_PRICE_QUERY`、`QUERY_DETAILS` 与 `DATA_MODIFICATION` handlers 已收口到 `src`，且七类 review handlers 已下沉；常见 query/modification 规则、上下文指代类 query/modification、`wire_base / add_auto_material / nc_base / standard / wire_total / tooth_hole_time / nc_z / nc_c_b / nc_b_view` 等稳定 query_type、`那材料费呢 / 热处理呢 / 那主视图时间呢 / 那线割总价呢` 这类短追问查询、`DIE-03 材料费 / 重量 / 线割基础费` 这类显式 ID 名词短语查询、`设为 / 更改为 / 变更为 / 更新为 / 调到 / 调成 / 调整到` 这类高频修改同义词，以及 data loader 默认使用的 display view/completeness helper 与 review repository 默认仓储访问也已迁入 `src`，legacy recognizer fallback 仅在真正 miss 时才懒加载 | 复杂 query / modification intent fallback 仍通过 `agents.intent_recognizer` 驱动 | 继续下沉 recognizer fallback，并评估 Redis/compat 壳的进一步压缩空间 | review 修改/确认主链默认装配不再依赖 `agents.*` 运行时 |
| R4 | pricing 主链与外部入口彻底去 legacy agent 化 | `pricing_service` 已接管主链，worker/API fallback 已落地；jobs/files API 路由已切到 `src` use case 与本地 auth dependency 包装 | 兼容类名、MCP 外部入口仍需评估是否保留 | 盘点真实调用面，删除无效兼容壳或继续压缩职责 | pricing 主链与主入口不再需要 legacy agent 包装 |
| R5 | job/review 使用统一共享 durable backend | `FileCheckpointStore` 已被 job/review 共用，且 `JobFileCheckpointStore` / `ReviewFileCheckpointStore` 已支持切到共享 SQLite backend，并通过 namespace 共用同一 checkpoint 数据库 | 默认兼容模式仍走文件型，生产默认值与部署方案尚待收口 | 评估是否切换 SQLite 为默认 backend，或继续接入外部共享存储 | 重启/跨进程后可从同一 backend 恢复相同 thread，且 job/review 命名空间互不污染 |
| R6 | CAD/feature 主链不再依赖 `scripts/*` | `feature_analysis_runtime.py`、`feature_batch_runtime.py`、`feature_persistence_runtime.py`、`slider_red_face_lookup_runtime.py`、`slider_red_face_update_runtime.py`、`cad_split_runtime.py`、`cad_process_runtime.py`、`cad_analysis_runtime.py`、`cad_source_runtime.py`、`cad_prepare_runtime.py`、`cad_region_runtime.py`、`cad_material_line_runtime.py`、`cad_upload_runtime.py`、`cad_split_persistence_runtime.py`、`cad_xt_export_runtime.py`、`material_line_integrator.py`、`cad_system.py`、`block_analyzer.py`、`number_extractor.py`、`text_processor.py`、`cutting_detector.py` 已落地，且 `.x_t` 的 PRT 组件匹配与 Parasolid 导出实现已迁入 `src` | 少量 CAD compatibility shell 与 legacy storage/db glue 仍待继续压缩 | 将 CAD 算法本体收尾结果并入兼容入口清理清单，后续主要转向 R8 | `domain.cad` 与 `domain.features` 主链默认不再依赖 legacy 算法脚本本体 |
| R7 | 增强 workflow/pricing golden 覆盖 | 已有稳定 baseline | 样本数量与分支覆盖不足 | 新增 2 到 3 组不同零件与工艺样本 | `tests/golden` 覆盖多零件、多工艺、多价格分支 |
| R8 | 压缩兼容入口与诊断脚本 | 已清理一部分 worker / router / agent 包装，且 `scripts/cad_chaitu/__init__.py` 已去掉导入即初始化副作用；`job/snapshot/audit/chat_history` repository 默认实现均已迁入 `src`，legacy `api_gateway.repositories.chat_history_repository` 也已缩成 compat 壳 | 仍有可进一步删除的兼容壳 | 建立保留清单，逐步删除无效入口 | legacy 目录仅保留明确仍需的兼容入口 |

## 建议执行顺序
1. R3：继续拆 review recognizer / action handler 链
2. R6：继续拆 CAD split analyzer 核心实现与算法本体
3. R5：升级 shared durable backend
4. R7：补 golden 样本
5. R8：继续清理兼容入口

## 当前回归基线
- `pytest tests/unit tests/integration tests/golden -q`
- 结果：`229 passed, 1 skipped`
