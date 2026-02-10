# mold_cost_account 合并执行详细计划

## 📋 执行概览

**目标**: 将 mold_cost_account (Flask) 的功能完整迁移到 mold_cost_ (FastAPI)
**预计时间**: 10个工作日
**执行方式**: 分阶段、可回滚、逐步验证

---

## 🎯 执行原则

1. **最小化风险**: 每个阶段独立可测试
2. **保持兼容**: API路径和响应格式不变
3. **逐步验证**: 完成一个模块测试一个模块
4. **可回滚**: 每个阶段都有回滚方案
5. **文档同步**: 代码和文档同步更新

---

## 📅 执行时间表

| 阶段 | 任务 | 预计时间 | 负责人 | 状态 |
|------|------|----------|--------|------|
| 阶段0 | 环境准备与分析 | 0.5天 | 架构师 | ⬜ 未开始 |
| 阶段1 | 基础设施搭建 | 1天 | 后端 | ⬜ 未开始 |
| 阶段2 | 认证模块迁移 | 2天 | 后端 | ⬜ 未开始 |
| 阶段3 | 工艺规则迁移 | 1.5天 | 后端 | ⬜ 未开始 |
| 阶段4 | 价格项迁移 | 1.5天 | 后端 | ⬜ 未开始 |
| 阶段5 | 聊天会话迁移 | 2天 | 后端 | ⬜ 未开始 |
| 阶段6 | 集成测试 | 1天 | 测试 | ⬜ 未开始 |
| 阶段7 | 部署上线 | 0.5天 | 运维 | ⬜ 未开始 |

**总计**: 10个工作日

---

## 🔧 阶段0: 环境准备与分析 (0.5天)

### 目标
- 确认数据库表结构
- 备份现有数据
- 创建开发分支
- 准备测试环境

### 执行步骤

#### 步骤 0.1: 数据库表结构确认
```bash
# 连接数据库
psql -h 192.168.1.54 -U root -d mold_cost_db

# 检查表是否存在
\dt users
\dt process_rules
\dt price_items
\dt chat_sessions

# 查看表结构
\d users
\d process_rules
\d price_items
\d chat_sessions
```

**检查清单**:
- [ ] users 表存在且结构正确
- [ ] process_rules 表存在且结构正确
- [ ] price_items 表存在且结构正确
- [ ] chat_sessions 表存在且结构正确
- [ ] 所有必要的索引已创建
- [ ] 外键约束正确设置

#### 步骤 0.2: 数据备份
```bash
# 备份整个数据库
pg_dump -h 192.168.1.54 -U root -d mold_cost_db > backup_$(date +%Y%m%d).sql

# 备份特定表
pg_dump -h 192.168.1.54 -U root -d mold_cost_db -t users -t process_rules \
  -t price_items -t chat_sessions > backup_account_tables_$(date +%Y%m%d).sql
```

**验证**:
- [ ] 备份文件已创建
- [ ] 备份文件大小合理
- [ ] 备份文件可以恢复

#### 步骤 0.3: 创建开发分支
```bash
cd mold_cost_
git checkout -b feature/merge-account-system
git push -u origin feature/merge-account-system
```

#### 步骤 0.4: 环境变量检查
```bash
# 检查 mold_cost_/.env.main
cat mold_cost_/.env.main | grep -E "JWT|DB_"

# 检查 mold_cost_account/config/.env
cat mold_cost_account/config/.env | grep -E "JWT|DB_"
```

**确认项**:
- [ ] 数据库连接信息一致
- [ ] JWT密钥需要统一
- [ ] 端口不冲突

### 交付物
- [ ] 数据库备份文件
- [ ] 开发分支已创建
- [ ] 环境检查报告

---

## 🏗️ 阶段1: 基础设施搭建 (1天)

### 目标
- 创建目录结构
- 创建Pydantic模型
- 创建基础工具函数
- 更新配置文件

### 执行步骤

