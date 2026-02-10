# 项目结构说明

## 目录结构

```
mold_cost_account_python/
├── app/                          # 应用主目录
│   ├── __init__.py              # 应用包初始化
│   ├── api/                     # API路由模块
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证相关API（未使用）
│   │   ├── process_rules.py    # 工艺规则API
│   │   └── price_items.py       # 价格项API
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   └── models.py            # Pydantic数据模型
│   ├── services/                # 业务逻辑服务
│   │   ├── __init__.py
│   │   └── database.py          # 数据库服务
│   └── utils/                   # 工具函数
│       └── __init__.py
│
├── config/                       # 配置文件目录
│   ├── __init__.py
│   ├── config.py                # 配置类
│   ├── .env                     # 环境变量（不提交到git）
│   └── .env.example             # 环境变量示例
│
├── docs/                         # 文档目录
│   ├── README.md                # 项目说明
│   ├── JWT_GUIDE.md             # JWT使用指南
│   ├── PROCESS_RULES_API.md     # 工艺规则API文档（详细）
│   ├── 工艺接口文档.md           # 工艺接口文档（中文）
│   ├── 价格接口文档.md           # 价格接口文档（详细）
│   ├── 价格接口文档-简洁版.md    # 价格接口文档（简洁）
│   ├── GEMINI_FEATURES.md       # Gemini功能说明
│   ├── ICON_FIX_SUMMARY.md      # 图标修复总结
│   └── KIMI_INTERFACE.md        # Kimi接口说明
│
├── tests/                        # 测试文件目录
│   ├── test_login.py            # 登录测试
│   └── test_process_rules.py   # 工艺规则测试
│
├── scripts/                      # 脚本工具目录
│   ├── check_config.py          # 配置检查脚本
│   └── hash_password.py         # 密码哈希工具
│
├── main.py                       # Flask应用主文件
├── run.py                        # 应用启动入口
├── requirements.txt              # Python依赖包
├── pip.ini                       # pip配置
├── PROJECT_STRUCTURE.md          # 项目结构说明（本文件）
└── .gitignore                    # Git忽略文件配置

```

## 模块说明

### 1. app/ - 应用主目录

#### app/api/ - API路由模块
- **process_rules.py**: 工艺规则管理API
  - 创建、查询、更新、删除工艺规则
  - 支持分页和多条件筛选
  - 批量操作支持

- **price_items.py**: 价格项管理API
  - 创建、查询、更新、删除价格项
  - 支持版本管理和分类筛选
  - 批量操作支持

- **auth.py**: 认证相关API（预留）

#### app/models/ - 数据模型
- **models.py**: Pydantic数据模型定义
  - 请求/响应数据验证
  - 数据序列化

#### app/services/ - 业务逻辑服务
- **database.py**: 数据库服务
  - 数据库连接管理
  - 查询执行封装
  - 连接测试功能

#### app/utils/ - 工具函数
- 通用工具函数（待扩展）

### 2. config/ - 配置目录

- **config.py**: 配置类定义
  - 数据库配置
  - JWT配置
  - 应用配置
  - 多环境支持（开发/生产/测试）

- **.env**: 环境变量文件（不提交到git）
- **.env.example**: 环境变量示例

### 3. docs/ - 文档目录

- **README.md**: 项目总体说明
- **JWT_GUIDE.md**: JWT完整使用指南
- **工艺接口文档.md**: 工艺规则API文档
- **价格接口文档.md**: 价格项API文档
- **价格接口文档-简洁版.md**: 价格项API快速参考

### 4. tests/ - 测试目录

- **test_login.py**: 登录功能测试
- **test_process_rules.py**: 工艺规则API测试

### 5. scripts/ - 脚本工具目录

- **check_config.py**: 配置检查工具
- **hash_password.py**: 密码哈希生成工具

### 6. 根目录文件

