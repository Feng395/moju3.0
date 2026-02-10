# shared 目录合并计划

## 📋 合并头信息标准格式

所有合并后的文件都应在文件头部添加以下信息：

```python
"""
=== 文件合并信息 ===
合并日期: 2026-02-10
源文件: [源文件路径]
合并策略: [具体策略]
主要改动: [改动说明]
说明: [文件功能说明]
=====================

[原有的文档字符串内容]
"""
```

## 📊 目录结构对比

### mold_cost-main/shared/
```
shared/
├── agent_types.py
├── database.py
├── mcp_client.py
├── message_queue.py
├── models.py
├── progress_publisher.py
└── progress_stages.py
```

### mold_cost_/shared/
```
shared/
├── __init__.py
├── database.py
├── logging_config.py
├── logging_middleware.py
├── message_queue.py
├── models.py
├── permissions.py
├── process_code_mapping.py
├── schemas.py
├── security.py
├── timezone_utils.py
└── validators/
    ├── __init__.py
    ├── business_validator.py
    ├── completeness_validator.py
    ├── field_validator.py
    └── modification_validator.py
```

## 📝 文件对比和合并策略

### 共同文件

#### 1. `database.py` ⭐ 共同文件（重点）
**对比需求：**
- mold_cost-main: 基础数据库连接
- mold_cost_: 增强的数据库连接池、异步支持

**合并策略：** 
- 对比两个版本的功能差异
- 使用 mold_cost_ 为基础（功能更完整）
- 补充 mold_cost-main 的独特功能（如果有）
- 添加合并头信息

---

#### 2. `message_queue.py` ⭐ 共同文件
**对比需求：**
- mold_cost-main: 基础 RabbitMQ 集成
- mold_cost_: 增强的消息队列功能

**合并策略：** 
- 对比两个版本的功能差异
- 使用 mold_cost_ 为基础
- 补充 mold_cost-main 的独特功能（如果有）
- 添加合并头信息

---

#### 3. `models.py` ⭐ 共同文件（重点）
**对比需求：**
- mold_cost-main: 基础数据模型
- mold_cost_: 更完整的数据模型定义

**合并策略：** 
- 对比两个版本的模型定义
- 使用 mold_cost_ 为基础
- 补充 mold_cost-main 的独特模型（如果有）
- 确保模型兼容性
- 添加合并头信息

---

### mold_cost-main 独有文件

#### 4. `agent_types.py` ⭐ mold_cost-main 独有
**功能：** Agent 类型定义

**合并策略：** 
- 复制到 mold_cost_/shared/
- 检查是否与现有代码冲突
- 添加合并头信息

---

#### 5. `mcp_client.py` ⭐ mold_cost-main 独有
**功能：** MCP 客户端封装

**合并策略：** 
- 复制到 mold_cost_/shared/
- 检查是否与 mcp_services 冲突
- 添加合并头信息

---

#### 6. `progress_publisher.py` ⭐ mold_cost-main 独有
**功能：** 进度发布器（WebSocket 进度推送）

**合并策略：** 
- 复制到 mold_cost_/shared/
- 检查是否与现有进度推送机制冲突
- 添加合并头信息

---

#### 7. `progress_stages.py` ⭐ mold_cost-main 独有
**功能：** 进度阶段定义（枚举）

**合并策略：** 
- 复制到 mold_cost_/shared/
- 添加合并头信息

---

### mold_cost_ 独有文件（保留）

#### 8. `__init__.py` ⭐ mold_cost_ 独有
**合并策略：** 
- 保留原文件
- 补充 mold_cost-main 独有模块的导出
- 添加合并头信息

---

#### 9. `logging_config.py` ⭐ mold_cost_ 独有
**功能：** 统一日志配置

**合并策略：** 保留原文件，添加合并头信息

---

#### 10. `logging_middleware.py` ⭐ mold_cost_ 独有
**功能：** 日志中间件（请求日志记录）

**合并策略：** 保留原文件，添加合并头信息

---

#### 11. `permissions.py` ⭐ mold_cost_ 独有
**功能：** RBAC 权限系统

