# API快速参考

**服务地址**: `http://192.168.0.14:8000`

---

## 认证接口

### 登录
```
POST /api/login
Body: {"username": "admin", "password": "123456"}
Response: {"success": true, "token": "...", "user_info": {...}}
```

### Token验证
```
POST /api/verify-token
Body: {"token": "..."}
Response: {"success": true, "payload": {...}}
```

---

## 工艺规则接口

**需要Token**: `Authorization: Bearer <token>`

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/process-rules` | 创建规则 |
| GET | `/api/process-rules/{id}` | 获取单个规则 |
| GET | `/api/process-rules` | 获取规则列表 |
| PUT | `/api/process-rules/{id}` | 更新规则 |
| DELETE | `/api/process-rules/{id}` | 删除规则 |
| POST | `/api/process-rules/batch-delete` | 批量删除 |
| GET | `/api/process-rules/by-version-type` | 按版本类型查询 |

### 查询参数
- `page`, `page_size`: 分页
- `version_id`: 版本筛选
- `feature_type`: 类型筛选（WIRE/NC/EDM等）
- `is_active`: 激活状态
- `name`: 名称搜索

### 必填字段
- `id`: 规则ID
- `version_id`: 版本号
- `feature_type`: 特征类型
- `name`: 规则名称
- `conditions`: 规则条件（≤255字符）
- `output_params`: 输出参数（≤255字符）

---

## 价格项接口

**需要Token**: `Authorization: Bearer <token>`

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/price-items` | 创建价格项 |
| GET | `/api/price-items/{id}` | 获取单个价格项 |
| GET | `/api/price-items` | 获取价格项列表 |
| PUT | `/api/price-items/{id}` | 更新价格项 |
| DELETE | `/api/price-items/{id}` | 删除价格项 |
| POST | `/api/price-items/batch-delete` | 批量删除 |
| GET | `/api/price-items/by-version-category` | 按版本类别查询 |

### 查询参数
- `page`, `page_size`: 分页
- `version_id`: 版本筛选
- `category`: 类别筛选
- `sub_category`: 子类别筛选
- `is_active`: 激活状态

### 必填字段
- `id`: 价格项ID
- `category`: 类别
- `sub_category`: 子类别
- `price`: 价格（字符串）
- `unit`: 单位

---

## Token自动刷新

所有需要认证的接口都支持Token自动刷新：

- 当token剩余时间 < 50%时，响应中会包含`new_token`字段
- 客户端应更新本地存储的token

```javascript
if (response.new_token) {
    localStorage.setItem('token', response.new_token);
}
```

---

## 响应格式

### 成功
```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

### 失败
```json
{
  "success": false,
  "message": "错误信息"
}
```

### Token刷新
```json
{
  "success": true,
  "message": "操作成功（token已刷新）",
  "data": {},
  "new_token": "..."
}
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 参数错误 |
| 401 | 未授权 |
| 404 | 不存在 |
| 500 | 服务器错误 |

---

## 快速测试

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://192.168.0.14:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}' \
  | jq -r '.token')

# 2. 获取价格项
curl -X GET "http://192.168.0.14:8000/api/price-items?page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN"

# 3. 获取工艺规则
curl -X GET "http://192.168.0.14:8000/api/process-rules?page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 完整文档

详细文档请参考: `API_DOCUMENTATION.md`
