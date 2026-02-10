# NC 时间对接集成文档

## 概述

本文档描述了如何将外部 NC Agent 返回的时间数据整理并写入数据库的 `subgraphs` 和 `features` 表。

## 数据流程

```
前端上传文件 (DWG/PRT)
    ↓
生成 job_id
    ↓
CAD 拆图
    ↓
┌───────────────┴───────────────┐
│                               │
│  并行执行（阶段2）             │
│                               │
├─ 特征识别 (CADAgent)          │
│                               │
└─ NC 时间计算 (NCTimeAgent)    │
    ↓
等待用户确认
    ↓
价格计算
```

## 执行时机

NC Agent 在 **CAD 拆图完成后立即启动**，与特征识别并行执行。

### 并行执行的优势

1. **节省时间**：特征识别和 NC 时间计算同时进行
2. **提高效率**：充分利用系统资源
3. **独立失败**：NC 失败不影响特征识别

### 执行顺序

```
阶段1: CAD 拆图
  ↓
阶段2: 并行执行
  ├─ 特征识别（必须成功）
  └─ NC 时间计算（失败不阻断）
  ↓
阶段3: 等待用户确认
  ↓
阶段4: 价格计算
```

## NC Agent 返回数据格式

```json
{
  "code": 200,
  "message": "NC 3D工作流执行成功",
  "data": {
    "task_id": "f827821b-7bed-435c-8ccc-7c5898a45f0c",
    "json_output": {
      "PH-01-M250297-P5.json": {
        "meta_data": {
          "export_time": "2026-01-28 15:13:03",
          "workpiece_name": "PH-01-M250297-P5",
          "total_operations": 13
        },
        "operations": [
          {
            "operation_name": "Z_ZXZ",
            "parameters": [
              {
                "id": 124,
                "display_name": "Toolpath Time",
                "type": "Double",
                "value": 0.3202303106282315
              }
            ]
          },
          {
            "operation_name": "开粗_110_行腔_SIMPLE_17R0.8",
            "parameters": [
              {
                "id": 124,
                "display_name": "Toolpath Time",
                "value": 14.82447987555903
              }
            ]
          }
        ]
      }
    }
  }
}
```

## 子图名称映射

NC 返回的子图名称（如 `PH-01-M250297-P5.json`）需要映射到数据库中的 `subgraph_id`。

### 映射规则

- NC 返回：`PH-01-M250297-P5.json`
- 提取短ID：`PH-01`
- 数据库完整ID：`2cd0b581-f2b9-481d-a2fd-33074f57ebd4_PH-01`

### 实现逻辑

```python
def _extract_subgraph_id(self, subgraph_name: str) -> str:
    """提取短ID（如 PH-01）"""
    name = subgraph_name.replace(".json", "")
    parts = name.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return name

async def _find_subgraph_id(self, job_id: str, short_id: str) -> str:
    """根据短ID查找完整的 subgraph_id"""
    # 查询所有子图，找到以 short_id 结尾的
    # 例如：找到 xxx_PH-01
```

## 时间分类规则

NC 返回的 operations 需要分类到三个字段：

### 1. nc_milling_time（精铣时间）
- **规则**：operation_name 中包含"精"字
- **示例**：
  - `半精_170_往复等高_SIMPLE_D14`
  - `全精_170_MIAN1_SIMPLE_D10`

### 2. nc_roughing_time（开粗时间）
- **规则**：operation_name 中包含"粗"字
- **示例**：
  - `开粗_110_行腔_SIMPLE_17R0.8`
  - `开粗_160_行腔_SIMPLE_D4`

### 3. drilling_time（钻孔时间）
- **规则**：
  - 中间是 `_M_` 或 `_L_`（如 `B_M_A9`, `Z_L_A3`）
  - 最后是 `_ZXZ`（如 `B_ZXZ`, `Z_ZXZ`）
- **示例**：
  - `Z_ZXZ` → 代码：ZXZ
  - `Z_L_A3` → 代码：L
  - `Z_M1_A9` → 代码：M1
  - `B_M_A9` → 代码：M

## 时间单位转换

- **NC 返回**：分钟（minutes）
- **数据库存储**：小时（hours）
- **转换公式**：`hours = minutes / 60`
- **保留位数**：小数点后两位

## 数据库写入

### 1. subgraphs 表

写入三个时间字段（单位：小时）：

```sql
UPDATE subgraphs 
SET 
  nc_roughing_time = 0.25,  -- 开粗时间
  nc_milling_time = 0.22,   -- 精铣时间
  drilling_time = 0.14,     -- 钻孔时间
  updated_at = NOW()
WHERE subgraph_id = '2cd0b581-f2b9-481d-a2fd-33074f57ebd4_PH-01';
```

### 2. features 表

写入 `nc_time_cost` 字段（JSONB 格式）：

```json
{
  "nc_details": [
    {"code": "ZXZ", "value": "0.01"},
    {"code": "L", "value": "0.10"},
    {"code": "M1", "value": "0.03"},
    {"code": "开粗", "value": "0.25"},
    {"code": "精铣", "value": "0.22"}
  ]
}
```

