# InteractiveAgent 集成需求文档

## 文档信息
- **创建日期**: 2026-01-16
- **负责人**: 人员B2（API网关与交互工程师）
- **集成方**: 人员B1（Agent编排与流程工程师）
- **版本**: v1.0

---

## 一、项目背景

### 1.1 当前问题

在模具成本核算系统中，特征识别阶段可能无法自动识别所有必要参数（如厚度、材料等），需要用户手动补充。

**当前流程的痛点**：
```
CADAgent 特征识别
    ↓
发现缺少参数（thickness_mm = null）
    ↓
❌ 需要手动保存状态到数据库
❌ 需要手动管理暂停/恢复逻辑
❌ 需要手动处理多次交互
❌ 代码复杂，难以维护
```

### 1.2 解决方案

引入 **InteractiveAgent**（基于 LangGraph），专门处理需要人机交互的任务。

**新流程**：
```
CADAgent 特征识别
    ↓
发现缺少参数
    ↓
InteractiveAgent 接管
    ↓
✅ 自动暂停工作流
✅ 自动保存状态到 checkpoints 表
✅ 生成交互卡片推送给前端
✅ 等待用户输入
✅ 自动恢复并继续执行
```

---

## 二、用户故事

### 用户故事 1：参数补全交互

**作为** 系统用户  
**我想要** 在特征识别不完整时，能够通过友好的界面补充缺失参数  
**以便** 系统能够继续自动计算成本，而不需要重新上传文件

#### 验收标准

1. WHEN 特征识别发现缺少必要参数 THEN 系统 SHALL 自动暂停工作流并通知用户
2. WHEN 用户收到参数补全请求 THEN 系统 SHALL 显示清晰的输入表单，包含参数说明和默认值
3. WHEN 用户提交参数 THEN 系统 SHALL 自动验证参数有效性
4. WHEN 参数验证通过 THEN 系统 SHALL 自动恢复工作流并继续执行
5. WHEN 用户提交无效参数 THEN 系统 SHALL 显示错误提示并允许重新输入
6. WHEN 工作流暂停超过 24 小时 THEN 系统 SHALL 自动清理状态并标记任务为超时

### 用户故事 2：多次交互支持

**作为** 系统用户  
**我想要** 在一个任务中多次补充参数  
**以便** 处理复杂的模具零件，逐步完善信息

#### 验收标准

1. WHEN 第一次参数补全完成后发现还有其他缺失参数 THEN 系统 SHALL 再次暂停并请求补充
2. WHEN 用户完成多次参数补全 THEN 系统 SHALL 保留所有历史输入记录
3. WHEN 用户想要查看之前的输入 THEN 系统 SHALL 提供历史记录查询功能

### 用户故事 3：状态持久化

**作为** 系统管理员  
**我想要** 工作流状态能够持久化保存  
**以便** 系统重启或崩溃后能够恢复任务

#### 验收标准

1. WHEN 工作流暂停等待用户输入 THEN 系统 SHALL 将完整状态保存到 checkpoints 表
2. WHEN 系统重启 THEN 系统 SHALL 能够从 checkpoints 表恢复所有暂停的任务
3. WHEN 任务完成或失败 THEN 系统 SHALL 清理对应的 checkpoint 记录
4. WHEN checkpoint 数据损坏 THEN 系统 SHALL 标记任务为失败并通知用户

---

## 三、功能需求

### 需求 1：工作流暂停与恢复

**优先级**: P0（必须）

#### 功能描述

InteractiveAgent 必须能够在任意节点暂停工作流，等待用户输入后自动恢复。

#### 技术要求

1. 使用 LangGraph 的 `interrupt_before` 机制实现自动暂停
2. 使用 PostgreSQL checkpointer 持久化状态
3. 支持通过 `thread_id` 恢复特定任务
4. 暂停时自动更新 jobs 表状态为 `need_user_input`
5. 恢复时自动更新 jobs 表状态为 `processing`

#### 性能要求

- 暂停操作延迟 < 100ms
- 恢复操作延迟 < 200ms
- checkpoint 写入延迟 < 500ms

### 需求 2：交互卡片生成

**优先级**: P0（必须）

#### 功能描述

根据缺失参数自动生成交互卡片，通过 WebSocket 推送给前端。

#### 卡片类型

