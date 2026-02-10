# 文档目录

## API接口文档

### 📘 完整文档
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - 完整的API接口文档
  - 包含所有接口的详细说明
  - 请求/响应示例
  - 错误码说明
  - 使用指南

### 📗 快速参考
- **[API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md)** - API快速参考手册
  - 简洁的接口列表
  - 快速查询
  - 常用命令

### 📦 Postman集合
- **[Postman_Collection.json](Postman_Collection.json)** - Postman导入文件
  - 可直接导入Postman
  - 包含所有接口
  - 自动保存token

## 功能文档

### 🔐 JWT认证
- **[JWT_GUIDE.md](JWT_GUIDE.md)** - JWT完整使用指南
  - JWT基础知识
  - 实现细节
  - 安全最佳实践

### 🔄 Token自动刷新
- **[TOKEN_AUTO_REFRESH.md](TOKEN_AUTO_REFRESH.md)** - Token自动刷新详细文档
- **[TOKEN_REFRESH_INTEGRATION_EXAMPLE.md](TOKEN_REFRESH_INTEGRATION_EXAMPLE.md)** - 集成示例
- **[TOKEN_REFRESH_SUMMARY.md](TOKEN_REFRESH_SUMMARY.md)** - 功能总结

### 🔧 工艺规则
- **[工艺接口文档.md](工艺接口文档.md)** - 工艺规则接口详细文档（中文）
- **[PROCESS_RULES_API.md](PROCESS_RULES_API.md)** - 工艺规则API文档（英文）

### 💰 价格项
- **[价格接口文档.md](价格接口文档.md)** - 价格项接口详细文档（中文）
- **[价格接口文档-简洁版.md](价格接口文档-简洁版.md)** - 价格项接口简洁版

### 🐛 问题修复
- **[DATABASE_FIX_SUMMARY.md](DATABASE_FIX_SUMMARY.md)** - 数据库事务提交问题修复
- **[DESCRIPTION_FIELD_UPDATE.md](DESCRIPTION_FIELD_UPDATE.md)** - description字段添加说明

## 快速开始

### 1. 查看API文档

```bash
# 查看完整文档
cat docs/API_DOCUMENTATION.md

# 查看快速参考
cat docs/API_QUICK_REFERENCE.md
```

### 2. 导入Postman集合

1. 打开Postman
2. 点击 Import
3. 选择 `docs/Postman_Collection.json`
4. 设置环境变量：
   - `base_url`: http://192.168.0.14:8000
   - `token`: (登录后自动保存)

### 3. 测试接口

```bash
# 1. 登录获取token
curl -X POST http://192.168.0.14:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'

# 2. 使用token访问接口
curl -X GET "http://192.168.0.14:8000/api/price-items?page=1&page_size=5" \
  -H "Authorization: Bearer <your_token>"
```

## 文档结构

```
docs/
├── README.md                                    # 本文件
├── API_DOCUMENTATION.md                         # 完整API文档
├── API_QUICK_REFERENCE.md                       # 快速参考
├── Postman_Collection.json                      # Postman集合
│
├── JWT_GUIDE.md                                 # JWT指南
├── TOKEN_AUTO_REFRESH.md                        # Token自动刷新
├── TOKEN_REFRESH_INTEGRATION_EXAMPLE.md         # 集成示例
├── TOKEN_REFRESH_SUMMARY.md                     # 功能总结
│
├── 工艺接口文档.md                               # 工艺规则文档（中文）
├── PROCESS_RULES_API.md                         # 工艺规则文档（英文）
├── 价格接口文档.md                               # 价格项文档（中文）
├── 价格接口文档-简洁版.md                        # 价格项文档（简洁版）
│
├── DATABASE_FIX_SUMMARY.md                      # 数据库修复说明
├── DESCRIPTION_FIELD_UPDATE.md                  # 字段更新说明
├── GEMINI_FEATURES.md                           # Gemini功能
├── ICON_FIX_SUMMARY.md                          # 图标修复
└── KIMI_INTERFACE.md                            # Kimi接口
```

## 接口概览

### 认证接口 (2个)
- POST `/api/login` - 用户登录
- POST `/api/verify-token` - Token验证

### 工艺规则接口 (7个)
- POST `/api/process-rules` - 创建规则
- GET `/api/process-rules/{id}` - 获取单个规则
- GET `/api/process-rules` - 获取规则列表
- PUT `/api/process-rules/{id}` - 更新规则
- DELETE `/api/process-rules/{id}` - 删除规则
- POST `/api/process-rules/batch-delete` - 批量删除
- GET `/api/process-rules/by-version-type` - 按版本类型查询

### 价格项接口 (7个)
- POST `/api/price-items` - 创建价格项
- GET `/api/price-items/{id}` - 获取单个价格项
- GET `/api/price-items` - 获取价格项列表
- PUT `/api/price-items/{id}` - 更新价格项
- DELETE `/api/price-items/{id}` - 删除价格项
- POST `/api/price-items/batch-delete` - 批量删除
- GET `/api/price-items/by-version-category` - 按版本类别查询

**总计**: 16个接口

## 特性

✓ JWT认证  
✓ Token自动刷新  
✓ 分页查询  
✓ 多条件筛选  
✓ 批量操作  
✓ 完整的CRUD  
✓ 详细的错误信息  
✓ 跨域支持  

## 技术栈

- **后端**: Python 3.10 + Flask
- **数据库**: PostgreSQL 14
- **认证**: JWT (PyJWT)
- **密码加密**: bcrypt

## 配置信息

- **服务地址**: http://192.168.0.14:8000
- **数据库**: PostgreSQL 192.168.1.54:5432/mold_cost_db
- **Token有效期**: 30000分钟（约21天）
- **刷新阈值**: 50%

## 更新日志

### v1.0.0 (2026-01-18)
- ✓ 完成所有基础接口
- ✓ 实现Token自动刷新
- ✓ 修复数据库事务问题
- ✓ 添加完整文档

## 联系方式

如有问题或建议，请联系开发团队。
