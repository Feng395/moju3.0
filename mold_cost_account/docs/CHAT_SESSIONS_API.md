# 聊天会话 API 文档

## 概述

聊天会话 API 提供了管理聊天会话的功能，包括更新会话名称、获取会话详情和会话列表。

所有接口都需要 JWT Token 认证。

## 基础信息

- **Base URL**: `/api/chat-sessions`
- **认证方式**: Bearer Token (JWT)
- **Content-Type**: `application/json`

## 接口列表

### 1. 根据任务ID更新会话名称（推荐）

根据任务ID（job_id）更新会话的名称字段。

**请求**

```
PUT /api/chat-sessions/update-name
```

**请求头**

```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**请求体**

```json
{
  "job_id": "job_001",
  "name": "新的会话名称"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| job_id | string | 是 | 任务ID |
| name | string | 是 | 新的会话名称，最大长度255字符 |

**响应示例**

成功响应 (200):
```json
{
  "success": true,
  "message": "会话名称更新成功",
  "data": {
    "session_id": "session_001",
    "job_id": "job_001",
    "user_id": "user_001",
    "name": "新的会话名称",
    "status": "active",
    "metadata": {
      "file_name": "example.pdf"
    },
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T12:00:00"
  }
}
```

错误响应:

- 400 Bad Request - 请求数据格式错误、任务ID或名称为空
```json
{
  "success": false,
  "message": "任务ID不能为空"
}
```

- 401 Unauthorized - Token无效或已过期
```json
{
  "success": false,
  "message": "Token无效或已过期"
}
```

- 404 Not Found - 会话不存在或无权访问
```json
{
  "success": false,
  "message": "会话不存在或无权访问"
}
```

---

### 2. 根据会话ID更新会话名称

根据会话ID（session_id）更新会话的名称字段。

**请求**

```
PUT /api/chat-sessions/{session_id}/name
```

**请求头**

```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话ID |

**请求体**

```json
{
  "name": "新的会话名称"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 新的会话名称，最大长度255字符 |

**响应示例**

成功响应 (200):
```json
{
  "success": true,
  "message": "会话名称更新成功",
  "data": {
    "session_id": "session_001",
    "job_id": "job_001",
    "user_id": "user_001",
    "name": "新的会话名称",
    "status": "active",
    "metadata": {
      "file_name": "example.pdf"
    },
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T12:00:00"
  }
}
```

错误响应:

- 400 Bad Request - 请求数据格式错误或名称为空
```json
{
  "success": false,
  "message": "会话名称不能为空"
}
```

- 401 Unauthorized - Token无效或已过期
```json
{
  "success": false,
  "message": "Token无效或已过期"
}
```

- 403 Forbidden - 无权修改此会话
```json
{
  "success": false,
  "message": "无权修改此会话"
}
```

- 404 Not Found - 会话不存在
```json
{
  "success": false,
  "message": "会话不存在"
}
```

---

### 3. 获取会话详情

获取指定会话的详细信息。

**请求**

```
GET /api/chat-sessions/{session_id}
```

**请求头**

```
Authorization: Bearer <your_jwt_token>
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话ID |

**响应示例**

成功响应 (200):
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "session_id": "session_001",
    "job_id": "job_001",
    "user_id": "user_001",
    "name": "会话名称",
    "status": "active",
    "metadata": {
      "file_name": "example.pdf",
      "description": "审核任务"
    },
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T12:00:00"
  }
}
```

错误响应:

- 401 Unauthorized - Token无效
- 403 Forbidden - 无权访问此会话
- 404 Not Found - 会话不存在

---

### 4. 获取用户会话列表

获取当前用户的所有会话列表，支持分页和状态过滤。

**请求**

```
GET /api/chat-sessions/
```

**请求头**

```
Authorization: Bearer <your_jwt_token>
```

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| status | string | 否 | - | 会话状态过滤（如：active, closed） |
| limit | integer | 否 | 50 | 返回数量限制，最大100 |
| offset | integer | 否 | 0 | 偏移量，用于分页 |

**响应示例**

成功响应 (200):
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "sessions": [
      {
        "session_id": "session_001",
        "job_id": "job_001",
        "user_id": "user_001",
        "name": "会话1",
        "status": "active",
        "metadata": {},
        "created_at": "2024-01-01T10:00:00",
        "updated_at": "2024-01-01T12:00:00"
      },
      {
        "session_id": "session_002",
        "job_id": "job_002",
        "user_id": "user_001",
        "name": "会话2",
        "status": "active",
        "metadata": {},
        "created_at": "2024-01-02T10:00:00",
        "updated_at": "2024-01-02T12:00:00"
      }
    ],
    "total": 100,
    "limit": 50,
    "offset": 0
  }
}
```

错误响应:

- 400 Bad Request - 参数格式错误
- 401 Unauthorized - Token无效

---

### 5. 根据任务ID删除会话（级联删除）

根据任务ID删除会话及所有相关数据。⚠️ **警告**: 此操作不可逆！

**请求**

```
DELETE /api/chat-sessions/delete-by-job
```

**请求头**

```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**请求体**