#### 步骤 1.1: 创建目录结构
```bash
cd mold_cost_/api_gateway

# 创建新的路由目录
mkdir -p routers/account

# 创建模型目录
mkdir -p models/account

# 创建服务目录
mkdir -p services/account

# 创建工具目录
mkdir -p utils/account
```

**目录结构**:
```
mold_cost_/api_gateway/
├── routers/
│   └── account/
│       ├── __init__.py
│       ├── auth.py
│       ├── process_rules.py
│       ├── price_items.py
│       └── chat_sessions.py
├── models/
│   └── account/
│       ├── __init__.py
│       ├── auth_models.py
│       ├── process_rule_models.py
│       ├── price_item_models.py
│       └── chat_session_models.py
├── services/
│   └── account/
│       ├── __init__.py
│       ├── auth_service.py
│       ├── process_rule_service.py
│       ├── price_item_service.py
│       └── chat_session_service.py
└── utils/
    └── account/
        ├── __init__.py
        ├── password.py
        └── jwt_helper.py
```

#### 步骤 1.2: 创建 Pydantic 模型文件

**文件**: `api_gateway/models/account/__init__.py`

```python
"""账户系统模型包"""
from .auth_models import *
from .process_rule_models import *
from .price_item_models import *
from .chat_session_models import *
```

**文件**: `api_gateway/models/account/auth_models.py`
```python
"""认证相关的Pydantic模型"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)

class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str
    token: Optional[str] = None
    user_info: Optional[dict] = None

class VerifyTokenRequest(BaseModel):
    """验证Token请求"""
    token: str

class VerifyTokenResponse(BaseModel):
    """验证Token响应"""
    success: bool
    message: str
    payload: Optional[dict] = None

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    new_password: str = Field(..., min_length=6)

class ChangePasswordResponse(BaseModel):
    """修改密码响应"""
    success: bool
    message: str
```

**文件**: `api_gateway/models/account/process_rule_models.py`
```python
"""工艺规则相关的Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProcessRuleBase(BaseModel):
    """工艺规则基础模型"""
    id: str = Field(..., max_length=50)
    version_id: str = Field(default="v1.0", max_length=20)
    feature_type: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    priority: int = Field(default=1)
    is_active: bool = Field(default=True)
    conditions: str = Field(..., max_length=255)
    output_params: str = Field(..., max_length=255)

class CreateProcessRuleRequest(ProcessRuleBase):
    """创建工艺规则请求"""
    pass

class UpdateProcessRuleRequest(BaseModel):
    """更新工艺规则请求"""
    version_id: Optional[str] = Field(None, max_length=20)
    feature_type: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    conditions: Optional[str] = Field(None, max_length=255)
    output_params: Optional[str] = Field(None, max_length=255)

class ProcessRuleResponse(BaseModel):
    """工艺规则响应"""
    id: str
    version_id: str
    feature_type: str
    name: str
    description: Optional[str]
    priority: int
    is_active: bool
    conditions: str
    output_params: str
    created_at: datetime

class ProcessRuleListResponse(BaseModel):
    """工艺规则列表响应"""
    success: bool
    message: str
    data: dict  # {total, page, page_size, total_pages, data: List[ProcessRuleResponse]}

class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[str] = Field(..., min_items=1)
```

