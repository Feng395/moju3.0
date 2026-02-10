# 工艺规则管理 API 文档

## 概述

工艺规则管理API提供完整的CRUD操作，支持工艺规则的创建、查询、更新和删除功能。

**基础URL**: `/api/process-rules`

## 数据模型

### ProcessRule 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string(50) | 是 | 规则唯一标识，如R001 |
| version_id | string(20) | 是 | 规则版本号，如v1.0 |
| feature_type | string(20) | 是 | 特征类型：WIRE-线割, NC-数控等 |
| name | string(100) | 是 | 规则名称 |
| description | text | 否 | 规则描述 |
| priority | integer | 否 | 优先级，数值越大优先级越高（默认0） |
| is_active | boolean | 否 | 是否激活（默认true） |
| conditions | string(255) | 是 | 规则条件，字符串格式 |
| output_params | string(255) | 是 | 输出参数，字符串格式 |
| created_at | timestamp | 自动 | 创建时间 |

## API接口

### 1. 创建工艺规则

**接口**: `POST /api/process-rules`

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
  "id": "R001",
  "version_id": "v1.0",
  "feature_type": "WIRE",
  "name": "线割规则1",
  "description": "这是一个线割工艺规则",
  "priority": 10,
  "is_active": true,
  "conditions": "length > 100 AND width < 50",
  "output_params": "speed=100,power=80"
}
```

**成功响应** (201):
```json
{
  "success": true,
  "message": "规则创建成功",
  "data": {
    "id": "R001",
    "version_id": "v1.0",
    "feature_type": "WIRE",
    "name": "线割规则1",
    "description": "这是一个线割工艺规则",
    "priority": 10,
    "is_active": true,
    "conditions": "length > 100 AND width < 50",
    "output_params": "speed=100,power=80",
    "created_at": "2024-01-13T12:00:00"
  }
}
```

**错误响应** (400):
```json
{
  "success": false,
  "message": "缺少必填字段: id"
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/process-rules \
  -H "Content-Type: application/json" \
  -d '{
    "id": "R001",
    "version_id": "v1.0",
    "feature_type": "WIRE",
    "name": "线割规则1",
    "conditions": "length > 100",
    "output_params": "speed=100"
  }'
```

---

### 2. 获取单个规则

**接口**: `GET /api/process-rules/{rule_id}`

**路径参数**:
- `rule_id`: 规则ID

**成功响应** (200):
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "id": "R001",
    "version_id": "v1.0",
    "feature_type": "WIRE",
    "name": "线割规则1",
    "description": "这是一个线割工艺规则",
    "priority": 10,
    "is_active": true,
    "conditions": "length > 100 AND width < 50",
    "output_params": "speed=100,power=80",
    "created_at": "2024-01-13T12:00:00"
  }
}
```

**错误响应** (404):
```json
{
  "success": false,
  "message": "规则不存在"
}
```

**示例**:
```bash
curl -X GET http://localhost:8000/api/process-rules/R001
```

---

### 3. 获取规则列表

**接口**: `GET /api/process-rules`

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码（默认1） |
| page_size | integer | 否 | 每页数量（默认20） |
| version_id | string | 否 | 版本号筛选 |
| feature_type | string | 否 | 特征类型筛选 |
| is_active | boolean | 否 | 是否激活筛选 |
| name | string | 否 | 名称模糊搜索 |

**成功响应** (200):
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "data": [
      {
        "id": "R001",
        "version_id": "v1.0",
        "feature_type": "WIRE",
        "name": "线割规则1",
        "description": "这是一个线割工艺规则",
        "priority": 10,
        "is_active": true,
        "conditions": "length > 100 AND width < 50",
        "output_params": "speed=100,power=80",
        "created_at": "2024-01-13T12:00:00"
      }
    ]
  }
}
```

**示例**:
```bash
# 获取所有规则
curl -X GET http://localhost:8000/api/process-rules

# 筛选版本v1.0的规则
curl -X GET "http://localhost:8000/api/process-rules?version_id=v1.0"

# 筛选WIRE类型的规则
curl -X GET "http://localhost:8000/api/process-rules?feature_type=WIRE"

# 名称模糊搜索
curl -X GET "http://localhost:8000/api/process-rules?name=线割"

# 分页查询
curl -X GET "http://localhost:8000/api/process-rules?page=1&page_size=10"

# 组合筛选
curl -X GET "http://localhost:8000/api/process-rules?version_id=v1.0&feature_type=WIRE&is_active=true"
```

---

### 4. 更新规则

**接口**: `PUT /api/process-rules/{rule_id}`

**路径参数**:
- `rule_id`: 规则ID

**请求头**:
```
Content-Type: application/json
```

**请求体** (所有字段可选):
```json
{
  "version_id": "v1.1",
  "feature_type": "NC",
  "name": "更新后的名称",
  "description": "更新后的描述",
  "priority": 20,
  "is_active": false,
  "conditions": "新条件",
  "output_params": "新输出参数"
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "规则更新成功",
  "data": {
    "id": "R001",
    "version_id": "v1.1",
    "feature_type": "NC",
    "name": "更新后的名称",
    "description": "更新后的描述",
    "priority": 20,
    "is_active": false,
    "conditions": "新条件",
    "output_params": "新输出参数",
    "created_at": "2024-01-13T12:00:00"
  }
}
```

**错误响应** (404):
```json
{
  "success": false,
  "message": "规则不存在"
}
```

**示例**:
```bash
curl -X PUT http://localhost:8000/api/process-rules/R001 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "更新后的规则名称",
    "priority": 25
  }'
