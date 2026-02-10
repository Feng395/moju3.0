# mold_cost-main 与 mold_cost_ 合并分析文档

## 一、目录结构对比

### 1.1 共同目录
两个项目都包含以下核心目录：
- `agents/` - Agent 模块
- `api_gateway/` - API 网关
- `shared/` - 共享模块
- `workers/` - 后台工作进程（仅 mold_cost-main）

### 1.2 mold_cost_ 独有目录
- `consumers/` - 消息队列消费者
- `docs/` - 文档
- `examples/` - 示例和测试代码
- `infrastructure/` - 基础设施配置（Docker、数据库初始化）
- `logs/` - 日志文件
- `mcp_services/` - MCP 服务
- `scripts/` - 脚本工具（CAD 处理、计算、特征识别、搜索）
- `tests/` - 测试文件

---

## 二、核心模块功能对比

### 2.1 agents/ 目录

#### mold_cost-main/agents/
**版本：v1.1 - 基础版本**

| 文件 | 功能 | 特点 |
|------|------|------|
| `base_agent.py` | Agent 基类 | 简单的 OpResult，基础功能 |
| `cad_agent.py` | CAD 文件处理 | 基础 CAD 解析 |
| `interaction_agent.py` | 用户交互 | 简单的参数缺失处理 |
| `nc_time_agent.py` | NC 时间计算 | 基础 NC 时间处理 |
| `orchestrator_agent.py` | 任务编排 | 基础任务流程编排 |
| `pricing_agent.py` | 价格计算 | 基础价格计算 |

#### mold_cost_/agents/
**版本：v2.0 - 增强版本**

| 文件 | 功能 | 特点 |
|------|------|------|
| `base_agent.py` | Agent 基类 | 增强的 OpResult，支持时区、日志 |
| `cad_agent.py` | CAD 文件处理 | 增强的 CAD 解析 |
| `interaction_agent.py` | **数据审核和交互** | **完整的审核流程、自然语言处理、多轮对话** |
| `nc_time_agent.py` | NC 时间计算 | 增强的 NC 时间处理 |
| `orchestrator_agent.py` | 任务编排 | 增强的任务流程编排 |
| `pricing_agent.py` | 价格计算 | 增强的价格计算 |
| **新增文件** | | |
| `confirm_handler.py` | 确认处理器 | 处理用户确认操作 |
| `data_view_builder.py` | 数据视图构建器 | 构建前端展示数据 |
| `decision_agent.py` | 决策 Agent | 智能决策逻辑 |
| `intent_recognizer.py` | 意图识别器 | 识别用户意图 |
| `intent_types.py` | 意图类型定义 | 意图枚举和定义 |
| `message_persistence_manager.py` | 消息持久化管理器 | 管理聊天消息持久化 |
| `nlp_parser.py` | 自然语言解析器 | 解析用户自然语言输入 |
| `review_status.py` | 审核状态管理 | 管理审核流程状态 |

**action_handlers/ 子目录（新增）**
- `base_handler.py` - 处理器基类
- `data_modification_handler.py` - 数据修改处理器
- `feature_recognition_handler.py` - 特征识别处理器
- `general_chat_handler.py` - 通用聊天处理器
- `price_calculation_handler.py` - 价格计算处理器
- `query_details_handler.py` - 查询详情处理器
- `weight_price_calculation_handler.py` - 重量价格计算处理器
- `weight_price_query_handler.py` - 重量价格查询处理器

---

### 2.2 api_gateway/ 目录

#### mold_cost-main/api_gateway/
**版本：基础版本**

| 文件 | 功能 |
|------|------|
| `auth.py` | 认证模块 |
| `database.py` | 数据库连接 |
| `main.py` | FastAPI 主应用 |
| `websocket.py` | WebSocket 处理 |

**routers/ 子目录**
- `__init__.py`
- `features.py` - 特征路由
- `jobs.py` - 任务路由
- `phase2.py` - 第二阶段路由
- `pricing.py` - 价格路由
- `recalculations.py` - 重新计算路由
- `reports.py` - 报告路由

**utils/ 子目录**
- `minio_client.py` - MinIO 客户端