**文件**: `api_gateway/models/account/price_item_models.py`
```python
"""价格项相关的Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class PriceItemBase(BaseModel):
    """价格项基础模型"""
    id: str = Field(..., max_length=50)
    version_id: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=100)
    price: Optional[Decimal] = None
    unit: Optional[str] = Field(None, max_length=20)
    work_hours: Optional[Decimal] = None
    min_num: Optional[Decimal] = None
    add_price: Optional[Decimal] = None
    weight_num: Optional[Decimal] = None
    note: Optional[str] = None
    instruction: Optional[str] = None
    is_active: bool = Field(default=True)
    created_by: Optional[str] = Field(None, max_length=50)

class CreatePriceItemRequest(PriceItemBase):
    """创建价格项请求"""
    pass

class UpdatePriceItemRequest(BaseModel):
    """更新价格项请求"""
    version_id: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    price: Optional[Decimal] = None
    unit: Optional[str] = None
    work_hours: Optional[Decimal] = None
    min_num: Optional[Decimal] = None
    add_price: Optional[Decimal] = None
    weight_num: Optional[Decimal] = None
    note: Optional[str] = None
    instruction: Optional[str] = None
    is_active: Optional[bool] = None
    created_by: Optional[str] = None

class PriceItemResponse(BaseModel):
    """价格项响应"""
    id: str
    version_id: Optional[str]
    category: Optional[str]
    sub_category: Optional[str]
    price: Optional[Decimal]
    unit: Optional[str]
    work_hours: Optional[Decimal]
    min_num: Optional[Decimal]
    add_price: Optional[Decimal]
    weight_num: Optional[Decimal]
    note: Optional[str]
    instruction: Optional[str]
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

class PriceItemListResponse(BaseModel):
    """价格项列表响应"""
    success: bool
    message: str
    data: dict
```

**文件**: `api_gateway/models/account/chat_session_models.py`
```python
"""聊天会话相关的Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UpdateSessionNameRequest(BaseModel):
    """更新会话名称请求"""
    name: str = Field(..., max_length=200)

class UpdateSessionNameByJobRequest(BaseModel):
    """根据job_id更新会话名称请求"""
    job_id: str
    name: str = Field(..., max_length=200)

class DeleteSessionByJobRequest(BaseModel):
    """根据job_id删除会话请求"""
    job_id: str

class BatchDeleteSessionsRequest(BaseModel):
    """批量删除会话请求"""
    job_ids: List[str] = Field(..., min_items=1, max_items=100)

class ChatSessionResponse(BaseModel):
    """聊天会话响应"""
    session_id: str
    job_id: str
    user_id: str
    name: Optional[str]
    status: str
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

class ChatSessionListResponse(BaseModel):
    """聊天会话列表响应"""
    success: bool
    message: str
    data: dict  # {sessions: List[ChatSessionResponse], total, limit, offset}
```

#### 步骤 1.3: 创建工具函数

**文件**: `api_gateway/utils/account/password.py`
```python
"""密码加密工具"""
import hashlib
import bcrypt
from typing import Tuple

def hash_password_bcrypt(password: str) -> str:
    """使用bcrypt加密密码"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def hash_password_sha256(password: str) -> str:
    """使用SHA256加密密码（用于兼容旧数据）"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """验证密码"""
    try:
        # 检查是否是bcrypt哈希
        if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
            return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
        else:
            # 简单哈希比较（用于测试）
            return hash_password_sha256(plain_password) == stored_hash
    except Exception:
        return False
```

**文件**: `api_gateway/utils/account/jwt_helper.py`
```python
"""JWT工具函数"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from api_gateway.config import settings

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

def get_current_user_from_token(token: str) -> Optional[Dict]:
    """从token中获取当前用户信息"""
    payload = verify_token(token)
    if payload is None:
        return None
    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "email": payload.get("email"),
        "real_name": payload.get("real_name")
    }
```

#### 步骤 1.4: 更新配置文件

**文件**: `api_gateway/config.py`

添加以下配置项：
```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 认证配置
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    PASSWORD_HASH_ROUNDS: int = 12
    
    # 会话配置
    CHAT_SESSION_TIMEOUT: int = 3600
    
    # ... 其他配置 ...
```

#### 步骤 1.5: 创建依赖注入函数

**文件**: `api_gateway/dependencies.py`
```python
"""FastAPI依赖注入"""
from fastapi import Header, HTTPException, Depends
from typing import Optional
from api_gateway.utils.account.jwt_helper import get_current_user_from_token

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """获取当前用户（依赖注入）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少认证token")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token格式错误")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user_from_token(token)
    
    if user is None:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """获取当前激活用户"""
    # 可以添加额外的检查，如用户是否被禁用
    return current_user
```

