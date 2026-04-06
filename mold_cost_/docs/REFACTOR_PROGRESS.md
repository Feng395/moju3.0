# 重构整合进度

本文档统一使用 UTF-8 编码。

## 当前结论
项目已经进入“主链迁移基本完成，剩余少量 legacy 运行时与共享基础设施收尾”的阶段。

目前已经明确落地的部分：
- `job_graph` 与 `review_graph` 均已运行在 LangGraph 工作流之上。
- `application / domain / infrastructure / interfaces` 四层已经成为真实执行路径，而不是占位目录。
- pricing 主链已完成从旧 agent 与 `scripts.search/*`、`scripts.calculate/*` 的迁移。
- API、worker、兼容 agent 的主调用路径已基本转向 `src/mold_cost`，其中 jobs/files 路由也已不再直接依赖 `api_gateway.services.*`。
- `job / snapshot / audit / chat_history / review` 这几条主链的默认 repository 访问已进一步向 `src` 收口。
- review 的 data loader、notifier、默认装配、确认执行链、src-first intent recognizer 与七类已迁入 handlers 已继续向 `src` 收口。
- feature 单文件分析、批处理编排、DB 读写 helper 与滑块红色面后处理已经迁入 `src/mold_cost`。

仍未完成的核心工作集中在：
- review 修改链中的少量复杂 handlers 与复杂意图识别 fallback 仍经由 legacy adapter 驱动。
- durable backend 已提供共享 SQLite backend 选项，但默认值与部署策略仍待收口。
- CAD split 主流程与 feature/CAD 的少量辅助能力仍停留在 `scripts/*`。
- golden 样本覆盖仍偏薄。

## 本轮新增进展

### 1. Feature 批处理与 DB helper 迁入 `src`
- 新增 `src/mold_cost/infrastructure/cad/feature_batch_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/feature_persistence_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/slider_red_face_update_runtime.py`
- `LegacyFeatureRecognitionGateway.batch_recognize()` 现在走 `src` 侧 batch runtime
- `LegacyFeatureRecognitionGateway.get_subgraphs()` / `save_features()` 现在走 `src` 侧 persistence runtime
- `LegacyFeatureRecognitionGateway.batch_recognize()` 现在直接注入 `src` 侧滑块红色面更新 runtime
- 新 runtime 已负责：
  - 查询待处理子图
  - 批量下载 DXF
  - 调用 `feature_analysis_runtime.analyze_dxf_features()`
  - 合并 `part_code` 后保存结果
  - 按条件触发滑块红面后处理
- `feature_persistence_runtime.py` 已负责：
  - 查询 `subgraphs` 并兼容 `xt_file_url` 列探测
  - upsert `features`
  - 初始化 `processing_cost_calculation_details`
  - 回写 `subgraphs.wire_process_note / wire_process`
- 新增 `src/mold_cost/infrastructure/cad/slider_red_face_lookup_runtime.py`
- `LegacyFeatureRecognitionGateway.save_features()` 与 `upload_feature_database()` 现在默认走 `src` 侧红面查表 runtime
- `scripts/feature_recognition/slider_red_face_updater.py` 已退化为兼容壳

### 2. Review 确认执行器从 `ConfirmHandler` 摘除
- 新增 `src/mold_cost/infrastructure/review/pending_action_store.py`
- 新增 `src/mold_cost/infrastructure/review/confirmation_executor.py`
- `build_default_review_change_applier()` 现在默认注入 `ReviewConfirmationExecutorAdapter`
- review workflow 默认确认链不再回到 `agents.confirm_handler`
- 当前确认执行器已在 `src` 内直接处理：
  - `DATA_MODIFICATION`
  - `FEATURE_RECOGNITION`
  - `PRICE_CALCULATION`
  - `WEIGHT_PRICE_CALCULATION`

