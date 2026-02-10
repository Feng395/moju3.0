# 系统架构接口文档

## 目录
1. [Agent 之间的接口](#agent-之间的接口)
2. [Agent 与 Redis 接口](#agent-与-redis-接口)
3. [Agent 与 MCP 接口](#agent-与-mcp-接口)
4. [MCP 与脚本接口](#mcp-与脚本接口)

---

## Agent 之间的接口

### OrchestratorAgent（编排器）

**职责**：协调整个工作流，调度各个 Agent

#### 方法：`start(job_id: str)`

**调用者**：Worker（RabbitMQ 消费者）

**流程**：
```
start() 
  ├─ 发布进度：initializing (0%)
  ├─ 调用 CADAgent.split()
  │   └─ 发布进度：cad_split_started (5%) / cad_split_completed (20%)
  ├─ 调用 CADAgent.recognize_features()
  │   └─ 发布进度：feature_recognition_started (25%) / feature_recognition_completed (50%)
  ├─ 发布进度：awaiting_confirm (50%)
  └─ 返回，等待用户确认
```

**返回值**：
```python
{
    "status": "ok",
    "message": "特征识别完成，等待用户确认",
    "action_required": "user_confirmation",
    "summary": {
        "job_id": "xxx",
        "success_count": 5,
        "failed_count": 0
    }
}
```

#### 方法：`continue_job(job_id: str)`

**调用者**：API Gateway（用户确认后）

**流程**：
```
continue_job()
  ├─ 验证状态：awaiting_confirm
  ├─ 调用 DecisionAgent.process()（可选）
  ├─ 调用 PricingAgent.process()
  │   └─ 发布进度：pricing_started (75%) / pricing_completed (90%)
  ├─ 发布进度：completed (100%)
  └─ 返回完成结果
```

**返回值**：
```python
{
    "status": "ok",
    "message": "任务处理完成",
    "summary": {
        "job_id": "xxx",
        "duration_ms": 45000
    }
}
```

---

### CADAgent（CAD 处理）

**职责**：调用 MCP 服务进行拆图和特征识别

#### 方法：`split(context: Dict)`

**调用者**：OrchestratorAgent

**参数**：
```python
{
    "job_id": "uuid"  # 必填
}
```

**返回值**：
```python
{
    "status": "ok",
    "message": "成功拆分 5 个子图",
    "summary": {
        "subgraph_count": 5
    }
}
```

#### 方法：`recognize_features(context: Dict)`

**调用者**：OrchestratorAgent

**参数**：
```python
{
    "job_id": "uuid"  # 必填
}
```

**返回值**：
```python
{
    "status": "ok",
    "message": "特征识别完成: 成功5个, 失败0个",
    "summary": {
        "success_count": 5,
        "failed_count": 0
    }
}
```

#### 方法：`recognize_features_batch(context: Dict)`

**调用者**：API Gateway（重新识别特征）

**参数**：
```python
{
    "job_id": "uuid",
    "subgraph_ids": ["sub_001", "sub_002"],
    "force_reprocess": True
}
```

**返回值**：
```python
{
    "status": "ok",
    "message": "批量特征识别完成: 成功2个, 失败0个",
    "total": 2,
    "success": 2,
    "failed": 0,
    "results": [
        {
            "subgraph_id": "sub_001",
            "status": "success",
            "features": {...},
            "duration_ms": 2500
        }
    ]
}
```

---

### PricingAgent（价格计算）

**职责**：调用 MCP 服务进行价格计算

#### 方法：`process(context: Dict)`

**调用者**：OrchestratorAgent

**参数**：
```python
{
    "job_id": "uuid",
    "subgraph_ids": ["sub_001", "sub_002"]
}
```

**返回值**：
```python
{
    "status": "ok",
    "message": "价格计算完成: 成功2个, 失败0个",
    "total_cost": 420.0,
    "breakdown": {
        "material": {"status": "ok", "cost": 100.0},
        "nc_milling": {"status": "ok", "cost": 200.0},
        ...
    }
}
```

#### 方法：`calculate_batch(context: Dict)`

**调用者**：API Gateway（重新计算价格）

**参数**：
```python
{
    "job_id": "uuid",
    "subgraph_ids": ["sub_001"],
    "user_params": {"material": "SKD11"}
}
```

**返回值**：同 `process()`

---

## Agent 与 Redis 接口

### ProgressPublisher

**职责**：发布任务进度到 Redis Pub/Sub

#### 方法：`publish_progress()`

**调用者**：所有 Agent

**参数**：
```python
progress_publisher.publish_progress(
    job_id="uuid",
    stage="cad_split_started",      # ProgressStage 常量
    progress=5,                      # 0-100
    message="正在拆图...",
    details={"source": "mcp_service"}
)
```

**Redis 频道**：`job:{job_id}:progress`

**消息格式**：
```json
{
    "stage": "cad_split_started",
    "progress": 5,
    "message": "正在拆图...",
    "timestamp": "2026-01-19T08:56:41.372779",
    "details": {
        "source": "mcp_service"
    }
}
```

### 进度阶段常量（ProgressStage）

```python
# 初始化
INITIALIZING = "initializing"

# CAD 拆图
CAD_SPLIT_STARTED = "cad_split_started"
CAD_SPLIT_COMPLETED = "cad_split_completed"
CAD_SPLIT_FAILED = "cad_split_failed"

# 特征识别
FEATURE_RECOGNITION_STARTED = "feature_recognition_started"
FEATURE_RECOGNITION_COMPLETED = "feature_recognition_completed"
FEATURE_RECOGNITION_FAILED = "feature_recognition_failed"

# 等待用户确认
WAITING_FOR_CONFIRMATION = "awaiting_confirm"

# 价格计算
PRICING_STARTED = "pricing_started"
PRICING_COMPLETED = "pricing_completed"
PRICING_FAILED = "pricing_failed"

# 完成/失败
COMPLETED = "completed"
FAILED = "failed"
```

### 进度百分比常量（ProgressPercent）

```python
INITIALIZING = 0
CAD_SPLIT_STARTED = 5
CAD_SPLIT_COMPLETED = 20
FEATURE_RECOGNITION_STARTED = 25
FEATURE_RECOGNITION_COMPLETED = 50
PRICING_STARTED = 75
PRICING_COMPLETED = 90
COMPLETED = 100
```

---

## Agent 与 MCP 接口

### MCPClient

**职责**：调用 MCP 服务的工具

#### 方法：`call_tool()`

**调用者**：CADAgent, PricingAgent

**参数**：
```python
result = await mcp_client.call_tool(
    server_name="cad-parser-mcp",
    tool_name="cad_chaitu",
    arguments={"job_id": "uuid"}
)
```

**HTTP 端点**：`POST http://localhost:8202/call_tool`

**请求体**：
```json
{
    "tool_name": "cad_chaitu",
    "arguments": {
        "job_id": "uuid"
    }
}
```

---

## MCP 与脚本接口

### CAD Parser MCP 服务

**端口**：8202

#### 工具 1：`cad_chaitu`

**功能**：CAD 拆图

**参数**：
```python
{
    "job_id": "uuid",           # 必填
    "dwg_url": "path/to/file"   # 可选
}
```

**返回值**：
```python
{
    "status": "ok",
    "message": "拆图完成，生成5个子图",
    "data": {
        "total_count": 5,
        "subgraph_list": [...]
    }
}
```

**进度发布**：
- `cad_split_started` (5%)
- `cad_split_completed` (20%)

**调用脚本**：`scripts/cad_chaitu/cad_chaitu.py`

---

#### 工具 2：`feature_recognition`

**功能**：特征识别

**参数**：
```python
{
    "job_id": "uuid",              # 必填
    "subgraph_id": "sub_001"       # 可选，不提供则处理所有
}
```

**返回值**：
```python
{
    "success": True,
    "message": "特征识别完成",
    "data": {
        "success_count": 5,
        "failed_count": 0,
        "results": [...]
    }
}
```

**进度发布**：
- `feature_recognition_started` (25%)
- `feature_recognition_completed` (50%)

**调用脚本**：`scripts/recognition/feature_recognition.py`

---

### Search Server MCP 服务

**端口**：8203

#### 工具：`search_*`

**功能**：搜索各类数据（物料、NC、焊丝等）

**参数**：
```python
{
    "job_id": "uuid",
    "subgraph_ids": ["sub_001", "sub_002"]
}
```

**返回值**：
```python
{
    "status": "ok",
    "data": {
        "items": [...],
        "material": [...],
        ...
    }
}
```

---

### Calculate Server MCP 服务

**端口**：8204

#### 工具：`calculate_*`

**功能**：计算各类费用（材料、NC、焊丝等）

**参数**：
```python
{
    "search_data": {...},
    "subgraph_ids": ["sub_001", "sub_002"]
}
```

**返回值**：
```python
{
    "status": "ok",
    "results": [
        {
            "subgraph_id": "sub_001",
            "success": True,
            "material_additional_cost": 50.0
        }
    ]
}
```

---

### Pricing Server MCP 服务

**端口**：8205

#### 工具：`calculate_pricing`

**功能**：综合价格计算

**参数**：
```python
{
    "job_id": "uuid",
    "subgraph_ids": ["sub_001"]
}
```

**返回值**：
```python
{
    "status": "ok",
    "total_cost": 420.0,
    "breakdown": {...}
}
```

---

## 脚本接口

### cad_chaitu.py

**功能**：DWG 文件拆图

**主函数**：`chaitu_process(dwg_url, job_id)`

**参数**：
- `dwg_url`: DWG 文件 URL 或 MinIO 路径
- `job_id`: 任务 ID

**返回值**：
```python
{
    "status": "ok",
    "data": {
        "total_count": 5,
        "subgraph_list": [
            {
                "subgraph_id": "sub_001",
                "part_code": "PH2-04",
                "dxf_path": "dxf/2026/01/xxx/PH2-04.dxf"
            }
        ]
    }
}
```

**依赖**：
- MinIO 客户端
- DWG 处理库

---

### feature_recognition.py

**功能**：特征识别

**主函数**：`batch_feature_recognition_process(job_id, subgraph_id=None)`

**参数**：
- `job_id`: 任务 ID
- `subgraph_id`: 子图 ID（可选，不提供则处理所有）

**返回值**：
```python
{
    "success": True,
    "data": {
        "success_count": 5,
        "failed_count": 0,
        "results": [
            {
                "subgraph_id": "sub_001",
                "success": True,
                "features": {
                    "length_mm": 100.0,
                    "width_mm": 50.0,
                    "thickness_mm": 10.0
                }
            }
        ]
    }
}
```

**依赖**：
- DXF 处理库
- 数据库连接

---

## 调用流程示例

### 完整任务流程

```
用户提交任务
  ↓
API Gateway → Worker (RabbitMQ)
  ↓
OrchestratorAgent.start()
  ├─ 发布：initializing (0%)
  ├─ CADAgent.split()
  │   ├─ MCPClient.call_tool("cad_chaitu")
  │   │   ├─ HTTP POST /call_tool
  │   │   ├─ MCP 服务调用 chaitu_process()
  │   │   ├─ 发布：cad_split_started (5%)
  │   │   ├─ 发布：cad_split_completed (20%)
  │   │   └─ 返回结果
  │   └─ 返回
  ├─ CADAgent.recognize_features()
  │   ├─ MCPClient.call_tool("feature_recognition")
  │   │   ├─ HTTP POST /call_tool
  │   │   ├─ MCP 服务调用 batch_feature_recognition_process()
  │   │   ├─ 发布：feature_recognition_started (25%)
  │   │   ├─ 发布：feature_recognition_completed (50%)
  │   │   └─ 返回结果
  │   └─ 返回
  ├─ 发布：awaiting_confirm (50%)
  └─ 返回，等待用户确认

用户确认
  ↓
API Gateway → OrchestratorAgent.continue_job()
  ├─ PricingAgent.process()
  │   ├─ MCPClient.call_tool("search_*")
  │   │   └─ 搜索数据
  │   ├─ MCPClient.call_tool("calculate_*")
  │   │   └─ 计算费用
  │   ├─ 发布：pricing_started (75%)
  │   ├─ 发布：pricing_completed (90%)
  │   └─ 返回结果
  ├─ 发布：completed (100%)
  └─ 返回完成结果
```

---

## 错误处理

### 标准错误响应

```python
{
    "status": "error",
    "message": "错误描述",
    "error_code": "ERROR_CODE",
    "details": {...}
}
```

### 常见错误码

- `MISSING_JOB_ID`: 缺少 job_id 参数
- `CHAITU_FAILED`: 拆图失败
- `FEATURE_RECOGNITION_FAILED`: 特征识别失败
- `PRICING_ERROR`: 价格计算失败
- `AGENT_NOT_REGISTERED`: Agent 未注册
- `METHOD_NOT_FOUND`: 方法不存在

---

## 环境配置

### 必需环境变量

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# MCP 服务地址
CAD_PARSER_MCP_URL=http://localhost:8202
SEARCH_SERVER_MCP_URL=http://localhost:8203
CALCULATE_SERVER_MCP_URL=http://localhost:8204
PRICING_SERVER_MCP_URL=http://localhost:8205

# MinIO
MINIO_ENDPOINT=192.168.0.30:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db
```

---

## 性能指标

### 典型处理时间

- CAD 拆图：3-5 分钟（取决于文件大小）
- 特征识别：1-2 分钟（4 个子图）
- 价格计算：30-60 秒

### 并发能力

- 同时处理任务数：10+
- MCP 服务连接池：20
- Redis 连接：10

---

## 监控和调试

### 日志位置

```
logs/
├── cad_parser_mcp.log
├── search_server_mcp.log
├── calculate_server_mcp.log
├── pricing_server_mcp.log
└── orchestrator_worker.log
```

### Redis 订阅监控

```bash
redis-cli SUBSCRIBE job:{job_id}:progress
```

### MCP 服务健康检查

```bash
curl http://localhost:8202/health
curl http://localhost:8203/health
curl http://localhost:8204/health
curl http://localhost:8205/health
```