```json
{
  "job_id": "job_001"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| job_id | string | 是 | 任务ID |

**响应示例**

成功响应 (200):
```json
{
  "success": true,
  "message": "会话删除成功，共删除 156 条记录: chat_messages(25条), features(45条), subgraphs(12条), job_price_snapshots(68条), jobs(1条), chat_sessions(1条)",
  "data": {
    "job_id": "job_001",
    "deleted_tables": ["chat_messages", "features", "subgraphs", "job_price_snapshots", "jobs", "chat_sessions"],
    "total_deleted": 156
  }
}
```

**删除范围**: 会级联删除19个相关表的数据，包括聊天消息、任务数据、子图、特征、价格快照、工艺快照、计算明细、日志等。

详细信息请参考: [删除接口文档](./DELETE_SESSION_API.md)

---

### 6. 根据会话ID删除会话（级联删除）

根据会话ID删除会话及所有相关数据。⚠️ **警告**: 此操作不可逆！

**请求**

```
DELETE /api/chat-sessions/{session_id}
```

**请求头**

```
Authorization: Bearer <your_jwt_token>
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话ID |

**响应示例**

成功响应 (200):
```json
{
  "success": true,
  "message": "会话删除成功，共删除 156 条记录: ...",
  "data": {
    "session_id": "session_001",
    "deleted_tables": ["chat_messages", "features", "subgraphs", "jobs", "chat_sessions"],
    "total_deleted": 156
  }
}
```

错误响应:

- 401 Unauthorized - Token无效
- 403 Forbidden - 无权删除此会话
- 404 Not Found - 会话不存在

---

## 使用示例

### Python 示例

```python
import requests

# 基础配置
BASE_URL = "http://localhost:8000"
TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. 根据任务ID更新会话名称（推荐）
def update_session_name_by_job_id(job_id, new_name):
    url = f"{BASE_URL}/api/chat-sessions/update-name"
    data = {
        "job_id": job_id,
        "name": new_name
    }
    response = requests.put(url, json=data, headers=headers)
    return response.json()

# 2. 根据会话ID更新会话名称
def update_session_name(session_id, new_name):
    url = f"{BASE_URL}/api/chat-sessions/{session_id}/name"
    data = {"name": new_name}
    response = requests.put(url, json=data, headers=headers)
    return response.json()

# 3. 根据任务ID删除会话（推荐）
def delete_session_by_job_id(job_id):
    url = f"{BASE_URL}/api/chat-sessions/delete-by-job"
    data = {"job_id": job_id}
    response = requests.delete(url, json=data, headers=headers)
    return response.json()

# 4. 根据会话ID删除会话
def delete_session_by_id(session_id):
    url = f"{BASE_URL}/api/chat-sessions/{session_id}"
    response = requests.delete(url, headers=headers)
    return response.json()

# 5. 获取会话详情
def get_session(session_id):
    url = f"{BASE_URL}/api/chat-sessions/{session_id}"
    response = requests.get(url, headers=headers)
    return response.json()

# 6. 获取会话列表
def get_sessions(status=None, limit=50, offset=0):
    url = f"{BASE_URL}/api/chat-sessions/"
    params = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 根据任务ID更新会话名称（推荐）
    result = update_session_name_by_job_id("job_001", "我的新会话")
    print(result)
    
    # 根据会话ID更新会话名称
    result = update_session_name("session_001", "我的新会话")
    print(result)
    
    # 删除会话（谨慎使用！）
    # result = delete_session_by_job_id("job_001")
    # print(result)
    
    # 获取会话详情
    session = get_session("session_001")
    print(session)
    
    # 获取会话列表
    sessions = get_sessions(status="active", limit=10)
    print(sessions)
```