1. **missing_input**: 缺少必要参数
2. **confirmation**: 需要用户确认
3. **choice**: 需要用户选择（如工艺方案）
4. **review**: 需要人工审核

#### 卡片数据结构

```json
{
  "card_id": "card_001",
  "type": "missing_input",
  "title": "缺少厚度参数",
  "message": "子图 UP01 无法识别厚度，请手动输入",
  "severity": "error",
  "fields": [
    {
      "key": "thickness_mm",
      "label": "厚度(mm)",
      "subgraph_id": "UP01",
      "component": "number",
      "required": true,
      "default": 10,
      "min": 1,
      "max": 500,
      "validation": {
        "type": "number",
        "rules": ["positive", "integer"]
      }
    }
  ],
  "buttons": [
    {
      "key": "submit",
      "label": "提交并继续",
      "style": "primary"
    },
    {
      "key": "cancel",
      "label": "取消任务",
      "style": "default"
    }
  ]
}
```

### 需求 3：参数验证

**优先级**: P0（必须）

#### 验证规则

1. **类型验证**: 数字、字符串、枚举等
2. **范围验证**: 最小值、最大值
3. **格式验证**: 正则表达式
4. **业务验证**: 自定义验证逻辑

#### 验证时机

- 前端提交时（客户端验证）
- API 接收时（服务端验证）
- 应用到状态前（业务验证）

### 需求 4：超时处理

**优先级**: P1（重要）

#### 超时策略

1. **短超时**: 5 分钟无响应 → 发送提醒通知
2. **中超时**: 1 小时无响应 → 发送警告邮件
3. **长超时**: 24 小时无响应 → 自动取消任务

#### 超时后处理

- 更新 jobs 表状态为 `timeout`
- 清理 checkpoints 表记录
- 发送通知给用户
- 记录到 operation_logs

---

## 四、非功能需求

### 4.1 性能要求

| 指标 | 要求 | 说明 |
|------|------|------|
| 暂停延迟 | < 100ms | 从检测到缺失参数到暂停工作流 |
| 恢复延迟 | < 200ms | 从接收用户输入到恢复工作流 |
| checkpoint 写入 | < 500ms | 状态持久化到数据库 |
| checkpoint 读取 | < 300ms | 从数据库恢复状态 |
| 并发支持 | 100 个任务 | 同时暂停等待用户输入的任务数 |

### 4.2 可靠性要求

1. **状态一致性**: checkpoint 与 jobs 表状态必须一致
2. **故障恢复**: 系统重启后能够恢复所有暂停任务
3. **数据完整性**: checkpoint 数据不能丢失或损坏
4. **幂等性**: 重复提交用户输入不会导致重复执行

### 4.3 可维护性要求

1. **日志完整**: 记录所有暂停/恢复操作到 operation_logs
2. **监控指标**: 暴露 Prometheus 指标（暂停任务数、平均等待时间等）
3. **错误追踪**: 集成 Sentry 错误追踪
4. **文档完善**: 提供 API 文档和使用示例

### 4.4 安全要求

1. **权限验证**: 只有任务创建者可以提交参数
2. **输入校验**: 防止 SQL 注入、XSS 攻击
3. **数据加密**: checkpoint 中的敏感数据需要加密
4. **审计日志**: 记录所有用户输入操作

---

## 五、集成接口规范

### 5.1 与 OrchestratorAgent 的集成

#### 集成方式 A：消息队列路由（推荐）

```
API Gateway
    ↓
判断是否需要交互
    ├─ 需要 → RabbitMQ: interactive_queue → InteractiveAgent
    └─ 不需要 → RabbitMQ: standard_queue → OrchestratorAgent
```

**优点**：
- 解耦，互不影响
- 可以独立扩展
- 失败隔离

#### 集成方式 B：OrchestratorAgent 内部调用

```python
# OrchestratorAgent 中
if requires_interaction:
    result = await interactive_agent.start(job_id)
else:
    result = await self._standard_flow(job_id)
```

**优点**：
- 实现简单
- 统一入口

**缺点**：
- 耦合度高
- 难以独立测试

### 5.2 API 接口规范

#### 接口 1：提交用户输入

```
POST /api/v1/jobs/{job_id}/submit-input
```

