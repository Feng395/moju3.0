# AI Agents 模块

## 📋 概述

AI Agents 模块是模具成本核算系统的核心智能层，负责处理用户交互、任务编排、CAD解析、特征识别和价格计算等复杂==业务逻辑==。采用 LangChain 和 LangGraph 框架构建多Agent协作系统。

## 🏗️ 架构设计

### Agent 层次结构

```
OrchestratorAgent (编排层)
    ├── InteractionAgent (交互层)
    │   ├── IntentRecognizer (意图识别)
    │   └── NLPParser (自然语言解析)
    ├── DecisionAgent (决策层)
    ├── CADAgent (CAD处理)
    ├── PricingAgent (价格计算)
    └── NCTimeAgent (NC时间计算)
```

## 📁 目录结构

```
agents/
├── action_handlers/              # 动作处理器
│   ├── base_handler.py          # 基础处理器抽象类
│   ├── feature_recognition_handler.py  # 特征识别处理
│   ├── price_calculation_handler.py    # 价格计算处理
│   ├── data_modification_handler.py    # 数据修改处理
│   ├── query_details_handler.py        # 详情查询处理
│   ├── general_chat_handler.py         # 通用对话处理
│   ├── weight_price_calculation_handler.py  # 重量价格计算
│   └── weight_price_query_handler.py   # 重量价格查询
├── orchestrator_agent.py        # 编排Agent（核心）
├── interaction_agent.py         # 交互Agent
├── decision_agent.py            # 决策Agent
├── cad_agent.py                 # CAD处理Agent
├── cad_agent_local.py          # 本地CAD处理
├── pricing_agent.py            # 价格计算Agent
├── pricing_agent_local.py      # 本地价格计算
├── nc_time_agent.py            # NC时间计算Agent
├── intent_recognizer.py        # 意图识别器
├── intent_types.py             # 意图类型定义
├── nlp_parser.py               # NLP解析器
├── confirm_handler.py          # 确认处理器
├── data_view_builder.py        # 数据视图构建器
├── message_persistence_manager.py  # 消息持久化管理
├── review_status.py            # 审核状态管理
└── phase2/                     # 第二期功能
    └── sheet_line_agent.py     # 板材线Agent
```

### Agent 业务处理

| Agent                 | 主要业务操作                                                |
| --------------------- | ----------------------------------------------------------- |
| **OrchestratorAgent** | 任务编排：CAD拆图 → 特征识别 → NC时间计算 → 价格计算 → 完成 |
| **InteractionAgent**  | 用户交互：启动审核流程、处理修改请求、确认修改、刷新数据    |
| **CADAgent**          | CAD处理：调用 MCP 服务执行拆图和特征识别                    |
| **PricingAgent**      | 价格计算：并发搜索数据 → 并发计算费用 → 汇总结果            |
| **DecisionAgent**     | 工艺决策：根据特征参数决定工艺参数（线割模式、刀数等）      |
| **IntentRecognizer**  | 意图识别：使用 LLM/规则识别用户意图（7种类型）              |

### Handler 业务处理

| Handler                           | 业务操作                                                     |
| --------------------------------- | ------------------------------------------------------------ |
| **FeatureRecognitionHandler**     | 1. 提取 subgraph_ids 2. 准备 API 参数 3. 保存到 Redis 4. 返回确认消息 |
| **PriceCalculationHandler**       | 1. 提取 subgraph_ids 2. 准备价格计算参数 3. 保存到 Redis 4. 返回确认消息 |
| **DataModificationHandler**       | 1. NLPParser 解析自然语言 2. ModificationValidator 验证 3. 应用修改到临时数据 4. 重新构建展示视图 5. 保存到 Redis |
| **QueryDetailsHandler**           | 1. 提取 subgraph_id 2. 查询 calculation_steps 3. LLM 格式化计算过程 4. 直接返回（无需确认） |
| **GeneralChatHandler**            | 1. 构建上下文信息 2. 调用 LLM 生成回复 3. 直接返回           |
| **WeightPriceCalculationHandler** | 1. 提取 subgraph_ids 2. 准备按重量计算参数 3. 保存到 Redis 4. 返回确认消息 |
| **WeightPriceQueryHandler**       | 1. 提取 subgraph_id 2. 查询 weight_price_steps 3. LLM 格式化计算过程 4. 直接返回 |

### 核心业务流程

