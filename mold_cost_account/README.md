# 模具成本核算系统 - 项目文档

## 📚 文档导航

### 快速开始
- **[QUICK_START.md](QUICK_START.md)** - 项目快速启动指南
- **[QUICK_START_TOKEN_REFRESH.md](QUICK_START_TOKEN_REFRESH.md)** - Token自动刷新快速开始

### API文档
- **[docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)** - 完整API接口文档 ⭐
- **[docs/API_QUICK_REFERENCE.md](docs/API_QUICK_REFERENCE.md)** - API快速参考
- **[docs/Postman_Collection.json](docs/Postman_Collection.json)** - Postman导入文件

### 功能文档
- **[docs/JWT_GUIDE.md](docs/JWT_GUIDE.md)** - JWT认证完整指南
- **[docs/TOKEN_AUTO_REFRESH.md](docs/TOKEN_AUTO_REFRESH.md)** - Token自动刷新详细文档
- **[docs/工艺接口文档.md](docs/工艺接口文档.md)** - 工艺规则接口文档
- **[docs/价格接口文档.md](docs/价格接口文档.md)** - 价格项接口文档

### 项目结构
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - 项目文件结构说明
- **[代码整理总结.md](代码整理总结.md)** - 代码整理记录

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

编辑 `config/.env` 文件：

```bash
# 数据库配置
DB_HOST=192.168.1.54
DB_PORT=5432
DB_NAME=mold_cost_db
DB_USER=root
DB_PASSWORD=yunzai123

# JWT配置
JWT_SECRET_KEY=your-secret-key-change-in-production-2024
JWT_EXPIRE_MINUTES=30000
```

### 3. 启动服务

```bash
python run.py
```

服务将在 `http://192.168.0.14:8000` 启动

### 4. 测试接口

```bash
# 登录
curl -X POST http://192.168.0.14:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'

# 获取价格项列表
curl -X GET "http://192.168.0.14:8000/api/price-items?page=1&page_size=5" \
  -H "Authorization: Bearer <your_token>"
```

---

## 📋 接口概览

### 认证接口 (2个)
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/login` | POST | 用户登录 |
| `/api/verify-token` | POST | Token验证 |

### 工艺规则接口 (7个)
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/process-rules` | POST | 创建规则 |
| `/api/process-rules/{id}` | GET | 获取单个规则 |
| `/api/process-rules` | GET | 获取规则列表 |
| `/api/process-rules/{id}` | PUT | 更新规则 |
| `/api/process-rules/{id}` | DELETE | 删除规则 |
| `/api/process-rules/batch-delete` | POST | 批量删除 |
| `/api/process-rules/by-version-type` | GET | 按版本类型查询 |

### 价格项接口 (7个)
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/price-items` | POST | 创建价格项 |
| `/api/price-items/{id}` | GET | 获取单个价格项 |
| `/api/price-items` | GET | 获取价格项列表 |
| `/api/price-items/{id}` | PUT | 更新价格项 |
| `/api/price-items/{id}` | DELETE | 删除价格项 |
| `/api/price-items/batch-delete` | POST | 批量删除 |
| `/api/price-items/by-version-category` | GET | 按版本类别查询 |

**总计**: 16个接口

---

## 🎯 核心特性

✓ **JWT认证**: 基于JWT的用户认证系统  
✓ **Token自动刷新**: 滑动过期时间机制，自动延长会话  
✓ **完整CRUD**: 工艺规则和价格项的完整增删改查  
✓ **分页查询**: 支持分页和多条件筛选  
✓ **批量操作**: 支持批量删除  
✓ **事务安全**: 数据库事务正确提交  
✓ **跨域支持**: CORS配置  

---

## 🛠️ 技术栈

- **后端框架**: Flask 2.3.3
- **数据库**: PostgreSQL 14
- **认证**: JWT (PyJWT 2.8.0)
- **密码加密**: bcrypt 4.0.1
- **数据库驱动**: psycopg2 2.9.7

---

## 📁 项目结构

```
mold_cost_account_python/
├── app/                          # 应用代码
│   ├── api/                      # API路由
│   │   ├── auth.py              # 认证接口
│   │   ├── process_rules.py     # 工艺规则接口
│   │   └── price_items.py       # 价格项接口
│   ├── models/                   # 数据模型
│   ├── services/                 # 业务服务
│   │   └── database.py          # 数据库服务
│   ├── middleware/               # 中间件
│   │   └── token_refresh.py     # Token刷新中间件
│   └── utils/                    # 工具函数
│       └── token_helper.py      # Token辅助函数
├── config/                       # 配置文件
│   ├── .env                     # 环境变量
│   └── config.py                # 配置类
├── docs/                         # 文档
│   ├── API_DOCUMENTATION.md     # API文档
│   └── ...                      # 其他文档
├── scripts/                      # 脚本工具
├── tests/                        # 测试文件
├── main.py                       # 主应用
├── run.py                        # 启动入口
└── requirements.txt              # 依赖列表
```

---

## 🔧 配置说明

### 环境变量 (.env)

```bash
# Flask配置
FLASK_ENV=development