### 验证清单
- [ ] 所有目录已创建
- [ ] 所有模型文件已创建且无语法错误
- [ ] 工具函数已创建且可导入
- [ ] 配置文件已更新
- [ ] 依赖注入函数已创建

### 交付物
- [ ] 完整的目录结构
- [ ] 所有Pydantic模型文件
- [ ] 工具函数文件
- [ ] 更新后的配置文件

---

## 🔐 阶段2: 认证模块迁移 (2天)

### 目标
- 迁移登录功能
- 迁移Token验证功能
- 迁移修改密码功能
- 完成单元测试

### 执行步骤

#### 步骤 2.1: 创建认证服务

**文件**: `api_gateway/services/account/auth_service.py`

```python
"""认证服务"""
import logging
from datetime import datetime
from typing import Tuple, Optional
from shared.database import get_db_connection
from api_gateway.utils.account.password import verify_password, hash_password_bcrypt
from api_gateway.utils.account.jwt_helper import create_access_token
from api_gateway.config import settings

logger = logging.getLogger(__name__)

class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.max_failed_attempts = settings.MAX_FAILED_LOGIN_ATTEMPTS
    
    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取用户信息"""
        query = """
        SELECT user_id, username, password_hash, email, real_name, role, 
               department, is_active, is_locked, failed_login_attempts,
               last_login_at, created_at
        FROM users 
        WHERE username = $1
        """
        async with get_db_connection() as conn:
            result = await conn.fetchrow(query, username)
            return dict(result) if result else None
    
    async def update_login_info(self, user_id: str, client_ip: str, success: bool = True):
        """更新登录信息"""
        try:
            if success:
                query = """
                UPDATE users 
                SET last_login_at = $1, last_login_ip = $2, 
                    failed_login_attempts = 0, is_locked = false,
                    updated_at = $3
                WHERE user_id = $4
                """
                params = (datetime.now(), client_ip, datetime.now(), user_id)
            else:
                query = """
                UPDATE users 
                SET failed_login_attempts = failed_login_attempts + 1,
                    is_locked = CASE 
                        WHEN failed_login_attempts + 1 >= $1 THEN true 
                        ELSE is_locked 
                    END,
                    updated_at = $2
                WHERE user_id = $3
                """
                params = (self.max_failed_attempts, datetime.now(), user_id)
            
            async with get_db_connection() as conn:
                await conn.execute(query, *params)
        except Exception as e:
            logger.error(f"更新登录信息错误: {e}")
    
    async def authenticate_user(
        self, username: str, password: str, client_ip: str
    ) -> Tuple[bool, str, Optional[dict]]:
        """用户认证"""
        try:
            # 获取用户信息
            user = await self.get_user_by_username(username)
            if not user:
                return False, "用户名或密码错误", None
            
            # 检查账号状态
            if not user['is_active']:
                return False, "账号已被禁用", None
            
            if user['is_locked']:
                return False, "账号已被锁定，请联系管理员", None
            
            # 验证密码
            if not verify_password(password, user['password_hash']):
                # 更新失败登录信息
                await self.update_login_info(str(user['user_id']), client_ip, success=False)
                
                failed_attempts = user['failed_login_attempts'] + 1
                if failed_attempts >= self.max_failed_attempts:
                    return False, "密码错误次数过多，账号已被锁定", None
                else:
                    return False, f"用户名或密码错误，还有{self.max_failed_attempts - failed_attempts}次机会", None
            
            # 登录成功
            await self.update_login_info(str(user['user_id']), client_ip, success=True)
            
            # 准备用户信息
            user_info = {
                'user_id': str(user['user_id']),
                'username': user['username'],
                'email': user['email'],
                'real_name': user['real_name'],
                'role': user['role'],
                'department': user['department'],
                'is_active': user['is_active'],
                'last_login_at': user['last_login_at'].isoformat() if user['last_login_at'] else None,
                'created_at': user['created_at'].isoformat() if user['created_at'] else None
            }
            
            return True, "登录成功", user_info
            
        except Exception as e:
            logger.error(f"用户认证错误: {e}")
            return False, "系统错误，请稍后重试", None
    
    async def change_password(
        self, user_id: str, new_password: str
    ) -> Tuple[bool, str]:
        """修改密码"""
        try:
            # 获取当前用户的密码哈希
            query_user = "SELECT password_hash FROM users WHERE user_id = $1"
            async with get_db_connection() as conn:
                user = await conn.fetchrow(query_user, user_id)
            
            if not user:
                return False, "用户不存在"
            
            # 检查新密码是否与当前密码相同
            if verify_password(new_password, user['password_hash']):
                return False, "新密码不能与当前密码相同"
            
            # 加密新密码
            password_hash = hash_password_bcrypt(new_password)
            
            # 更新密码
            query = """
            UPDATE users 
            SET password_hash = $1, updated_at = $2
            WHERE user_id = $3
            RETURNING user_id, username
            """
            async with get_db_connection() as conn:
                result = await conn.fetchrow(query, password_hash, datetime.now(), user_id)
            
            if result:
                logger.info(f"用户 {result['username']} (ID: {user_id}) 修改密码成功")
                return True, "密码修改成功"
            else:
                return False, "用户不存在"
                
        except Exception as e:
            logger.error(f"修改密码错误: {e}")
            return False, "系统错误，请稍后重试"

# 创建服务实例
auth_service = AuthService()
```