#### mold_cost_/api_gateway/
**版本：增强版本**

| 文件 | 功能 | 特点 |
|------|------|------|
| `auth.py` | 认证模块 | 增强的认证 |
| `config.py` | **配置管理** | **新增：统一配置** |
| `main.py` | FastAPI 主应用 | 增强的路由和中间件 |
| `websocket.py` | WebSocket 处理 | 增强的 WebSocket |

**新增目录结构：**

**models/ 子目录（新增）**
- `interaction_models.py` - 交互数据模型

**repositories/ 子目录（新增）**
- `audit_repository.py` - 审计仓储
- `chat_history_repository.py` - 聊天历史仓储
- `interaction_repository.py` - 交互仓储
- `job_repository.py` - 任务仓储
- `process_rules_repository.py` - 工艺规则仓储
- `review_repository.py` - 审核仓储
- `snapshot_repository.py` - 快照仓储

**routers/ 子目录（增强）**
- `chat_router.py` - **聊天路由（新增）**
- `file_router.py` - **文件路由（新增）**
- `interactions.py` - **交互路由（新增）**
- `jobs.py` - 任务路由
- `phase2.py` - 第二阶段路由
- `recalculations.py` - 重新计算路由
- `review_router.py` - **审核路由（新增）**
- `websocket_router.py` - **WebSocket 路由（新增）**

**services/ 子目录（新增）**
- `file_service.py` - 文件服务
- `interaction_service.py` - 交互服务
- `job_service.py` - 任务服务

**utils/ 子目录（增强）**
- `chat_logger.py` - **聊天日志（新增）**
- `encryption.py` - **加密工具（新增）**
- `message_formatter.py` - **消息格式化（新增）**
- `minio_client.py` - MinIO 客户端
- `rabbitmq_client.py` - **RabbitMQ 客户端（新增）**
- `redis_client.py` - **Redis 客户端（新增）**
- `snapshot_manager.py` - **快照管理器（新增）**
- `validators.py` - **验证器（新增）**

---

### 2.3 shared/ 目录

#### mold_cost-main/shared/
**版本：基础版本**

| 文件 | 功能 |
|------|------|
| `agent_types.py` | Agent 类型定义 |
| `database.py` | 数据库工具 |
| `mcp_client.py` | MCP 客户端 |
| `message_queue.py` | 消息队列 |
| `models.py` | 数据模型 |
| `progress_publisher.py` | 进度发布器 |
| `progress_stages.py` | 进度阶段定义 |

#### mold_cost_/shared/
**版本：增强版本**

| 文件 | 功能 | 特点 |
|------|------|------|
| `database.py` | 数据库工具 | 增强的数据库连接池 |
| `message_queue.py` | 消息队列 | 增强的 RabbitMQ 集成 |
| `models.py` | 数据模型 | 更完整的数据模型 |
| **新增文件** | | |
| `logging_config.py` | **日志配置** | **统一日志配置** |
| `logging_middleware.py` | **日志中间件** | **请求日志记录** |
| `permissions.py` | **权限管理** | **RBAC 权限系统** |
| `process_code_mapping.py` | **工艺代码映射** | **工艺代码转换** |
| `schemas.py` | **数据模式** | **Pydantic 模式定义** |
| `security.py` | **安全工具** | **加密、JWT 等** |
| `timezone_utils.py` | **时区工具** | **上海时区处理** |

**validators/ 子目录（新增）**
- `business_validator.py` - 业务验证器
- `completeness_validator.py` - 完整性验证器
- `field_validator.py` - 字段验证器
- `modification_validator.py` - 修改验证器

---

### 2.4 workers/ 目录

#### mold_cost-main/workers/
**版本：基础版本**

| 文件 | 功能 |
|------|------|
| `all_tasks_worker.py` | 全任务工作进程 |
| `orchestrator_worker.py` | 编排工作进程 |
| `pricing_recalculate_worker.py` | 价格重算工作进程 |

#### mold_cost_/workers/
**不存在此目录**

---

### 2.5 mold_cost_ 独有模块

#### consumers/
- `review_consumer.py` - 审核消息消费者

