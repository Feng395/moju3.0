# 日志快速参考卡片

## 🔍 常用日志搜索命令

### 按任务ID搜索

```bash
# 查看特定任务的所有日志
grep "job_id=J20260228001" mold_cost_/logs/app.log

# 查看任务的错误日志
grep "job_id=J20260228001" mold_cost_/logs/app.log | grep "error\|失败"

# 查看任务的性能日志
grep "job_id=J20260228001" mold_cost_/logs/app.log | grep "duration"
```

### 按模块搜索

```bash
# CAD拆图日志
grep "CADAgent\|cad_chaitu" mold_cost_/logs/app.log

# 特征识别日志
grep "feature_recognition\|特征识别" mold_cost_/logs/app.log

# NC时间计算日志
grep "NCTimeAgent\|NC时间" mold_cost_/logs/app.log

# 价格计算日志
grep "PricingAgent\|价格计算" mold_cost_/logs/app.log

# 编排器日志
grep "OrchestratorAgent\|编排" mold_cost_/logs/app.log
```

### 按操作类型搜索

```bash
# 查看所有失败的操作
grep "失败\|failed\|error" mold_cost_/logs/app.log

# 查看所有成功的操作
grep "成功\|success\|完成" mold_cost_/logs/app.log

# 查看并发处理
grep "并发\|concurrent\|batch" mold_cost_/logs/app.log

# 查看数据库操作
grep "数据库\|database\|写入\|更新" mold_cost_/logs/app.log
```

### 按性能指标搜索

```bash
# 查找耗时超过5秒的操作
grep "duration=[5-9]\|duration=[0-9][0-9]" mold_cost_/logs/app.log

# 查找处理数量超过100的批次
grep "count=[1-9][0-9][0-9]" mold_cost_/logs/app.log

# 查看进度信息
grep "progress=\|进度" mold_cost_/logs/app.log
```

## 📊 关键日志模式

### 任务流程追踪

```
1. 任务开始
   "开始执行 start 阶段, job_id={job_id}"

2. CAD拆图
   "开始拆图: job_id={job_id}"
   "成功拆分 {count} 个子图"

3. 特征识别
   "开始特征识别, job_id={job_id}"
   "特征识别完成: 成功={success}, 失败={failed}"

4. NC时间计算
   "开始NC时间计算, job_id={job_id}"
   "NC数据写入完成: subgraphs={count}"

5. 价格计算
   "开始价格计算, job_id={job_id}"
   "价格计算全部完成: 总耗时={duration}s"

6. 任务完成
   "任务完成: job_id={job_id}, status={status}"
```

### 错误定位模式

```
1. 查找错误发生的模块
   grep "error" app.log | grep -o "[A-Z][a-zA-Z]*Agent"

2. 查找错误的详细信息
   grep "error.*job_id=xxx" app.log

3. 查找错误的堆栈信息
   grep -A 10 "error.*job_id=xxx" app.log

4. 查找相同类型的错误
   grep "error_code=CHAITU_FAILED" app.log
```

### 性能分析模式

```
1. 统计各模块的平均耗时
   grep "CADAgent.*duration" app.log | awk '{print $NF}' | sort -n

2. 查找最慢的10个操作
   grep "duration" app.log | sort -t= -k2 -n | tail -10

3. 统计并发批次的处理情况
   grep "批次完成" app.log | grep -o "成功=[0-9]*"

4. 查看内存使用情况
   grep "memory\|内存" app.log
```

## 🎯 常见问题排查

### 问题1：任务卡住不动

```bash
# 1. 查看任务当前状态
grep "job_id=xxx" app.log | tail -20

# 2. 查看是否有错误
grep "job_id=xxx" app.log | grep "error"

# 3. 查看最后一次进度更新
grep "job_id=xxx.*progress" app.log | tail -1

# 4. 查看Worker是否正常
grep "Worker" app.log | tail -20
```

### 问题2：价格计算错误

```bash
# 1. 查看价格计算的开始
grep "job_id=xxx.*开始价格计算" app.log

# 2. 查看MCP调用是否成功
grep "job_id=xxx.*MCP" app.log | grep "error"

# 3. 查看具体哪个子图失败
grep "job_id=xxx.*计算失败" app.log

# 4. 查看数据库写入是否成功
grep "job_id=xxx.*数据库写入" app.log
```

### 问题3：特征识别失败

```bash
# 1. 查看特征识别的开始
grep "job_id=xxx.*特征识别" app.log

# 2. 查看并发处理情况
grep "job_id=xxx.*并发处理" app.log

# 3. 查看失败的子图
grep "job_id=xxx.*识别失败" app.log

# 4. 查看DXF文件下载是否成功
grep "job_id=xxx.*下载DXF" app.log
```

### 问题4：报表导出慢

```bash
# 1. 查看导出模式
grep "job_id=xxx.*导出模式" app.log

# 2. 查看数据查询耗时
grep "job_id=xxx.*查询报表数据" app.log

# 3. 查看Excel生成耗时
grep "job_id=xxx.*Excel生成" app.log

# 4. 查看MinIO上传耗时
grep "job_id=xxx.*上传.*MinIO" app.log
```

## 📈 性能基线参考

| 操作 | 正常耗时 | 警告阈值 | 说明 |
|------|---------|---------|------|
| CAD拆图 | 5-30s | >60s | 取决于DWG文件大小 |
| 特征识别（单个） | 0.5-2s | >5s | 取决于子图复杂度 |
| NC时间计算 | 10-60s | >120s | 取决于子图数量 |
| 价格计算（单个） | 0.1-0.5s | >2s | 取决于计算项目 |
| 报表导出（同步） | 5-30s | >60s | 子图数<500 |
| 报表导出（异步） | 30-300s | >600s | 子图数≥500 |

## 🔔 告警规则建议

### 错误告警

```bash
# 任务失败率超过10%
# 连续3次相同错误
# 数据库连接失败
# MCP服务不可用
```

### 性能告警

```bash
# 单个操作耗时超过阈值的2倍
# 队列积压超过100个任务
# 内存使用超过80%
# CPU使用超过90%
```

### 业务告警

```bash
# 任务等待时间超过5分钟
# 特征识别失败率超过5%
# 价格计算失败率超过5%
# 报表导出失败
```

## 💡 日志最佳实践

### 1. 日志查看

- 使用 `tail -f` 实时查看日志
- 使用 `grep` 过滤关键信息
- 使用 `awk` 提取特定字段
- 使用 `sort` 排序分析

### 2. 日志分析

- 定期分析错误日志
- 统计各模块的性能指标
- 识别常见问题模式
- 建立性能基线

### 3. 日志维护

- 定期清理过期日志
- 归档重要任务日志
- 监控日志文件大小
- 设置日志轮转策略

### 4. 日志优化

- 根据实际情况调整日志级别
- 添加更多业务相关日志
- 优化日志格式便于解析
- 使用结构化日志

## 📞 快速联系

遇到问题时：
1. 先查看日志，定位问题
2. 记录关键日志信息
3. 联系技术支持，提供日志

---

**版本**: 1.0.0
**更新**: 2026-02-28