#### 步骤 2.2: 创建认证路由

**文件**: `api_gateway/routers/account/auth.py`
```python
"""认证路由"""
from fastapi import APIRouter, Request, Depends, HTTPException
from api_gateway.models.account.auth_models import (
    LoginRequest, LoginResponse,
    VerifyTokenRequest, VerifyTokenResponse,
    ChangePasswordRequest, ChangePasswordResponse
)
from api_gateway.services.account.auth_service import auth_service
from api_gateway.utils.account.jwt_helper import create_access_token, verify_token
from api_gateway.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@router.post("/api/login", response_model=LoginResponse, tags=["认证"])
async def login(request: LoginRequest, req: Request):
    """
    用户登录接口
    
    - **username**: 用户名
    - **password**: 密码
    """
    client_ip = get_client_ip(req)
    
    # 用户认证
    success, message, user_info = await auth_service.authenticate_user(
        request.username, request.password, client_ip
    )
    
    if success:
        # 创建JWT令牌
        token_data = {
            "sub": user_info["username"],
            "user_id": user_info["user_id"],
            "role": user_info["role"],
            "email": user_info.get("email"),
            "real_name": user_info.get("real_name")
        }
        access_token = create_access_token(token_data)
        
        logger.info(f"用户 {request.username} 登录成功，IP: {client_ip}")
        return LoginResponse(
            success=True,
            message=message,
            token=access_token,
            user_info=user_info
        )
    else:
        logger.warning(f"用户 {request.username} 登录失败: {message}，IP: {client_ip}")
        return LoginResponse(success=False, message=message)

@router.post("/api/verify-token", response_model=VerifyTokenResponse, tags=["认证"])
async def verify_token_endpoint(request: VerifyTokenRequest):
    """
    验证JWT令牌
    
    - **token**: JWT令牌
    """
    payload = verify_token(request.token)
    
    if payload:
        return VerifyTokenResponse(
            success=True,
            message="token有效",
            payload=payload
        )
    else:
        return VerifyTokenResponse(
            success=False,
            message="token无效或已过期"
        )

@router.post("/api/change-password", response_model=ChangePasswordResponse, tags=["认证"])
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    修改密码接口（需要token认证）
    
    - **new_password**: 新密码（至少6个字符）
    """
    user_id = current_user.get("user_id")
    username = current_user.get("username")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="token中缺少用户信息")
    
    # 修改密码
    success, message = await auth_service.change_password(user_id, request.new_password)
    
    if success:
        logger.info(f"用户 {username} (ID: {user_id}) 修改密码成功")
        return ChangePasswordResponse(success=True, message=message)
    else:
        status_code = 404 if "不存在" in message else 400
        raise HTTPException(status_code=status_code, detail=message)
```

