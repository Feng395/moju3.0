# Agent 交互规范文档

> **版本**: v1.0  
> **日期**: 2026-01-13  
> **适用**: 编排器与所有 Agent 的交互

---

## 一、通用规范

### 1.1 请求格式（统一）

所有 Agent 的 `process()` 方法接收相同的参数格式：

```python
context = {
    "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**说明**：
- 只传 `job_id`，Agent 自己从数据库查询需要的数据
- 保持接口简洁，降低耦合

---

### 1.2 返回格式（统一）

所有 Agent 返回相同的结构：

#### 成功返回：
```python
{
    "status": "ok",
    "message": "操作成功的描述",
    
    # 可选：简单统计信息
    "summary": {
        "key1": "value1",
        "key2": "value2"
    }
}
```

#### 失败返回：
```python
{
    "status": "error",
    "message": "错误描述",
    "error_code": "ERROR_CODE"  # 标准错误码
}
```

---

## 二、CADAgent 交互规范

### 2.1 编排器 → CADAgent

```python
# 调用方式
result = await cad_agent.process({"job_id": "xxx"})
```

### 2.2 CADAgent 内部操作

```python
async def process(context):
    job_id = context["job_id"]
    
    # 1. 从数据库查询 job 信息
    job = await db.query(Job).filter(Job.job_id == job_id).first()
    dwg_file_path = job.dwg_file_path
    user_id = job.user_id
    
    # 2. 从 MinIO 下载文件
    file_content = minio_client.get_file(dwg_file_path)
    
    # 3. 调用拆图服务（HTTP API 或 MCP）
    chaitu_result = await call_chaitu_service(file_content)
    
    # 4. 调用特征识别服务
    feature_results = await call_feature_service(chaitu_result["subgraphs"])
    
    # 5. 【写入数据库 - CADAgent 职责】
    for subgraph in chaitu_result["subgraphs"]:
        # 写入 subgraphs 表
        await db.execute(
            insert(Subgraph).values(
                subgraph_id=subgraph["subgraph_id"],  # 幂等键
                job_id=job_id,
                part_name=subgraph["part_name"],
                part_code=subgraph["part_code"],
                material=subgraph["material"],
                subgraph_file_url=subgraph["dxf_path"],
                status="pending",
                created_at=datetime.utcnow()
            )
        )
    
    for feature in feature_results:
        # 写入 features 表
        await db.execute(
            insert(Feature).values(
                subgraph_id=feature["subgraph_id"],
                job_id=job_id,
                version=1,
                length_mm=feature.get("length_mm"),
                width_mm=feature.get("width_mm"),
                thickness_mm=feature.get("thickness_mm"),
                material=feature.get("material"),
                weight_kg=feature.get("weight_kg"),
                top_view_wire_length=feature.get("wire_length_mm"),
                is_complete=feature.get("is_complete", True),
                missing_params=feature.get("missing_params", []),
                created_at=datetime.utcnow()
            )
        )
    
    await db.commit()
    
    # 6. 返回简单结果
    return {
        "status": "ok",
        "message": f"成功拆分 {len(chaitu_result['subgraphs'])} 个子图",
        "summary": {
            "subgraph_count": len(chaitu_result["subgraphs"]),
            "feature_count": len(feature_results)
        }
    }
