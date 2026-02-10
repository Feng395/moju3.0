-- 检查实际数据库表结构的SQL脚本
-- 使用方法: psql -h localhost -U root -d mold_cost_db -f check_table_structure.sql

\echo '========================================='
\echo '检查 price_items 表结构'
\echo '========================================='
\d price_items

\echo ''
\echo '========================================='
\echo '检查 job_price_snapshots 表结构'
\echo '========================================='
\d job_price_snapshots

\echo ''
\echo '========================================='
\echo '检查 process_rules 表结构'
\echo '========================================='
\d process_rules

\echo ''
\echo '========================================='
\echo '检查 job_process_snapshots 表结构'
\echo '========================================='
\d job_process_snapshots

\echo ''
\echo '========================================='
\echo '查询 price_items 表的列名'
\echo '========================================='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'price_items'
ORDER BY ordinal_position;

\echo ''
\echo '========================================='
\echo '查询 job_price_snapshots 表的列名'
\echo '========================================='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'job_price_snapshots'
ORDER BY ordinal_position;

\echo ''
\echo '========================================='
\echo '查询 process_rules 表的列名'
\echo '========================================='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'process_rules'
ORDER BY ordinal_position;

\echo ''
\echo '========================================='
\echo '查询 job_process_snapshots 表的列名'
\echo '========================================='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'job_process_snapshots'
ORDER BY ordinal_position;
