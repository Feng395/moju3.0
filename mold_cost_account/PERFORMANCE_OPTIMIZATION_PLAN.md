# /chat-sessions/delete-by-job 接口性能优化方案

## 问题诊断

接口响应时间：**3秒**

### 根本原因

1. **没有数据库连接池** ❌
   - 每次查询都创建新连接：`psycopg2.connect()`
   - 删除操作需要18次数据库查询 = 18次连接建立/关闭
   - 连接开销：每次约100-200ms

2. **没有使用事务批量执行** ❌
   - 18个独立的 DELETE 语句
   - 每个都是独立的数据库往返
   - 网络延迟累积

3. **查询次数过多** ❌
   - 权限检查：1次查询
   - 删除操作：17个表 = 17次查询
   - 总计：18次数据库往返

## 优化方案

### 方案1：添加数据库连接池（推荐）⭐

**效果：减少80%的连接开销**

```python
# app/services/database.py
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from config.config import get_config

config = get_config()

class DatabaseManager:
    def __init__(self):
        self.config = config.get_database_config()
        self.logger = logging.getLogger(__name__)
        
        # 创建连接池
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,      # 最小连接数
                maxconn=10,     # 最大连接数
                **self.config
            )
            self.logger.info("数据库连接池初始化成功")
        except Exception as e:
            self.logger.error(f"连接池初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """从连接池获取连接"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"数据库操作错误: {e}")
            raise
        finally:
            if conn:
                # 归还连接到池中，而不是关闭
                self.connection_pool.putconn(conn)
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """执行查询"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                
                if fetch_one:
                    result = cursor.fetchone()
                    conn.commit()
                    return dict(result) if result else None
                elif fetch_all:
                    results = cursor.fetchall()
                    conn.commit()
                    return [dict(row) for row in results]
                else:
                    conn.commit()
                    return cursor.rowcount
    
    def execute_batch(self, queries_with_params):
        """批量执行多个查询（在同一个连接中）"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                results = []
                for query, params in queries_with_params:
                    cursor.execute(query, params)
                    results.append(cursor.rowcount)
                conn.commit()
                return results
    
    def close_all_connections(self):
        """关闭所有连接（应用关闭时调用）"""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
            self.logger.info("数据库连接池已关闭")

db_manager = DatabaseManager()
```

**预期效果：**
- 响应时间从 3秒 → 0.5-1秒
- 减少连接开销：18次 × 150ms = 2.7秒 → 几乎为0

---

### 方案2：优化删除逻辑（配合方案1）

**使用单个连接执行所有删除操作**

```python
# app/services/chat_session_service.py

def delete_session_by_job_id(self, job_id: str, user_id: Optional[str] = None) -> tuple[bool, str]:
    """优化后的删除方法"""
    try:
        if not job_id or not job_id.strip():
            return False, "任务ID不能为空"
        
        # 检查权限
        session = self.get_session_by_job_id(job_id, user_id)
        if not session:
            return False, "会话不存在或无权访问"
        
        # 准备所有删除查询
        delete_queries = [
            # 1. 删除聊天消息
            ("DELETE FROM chat_messages WHERE session_id IN (SELECT session_id FROM chat_sessions WHERE job_id = %s)", (job_id,)),
            
            # 2. 删除引用subgraphs的子表
            ("DELETE FROM features WHERE job_id = %s", (job_id,)),
            ("DELETE FROM processing_cost_calculation_details WHERE job_id = %s", (job_id,)),
            
            # 3. 删除子图
            ("DELETE FROM subgraphs WHERE job_id = %s", (job_id,)),
            
            # 4-17. 其他表...
            ("DELETE FROM job_price_snapshots WHERE job_id = %s", (job_id,)),
            ("DELETE FROM job_process_snapshots WHERE job_id = %s", (job_id,)),
            ("DELETE FROM operation_logs WHERE job_id = %s", (job_id,)),
            ("DELETE FROM price_histories WHERE job_id = %s", (job_id,)),
            ("DELETE FROM recalculations WHERE job_id = %s", (job_id,)),
            ("DELETE FROM batch_recalculations WHERE job_id = %s", (job_id,)),
            ("DELETE FROM process_changes WHERE job_id = %s", (job_id,)),
            ("DELETE FROM nc_calculations WHERE job_id = %s", (job_id,)),
            ("DELETE FROM user_interactions WHERE job_id = %s", (job_id,)),
            ("DELETE FROM report_summary WHERE job_id = %s", (job_id,)),
            ("DELETE FROM reports WHERE job_id = %s", (job_id,)),
            ("DELETE FROM archives WHERE job_id = %s", (job_id,)),
            ("DELETE FROM audit_logs WHERE resource_type = 'job' AND resource_id = %s", (job_id,)),
            ("DELETE FROM jobs WHERE job_id = %s", (job_id,)),
            
            # 18. 最后删除会话
            ("DELETE FROM chat_sessions WHERE job_id = %s", (job_id,)),
        ]
        
        # 使用批量执行（单个连接）
        deleted_counts_list = self.db.execute_batch(delete_queries)
        
        # 构建统计信息
        table_names = [
            'chat_messages', 'features', 'processing_cost_calculation_details',
            'subgraphs', 'job_price_snapshots', 'job_process_snapshots',
            'operation_logs', 'price_histories', 'recalculations',
            'batch_recalculations', 'process_changes', 'nc_calculations',
            'user_interactions', 'report_summary', 'reports', 'archives',
            'audit_logs', 'jobs', 'chat_sessions'
        ]
        
        deleted_counts = dict(zip(table_names, deleted_counts_list))
        total_deleted = sum(deleted_counts.values())
        
        # 构建响应消息
        summary_parts = [f"{table}({count}条)" for table, count in deleted_counts.items() if count > 0]
        summary = f"会话删除成功，共删除 {total_deleted} 条记录: " + ", ".join(summary_parts)
        
        logger.info(f"已删除任务 {job_id} 的所有相关数据: {deleted_counts}")
        return True, summary
        
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return False, f"系统错误: {str(e)}"
```

