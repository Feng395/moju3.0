# 测试脚本目录

本目录存放所有测试、验证和调试脚本。

## 目录结构

```
tests/
├── infrastructure/     # 基础设施相关的测试脚本
│   ├── migrations/    # 数据库迁移脚本（历史版本升级用）
│   ├── check_*.py     # 检查脚本（检查数据一致性、配置等）
│   ├── test_*.py      # 测试脚本（测试功能逻辑）
│   ├── verify_*.py    # 验证脚本（验证数据库字段、迁移结果等）
│   ├── list_jobs.py   # 列出所有任务
│   └── get_subgraph_ids.py  # 获取任务的子图ID
```

## 使用说明

### 数据库迁移脚本 (migrations/)
历史数据库迁移脚本，用于升级旧版本数据库。新部署无需使用。
详见 `migrations/README.md`

### 检查脚本 (check_*.py)
用于检查系统状态、数据一致性等：
- `check_both_jobs.py` - 检查两个任务的总成本
- `check_job_total_cost.py` - 检查任务总成本和子图成本的一致性
- `check_nc_config.py` - 检查 NC Agent 配置

### 测试脚本 (test_*.py)
用于测试功能逻辑：
- `test_nc_time_parsing.py` - 测试 NC 时间解析逻辑
- `test_price_calculation.py` - 测试价格计算流程

### 验证脚本 (verify_*.py)
用于验证数据库迁移结果：
- `verify_column.py` - 验证数据库列是否存在
- `verify_nc_time_cost.py` - 验证 nc_time_cost 字段

### 工具脚本
- `list_jobs.py` - 列出数据库中的所有任务
- `get_subgraph_ids.py` - 获取指定任务的所有子图ID

## 运行方式

所有脚本都可以直接运行：

```bash
# 列出所有任务
python tests/infrastructure/list_jobs.py

# 获取任务的子图ID
python tests/infrastructure/get_subgraph_ids.py <job_id>

# 检查任务总成本
python tests/infrastructure/check_job_total_cost.py <job_id>

# 测试 NC 时间解析
python tests/infrastructure/test_nc_time_parsing.py
```

## 注意事项

1. 这些脚本仅用于开发、测试和调试，不应在生产环境中使用
2. 运行前请确保已配置好数据库连接（.env 文件）
3. 某些脚本可能会修改数据库数据，请谨慎使用