```

---

### 5. 删除规则

**接口**: `DELETE /api/process-rules/{rule_id}`

**路径参数**:
- `rule_id`: 规则ID

**成功响应** (200):
```json
{
  "success": true,
  "message": "规则删除成功"
}
```

**错误响应** (404):
```json
{
  "success": false,
  "message": "规则不存在"
}
```

**示例**:
```bash
curl -X DELETE http://localhost:8000/api/process-rules/R001
```

---

### 6. 批量删除规则

**接口**: `POST /api/process-rules/batch-delete`

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
  "ids": ["R001", "R002", "R003"]
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "成功删除 3 条规则",
  "data": {
    "deleted_count": 3
  }
}
```

**错误响应** (400):
```json
{
  "success": false,
  "message": "ids必须是非空数组"
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/process-rules/batch-delete \
  -H "Content-Type: application/json" \
  -d '{
    "ids": ["R001", "R002", "R003"]
  }'
```

---

### 7. 根据版本和类型获取规则

**接口**: `GET /api/process-rules/by-version-type`

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version_id | string | 是 | 版本号 |
| feature_type | string | 是 | 特征类型 |
| active_only | boolean | 否 | 是否只返回激活的规则（默认true） |

**成功响应** (200):
```json
{
  "success": true,
  "message": "获取成功",
  "data": [
    {
      "id": "R001",
      "version_id": "v1.0",
      "feature_type": "WIRE",
      "name": "线割规则1",
      "description": "这是一个线割工艺规则",
      "priority": 10,
      "is_active": true,
      "conditions": "length > 100 AND width < 50",
      "output_params": "speed=100,power=80",
      "created_at": "2024-01-13T12:00:00"
    }
  ]
}
```

**错误响应** (400):
```json
{
  "success": false,
  "message": "缺少必填参数: version_id 和 feature_type"
}
```

**示例**:
```bash
# 获取v1.0版本的WIRE类型规则（只返回激活的）
curl -X GET "http://localhost:8000/api/process-rules/by-version-type?version_id=v1.0&feature_type=WIRE"

# 获取所有规则（包括未激活的）
curl -X GET "http://localhost:8000/api/process-rules/by-version-type?version_id=v1.0&feature_type=WIRE&active_only=false"
```

---

## 错误码说明

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 使用示例

### Python示例

```python
import requests
import json

base_url = "http://localhost:8000/api/process-rules"

# 创建规则
rule_data = {
    "id": "R001",
    "version_id": "v1.0",
    "feature_type": "WIRE",
    "name": "线割规则1",
    "conditions": "length > 100",
    "output_params": "speed=100"
}
response = requests.post(base_url, json=rule_data)
print(response.json())

# 获取规则列表
response = requests.get(base_url, params={"version_id": "v1.0"})
print(response.json())

# 更新规则
update_data = {"name": "更新后的名称", "priority": 20}
response = requests.put(f"{base_url}/R001", json=update_data)
print(response.json())

# 删除规则
response = requests.delete(f"{base_url}/R001")
print(response.json())
```

### JavaScript示例

```javascript
const baseUrl = 'http://localhost:8000/api/process-rules';

// 创建规则
async function createRule() {
    const ruleData = {
        id: 'R001',
        version_id: 'v1.0',
        feature_type: 'WIRE',
        name: '线割规则1',
        conditions: 'length > 100',
        output_params: 'speed=100'
    };
    
    const response = await fetch(baseUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(ruleData)
    });
    
    const result = await response.json();
    console.log(result);
}

// 获取规则列表
async function getRules() {
    const response = await fetch(`${baseUrl}?version_id=v1.0`);
    const result = await response.json();
    console.log(result);
}

// 更新规则
async function updateRule(ruleId) {
    const updateData = {
        name: '更新后的名称',
        priority: 20
    };
    
    const response = await fetch(`${baseUrl}/${ruleId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
    });
    
    const result = await response.json();
    console.log(result);
}

// 删除规则
async function deleteRule(ruleId) {
    const response = await fetch(`${baseUrl}/${ruleId}`, {
        method: 'DELETE'
    });
    
    const result = await response.json();
    console.log(result);
}
```

## 测试

运行测试脚本：
```bash
python test_process_rules.py
```

测试脚本会执行以下操作：
1. 创建多个测试规则
2. 获取单个规则
3. 获取规则列表（各种筛选条件）
4. 分页测试
5. 根据版本和类型获取规则
6. 更新规则
7. 删除单个规则
8. 批量删除规则

## 注意事项

1. **字段长度限制**:
   - `conditions` 和 `output_params` 字段最大长度为255字符
   - 超过限制会返回400错误

2. **唯一性约束**:
   - `id` 字段必须唯一
   - 重复的ID会导致创建失败

3. **优先级排序**:
   - 规则列表按优先级降序排列
   - 相同优先级按创建时间降序排列

4. **激活状态**:
   - 默认情况下，`by-version-type` 接口只返回激活的规则
   - 可通过 `active_only=false` 参数获取所有规则

5. **分页**:
   - 默认每页20条记录
   - 最大每页100条记录（建议）

## 总结

工艺规则管理API提供了完整的CRUD功能，支持：
- ✅ 创建、查询、更新、删除规则
- ✅ 分页和多条件筛选
- ✅ 批量操作
- ✅ 版本和类型快速查询
- ✅ 优先级排序
- ✅ 完整的错误处理