**预期效果：**
- 18次数据库往返 → 2次（1次权限检查 + 1次批量删除）
- 响应时间：0.5-1秒 → 0.2-0.3秒

---

### 方案3：数据库级联删除（最优）⭐⭐

**在数据库层面配置外键级联删除**

```sql
-- 修改外键约束，添加 ON DELETE CASCADE
ALTER TABLE chat_messages 
DROP CONSTRAINT IF EXISTS fk_chat_messages_session,
ADD CONSTRAINT fk_chat_messages_session 
    FOREIGN KEY (session_id) 
    REFERENCES chat_sessions(session_id) 
    ON DELETE CASCADE;

ALTER TABLE features
DROP CONSTRAINT IF EXISTS fk_features_job,
ADD CONSTRAINT fk_features_job
    FOREIGN KEY (job_id)
    REFERENCES jobs(job_id)
    ON DELETE CASCADE;

-- ... 为所有相关表添加级联删除
```

**简化后的删除代码：**

```python
def delete_session_by_job_id(self, job_id: str, user_id: Optional[str] = None) -> tuple[bool, str]:
    """使用数据库级联删除"""
    try:
        # 检查权限
        session = self.get_session_by_job_id(job_id, user_id)
        if not session:
            return False, "会话不存在或无权访问"
        
        # 只需删除主表，数据库自动级联删除
        query = "DELETE FROM jobs WHERE job_id = %s"
        deleted = self.db.execute_query(query, (job_id,))
        
        if deleted > 0:
            return True, f"会话删除成功，已级联删除所有相关数据"
        return False, "删除失败"
        
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return False, f"系统错误: {str(e)}"
```

**预期效果：**
- 18次查询 → 2次（1次权限检查 + 1次删除）
- 数据库自动处理级联，性能最优
- 响应时间：< 0.2秒

---

## 实施建议

### 立即实施（必须）
1. ✅ **添加数据库连接池**（方案1）
   - 影响：全局性能提升
   - 工作量：30分钟
   - 风险：低

### 短期优化（推荐）
2. ✅ **批量执行删除**（方案2）
   - 影响：删除接口性能提升
   - 工作量：1小时
   - 风险：低

### 长期优化（可选）
3. ⚠️ **数据库级联删除**（方案3）
   - 影响：最佳性能，代码最简洁
   - 工作量：2-3小时（需要仔细设计外键）
   - 风险：中（需要充分测试）

---

## 性能对比

| 方案 | 响应时间 | 数据库往返 | 实施难度 |
|------|---------|-----------|---------|
| 当前 | 3秒 | 18次 | - |
| 方案1（连接池） | 0.5-1秒 | 18次 | 简单 |
| 方案1+2（批量） | 0.2-0.3秒 | 2次 | 中等 |
| 方案1+3（级联） | < 0.2秒 | 2次 | 复杂 |

---

## 其他优化建议

### 1. 添加数据库索引
```sql
-- 确保这些字段有索引
CREATE INDEX IF NOT EXISTS idx_chat_sessions_job_id ON chat_sessions(job_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
-- ... 为所有外键字段添加索引
```

### 2. 异步删除（可选）
对于大量数据的删除，可以考虑：
- 先标记为"删除中"状态
- 后台异步执行删除
- 立即返回响应

### 3. 监控和日志
```python
import time

def delete_session_by_job_id(self, job_id: str, user_id: Optional[str] = None):
    start_time = time.time()
    
    # ... 删除逻辑 ...
    
    elapsed = time.time() - start_time
    logger.info(f"删除操作耗时: {elapsed:.2f}秒")
    
    if elapsed > 1.0:
        logger.warning(f"删除操作较慢: {elapsed:.2f}秒, job_id={job_id}")
```

---

## 总结

**立即实施方案1（连接池）可以将响应时间从3秒降低到0.5-1秒，这是最简单且影响最大的优化。**