### cURL 示例

```bash
# 1. 根据任务ID更新会话名称（推荐）
curl -X PUT "http://localhost:8000/api/chat-sessions/update-name" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "job_001", "name": "新的会话名称"}'

# 2. 根据会话ID更新会话名称
curl -X PUT "http://localhost:8000/api/chat-sessions/session_001/name" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"name": "新的会话名称"}'

# 3. 获取会话详情
curl -X GET "http://localhost:8000/api/chat-sessions/session_001" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 获取会话列表
curl -X GET "http://localhost:8000/api/chat-sessions/?status=active&limit=10&offset=0" \
  -H "Authorization: Bearer your_jwt_token"
```

### JavaScript (Fetch API) 示例

```javascript
const BASE_URL = 'http://localhost:8000';
const TOKEN = 'your_jwt_token_here';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// 1. 根据任务ID更新会话名称（推荐）
async function updateSessionNameByJobId(jobId, newName) {
  const response = await fetch(`${BASE_URL}/api/chat-sessions/update-name`, {
    method: 'PUT',
    headers: headers,
    body: JSON.stringify({ job_id: jobId, name: newName })
  });
  return await response.json();
}

// 2. 根据会话ID更新会话名称
async function updateSessionName(sessionId, newName) {
  const response = await fetch(`${BASE_URL}/api/chat-sessions/${sessionId}/name`, {
    method: 'PUT',
    headers: headers,
    body: JSON.stringify({ name: newName })
  });
  return await response.json();
}

// 2. 根据会话ID更新会话名称
async function updateSessionName(sessionId, newName) {
  const response = await fetch(`${BASE_URL}/api/chat-sessions/${sessionId}/name`, {
    method: 'PUT',
    headers: headers,
    body: JSON.stringify({ name: newName })
  });
  return await response.json();
}

// 3. 获取会话详情
async function getSession(sessionId) {
  const response = await fetch(`${BASE_URL}/api/chat-sessions/${sessionId}`, {
    method: 'GET',
    headers: headers
  });
  return await response.json();
}

// 3. 获取会话列表
async function getSessions(status = null, limit = 50, offset = 0) {
  const params = new URLSearchParams({ limit, offset });
  if (status) params.append('status', status);
  
  const response = await fetch(`${BASE_URL}/api/chat-sessions/?${params}`, {
    method: 'GET',
    headers: headers
  });
  return await response.json();
}

// 使用示例
(async () => {
  try {
    // 根据任务ID更新会话名称（推荐）
    const updateResult1 = await updateSessionNameByJobId('job_001', '我的新会话');
    console.log(updateResult1);
    
    // 根据会话ID更新会话名称
    const updateResult2 = await updateSessionName('session_001', '我的新会话');
    console.log(updateResult2);
    
    // 获取会话详情
    const session = await getSession('session_001');
    console.log(session);
    
    // 获取会话列表
    const sessions = await getSessions('active', 10, 0);
    console.log(sessions);
  } catch (error) {
    console.error('Error:', error);
  }
})();
```

## 数据库表结构

```sql
CREATE TABLE "public"."chat_sessions" (
  "session_id" varchar(50) NOT NULL,
  "job_id" varchar(50) NOT NULL,
  "user_id" varchar(50) NOT NULL,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "status" varchar(20) DEFAULT 'active',
  "metadata" jsonb,
  "name" varchar(255),
  CONSTRAINT "chat_sessions_pkey" PRIMARY KEY ("session_id")
);

-- 索引
CREATE INDEX "idx_chat_sessions_created_at" ON "public"."chat_sessions" USING btree ("created_at");
CREATE INDEX "idx_chat_sessions_job_id" ON "public"."chat_sessions" USING btree ("job_id");
CREATE INDEX "idx_chat_sessions_user_id" ON "public"."chat_sessions" USING btree ("user_id");
```

## 注意事项

1. **认证**: 所有接口都需要有效的 JWT Token
2. **权限**: 用户只能访问和修改自己的会话
3. **名称长度**: 会话名称最大长度为 255 个字符
4. **分页**: 获取会话列表时，limit 最大值为 100
5. **Token 刷新**: 如果 Token 即将过期，响应中会包含 `new_token` 字段

## 错误码说明

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token无效或缺失） |
| 403 | 禁止访问（无权限） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