#### 步骤 2.3: 注册认证路由

**文件**: `api_gateway/main.py`

添加导入和注册：
```python
# 导入
from .routers.account import auth

# 注册路由
app.include_router(auth.router, tags=["认证"])
```

#### 步骤 2.4: 创建单元测试

**文件**: `tests/test_auth.py`
```python
"""认证模块测试"""
import pytest
from httpx import AsyncClient
from api_gateway.main import app

@pytest.mark.asyncio
async def test_login_success():
    """测试登录成功"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"] is not None

@pytest.mark.asyncio
async def test_login_wrong_password():
    """测试登录失败-密码错误"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "密码错误" in data["message"]

@pytest.mark.asyncio
async def test_verify_token():
    """测试Token验证"""
    # 先登录获取token
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_response = await client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["token"]
        
        # 验证token
        verify_response = await client.post(
            "/api/verify-token",
            json={"token": token}
        )
        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data["success"] is True
        assert data["payload"] is not None
```

#### 步骤 2.5: 手动测试

使用Postman或curl测试：

```bash
# 测试登录
curl -X POST http://localhost:8211/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 测试Token验证
curl -X POST http://localhost:8211/api/verify-token \
  -H "Content-Type: application/json" \
  -d '{"token":"YOUR_TOKEN_HERE"}'

# 测试修改密码
curl -X POST http://localhost:8211/api/change-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"new_password":"newpassword123"}'
```

### 验证清单
- [ ] 登录接口正常工作
- [ ] Token验证接口正常工作
- [ ] 修改密码接口正常工作
- [ ] 单元测试全部通过
- [ ] 手动测试全部通过
- [ ] 日志记录正常

### 交付物
- [ ] 认证服务代码
- [ ] 认证路由代码
- [ ] 单元测试代码
- [ ] 测试报告

---

## 📋 阶段3: 工艺规则迁移 (1.5天)

### 目标
- 迁移工艺规则CRUD功能
- 迁移批量操作功能
- 完成单元测试

### 执行步骤

#### 步骤 3.1: 创建工艺规则服务

**文件**: `api_gateway/services/account/process_rule_service.py`

参考 `mold_cost_account/app/api/process_rules.py` 中的 `ProcessRuleService` 类，转换为异步版本。

**关键改动**:
1. 所有方法添加 `async`
2. 数据库查询使用 `get_db_connection()`
3. 使用 `await` 调用异步方法

#### 步骤 3.2: 创建工艺规则路由

**文件**: `api_gateway/routers/account/process_rules.py`

实现以下端点：
- POST `/api/process-rules` - 创建规则
- GET `/api/process-rules` - 获取规则列表（分页）
- GET `/api/process-rules/{id}` - 获取单个规则
- PUT `/api/process-rules/{id}` - 更新规则
- DELETE `/api/process-rules/{id}` - 删除规则
- POST `/api/process-rules/batch-delete` - 批量删除
- GET `/api/process-rules/by-version-type` - 按版本类型查询

#### 步骤 3.3: 注册路由

在 `api_gateway/main.py` 中注册：
```python
from .routers.account import process_rules
app.include_router(process_rules.router, tags=["工艺规则"])
```

#### 步骤 3.4: 创建单元测试

**文件**: `tests/test_process_rules.py`

测试所有CRUD操作和批量操作。

#### 步骤 3.5: 手动测试

使用Postman测试所有端点。

### 验证清单
- [ ] 创建规则接口正常
- [ ] 查询规则接口正常（列表、单个、按条件）
- [ ] 更新规则接口正常
- [ ] 删除规则接口正常
- [ ] 批量操作接口正常
- [ ] 单元测试全部通过
- [ ] 手动测试全部通过

