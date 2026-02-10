-- 报表导出性能优化 - 数据库索引
-- 用于加速报表数据查询

-- 1. Subgraph表索引
-- 加速按job_id查询子图
CREATE INDEX IF NOT EXISTS idx_subgraph_job_id 
ON subgraphs(job_id);

-- 加速按job_id排序查询
CREATE INDEX IF NOT EXISTS idx_subgraph_job_id_order 
ON subgraphs(job_id, subgraph_id);

-- 2. Feature表索引
-- 加速按job_id和subgraph_id查询特征
CREATE INDEX IF NOT EXISTS idx_feature_job_subgraph 
ON features(job_id, subgraph_id);

-- 加速按版本查询最新特征
CREATE INDEX IF NOT EXISTS idx_feature_subgraph_version 
ON features(subgraph_id, version DESC);

-- 组合索引，优化报表查询
CREATE INDEX IF NOT EXISTS idx_feature_job_subgraph_version 
ON features(job_id, subgraph_id, version DESC);

-- 3. Job表索引（如果还没有）
-- 加速按job_id查询
CREATE INDEX IF NOT EXISTS idx_job_id 
ON jobs(job_id);

-- 加速按状态和创建时间查询
CREATE INDEX IF NOT EXISTS idx_job_status_created 
ON jobs(status, created_at DESC);

-- 4. 查看索引创建结果
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('jobs', 'subgraphs', 'features')
ORDER BY tablename, indexname;

-- 5. 分析表统计信息（优化查询计划）
ANALYZE jobs;
ANALYZE subgraphs;
ANALYZE features;

-- 6. 查看表大小和索引大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE tablename IN ('jobs', 'subgraphs', 'features')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 7. 查看索引使用情况（运行一段时间后执行）
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename IN ('jobs', 'subgraphs', 'features')
ORDER BY idx_scan DESC;

-- 8. 性能测试查询
-- 测试报表查询性能
EXPLAIN ANALYZE
SELECT 
    j.job_id,
    j.dwg_file_name,
    s.subgraph_id,
    s.part_name,
    s.weight_kg,
    s.total_cost,
    f.material,
    f.length_mm,
    f.width_mm,
    f.thickness_mm
FROM jobs j
JOIN subgraphs s ON j.job_id = s.job_id
LEFT JOIN LATERAL (
    SELECT *
    FROM features f2
    WHERE f2.subgraph_id = s.subgraph_id
    ORDER BY f2.version DESC
    LIMIT 1
) f ON true
WHERE j.job_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY s.subgraph_id;

-- 注意事项：
-- 1. 索引会占用额外的存储空间
-- 2. 索引会略微降低INSERT/UPDATE性能
-- 3. 对于报表导出这种读多写少的场景，索引收益远大于成本
-- 4. 建议在非高峰期执行索引创建
-- 5. 创建索引后运行ANALYZE更新统计信息