**合并策略：** 保留原文件，添加合并头信息

---

#### 12. `process_code_mapping.py` ⭐ mold_cost_ 独有
**功能：** 工艺代码映射和转换

**合并策略：** 保留原文件，添加合并头信息

---

#### 13. `schemas.py` ⭐ mold_cost_ 独有
**功能：** Pydantic 数据模式定义

**合并策略：** 保留原文件，添加合并头信息

---

#### 14. `security.py` ⭐ mold_cost_ 独有
**功能：** 安全工具（加密、JWT 等）

**合并策略：** 保留原文件，添加合并头信息

---

#### 15. `timezone_utils.py` ⭐ mold_cost_ 独有
**功能：** 上海时区处理工具

**合并策略：** 保留原文件，添加合并头信息

---

### validators/ 子目录（mold_cost_ 独有）

#### 16. `validators/__init__.py`
**合并策略：** 保留原文件，添加合并头信息

#### 17. `validators/business_validator.py`
**功能：** 业务规则验证器

**合并策略：** 保留原文件，添加合并头信息

#### 18. `validators/completeness_validator.py`
**功能：** 数据完整性验证器

**合并策略：** 保留原文件，添加合并头信息

#### 19. `validators/field_validator.py`
**功能：** 字段验证器

**合并策略：** 保留原文件，添加合并头信息

#### 20. `validators/modification_validator.py`
**功能：** 修改验证器

**合并策略：** 保留原文件，添加合并头信息

---

## 📝 合并执行清单

### 阶段 1：准备工作
- [ ] 创建备份：`cp -r mold_cost_/shared mold_cost_/shared_backup`
- [ ] 阅读本合并计划
- [ ] 确认所有文件对比结果

### 阶段 2：对比共同文件

#### 2.1 对比 database.py
- [ ] 读取两个版本的 database.py
- [ ] 对比功能差异（连接池、异步支持、错误处理）
- [ ] 确定合并策略
- [ ] 执行合并
- [ ] 添加合并头信息

#### 2.2 对比 message_queue.py
- [ ] 读取两个版本的 message_queue.py
- [ ] 对比功能差异（消息发送、接收、错误处理）
- [ ] 确定合并策略
- [ ] 执行合并
- [ ] 添加合并头信息

#### 2.3 对比 models.py（重点）
- [ ] 读取两个版本的 models.py
- [ ] 对比模型定义（表结构、字段、关系）
- [ ] 确定合并策略
- [ ] 执行合并（确保兼容性）
- [ ] 添加合并头信息

### 阶段 3：复制 mold_cost-main 独有文件

#### 3.1 复制 agent_types.py
- [ ] 复制文件到 mold_cost_/shared/
- [ ] 检查导入和依赖
- [ ] 添加合并头信息

#### 3.2 复制 mcp_client.py
- [ ] 复制文件到 mold_cost_/shared/
- [ ] 检查与 mcp_services 的关系
- [ ] 添加合并头信息

#### 3.3 复制 progress_publisher.py
- [ ] 复制文件到 mold_cost_/shared/
- [ ] 检查与现有进度推送的兼容性
- [ ] 添加合并头信息

#### 3.4 复制 progress_stages.py
- [ ] 复制文件到 mold_cost_/shared/
- [ ] 添加合并头信息

### 阶段 4：更新 mold_cost_ 独有文件

#### 4.1 更新 __init__.py
- [ ] 补充 mold_cost-main 独有模块的导出
- [ ] 添加合并头信息

#### 4.2 为独有文件添加合并头信息
- [ ] `logging_config.py`
- [ ] `logging_middleware.py`
- [ ] `permissions.py`
- [ ] `process_code_mapping.py`
- [ ] `schemas.py`
- [ ] `security.py`
- [ ] `timezone_utils.py`

#### 4.3 为 validators/ 目录添加合并头信息
- [ ] `validators/__init__.py`
- [ ] `validators/business_validator.py`
- [ ] `validators/completeness_validator.py`
- [ ] `validators/field_validator.py`
- [ ] `validators/modification_validator.py`

