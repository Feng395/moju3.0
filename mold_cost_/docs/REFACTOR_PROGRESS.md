# 重构整合文档

本文档用于跟踪每个阶段的重构任务、目标和完成情况。

## 阶段 1：工程骨架与兼容层

目标：
- 建立 `src/mold_cost` 新包结构
- 收口配置、数据库、对象存储、消息队列入口
- 保留旧导入路径可用，避免一次性切换
- 为后续 LangChain/LangGraph 改造预留 workflow 落点

任务与完成情况：
- 已完成：新增 [pyproject.toml](/d:/workspace/project/python/mold3.0/mold_cost_/pyproject.toml)
- 已完成：新增 [src/mold_cost](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost) 基础包结构
- 已完成：统一配置入口 [settings.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/core/settings.py)
- 已完成：统一数据库入口 [session.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/db/session.py) 和 [asyncpg.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/db/asyncpg.py)
- 已完成：统一基础设施客户端 [minio_client.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/storage/minio_client.py)、[rabbitmq_client.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/messaging/rabbitmq_client.py)、[redis_client.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/messaging/redis_client.py)
- 已完成：旧模块兼容包装 [shared/config.py](/d:/workspace/project/python/mold3.0/mold_cost_/shared/config.py)、[shared/database.py](/d:/workspace/project/python/mold3.0/mold_cost_/shared/database.py)、[api_gateway/database.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/database.py)
- 已完成：建立工作流占位 [job_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/job_graph.py)、[review_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/review_graph.py)
- 已完成：建立 CAD 桥接落点 [split_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/cad/services/split_service.py)

阶段结果：
- 现有入口仍可运行
- 新旧结构已并存
- 后续迁移可以围绕 `application/domain/infrastructure` 继续收敛

## 阶段 2：任务主链路下沉到应用层

目标：
- 将任务创建、状态查询、快照查询、文件访问等主链路下沉到 `application/use_cases`
- 让 `api_gateway/services` 变成兼容外壳
- 为下一步把 orchestration 迁到 LangGraph 做准备

任务与完成情况：
- 已完成：新增任务创建用例 [create_job.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/create_job.py)
- 已完成：新增任务查询与快照查询用例 [get_job.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/get_job.py)
- 已完成：新增文件访问用例 [get_job_file.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/get_job_file.py)
- 已完成：新增继续执行用例 [continue_job.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/continue_job.py)
- 已完成：将 [job_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/services/job_service.py) 改为 use case 转发层
- 已完成：将 [file_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/services/file_service.py) 改为 use case 转发层
- 已完成：将 MinIO / RabbitMQ 在 use case 内改为懒加载，避免导入时立刻触发外部连接
- 未完成：`jobs router` 中 `continue_job` 的旧入口仍未完全替换，计划在 workflow 阶段统一迁移

阶段结果：
- 任务主链路已经从 service 下沉到了 application/use_cases
- API Gateway service 现在主要承担兼容层职责
- 下一阶段可以开始把继续执行、审核中断恢复、状态推进统一迁入 workflow

## 下一阶段建议

- 阶段 3：把 `continue_job`、审核中断恢复、编排状态推进迁到 `application/workflows/job_graph.py`
- 阶段 4：把 `interaction_agent` 相关逻辑拆分为 review workflow + LangChain chat/tool 层
- 阶段 5：逐步消除 `scripts/* -> api_gateway.*` 的反向依赖

## 阶段 3：工作流外壳落地

目标：
- 将任务和审核主流程统一收口到 `application/workflows`
- 让 worker 优先通过 workflow 执行，而不是直接依赖 legacy agent
- 为后续 LangGraph 持久化、interrupt、human-in-the-loop 留稳定入口

任务与完成情况：
- 已完成：将 [job_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/job_graph.py) 升级为任务工作流门面
- 已完成：将 [review_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/review_graph.py) 升级为审核工作流门面
- 已完成：新增审核用例集合 [review.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/review.py)
- 已完成：`ContinueJobUseCase` 改为通过 `job_graph` 执行
- 已完成：重写 [all_tasks_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/all_tasks_worker.py)，任务主流程开始通过 `job_graph`
- 已完成：重写 [review_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/review_worker.py)，审核启动开始通过 `review_graph`
- 已完成：新增新目录下的 worker 落点 [orchestrator_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/worker/orchestrator_worker.py)、[review_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/worker/review_worker.py)

阶段结果：
- 后台任务执行链已经统一走 workflow 外壳
- LangGraph 目前以最小门面形式存在，真实节点拆分可在后续继续推进
- 旧 agent 仍在内部复用，但对外依赖边界已经明显收敛

## 阶段 4：审核与聊天路由收口

目标：
- 让 review/chat 路由从直接依赖 `InteractionAgent` 改为依赖 use case
- 保留原有 HTTP 路径和返回结构，降低前端联调成本
- 继续削薄 router 层职责

