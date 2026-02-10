# mold_cost_account 合并到 mold_cost_ 详细方案

## 📋 项目概况

### 源项目：mold_cost_account
- **框架**: Flask 2.3.3
- **端口**: 8000
- **主要功能**: 
  - 用户登录认证 (JWT)
  - 工艺规则管理 (process_rules)
  - 价格项管理 (price_items)
  - 聊天会话管理 (chat_sessions)
- **数据库**: PostgreSQL (psycopg2, 同步)
- **特点**: 简单、直接、Flask蓝图架构

### 目标项目：mold_cost_
- **框架**: FastAPI
- **端口**: 8211
- **主要功能**: 
  - 任务管理 (jobs)
  - 特征识别 (features)
  - 价格计算 (pricing)
  - 交互管理 (interactions)
  - 审核系统 (reviews)
  - WebSocket实时通信
- **数据库**: PostgreSQL (asyncpg, 异步)
- **特点**: 异步、高性能、微服务架构

---

## 🎯 合并策略

### 核心原则
1. **保留 mold_cost_ 的架构**: FastAPI + 异步
2. **迁移 mold_cost_account 的功能**: 转换为 FastAPI 路由
3. **统一数据库访问**: 使用 mold_cost_ 的 shared/database.py
4. **统一认证机制**: 使用 mold_cost_ 的 JWT 配置
5. **保持向后兼容**: 保留原有 API 路径

---

## 📊 详细对比分析

### 1. 框架差异

| 对比项 | mold_cost_account | mold_cost_ | 合并策略 |
|--------|-------------------|------------|----------|
| Web框架 | Flask (同步) | FastAPI (异步) | ✅ 转换为 FastAPI |
| 路由方式 | Blueprint | APIRouter | ✅ 使用 APIRouter |
| 数据库驱动 | psycopg2 (同步) | asyncpg (异步) | ✅ 改用异步 |
| 请求处理 | request.get_json() | Pydantic models | ✅ 使用 Pydantic |
| 响应格式 | jsonify() | JSONResponse | ✅ 使用 FastAPI 响应 |

### 2. 目录结构对比

```
mold_cost_account/              mold_cost_/
├── app/                        ├── api_gateway/
│   ├── api/                    │   ├── routers/
│   │   ├── auth.py            │   │   ├── jobs.py
│   │   ├── process_rules.py   │   │   ├── interactions.py
│   │   ├── price_items.py     │   │   └── ...
│   │   └── chat_sessions.py   │   ├── models/
│   ├── models/                 │   ├── services/
│   ├── services/               │   └── utils/
│   │   └── database.py        ├── shared/
│   └── utils/                  │   ├── database.py
├── config/                     │   ├── models.py
│   └── config.py              │   └── ...
└── main.py                     └── agents/
```

### 3. API 端点对比

#### mold_cost_account 的 API (需要迁移)

| 功能模块 | 端点 | 方法 | 说明 |
|---------|------|------|------|
| **认证** | `/api/login` | POST | 用户登录 |
| | `/api/verify-token` | POST | Token验证 |
| | `/api/change-password` | POST | 修改密码 |
| **工艺规则** | `/api/process-rules` | POST | 创建规则 |
| | `/api/process-rules` | GET | 获取规则列表 |
| | `/api/process-rules/{id}` | GET | 获取单个规则 |
| | `/api/process-rules/{id}` | PUT | 更新规则 |
| | `/api/process-rules/{id}` | DELETE | 删除规则 |
| | `/api/process-rules/batch-delete` | POST | 批量删除 |
| | `/api/process-rules/by-version-type` | GET | 按版本类型查询 |
| **价格项** | `/api/price-items` | POST | 创建价格项 |
| | `/api/price-items` | GET | 获取价格项列表 |
| | `/api/price-items/{id}` | GET | 获取单个价格项 |
| | `/api/price-items/{id}` | PUT | 更新价格项 |
| | `/api/price-items/{id}` | DELETE | 删除价格项 |
| | `/api/price-items/batch-delete` | POST | 批量删除 |
| | `/api/price-items/by-version-category` | GET | 按版本类别查询 |
| **聊天会话** | `/api/chat-sessions/update-name` | PUT | 更新会话名称(按job) |
| | `/api/chat-sessions/{id}/name` | PUT | 更新会话名称 |
| | `/api/chat-sessions/{id}` | GET | 获取会话详情 |
| | `/api/chat-sessions/` | GET | 获取用户会话列表 |
| | `/api/chat-sessions/delete-by-job` | DELETE | 删除会话(按job) |
| | `/api/chat-sessions/{id}` | DELETE | 删除会话 |

