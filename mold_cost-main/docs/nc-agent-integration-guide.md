# NC Agent 集成指南

> 更新日期: 2026-01-29
> NC Agent API 版本: 1.0

## 概述

本文档说明如何将外部 NC 3D Workflow API 集成到模具成本核算系统中。

## 已完成的修改

### 1. NCTimeAgent 更新

已将 `agents/nc_time_agent.py` 中的 `call_nc_agent` 方法更新为使用新的 API：

- **旧接口**: `POST /api/nc/calculate` (JSON)
- **新接口**: `POST /api/v1/workflow/3d/run` (multipart/form-data)

主要变更：
- 请求方式从 JSON 改为文件上传（multipart/form-data）
- 需要上传实际的 PRT 和 DXF/DWG 文件，而不是传递文件路径
- 添加了 `skip_approval=true` 和 `auto_continue=true` 参数

## 需要配置的环境变量

在 `.env` 文件中确保配置了正确的 NC Agent URL：

```bash
# 外部NC Agent配置
NC_AGENT_URL=http://192.168.0.65:8001
NC_AGENT_TIMEOUT=86400  # 24小时 = 86400秒
```

配置说明：
- `NC_AGENT_URL`: NC Agent 服务的地址（当前配置为 192.168.0.65:8001）
- `NC_AGENT_TIMEOUT`: 请求超时时间（秒），默认60秒
  - 对于复杂模型，建议设置为 86400 秒（24小时）
  - NC 3D 工作流可能需要较长时间处理大型或复杂的模型

如果 NC Agent 部署在其他地址，请相应修改。

## 文件路径要求

调用 NCTimeAgent 时，需要提供以下参数：

```python
context = {
    "job_id": "任务UUID",
    "prt_file_path": "files/jobs/xxx/model.prt",      # MinIO 路径或本地路径
    "dwg_file_path": "files/jobs/xxx/drawing.dxf"     # MinIO 路径或本地路径
}
```

**文件处理逻辑**：

NCTimeAgent 会自动检测文件路径类型：

1. **MinIO 路径**（如 `files/jobs/xxx/model.prt`）
   - 自动从 MinIO 下载到临时目录
   - 临时目录：`/tmp/nc_agent/{job_id}/`
   - 处理完成后自动清理临时文件

2. **本地路径**（如 `/path/to/model.prt` 或 `C:\path\to\model.prt`）
   - 直接使用，不进行下载
   - 需要确保文件存在且可读

**注意事项**：
1. 如果提供 DWG 文件，NC Agent 会自动转换为 DXF
2. 两个文件都是必需的，缺一不可
3. MinIO 配置需要正确（见环境变量配置）

## API 响应结构

NC Agent 返回的响应结构：

```json
{
  "code": 200,
  "message": "执行成功",
  "data": {
    "task_id": "uuid",
    "json_output": {
      "PH-01-M250297-P5.json": {
        "operations": [
          {
            "operation_name": "B_M_A9",
            "parameters": [
              {
                "id": 124,
                "display_name": "Toolpath Time",
                "value": 5.5
              }
            ]
          }
        ]
      }
    },
    "output_dir": "/tmp/...",
    "execution_time": 120.5,
    "steps_completed": 15
  },
  "trace_id": "..."
}
```

## 错误处理

NC Agent 可能返回以下状态码：

| 状态码 | 说明 | 处理方式 |
|--------|------|----------|
| 200 | 执行成功 | 正常处理数据 |
| 206 | 部分完成（某些步骤失败） | 记录警告，处理可用数据 |
| 422 | 参数验证错误 | 检查文件是否存在和有效 |
| 500 | 服务器内部错误 | 重试或记录错误 |

NCTimeAgent 已配置了重试机制（最多3次，指数退避）。

## 测试建议

### 1. 单元测试

创建测试文件 `tests/test_nc_time_agent.py`：

```python
import pytest
from agents.nc_time_agent import NCTimeAgent

@pytest.mark.asyncio
async def test_call_nc_agent():
    agent = NCTimeAgent(nc_agent_url="http://localhost:8001")
    
    result = await agent.call_nc_agent(
        job_id="test-job-id",
        prt_file="path/to/test.prt",
        dwg_file="path/to/test.dxf"
    )
    
    assert result["code"] == 200
    assert "json_output" in result["data"]
```

### 2. 集成测试

使用实际的 PRT 和 DXF 文件测试完整流程：

```bash
# 确保 NC Agent 正在运行
curl http://localhost:8001/health

# 运行集成测试
python -m pytest tests/test_nc_time_agent.py -v
```

## 常见问题

### Q1: 文件上传失败

**问题**: `422 参数验证错误`

**解决方案**:
- 检查文件路径是否正确
- 确认文件存在且可读
- 验证文件格式（必须是 .prt 和 .dxf/.dwg）

### Q2: 超时错误

**问题**: NC Agent 处理时间过长

**解决方案**:
- 当前超时设置为 120 秒
- 如需调整，修改 `NCTimeAgent.__init__` 中的 `self.timeout`
- 考虑异步处理大文件

### Q3: 子图ID映射失败

**问题**: 无法找到对应的 subgraph_id

**解决方案**:
- 检查数据库中的 subgraph_id 格式
- 确认 `_extract_subgraph_id` 方法的提取逻辑
- 查看 NC Agent 返回的子图名称格式

## 下一步工作

1. **文件管理集成**
   - 确定 PRT 和 DXF 文件的存储位置
   - 实现文件上传和存储逻辑
   - 考虑使用 MinIO 或其他对象存储

2. **Orchestrator 集成**
   - 在 `orchestrator_agent.py` 中调用 NCTimeAgent
   - 传递正确的文件路径参数
   - 处理 NC 时间计算结果

3. **监控和日志**
   - 添加详细的日志记录
   - 监控 NC Agent 调用性能
   - 设置告警机制

4. **文档更新**
   - 更新系统架构文档
   - 补充 API 调用示例
   - 编写运维手册

## 参考文档

- [NC 3D Workflow API Reference](../NC_3D_Workflow_API_Reference.md)
- [NC Time Integration](./nc-time-integration.md)
- [Agent Interaction Spec](./agent-interaction-spec.md)
