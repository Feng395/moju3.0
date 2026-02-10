# JWT (JSON Web Token) 完整指南

## 目录
- [JWT 简介](#jwt-简介)
- [JWT 结构](#jwt-结构)
- [项目中的JWT实现](#项目中的jwt实现)
- [JWT 配置](#jwt-配置)
- [JWT 使用流程](#jwt-使用流程)
- [API 接口详解](#api-接口详解)
- [JWT 安全最佳实践](#jwt-安全最佳实践)
- [常见问题与解决方案](#常见问题与解决方案)
- [测试示例](#测试示例)

---

## JWT 简介

JWT (JSON Web Token) 是一种开放标准 (RFC 7519)，用于在各方之间安全地传输信息。它是一种紧凑的、URL安全的方式来表示要在两方之间传输的声明。

### JWT 的优势

- **无状态**: 服务器不需要存储会话信息
- **跨域支持**: 可以在不同域名间使用
- **移动友好**: 适合移动应用和单页应用
- **性能好**: 避免了数据库查询验证
- **标准化**: 基于开放标准，支持广泛

### JWT 的应用场景

- **身份认证**: 用户登录后的身份验证
- **信息交换**: 安全地在各方之间传输信息
- **授权**: 访问受保护资源的权限控制

---

## JWT 结构

JWT 由三部分组成，用点 (.) 分隔：

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiIxMjM0NTY3OCIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTY0MDk5NTIwMH0.signature
```

### 1. Header (头部)
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```
- `alg`: 签名算法 (如 HS256, RS256)
- `typ`: 令牌类型 (JWT)

### 2. Payload (载荷)
```json
{
  "sub": "admin",           // 主题 (用户名)
  "user_id": "12345678",    // 用户ID
  "role": "admin",          // 用户角色
  "email": "admin@example.com",
  "real_name": "管理员",
  "iat": 1640995200,        // 签发时间
  "exp": 1640998800         // 过期时间
}
```

#### 标准声明 (Registered Claims)
- `iss` (issuer): 签发者
- `sub` (subject): 主题
- `aud` (audience): 受众
- `exp` (expiration time): 过期时间
- `nbf` (not before): 生效时间
- `iat` (issued at): 签发时间
- `jti` (JWT ID): JWT唯一标识

#### 自定义声明 (Private Claims)
- `user_id`: 用户ID
- `role`: 用户角色
- `email`: 用户邮箱
- `real_name`: 真实姓名

### 3. Signature (签名)
```
HMACSHA256(
  base64UrlEncode(header) + "." +
  base64UrlEncode(payload),
  secret
)
```

---

## 项目中的JWT实现

### 依赖库
```python
import jwt
from datetime import datetime, timedelta
```

### JWT 配置类
```python
class Config:
    JWT_SECRET_KEY = "your-secret-key-change-in-production-2024"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

### JWT 服务实现
```python
class AuthService:
    def create_access_token(self, data: dict) -> str:
        """创建JWT访问令牌"""
        if not JWT_AVAILABLE:
            logger.warning("JWT库未安装，无法生成token")
            return None
            
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"JWT token生成错误: {e}")
            return None
    
    def verify_token(self, token: str) -> dict:
        """验证JWT令牌"""
        if not JWT_AVAILABLE:
            return None
            
        try:
            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token已过期")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT token验证失败: {e}")
            return None
```

---

## JWT 配置

### 环境变量配置
```bash
# .env 文件
JWT_SECRET_KEY=your-very-secure-secret-key-here
JWT_EXPIRE_MINUTES=30
```

### 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| JWT_SECRET_KEY | string | - | JWT签名密钥（必须设置） |
| JWT_ALGORITHM | string | HS256 | 签名算法 |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | int | 30 | 令牌有效期（分钟） |

### 不同环境的配置

#### 开发环境
```python
class DevelopmentConfig(Config):
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1小时
    JWT_SECRET_KEY = "dev-secret-key"
```

#### 生产环境
```python
class ProductionConfig(Config):
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15分钟
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  # 必须从环境变量获取
```

---

## JWT 使用流程

### 1. 用户登录获取Token

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as 登录API
    participant DB as 数据库
    
    Client->>API: POST /api/login {username, password}
    API->>DB: 验证用户凭据
    DB-->>API: 返回用户信息
    API->>API: 生成JWT Token
    API-->>Client: 返回 {success, token, user_info}
```

### 2. 使用Token访问受保护资源

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as 受保护API
    
    Client->>API: Request + Authorization: Bearer <token>
    API->>API: 验证JWT Token
    alt Token有效
        API-->>Client: 返回受保护资源
    else Token无效/过期
        API-->>Client: 401 Unauthorized
    end
```

---

## API 接口详解

### 1. 登录接口 - 获取JWT Token

**接口**: `POST /api/login`

**请求示例**:
```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456"
  }'
```

**成功响应**:
```json
{
  "success": true,
  "message": "登录成功",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiIxMjM0NTY3OCIsInJvbGUiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AZXhhbXBsZS5jb20iLCJyZWFsX25hbWUiOiLnrqHnkIblkZgiLCJpYXQiOjE2NDA5OTUyMDAsImV4cCI6MTY0MDk5NzAwMH0.signature",
  "user_info": {
    "user_id": "12345678-1234-1234-1234-123456789012",
    "username": "admin",
    "email": "admin@example.com",
    "real_name": "管理员",
    "role": "admin",
    "department": "IT部门",
    "is_active": true,
    "last_login_at": "2024-01-13T12:00:00",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

**失败响应**:
```json
{
  "success": false,
  "message": "用户名或密码错误"
}
```

### 2. Token验证接口

**接口**: `POST /api/verify-token`

**请求示例**:
```bash
curl -X POST http://localhost:8000/api/verify-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**成功响应**:
```json
{
  "success": true,
  "message": "token有效",
  "payload": {
    "sub": "admin",
    "user_id": "12345678-1234-1234-1234-123456789012",
    "role": "admin",
    "email": "admin@example.com",
    "real_name": "管理员",
    "iat": 1640995200,
    "exp": 1640997000
  }
}
```

**失败响应**:
```json
{
  "success": false,
  "message": "token无效或已过期"
}
```

### 3. 在请求中使用JWT Token

#### Authorization Header 方式 (推荐)
```bash
curl -X GET http://localhost:8000/api/protected \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 请求体方式
```bash
curl -X POST http://localhost:8000/api/protected \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "data": "other_data"
  }'
```

---

## JWT 安全最佳实践

### 1. 密钥管理
```python
# ❌ 错误：硬编码密钥
JWT_SECRET_KEY = "123456"

# ✅ 正确：使用环境变量
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

# ✅ 正确：生成强密钥
import secrets
JWT_SECRET_KEY = secrets.token_urlsafe(32)
```

### 2. 过期时间设置
```python
# 根据应用场景设置合适的过期时间
ACCESS_TOKEN_EXPIRE_MINUTES = {
    'development': 60,    # 开发环境：1小时
    'production': 15,     # 生产环境：15分钟
    'mobile_app': 30,     # 移动应用：30分钟
    'web_app': 15         # Web应用：15分钟
}
```

### 3. 敏感信息处理
```python
# ❌ 错误：在JWT中存储敏感信息
payload = {
    "user_id": "123",
    "password": "secret",      # 不要存储密码
    "credit_card": "1234567890"  # 不要存储敏感数据
}

# ✅ 正确：只存储必要的非敏感信息
payload = {
    "sub": "username",
    "user_id": "123",
    "role": "admin",
    "email": "user@example.com"
}
```

### 4. HTTPS 传输
```python
# 生产环境必须使用HTTPS
if app.config['ENV'] == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
```

### 5. Token 刷新机制
```python
def refresh_token(old_token):
    """刷新JWT Token"""
    try:
        # 验证旧token（允许过期）
        payload = jwt.decode(old_token, SECRET_KEY, 
                           algorithms=[ALGORITHM], 
                           options={"verify_exp": False})
        
        # 检查是否在刷新窗口内
        if payload['exp'] + REFRESH_WINDOW > time.time():
            # 生成新token
            new_payload = {k: v for k, v in payload.items() 
                          if k not in ['exp', 'iat']}
            return create_access_token(new_payload)
    except jwt.JWTError:
        return None
```

---

## 常见问题与解决方案

### 1. Token过期处理

**问题**: 客户端收到401错误，token已过期

**解决方案**:
```javascript
// 前端处理示例
async function apiRequest(url, options = {}) {
    let token = localStorage.getItem('token');
    
    const response = await fetch(url, {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    
    if (response.status === 401) {
        // Token过期，重新登录
        localStorage.removeItem('token');
        window.location.href = '/login';
        return;
    }
    
    return response.json();
}
```

### 2. 时钟偏差问题

**问题**: 服务器时间不同步导致token验证失败

**解决方案**:
```python
# 添加时钟偏差容忍度
jwt.decode(token, SECRET_KEY, 
          algorithms=[ALGORITHM],
          leeway=timedelta(seconds=10))  # 允许10秒偏差
```

### 3. 密钥轮换

**问题**: 需要定期更换JWT密钥

**解决方案**:
```python
class JWTManager:
    def __init__(self):
        self.current_key = os.getenv('JWT_SECRET_KEY')
        self.old_keys = os.getenv('JWT_OLD_KEYS', '').split(',')
    
    def verify_token(self, token):
        # 先用当前密钥验证
        try:
            return jwt.decode(token, self.current_key, algorithms=['HS256'])
        except jwt.JWTError:
            # 用旧密钥验证
            for old_key in self.old_keys:
                try:
                    return jwt.decode(token, old_key, algorithms=['HS256'])
                except jwt.JWTError:
                    continue
            raise jwt.JWTError("Token验证失败")
```

### 4. 性能优化

**问题**: JWT验证影响性能

**解决方案**:
```python
import functools
from flask import g

@functools.lru_cache(maxsize=1000)
def verify_token_cached(token_hash):
    """缓存token验证结果"""
    return auth_service.verify_token(token_hash)

def get_current_user():
    """获取当前用户（带缓存）"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None
    
    # 使用token的哈希作为缓存键
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return verify_token_cached(token_hash)
```

---

## 测试示例

### Python 测试脚本

```python
import requests
import json
import time

class JWTTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        """登录获取token"""
        url = f"{self.base_url}/api/login"
        data = {"username": username, "password": password}
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('success'):
            self.token = result.get('token')
            print(f"✅ 登录成功，获取到token")
            return True
        else:
            print(f"❌ 登录失败: {result.get('message')}")
            return False
    
    def verify_token(self):
        """验证token"""
        if not self.token:
            print("❌ 没有token")
            return False
        
        url = f"{self.base_url}/api/verify-token"
        data = {"token": self.token}
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('success'):
            print(f"✅ Token验证成功")
            print(f"载荷: {json.dumps(result.get('payload'), indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ Token验证失败: {result.get('message')}")
            return False
    
    def test_expired_token(self):
        """测试过期token"""
        print("\n--- 测试Token过期 ---")
        print("等待token过期...")
        # 这里可以修改配置让token快速过期，或者等待
        time.sleep(2)  # 假设token很快过期
        self.verify_token()

# 运行测试
if __name__ == "__main__":
    tester = JWTTester()
    
    # 测试登录
    if tester.login("admin", "123456"):
        # 测试token验证
        tester.verify_token()
        
        # 测试过期token
        tester.test_expired_token()
```

### JavaScript 测试示例

```javascript
class JWTTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async login(username, password) {
        try {
            const response = await fetch(`${this.baseUrl}/api/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.token = result.token;
                console.log('✅ 登录成功，获取到token');
                localStorage.setItem('jwt_token', this.token);
                return true;
            } else {
                console.log(`❌ 登录失败: ${result.message}`);
                return false;
            }
        } catch (error) {
            console.error('登录请求失败:', error);
            return false;
        }
    }
    
    async verifyToken() {
        if (!this.token) {
            console.log('❌ 没有token');
            return false;
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/api/verify-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ token: this.token })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('✅ Token验证成功');
                console.log('载荷:', result.payload);
                return true;
            } else {
                console.log(`❌ Token验证失败: ${result.message}`);
                return false;
            }
        } catch (error) {
            console.error('Token验证请求失败:', error);
            return false;
        }
    }
    
    // 解析JWT token（仅用于调试）
    parseToken(token = this.token) {
        if (!token) return null;
        
        try {
            const parts = token.split('.');
            const header = JSON.parse(atob(parts[0]));
            const payload = JSON.parse(atob(parts[1]));
            
            return { header, payload };
        } catch (error) {
            console.error('Token解析失败:', error);
            return null;
        }
    }
}

// 使用示例
const tester = new JWTTester();
tester.login('admin', '123456').then(success => {
    if (success) {
        tester.verifyToken();
        
        // 解析token内容
        const parsed = tester.parseToken();
        console.log('Token内容:', parsed);
    }
});
```

---

## 总结

JWT是现代Web应用中重要的身份认证机制。本项目实现了完整的JWT功能，包括：

1. **Token生成**: 用户登录后生成包含用户信息的JWT
2. **Token验证**: 提供接口验证token有效性
3. **安全配置**: 支持环境变量配置，密钥管理
4. **错误处理**: 完善的异常处理和日志记录
5. **多环境支持**: 开发、测试、生产环境配置

通过合理使用JWT，可以构建安全、高效、可扩展的身份认证系统。