```sql
UPDATE features 
SET 
  nc_time_cost = '{"nc_details": [...]}'::jsonb,
  created_at = NOW()
WHERE subgraph_id = '2cd0b581-f2b9-481d-a2fd-33074f57ebd4_PH-01';
```

## 代码实现

### NCTimeAgent 主要方法

```python
class NCTimeAgent(BaseAgent):
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 NC 时间计算
        
        Args:
            context: {
                "job_id": "任务ID",
                "dwg_file_path": "DWG文件路径",
                "prt_file_path": "PRT文件路径"
            }
        
        Returns:
            {
                "status": "ok" | "error",
                "message": "消息",
                "summary": {
                    "total_subgraphs": 总子图数,
                    "success_count": 成功数,
                    "failed_count": 失败数
                }
            }
        """
        # 1. 调用外部 NC Agent
        # 2. 解析返回的 JSON 数据
        # 3. 处理每个子图的数据
        # 4. 写入数据库
```

### 关键方法

1. **call_nc_agent()** - 调用外部 NC Agent
2. **_extract_subgraph_id()** - 提取子图短ID
3. **_find_subgraph_id()** - 查找完整的 subgraph_id
4. **_parse_operations()** - 解析操作数据，分类时间
5. **_is_drilling_operation()** - 判断是否为钻孔操作
6. **_extract_operation_code()** - 提取操作代码
7. **_save_nc_time_data()** - 保存数据到数据库

## 集成到工作流

在 `OrchestratorAgent` 中，NC Agent 在 CAD 拆图完成后与特征识别并行执行：

```python
# 阶段1：CAD 拆图
split_result = await self._execute_agent_method(...)

# 阶段2：并行执行特征识别 + NC 时间计算
parallel_tasks = []

# 任务1：特征识别
feature_task = self._execute_agent_method(
    job_id, self.cad_agent, "CADAgent", "feature_recognition"
)
parallel_tasks.append(("feature_recognition", feature_task))

# 任务2：NC 时间计算
if self.nc_time_agent:
    nc_task = self._execute_agent_with_context(
        job_id, self.nc_time_agent, "NCTimeAgent", "nc_time_calculation",
        context={
            "job_id": job_id,
            "dwg_file_path": dwg_file_path,
            "prt_file_path": prt_file_path
        }
    )
    parallel_tasks.append(("nc_time_calculation", nc_task))

# 并行执行
task_results = await asyncio.gather(*[task for _, task in parallel_tasks])
```

### 并行执行说明

- **特征识别**：必须成功，失败会阻断流程
- **NC 时间计算**：失败不阻断流程，只记录警告
- **执行时机**：CAD 拆图完成后立即启动
- **性能优势**：两个任务同时进行，节省时间

## 错误处理

- NC Agent 调用失败不会阻断整个流程
- 失败的子图会被记录，但不影响其他子图
- 所有错误都会记录到日志中

## 测试

运行测试脚本验证解析逻辑：

```bash
python infrastructure/test_nc_time_parsing.py
```

测试内容：
- 子图ID提取
- 钻孔操作判断
- 操作代码提取
- 时间解析和分类

## 数据库迁移

如果 features 表没有 `nc_time_cost` 字段，运行迁移脚本：

```bash
# 方式1：使用 Python 脚本
python infrastructure/migrate_add_nc_time_cost.py

# 方式2：使用 SQL 脚本
psql -U root -d mold_cost_db -f infrastructure/add_nc_time_cost_column.sql
```

## 示例数据

### 输入（NC Agent 返回）

```json
{
  "PH-01-M250297-P5.json": {
    "operations": [
      {"operation_name": "Z_ZXZ", "parameters": [{"id": 124, "value": 0.32}]},
      {"operation_name": "Z_L_A3", "parameters": [{"id": 124, "value": 5.97}]},
      {"operation_name": "开粗_110", "parameters": [{"id": 124, "value": 14.82}]},
      {"operation_name": "半精_170", "parameters": [{"id": 124, "value": 13.11}]}
    ]
  }
}
```

### 输出（数据库）

**subgraphs 表：**
- nc_roughing_time: 0.25 小时
- nc_milling_time: 0.22 小时
- drilling_time: 0.10 小时

**features 表：**
```json
{
  "nc_details": [
    {"code": "ZXZ", "value": "0.01"},
    {"code": "L", "value": "0.10"},
    {"code": "开粗", "value": "0.25"},
    {"code": "精铣", "value": "0.22"}
  ]
}
```

## 注意事项

1. **时间单位**：NC 返回分钟，数据库存储小时
2. **子图映射**：需要正确映射短ID到完整ID
3. **分类规则**：严格按照规则分类操作类型
4. **错误处理**：NC 失败不阻断流程
5. **数据精度**：保留小数点后两位

## 相关文件

- `agents/nc_time_agent.py` - NC Agent 实现
- `agents/orchestrator_agent.py` - 工作流编排
- `shared/models.py` - 数据库模型
- `infrastructure/test_nc_time_parsing.py` - 测试脚本
- `infrastructure/migrate_add_nc_time_cost.py` - 迁移脚本
