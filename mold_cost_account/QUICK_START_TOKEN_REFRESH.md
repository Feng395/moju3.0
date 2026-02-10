# Token自动刷新 - 快速开始

## 5分钟快速集成

### 1. 在API中添加Token验证（3行代码）

```python
from app.utils import verify_and_refresh_token, get_token_from_request, add_new_token_to_response

@app.route('/api/your-endpoint', methods=['GET'])
def your_endpoint():
    # 第1行：获取token
    token, error_response = get_token_from_request()
    if error_response:
        return error_response
    
    # 第2行：验证并刷新token
    payload, new_token, error_message = verify_and_refresh_token(token)
    if payload is None:
        return jsonify({'success': False, 'message': error_message}), 401
    
    # 你的业务逻辑
    response_data = {
        'success': True,
        'data': {}
    }
    
    # 第3行：添加新token
    response_data = add_new_token_to_response(response_data, new_token)
    
    return jsonify(response_data)
```

### 2. 客户端处理（JavaScript）

```javascript
// 封装API请求
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
    
    // 自动更新token
    if (data.new_token) {
        localStorage.setItem('token', data.new_token);
    }
    
    return data;
}

// 使用
const result = await apiRequest('http://192.168.0.14:8000/api/price-items');
```

### 3. 测试

```bash
python test_token_refresh.py
```

## 完成！

就这么简单！现在你的API已经支持Token自动刷新了。

## 工作原理

```
用户请求 → 验证token → 检查剩余时间 → 如果<50% → 生成新token → 返回响应+新token
```

## 配置

在 `.env` 文件中：

```bash
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30000  # token有效期（分钟）
```

## 更多信息

- 详细文档: `docs/TOKEN_AUTO_REFRESH.md`
- 集成示例: `docs/TOKEN_REFRESH_INTEGRATION_EXAMPLE.md`
- 功能总结: `docs/TOKEN_REFRESH_SUMMARY.md`