任务与完成情况：
- 已完成：重写 [review_router.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/review_router.py)，统一转发到 review use case
- 已完成：重写 [chat_router.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/chat_router.py)，聊天状态和聊天执行统一走 `ReviewChatUseCase`
- 已完成：`review_graph` 增加 chat/chat_stream/check_lock 能力，承接审核交互入口
- 已完成：审核链路从 router 到 workflow 基本收口完成
- 未完成：`jobs.py` 中 continue 入口仍保留 legacy 实现，虽然后台 worker 已改走 workflow，但该路由仍建议在下一轮完全切换

阶段结果：
- router 层已明显变薄，主要职责变为协议适配和错误映射
- review/chat 入口不再直接 new legacy agent
- 下一轮可以集中清理 `jobs.py` 和更多 legacy 反向依赖

## 阶段 5：补齐领域桥接与去反向依赖

目标：
- 为 `features/pricing/review` 建立真正可落脚的 domain 包
- 逐步减少 `agents` 对 `scripts/*` 的直接依赖
- 为后续把 pricing/feature 逻辑继续下沉到领域层做准备

任务与完成情况：
- 已完成：补齐 [domain/features](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/features)、[domain/pricing](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing)、[domain/review](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review)
- 已完成：新增工艺规则匹配桥接 [process_rule_matcher.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/services/process_rule_matcher.py)
- 已完成：新增定价桥接服务 [pricing_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/services/pricing_service.py)
- 已完成：新增审核桥接服务 [review_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_service.py)
- 已完成：将 [cad_agent.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/cad_agent.py) 和 [cad_agent_local.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/cad_agent_local.py) 对 `process_rule_matcher` 的直接脚本依赖切到 domain 路径
- 未完成：`scripts/* -> api_gateway.*` 的反向依赖仍然存在较多，需要后续分批迁移

阶段结果：
- 新目录结构不再只有空壳，pricing/features/review 都已有桥接落点
- agent 到脚本层的直接耦合开始收缩
- 后续可以围绕这些桥接点逐步替换旧实现，而不是继续从 `scripts` 横向扩散

## 阶段 6：可用性验证与历史残留清理
目标：
- 验证重构后的主骨架可以在离线条件下真实导入、组装并执行最小流程
- 清理已确认无运行引用的历史备份文件
- 修正影响 Windows 控制台验证的日志编码噪音

任务与完成情况：
- 已完成：修正 [shared/unified_logging.py](/d:/workspace/project/python/mold3.0/mold_cost_/shared/unified_logging.py) 中的 emoji 初始化日志，降低 `gbk` 控制台下的编码告警
- 已完成：将 [api_gateway/routers/jobs.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/jobs.py) 的继续执行辅助函数桥接到 `ContinueJobUseCase`
- 已完成：新增离线冒烟测试 [test_refactor_smoke.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_refactor_smoke.py)
- 已完成：删除 4 个确认无引用的历史备份文件
- 已完成：运行 `pytest tests/unit/test_refactor_smoke.py -q` 做最小链路验证

阶段结果：
- 新的 `workflow/use case/router/service` 主骨架已能离线完成导入和最小委派执行
- `jobs continue` 的后台执行入口已经不再直接依赖旧 orchestrator 结果处理逻辑
- 第一批可安全删除的历史备份文件已经清掉

当前仍保留的遗留项：
- `review_graph` 当前仍以桥接方式复用 `InteractionAgent`，尚未完全替换为真实 LangGraph 节点
- 大量 `scripts/*` 仍承载旧业务实现，当前还被桥接层复用，不能直接整体删除；后续需要按模块迁移后再分批清理

## 阶段 7：特征识别入口收口与备份目录清理
目标：
- 将特征识别的外部调用入口统一收口到 `domain.features` 和 `application.use_cases`
- 修复本地 agent 与 legacy 特征识别脚本之间的进度回调不一致问题
- 清理确认无引用的历史备份目录

任务与完成情况：
- 已完成：重写 [recognition_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/features/services/recognition_service.py)，为 legacy 特征识别脚本提供统一领域桥接
- 已完成：新增 [features.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/features.py)，将特征重处理任务下沉到应用层用例
- 已完成：改造 [features.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/features.py)，路由层只做参数转发
- 已完成：改造 [cad_agent_local.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/cad_agent_local.py)，去掉对 `scripts.feature_recognition.feature_recognition` 的直接 import
- 已完成：扩展 [feature_recognition.py](/d:/workspace/project/python/mold3.0/mold_cost_/scripts/feature_recognition/feature_recognition.py)，为批处理函数补充可选 `progress_callback`
- 已完成：改造 [server.py](/d:/workspace/project/python/mold3.0/mold_cost_/mcp_services/cad_price_search_mcp/server.py)，MCP 特征识别入口改走领域服务桥接
- 已完成：补充 [test_feature_refactor.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_feature_refactor.py) 并扩展原冒烟测试
- 已完成：删除无引用历史备份目录 `scripts/backup_20260310_sheetline`

