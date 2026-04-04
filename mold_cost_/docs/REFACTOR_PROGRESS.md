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
- 待开始：新增任务创建、查询、文件访问、继续执行用例
- 待开始：将 `api_gateway/services` 改为 use case 转发层
- 待开始：继续把 `jobs router` 直接耦合的继续执行逻辑迁到应用层并替换旧实现

阶段结果：
- 当前尚未开始，此处作为下一提交阶段的目标说明

## 下一阶段建议

- 阶段 3：把 `continue_job`、审核中断恢复、编排状态推进迁到 `application/workflows/job_graph.py`
- 阶段 4：把 `interaction_agent` 相关逻辑拆分为 review workflow + LangChain chat/tool 层
- 阶段 5：逐步消除 `scripts/* -> api_gateway.*` 的反向依赖
