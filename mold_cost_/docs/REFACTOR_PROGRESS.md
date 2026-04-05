# 重构整合文档

本文档用于跟踪每个阶段的重构任务、目标和完成情况。

基于现状，我的判断是：这个项目适合“渐进式重构”，不适合一次性推倒重写。你现在的业务脚本本身价值很高，重点不是重写算法，而是先把边界拆清，再把流程编排迁到 LangGraph。

现状诊断

目录和职责已经失衡。scripts 里其实承载了正式业务主链，当前大约有 115 个 Python 文件，而 api_gateway 有 60 个、agents 有 28 个，说明“脚本目录”已经不是脚本层了。
配置和基础设施重复。现在至少有三套配置/加载入口：shared/config.py、scripts/config_loader.py、api_gateway/config.py；数据库访问也至少三套：shared/database.py、api_gateway/database.py、scripts/cad_chaitu/database.py。
存在明显“反向依赖”。大量 scripts/search/*、scripts/calculate/*、scripts/process_rule_matcher.py 直接依赖 api_gateway.database，这意味着底层算法层反过来依赖接口层。
编排层还是手写状态流，不是图式工作流。当前主流程散落在 agents/orchestrator_agent.py、agents/cad_agent.py、agents/pricing_agent.py、api_gateway/routers/jobs.py 和 mcp_services/cad_price_search_mcp/server.py。
LangChain/LangGraph 只是“装了依赖”，还没真正落到主链路。requirements.txt
交互审核运行链耦合过重。agents/interaction_agent.py 直接粘着 repository、Redis、WebSocket、NLP、持久化，这会让后续扩展很难。
工程化基线偏弱。仓库里有多个 .env*、scripts/.env.example、feature_recognition.py.backup 这类历史文件，同时测试更多是诊断脚本，不是稳定回归测试。
重构总原则

先解耦，再图化，再智能化。
LangGraph 负责“长流程、状态、暂停/恢复、人审节点”。
LangChain 只负责“聊天、意图识别、工具调用、结构化输出”。
CAD/特征识别/价格计算这些确定性逻辑，继续保留为纯 Python 领域服务，不要为了“AI 化”强行改成 agent/tool。
建议目标结构

mold_cost_/
  src/mold_cost/
    core/
    domain/
      jobs/
      cad/
      features/
      pricing/
      review/
      files/
    application/
      use_cases/
      workflows/
        job_graph.py
        review_graph.py
      dto/
    infrastructure/
      db/
      storage/
      messaging/
      llm/
      cad/
      mcp/
    interfaces/
      api/
      worker/
      mcp/
      cli/
  tests/
    unit/
    integration/
    e2e/
    golden/
  legacy/
    scripts/
可执行重构计划书

Phase 0 基线冻结：先梳理真实主链路“上传 -> 拆图 -> 特征识别 -> 人工确认 -> 计价 -> 报表”，补一套 golden 样本和结果快照。验收：旧链路对固定样本可稳定复现。
Phase 1 目录规范化：建立 src/mold_cost 新骨架，把运行时代码、测试、诊断、备份、历史脚本彻底分离；scripts 逐步迁到 legacy/scripts。验收：入口不变，但新目录已能承接新增代码。
Phase 2 基础设施收敛：统一配置、日志、数据库、MinIO、RabbitMQ 客户端，删除 scripts.config_loader 这一支。验收：不再出现“同一能力三套实现”。
Phase 3 领域服务抽离：把 cad_chaitu、feature_recognition、search、calculate 提炼成领域服务和仓储接口。验收：API/worker 不再直接 import scripts/*。
Phase 4 LangGraph 主流程落地：把当前 orchestrator_agent.py 改为 job_graph。建议图为：load_job -> split_cad -> recognize_features -> validate_review_data -> interrupt(wait_user_confirm) -> apply_review_changes -> match_process_rules -> calculate_pricing -> finalize_job。这里 job_id 直接作为 thread_id。这部分是我结合你现有流程和官方文档后的建议边界。
Phase 5 LangChain 交互层重构：把 interaction_agent.py 拆成“review session service + chat agent + tool set + middleware”。验收：聊天路由只依赖应用层，不再直连 Redis/WebSocket/repository 细节。
Phase 6 接口层瘦身：API Gateway、Worker、MCP 都只做 adapter，不写业务；jobs.py 这种既管上传又管 legacy 又管继续执行的路由要拆开。验收：接口层只负责协议转换和鉴权。
Phase 7 并行迁移与切换：旧 orchestrator 和新 LangGraph 通过 feature flag 并行运行，先切 CAD 主流程，再切 review，再切 pricing。验收：新老结果在 golden 数据集上可比对。
Phase 8 测试与治理：补单元测试、集成测试、图工作流暂停/恢复测试、价格回归测试、性能压测。验收：CI 可稳定拦截回归，而不是靠人工诊断脚本。
你这次最该优先做的三件事

先统一 config/db/storage/message bus，这是所有后续重构的地基。
再把 scripts 中的正式业务逻辑抽成领域模块，保留算法不变。
最后再把“开始处理/等待确认/继续处理”这条链迁到 LangGraph。
不建议这么做

不建议一开始就把 100+ 个脚本全部包装成 LangChain tools。
不建议先拆微服务，当前更适合“单仓库分层 + 清晰边界”。
不建议先动 CAD/计价核心算法，先动壳层和编排层，风险最低。
官方参考，我用来判断 LangGraph 适合你这个项目的核心原因是：它天然适合长流程、持久化、人工确认后的暂停/恢复；而 LangChain 更适合聊天 agent 和工具调用。

LangGraph 概览: https://docs.langchain.com/oss/python/langgraph
LangGraph Durable Execution: https://docs.langchain.com/oss/python/langgraph/durable-execution
LangGraph Human-in-the-loop / Interrupts: https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
LangGraph Workflows and Agents: https://docs.langchain.com/oss/python/langgraph/workflows-agents
LangChain Agents: https://docs.langchain.com/oss/python/langchain/agents
如果你愿意，我下一步可以直接继续给你输出一版“按目录到文件级”的重构实施清单，把每个阶段要新建/迁移/删除的文件列出来。


 


实施清单
先按“兼容迁移”做，不要先大搬目录。旧入口先保留，只把实现逐步迁到新包里。

mold_cost_/
  pyproject.toml
  src/mold_cost/
    core/
      settings.py
      logging.py
      exceptions.py
      constants.py
    application/
      dto/
      use_cases/
        create_job.py
        get_job_status.py
        continue_job.py
        start_review.py
        handle_review_message.py
      workflows/
        job_state.py
        job_graph.py
        review_state.py
        review_graph.py
    domain/
      jobs/
      cad/
        services/
        ports.py
      features/
        services/
        ports.py
      pricing/
        search/
        calculators/
        services/
        ports.py
      review/
        services/
        ports.py
      files/
        services/
        ports.py
    infrastructure/
      db/
        session.py
        models.py
        repositories/
      storage/
        minio_client.py
      messaging/
        rabbitmq_client.py
        redis_client.py
      llm/
        langchain_factory.py
        prompts/
      cad/
        oda_converter.py
        nx_adapter.py
      mcp/
        tool_gateway.py
    interfaces/
      api/
        app.py
        routers/
      worker/
        orchestrator_worker.py
        review_worker.py
      mcp/
        server.py
      cli/
  tests/
    unit/
    integration/
    e2e/
    golden/
  legacy/
    scripts/
  tools/
    diagnostics/
旧文件到新文件映射

shared/config.py + scripts/config_loader.py -> src/mold_cost/core/settings.py
shared/database.py + api_gateway/database.py + scripts/cad_chaitu/database.py -> src/mold_cost/infrastructure/db/*
scripts/cad_chaitu/main.py -> src/mold_cost/domain/cad/services/split_service.py
scripts/cad_chaitu/converter.py -> src/mold_cost/infrastructure/cad/oda_converter.py
scripts/feature_recognition/* -> src/mold_cost/domain/features/services/*
scripts/search/* -> src/mold_cost/domain/pricing/search/*
scripts/calculate/* -> src/mold_cost/domain/pricing/calculators/*
scripts/process_rule_matcher.py -> src/mold_cost/domain/pricing/services/process_rule_matcher.py
agents/orchestrator_agent.py -> src/mold_cost/application/workflows/job_graph.py
agents/cad_agent.py -> src/mold_cost/application/use_cases/cad_pipeline.py 或 job_graph 节点
agents/pricing_agent.py -> src/mold_cost/application/use_cases/pricing_pipeline.py 或 job_graph 节点
agents/interaction_agent.py -> src/mold_cost/application/workflows/review_graph.py + domain/review/services/*
api_gateway/routers/jobs.py -> src/mold_cost/interfaces/api/routers/jobs.py
mcp_services/cad_price_search_mcp/server.py -> src/mold_cost/interfaces/mcp/server.py
第一批必须新建的文件

pyproject.toml
src/mold_cost/core/settings.py
src/mold_cost/core/logging.py
src/mold_cost/infrastructure/db/session.py
src/mold_cost/infrastructure/db/models.py
src/mold_cost/infrastructure/storage/minio_client.py
src/mold_cost/infrastructure/messaging/rabbitmq_client.py
src/mold_cost/infrastructure/messaging/redis_client.py
src/mold_cost/application/workflows/job_state.py
src/mold_cost/application/workflows/job_graph.py
src/mold_cost/application/workflows/review_state.py
src/mold_cost/application/workflows/review_graph.py
src/mold_cost/infrastructure/llm/langchain_factory.py
tests/unit/
tests/integration/
tests/golden/
legacy/scripts/
tools/diagnostics/
四阶段落地顺序

基础设施收口。
产出：统一 settings/logging/db/minio/rabbitmq/redis，旧文件改为薄包装；先解决配置和数据库三套实现并存的问题。
验收：scripts、agents、api_gateway 不再直接各自维护一套配置和数据库客户端。

领域服务抽离。
产出：把 cad_chaitu、feature_recognition、search、calculate 提炼到 domain；旧 scripts/* 只保留兼容调用。
验收：domain 不再 import api_gateway.*；尤其要消掉现在 scripts/* -> api_gateway.database 的反向依赖。

LangGraph 主流程替换。
产出：job_graph.py 接管上传后主链，状态建议只保留 job_id/dwg_path/prt_path/subgraph_ids/feature_summary/review_status/pricing_summary/errors/artifacts。
节点建议：load_job -> split_cad -> recognize_features -> match_process_rules -> interrupt(wait_confirm) -> calculate_pricing -> finalize_job
验收：原 workers/orchestrator_worker.py 只负责启动 graph，不再持有业务编排逻辑。

审核聊天链重构。
产出：review_graph.py 负责“加载审查数据 -> 检查完整性 -> 生成建议 -> 等待用户修改 -> 应用修改 -> 继续主流程”；LangChain 只用于意图识别、结构化输出、聊天工具调用。
验收：原 agents/interaction_agent.py 被拆成小服务，API 路由不再直连 Redis/WebSocket/repository 细节。

必须遵守的依赖规则

interfaces 只能调用 application，不能直接调 scripts。
application 只编排流程，不写 SQL，不写 MinIO/RabbitMQ 细节。
domain 只放业务规则和算法，不得 import FastAPI、Redis、RabbitMQ、LangChain。
infrastructure 只实现 ports，不放业务判断。
LangGraph 节点只做状态推进，不重写你现有 CAD/计价算法。
建议你现在就开的任务单

任务 1：建立 src/mold_cost 骨架和 pyproject.toml
任务 2：合并配置与数据库访问层
任务 3：迁移 cad_chaitu 为 domain.cad
任务 4：迁移 feature_recognition 为 domain.features
任务 5：迁移 search/calculate 为 domain.pricing
任务 6：实现 job_graph
任务 7：实现 review_graph
任务 8：把旧入口改成兼容包装
任务 9：补 golden 回归测试
任务 10：删除 .backup、诊断脚本散落、重复 .env 策略


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

## 阶段 10：对照清单补齐骨架文件
目标：
- 按实施清单继续补齐新包结构中尚缺的目录、端口定义和兼容入口文件
- 为后续真正的算法迁移和 LangGraph 深化改造预留稳定落点
- 保持兼容迁移策略，不直接删除仍在运行链上的核心 legacy 实现

任务与完成情况：
- 已完成：补齐兼容用例文件 [get_job_status.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/get_job_status.py)、[start_review.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/start_review.py)、[handle_review_message.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/handle_review_message.py)
- 已完成：补齐领域骨架 [domain/jobs/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/jobs/__init__.py)、[domain/files/ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/files/ports.py)、[domain/review/ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/ports.py)
- 已完成：补齐定价子目录 [pricing/search/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/__init__.py)、[pricing/calculators/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/calculators/__init__.py)
- 已完成：补齐基础设施骨架 [nx_adapter.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/cad/nx_adapter.py)、[tool_gateway.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/mcp/tool_gateway.py)、[prompts/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/llm/prompts/__init__.py)、[repositories/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/db/repositories/__init__.py)
- 已完成：补齐接口层入口 [app.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/api/app.py)、[routers/jobs.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/api/routers/jobs.py)、[interfaces/mcp/server.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/mcp/server.py)、[interfaces/cli/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/cli/__init__.py)
- 已完成：补齐 [legacy/scripts/README.md](/d:/workspace/project/python/mold3.0/mold_cost_/legacy/scripts/README.md) 以及测试目录说明文件
- 已完成：扩展冒烟测试，验证新增 wrapper/port/app 级骨架可导入

阶段结果：
- 这份实施清单中的大部分骨架文件已经在仓库内落地
- 后续迁移工作可以围绕这些稳定新路径继续推进，而不是再往旧目录新增实现
- 当前策略仍保持“新路径先建好，旧实现逐步替换”的兼容迁移方式

当前仍保留的遗留项：
- `scripts/cad_chaitu/main.py` 与 `scripts/feature_recognition/feature_recognition.py` 仍是核心 legacy 算法落点
- `scripts/search/*` 与 `scripts/calculate/*` 目前主要完成了目录级承接，尚未完成逐文件迁移到 `domain/pricing/search` 和 `domain/pricing/calculators`
- `job_graph` / `review_graph` 目前仍是 workflow 外壳，尚未完全拆成真实 LangGraph 节点图

## 阶段 11：收口 pricing 直接脚本依赖
目标：
- 将 `scripts.search` 和 `scripts.calculate` 的外部调用入口统一收口到 `domain.pricing`
- 缩小 `mcp` 服务与本地 `pricing agent` 对 legacy 脚本路径的直接依赖面
- 为后续按模块迁移 pricing 算法实现打下桥接层基础

任务与完成情况：
- 已完成：重写 [pricing/search/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/__init__.py)，统一桥接 legacy 搜索模块
- 已完成：重写 [pricing/calculators/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/calculators/__init__.py)，统一桥接 legacy 计算模块
- 已完成：改造 [server.py](/d:/workspace/project/python/mold3.0/mold_cost_/mcp_services/cad_price_search_mcp/server.py)，MCP 侧改走 `domain.pricing.search` 与 `domain.pricing.calculators`
- 已完成：改造 [pricing_agent_local.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/pricing_agent_local.py)，本地 pricing agent 不再直接 import `scripts.search` / `scripts.calculate`
- 已完成：扩展 [test_refactor_smoke.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_refactor_smoke.py)，验证新的 pricing bridge 可导入
- 已完成：运行 `py_compile` 与 `pytest tests/unit/test_refactor_smoke.py tests/unit/test_feature_refactor.py -q` 验证迁移结果

阶段结果：
- pricing 相关外层入口已开始统一经由 `domain.pricing` 访问 legacy 实现
- legacy 搜索/计算脚本依赖面明显缩小，后续可以按模块逐步内迁，而不是继续新增散点引用

当前仍保留的遗留项：
- `scripts/search/*` 与 `scripts/calculate/*` 的算法本体仍位于 legacy 目录
- `price_weight.py` 等少量 legacy 文件内部仍可能存在反向脚本引用，后续需要逐文件清理

## 阶段 12：补齐 pricing 逐模块桥接与第一批 golden 回归
目标：
- 将 `domain/pricing/search` 与 `domain/pricing/calculators` 从包级桥接推进到逐模块桥接
- 为 pricing 迁移建立更细粒度的新路径落点
- 开始补第一批 `golden` 回归测试，先覆盖结构稳定的桥接清单

任务与完成情况：
- 已完成：为 `search` 目录下的关键 legacy 模块批量生成逐文件桥接，如 [base_itemcode_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/base_itemcode_search.py)、[total_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/total_search.py)
- 已完成：为 `calculators` 目录下的关键 legacy 模块批量生成逐文件桥接，如 [price_total.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/calculators/price_total.py)、[judgment.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/calculators/judgment.py)
- 已完成：更新 [pricing/search/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/__init__.py) 与 [pricing/calculators/__init__.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/calculators/__init__.py)，优先暴露 bridge 模块
- 已完成：新增第一批 golden 基线 [pricing_bridge_inventory.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/pricing_bridge_inventory.json)
- 已完成：新增 golden 测试 [test_pricing_bridge_golden.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/test_pricing_bridge_golden.py)
- 已完成：运行 `pytest tests/unit/test_refactor_smoke.py tests/unit/test_feature_refactor.py tests/golden/test_pricing_bridge_golden.py -q`，结果为 `8 passed`

阶段结果：
- `domain.pricing` 已经不再只是目录级承接，而是开始具备逐文件迁移能力
- 第一批 golden 回归测试已落地，后续可以继续引入真实样本快照和价格结果快照

当前仍保留的遗留项：
- 这些 bridge 文件内部仍转发到 `scripts/search/*` 与 `scripts/calculate/*`，算法本体尚未迁出 legacy 目录
- 真实业务 golden 样本和数值回归还未建立，目前 golden 仅覆盖桥接清单结构

## 阶段 13：Job Workflow 显式状态流深化
目标：
- 将 `job_graph` 从最小 facade 推进为显式状态推进工作流
- 固化 `JobState` 的稳定字段面，为后续 LangGraph checkpoint / interrupt 做准备
- 统一 worker 与 continue-job 路径的 workflow 入口

任务与完成情况：
- 已完成：扩展 [job_state.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/job_state.py)，固化 `job_id / dwg_path / prt_path / subgraph_ids / feature_summary / review_status / pricing_summary / errors / artifacts` 等状态字段
- 已完成：重写 [job_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/job_graph.py)，显式声明 `load_context -> validate_* -> execute_* -> collect_post_run -> finalize` 步骤
- 已完成：为 `job_graph` 增加 `checkpoint_config`、`build_checkpoint`、`serialize_state` 等接口，预留后续持久化落点
- 已完成：改造 [continue_job.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/continue_job.py)，continue 优先走统一 job queue，消息失败时退回本地 workflow
- 已完成：重写 [workers/orchestrator_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/orchestrator_worker.py) 与 [workers/all_tasks_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/all_tasks_worker.py)，worker 不再自行持有编排细节

阶段结果：
- `job_graph` 已不再是简单 passthrough，而是具备显式状态推进、checkpoint 元数据和 start/continue 统一入口的工作流 facade
- 后续接入真实 LangGraph 时，可以围绕现有 `JobState` 与步骤边界平移，而不需要再次从 worker 回收状态逻辑

当前仍保留的遗留项：
- `job_graph` 仍然在执行节点内复用 legacy orchestrator，尚未完全切换到真实 LangGraph runtime
- checkpoint 目前仍是本地 envelope，尚未落到真实持久化后端

## 阶段 14：Review Workflow 服务边界拆分
目标：
- 将 `review_graph` 从“包一层 InteractionAgent”推进为可拆分的 workflow
- 拆出 review session、state store、data loader、chat executor、change applier、notifier 边界
- 保持 review/chat 路由协议兼容

任务与完成情况：
- 已完成：扩展 [review_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/review_graph.py)，显式落地 `load_review_data / check_completeness / generate_review_prompt_or_suggestion / wait_user_message / apply_review_change / confirm_and_resume` 节点边界
- 已完成：补齐 review 领域端口 [ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/ports.py)
- 已完成：新增 review 服务适配器 [review_session_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_session_service.py)、[review_state_adapter.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_state_adapter.py)、[review_data_loader.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_data_loader.py)、[review_chat_execution_adapter.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_chat_execution_adapter.py)、[review_change_applier.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_change_applier.py)、[review_notifier.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_notifier.py)
- 已完成：保持 [review.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/review.py) 与现有 review/chat 路由兼容，外部协议未破坏

阶段结果：
- `review_graph` 已经从“直接 new InteractionAgent”推进到“workflow + 多适配器”结构
- 会话锁、状态存储、数据加载、聊天执行、变更应用、推送副作用的边界已经清晰收口

当前仍保留的遗留项：
- chat executor / change applier / notifier 仍桥接 `InteractionAgent`，尚未替换为完全独立实现
- review state / session 目前仍默认依赖 Redis 适配器

## 阶段 15：CAD 与 Feature 入口继续收口
目标：
- 让 CAD 拆图与特征识别的外部调用入口继续集中到领域服务
- 减少接口层直接触达 legacy 脚本
- 为 workflow 调用提供稳定的领域服务 API

任务与完成情况：
- 已完成：扩展 [domain/cad/ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/cad/ports.py) 与 [domain/features/ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/features/ports.py)
- 已完成：增强 [split_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/cad/services/split_service.py) 与 [recognition_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/features/services/recognition_service.py)，使外部入口统一走领域服务
- 已完成：新增 legacy 基础设施网关 [legacy_cad_split_gateway.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/cad/legacy_cad_split_gateway.py) 与 [legacy_feature_recognition_gateway.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/cad/legacy_feature_recognition_gateway.py)
- 已完成：收敛 [legacy_cad_api.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/api/legacy_cad_api.py) 与 [features.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/features.py) 的领域服务入口
- 已完成：继续改造 [server.py](/d:/workspace/project/python/mold3.0/mold_cost_/mcp_services/cad_price_search_mcp/server.py)，MCP 的 CAD / feature 调用边界进一步收口

阶段结果：
- CAD 拆图与特征识别的 API / MCP 入口已经更稳定地收敛到 `domain.cad` 与 `domain.features`
- workflow 侧后续接入时，可以直接面向领域服务，而不是继续新增脚本级散点调用

当前仍保留的遗留项：
- `scripts/cad_chaitu/main.py` 与 `scripts/feature_recognition/feature_recognition.py` 仍承载算法本体
- 网关层目前仍是 legacy 实现包装，不是全新领域实现

## 阶段 16：反向依赖清理与 jobs 路由瘦身
目标：
- 清理 pricing / process matcher 主链上的 `scripts/* -> api_gateway.*` 反向依赖
- 继续削薄 `jobs.py`
- 将脚本侧数据库访问统一收口到 infrastructure 仓储出口

任务与完成情况：
- 已完成：新增脚本数据库兼容出口 [script_db.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/db/repositories/script_db.py)
- 已完成：批量改造 `scripts/search/*`、`scripts/calculate/*` 与 [process_rule_matcher.py](/d:/workspace/project/python/mold3.0/mold_cost_/scripts/process_rule_matcher.py)，不再通过 `api_gateway.*` 访问数据库
- 已完成：重写 [jobs.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/jobs.py)，继续压缩 legacy helper 和编排细节
- 已完成：同步调整 [job_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/services/job_service.py) 与 [job_repository.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/repositories/job_repository.py)，路由层继续收口为协议转换 + use case / repository 调用
- 已完成：在 pricing bridge 基线中验证 `scripts/search/*` 与 `scripts/calculate/*` 对 `api_gateway.*` 的残留依赖已清空

阶段结果：
- pricing / process matcher 这条主链上的脚本反向依赖已经从 `api_gateway.*` 切走
- `jobs` 路由继续减薄，继续执行入口统一走 `JobService.submit_continue_job`

当前仍保留的遗留项：
- `scripts/monitor_redis_websocket.py` 仍存在对 `api_gateway.*` 的依赖
- 其它未纳入本轮范围的 legacy 脚本后续仍需继续排查

## 阶段 17：Workflow Golden 样本与暂停/恢复回归骨架
目标：
- 将测试从 smoke 提升到业务阶段合同回归
- 建立第一版 workflow 样本三件套
- 为 review 阶段暂停 / continue 恢复补齐最小夹具

任务与完成情况：
- 已完成：新增 [tests/golden/README.md](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/README.md)，明确 golden 三层结构
- 已完成：新增第一版 workflow 样本 [manifest.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/samples/workflow_pricing_m250286_p3/manifest.json)、[expected_summary.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/samples/workflow_pricing_m250286_p3/expected_summary.json)、[assertion_rules.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/samples/workflow_pricing_m250286_p3/assertion_rules.json)
- 已完成：新增 golden / integration 共享工具 [golden_workflow.py](/d:/workspace/project/python/mold3.0/mold_cost_/tools/diagnostics/golden_workflow.py)
- 已完成：新增 pause/resume 夹具 [workflow_pause_resume_fixture.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/integration/fixtures/workflow_pause_resume_fixture.json) 与 [test_workflow_regression_scaffold.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/integration/test_workflow_regression_scaffold.py)
- 已完成：同步更新 smoke / golden 测试，适配新的 review workflow 和清理后的 pricing 依赖基线
- 已完成：运行 `pytest tests/unit tests/integration tests/golden -q`，结果为 `16 passed`

阶段结果：
- 仓库里已经存在第一版可复用 workflow golden 样本与 pause/resume 回归骨架
- 集成验证粒度从“能导入”推进到了“阶段合同、样本清单、恢复夹具”层面

当前仍保留的遗留项：
- 当前 workflow golden 仍以阶段摘要、样本清单和结构性断言为主，尚未覆盖完整数值级计价回归
- 暂停/恢复夹具目前仍是模板化恢复快照，尚未接入真实 LangGraph checkpoint 存储

## 阶段 18：Pricing 第一批真实 Search 模块迁移
目标：
- 将 `domain.pricing.search` 中第一批低风险 bridge 模块迁移为真实领域实现
- 不再只是 `import_module("scripts.search.*")` 转发
- 为后续 calculator / matcher 迁移沉淀统一查询仓储与服务

任务与完成情况：
- 已完成：扩展 [ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/ports.py)，补齐 pricing snapshot 查询端口
- 已完成：新增 [price_snapshot_search_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/services/price_snapshot_search_service.py)，统一封装 search 服务入口
- 已完成：新增 [pricing_snapshot_repository.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/db/repositories/pricing_snapshot_repository.py)，从 `job_price_snapshots` 承接真实查询
- 已完成：将 [density_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/density_search.py)、[heat_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/heat_search.py)、[material_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/material_search.py)、[nc_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/nc_search.py)、[wire_standard_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/wire_standard_search.py) 从 bridge 推进为真实实现
- 已完成：更新 [pricing_bridge_inventory.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/pricing_bridge_inventory.json) 与 [test_pricing_bridge_golden.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/test_pricing_bridge_golden.py)，使 golden inventory 能区分“真实实现”与“legacy 转发”
- 已完成：新增 [test_pricing_search_refactor.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_pricing_search_refactor.py)，验证第一批 search 模块的行为边界

阶段结果：
- `domain.pricing.search` 已经不再是纯 bridge 目录，第一批真实查询模块已落在新路径
- pricing 迁移第一次从“目录收口”推进到了“真实领域实现”
- 后续 calculator / process matcher 可以复用同一套仓储与 service 边界

当前仍保留的遗留项：
- 大部分 pricing calculator 仍然桥接到 `scripts/calculate/*`
- 第一批真实 search 仍依赖当前 `job_price_snapshots` 表结构，后续若做更细粒度领域模型还需继续抽象

## 阶段 19：CAD 与 Feature 服务契约硬化
目标：
- 把 CAD 拆图与特征识别服务的输入 / 输出 / 错误 / artifact 结构固化下来
- 让 workflow、API、worker 统一面向领域服务契约，而不是继续吞吐 legacy 原始返回值
- 为后续真正迁出算法本体做契约准备

任务与完成情况：
- 已完成：扩展 [domain/cad/ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/cad/ports.py) 与 [domain/features/ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/features/ports.py)，统一 summary / error / artifact 结构
- 已完成：增强 [split_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/cad/services/split_service.py)，使 CAD 侧对外返回稳定服务结果
- 已完成：重写 [recognition_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/features/services/recognition_service.py)，将 batch / reprocess / upload-feature-db 等能力收口到同一服务契约
- 已完成：补齐 [legacy_cad_split_gateway.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/cad/legacy_cad_split_gateway.py) 等基础设施网关，明确 legacy 适配层边界
- 已完成：同步调整 [features.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/features.py) 与 [legacy_cad_api.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/api/legacy_cad_api.py)，使接口层统一走领域服务
- 已完成：新增 [test_service_contracts.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/features/services/test_service_contracts.py)，校验服务契约的稳定性

阶段结果：
- CAD / feature 的调用面已经开始从“直接跑脚本”转成“面向契约的领域服务”
- workflow 与接口层后续接入时，可以稳定读取 summary / errors / artifacts，而不是继续适配散乱返回值

当前仍保留的遗留项：
- `scripts/cad_chaitu/main.py` 与 `scripts/feature_recognition/feature_recognition.py` 仍然承载核心算法本体
- 现有 gateway 仍主要是 legacy 包装层，不是全新的领域实现

## 阶段 20：Job LangGraph Runtime 与 Checkpoint 恢复链路落地
目标：
- 将 `job_graph` 从 workflow facade 推进为真实 LangGraph runtime
- 让 `thread_id = job_id`、checkpoint config、resume 链路真正参与执行
- 保持 start / continue 对外契约兼容

任务与完成情况：
- 已完成：重写 [job_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/job_graph.py)，使用 `StateGraph` 落地 `load_context -> validate_* -> execute_* -> collect_post_run -> finalize`
- 已完成：扩展 [job_state.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/job_state.py)，继续稳定 checkpoint / thread / resume 相关状态字段
- 已完成：将 `checkpoint_config`、`build_checkpoint`、`get_checkpoint_snapshot` 接到真实 LangGraph config 与 snapshot 读取逻辑
- 已完成：改造 [continue_job.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/continue_job.py)，continue 路径优先恢复同一 `job_id` 的图状态
- 已完成：同步 [orchestrator_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/worker/orchestrator_worker.py)、[workers/orchestrator_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/orchestrator_worker.py)、[all_tasks_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/all_tasks_worker.py)，worker 继续只面向 workflow
- 已完成：新增 [test_job_graph_checkpoint_resume.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/integration/test_job_graph_checkpoint_resume.py)，验证 `thread_id = job_id`、checkpoint 递进与 resume 恢复链路

阶段结果：
- `job_graph` 已不再只是“显式状态流 facade”，而是真正运行在 LangGraph 上
- start / continue 已经围绕同一 thread 与 checkpoint 执行，后续 durable execution 可以直接接持久化后端

当前仍保留的遗留项：
- 默认 checkpointer 仍是内存实现，尚未接入真实 durable checkpoint backend
- 节点内部仍复用现有 orchestrator / 领域服务实现，尚未继续细分为更纯的独立节点职责

## 阶段 21：Review LangGraph 主链落地并缩小 InteractionAgent 桥接
目标：
- 将 `review_graph` 从“workflow + adapters”推进为真实 LangGraph runtime
- 把 interrupt / resume 落到 review 主链
- 继续缩小 review 链对 legacy `InteractionAgent` 的依赖

任务与完成情况：
- 已完成：重写 [review_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/review_graph.py)，使用 `StateGraph` 落地 `load_review_data / check_completeness / generate_review_prompt_or_suggestion / wait_user_message / apply_review_change / confirm_and_resume`
- 已完成：扩展 [review_state.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/review_state.py)，补齐 checkpoint 与节点状态字段
- 已完成：收敛 [review_change_applier.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_change_applier.py)、[review_chat_execution_adapter.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_chat_execution_adapter.py)、[review_notifier.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_notifier.py)，缩小对 `InteractionAgent` 私有实现的穿透
- 已完成：同步 [ports.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/ports.py) 与 [review_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/review_worker.py)，让 review worker 继续只依赖 workflow
- 已完成：扩展 [test_refactor_smoke.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_refactor_smoke.py)，验证 review interrupt / resume 主链

阶段结果：
- `review_graph` 已经真正运行在 LangGraph 上，并具备 interrupt / resume 主链
- review 主流程的状态推进已不再依赖 `InteractionAgent` 直接持有整条流程
- chat / change / notifier 的 legacy 依赖面进一步缩小

当前仍保留的遗留项：
- review 的 state/session 默认仍依赖 Redis 适配器
- chat / change / notifier 仍存在兼容性 `InteractionAgent*` 适配器，尚未彻底替换为完全独立实现
- review graph 默认 checkpointer 仍是内存实现，尚未接 durable backend

## 阶段 22：Workflow Golden 数值级 Pricing 回归扩展
目标：
- 将 workflow golden 从结构回归推进到数值级 pricing 回归
- 为 Job / Review LangGraph 的 pause-resume 链路补更真实的样本断言
- 让后续 pricing 真正迁模块时有更可靠的业务基线

任务与完成情况：
- 已完成：扩展 [assertion_rules.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/samples/workflow_pricing_m250286_p3/assertion_rules.json)、[expected_summary.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/samples/workflow_pricing_m250286_p3/expected_summary.json)、[manifest.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/samples/workflow_pricing_m250286_p3/manifest.json)，补齐 pricing baseline 断言
- 已完成：增强 [test_pricing_bridge_golden.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/test_pricing_bridge_golden.py)，对 `DIE-06` 样本增加与 legacy calculator 对齐的数值级回归
- 已完成：同步 [workflow_pause_resume_fixture.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/integration/fixtures/workflow_pause_resume_fixture.json) 与 [test_workflow_regression_scaffold.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/integration/test_workflow_regression_scaffold.py)，补强 pause / resume 固件断言
- 已完成：增强 [golden_workflow.py](/d:/workspace/project/python/mold3.0/mold_cost_/tools/diagnostics/golden_workflow.py)，使 golden 样本和业务结果校验更贴近真实工作流
- 已完成：运行 `pytest tests/unit tests/integration tests/golden -q`，结果为 `24 passed`

阶段结果：
- workflow golden 已经从“结构级 scaffold”推进到“带真实 pricing baseline 的数值级回归”
- Job / Review LangGraph 与 pricing 第一批真实模块迁移已有统一回归面

当前仍保留的遗留项：
- 当前数值级 golden 仍以单样本、单价基线为主，尚未覆盖更多零件类型与价格分支
- golden baseline 仍部分依赖 legacy calculator 作为参照，后续需要逐步过渡到新实现自证

## 阶段 23：Pricing 第二批 Search 模块迁移
目标：
- 继续把 `domain.pricing.search` 从 bridge 推进到真实实现
- 清空第二批低风险 snapshot / aggregation search 模块的 legacy 转发
- 收缩 `next_extract_candidates`，把下一轮聚焦到更少的聚合模块

任务与完成情况：
- 已完成：将 [base_itemcode_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/base_itemcode_search.py) 迁为真实实现，改走 `subgraphs + features` 组合查询
- 已完成：将 [tooth_hole_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/tooth_hole_search.py)、[water_mill_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/water_mill_search.py)、[wire_base_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/wire_base_search.py)、[wire_special_search.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/search/wire_special_search.py) 迁为真实实现，统一复用 snapshot service
- 已完成：扩展 [price_snapshot_search_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/pricing/services/price_snapshot_search_service.py) 与 [pricing_snapshot_repository.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/db/repositories/pricing_snapshot_repository.py)，补齐第二批模块需要的查询能力
- 已完成：更新 [pricing_bridge_inventory.json](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/pricing_bridge_inventory.json) 与 [test_pricing_bridge_golden.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/golden/test_pricing_bridge_golden.py)，把下一批候选收敛到 `search / total_search / wire_total_search`
- 已完成：扩展 [test_pricing_search_refactor.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_pricing_search_refactor.py)，覆盖第二批迁移模块

阶段结果：
- `domain.pricing.search` 的真实实现覆盖面进一步扩大，bridge 模块已从第一批扩展到第二批
- pricing 下一轮已经可以从 search 迁移转向更聚合的 search / total / calculator 层

当前仍保留的遗留项：
- `search.py`、`total_search.py`、`wire_total_search.py` 仍然是下轮最直接的 search 迁移候选
- 大部分 calculator 仍然桥接到 `scripts/calculate/*`

## 阶段 24：Job Durable Checkpoint 本地落盘与 Worker 重启恢复
目标：
- 在当前环境不具备官方 sqlite checkpointer 时，为 `job_graph` 落地一个可测试的 durable fallback
- 让 `continue` 在新 `JobGraph` 实例和 worker 重启后也能恢复同一 `job_id`
- 保持外部契约不变

任务与完成情况：
- 已完成：新增 [job_file_checkpoint_store.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/workflows/job_file_checkpoint_store.py)，提供 file-backed durable checkpoint store
- 已完成：扩展 [job_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/job_graph.py)，将 durable store 接入 checkpoint 持久化与恢复链路
- 已完成：保持 `thread_id = job_id`，并把恢复来源落到 `resume_checkpoint_source = durable_store`
- 已完成：同步 [continue_job.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/use_cases/continue_job.py)、[orchestrator_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/orchestrator_worker.py)、[all_tasks_worker.py](/d:/workspace/project/python/mold3.0/mold_cost_/workers/all_tasks_worker.py)，确保 worker 继续只依赖 workflow
- 已完成：增强 [test_job_graph_checkpoint_resume.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/integration/test_job_graph_checkpoint_resume.py)，增加“worker 重启后继续恢复”的集成断言，并补齐测试目录清理逻辑
- 已完成：新增 [tests/conftest.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/conftest.py)，让测试期间的 checkpoint 临时目录统一落到 repo-local 临时路径并自动清理

阶段结果：
- `job_graph` 已经不只是内存 checkpoint + envelope，而是具备可跨实例恢复的本地 durable fallback
- 当前环境下即便没有官方 sqlite saver，worker 重启后的 `continue` 链路也有明确落点

当前仍保留的遗留项：
- durable backend 目前仍是本地文件存储，不是多实例共享存储
- 默认 LangGraph checkpointer 仍是 memory saver；后续仍应切到真正持久化后端

## 阶段 25：Review 默认装配继续去 InteractionAgent 化
目标：
- 继续收缩 review 默认装配中对 `InteractionAgent` 的直接依赖
- 让 review graph 的默认 chat / notifier / Redis 依赖直接走新路径
- 保持 review/chat 路由协议兼容

任务与完成情况：
- 已完成：将 [review_chat_execution_adapter.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_chat_execution_adapter.py) 的默认实现改为直接走共享 LLM 配置，不再默认实例化 `InteractionAgent`
- 已完成：调整 [review_graph.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/application/workflows/review_graph.py)，移除 `_get_agent()` 默认装配路径，默认 chat/change/notifier 装配不再回流到 `InteractionAgent`
- 已完成：将 [review_notifier.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_notifier.py)、[review_session_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_session_service.py)、[review_state_adapter.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/domain/review/services/review_state_adapter.py) 收敛到 `mold_cost.infrastructure.messaging.redis_client`
- 已完成：扩展 [test_refactor_smoke.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_refactor_smoke.py)，锁定 review 默认装配不再回退到 `_get_agent`

阶段结果：
- review 默认装配已经不再直接实例化 `InteractionAgent`
- review 侧 Redis 依赖路径已进一步收敛到 `src/mold_cost`

当前仍保留的遗留项：
- `review_change_applier.py` 与 `review_data_loader.py` 仍复用 legacy `ReviewRepository` / handler 体系
- `InteractionAgent*` 兼容类名仍保留，用于平滑迁移，不代表运行时仍依赖旧 agent

## 阶段 26：WebSocket 与 Monitor 尾项清理
目标：
- 清掉仓库里最后一条显式脚本反向依赖尾项
- 将 websocket runtime 和监控脚本进一步收口到 `src/mold_cost`
- 保持 legacy 入口兼容

任务与完成情况：
- 已完成：新增 [websocket_runtime.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/interfaces/api/websocket_runtime.py)，把共享 websocket runtime 收口到新路径
- 已完成：将 [api_gateway/websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/websocket.py) 收敛为兼容 wrapper
- 已完成：重写 [monitor_redis_websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/scripts/monitor_redis_websocket.py)，移除对 `api_gateway.*` 的直接依赖
- 已完成：新增 [monitor_websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/src/mold_cost/infrastructure/messaging/monitor_websocket.py)，提供基于 Redis 活动的 best-effort websocket 监控
- 已完成：新增 [test_monitor_websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/tests/unit/test_monitor_websocket.py)，覆盖 monitor tracker 基本行为

阶段结果：
- `scripts/monitor_redis_websocket.py` 已从 `api_gateway.*` 脱钩
- websocket runtime 与监控脚本都已有 `src/mold_cost` 下的承接路径

当前仍保留的遗留项：
- monitor 的 websocket 统计目前是基于 Redis 活动的 best-effort 视图，不是 API 进程内的精确连接数
- 若后续要恢复精确连接计数，需要引入共享注册表或心跳协议

## 当前整体状态

- `job_graph` 与 `review_graph` 已经都运行在真实 LangGraph runtime 上；job 侧已经具备本地 durable fallback，review 侧默认装配已不再直接实例化 `InteractionAgent`
- `domain.pricing.search` 已完成三批真实模块迁移，`search.py`、`total_search.py`、`wire_total_search.py` 已落地为真实 domain 实现；`process_rule_matcher` 也已从脚本桥接迁到 `src/mold_cost`
- `domain.cad` 与 `domain.features` 已形成更稳定的服务契约，API / workflow / worker 已开始统一面向服务结果；算法本体仍主要位于 `scripts/*`
- pricing / process matcher 主链和 monitor 脚本上的显式 `scripts/* -> api_gateway.*` 反向依赖已基本清理；剩余 legacy 耦合进一步收敛到 review handler 与 pricing calculators
- 当前回归基线更新为：`pytest tests/unit tests/integration tests/golden -q` => `45 passed`

## 下一轮建议

- 优先把 `job_graph` / `review_graph` 的 checkpoint backend 从本地 fallback 推进到真正可共享的 durable 存储
- pricing 下一轮迁移聚焦 calculator 主链，优先处理 `price_material.py`、`price_wire_total.py`、`price_total.py`，再向其余 calculator 扩展
- 继续把 review 里的 action handler 依赖从 legacy 目录抽成应用层或基础设施适配层
- 扩展数值级 golden，增加至少 2 到 3 组不同零件与价格分支样本，避免单样本基线失真
- 继续迁 CAD / feature 算法本体前，先把剩余 legacy 兼容入口和诊断脚本清单再收一轮
