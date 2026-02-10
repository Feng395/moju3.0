# NC Agent 数据写入验证步骤

## 修复内容总结

### 1. 恢复了数据库写入代码
**文件**: `agents/nc_time_agent.py`

**修复内容**:
- 移除了注释标记，恢复了完整的数据处理流程
- 添加了原始响应保存功能（保存到 `logs/nc_responses/`）

### 2. 注册了 NC Time Agent
**文件**: `workers/orchestrator_worker.py`

**修复内容**:
- 在 Worker 启动时创建 NCTimeAgent 实例
- 将 NCTimeAgent 注册到 Orchestrator

---

## 验证步骤

### 步骤 1: 验证 Agent 注册（已完成 ✅）

```bash
python tests/infrastructure/test_nc_agent_registration.py
```

**预期结果**:
```
✅ 所有 Agent 都已正确注册！
   - cad_agent: True (✅)
   - nc_time_agent: True (✅)
   - pricing_agent: True (✅)
```

---

### 步骤 2: 重启 Orchestrator Worker

**重要**: 必须重启 Worker 才能加载新代码！

#### Windows:
```bash
# 1. 停止旧的 Worker（如果正在运行）
# 按 Ctrl+C 或关闭终端

# 2. 启动新的 Worker
python workers/orchestrator_worker.py
```

#### Linux/Mac:
```bash
# 1. 停止旧的 Worker
pkill -f orchestrator_worker

# 2. 启动新的 Worker
python workers/orchestrator_worker.py
```

**预期日志**:
```
✅ NCTimeAgent 创建成功
✅ 编排器已初始化，已注册 CADAgent、NCTimeAgent 和 PricingAgent
```

---

### 步骤 3: 提交新任务

通过 API Gateway 提交一个新任务：

```bash
curl -X POST http://localhost:8300/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "dwg_file_path": "path/to/your.dwg",
    "prt_file_path": "path/to/your.prt"
  }'
```

**或者使用已有的测试文件**:
```bash
# 使用 API Gateway 的 Web 界面上传文件
# 访问: http://localhost:8300/docs
```

---

### 步骤 4: 观察 Worker 日志

在 Worker 的终端中，应该能看到以下日志：

```
[编排器] 阶段2: 并行执行特征识别 + NC 时间计算
[编排器] 开始并行执行 2 个任务
[NCTimeAgent] 开始处理 NC 时间计算: job_id=xxx
[NCTimeAgent] 调用 NC Agent: http://192.168.0.65:8001
[NCTimeAgent] 上传文件: prt=..., dwg=...
[NCTimeAgent] ========================================
[NCTimeAgent] NC Agent 返回数据（原始）
[NCTimeAgent] 子图总数: 4
[NCTimeAgent] ========================================
[NCTimeAgent] 子图: PH-01-M250297-P5.json
[NCTimeAgent] 操作数量: 10
[NCTimeAgent]   操作: B_M_A9 | 时间: 15.5 | 参数: id=124, Toolpath Time
[NCTimeAgent] ✅ 原始响应已保存: logs/nc_responses/xxx_20240129_143022.json
[NCTimeAgent] 成功处理子图: PH-01-M250297-P5.json -> xxx_PH-01
[NCTimeAgent] NC 时间计算完成: total=4, success=4, failed=0
```

---

### 步骤 5: 验证数据写入

#### 5.1 检查本地文件

```bash
# 查看保存的响应文件
ls -lh logs/nc_responses/

# 查看文件内容（格式化的 JSON）
cat logs/nc_responses/xxx_20240129_143022.json | python -m json.tool
```

**预期结果**:
- 文件存在
- 包含完整的 NC Agent 响应数据

#### 5.2 检查数据库

```bash
# 运行验证脚本
python tests/infrastructure/verify_nc_data.py

# 或者指定任务 ID
python tests/infrastructure/verify_nc_data.py --job-id <job_id>
```

**预期结果**:
```
================================================================================
验证总结:
================================================================================
1. 本地文件: ✅ 已保存
2. subgraphs 表: ✅ 已写入 (4/4 100.0%)
3. features 表: ✅ 已写入 (4/4 100.0%)

✅ NC Agent 数据写入正常！
```

#### 5.3 手动查询数据库

```sql
-- 查询 subgraphs 表的 NC 时间
SELECT 
  subgraph_id,
  nc_roughing_time,
  nc_milling_time,
  drilling_time,
  (nc_roughing_time + nc_milling_time + drilling_time) as total_nc_time
FROM subgraphs
WHERE job_id = '<job_id>'
ORDER BY subgraph_id;

-- 查询 features 表的详细数据
SELECT 
  subgraph_id,
  nc_time_cost
FROM features
WHERE job_id = '<job_id>'
ORDER BY subgraph_id;
```

---

## 故障排查

### 问题 1: Worker 日志中没有 NCTimeAgent 相关日志

**可能原因**:
- Worker 没有重启，还在运行旧代码
- NC Agent 调用失败（网络问题、超时等）

**解决方法**:
1. 确认 Worker 已重启
2. 检查 NC Agent 是否可访问：
   ```bash
   curl http://192.168.0.65:8001/health
   ```
3. 检查环境变量：
   ```bash
   echo $NC_AGENT_URL
   echo $NC_AGENT_TIMEOUT
   ```

---

### 问题 2: 本地文件已保存，但数据库没有数据

**可能原因**:
- 子图 ID 映射失败
- 数据库写入权限问题
- 数据解析失败

**解决方法**:
1. 查看 Worker 日志中的错误信息
2. 检查子图 ID 格式：
   ```sql
   SELECT subgraph_id FROM subgraphs WHERE job_id = '<job_id>';
   ```
3. 检查 NC Agent 返回的子图名称格式

---

### 问题 3: 部分子图有数据，部分没有

**可能原因**:
- 子图 ID 映射失败（名称不匹配）
- NC Agent 返回的数据不完整

**解决方法**:
1. 查看日志中的警告信息：
   ```
   [NCTimeAgent] 未找到子图映射: xxx -> xxx
   ```
2. 对比 NC Agent 返回的子图名称和数据库中的 subgraph_id
3. 检查 `_extract_subgraph_id()` 方法的提取逻辑

---

## 数据写入详细说明

### subgraphs 表字段

| 字段 | 类型 | 说明 | 单位 |
|------|------|------|------|
| `nc_roughing_time` | DECIMAL(10,2) | 开粗时间 | 小时 |
| `nc_milling_time` | DECIMAL(10,2) | 精铣时间 | 小时 |
| `drilling_time` | DECIMAL(10,2) | 钻孔时间 | 小时 |

### features 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `nc_time_cost` | JSONB | NC 时间详细数据 |

**nc_time_cost 格式**:
```json
{
  "nc_details": [
    {"code": "L", "value": "0.25"},
    {"code": "M", "value": "0.50"},
    {"code": "ZXZ", "value": "0.30"},
    {"code": "开粗", "value": "2.50"},
    {"code": "精铣", "value": "1.25"}
  ]
}
```

---

## 相关文档

- [NC Agent 数据存储说明](./nc-agent-data-storage.md)
- [NC Agent 集成指南](./nc-agent-integration-guide.md)
- [NC Agent 快速开始](./nc-agent-quick-start.md)

---

## 测试脚本

- **注册测试**: `tests/infrastructure/test_nc_agent_registration.py`
- **数据验证**: `tests/infrastructure/verify_nc_data.py`
- **连接测试**: `tests/infrastructure/test_nc_agent_connection.py`
- **集成测试**: `tests/infrastructure/test_nc_time_integration.py`
