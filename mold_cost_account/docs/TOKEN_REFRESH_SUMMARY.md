# Token自动刷新功能总结

## 功能概述

实现了Token自动刷新（滑动过期时间）机制，当用户使用有效token访问接口时，如果token即将过期，系统会自动生成新token并返回，无需用户重新登录。

## 核心特性

✓ **自动刷新**: 当token剩余时间小于50%时自动生成新token  
✓ **无感知**: 用户无需任何操作，会话自动延长  
✓ **不改变原token**: 原token保持不变，新token在响应中返回  
✓ **向后兼容**: 客户端可以选择是否使用新token  
✓ **灵活配置**: 可配置刷新阈值和过期时间  

## 文件结构

```
app/
├── middleware/
│   ├── __init__.py
│   └── token_refresh.py          # Token刷新中间件类
├── utils/
│   ├── __init__.py
│   └── token_helper.py            # Token辅助函数（推荐使用）
└── api/
    └── protected_example.py       # 使用示例

docs/
├── TOKEN_AUTO_REFRESH.md          # 详细文档
├── TOKEN_REFRESH_INTEGRATION_EXAMPLE.md  # 集成示例
└── TOKEN_REFRESH_SUMMARY.md       # 本文档

test_token_refresh.py              # 测试脚本
```

## 使用方法

### 方法1: 使用辅助函数（推荐）

```python
from app.utils import verify_and_refresh_token, get_token_from_request, add_new_token_to_response

@app.route('/api/my-endpoint', methods=['GET'])
def my_endpoint():
    # 获取并验证token
    token, error_response = get_token_from_request()
    if error_response:
        return error_response
    
    payload, new_token, error_message = verify_and_refresh_token(token)
    if payload is None:
        return jsonify({'success': False, 'message': error_message}), 401
    
    # 业务逻辑
    response_data = {'success': True, 'data': {}}
    
    # 添加新token（如果有）
    response_data = add_new_token_to_response(response_data, new_token)
    
    return jsonify(response_data)
```

### 方法2: 使用装饰器（最简洁）

```python
from app.utils import require_token_with_refresh
from flask import g

@app.route('/api/my-endpoint', methods=['GET'])
@require_token_with_refresh
def my_endpoint():
    # 用户信息在 g.current_user 中
    user_id = g.current_user.get('user_id')
    
    # 业务逻辑
    return jsonify({'success': True, 'data': {}})
    # 新token会自动添加到响应中
```

## 配置参数

### 环境变量（.env）

```bash
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30000  # token总有效期（分钟）
```

### 代码配置

```python
# 刷新阈值（默认0.5，即50%）
refresh_threshold = 0.5

# 刷新窗口 = 总有效期 × 刷新阈值
# 例如: 30000分钟 × 0.5 = 15000分钟
```

## 工作流程

```
1. 客户端发送请求 + Authorization: Bearer <token>
2. 服务器验证token
3. 检查剩余时间
4. 如果剩余时间 < 刷新窗口:
   - 生成新token
   - 在响应中添加 new_token 字段
5. 客户端收到响应
6. 如果有 new_token，更新本地存储的token
```

## 响应格式

### 正常响应（无需刷新）

```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

### 刷新响应（包含新token）

```json
{
  "success": true,
  "message": "操作成功（token已刷新）",
  "data": {},
  "new_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## 客户端处理

### JavaScript示例

```javascript
async function apiRequest(url, options = {}) {
    let token = localStorage.getItem('token');
    
    const response = await fetch(url, {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            ...options.headers
        }
    });
    
    const data = await response.json();
    
    // 检查并更新token
    if (data.new_token) {
        localStorage.setItem('token', data.new_token);
        console.log('Token已自动刷新');
    }
    
    return data;
}
```

### Python示例

```python
class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    
    def request(self, method, endpoint, **kwargs):
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.token}"
        kwargs['headers'] = headers
        
        response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
        result = response.json()
        
        # 自动更新token
        if 'new_token' in result:
            self.token = result['new_token']
        
        return result
```

## 测试

```bash
# 运行测试脚本
python test_token_refresh.py
```

## 优点

1. **提高用户体验**: 用户无需频繁登录
2. **保持安全性**: token仍然有过期时间
3. **实现简单**: 无需单独的刷新接口
4. **向后兼容**: 不影响现有功能

## 注意事项

1. **客户端必须处理new_token**: 否则旧token过期后无法访问
2. **不要在登录接口使用**: 登录接口本身就是获取token的
3. **公开接口不需要**: 完全公开的接口不需要token验证
4. **并发请求**: 多个并发请求可能都返回新token，使用最新的即可

## 集成到现有API

只需3步：

1. **导入辅助函数**
```python
from app.utils import verify_and_refresh_token, get_token_from_request, add_new_token_to_response
```

2. **添加token验证**
```python
token, error_response = get_token_from_request()
if error_response:
    return error_response

payload, new_token, error_message = verify_and_refresh_token(token)
if payload is None:
    return jsonify({'success': False, 'message': error_message}), 401
```

3. **添加新token到响应**
```python
response_data = add_new_token_to_response(response_data, new_token)
```

## 相关文档

- `TOKEN_AUTO_REFRESH.md` - 详细功能文档
- `TOKEN_REFRESH_INTEGRATION_EXAMPLE.md` - 集成示例
- `JWT_GUIDE.md` - JWT使用指南

## 总结

Token自动刷新功能已完全实现，可以直接在任何需要认证的接口中使用。通过简单的几行代码，就可以实现用户会话的自动延长，大大提高用户体验。
