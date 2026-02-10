# 会话删除 API 文档

## 概述

会话删除 API 提供了删除聊天会话及其所有相关数据的功能。删除操作是**级联删除**，会同时删除与 `job_id` 相关的所有数据表记录。

⚠️ **警告**: 删除操作不可逆，请谨慎使用！

## 删除范围

删除会话时，会级联删除以下表中的相关数据：

### 核心业务数据
1. **chat_sessions** - 聊天会话
2. **chat_messages** - 聊天消息
3. **jobs** - 任务主表
4. **subgraphs** - 子图数据
5. **features** - 特征数据

### 快照和配置数据
6. **job_price_snapshots** - 价格快照
7. **job_process_snapshots** - 工艺快照

### 计算和分析数据
8. **processing_cost_calculation_details** - 加工费用计算明细
9. **nc_calculations** - NC计算记录
10. **price_histories** - 价格历史
11. **recalculations** - 重算记录
12. **batch_recalculations** - 批量重算

### 变更和交互数据
13. **process_changes** - 工艺变更
14. **user_interactions** - 用户交互

### 报表和归档数据
15. **reports** - 报表文件
16. **report_summary** - 报表汇总
17. **archives** - 归档数据

### 日志数据
18. **operation_logs** - 操作日志
19. **audit_logs** - 审计日志（相关记录）

## 接口列表

### 1. 根据任务ID删除会话（推荐）

根据任务ID删除会话及所有相关数据。

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
    "deleted_tables": [
      "chat_messages",
      "features", 
      "subgraphs",
      "job_price_snapshots",
      "jobs",
      "chat_sessions"
    ],
    "total_deleted": 156
  }
}
```

错误响应:

- 400 Bad Request - 请求数据格式错误或任务ID为空
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

### 2. 根据会话ID删除会话

根据会话ID删除会话及所有相关数据。

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
  "message": "会话删除成功，共删除 156 条记录: chat_messages(25条), features(45条), subgraphs(12条), job_price_snapshots(68条), jobs(1条), chat_sessions(1条)",
  "data": {
    "session_id": "session_001",
    "deleted_tables": [
      "chat_messages",
      "features", 
      "subgraphs",
      "job_price_snapshots",
      "jobs",
      "chat_sessions"
    ],
    "total_deleted": 156
  }
}
```

错误响应:

- 401 Unauthorized - Token无效
- 403 Forbidden - 无权删除此会话
- 404 Not Found - 会话不存在

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. 根据任务ID删除会话（推荐）
def delete_session_by_job_id(job_id):
    url = f"{BASE_URL}/api/chat-sessions/delete-by-job"
    data = {"job_id": job_id}
    response = requests.delete(url, json=data, headers=headers)
    return response.json()

# 2. 根据会话ID删除会话
def delete_session_by_id(session_id):
    url = f"{BASE_URL}/api/chat-sessions/{session_id}"
    response = requests.delete(url, headers=headers)
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 删除指定任务的会话
    result = delete_session_by_job_id("job_001")
    print(f"删除结果: {result}")
    
    if result['success']:
        print(f"删除成功，共删除 {result['data']['total_deleted']} 条记录")
        print(f"涉及表: {', '.join(result['data']['deleted_tables'])}")
    else:
        print(f"删除失败: {result['message']}")
```

### cURL 示例

```bash
# 1. 根据任务ID删除会话
curl -X DELETE "http://localhost:8000/api/chat-sessions/delete-by-job" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "job_001"}'

# 2. 根据会话ID删除会话
curl -X DELETE "http://localhost:8000/api/chat-sessions/session_001" \
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

// 1. 根据任务ID删除会话
async function deleteSessionByJobId(jobId) {
  const response = await fetch(`${BASE_URL}/api/chat-sessions/delete-by-job`, {
    method: 'DELETE',
    headers: headers,
    body: JSON.stringify({ job_id: jobId })
  });
  return await response.json();
}

// 2. 根据会话ID删除会话
async function deleteSessionById(sessionId) {
  const response = await fetch(`${BASE_URL}/api/chat-sessions/${sessionId}`, {
    method: 'DELETE',
    headers: headers
  });
  return await response.json();
}

// 使用示例
(async () => {
  try {
    // 删除会话
    const result = await deleteSessionByJobId('job_001');
    
    if (result.success) {
      console.log(`删除成功，共删除 ${result.data.total_deleted} 条记录`);
      console.log(`涉及表: ${result.data.deleted_tables.join(', ')}`);
    } else {
      console.error(`删除失败: ${result.message}`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
})();
```

## 安全考虑

### 权限验证
- 用户只能删除自己的会话
- 通过 JWT Token 验证用户身份
- 通过 user_id 验证会话所有权

### 数据保护
- 删除操作不可逆
- 建议在删除前进行数据备份
- 重要数据可考虑软删除（标记为已删除）

### 审计日志
- 删除操作会被记录到审计日志
- 包含删除的表和记录数量
- 便于后续审计和问题排查

## 注意事项

### 1. 删除顺序
删除操作按照外键依赖关系的逆序进行：
1. 先删除子表（如 chat_messages, features 等）
2. 再删除父表（如 jobs, chat_sessions）

### 2. 事务处理
- 所有删除操作在同一个事务中执行
- 如果任何一步失败，整个操作会回滚
- 保证数据一致性

### 3. 性能考虑
- 大量数据删除可能耗时较长
- 建议在业务低峰期执行
- 可考虑分批删除大量数据

### 4. 备份建议
```sql
-- 删除前备份重要数据
CREATE TABLE jobs_backup AS SELECT * FROM jobs WHERE job_id = 'your_job_id';
CREATE TABLE subgraphs_backup AS SELECT * FROM subgraphs WHERE job_id = 'your_job_id';
-- ... 其他重要表
```

## 错误码说明

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 删除成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token无效或缺失） |
| 403 | 禁止访问（无权限） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 相关接口

- [获取会话列表](./CHAT_SESSIONS_API.md#获取用户会话列表)
- [更新会话名称](./CHAT_SESSIONS_API.md#更新会话名称)
- [获取会话详情](./CHAT_SESSIONS_API.md#获取会话详情)

## 更新日志

- **2024-01-20**: 初始版本，支持级联删除19个相关表