### 3. CAD split gateway 建立 src-owned runtime 边界
- 新增 `src/mold_cost/infrastructure/cad/cad_split_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_process_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_analysis_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_source_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_prepare_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_region_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_material_line_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_split_persistence_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_xt_export_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_upload_runtime.py`
- 新增 `src/mold_cost/infrastructure/cad/cad_system.py`
- 新增 `src/mold_cost/infrastructure/cad/block_analyzer.py`
- 新增 `src/mold_cost/infrastructure/cad/number_extractor.py`
- 新增 `src/mold_cost/infrastructure/cad/text_processor.py`
- 新增 `src/mold_cost/infrastructure/cad/cutting_detector.py`
- `LegacyCadSplitGateway.split()` 现在通过 `run_cad_split()` 调度 legacy entrypoints
- `scripts/cad_chaitu/main.py` 现在直接委托 `cad_process_runtime.execute_cad_split_process()`
- `scripts/cad_chaitu/main.py` 现在通过 `src` runtime 处理子图识别/导出编排、DWG/PRT 来源解析、DWG 获取与 DXF 转换准备、子图编号解析/导出计划、板料线后处理、`.x_t` 导出准备、PRT 组件匹配与 Parasolid 导出、上传与结果落库统计
- `src/mold_cost/infrastructure/cad/material_line_integrator.py` 已承接板料线算法本体，`scripts/cad_chaitu/material_line_integrator.py` 已退化为兼容壳
- `src/mold_cost/infrastructure/cad/cad_system.py` 已承接 `CADAnalysisSystem` 分析系统本体，`scripts/cad_chaitu/cad_system.py` 已退化为兼容壳
- `src/mold_cost/infrastructure/cad/block_analyzer.py` 已承接 `OptimizedCADBlockAnalyzer` 分析器主体，`scripts/cad_chaitu/block_analyzer.py` 已退化为兼容壳
- `src/mold_cost/infrastructure/cad/number_extractor.py` 已承接图纸编号提取本体，`scripts/cad_chaitu/number_extractor.py` 已退化为兼容壳
- `src/mold_cost/infrastructure/cad/text_processor.py` 与 `cutting_detector.py` 已承接深层 analyzer helper，本地 `scripts/cad_chaitu/text_processor.py`、`cutting_detector.py` 已退化为兼容壳
- `scripts/cad_chaitu/__init__.py` 已改为惰性导出，不再在包导入阶段自动初始化 `main` / `init_managers`
- `src/mold_cost/infrastructure/db/cad_pool.py` 已改为惰性桥接，避免模块导入阶段直接触发 `scripts.cad_chaitu.database`
- 已补 `tests/unit/test_cad_split_refactor.py`、`test_cad_analysis_runtime.py`、`test_cad_source_runtime.py`、`test_cad_prepare_runtime.py`、`test_cad_region_runtime.py`、`test_cad_material_line_runtime.py`、`test_cad_process_runtime.py`、`test_cad_upload_runtime.py`、`test_cad_split_persistence_runtime.py`、`test_cad_xt_export_runtime.py` 锁定 CAD split runtime/gateway、子图识别/导出编排、来源解析、输入准备、子图编号编排、板料线后处理、主流程编排、上传与持久化边界

