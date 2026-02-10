# Token自动刷新集成示例

## 如何在现有API中添加Token自动刷新

### 示例1: 在价格项API中添加

```python
# app/api/price_items.py

from flask import Blueprint, request, jsonify
from app.utils import verify_and_refresh_token, get_token_from_request, add_new_token_to_response

price_items_bp = Blueprint('price_items', __name__, url_prefix='/api/price-items')

@price_items_bp.route('', methods=['GET'])
def get_price_items():
    """获取价格项列表（带token自动刷新）"""
    
    # 1. 获取并验证token
    token, error_response = get_token_from_request()
    if error_response:
        return error_response
    
    payload, new_token, error_message = verify_and_refresh_token(token)
    if payload is None:
        return jsonify({
            'success': False,
            'message': error_message or 'Token无效'
        }), 401
    
    # 2. 原有的业务逻辑
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # ... 查询数据库 ...
        
        response_data = {
            'success': True,
            'message': '获取成功',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'items': items
            }
        }
        
        # 3. 添加新token（如果有）
        response_data = add_new_token_to_response(response_data, new_token)
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500
```

### 示例2: 使用装饰器（更简洁）

```python
# app/api/price_items.py

from flask import Blueprint, request, jsonify, g
from app.utils import require_token_with_refresh

price_items_bp = Blueprint('price_items', __name__, url_prefix='/api/price-items')

@price_items_bp.route('', methods=['GET'])
@require_token_with_refresh  # 添加装饰器
def get_price_items():
    """获取价格项列表（带token自动刷新）"""
    
    # 用户信息已经在 g.current_user 中
    user_id = g.current_user.get('user_id')
    username = g.current_user.get('sub')
    
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # ... 查询数据库 ...
        
        # 直接返回，装饰器会自动处理token刷新
        return jsonify({
            'success': True,
            'message': '获取成功',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'items': items
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500
```

### 示例3: 在工艺规则API中添加

```python
# app/api/process_rules.py

from flask import Blueprint, request, jsonify
from app.utils import verify_and_refresh_token, get_token_from_request, add_new_token_to_response

process_rules_bp = Blueprint('process_rules', __name__, url_prefix='/api/process-rules')

@process_rules_bp.route('', methods=['POST'])
def create_rule():
    """创建工艺规则（带token自动刷新）"""
    
    # 1. 验证token
    token, error_response = get_token_from_request()
    if error_response:
        return error_response
    
    payload, new_token, error_message = verify_and_refresh_token(token)
    if payload is None:
        return jsonify({
            'success': False,
            'message': error_message or 'Token无效'
        }), 401
    
    # 2. 检查权限（可选）
    user_role = payload.get('role')
    if user_role not in ['admin', 'operator']:
        return jsonify({
            'success': False,
            'message': '权限不足'
        }), 403
    
    # 3. 业务逻辑
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['id', 'version_id', 'feature_type', 'name', 'conditions', 'output_params']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必填字段: {field}'
                }), 400
        
        # ... 创建规则 ...
        
        response_data = {
            'success': True,
            'message': '规则创建成功',
            'data': result
        }
        
        # 4. 添加新token
        response_data = add_new_token_to_response(response_data, new_token)
        
        return jsonify(response_data), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'创建失败: {str(e)}'
        }), 500
```

## 完整的API文件示例

