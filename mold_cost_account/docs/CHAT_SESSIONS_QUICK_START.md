# 聊天会话 API 快速开始

## 快速测试

### 1. 登录获取 Token

```bash
curl -X POST "http://localhost:8000/api/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

响应示例：
```json
{
  "success": true,
  "message": "登录成功",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_info": {
    "user_id": "user_001",
    "username": "admin",
    "role": "admin"
  }
}
```

### 2. 根据任务ID更新会话名称（推荐）

```bash
curl -X PUT "http://localhost:8000/api/chat-sessions/update-name" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_001",
    "name": "我的新会话名称"
  }'
```

响应示例：
```json
{
  "success": true,
  "message": "会话名称更新成功",
  "data": {
    "session_id": "session_001",
    "job_id": "job_001",
    "user_id": "user_001",
    "name": "我的新会话名称",
    "status": "active",
    "metadata": {},
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T12:00:00"
  }
}
```

### 3. 获取会话列表

```bash
curl -X GET "http://localhost:8000/api/chat-sessions/?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Python 快速示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 登录
response = requests.post(
    f"{BASE_URL}/api/login",
    json={"username": "admin", "password": "admin123"}
)
token = response.json()["token"]

# 2. 更新会话名称
headers = {"Authorization": f"Bearer {token}"}
response = requests.put(
    f"{BASE_URL}/api/chat-sessions/update-name",
    headers=headers,
    json={"job_id": "job_001", "name": "新名称"}
)
print(response.json())
```

## JavaScript 快速示例

```javascript
const BASE_URL = 'http://localhost:8000';

// 1. 登录
const loginResponse = await fetch(`${BASE_URL}/api/login`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'admin', password: 'admin123'})
});
const {token} = await loginResponse.json();

// 2. 更新会话名称
const updateResponse = await fetch(`${BASE_URL}/api/chat-sessions/update-name`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({job_id: 'job_001', name: '新名称'})
});
const result = await updateResponse.json();
console.log(result);
```

## 常见错误

### 401 Unauthorized
- 检查 Token 是否正确
- 检查 Token 是否过期
- 确保 Authorization 头格式正确：`Bearer <token>`

### 404 Not Found
- 检查 job_id 或 session_id 是否存在
- 确认该会话属于当前登录用户

### 400 Bad Request
- 检查请求体格式是否正确
- 确保 name 字段不为空
- 确保 name 长度不超过 255 字符

## 完整文档

详细的 API 文档请查看：[CHAT_SESSIONS_API.md](./CHAT_SESSIONS_API.md)