### 4. Review 默认装配继续收口
- `review_change_applier` 不再主动 import infrastructure fallback
- `interfaces/api/app.py` 已通过 `src` 侧 `action_handler_runtime` 初始化 review handler
- 新增 `src/mold_cost/infrastructure/review/action_handler_runtime.py`
- 新增 `src/mold_cost/infrastructure/review/intent_recognizer_runtime.py`
- 新增 `src/mold_cost/infrastructure/review/review_change_applier_runtime.py`
- 新增 `src/mold_cost/infrastructure/review/weight_price_query_handler.py`
- 新增 `src/mold_cost/infrastructure/review/display_view_builder.py`
- 新增 `src/mold_cost/infrastructure/review/completeness_validator.py`
- 新增 `src/mold_cost/infrastructure/db/repositories/review_repository.py`
- `src/mold_cost/infrastructure/db/repositories/chat_history_repository.py` 已改为 `src` 自有 SQL 实现，`create_session / add_message / get_session_history / get_recent_session_history / get_session_info / get_user_sessions / archive_session` 均不再默认代理 legacy repository
- `api_gateway/repositories/chat_history_repository.py` 已退化为 compat 壳，旧 `agents/api_gateway` 调用面会直接复用 `src` 侧聊天历史仓储实现
- 新增 `src/mold_cost/infrastructure/review/query_details_review_handler.py`
- 新增 `src/mold_cost/infrastructure/review/data_modification_review_handler.py`
- `DATA_MODIFICATION`、`FEATURE_RECOGNITION`、`PRICE_CALCULATION`、`QUERY_DETAILS`、`WEIGHT_PRICE_CALCULATION`、`GENERAL_CHAT`、`WEIGHT_PRICE_QUERY` 已切到 `src` 侧 review action handlers
- review 默认 intent recognizer 已改为 `src-first + legacy fallback`，并补齐上下文指代类 query/modification 识别、`wire_base / add_auto_material / nc_base / standard / wire_total / tooth_hole_time / nc_z / nc_c_b / nc_b_view` 等稳定 `query_type`，以及 `那材料费呢 / 热处理呢 / 那主视图时间呢 / 那线割总价呢` 这类短追问查询；现在连 `DIE-03 材料费 / DIE-03 重量 / DIE-03 线割基础费` 这类显式 ID 名词短语查询，以及 `设为 / 更改为 / 变更为 / 更新为 / 调到 / 调成 / 调整到` 这批高频修改表达也已本地化，同时本地 `QUERY_DETAILS` 泛问句命中面已收窄，避免把“这个系统能做什么？”误判成查询；legacy fallback 继续保持懒加载实例化
- review data loader 默认使用的 display view builder 与 completeness validator 也已迁入 `src`，`legacy_review_support_adapter.py` 仅保留兼容类名
- review 默认仓储访问也已切到 `SrcReviewRepository`，`review_repository_adapter.py` 仅保留兼容类名与延迟实例化包装
- `review_graph.py` 现在默认直接装配 `review_change_applier_runtime.py`，`legacy_review_handler_adapter.py` 已退化为纯 compat 转发壳

### 5. Workflow durable store 已抽为共享 backend 基础实现
- `job` 与 `review` 共用 `FileCheckpointStore`
- 新增 `src/mold_cost/infrastructure/workflows/sqlite_checkpoint_store.py`
- `JobFileCheckpointStore` / `ReviewFileCheckpointStore` 现在支持通过环境变量切换到共享 SQLite backend，并通过 namespace 共用同一份 checkpoint 数据库文件
- review durable snapshot 重启恢复链路已有集成测试覆盖

## 已完成里程碑

### 1. 工程骨架与基础设施
- 建立 `src/mold_cost` 分层结构
- 统一配置、数据库、MinIO、RabbitMQ、Redis 入口
- 旧入口保留为兼容壳，避免一次性切换
- `job_repository.py`、`snapshot_repository.py`、`audit_repository.py`、`chat_history_repository.py` 的默认实现也已迁入 `src/mold_cost/infrastructure/db/repositories`

### 2. Use Case 与接口层下沉
- 任务创建、查询、文件访问、继续执行等 use case 已落到 `application/use_cases`
- `src/mold_cost/interfaces/api` 已接管主 API 入口
- `src/mold_cost/interfaces/api/routers/jobs.py` 已切到 `src` use case 与本地 compat `JobService` 外壳，不再直接 import `api_gateway.services.job_service` / `file_service`
- `src/mold_cost/interfaces/api/dependencies/auth.py` 已提供本地 auth dependency 包装，`jobs.py` 与 `files.py` 不再直接 import `api_gateway.auth`
- `api_gateway/services/*` 大部分已退化为兼容包装

### 3. Job Workflow 迁移到 LangGraph
- `job_graph` 已从兼容外壳升级为真实 `StateGraph`
- `thread_id = job_id` 的 checkpoint / continue / resume 主链已打通
- job 侧已经具备 durable checkpoint 能力