#### mold_cost_ 现有 API (保留)

| 功能模块 | 端点 | 方法 | 说明 |
|---------|------|------|------|
| **任务** | `/api/v1/jobs` | POST | 创建任务 |
| | `/api/v1/jobs/{id}` | GET | 获取任务详情 |
| **交互** | `/api/interactions` | POST | 创建交互 |
| **审核** | `/api/reviews` | POST | 提交审核 |
| **WebSocket** | `/ws/{job_id}` | WS | 实时通信 |

---

## 🔄 合并执行计划

### 阶段一：准备工作 ✅

#### 1.1 创建新的路由文件
```
mold_cost_/api_gateway/routers/
├── auth.py              # 认证相关 (新建)
├── process_rules.py     # 工艺规则 (新建)
├── price_items.py       # 价格项 (新建)
└── chat_sessions.py     # 聊天会话 (新建)
```

#### 1.2 创建 Pydantic 模型
```
mold_cost_/api_gateway/models/
├── auth_models.py           # 认证模型
├── process_rule_models.py   # 工艺规则模型
├── price_item_models.py     # 价格项模型
└── chat_session_models.py   # 聊天会话模型
```

#### 1.3 创建服务层
```
mold_cost_/api_gateway/services/
├── auth_service.py          # 认证服务
├── process_rule_service.py  # 工艺规则服务
├── price_item_service.py    # 价格项服务
└── chat_session_service.py  # 聊天会话服务
```

### 阶段二：代码迁移

#### 2.1 认证模块迁移

**源文件**: `mold_cost_account/main.py` (AuthService类)
**目标文件**: `mold_cost_/api_gateway/services/auth_service.py`

**关键改动**:
1. ✅ 同步函数 → 异步函数 (async/await)
2. ✅ psycopg2 → shared.database (异步)
3. ✅ Flask request → FastAPI Request
4. ✅ jsonify() → Pydantic 响应模型

**示例转换**:
```python
# 原代码 (Flask + 同步)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    # ...
    return jsonify({'success': True, 'token': token})

# 新代码 (FastAPI + 异步)
@router.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    username = request.username
    # ...
    return LoginResponse(success=True, token=token)
```

#### 2.2 工艺规则模块迁移

**源文件**: `mold_cost_account/app/api/process_rules.py`
**目标文件**: `mold_cost_/api_gateway/routers/process_rules.py`

**关键改动**:
1. ✅ Blueprint → APIRouter
2. ✅ db_manager.execute_query() → shared.database 异步方法
3. ✅ 添加依赖注入 (Depends)
4. ✅ 使用 Pydantic 模型验证

**迁移清单**:
- [x] ProcessRuleService 类转换
- [x] 创建规则 API
- [x] 获取规则列表 API (分页)
- [x] 获取单个规则 API
- [x] 更新规则 API
- [x] 删除规则 API
- [x] 批量删除 API
- [x] 按版本类型查询 API

#### 2.3 价格项模块迁移

**源文件**: `mold_cost_account/app/api/price_items.py`
**目标文件**: `mold_cost_/api_gateway/routers/price_items.py`

**迁移清单**:
- [x] PriceItemService 类转换
- [x] 创建价格项 API
- [x] 获取价格项列表 API (分页)
- [x] 获取单个价格项 API
- [x] 更新价格项 API
- [x] 删除价格项 API
- [x] 批量删除 API
- [x] 按版本类别查询 API

#### 2.4 聊天会话模块迁移

**源文件**: `mold_cost_account/app/api/chat_sessions.py`
**目标文件**: `mold_cost_/api_gateway/routers/chat_sessions.py`

**迁移清单**:
- [x] ChatSessionService 类转换
- [x] 更新会话名称 API (按job_id)
- [x] 更新会话名称 API (按session_id)
- [x] 获取会话详情 API
- [x] 获取用户会话列表 API
- [x] 删除会话 API (按job_id)
- [x] 删除会话 API (按session_id)
- [x] 批量删除会话 API

### 阶段三：数据库整合

#### 3.1 数据库服务统一

**问题**: mold_cost_account 使用同步 psycopg2，mold_cost_ 使用异步 asyncpg