#### scripts/
**cad_chaitu/ - CAD 拆图工具**
- `block_analyzer.py` - 块分析器
- `cad_system.py` - CAD 系统
- `converter.py` - 转换器
- `cutting_detector.py` - 切割检测器
- `database.py` - 数据库操作
- `main.py` - 主程序
- `number_extractor.py` - 数字提取器
- `storage.py` - 存储管理
- `text_processor.py` - 文本处理器
- `unified_api.py` - 统一 API
- `utils.py` - 工具函数

**calculate/ - 价格计算模块**
- `judgment.py` - 判断逻辑
- `price_add_auto_material.py` - 自动材料价格
- `price_heat.py` - 热处理价格
- `price_material.py` - 材料价格
- `price_nc_base.py` - NC 基础价格
- `price_nc_time.py` - NC 时间价格
- `price_nc_total.py` - NC 总价格
- `price_tooth_hole.py` - 齿孔价格
- `price_total.py` - 总价格
- `price_water_mill_*.py` - 水磨相关价格（多个文件）
- `price_wire_*.py` - 线切割相关价格（多个文件）

**feature_recognition/ - 特征识别模块**
- `bevel_detector.py` - 斜面检测器
- `boring_calculator.py` - 镗孔计算器
- `chamfer_detector.py` - 倒角检测器
- `closed_area_detector.py` - 封闭区域检测器
- `dimension_extractor.py` - 尺寸提取器
- `feature_recognition.py` - 特征识别主程序
- `frame_text_extractor.py` - 框架文本提取器
- `grinding_detector.py` - 磨削检测器
- `hanging_table_detector.py` - 挂台检测器
- `material_info_extractor.py` - 材料信息提取器
- `material_preparation_extractor.py` - 材料准备提取器
- `oil_tank_detector.py` - 油槽检测器
- `plate_line_view_identifier.py` - 板料线视图识别器
- `processing_instruction_extractor.py` - 加工指令提取器
- `red_line_calculator.py` - 红线计算器
- `slider_calculator.py` - 滑块计算器
- `text_extractor.py` - 文本提取器
- `tooth_hole_detector.py` - 齿孔检测器
- `view_identifier.py` - 视图识别器
- `view_wire_calculator.py` - 视图线切割计算器
- `water_mill_calculator.py` - 水磨计算器
- `wire_cut_filter.py` - 线切割过滤器
- `wire_length_calculator.py` - 线长度计算器
- `wire_plate_overlap_filter.py` - 线板重叠过滤器

**search/ - 搜索模块**
- `base_itemcode_search.py` - 基础项目代码搜索
- `density_search.py` - 密度搜索
- `heat_search.py` - 热处理搜索
- `material_search.py` - 材料搜索
- `nc_search.py` - NC 搜索
- `search.py` - 搜索主程序
- `tooth_hole_search.py` - 齿孔搜索
- `total_search.py` - 总搜索
- `water_mill_search.py` - 水磨搜索
- `wire_*_search.py` - 线切割相关搜索（多个文件）

**其他脚本**
- `minio_client.py` - MinIO 客户端
- `monitor_concurrency.py` - 并发监控
- `monitor_locks.py` - 锁监控
- `monitor_redis_websocket.py` - Redis WebSocket 监控
- `process_rule_matcher.py` - 工艺规则匹配器

#### mcp_services/
- `cad_parser_mcp/` - CAD 解析 MCP 服务
- `cad_price_search_mcp/` - CAD 价格搜索 MCP 服务
- `pricing_server_mcp/` - 价格服务器 MCP 服务

#### infrastructure/
- `docker-compose.yml` - Docker 编排配置
- `init-db.sql` - 数据库初始化脚本
- `add-comments.sql` - 数据库注释脚本

---

## 三、功能差异总结

### 3.1 mold_cost-main 特点
- **简洁版本**：基础功能实现
- **核心模块**：agents、api_gateway、shared、workers
- **适合场景**：快速原型、基础功能验证

