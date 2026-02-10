# 数据库迁移脚本

本目录存放历史数据库迁移脚本，用于升级已有的数据库。

**注意：** 对于新部署的系统，这些改动已经包含在 `infrastructure/init-db.sql` 中，无需执行这些迁移脚本。

## 迁移脚本列表

### add-small-grinding-count.sql
- **用途：** 添加 `small_grinding_count` 字段到 `subgraphs` 表
- **执行时机：** 如果数据库是在该字段添加之前创建的
- **状态：** 已合并到 init-db.sql

### add_nc_time_cost_column.sql
- **用途：** 添加 `nc_time_cost` 字段（JSONB 类型）到 `features` 表
- **执行时机：** 如果数据库是在该字段添加之前创建的
- **状态：** 已合并到 init-db.sql

## 使用方法

如果你的数据库是旧版本，需要执行迁移：

```bash
# 连接到数据库
psql -U postgres -d mold_cost

# 执行迁移脚本
\i tests/infrastructure/migrations/add-small-grinding-count.sql
\i tests/infrastructure/migrations/add_nc_time_cost_column.sql
```

或者使用命令行：

```bash
psql -U postgres -d mold_cost -f tests/infrastructure/migrations/add-small-grinding-count.sql
psql -U postgres -d mold_cost -f tests/infrastructure/migrations/add_nc_time_cost_column.sql
```

## 新部署

对于新部署的系统，直接使用 `infrastructure/init-db.sql` 初始化数据库即可，无需执行这些迁移脚本。
