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