### 3.2 mold_cost_ 特点
- **完整版本**：生产级实现
- **增强功能**：
  - ✅ 完整的用户交互和审核流程
  - ✅ 自然语言处理和意图识别
  - ✅ 多轮对话支持
  - ✅ 完整的权限和安全系统
  - ✅ 日志和监控系统
  - ✅ 数据验证和完整性检查
  - ✅ CAD 处理和特征识别
  - ✅ 价格计算引擎
  - ✅ 搜索和查询功能
  - ✅ MCP 服务集成
  - ✅ 完整的测试和示例

---

## 四、合并策略建议

### 4.1 保留 mold_cost_ 为主体
**原因：**
1. 功能更完整
2. 架构更成熟
3. 包含生产级特性
4. 有完整的测试和文档

### 4.2 从 mold_cost-main 迁移的内容

#### 需要检查的文件：
1. **workers/** 目录
   - 检查是否有 mold_cost_ 中缺失的功能
   - 如果有，迁移到 mold_cost_

2. **配置文件**
   - 对比 `.env` 文件
   - 对比 `requirements.txt`
   - 合并配置项

3. **文档**
   - `启动清单.md`
   - `NC_3D_Workflow_API_Reference.md`
   - `QUICK_START.md`

### 4.3 合并步骤

#### 第一步：备份
```bash
# 备份 mold_cost-main 的独有内容
cp -r mold_cost-main/workers mold_cost_/workers_backup
cp mold_cost-main/启动清单.md mold_cost_/docs/
cp mold_cost-main/NC_3D_Workflow_API_Reference.md mold_cost_/docs/
cp mold_cost-main/QUICK_START.md mold_cost_/docs/
```

#### 第二步：对比和合并
1. 对比 `requirements.txt`
2. 对比 `.env` 配置
3. 检查 workers 功能差异
4. 合并文档

#### 第三步：测试
1. 运行所有测试
2. 验证核心功能
3. 检查 API 兼容性

#### 第四步：清理
1. 删除 mold_cost-main 目录
2. 重命名 mold_cost_ 为 mold_cost（可选）
3. 更新 Git 仓库

---

## 五、风险评估

### 5.1 低风险
- ✅ 配置文件合并
- ✅ 文档迁移
- ✅ 依赖包合并

### 5.2 中风险
- ⚠️ workers 模块迁移（需要测试）
- ⚠️ 数据库模型兼容性

### 5.3 高风险
- ❌ 无（两个项目结构相似）

---

## 六、下一步行动

1. **审查本文档**：确认分析正确
2. **对比 workers**：检查功能差异
3. **对比配置**：合并配置文件
4. **执行合并**：按照合并步骤操作
5. **测试验证**：确保功能正常
6. **提交代码**：更新 Git 仓库

---

## 七、建议的最终目录结构

```
mold_cost/  (合并后)
├── agents/                    # Agent 模块（来自 mold_cost_）
│   ├── action_handlers/       # 动作处理器
│   ├── phase2/                # 第二阶段
│   └── *.py                   # 各种 Agent
├── api_gateway/               # API 网关（来自 mold_cost_）
│   ├── models/                # 数据模型
│   ├── repositories/          # 数据仓储
│   ├── routers/               # 路由
│   ├── services/              # 服务
│   └── utils/                 # 工具
├── consumers/                 # 消息消费者
├── docs/                      # 文档（合并两者）
├── examples/                  # 示例代码
├── infrastructure/            # 基础设施
├── logs/                      # 日志
├── mcp_services/              # MCP 服务
├── scripts/                   # 脚本工具
│   ├── cad_chaitu/            # CAD 拆图
│   ├── calculate/             # 价格计算
│   ├── feature_recognition/   # 特征识别
│   └── search/                # 搜索
├── shared/                    # 共享模块（来自 mold_cost_）
│   └── validators/            # 验证器
├── tests/                     # 测试
├── workers/                   # 工作进程（来自 mold_cost-main，需检查）
├── .env                       # 环境配置（合并）
├── .gitignore                 # Git 忽略
├── conftest.py                # Pytest 配置
├── README.md                  # 项目说明
└── requirements.txt           # 依赖包（合并）
```

---

**文档版本：** v1.0  
**创建时间：** 2026-02-10  
**最后更新：** 2026-02-10
