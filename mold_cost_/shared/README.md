# Shared 模块

## 📋 概述

Shared 模块包含系统中各个模块共享的通用组件、工具函数、数据模型和配置。这些组件被 API Gateway、Agents 和 Workers 等模块广泛使用。

## 📁 目录结构

```
shared/
├── validators/              # 验证器模块
│   ├── business_validator.py      # 业务逻辑验证
│   ├── completeness_validator.py  # 完整性验证
│   ├── field_validator.py         # 字段验证
│   ├── modification_validator.py  # 修改验证
│   └── __init__.py
├── agent_types.py          # Agent类型定义
├── database.py             # 数据库连接管理
├── logging_config.py       # 日志配置
├── logging_middleware.py   # 日志中间件
├── mcp_client.py          # MCP客户端
├── message_queue.py       # 消息队列
├── models.py              # 数据模型
├── permissions.py         # 权限管理
├── process_code_mapping.py # 工艺代码映射
├── progress_publisher.py  # 进度发布器
├── progress_stages.py     # 进度阶段定义
├── schemas.py             # 数据Schema
├── security.py            # 安全工具
├── timezone_utils.py      # 时区工具
└── __init__.py
```

## 🗄️ 数据库模块 (database.py)

### 功能概述

提供统一的数据库连接管理和连接池。

### 核心功能

```python
from shared.database import get_db_pool, get_db_connection

# 获取连接池
pool = await get_db_pool()

# 使用连接
async with pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM jobs")

# 获取单个连接
async with get_db_connection() as conn:
    await conn.execute("INSERT INTO jobs ...")
```

### 连接池配置

```python
# 连接池参数
min_size = 10      # 最小连接数
max_size = 20      # 最大连接数
timeout = 30       # 连接超时（秒）
command_timeout = 60  # 命令超时（秒）
```

## 📊 数据模型 (models.py)

### 功能概述

定义系统中使用的 SQLAlchemy ORM 模型。

### 核心模型

#### Job (任务)
```python
class Job(Base):
    __tablename__ = 'jobs'
    
    job_id = Column(UUID, primary_key=True)
    job_name = Column(String(100))
    status = Column(String(20))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

#### User (用户)
```python
class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(UUID, primary_key=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(255))
    role = Column(String(20))
```

#### ProcessRule (工艺规则)
```python
class ProcessRule(Base):
    __tablename__ = 'process_rules'
    
    rule_id = Column(UUID, primary_key=True)
    rule_name = Column(String(100))
    feature_type = Column(String(50))
    conditions = Column(JSON)
    version_id = Column(String(50))
```

## 📋 数据Schema (schemas.py)

### 功能概述

定义 Pydantic 数据验证模型。

### 核心Schema

#### JobSchema
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class JobCreate(BaseModel):
    job_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class JobUpdate(BaseModel):
    job_name: Optional[str] = None
    status: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    job_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

## 📝 日志配置 (logging_config.py)

### 功能概述

统一的日志配置和管理。

### 使用方法

```python
from shared.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 日志配置

```python
# 日志级别
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 日志文件
LOG_FILE = "logs/app.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

### 日志中间件 (logging_middleware.py)

自动记录所有 HTTP 请求和响应：

```python
from shared.logging_middleware import LoggingMiddleware

app.add_middleware(LoggingMiddleware)
```

记录内容：
- 请求方法和路径
- 请求参数
- 响应状态码
- 处理时间
- 错误信息

## 🔐 安全模块 (security.py)

### 功能概述

提供安全相关的工具函数。

### 核心功能

#### 密码加密
```python
from shared.security import hash_password, verify_password

# 加密密码
hashed = hash_password("password123")

# 验证密码
is_valid = verify_password("password123", hashed)
```

#### JWT Token
```python
from shared.security import create_access_token, decode_token

# 创建 Token
token = create_access_token(
    data={"user_id": "123", "username": "admin"},
    expires_delta=timedelta(hours=2)
)

# 解码 Token
payload = decode_token(token)
```

#### 数据加密
```python
from shared.security import encrypt_data, decrypt_data

# 加密数据
encrypted = encrypt_data("sensitive data")

# 解密数据
decrypted = decrypt_data(encrypted)
```

## 🔑 权限管理 (permissions.py)

### 功能概述

基于角色的访问控制 (RBAC)。

### 角色定义

```python
class Role:
    ADMIN = "admin"          # 管理员
    USER = "user"            # 普通用户
    VIEWER = "viewer"        # 只读用户
    OPERATOR = "operator"    # 操作员
```

### 权限检查

```python
from shared.permissions import check_permission, require_role

# 检查权限
if check_permission(user, "job:create"):
    # 允许创建任务
    pass

# 装饰器方式
@require_role(Role.ADMIN)
async def admin_only_function():
    pass
```

### 权限定义

```python
PERMISSIONS = {
    Role.ADMIN: ["*"],  # 所有权限
    Role.USER: [
        "job:create",
        "job:read",
        "job:update",
        "file:upload",
        "file:download"
    ],
    Role.VIEWER: [
        "job:read",
        "file:download"
    ]
}
```

## ✅ 验证器模块 (validators/)

### BusinessValidator (业务逻辑验证)

```python
from shared.validators.business_validator import BusinessValidator

validator = BusinessValidator()

# 验证任务数据
is_valid = await validator.validate_job_data(job_data)

# 验证工艺规则
is_valid = await validator.validate_process_rule(rule_data)
```

### CompletenessValidator (完整性验证)

```python
from shared.validators.completeness_validator import CompletenessValidator

validator = CompletenessValidator()

