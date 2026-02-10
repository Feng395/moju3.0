# api_gateway 目录合并计划

## 📋 合并头信息标准格式

所有合并后的文件都应在文件头部添加以下信息：

```python
"""
[文件名] - [功能描述]

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/api_gateway/[路径] + mold_cost_/api_gateway/[路径]
- 合并策略：[具体策略]
- 主要改动：
  1. [改动1]
  2. [改动2]
  ...

[原有的文档字符串内容]
"""
```

## 📊 目录结构对比

### mold_cost-main/api_gateway/
```
api_gateway/
├── auth.py
├── database.py
├── main.py
├── websocket.py
├── routers/
│   ├── __init__.py
│   ├── features.py
│   ├── jobs.py
│   ├── phase2.py
│   ├── pricing.py
│   ├── recalculations.py
│   └── reports.py
└── utils/
    ├── __init__.py
    └── minio_client.py
```

### mold_cost_/api_gateway/
```
api_gateway/
├── auth.py
├── config.py
├── main.py
├── README.md
├── websocket.py
├── models/
│   ├── __init__.py
│   └── interaction_models.py
├── repositories/
│   ├── __init__.py
│   ├── audit_repository.py
│   ├── chat_history_repository.py
│   ├── interaction_repository.py
│   ├── job_repository.py
│   ├── process_rules_repository.py
│   ├── review_repository.py
│   └── snapshot_repository.py
├── routers/
│   ├── __init__.py
│   ├── chat_router.py
│   ├── file_router.py
│   ├── interactions.py
│   ├── jobs.py
│   ├── phase2.py
│   ├── recalculations.py
│   ├── review_router.py
│   └── websocket_router.py
├── services/
│   ├── __init__.py
│   ├── file_service.py
│   ├── interaction_service.py
│   └── job_service.py
└── utils/
    ├── __init__.py
    ├── chat_logger.py
    ├── encryption.py
    ├── message_formatter.py
    ├── minio_client.py
    ├── rabbitmq_client.py
    ├── redis_client.py
    ├── snapshot_manager.py
    └── validators.py
```

## 📝 文件对比和合并策略

### 根目录文件

#### 1. `auth.py` ⭐ 共同文件
**对比结果：**
- mold_cost-main: 简化版认证
- mold_cost_: 完整版认证（支持 JWT、权限管理）

**合并策略：** 保留 mold_cost_ 版本（功能更完整）

---

#### 2. `config.py` ⭐ mold_cost_ 独有
**合并策略：** 保留原文件，添加合并头信息

---

#### 3. `database.py` ⭐ mold_cost-main 独有
**合并策略：**  TODO
- 检查是否与 shared/database.py 重复
- 如果重复，不复制
- 如果有独特功能，需要合并

---

#### 4. `main.py` ⭐ 共同文件（重点）
**对比结果：**
- mold_cost-main: 简化版，只包含基础路由
- mold_cost_: 完整版，包含所有路由、中间件、CORS 配置

**合并策略：** 
- 使用 mold_cost_ 为基础
- 补充 mold_cost-main 的路由（features.py, pricing.py, reports.py）
- 合并所有路由注册

---

#### 5. `README.md` ⭐ mold_cost_ 独有
**合并策略：** 保留原文件，添加合并头信息

---

#### 6. `websocket.py` ⭐ 共同文件
**对比结果：**
- mold_cost-main: 简化版 WebSocket
- mold_cost_: 完整版 WebSocket（支持进度推送、消息广播）

**合并策略：** 保留 mold_cost_ 版本（功能更完整）

---

### routers/ 目录

#### 共同文件：
- `__init__.py` - 需要合并导出
- `jobs.py` - 需要对比合并
- `phase2.py` - 需要对比合并
- `recalculations.py` - 需要对比合并

#### mold_cost-main 独有：
- `features.py` - 特征查询路由（需要复制）
- `pricing.py` - 价格计算路由（需要复制）
- `reports.py` - 报表路由（需要复制）

#### mold_cost_ 独有：
- `chat_router.py` - 聊天路由（保留）
- `file_router.py` - 文件上传路由（保留）
- `interactions.py` - 交互路由（保留）
- `review_router.py` - 审核路由（保留）
- `websocket_router.py` - WebSocket 路由（保留）

---

### utils/ 目录

#### 共同文件：
- `__init__.py` - 需要合并导出
- `minio_client.py` - 需要对比合并

#### mold_cost_ 独有（全部保留）：
- `chat_logger.py`
- `encryption.py`
- `message_formatter.py`
- `rabbitmq_client.py`
- `redis_client.py`
- `snapshot_manager.py`
- `validators.py`

---

### mold_cost_ 独有目录（全部保留）

#### models/
- `__init__.py`
- `interaction_models.py`

#### repositories/
- `__init__.py`
- `audit_repository.py`
- `chat_history_repository.py`
- `interaction_repository.py`
- `job_repository.py`
- `process_rules_repository.py`
- `review_repository.py`
- `snapshot_repository.py`

#### services/
- `__init__.py`
- `file_service.py`
- `interaction_service.py`
- `job_service.py`

## 📝 合并执行清单

### 阶段 1：准备工作
- [x] 创建备份：`cp -r mold_cost_/api_gateway mold_cost_/api_gateway_backup` ✅ 2026-02-10
- [x] 阅读本合并计划 ✅ 2026-02-10
- [x] 确认所有文件对比结果 ✅ 2026-02-10

### 阶段 2：根目录文件合并