**请求头**：
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**请求体**：
```json
{
  "card_id": "card_001",
  "action": "submit",
  "inputs": {
    "UP01": {
      "thickness_mm": 10,
      "material": "45#"
    }
  }
}
```

**响应**：
```json
{
  "status": "ok",
  "message": "参数已提交，任务继续执行",
  "job_id": "job_123",
  "current_stage": "processing"
}
```

#### 接口 2：查询暂停任务

```
GET /api/v1/jobs/{job_id}/pending-cards
```

**响应**：
```json
{
  "status": "ok",
  "cards": [
    {
      "card_id": "card_001",
      "type": "missing_input",
      "created_at": "2026-01-16T10:00:00Z",
      "fields": [...]
    }
  ]
}
```

#### 接口 3：取消暂停任务

```
POST /api/v1/jobs/{job_id}/cancel
```

**响应**：
```json
{
  "status": "ok",
  "message": "任务已取消",
  "job_id": "job_123"
}
```

### 5.3 WebSocket 消息规范

#### 消息类型 1：工作流暂停

```json
{
  "type": "workflow_paused",
  "job_id": "job_123",
  "thread_id": "job_123",
  "stage": "waiting_user_input",
  "timestamp": "2026-01-16T10:00:00Z",
  "cards": [
    {
      "card_id": "card_001",
      "type": "missing_input",
      "title": "缺少厚度参数",
      "fields": [...]
    }
  ]
}
```

#### 消息类型 2：工作流恢复

```json
{
  "type": "workflow_resumed",
  "job_id": "job_123",
  "thread_id": "job_123",
  "stage": "decision",
  "timestamp": "2026-01-16T10:05:00Z",
  "message": "参数已补全，继续执行"
}
```

---

## 六、数据库设计

### 6.1 checkpoints 表（新增）

```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_parent ON checkpoints(parent_checkpoint_id);
CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at);
```

**字段说明**：
- `thread_id`: 任务 ID（通常等于 job_id）
- `checkpoint_id`: checkpoint 唯一 ID（LangGraph 自动生成）
- `parent_checkpoint_id`: 父 checkpoint ID（用于追溯历史）
- `checkpoint`: 完整的工作流状态（JSONB 格式）
- `metadata`: 元数据（如创建时间、节点名称等）

### 6.2 user_interactions 表（新增）

```sql
CREATE TABLE IF NOT EXISTS user_interactions (
    interaction_id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    card_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    inputs JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

CREATE INDEX idx_user_interactions_job_id ON user_interactions(job_id);
CREATE INDEX idx_user_interactions_user_id ON user_interactions(user_id);
```

**字段说明**：
- `interaction_id`: 交互记录 ID
- `job_id`: 任务 ID
- `card_id`: 卡片 ID
- `card_type`: 卡片类型（missing_input, confirmation 等）
- `user_id`: 用户 ID
- `action`: 用户操作（submit, cancel 等）
- `inputs`: 用户输入的数据

### 6.3 jobs 表（修改）

需要添加新字段：

```sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS thread_id TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS requires_interaction BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS interaction_count INTEGER DEFAULT 0;
```

---

## 七、测试要求

### 7.1 单元测试

**测试覆盖率**: ≥ 80%

**必测场景**：
1. 工作流暂停逻辑
2. 工作流恢复逻辑
3. 参数验证逻辑
4. 卡片生成逻辑
5. 超时处理逻辑

### 7.2 集成测试

**必测场景**：
1. 完整的暂停-输入-恢复流程
2. 多次交互流程
3. 并发任务处理
4. 系统重启后恢复
5. 超时自动取消

### 7.3 性能测试

**测试指标**：
- 暂停延迟
- 恢复延迟
- checkpoint 读写性能
- 并发支持能力

---

## 八、交接清单

### 8.1 你需要提供给同事的

#### 文档
- [x] 本需求文档
- [ ] 现有 OrchestratorAgent 代码说明
- [ ] 数据库 schema 文档
- [ ] API 接口文档
- [ ] WebSocket 消息格式文档

#### 代码
- [ ] BaseAgent 基类
- [ ] 现有 Agent 示例（CADAgent, PricingAgent）
- [ ] 数据库模型（shared/models.py）
- [ ] 进度发布器（shared/progress_publisher.py）

#### 环境
- [ ] 开发环境配置（.env.example）
- [ ] 数据库连接信息
- [ ] RabbitMQ 配置
- [ ] Redis 配置