# 数据库配置
DB_HOST=192.168.1.54
DB_PORT=5432
DB_NAME=mold_cost_db
DB_USER=root
DB_PASSWORD=yunzai123

# JWT配置
JWT_SECRET_KEY=your-secret-key-change-in-production-2024
JWT_EXPIRE_MINUTES=30000

# 安全配置
MAX_FAILED_ATTEMPTS=5
BCRYPT_ROUNDS=12

# 日志配置
LOG_LEVEL=INFO
```

---

## 📝 开发指南

### 添加新接口

1. 在 `app/api/` 下创建新的蓝图文件
2. 实现接口逻辑
3. 在 `main.py` 中注册蓝图
4. 更新API文档

### 使用Token自动刷新

```python
from app.utils import verify_and_refresh_token, get_token_from_request, add_new_token_to_response

@app.route('/api/your-endpoint', methods=['GET'])
def your_endpoint():
    # 获取并验证token
    token, error_response = get_token_from_request()
    if error_response:
        return error_response
    
    payload, new_token, error_message = verify_and_refresh_token(token)
    if payload is None:
        return jsonify({'success': False, 'message': error_message}), 401
    
    # 业务逻辑
    response_data = {'success': True, 'data': {}}
    
    # 添加新token
    response_data = add_new_token_to_response(response_data, new_token)
    
    return jsonify(response_data)
```

---

## 🧪 测试

### 运行测试脚本

```bash
# 测试登录
python tests/test_login.py

# 测试工艺规则
python tests/test_process_rules.py

# 测试Token刷新
python test_token_refresh.py
```

---

## 📊 数据库

### 连接信息
- **主机**: 192.168.1.54
- **端口**: 5432
- **数据库**: mold_cost_db
- **用户**: root
- **密码**: yunzai123

### 主要表
- `users` - 用户表
- `process_rules` - 工艺规则表
- `price_items` - 价格项表

---

## 🔐 安全说明

1. **密码加密**: 使用bcrypt加密存储
2. **JWT认证**: 所有接口需要有效token
3. **Token刷新**: 自动延长会话，提高安全性
4. **失败锁定**: 连续登录失败5次后锁定账号
5. **HTTPS**: 生产环境建议使用HTTPS

---

## 📞 联系方式

- **服务地址**: http://192.168.0.14:8000
- **数据库**: PostgreSQL 192.168.1.54:5432/mold_cost_db

---

## 📅 更新日志

### v1.0.0 (2026-01-18)
- ✓ 实现用户登录和JWT认证
- ✓ 实现工艺规则完整CRUD
- ✓ 实现价格项完整CRUD
- ✓ 实现Token自动刷新机制
- ✓ 修复数据库事务提交问题
- ✓ 添加description字段支持
- ✓ 完善API文档

---

## 📖 相关文档

- [完整API文档](docs/API_DOCUMENTATION.md)
- [JWT使用指南](docs/JWT_GUIDE.md)
- [Token自动刷新](docs/TOKEN_AUTO_REFRESH.md)
- [项目结构说明](PROJECT_STRUCTURE.md)

---

**祝开发愉快！** 🎉