阶段结果：
- 特征识别对外主入口已经基本统一到新分层
- 本地脚本模式的进度回调链路已具备真实兼容性，不再依赖错误签名
- 又清掉了一批明确属于重构前残留的历史代码

当前仍保留的遗留项：
- `scripts/unified_api.py` 与 `scripts/cad_chaitu/unified_api.py` 仍保留旧式入口形态，且文件内存在历史编码/注释残留，后续需要单独清理
- 特征识别核心算法本体仍位于 `scripts/feature_recognition/feature_recognition.py`，当前属于“实现保留、入口收口”的阶段，尚未完全迁移出 legacy 目录

## 阶段 8：统一历史独立 API 入口
目标：
- 清理 `scripts/unified_api.py` 与 `scripts/cad_chaitu/unified_api.py` 中的大块历史实现
- 保留旧启动路径可用性，但将真实实现统一收口到 `src` 下的新接口模块
- 继续减少 legacy 独立服务实现分叉

任务与完成情况：
- 已完成：新增 [legacy_cad_api.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/api/legacy_cad_api.py)，统一承接旧 `/api/chaitu`、`/api/feature-recognition/batch`、`/api/feature-recognition/upload-feature-db` 等入口
- 已完成：将 [scripts/unified_api.py](/d:/workspace/project/python/mold3.0/mold_cost_/scripts/unified_api.py) 重写为兼容启动壳
- 已完成：将 [scripts/cad_chaitu/unified_api.py](/d:/workspace/project/python/mold3.0/mold_cost_/scripts/cad_chaitu/unified_api.py) 重写为兼容启动壳
- 已完成：补充 [interfaces/api/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/api/__init__.py) 并扩展冒烟测试，覆盖 legacy compatibility app 的导入验证
- 已完成：运行 `py_compile` 和 `pytest tests/unit/test_refactor_smoke.py tests/unit/test_feature_refactor.py -q` 验证兼容壳和新接口模块可用

阶段结果：
- 两个历史 `unified_api.py` 文件的旧实现代码已经被实际清空并替换为薄壳
- 旧独立启动方式仍可保留，但内部真实实现已经统一到新接口层
- 又消掉了一类典型的“历史大文件复制分叉”问题

当前仍保留的遗留项：
- `scripts/cad_chaitu` 包本身仍包含较重的 legacy 初始化链，当前兼容壳通过按文件加载已可使用，但整个包尚未完全轻量化
- `scripts/feature_recognition/feature_recognition.py` 与 `scripts/cad_chaitu/main.py` 仍承载核心 legacy 业务实现，后续如需继续清理，需要把算法本体逐步迁出 `scripts`

## 阶段 9：诊断脚本迁移到 tools
目标：
- 将明显属于诊断/工具性质的脚本从 `scripts/` 根目录迁到 `tools/diagnostics`
- 保留旧脚本路径的兼容调用方式，避免外部使用习惯被一次性打断
- 进一步区分“业务脚本”与“工程工具”职责边界

任务与完成情况：
- 已完成：新增 [tools/diagnostics/check_services.py](/d:/workspace/project/python/mold3.0/mold_cost_/tools/diagnostics/check_services.py)
- 已完成：新增 [tools/diagnostics/verify_integration.py](/d:/workspace/project/python/mold3.0/mold_cost_/tools/diagnostics/verify_integration.py)
- 已完成：新增 [tools/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/tools/__init__.py) 与 [tools/diagnostics/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/tools/diagnostics/__init__.py)
- 已完成：将 [scripts/check_services.py](/d:/workspace/project/python/mold3.0/mold_cost_/scripts/check_services.py) 改写为兼容壳
- 已完成：将 [scripts/verify_integration.py](/d:/workspace/project/python/mold3.0/mold_cost_/scripts/verify_integration.py) 改写为兼容壳
- 已完成：扩展 [test_refactor_smoke.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_refactor_smoke.py)，验证 tools 模块与旧壳都可导入
- 已完成：运行 `py_compile` 与 `pytest tests/unit/test_refactor_smoke.py tests/unit/test_feature_refactor.py -q` 验证迁移结果

阶段结果：
- `scripts/` 根目录又减少了一批非业务性质的历史实现
- 工具脚本职责开始从业务运行链中分离出来
- 旧命令仍可继续使用，但真实实现已经移到更合理的目录

当前仍保留的遗留项：
- `scripts/monitor_concurrency.py`、`scripts/monitor_locks.py`、`scripts/monitor_redis_websocket.py` 等监控类脚本仍在 `scripts/` 根目录
- `scripts/feature_recognition/feature_recognition.py` 与 `scripts/cad_chaitu/main.py` 仍是 legacy 算法主实现，后续如继续清理，需要以算法迁移为主，而不是直接删除
