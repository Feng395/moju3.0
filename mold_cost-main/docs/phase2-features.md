# 第二期功能说明

本文档说明第二期预留的功能接口和实现方案。

## 1. 线割改精铣场景（2D转3D）

### 业务场景
用户在查看成本结果后，发现某个子图使用线割成本较高，希望改用精铣工艺。系统需要将2D线割轮廓拉伸为3D实体，传入NC精铣Agent计算成本。

### API接口
```
POST /api/v1/phase2/jobs/{job_id}/wire-to-milling
```

**请求体**:
```json
{
  "subgraph_id": "UP01",
  "extrusion_height": 10.0,
  "reason": "线割成本过高，改用精铣"
}
```

**响应**:
```json
{
  "change_id": "uuid",
  "status": "pending",
  "old_cost": 617.28,
  "estimated_new_cost": 450.00
}
```

### 实现要点
1. 调用 `cad-parser-mcp` 的 `extrude_2d` 工具
2. 生成3D PRT文件
3. 调用外部NC Agent计算精铣成本
4. 记录工艺变更到 `process_changes` 表

---

## 2. 单个子图3D传入NC场景

### 业务场景
用户需要单独计算某个子图的NC加工成本，需要从完整3D PRT文件中拆分出该子图对应的3D部分，传入NC Agent。

### API接口
```
POST /api/v1/phase2/jobs/{job_id}/subgraphs/{subgraph_id}/nc-single
```

**响应**:
```json
{
  "calc_id": "uuid",
  "status": "pending",
  "drilling_time": 0.5,
  "roughing_time": 2.0,
  "milling_time": 1.5,
  "total_cost": 1200.00
}
```

### 实现要点
1. 调用 `cad-parser-mcp` 的 `split_3d_by_region` 工具
2. 根据2D边界框定位3D区域
3. 提取单个子图的3D实体
4. 调用外部NC Agent的 `/api/nc/estimate_single` 接口

---

## 3. 板料线生成场景

### 业务场景
系统在接收到DWG和PRT文件后，自动为每个2D子图生成板料线（外框线），用于后续的板料切割工艺。

### API接口
```
POST /api/v1/phase2/jobs/{job_id}/generate-sheet-lines
```

**响应**:
```json
{
  "dwg_with_sheet_lines": "/files/2026/01/job_123_with_sheet.dwg",
  "subgraphs": [
    {
      "subgraph_id": "UP01",
      "sheet_area_mm2": 15360.0,
      "sheet_perimeter_mm": 496.0
    }
  ]
}
```

### 实现要点
1. 创建 `SheetLineAgent`
2. 使用Clipper库进行轮廓偏移（向外5mm）
3. 处理圆角和尖角
4. 生成新图层 "SHEET_LINE"
5. 保存带板料线的DWG文件

---

## 4. 多工艺并行处理场景

### 业务场景
同一个任务需要多种工艺并行处理，如线割、NC加工、磨床加工、电火花加工等，系统需要支持动态加载多个工艺Agent，并行计算成本。

### API接口
```
POST /api/v1/phase2/jobs/{job_id}/multi-process
```

**请求体**:
```json
{
  "enabled_processes": ["WIRE", "NC", "GRINDING", "EDM"]
}
```

**响应**:
```json
{
  "job_id": "uuid",
  "processes": ["WIRE", "NC", "GRINDING", "EDM"],
  "status": "processing",
  "cost_breakdown": {
    "wire_cost": 5000.00,
    "nc_cost": 3000.00,
    "grinding_cost": 2000.00,
    "edm_cost": 1500.00,
    "total": 11500.00
  }
}
```

### 实现要点
1. 在 `workflow_config.yaml` 中配置启用的工艺
2. 动态加载Agent（使用importlib）
3. 使用 `asyncio.gather` 并行执行
4. 汇总各工艺成本
5. 生成多工艺报表（包含成本饼图）

---

## 扩展Agent列表

### 待实现的Agent
- `WireToMillingAgent` - 线割改精铣Agent
- `SheetLineAgent` - 板料线生成Agent
- `MultiProcessAgent` - 多工艺编排Agent
- `GrindingAgent` - 磨床加工Agent（调用外部磨床Agent）
- `EDMAgent` - 电火花加工Agent（调用外部电火花Agent）

### Agent注册机制
在 `agent_registry.yaml` 中注册新Agent：

```yaml
agents:
  - name: SheetLineAgent
    module: agents.phase2.sheet_line_agent
    class: SheetLineAgent
    enabled: false  # 第二期启用
    
  - name: GrindingAgent
    module: agents.phase2.grinding_agent
    class: GrindingAgent
    enabled: false
```

---

## 数据库扩展

### 新增字段
- `jobs.dwg_with_sheet_lines` - 带板料线的DWG文件路径
- `subgraphs.has_sheet_line` - 是否有板料线
- `subgraphs.sheet_area_mm2` - 板料面积
- `subgraphs.sheet_perimeter_mm` - 板料周长
- `subgraphs.process_changed` - 工艺是否变更
- `subgraphs.prt_3d_file` - 3D PRT文件路径

### 新增表
- `process_changes` - 工艺变更记录表（已创建）
- `nc_calculations` - NC计算记录表（已创建）

---

## 开发优先级

1. **高优先级**：线割改精铣（业务需求强烈）
2. **中优先级**：板料线生成（自动化需求）
3. **低优先级**：单个子图3D传入NC、多工艺并行处理

---

## 测试计划

### 线割改精铣测试
1. 选择一个线割子图
2. 调用API改为精铣
3. 验证3D文件生成
4. 验证成本计算正确
5. 验证工艺变更记录

### 板料线生成测试
1. 上传DWG文件
2. 调用板料线生成API
3. 验证外框线正确
4. 验证面积和周长计算
5. 验证新DWG文件可打开

---

## 注意事项

1. 所有第二期功能默认禁用，通过配置文件启用
2. API接口已预留，但返回"功能待实现"
3. Agent基类已定义，便于快速扩展
4. 数据库字段已预留，无需修改表结构
5. 前端UI需要添加对应的操作按钮