### 交付物
- [ ] 工艺规则服务代码
- [ ] 工艺规则路由代码
- [ ] 单元测试代码
- [ ] 测试报告

---

## 💰 阶段4: 价格项迁移 (1.5天)

### 目标
- 迁移价格项CRUD功能
- 迁移批量操作功能
- 完成单元测试

### 执行步骤

与阶段3类似，迁移价格项模块。

**文件**:
- `api_gateway/services/account/price_item_service.py`
- `api_gateway/routers/account/price_items.py`
- `tests/test_price_items.py`

### 验证清单
- [ ] 创建价格项接口正常
- [ ] 查询价格项接口正常
- [ ] 更新价格项接口正常
- [ ] 删除价格项接口正常
- [ ] 批量操作接口正常
- [ ] 单元测试全部通过

### 交付物
- [ ] 价格项服务代码
- [ ] 价格项路由代码
- [ ] 单元测试代码
- [ ] 测试报告

---

## 💬 阶段5: 聊天会话迁移 (2天)

### 目标
- 迁移聊天会话管理功能
- 迁移级联删除功能
- 完成单元测试

### 执行步骤

#### 步骤 5.1: 创建聊天会话服务

**文件**: `api_gateway/services/account/chat_session_service.py`

参考 `mold_cost_account/app/services/chat_session_service.py`，转换为异步版本。

**特别注意**:
- 级联删除逻辑需要仔细处理
- 批量删除需要异步并发处理

#### 步骤 5.2: 创建聊天会话路由

**文件**: `api_gateway/routers/account/chat_sessions.py`

实现以下端点：
- PUT `/api/chat-sessions/update-name` - 更新会话名称(按job_id)
- PUT `/api/chat-sessions/{id}/name` - 更新会话名称
- GET `/api/chat-sessions/{id}` - 获取会话详情
- GET `/api/chat-sessions/` - 获取用户会话列表
- DELETE `/api/chat-sessions/delete-by-job` - 删除会话(按job_id)
- DELETE `/api/chat-sessions/{id}` - 删除会话
- POST `/api/chat-sessions/batch-delete-by-job` - 批量删除

#### 步骤 5.3: 注册路由

#### 步骤 5.4: 创建单元测试

**文件**: `tests/test_chat_sessions.py`

重点测试：
- 级联删除功能
- 批量删除功能
- 权限验证

#### 步骤 5.5: 手动测试

### 验证清单
- [ ] 会话管理接口正常
- [ ] 级联删除功能正常
- [ ] 批量删除功能正常
- [ ] 权限验证正常
- [ ] 单元测试全部通过

### 交付物
- [ ] 聊天会话服务代码
- [ ] 聊天会话路由代码
- [ ] 单元测试代码
- [ ] 测试报告

---

## 🧪 阶段6: 集成测试 (1天)

### 目标
- 完整的端到端测试
- 性能测试
- 前端联调

### 执行步骤

#### 步骤 6.1: 端到端测试

创建完整的业务流程测试：
1. 用户登录
2. 创建工艺规则
3. 创建价格项
4. 创建聊天会话
5. 查询数据
6. 更新数据
7. 删除数据

#### 步骤 6.2: 性能测试

使用 `locust` 或 `ab` 进行压力测试：
```python
# locustfile.py
from locust import HttpUser, task, between

class MoldCostUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # 登录获取token
        response = self.client.post("/api/login", json={
            "username": "admin",
            "password": "admin123"
        })
        self.token = response.json()["token"]
    
    @task
    def get_process_rules(self):
        self.client.get(
            "/api/process-rules",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

运行测试：
```bash
locust -f locustfile.py --host=http://localhost:8211
```

#### 步骤 6.3: 前端联调

与前端团队协调，测试所有API接口。

### 验证清单
- [ ] 端到端测试通过
- [ ] 性能测试达标（响应时间<200ms，并发>100）
- [ ] 前端联调成功
- [ ] 无内存泄漏
- [ ] 无数据库连接泄漏

### 交付物
- [ ] 集成测试报告
- [ ] 性能测试报告
- [ ] 前端联调报告

---

## 🚀 阶段7: 部署上线 (0.5天)

### 目标
- 部署到生产环境
- 监控系统运行
- 准备回滚方案

### 执行步骤

#### 步骤 7.1: 代码合并

```bash
# 合并到主分支
git checkout main
git merge feature/merge-account-system
git push origin main
```

#### 步骤 7.2: 部署

```bash
# 拉取最新代码
cd /path/to/mold_cost_
git pull origin main

