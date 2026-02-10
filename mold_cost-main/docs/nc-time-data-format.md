# NC 时间数据格式说明

## 时间单位：分钟

所有时间字段的单位都是**分钟**（不是小时）。

---

## 数据库字段

### subgraphs 表

| 字段名 | 类型 | 说明 | 单位 |
|--------|------|------|------|
| `nc_roughing_time` | DECIMAL(10,2) | 开粗时间 | 分钟 |
| `nc_milling_time` | DECIMAL(10,2) | 精铣时间 | 分钟 |
| `drilling_time` | DECIMAL(10,2) | 钻孔时间 | 分钟 |

**示例**:
```sql
nc_roughing_time = 150.00  -- 150 分钟
nc_milling_time = 75.00    -- 75 分钟
drilling_time = 45.00      -- 45 分钟
```

---

### features 表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `nc_time_cost` | JSONB | NC 时间详细数据（按类型汇总） |

**格式**（按类型汇总）:
```json
{
  "nc_details": [
    {"code": "M", "value": "15.50"},     // M 类型钻孔的总时间（分钟）
    {"code": "L", "value": "20.30"},     // L 类型钻孔的总时间（分钟）
    {"code": "ZXZ", "value": "9.20"},    // ZXZ 类型钻孔的总时间（分钟）
    {"code": "开粗", "value": "150.00"}, // 开粗的总时间（分钟）
    {"code": "精铣", "value": "75.00"}   // 精铣的总时间（分钟）
  ]
}
```

**说明**:
- 每个 `code` 只出现一次
- `value` 是该类型所有操作的**总和**（分钟）
- 如果某个类型没有数据，则不出现在数组中

---

## 分类规则

### 1. 钻孔（drilling_time）
- 操作名称以 `ZXZ` 结尾 → code = "ZXZ"
- 操作名称包含 `_M_` 或 `_M数字_` → code = "M" 或 "M1", "M2" 等
- 操作名称包含 `_L_` 或 `_L数字_` → code = "L" 或 "L1", "L2" 等

**示例**:
- `Z_ZXZ` → ZXZ
- `Z_M_A14` → M
- `B_M1_A9` → M1
- `Z_L_A3` → L

### 2. 开粗（nc_roughing_time）
- 操作名称包含 "粗" 字 → code = "开粗"
- 其他未分类的操作也归入开粗

### 3. 精铣（nc_milling_time）
- 操作名称包含 "精" 字 → code = "精铣"

---

## 数据处理流程

```
1. NC Agent 返回原始数据（分钟）
   ↓
2. 按操作名称分类（钻孔/开粗/精铣）
   ↓
3. 提取操作代码（M/L/ZXZ/开粗/精铣）
   ↓
4. 按代码汇总时间（同一代码的所有操作求和）
   ↓
5. 写入 subgraphs 表（汇总时间，分钟）
   ↓
6. 写入 features 表（详细数据，按类型汇总，分钟）
```

---

## 示例

### 原始数据（NC Agent 返回）
```json
{
  "operations": [
    {"operation_name": "Z_ZXZ", "parameters": [{"id": 124, "value": 0.19}]},
    {"operation_name": "Z_M_A14", "parameters": [{"id": 124, "value": 0.91}]},
    {"operation_name": "Z_M_A15", "parameters": [{"id": 124, "value": 1.20}]},
    {"operation_name": "Z_L_A3", "parameters": [{"id": 124, "value": 2.50}]},
    {"operation_name": "开粗_1", "parameters": [{"id": 124, "value": 150.00}]},
    {"operation_name": "精铣_1", "parameters": [{"id": 124, "value": 75.00}]}
  ]
}
```

### 处理后的数据

**subgraphs 表**:
```sql
nc_roughing_time = 150.00  -- 开粗总时间
nc_milling_time = 75.00    -- 精铣总时间
drilling_time = 4.80       -- 钻孔总时间 (0.19 + 0.91 + 1.20 + 2.50)
```

**features 表**:
```json
{
  "nc_details": [
    {"code": "M", "value": "2.11"},      // 0.91 + 1.20 = 2.11
    {"code": "L", "value": "2.50"},      // 2.50
    {"code": "ZXZ", "value": "0.19"},    // 0.19
    {"code": "开粗", "value": "150.00"}, // 150.00
    {"code": "精铣", "value": "75.00"}   // 75.00
  ]
}
```

---

## 查询示例

### 查询某个任务的总时间（分钟）
```sql
SELECT 
  SUM(nc_roughing_time) as total_roughing_min,
  SUM(nc_milling_time) as total_milling_min,
  SUM(drilling_time) as total_drilling_min,
  SUM(nc_roughing_time + nc_milling_time + drilling_time) as total_nc_min
FROM subgraphs
WHERE job_id = '<job_id>';
```

### 转换为小时
```sql
SELECT 
  ROUND(SUM(nc_roughing_time) / 60.0, 2) as total_roughing_hours,
  ROUND(SUM(nc_milling_time) / 60.0, 2) as total_milling_hours,
  ROUND(SUM(drilling_time) / 60.0, 2) as total_drilling_hours
FROM subgraphs
WHERE job_id = '<job_id>';
```

### 查询详细数据
```sql
SELECT 
  subgraph_id,
  nc_time_cost->'nc_details' as nc_details
FROM features
WHERE job_id = '<job_id>';
```