# 检查必填字段
missing_fields = validator.check_required_fields(data, required_fields)

# 检查数据完整性
is_complete = await validator.validate_completeness(job_id)
```

### FieldValidator (字段验证)

```python
from shared.validators.field_validator import FieldValidator

validator = FieldValidator()

# 验证字段类型
is_valid = validator.validate_field_type(value, expected_type)

# 验证字段范围
is_valid = validator.validate_field_range(value, min_val, max_val)

# 验证字段格式
is_valid = validator.validate_field_format(value, pattern)
```

### ModificationValidator (修改验证)

```python
from shared.validators.modification_validator import ModificationValidator

validator = ModificationValidator()

# 验证修改权限
can_modify = await validator.can_modify(user, job_id)

# 验证修改数据
is_valid = await validator.validate_modification(old_data, new_data)
```

## 📡 消息队列 (message_queue.py)

### 功能概述

RabbitMQ 消息队列的封装。

### 使用方法

```python
from shared.message_queue import MessageQueue

mq = MessageQueue()

# 发布消息
await mq.publish(
    queue="job_processing",
    message={"job_id": "123", "action": "process"}
)

# 消费消息
async def callback(message):
    print(f"Received: {message}")

await mq.consume(
    queue="job_processing",
    callback=callback
)
```

### 队列定义

```python
QUEUES = {
    "job_processing": "任务处理队列",
    "cad_parsing": "CAD解析队列",
    "price_calculation": "价格计算队列",
    "notification": "通知队列"
}
```

## 📢 进度发布器 (progress_publisher.py)

### 功能概述

发布任务处理进度到 WebSocket 和 Redis。

### 使用方法

```python
from shared.progress_publisher import ProgressPublisher

publisher = ProgressPublisher()

# 发布进度
await publisher.publish_progress(
    job_id="job-123",
    stage="cad_parsing",
    progress=50,
    message="正在解析CAD文件..."
)

# 发布完成
await publisher.publish_completion(
    job_id="job-123",
    result={"success": True}
)

# 发布错误
await publisher.publish_error(
    job_id="job-123",
    error="处理失败"
)
```

## 🎯 进度阶段 (progress_stages.py)

### 阶段定义

```python
class ProgressStage:
    UPLOADING = "uploading"              # 上传中
    CAD_PARSING = "cad_parsing"          # CAD解析
    FEATURE_RECOGNITION = "feature_recognition"  # 特征识别
    PRICE_CALCULATION = "price_calculation"      # 价格计算
    REPORT_GENERATION = "report_generation"      # 报表生成
    COMPLETED = "completed"              # 完成
    FAILED = "failed"                    # 失败
```

### 阶段进度

```python
STAGE_PROGRESS = {
    ProgressStage.UPLOADING: (0, 10),
    ProgressStage.CAD_PARSING: (10, 30),
    ProgressStage.FEATURE_RECOGNITION: (30, 60),
    ProgressStage.PRICE_CALCULATION: (60, 80),
    ProgressStage.REPORT_GENERATION: (80, 95),
    ProgressStage.COMPLETED: (95, 100)
}
```

## 🔧 工艺代码映射 (process_code_mapping.py)

### 功能概述

工艺代码和名称的映射关系。

### 使用方法

```python
from shared.process_code_mapping import get_process_name, get_process_code

# 获取工艺名称
name = get_process_name("NC001")  # "数控铣削"

# 获取工艺代码
code = get_process_code("数控铣削")  # "NC001"
```

## 🌐 时区工具 (timezone_utils.py)

### 功能概述

时区转换和时间处理工具。

### 使用方法

```python
from shared.timezone_utils import (
    get_current_time,
    convert_to_utc,
    convert_from_utc,
    format_datetime
)

# 获取当前时间
now = get_current_time()

# 转换为 UTC
utc_time = convert_to_utc(local_time, "Asia/Shanghai")

# 从 UTC 转换
local_time = convert_from_utc(utc_time, "Asia/Shanghai")

# 格式化时间
formatted = format_datetime(now, "%Y-%m-%d %H:%M:%S")
```

## 🔌 MCP 客户端 (mcp_client.py)

### 功能概述

Model Context Protocol 客户端，用于调用 MCP 服务。

### 使用方法

```python
from shared.mcp_client import MCPClient

client = MCPClient(base_url="http://localhost:8200")

# 调用 CAD 解析服务
result = await client.call(
    service="cad_parser",
    method="parse",
    params={"file_path": "path/to/file.dwg"}
)

# 调用价格计算服务
result = await client.call(
    service="pricing",
    method="calculate",
    params={"job_id": "job-123"}
)
```

## 🧪 测试

### 单元测试

```bash
# 测试所有共享模块
pytest tests/shared/

# 测试特定模块
pytest tests/shared/test_database.py
pytest tests/shared/test_security.py
pytest tests/shared/test_validators.py
```

## 📝 配置

### 环境变量

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mold_cost_db
DB_USER=root
DB_PASSWORD=password

# Redis配置
REDIS_URL=redis://localhost:6379

# RabbitMQ配置
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672

# JWT配置
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

## 📚 相关文档

- [API Gateway 文档](../api_gateway/README.md)
- [Agents 文档](../agents/README.md)
- [Scripts 文档](../scripts/README.md)
- [主项目文档](../README.md)

## 🤝 贡献指南

1. 保持代码的通用性和可复用性
2. 添加完整的类型注解
3. 编写详细的文档字符串
4. 编写单元测试
5. 遵循现有的代码风格

## 📞 联系方式

如有问题，请联系 Shared 模块团队或提交 Issue。
