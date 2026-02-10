# NC 3D 工作流 API 参考文档

> 版本: 1.0
> 日期: 2026-01-27

## 概述

NC 3D 工作流 API 提供了一个简化接口，用于执行完整的 NC 3D 工作流（步骤 1 至 步骤 15）。它支持直接文件上传（必须包含 PRT 和 DXF/DWG 文件），自动管理临时目录，并允许跳过人工审批步骤。

**基础 URL**: `http://localhost:8001`

---

## 接口端点

### 执行工作流

触发 NC 3D 工作流的执行。

- **URL**: `/api/v1/workflow/3d/run`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|-----------|------|----------|-------------|
| `prt_file` | File | 是 | 3D 模型文件 (.prt)。 |
| `dxf_file` | File | 是 | 2D 图纸文件 (.dxf 或 .dwg)。如果提供 .dwg，将自动转换为 .dxf。 |
| `output_dir` | String | 否 | 自定义输出目录路径。如果不提供，将创建一个临时目录，并在执行完成后自动清理（除非通过其他方式处理检索）。 |
| `skip_approval` | Boolean | 否 | 是否跳过人工审批步骤（默认：`true`）。 |
| `auto_continue` | Boolean | 否 | 完成后是否自动继续下一步（默认：`true`）。 |

#### 响应格式

API 返回一个包含执行结果的 JSON 对象。

- **成功 (200)**: 工作流顺利完成。
- **部分成功 (206)**: 工作流已完成，但某些步骤失败。
- **错误 (500)**: 执行过程中发生严重错误。

**响应结构:**

```json
{
  "code": "integer",      // 200, 206, 或 500
  "message": "string",    // 状态消息
  "data": {
    "task_id": "string",          // 此执行追踪的唯一 UUID
    "json_output": "object",      // 步骤 15 的最终 JSON 输出（如果成功）
    "output_dir": "string",       // 使用的输出目录路径
    "execution_time": "float",    // 总执行时间（秒）
    "steps_completed": "integer", // 成功完成的步骤数（成功时）
    "failed_at_step": "integer",  // 失败发生的步骤编号（失败时）
    "error_details": "string"     // 详细错误消息（失败时）
  },
  "trace_id": "string"    // 请求追踪 ID
}
```

#### 示例

**cURL**

```bash
curl -X POST "http://localhost:8001/api/v1/workflow/3d/run" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "prt_file=@./model.prt" \
  -F "dxf_file=@./drawing.dxf" \
  -F "skip_approval=true"
```

**Python (requests)**

```python
import requests

url = "http://localhost:8001/api/v1/workflow/3d/run"
files = {
    'prt_file': open('model.prt', 'rb'),
    'dxf_file': open('drawing.dxf', 'rb')
}
data = {
    'skip_approval': 'true'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

---

## 错误代码

| 代码 | 说明 |
|------|-------------|
| 200  | 执行成功。 |
| 206  | 部分完成（某些步骤失败）。 |
| 422  | 参数验证错误（例如：缺失必要文件）。 |
| 500  | 服务器内部错误。 |