# 重启服务
systemctl restart mold-cost-api-gateway

# 或使用Docker
docker-compose down
docker-compose up -d --build
```

#### 步骤 7.3: 监控

监控以下指标：
- API响应时间
- 错误率
- 数据库连接数
- 内存使用率
- CPU使用率

#### 步骤 7.4: 回滚方案

如果出现问题，执行回滚：
```bash
# 回滚代码
git revert HEAD
git push origin main

# 重启服务
systemctl restart mold-cost-api-gateway

# 恢复数据库（如需要）
psql -h 192.168.1.54 -U root -d mold_cost_db < backup_YYYYMMDD.sql
```

### 验证清单
- [ ] 代码已合并到主分支
- [ ] 服务已部署到生产环境
- [ ] 所有API端点正常工作
- [ ] 监控系统正常
- [ ] 回滚方案已准备

### 交付物
- [ ] 部署文档
- [ ] 监控报告
- [ ] 回滚方案文档

---

## 📊 进度跟踪

### 每日站会

每天早上10:00进行站会，汇报：
1. 昨天完成的工作
2. 今天计划的工作
3. 遇到的问题和阻碍

### 进度报告

每个阶段完成后，提交进度报告：
- 完成的任务
- 遇到的问题
- 解决方案
- 下一步计划

### 风险管理

| 风险 | 影响 | 概率 | 缓解措施 | 负责人 |
|------|------|------|----------|--------|
| 数据库兼容性问题 | 高 | 中 | 提前测试，准备回滚 | DBA |
| 性能下降 | 中 | 低 | 性能测试，优化查询 | 后端 |
| API不兼容 | 高 | 低 | 保持路径和格式一致 | 后端 |
| 前端调用失败 | 高 | 中 | 充分联调测试 | 前端+后端 |

---

## ✅ 最终验收标准

### 功能验收
- [ ] 所有API端点正常工作
- [ ] 响应格式与原系统一致
- [ ] 认证机制正常
- [ ] 数据库操作正常
- [ ] 错误处理完善

### 性能验收
- [ ] API响应时间 < 200ms (P95)
- [ ] 并发支持 > 100 QPS
- [ ] 无内存泄漏
- [ ] 无数据库连接泄漏

### 测试验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试全部通过
- [ ] 性能测试达标
- [ ] 前端联调成功

### 文档验收
- [ ] API文档已更新
- [ ] 部署文档已更新
- [ ] 代码注释完整
- [ ] README已更新

---

## 📞 联系方式

### 团队成员

| 角色 | 姓名 | 联系方式 | 职责 |
|------|------|----------|------|
| 架构师 | [待填写] | [待填写] | 技术方案、架构设计 |
| 后端负责人 | [待填写] | [待填写] | 代码实现、测试 |
| 前端负责人 | [待填写] | [待填写] | 前端联调 |
| DBA | [待填写] | [待填写] | 数据库支持 |
| 测试负责人 | [待填写] | [待填写] | 测试计划、执行 |
| 运维负责人 | [待填写] | [待填写] | 部署、监控 |

### 沟通渠道
- 日常沟通：企业微信群
- 紧急问题：电话
- 文档共享：Git仓库
- 进度跟踪：Jira/Trello

---

**文档版本**: v1.0
**创建日期**: 2026-02-10
**最后更新**: 2026-02-10
**下次审查**: 每个阶段完成后