#### 测试
- [ ] 测试数据（示例 DWG 文件）
- [ ] Mock MCP 客户端（tests/mock_mcp_client.py）
- [ ] 现有测试用例

### 8.2 同事需要交付的

#### 代码
- [ ] InteractiveAgent 实现
- [ ] LangGraph 工作流定义
- [ ] API 路由实现
- [ ] WebSocket 消息处理

#### 测试
- [ ] 单元测试（覆盖率 ≥ 80%）
- [ ] 集成测试
- [ ] 性能测试报告

#### 文档
- [ ] 实现文档
- [ ] API 文档
- [ ] 部署文档
- [ ] 故障排查指南

---

## 九、时间计划

### 阶段 1：准备阶段（1-2 天）
- [ ] 你：准备交接文档和代码
- [ ] 同事：熟悉项目结构和现有代码
- [ ] 你：创建 checkpoints 表和 user_interactions 表
- [ ] 同事：搭建开发环境

### 阶段 2：开发阶段（5-7 天）
- [ ] 同事：实现 InteractiveAgent 核心逻辑
- [ ] 同事：实现 API 接口
- [ ] 同事：实现 WebSocket 消息处理
- [ ] 你：提供技术支持和代码审查

### 阶段 3：集成阶段（2-3 天）
- [ ] 你：集成 InteractiveAgent 到 OrchestratorAgent
- [ ] 同事：配合调试和修复问题
- [ ] 你：更新 API Gateway 路由逻辑

### 阶段 4：测试阶段（2-3 天）
- [ ] 同事：完成单元测试和集成测试
- [ ] 你：进行端到端测试
- [ ] 共同：性能测试和压力测试

### 阶段 5：上线阶段（1 天）
- [ ] 你：部署到测试环境
- [ ] 共同：验证功能
- [ ] 你：部署到生产环境

**总计**: 11-16 天

---

## 十、风险与应对

### 风险 1：性能不达标

**风险描述**: checkpoint 读写性能可能影响整体流程

**应对措施**:
- 使用 Redis 作为 checkpoint 缓存层
- 异步写入数据库
- 定期清理过期 checkpoint

### 风险 2：状态不一致

**风险描述**: checkpoints 表与 jobs 表状态可能不一致

**应对措施**:
- 使用数据库事务保证一致性
- 定期检查和修复不一致数据
- 实现状态同步机制

### 风险 3：学习曲线

**风险描述**: 同事可能不熟悉 LangGraph

**应对措施**:
- 提供 LangGraph 学习资料
- 安排技术分享会
- 提供代码示例和最佳实践

### 风险 4：集成问题

**风险描述**: InteractiveAgent 与现有系统集成可能出现问题

**应对措施**:
- 充分的集成测试
- 灰度发布，先处理少量任务
- 保留回滚方案

---

## 十一、成功标准

### 功能完整性
- [x] 支持工作流暂停与恢复
- [x] 支持交互卡片生成
- [x] 支持参数验证
- [x] 支持超时处理
- [x] 支持多次交互

### 性能指标
- [x] 暂停延迟 < 100ms
- [x] 恢复延迟 < 200ms
- [x] checkpoint 写入 < 500ms
- [x] 支持 100 个并发暂停任务

### 质量指标
- [x] 单元测试覆盖率 ≥ 80%
- [x] 集成测试通过率 100%
- [x] 无 P0/P1 级别 bug

### 用户体验
- [x] 用户能够顺利补充参数
- [x] 界面友好，提示清晰
- [x] 响应及时，无明显延迟

---

## 附录

### 附录 A：LangGraph 学习资源

1. **官方文档**: https://langchain-ai.github.io/langgraph/
2. **示例代码**: https://github.com/langchain-ai/langgraph/tree/main/examples
3. **视频教程**: [待补充]

### 附录 B：相关文档

1. `docs/langgraph-migration-analysis.md` - LangGraph 迁移分析
2. `docs/langgraph-use-cases.md` - LangGraph 应用场景
3. `docs/agent-interaction-spec.md` - Agent 交互规范
4. `docs/progress-publishing-guide.md` - 进度发布指南

### 附录 C：联系方式

- **你的联系方式**: [待补充]
- **同事的联系方式**: [待补充]
- **技术支持群**: [待补充]