- **main.py**: Flask应用主文件，包含所有路由和业务逻辑
- **run.py**: 应用启动入口
- **requirements.txt**: Python依赖包列表
- **pip.ini**: pip配置文件

## 启动方式

### 开发环境

```bash
# 方式1：使用run.py
python run.py

# 方式2：直接运行main.py
python main.py
```

### 生产环境

```bash
# 使用gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

## 配置管理

### 1. 环境变量配置

复制 `.env.example` 到 `.env` 并修改：

```bash
cp config/.env.example config/.env
```

### 2. 修改配置

编辑 `config/.env` 文件：

```env
# 数据库配置
DB_HOST=192.168.1.54
DB_PORT=5432
DB_NAME=mold_cost_db
DB_USER=root
DB_PASSWORD=yunzai123

# JWT配置
JWT_SECRET_KEY=your-secret-key
JWT_EXPIRE_MINUTES=30
```

### 3. 环境切换

```bash
# 设置环境
export FLASK_ENV=production  # Linux/Mac
set FLASK_ENV=production     # Windows CMD
$env:FLASK_ENV="production"  # Windows PowerShell
```

## API接口

### 基础URL
```
http://192.168.0.14:8000
```

### 主要接口

#### 1. 用户认证
- `POST /api/login` - 用户登录
- `POST /api/verify-token` - 验证JWT令牌

#### 2. 工艺规则
- `POST /api/process-rules` - 创建规则
- `GET /api/process-rules` - 获取规则列表
- `GET /api/process-rules/{id}` - 获取单个规则
- `PUT /api/process-rules/{id}` - 更新规则
- `DELETE /api/process-rules/{id}` - 删除规则
- `POST /api/process-rules/batch-delete` - 批量删除
- `GET /api/process-rules/by-version-type` - 按版本类型查询

#### 3. 价格项
- `POST /api/price-items` - 创建价格项
- `GET /api/price-items` - 获取价格项列表
- `GET /api/price-items/{id}` - 获取单个价格项
- `PUT /api/price-items/{id}` - 更新价格项
- `DELETE /api/price-items/{id}` - 删除价格项
- `POST /api/price-items/batch-delete` - 批量删除
- `GET /api/price-items/by-version-category` - 按版本类别查询

## 数据库

### 数据库表

1. **users** - 用户表
2. **process_rules** - 工艺规则表
3. **price_items** - 价格项表

### 连接信息

- 主机: 192.168.1.54
- 端口: 5432
- 数据库: mold_cost_db
- 用户: root

## 依赖包

主要依赖：
- Flask 2.3.3 - Web框架
- psycopg2-binary 2.9.7 - PostgreSQL驱动
- bcrypt 4.0.1 - 密码加密
- PyJWT 2.8.0 - JWT令牌
- python-dotenv 1.0.0 - 环境变量加载

## 开发规范

### 1. 代码组织
- API路由放在 `app/api/`
- 业务逻辑放在 `app/services/`
- 数据模型放在 `app/models/`
- 工具函数放在 `app/utils/`

### 2. 命名规范
- 文件名：小写+下划线（snake_case）
- 类名：大驼峰（PascalCase）
- 函数名：小写+下划线（snake_case）
- 常量：大写+下划线（UPPER_CASE）

### 3. 导入规范
```python
# 标准库
import os
import sys

# 第三方库
from flask import Flask
import psycopg2

# 本地模块
from config.config import get_config
from app.services.database import db_manager
```

## 注意事项

1. **环境变量**: `.env` 文件不要提交到git
2. **密钥安全**: 生产环境必须更换JWT密钥
3. **数据库连接**: 确保数据库服务正常运行
4. **端口占用**: 默认端口8000，如被占用需修改
5. **Python版本**: 建议使用Python 3.8+

## 维护建议

1. 定期更新依赖包
2. 备份数据库
3. 监控日志文件
4. 定期检查安全配置
5. 保持文档更新

## 联系方式

如有问题，请查看文档或联系开发团队。
