# NC Agent 快速启动指南

> 更新日期: 2026-01-29

## 系统架构

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  模具成本系统    │      │   MinIO 存储     │      │   NC Agent      │
│  (本机)         │◄────►│  192.168.0.41    │      │  192.168.0.65   │
│                 │      │                  │      │                 │
│  NCTimeAgent    │      │  - PRT 文件      │      │  - 3D 工作流    │
│                 │      │  - DXF 文件      │      │  - NC 时间计算  │
└─────────────────┘      └──────────────────┘      └─────────────────┘
        │                         │                         │
        └─────────────────────────┴─────────────────────────┘
                    1. 下载文件    2. 上传文件    3. 计算时间
```

## 快速开始

### 1. 检查环境配置

确保 `.env` 文件中有以下配置：

```bash
# NC Agent 配置
NC_AGENT_URL=http://192.168.0.65:8001
NC_AGENT_TIMEOUT=60

# MinIO 配置
MINIO_ENDPOINT=192.168.0.41:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_FILES=files
```

### 2. 测试连接

```bash
# 测试 NC Agent 连接
python tests/infrastructure/test_nc_agent_connection.py

# 测试完整集成
python tests/infrastructure/test_nc_time_integration.py
```

### 3. 工作流程

#### 自动流程（推荐）

当 Orchestrator 执行任务时，会自动调用 NCTimeAgent：

```python
# Orchestrator 会自动执行以下流程：
# 1. 从数据库获取 dwg_file_path 和 prt_file_path
# 2. 调用 NCTimeAgent.process()
# 3. NCTimeAgent 自动处理文件下载和上传
# 4. 解析 NC 返回的时间数据
# 5. 保存到数据库
```

#### 手动测试

如果需要手动测试 NCTimeAgent：

```python
import asyncio
from agents.nc_time_agent import NCTimeAgent

async def test():
    agent = NCTimeAgent()
    
    result = await agent.process({
        "job_id": "your-job-id",
        "prt_file_path": "files/jobs/xxx/model.prt",  # MinIO 路径
        "dwg_file_path": "files/jobs/xxx/drawing.dxf"  # MinIO 路径
    })
    
    print(result)

asyncio.run(test())
```

## 文件处理流程

### MinIO 路径（自动下载）

```python
# 输入：MinIO 路径
"files/jobs/2024/01/model.prt"

# NCTimeAgent 自动执行：
# 1. 检测到 MinIO 路径
# 2. 从 MinIO 下载到临时目录：/tmp/nc_agent/{job_id}/prt.prt
# 3. 上传到 NC Agent
# 4. 处理完成后删除临时文件
```

### 本地路径（直接使用）

```python
# 输入：本地路径
"/tmp/model.prt"  # Linux
"C:\\temp\\model.prt"  # Windows

# NCTimeAgent 自动执行：
# 1. 检测到本地路径
# 2. 验证文件存在
# 3. 直接上传到 NC Agent
```

## 数据流

```
1. Job 表
   ├─ dwg_file_path: "files/jobs/xxx/drawing.dxf"
   └─ prt_file_path: "files/jobs/xxx/model.prt"
        ↓
2. NCTimeAgent.process()
   ├─ 下载文件（如果是 MinIO 路径）
   ├─ 调用 NC Agent API
   └─ 解析返回数据
        ↓
3. NC Agent 返回
   {
     "code": 200,
     "data": {
       "json_output": {
         "PH-01-M250297-P5.json": {
           "operations": [...]
         }
       }
     }
   }
        ↓
4. 保存到数据库
   ├─ Subgraph 表
   │  ├─ nc_roughing_time
   │  ├─ nc_milling_time
   │  └─ drilling_time
   └─ Feature 表
      └─ nc_time_cost (JSON)
```

## 常见问题

### Q1: 连接 NC Agent 失败

```bash
❌ 无法连接到 NC Agent: http://192.168.0.65:8001
```

**解决方案**：
1. 检查 NC Agent 是否运行：`curl http://192.168.0.65:8001/`
2. 检查网络连接：`ping 192.168.0.65`
3. 检查防火墙设置
4. 验证 `.env` 中的 `NC_AGENT_URL` 配置

### Q2: MinIO 下载失败

```bash
❌ 从 MinIO 下载文件失败: files/jobs/xxx/model.prt
```

**解决方案**：
1. 检查 MinIO 连接：`curl http://192.168.0.41:9000/`
2. 验证文件路径是否正确
3. 检查 MinIO 访问密钥配置
4. 确认文件在 MinIO 中存在

### Q3: 文件路径格式错误

```bash
❌ 本地文件不存在: /tmp/model.prt
```

**解决方案**：
1. 检查数据库中的文件路径格式
2. 确认是 MinIO 路径还是本地路径
3. 如果是 MinIO 路径，不应该以 `/` 开头

### Q4: 临时文件清理失败

```bash
⚠️ 清理临时文件失败: /tmp/nc_agent/xxx/prt.prt
```

**说明**：这是警告，不影响功能。临时文件会在下次系统重启时自动清理。

## 性能优化

### 超时设置

根据文件大小和模型复杂度调整超时时间：

```bash
# 简单模型（< 10MB，处理时间 < 5分钟）
NC_AGENT_TIMEOUT=300  # 5分钟

# 中等复杂模型（10-50MB，处理时间 5-30分钟）
NC_AGENT_TIMEOUT=3600  # 1小时

# 复杂模型（> 50MB，处理时间 > 30分钟）
NC_AGENT_TIMEOUT=86400  # 24小时（推荐）
```

**当前配置**: 86400 秒（24小时），适用于所有复杂度的模型。

### MinIO 下载优化

```bash
# 增加并发下载数
MINIO_DOWNLOAD_WORKERS=10

# 调整分片大小
MINIO_UPLOAD_PART_SIZE=20971520  # 20MB
```

## 监控和日志

### 查看日志

```bash
# NCTimeAgent 日志
grep "NCTimeAgent" logs/app.log

# 查看文件下载日志
grep "MinIO 路径" logs/app.log

# 查看 NC Agent 调用日志
grep "调用 NC Agent" logs/app.log
```

### 关键指标

- **文件下载时间**：MinIO 下载耗时
- **NC Agent 响应时间**：API 调用耗时
- **数据处理时间**：解析和保存耗时
- **成功率**：成功处理的子图比例

## 下一步

1. ✅ 环境配置完成
2. ✅ 连接测试通过
3. ⏳ 准备测试数据（PRT + DXF 文件）
4. ⏳ 运行完整流程测试
5. ⏳ 集成到生产环境

## 参考文档

- [NC Agent Integration Guide](./nc-agent-integration-guide.md) - 详细集成文档
- [NC 3D Workflow API Reference](../NC_3D_Workflow_API_Reference.md) - API 文档
- [NC Time Integration](./nc-time-integration.md) - 原有集成文档