### 阶段 5：测试验证
- [ ] 检查导入是否正常
- [ ] 运行单元测试
- [ ] 验证数据库模型兼容性
- [ ] 验证消息队列功能
- [ ] 验证进度推送功能

### 阶段 6：提交到 Git
```bash
git add mold_cost_/shared/
git commit -m "合并 shared 目录

- 对比合并共同文件（database, message_queue, models）
- 复制 mold_cost-main 独有文件（agent_types, mcp_client, progress_publisher, progress_stages）
- 保留 mold_cost_ 的增强功能（日志、权限、安全、验证器）
- 为所有文件添加合并头信息"
```

---

## ⚠️ 注意事项

### 1. models.py 合并重点
- **关键风险：** 数据模型不兼容可能导致数据库错误
- **检查项：**
  - 表名是否一致
  - 字段类型是否兼容
  - 外键关系是否正确
  - 索引定义是否完整
- **建议：** 
  - 仔细对比每个模型
  - 运行数据库迁移测试
  - 备份数据库

### 2. database.py 合并重点
- **检查项：**
  - 连接池配置
  - 异步支持
  - 事务处理
  - 错误处理
- **建议：** 保留 mold_cost_ 的增强功能

### 3. message_queue.py 合并重点
- **检查项：**
  - RabbitMQ 连接配置
  - 消息序列化
  - 错误重试机制
  - 消息确认机制
- **建议：** 保留 mold_cost_ 的增强功能

### 4. 进度推送功能
- **检查项：**
  - progress_publisher.py 与现有 WebSocket 的兼容性
  - progress_stages.py 的阶段定义是否与现有流程匹配
- **建议：** 
  - 测试进度推送功能
  - 确保前端能正确接收

---

## 📊 合并统计

### 文件分类
- **共同文件：** 3 个（database, message_queue, models）
- **mold_cost-main 独有：** 4 个（agent_types, mcp_client, progress_publisher, progress_stages）
- **mold_cost_ 独有：** 8 个文件 + 1 个子目录（validators/，4个文件）

### 合并策略分布
- **对比合并：** 3 个文件（database, message_queue, models）
- **复制文件：** 4 个文件（mold_cost-main 独有）
- **保留文件：** 12 个文件（mold_cost_ 独有）

### 预计工作量
- **对比和合并：** 约 30-40 分钟
- **复制和添加头信息：** 约 15-20 分钟
- **测试验证：** 约 20-30 分钟
- **总计：** 约 1-1.5 小时

---

## 🎯 合并优先级

### 高优先级（核心功能）
1. ✅ `models.py` - 数据模型（最重要）
2. ✅ `database.py` - 数据库连接
3. ✅ `message_queue.py` - 消息队列

### 中优先级（增强功能）
4. ⭐ `progress_publisher.py` - 进度推送
5. ⭐ `progress_stages.py` - 进度阶段
6. ⭐ `mcp_client.py` - MCP 客户端
7. ⭐ `agent_types.py` - Agent 类型

### 低优先级（添加头信息）
8. 📝 mold_cost_ 独有文件（12个）

---

## 📋 详细对比检查表

### database.py 对比检查
- [ ] 数据库引擎配置
- [ ] 连接池大小和超时设置
- [ ] 异步会话管理
- [ ] 事务处理机制
- [ ] 错误处理和重试逻辑
- [ ] 连接健康检查
- [ ] 日志记录

### message_queue.py 对比检查
- [ ] RabbitMQ 连接配置
- [ ] 队列声明和绑定
- [ ] 消息发送方法
- [ ] 消息接收和消费
- [ ] 消息序列化（JSON/Pickle）
- [ ] 错误处理和重试
- [ ] 连接断开重连
- [ ] 消息确认机制

### models.py 对比检查
- [ ] 所有表模型定义
- [ ] 字段类型和约束
- [ ] 主键和外键
- [ ] 索引定义
- [ ] 关系定义（一对多、多对多）
- [ ] 默认值和自动填充
- [ ] 时间戳字段
- [ ] 软删除支持

---

**文档版本：** v1.0  
**创建时间：** 2026-02-10  
**最后更新：** 2026-02-10