```
用户输入 → IntentRecognizer(识别意图) 
    ↓
    ├─→ FEATURE_RECOGNITION → FeatureRecognitionHandler → Redis → ConfirmHandler → CADAgent
    ├─→ PRICE_CALCULATION → PriceCalculationHandler → Redis → ConfirmHandler → PricingAgent
    ├─→ DATA_MODIFICATION → DataModificationHandler → Redis → ConfirmHandler → DB Update
    ├─→ QUERY_DETAILS → QueryDetailsHandler → 直接返回 calculation_steps
    ├─→ WEIGHT_PRICE_CALCULATION → WeightPriceCalculationHandler → Redis → ConfirmHandler
    ├─→ WEIGHT_PRICE_QUERY → WeightPriceQueryHandler → 直接返回 weight_price_steps
    └─→ GENERAL_CHAT → GeneralChatHandler → 直接返回 LLM 回复
```

## 🤖 核心 Agents

### 1. OrchestratorAgent (编排Agent)

**职责**: 任务编排和流程控制

**主要功能**:
- 接收用户消息并分发给相应的Agent
- 协调多个Agent之间的协作
- 管理任务状态和进度
- 处理异常和错误恢复

**关键方法**:
```python
async def process_message(message: str, job_id: str) -> dict
async def handle_interaction(interaction_data: dict) -> dict
async def get_job_status(job_id: str) -> dict
```

### 2. InteractionAgent (交互Agent)

**职责**: 用户交互和对话管理

**主要功能**:
- 解析用户输入的自然语言
- 识别用户意图
- 生成友好的响应消息
- 处理多轮对话上下文

**支持的意图类型**:
- `FEATURE_RECOGNITION` - 特征识别
- `PRICE_CALCULATION` - 价格计算
- `DATA_MODIFICATION` - 数据修改
- `QUERY_DETAILS` - 查询详情
- `GENERAL_CHAT` - 通用对话

### 3. CADAgent (CAD处理Agent)

**职责**: CAD文件解析和特征提取

**主要功能**:
- DWG/PRT文件格式转换
- CAD图纸解析
- 特征识别和提取
- 尺寸信息提取

**处理流程**:
1. 文件格式验证
2. DWG → DXF 转换
3. 图层分析
4. 特征识别
5. 结果存储

### 4. PricingAgent (价格计算Agent)

**职责**: 成本计算和价格估算

**主要功能**:
- 材料成本计算
- 加工成本计算
- NC时间计算
- 水磨、线割等工艺成本
- 总成本汇总

**计算模块**:
- 材料价格 (`price_material.py`)
- NC基础价格 (`price_nc_base.py`)
- NC时间价格 (`price_nc_time.py`)
- 水磨价格 (`price_water_mill_*.py`)
- 线割价格 (`price_wire_*.py`)
- 热处理价格 (`price_heat.py`)

### 5. DecisionAgent (决策Agent)

**职责**: 业务决策和规则匹配

**主要功能**:
- 工艺规则匹配
- 参数验证
- 业务逻辑判断
- 异常情况处理

## 🎯 Action Handlers (动作处理器)

### BaseHandler (基础处理器)

所有处理器的抽象基类，定义统一接口:

```python
class BaseHandler(ABC):
    @abstractmethod
    async def handle(self, context: dict) -> dict:
        """处理业务逻辑"""
        pass
    
    @abstractmethod
    async def validate(self, data: dict) -> bool:
        """验证输入数据"""
        pass
```

### FeatureRecognitionHandler (特征识别处理器)

**功能**: 处理CAD特征识别请求

**输入**:
```python
{
    "job_id": "uuid",
    "file_path": "path/to/cad/file.dwg",
    "recognition_type": "auto"  # auto, manual, specific
}
```

**输出**:
```python
{
    "success": True,
    "features": {
        "dimensions": {...},
        "holes": [...],
        "threads": [...],
        "surfaces": [...]
    }
}
```

### PriceCalculationHandler (价格计算处理器)

**功能**: 处理价格计算请求

**输入**:
```python
{
    "job_id": "uuid",
    "calculation_type": "full",  # full, material, processing
    "parameters": {...}
}
```

**输出**:
```python
{
    "success": True,
    "total_price": 1234.56,
    "breakdown": {
        "material": 500.00,
        "processing": 734.56
    }
}
```

### DataModificationHandler (数据修改处理器)

**功能**: 处理用户数据修改请求