### 4. Review Workflow 迁移到 LangGraph
- `review_graph` 已具备 `interrupt / resume` 主链
- review chat、state adapter、notifier 已继续收口
- review durable snapshot 恢复能力已补齐

### 5. Pricing 主链迁移
- `domain.pricing.search` 已完成迁移
- `domain.pricing.calculators` 已清零 `scripts.calculate.*` 直连
- `process_rule_matcher` 与 `pricing_service` 已迁入 `src`
- pricing worker / API fallback 已直接调用 `pricing_service`

### 6. Pricing 兼容层压缩
- `agents/pricing_agent.py` 与 `agents/pricing_agent_local.py` 已缩成兼容包装
- `mcp_services/cad_price_search_mcp/server.py` 已改为 registry-based dispatch

### 7. Feature 分析与持久化入口迁移
- `feature_analysis_runtime.py` 已接管 DXF 单文件分析 orchestration
- `feature_persistence_runtime.py` 已接管 feature DB 查询与落库 helper
- `slider_red_face_lookup_runtime.py` 已接管滑块红色面查表与缓存失效逻辑
- `slider_red_face_update_runtime.py` 已接管 `.x_t` 下载、NX 红色面提取与 `features.metadata` 写回
- `scripts/feature_recognition/__init__.py` 已改为惰性导出，避免重型导入副作用

## 当前剩余高优先级

### R3 Review 剩余 legacy 运行时
- 默认确认执行器已迁出 `ConfirmHandler`
- handler registry 已迁出 `ActionHandlerFactory`
- 默认 recognizer 已切为 `src-first + legacy fallback`
- 默认 change applier 装配已切到 `review_change_applier_runtime.py`
- 常见 `QUERY_DETAILS / DATA_MODIFICATION / WEIGHT_PRICE_QUERY` 规则识别已迁入 `src`，上下文指代类 query/modification、稳定 `query_type`、短追问查询、显式 ID 名词短语查询与高频修改同义词识别也已本地化；review data loader 默认 helper 不再依赖 `agents.data_view_builder` / `shared.validators.completeness_validator`，默认仓储访问也不再直接依赖 `api_gateway.repositories.review_repository`；现在连 `线割总价`、`牙孔费用`、`主视图/侧背/正面的背面`、`DIE-03 材料费 / 重量 / 线割基础费`、`把 DIE-03 的材质设为 S136 / 更改为 SKD11 / 长度调到 120`，以及 `那材料费呢 / 热处理呢 / 那主视图时间呢 / 那线割总价呢` 这类追问都不再默认回落 legacy recognizer
- 仍未迁出的部分：
  - `agents.intent_recognizer` 中复杂 query / modification fallback 分支
- 下一步应继续把复杂 recognizer fallback 分支下沉到 `src` adapter 或新 runtime，并评估是否还能继续压缩 Redis/legacy compat 外壳

### R5 Shared Durable Backend
- 当前已经具备共享接口 + 文件型实现，并新增可按配置启用的 SQLite 共享 backend
- 下一步应根据部署方式评估是否把 SQLite backend 设为默认，或继续外接更强的共享存储

### R6 CAD / Feature 算法本体迁移
- CAD 剩余：
  - 算法本体已基本迁完，剩余重点转向少量 CAD 兼容入口与 legacy glue 清理

### R7 Golden 样本扩展
- 现有基线可用，但样本数量仍偏少
- 需要补不同零件类型、工艺组合和价格分支

### R8 兼容入口持续清理
- `scripts/cad_chaitu/__init__.py` 已去掉包级初始化副作用
- `src` API jobs/files 路由已摘掉对 `api_gateway.services.*` / `api_gateway.auth` 的直接依赖
- `src` 侧 `job/snapshot/audit/chat_history` repository 已不再直接代理 `api_gateway.repositories.*`
- `api_gateway/repositories/chat_history_repository.py` 也已改为薄 compat 壳，不再保留第二份聊天历史 SQL 实现
- 仍有少量兼容入口与诊断脚本可继续压缩

## 当前回归基线
- `pytest tests/unit tests/integration tests/golden -q`
- 结果：`229 passed, 1 skipped`