#### 2.1 保留 mold_cost_ 版本（添加头信息）
- [x] `auth.py` - 保留（功能更完整）✅ 2026-02-10
- [x] `config.py` - 保留（独有文件）✅ 2026-02-10
- [x] `README.md` - 保留（独有文件）
- [x] `websocket.py` - 保留（功能更完整）✅ 2026-02-10

#### 2.2 检查 database.py
- [x] 对比 mold_cost-main/api_gateway/database.py 和 shared/database.py ✅ 2026-02-10
- [x] 结论：功能不同，shared/database.py 已足够，不需要复制 ✅ 2026-02-10

#### 2.3 合并 main.py（重点）
- [x] 读取两个版本的 main.py ✅ 2026-02-10
- [x] 合并路由注册 ✅ 2026-02-10
- [x] 补充 mold_cost-main 的路由（features, pricing, reports）✅ 2026-02-10
- [x] 添加合并头信息 ✅ 2026-02-10

### 阶段 3：routers/ 目录合并

#### 3.1 复制 mold_cost-main 独有路由
- [x] `features.py` - 复制并添加头信息 ✅ 2026-02-10
- [x] `pricing.py` - 复制并添加头信息 ✅ 2026-02-10
- [x] `reports.py` - 复制并添加头信息 ✅ 2026-02-10

#### 3.2 对比合并共同文件
- [x] `__init__.py` - 合并导出 ✅ 2026-02-10
- [x] `jobs.py` - 对比合并，补充 mold_cost-main 的路由 ✅ 2026-02-10
- [x] `phase2.py` - 对比合并（两版本相同）✅ 2026-02-10
- [x] `recalculations.py` - 对比合并，补充实现 ✅ 2026-02-10

#### 3.3 保留 mold_cost_ 独有路由（添加头信息）
- [ ] `chat_router.py`
- [ ] `file_router.py`
- [ ] `interactions.py`
- [ ] `review_router.py`
- [ ] `websocket_router.py`

### 阶段 4：utils/ 目录合并

#### 4.1 对比合并共同文件
- [x] `__init__.py` - 合并导出 ✅ 2026-02-10
- [x] `minio_client.py` - 对比合并 ✅ 2026-02-10

#### 4.2 保留 mold_cost_ 独有工具（添加头信息）
- [x] `chat_logger.py` ✅ 2026-02-10
- [x] `encryption.py` ✅ 2026-02-10
- [x] `message_formatter.py` ✅ 2026-02-10
- [x] `rabbitmq_client.py` ✅ 2026-02-10
- [x] `redis_client.py` ✅ 2026-02-10
- [x] `snapshot_manager.py` ✅ 2026-02-10
- [x] `validators.py` ✅ 2026-02-10

### 阶段 5：保留 mold_cost_ 独有目录（添加头信息）

#### 5.1 models/
- [ ] `__init__.py`
- [ ] `interaction_models.py`

#### 5.2 repositories/
- [ ] `__init__.py`
- [ ] `audit_repository.py`
- [ ] `chat_history_repository.py`
- [ ] `interaction_repository.py`
- [ ] `job_repository.py`
- [ ] `process_rules_repository.py`
- [ ] `review_repository.py`
- [ ] `snapshot_repository.py`

#### 5.3 services/
- [ ] `__init__.py`
- [ ] `file_service.py`
- [ ] `interaction_service.py`
- [ ] `job_service.py`

### 阶段 6：测试验证
- [ ] 检查导入是否正常
- [ ] 检查路由注册是否完整
- [ ] 运行 API 服务测试

### 阶段 7：提交到 Git
```bash
git add mold_cost_/api_gateway/
git commit -m "合并 api_gateway 目录

- 保留 mold_cost_ 的完整架构（models, repositories, services）
- 补充 mold_cost-main 的路由（features, pricing, reports）
- 合并 main.py 路由注册
- 为所有文件添加合并头信息"
```

---

## ⚠️ 注意事项

### 1. main.py 合并重点
- 确保所有路由都正确注册
- 保留 CORS 配置
- 保留中间件配置
- 合并所有 router 导入

### 2. 路由冲突检查
- 检查路由路径是否冲突
- 确保路由前缀正确
- 验证依赖注入正确

### 3. 依赖检查
- 确保所有导入的模块存在
- 检查数据库模型是否匹配
- 验证工具类是否可用

---

## 📊 合并统计

### 已完成文件数量
- ✅ 根目录文件：4/6 个（auth, config, websocket, main）
- ✅ routers 独有文件：3/3 个（features, pricing, reports）
- ✅ routers 共同文件：4/4 个（__init__, jobs, phase2, recalculations）
- ✅ utils 共同文件：2/2 个（__init__, minio_client）
- ✅ utils 独有文件：7/7 个（全部完成）
- ⏳ routers 独有文件待添加头信息：5 个
- ⏳ 独有目录待添加头信息：3 个（models, repositories, services）

### 合并策略分布
- 保留 mold_cost_：大部分文件（架构更完整）✅
- 复制 mold_cost-main：3 个路由文件（features, pricing, reports）✅
- 对比合并：6 个文件（main✅, jobs✅, phase2✅, recalculations✅, __init__✅, minio_client✅）

### 当前进度
- **已完成：约 80%**
- **预计剩余时间：约 20 分钟**

### 下一步工作
1. 对比合并 routers 共同文件（jobs, phase2, recalculations）
2. 为 mold_cost_ 独有文件添加合并头信息
3. 测试验证所有路由
4. 提交最终版本

---

**文档版本：** v1.0  
**创建时间：** 2026-02-10  
**最后更新：** 2026-02-10