```python
# app/api/protected_api.py

from flask import Blueprint, request, jsonify, g
from app.utils import require_token_with_refresh, verify_and_refresh_token, get_token_from_request, add_new_token_to_response
from app.services.database import db_manager
import logging

logger = logging.getLogger(__name__)

protected_bp = Blueprint('protected', __name__, url_prefix='/api')

# 方法1: 使用装饰器（推荐用于简单场景）
@protected_bp.route('/user/profile', methods=['GET'])
@require_token_with_refresh
def get_user_profile():
    """获取用户信息"""
    user_id = g.current_user.get('user_id')
    
    try:
        query = "SELECT * FROM users WHERE user_id = %s"
        user = db_manager.execute_query(query, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'message': '获取成功',
            'data': {
                'user_id': user['user_id'],
                'username': user['username'],
                'email': user['email'],
                'real_name': user['real_name'],
                'role': user['role']
            }
        })
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取失败'
        }), 500

# 方法2: 手动验证（推荐用于需要细粒度控制的场景）
@protected_bp.route('/data/list', methods=['GET'])
def get_data_list():
    """获取数据列表"""
    
    # 获取并验证token
    token, error_response = get_token_from_request()
    if error_response:
        return error_response
    
    payload, new_token, error_message = verify_and_refresh_token(token)
    if payload is None:
        return jsonify({
            'success': False,
            'message': error_message or 'Token无效'
        }), 401
    
    # 检查权限
    user_role = payload.get('role')
    if user_role not in ['admin', 'operator', 'viewer']:
        return jsonify({
            'success': False,
            'message': '权限不足'
        }), 403
    
    try:
        # 业务逻辑
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # 查询数据
        query = "SELECT * FROM some_table LIMIT %s OFFSET %s"
        offset = (page - 1) * page_size
        items = db_manager.execute_query(query, (page_size, offset), fetch_all=True)
        
        response_data = {
            'success': True,
            'message': '获取成功',
            'data': {
                'items': items,
                'page': page,
                'page_size': page_size
            }
        }
        
        # 添加新token
        response_data = add_new_token_to_response(response_data, new_token)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取数据失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取失败'
        }), 500

# 方法3: 可选的token验证（某些接口可以不需要token）
@protected_bp.route('/public/data', methods=['GET'])
def get_public_data():
    """获取公开数据（可选token）"""
    
    # 尝试获取token
    auth_header = request.headers.get('Authorization')
    user_info = None
    new_token = None
    
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            token = parts[1]
            payload, new_token, _ = verify_and_refresh_token(token)
            if payload:
                user_info = payload
    
    try:
        # 根据是否有token返回不同的数据
        if user_info:
            # 已登录用户可以看到更多数据
            query = "SELECT * FROM public_data"
        else:
            # 未登录用户只能看到部分数据
            query = "SELECT id, title FROM public_data WHERE is_public = true"
        
        items = db_manager.execute_query(query, fetch_all=True)
        
        response_data = {
            'success': True,
            'message': '获取成功',
            'data': {
                'items': items,
                'is_authenticated': user_info is not None
            }
        }
        
        # 如果有新token，添加到响应
        if new_token:
            response_data['new_token'] = new_token
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取数据失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取失败'
        }), 500
```

## 集成步骤

### 1. 选择合适的方法

- **装饰器方式**: 适合简单场景，代码最简洁
- **手动验证方式**: 适合需要细粒度控制的场景（如权限检查）
- **可选验证方式**: 适合某些接口可以不需要token的场景

### 2. 添加导入

```python
from app.utils import (
    require_token_with_refresh,      # 装饰器
    verify_and_refresh_token,        # 手动验证
    get_token_from_request,          # 获取token
    add_new_token_to_response        # 添加新token到响应
)
```

### 3. 修改现有接口

只需在现有代码前添加token验证逻辑，业务逻辑保持不变。

### 4. 测试

```bash
# 测试token刷新功能
python test_token_refresh.py
```

## 注意事项

1. **不要在登录接口使用**: 登录接口本身就是获取token的，不需要验证
2. **公开接口不需要**: 完全公开的接口不需要token验证
3. **权限检查**: 验证token后，可以根据用户角色进行权限检查
4. **错误处理**: 确保正确处理token验证失败的情况
5. **日志记录**: 记录token刷新事件，便于监控和调试

## 总结

Token自动刷新功能可以很容易地集成到现有API中，只需要：
1. 添加token验证逻辑
2. 在响应中添加新token（如果有）
3. 客户端更新本地token

这样就可以实现用户会话的自动延长，提高用户体验。