**支持的修改类型**:
- 单个字段修改
- 批量修改
- 工艺参数调整
- 价格项更新

### QueryDetailsHandler (详情查询处理器)

**功能**: 查询任务详情和状态

**查询类型**:
- 任务基本信息
- 特征识别结果
- 价格计算明细
- 处理进度

## 🔄 工作流程

### 典型任务处理流程

```
1. 用户上传CAD文件
   ↓
2. OrchestratorAgent 接收任务
   ↓
3. CADAgent 解析文件
   ↓
4. FeatureRecognitionHandler 识别特征
   ↓
5. PricingAgent 计算价格
   ↓
6. InteractionAgent 生成报告
   ↓
7. 返回结果给用户
```

### 交互式对话流程

```
1. 用户发送消息
   ↓
2. InteractionAgent 解析意图
   ↓
3. IntentRecognizer 识别意图类型
   ↓
4. 路由到对应的 Handler
   ↓
5. Handler 处理业务逻辑
   ↓
6. 生成响应消息
   ↓
7. 返回给用户
```

## 🛠️ 开发指南

### 添加新的 Agent

1. 继承 `BaseAgent` 类
2. 实现必要的方法
3. 在 `OrchestratorAgent` 中注册
4. 添加相应的测试

示例:
```python
from agents.base_agent import BaseAgent

class MyNewAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.name = "MyNewAgent"
    
    async def process(self, data: dict) -> dict:
        # 实现处理逻辑
        return {"success": True}
```

### 添加新的 Handler

1. 继承 `BaseHandler` 类
2. 实现 `handle()` 和 `validate()` 方法
3. 在对应的 Agent 中注册
4. 添加单元测试

示例:
```python
from agents.action_handlers.base_handler import BaseHandler

class MyNewHandler(BaseHandler):
    async def handle(self, context: dict) -> dict:
        # 实现处理逻辑
        return {"success": True}
    
    async def validate(self, data: dict) -> bool:
        # 实现验证逻辑
        return True
```

### 添加新的意图类型

1. 在 `intent_types.py` 中定义新意图
2. 在 `IntentRecognizer` 中添加识别规则
3. 创建对应的 Handler
4. 更新文档

## 📊 性能优化

### 异步处理

所有 Agent 和 Handler 都使用异步方法，提高并发性能:

```python
async def process_multiple_jobs(job_ids: list):
    tasks = [process_job(job_id) for job_id in job_ids]
    results = await asyncio.gather(*tasks)
    return results
```

### 缓存策略

使用 Redis 缓存频繁访问的数据:

```python
# 缓存特征识别结果
await redis_client.set(f"features:{job_id}", features, expire=3600)

# 缓存价格计算结果
await redis_client.set(f"price:{job_id}", price_data, expire=3600)
```

### 消息队列

使用 RabbitMQ 处理耗时任务:

```python
# 发送任务到队列
await rabbitmq_client.publish(
    queue="cad_processing",
    message={"job_id": job_id, "file_path": file_path}
)
```

## 🧪 测试

### 单元测试

```bash
# 测试所有 Agents
pytest tests/agents/

# 测试特定 Agent
pytest tests/agents/test_orchestrator_agent.py

# 测试 Handlers
pytest tests/agents/test_handlers.py
```

### 集成测试

```bash
# 端到端测试
pytest tests/integration/test_agent_workflow.py
```

## 📝 配置

### Agent 配置

在 `.env` 文件中配置:

```bash
# Agent 配置
AGENT_TIMEOUT=300
AGENT_MAX_RETRIES=3
AGENT_LOG_LEVEL=INFO

# LLM 配置
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
```

## 🔍 调试

### 启用详细日志

```python
from shared.logging_config import get_logger

logger = get_logger(__name__)
logger.setLevel("DEBUG")
```

### 查看 Agent 执行轨迹

```python
# 在 OrchestratorAgent 中启用追踪
orchestrator.enable_tracing = True
```

## 📚 相关文档

- [API Gateway 文档](../api_gateway/README.md)
- [Scripts 文档](../scripts/README.md)
- [Shared 模块文档](../shared/README.md)
- [主项目文档](../README.md)

## 🤝 贡献指南

1. 遵循现有的代码风格
2. 添加必要的类型注解
3. 编写单元测试
4. 更新相关文档
5. 提交 Pull Request

## 📞 联系方式

如有问题，请联系 AI Agents 团队或提交 Issue。