**解决方案**:
1. ✅ 使用 `mold_cost_/shared/database.py` 的异步连接池
2. ✅ 所有数据库操作改为异步
3. ✅ 统一使用 `get_db_connection()` 获取连接

**示例**:
```python
# 原代码 (同步)
result = db_manager.execute_query(query, params, fetch_one=True)

# 新代码 (异步)
from shared.database import get_db_connection
async with get_db_connection() as conn:
    result = await conn.fetchrow(query, *params)
```

#### 3.2 数据表确认

**需要确认的表**:
- ✅ users (用户表)
- ✅ process_rules (工艺规则表)
- ✅ price_items (价格项表)
- ✅ chat_sessions (聊天会话表)

**检查项**:
- [ ] 表结构是否存在
- [ ] 字段类型是否匹配
- [ ] 索引是否完整
- [ ] 外键约束是否正确

### 阶段四：配置整合

#### 4.1 环境变量合并

**源文件**: `mold_cost_account/config/.env`
**目标文件**: `mold_cost_/.env.main`

**需要合并的配置**:
```bash
# JWT配置 (已存在，需确认一致性)
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120

# 安全配置 (新增)
MAX_FAILED_LOGIN_ATTEMPTS=5
PASSWORD_HASH_ROUNDS=12
```

#### 4.2 配置类整合

**源文件**: `mold_cost_account/config/config.py`
**目标文件**: `mold_cost_/api_gateway/config.py`

**需要添加的配置项**:
```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 新增：认证配置
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    PASSWORD_HASH_ROUNDS: int = 12
    
    # 新增：会话配置
    CHAT_SESSION_TIMEOUT: int = 3600
```

### 阶段五：路由注册

#### 5.1 在 main.py 中注册新路由

**文件**: `mold_cost_/api_gateway/main.py`

**添加导入**:
```python
from .routers import (
    jobs, websocket_router, interactions, 
    review_router, chat_router, file_router,
    # 新增
    auth, process_rules, price_items, chat_sessions
)
```

**注册路由**:
```python
# 现有路由
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(interactions.router)
# ...

# 新增路由
app.include_router(auth.router, tags=["认证"])
app.include_router(process_rules.router, tags=["工艺规则"])
app.include_router(price_items.router, tags=["价格项"])
app.include_router(chat_sessions.router, tags=["聊天会话"])
```

#### 5.2 更新根路径端点信息

```python
@app.get("/")
async def root():
    return {
        "message": "Mold Cost System API Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            # 现有端点
            "jobs": "/api/v1/jobs",
            "features": "/api/features",
            # ...
            
            # 新增端点
            "auth": "/api/login",
            "process_rules": "/api/process-rules",
            "price_items": "/api/price-items",
            "chat_sessions": "/api/chat-sessions",
        }
    }
```

---

## 🔍 关键技术转换

### 1. 数据库查询转换

#### 同步 → 异步
```python
# 原代码 (psycopg2 同步)
def get_rule_by_id(self, rule_id):
    query = "SELECT * FROM process_rules WHERE id = %s"
    result = self.db.execute_query(query, (rule_id,), fetch_one=True)
    return result

# 新代码 (asyncpg 异步)
async def get_rule_by_id(self, rule_id: str):
    query = "SELECT * FROM process_rules WHERE id = $1"
    async with get_db_connection() as conn:
        result = await conn.fetchrow(query, rule_id)
    return result
```

### 2. 请求处理转换

#### Flask → FastAPI
```python
# 原代码 (Flask)
@app.route('/api/process-rules', methods=['POST'])
def create_rule():
    data = request.get_json()
    if 'id' not in data:
        return jsonify({'success': False, 'message': '缺少id'}), 400
    # ...
    return jsonify({'success': True, 'data': result}), 201

# 新代码 (FastAPI)
@router.post("/api/process-rules", response_model=ProcessRuleResponse)
async def create_rule(request: CreateProcessRuleRequest):
    # Pydantic 自动验证 id 字段
    result = await rule_service.create_rule(request)
    return ProcessRuleResponse(success=True, data=result)
```

### 3. 认证中间件转换

#### Flask装饰器 → FastAPI依赖注入
```python
# 原代码 (Flask)
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token'}), 401
        # ...
        return f(*args, **kwargs)
    return decorated

# 新代码 (FastAPI)
async def get_current_user(
    authorization: str = Header(None)
) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="No token")
    # ...
    return user

@router.get("/api/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    return {"user": user}
```

