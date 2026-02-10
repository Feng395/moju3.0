# 数据库事务提交问题修复总结

## 问题描述

创建价格项（price_items）或工艺规则（process_rules）时，API返回成功响应，但数据实际上没有保存到数据库中。

### 具体表现
- 调用创建接口返回201状态码和成功消息
- 返回的数据包含所有字段（包括created_at等）
- 但通过API或直接查询数据库都找不到刚创建的数据

## 根本原因

在 `app/services/database.py` 的 `execute_query` 方法中：

```python
def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
    with self.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                # ❌ 缺少 conn.commit()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                # ❌ 缺少 conn.commit()
                return [dict(row) for row in results]
            else:
                conn.commit()  # ✓ 只有这个分支有提交
                return cursor.rowcount
```

### 问题分析

1. 创建价格项和工艺规则的SQL使用了 `RETURNING *` 子句
2. 为了获取返回的数据，代码设置了 `fetch_one=True`
3. 在 `fetch_one` 分支中执行了 `fetchone()` 但没有 `commit()`
4. 虽然返回了数据，但事务没有提交，数据库回滚了更改

## 修复方案

在 `fetch_one` 和 `fetch_all` 分支中添加 `conn.commit()`：

```python
def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
    with self.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                conn.commit()  # ✓ 添加提交
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                conn.commit()  # ✓ 添加提交
                return [dict(row) for row in results]
            else:
                conn.commit()
                return cursor.rowcount
```

## 验证结果

### 修复前
```bash
# 创建P044
POST /api/price-items
响应: {"success": true, "message": "价格项创建成功"}

# 查询P044
GET /api/price-items/P044
响应: {"success": false, "message": "价格项不存在"}  # ❌ 找不到

# 数据库查询
SELECT * FROM price_items WHERE id = 'P044'
结果: 无数据  # ❌ 数据库中不存在
```

### 修复后
```bash
# 创建P044
POST /api/price-items
响应: {"success": true, "message": "价格项创建成功"}

# 查询P044
GET /api/price-items/P044
响应: {"success": true, "data": {...}}  # ✓ 查询成功

# 数据库查询
SELECT * FROM price_items WHERE id = 'P044'
结果: 返回完整数据  # ✓ 数据已保存
```

## 影响范围

此问题影响所有使用 `RETURNING` 子句的INSERT/UPDATE/DELETE操作：

1. **价格项API** (`app/api/price_items.py`)
   - 创建价格项
   - 更新价格项
   - 删除价格项（如果使用RETURNING）

2. **工艺规则API** (`app/api/process_rules.py`)
   - 创建工艺规则
   - 更新工艺规则
   - 删除工艺规则（如果使用RETURNING）

3. **其他可能的API**
   - 任何使用 `fetch_one=True` 或 `fetch_all=True` 的写操作

## 测试验证

运行以下测试脚本验证修复：

```bash
# 综合测试
python test_fix_verification.py

# 价格项查询测试
python test_price_query.py

# 创建P044测试
python create_p044.py
```

所有测试均通过，确认问题已完全修复。

## 修复时间

2026-01-16

## 相关文件

- `app/services/database.py` - 修复的核心文件
- `test_fix_verification.py` - 验证测试脚本
- `test_price_query.py` - 价格项查询测试
- `create_p044.py` - P044创建测试