```

### 2.3 CADAgent → 编排器（返回）

#### 成功：
```python
{
    "status": "ok",
    "message": "成功拆分 5 个子图",
    "summary": {
        "subgraph_count": 5,
        "feature_count": 5
    }
}
```

#### 失败：
```python
{
    "status": "error",
    "message": "DWG 文件解析失败: 文件格式不支持",
    "error_code": "FILE_PARSE_ERROR"
}
```

### 2.4 CADAgent 写入的表

| 表名 | 操作 | 幂等键 | 说明 |
|------|------|--------|------|
| `subgraphs` | INSERT | `subgraph_id` | 子图基本信息 |
| `features` | INSERT | `subgraph_id` + `version` | 特征数据 |

---

## 三、DecisionAgent 交互规范

### 3.1 编排器 → DecisionAgent

```python
result = await decision_agent.process({"job_id": "xxx"})
```

### 3.2 DecisionAgent 内部操作

```python
async def process(context):
    job_id = context["job_id"]
    
    # 1. 从数据库读取数据
    job = await db.query(Job).filter(Job.job_id == job_id).first()
    subgraphs = await db.query(Subgraph).filter(Subgraph.job_id == job_id).all()
    features = await db.query(Feature).filter(Feature.job_id == job_id).all()
    
    # 2. 从工艺快照表读取规则
    process_snapshots = await db.query(JobProcessSnapshot).filter(
        JobProcessSnapshot.job_id == job_id,
        JobProcessSnapshot.version_id == job.process_version_locked
    ).all()
    
    # 3. 匹配工艺规则（可选：调用 MCP 服务）
    decisions = []
    for subgraph, feature in zip(subgraphs, features):
        # 匹配规则
        matched_rule = match_process_rule(feature, process_snapshots)
        
        # 计算输出参数
        output_params = calculate_output_params(feature, matched_rule)
        
        decisions.append({
            "subgraph_id": subgraph.subgraph_id,
            "matched_rule_id": matched_rule.snapshot_id,
            "output_params": output_params
        })
    
    # 4. 【写入数据库 - DecisionAgent 职责】
    for decision in decisions:
        # 更新 subgraphs 表的工艺字段
        await db.execute(
            update(Subgraph)
            .where(Subgraph.subgraph_id == decision["subgraph_id"])
            .values(
                process_description=decision["output_params"].get("process_description"),
                slow_wire_length=decision["output_params"].get("slow_wire_length"),
                slow_wire_side_length=decision["output_params"].get("slow_wire_side_length"),
                nc_roughing_time=decision["output_params"].get("nc_roughing_time"),
                nc_milling_time=decision["output_params"].get("nc_milling_time"),
                applied_snapshot_ids=[decision["matched_rule_id"]],
                rule_reason=decision["output_params"].get("rule_reason"),
                updated_at=datetime.utcnow()
            )
        )
    
    await db.commit()
    
    # 5. 返回简单结果
    return {
        "status": "ok",
        "message": "工艺决策完成",
        "summary": {
            "decision_count": len(decisions)
        }
    }
```

### 3.3 DecisionAgent → 编排器（返回）

#### 成功：
```python
{
    "status": "ok",
    "message": "工艺决策完成",
    "summary": {
        "decision_count": 5
    }
}
```

#### 失败：
```python
{
    "status": "error",
    "message": "工艺决策失败: 未找到匹配的工艺规则",
    "error_code": "RULE_NOT_FOUND"
}
```

### 3.4 DecisionAgent 写入的表

| 表名 | 操作 | 幂等键 | 说明 |
|------|------|--------|------|
| `subgraphs` | UPDATE | `subgraph_id` | 更新工艺相关字段 |

---

## 四、PricingAgent 交互规范

### 4.1 编排器 → PricingAgent

```python
result = await pricing_agent.process({"job_id": "xxx"})
```

### 4.2 PricingAgent 内部操作

```python
async def process(context):
    job_id = context["job_id"]
    
    # 1. 从数据库读取数据
    job = await db.query(Job).filter(Job.job_id == job_id).first()
    subgraphs = await db.query(Subgraph).filter(Subgraph.job_id == job_id).all()
    features = await db.query(Feature).filter(Feature.job_id == job_id).all()
    
    # 2. 从价格快照表读取价格
    price_snapshots = await db.query(JobPriceSnapshot).filter(
        JobPriceSnapshot.job_id == job_id,
        JobPriceSnapshot.version_id == job.price_version_locked
    ).all()
    
    # 3. 计算价格（可选：调用 MCP 服务）
    total_cost = 0
    for subgraph, feature in zip(subgraphs, features):
        # 计算材料成本
        material_cost = calculate_material_cost(feature, price_snapshots)
        
        # 计算热处理成本
        heat_treatment_cost = calculate_heat_treatment_cost(feature, price_snapshots)
        
        # 计算线割成本
        wire_cost = calculate_wire_cost(subgraph, price_snapshots)
        
        # 计算 NC 成本
        nc_cost = calculate_nc_cost(subgraph, price_snapshots)
        
        # 子图总成本
        subgraph_total = material_cost + heat_treatment_cost + wire_cost + nc_cost
        total_cost += subgraph_total
        
        # 4. 【写入数据库 - PricingAgent 职责】
        await db.execute(
            update(Subgraph)
            .where(Subgraph.subgraph_id == subgraph.subgraph_id)
            .values(
                material_cost=material_cost,
                heat_treatment_cost=heat_treatment_cost,
                slow_wire_cost=wire_cost,
                nc_roughing_cost=nc_cost,
                total_cost=subgraph_total,
                processing_cost_total=heat_treatment_cost + wire_cost + nc_cost,
                updated_at=datetime.utcnow()
            )
        )
    
    await db.commit()
    
    # 5. 返回简单结果
    return {
        "status": "ok",
        "message": "价格计算完成",
        "summary": {
            "total_cost": float(total_cost),
            "currency": "CNY"
        }
    }