---

## 📝 迁移检查清单

### 代码迁移
- [ ] 认证模块 (auth.py)
  - [ ] 登录接口
  - [ ] Token验证接口
  - [ ] 修改密码接口
  - [ ] JWT工具函数
  - [ ] 密码加密函数

- [ ] 工艺规则模块 (process_rules.py)
  - [ ] ProcessRuleService 类
  - [ ] 创建规则 API
  - [ ] 查询规则 API (列表、单个、按条件)
  - [ ] 更新规则 API
  - [ ] 删除规则 API (硬删除、软删除)
  - [ ] 批量操作 API

- [ ] 价格项模块 (price_items.py)
  - [ ] PriceItemService 类
  - [ ] 创建价格项 API
  - [ ] 查询价格项 API (列表、单个、按条件)
  - [ ] 更新价格项 API
  - [ ] 删除价格项 API (硬删除、软删除)
  - [ ] 批量操作 API

- [ ] 聊天会话模块 (chat_sessions.py)
  - [ ] ChatSessionService 类
  - [ ] 会话管理 API (创建、查询、更新、删除)
  - [ ] 批量操作 API
  - [ ] 级联删除逻辑

### 数据库
- [ ] 确认表结构
  - [ ] users 表
  - [ ] process_rules 表
  - [ ] price_items 表
  - [ ] chat_sessions 表
- [ ] 数据迁移 (如需要)
- [ ] 索引优化
- [ ] 外键约束检查

### 配置
- [ ] 环境变量合并
- [ ] 配置类更新
- [ ] JWT密钥统一
- [ ] 数据库连接配置统一

### 测试
- [ ] 单元测试
  - [ ] 认证服务测试
  - [ ] 工艺规则服务测试
  - [ ] 价格项服务测试
  - [ ] 聊天会话服务测试
- [ ] 集成测试
  - [ ] API端点测试
  - [ ] 数据库操作测试
  - [ ] 认证流程测试
- [ ] 性能测试
  - [ ] 并发请求测试
  - [ ] 数据库连接池测试

### 文档
- [ ] API文档更新
- [ ] README更新
- [ ] 部署文档更新
- [ ] 迁移说明文档

---

## ⚠️ 风险与注意事项

### 1. 数据库兼容性
**风险**: 异步数据库驱动可能与现有查询不兼容
**缓解**: 
- 逐个模块测试
- 保留原项目作为参考
- 使用事务确保数据一致性

### 2. 认证机制差异
**风险**: JWT配置不一致导致token无法互通
**缓解**:
- 统一JWT_SECRET_KEY
- 统一token过期时间
- 统一token payload结构

### 3. API向后兼容
**风险**: 前端调用失败
**缓解**:
- 保持原有API路径不变
- 保持响应格式一致
- 提供API版本控制

### 4. 性能影响
**风险**: 异步转换可能影响性能
**缓解**:
- 使用连接池
- 优化数据库查询
- 添加缓存层

### 5. 并发安全
**风险**: 异步环境下的并发问题
**缓解**:
- 使用数据库事务
- 添加乐观锁
- 使用Redis分布式锁

---

## 🚀 部署计划

### 1. 开发环境测试
1. 在开发分支完成代码迁移
2. 本地测试所有API端点
3. 运行单元测试和集成测试
4. 性能测试

### 2. 测试环境部署
1. 部署到测试服务器
2. 前端联调测试
3. 压力测试
4. 安全测试

### 3. 生产环境部署
1. 数据库备份
2. 灰度发布 (10% → 50% → 100%)
3. 监控关键指标
4. 准备回滚方案

### 4. 监控指标
- API响应时间
- 数据库连接数
- 错误率
- 并发用户数
- 内存使用率

---

## 📚 参考文档

### 技术文档
- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [asyncpg文档](https://magicstack.github.io/asyncpg/)
- [Pydantic文档](https://docs.pydantic.dev/)

### 项目文档
- `mold_cost_/README.md` - 主项目说明
- `mold_cost_account/README.md` - 账户系统说明
- `mold_cost_account/docs/API_DOCUMENTATION.md` - API文档

---

## 📞 联系方式

如有问题，请联系：
- 架构负责人：[待填写]
- 后端负责人：[待填写]
- 数据库负责人：[待填写]

---

**文档版本**: v1.0
**创建日期**: 2026-02-10
**最后更新**: 2026-02-10