```

### 4.3 PricingAgent → 编排器（返回）

#### 成功：
```python
{
    "status": "ok",
    "message": "价格计算完成",
    "summary": {
        "total_cost": 2752.50,
        "currency": "CNY"
    }
}
```

#### 失败：
```python
{
    "status": "error",
    "message": "价格计算失败: 未找到价格快照",
    "error_code": "SNAPSHOT_NOT_FOUND"
}
```

### 4.4 PricingAgent 写入的表

| 表名 | 操作 | 幂等键 | 说明 |
|------|------|--------|------|
| `subgraphs` | UPDATE | `subgraph_id` | 更新成本字段 |

---

## 五、编排器操作规范

### 5.1 编排器调用流程

```python
async def orchestrate(job_id: str):
    start_time = datetime.utcnow()
    
    # 1. 更新 jobs 表：开始处理
    await db.execute(
        update(Job)
        .where(Job.job_id == job_id)
        .values(
            status="processing",
            current_stage="cad_parsing",
            progress=0,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    # 2. 调用 CADAgent
    cad_start = datetime.utcnow()
    cad_result = await cad_agent.process({"job_id": job_id})
    cad_duration = int((datetime.utcnow() - cad_start).total_seconds() * 1000)
    
    if cad_result["status"] == "error":
        # 记录失败日志
        await log_operation(job_id, "CADAgent", "cad_parsing", cad_result, cad_duration)
        await update_job_failed(job_id, cad_result["message"])
        return
    
    # 记录成功日志
    await log_operation(job_id, "CADAgent", "cad_parsing", cad_result, cad_duration)
    
    # 更新 jobs 表
    await db.execute(
        update(Job)
        .where(Job.job_id == job_id)
        .values(
            current_stage="cad_completed",
            progress=30,
            total_subgraphs=cad_result["summary"]["subgraph_count"],
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    # 3. 调用 DecisionAgent
    decision_start = datetime.utcnow()
    decision_result = await decision_agent.process({"job_id": job_id})
    decision_duration = int((datetime.utcnow() - decision_start).total_seconds() * 1000)
    
    if decision_result["status"] == "error":
        await log_operation(job_id, "DecisionAgent", "process_decision", decision_result, decision_duration)
        await update_job_failed(job_id, decision_result["message"])
        return
    
    await log_operation(job_id, "DecisionAgent", "process_decision", decision_result, decision_duration)
    
    await db.execute(
        update(Job)
        .where(Job.job_id == job_id)
        .values(
            current_stage="decision_completed",
            progress=60,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    # 4. 调用 PricingAgent
    pricing_start = datetime.utcnow()
    pricing_result = await pricing_agent.process({"job_id": job_id})
    pricing_duration = int((datetime.utcnow() - pricing_start).total_seconds() * 1000)
    
    if pricing_result["status"] == "error":
        await log_operation(job_id, "PricingAgent", "pricing_calculation", pricing_result, pricing_duration)
        await update_job_failed(job_id, pricing_result["message"])
        return
    
    await log_operation(job_id, "PricingAgent", "pricing_calculation", pricing_result, pricing_duration)
    
    # 5. 更新 jobs 表：完成
    await db.execute(
        update(Job)
        .where(Job.job_id == job_id)
        .values(
            status="completed",
            current_stage="completed",
            progress=100,
            total_cost=pricing_result["summary"]["total_cost"],
            currency=pricing_result["summary"]["currency"],
            completed_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
```

### 5.2 编排器写入 operation_logs

```python
async def log_operation(
    job_id: str,
    agent: str,
    action: str,
    result: dict,
    duration_ms: int
):
    await db.execute(
        insert(OperationLog).values(
            job_id=job_id,
            subgraph_id=None,  # Agent 级别操作
            agent=agent,
            action=action,
            input_data={"job_id": job_id},
            output_data=result,
            status=result["status"],
            duration_ms=duration_ms,
            error_message=result.get("message") if result["status"] == "error" else None,
            created_at=datetime.utcnow()
        )
    )
    await db.commit()
```

### 5.3 编排器更新 jobs 表

| 阶段 | status | current_stage | progress | 其他字段 |
|------|--------|---------------|----------|---------|
| 开始 | processing | cad_parsing | 0 | - |
| CAD完成 | processing | cad_completed | 30 | total_subgraphs |
| 决策完成 | processing | decision_completed | 60 | - |
| 定价完成 | processing | pricing_completed | 80 | total_cost, currency |
| 全部完成 | completed | completed | 100 | completed_at |
| 失败 | failed | (当前阶段) | (当前进度) | error_message |

---

## 六、标准错误码

| 错误码 | 说明 | 可重试 |
|--------|------|--------|
| `FILE_NOT_FOUND` | 文件不存在 | ❌ |
| `FILE_PARSE_ERROR` | 文件解析失败 | ❌ |
| `MINIO_ERROR` | MinIO 读取失败 | ✅ |
| `SERVICE_TIMEOUT` | 服务超时 | ✅ |
| `SERVICE_UNAVAILABLE` | 服务不可用 | ✅ |
| `RULE_NOT_FOUND` | 未找到匹配规则 | ❌ |
| `SNAPSHOT_NOT_FOUND` | 快照不存在 | ❌ |
| `DATABASE_ERROR` | 数据库错误 | ✅ |
| `INTERNAL_ERROR` | 内部错误 | ✅ |

---

## 七、数据流总结

```
【前端上传】
  ↓
【API Gateway】
  ├─ 保存文件到 MinIO
  ├─ INSERT jobs (status: pending)
  ├─ INSERT job_price_snapshots (复制价格表)
  ├─ INSERT job_process_snapshots (复制工艺表)
  └─ 发送 MQ: {"job_id": "xxx"}
  ↓
【编排器消费 MQ】
  ├─ UPDATE jobs: status=processing, progress=0
  │
  ├─ 调用 CADAgent.process({"job_id": "xxx"})
  │   ├─ INSERT subgraphs
  │   ├─ INSERT features
  │   └─ 返回: {"status": "ok", "subgraph_count": 5}
  │
  ├─ UPDATE jobs: progress=30, total_subgraphs=5
  ├─ INSERT operation_logs (CADAgent)
  │
  ├─ 调用 DecisionAgent.process({"job_id": "xxx"})
  │   ├─ UPDATE subgraphs (工艺字段)
  │   └─ 返回: {"status": "ok", "decision_count": 5}
  │
  ├─ UPDATE jobs: progress=60
  ├─ INSERT operation_logs (DecisionAgent)
  │
  ├─ 调用 PricingAgent.process({"job_id": "xxx"})
  │   ├─ UPDATE subgraphs (成本字段)
  │   └─ 返回: {"status": "ok", "total_cost": 2752.50}
  │
  ├─ UPDATE jobs: progress=100, status=completed, total_cost=2752.50
  └─ INSERT operation_logs (PricingAgent)
```

---

## 八、幂等性保证

### 8.1 CADAgent 幂等性
- 使用 `subgraph_id` 作为主键
- 重复调用时，使用 `INSERT ... ON CONFLICT DO UPDATE`

### 8.2 DecisionAgent 幂等性
- 使用 `subgraph_id` 作为 WHERE 条件
- UPDATE 操作天然幂等

### 8.3 PricingAgent 幂等性
- 使用 `subgraph_id` 作为 WHERE 条件
- UPDATE 操作天然幂等

---

**文档结束**
