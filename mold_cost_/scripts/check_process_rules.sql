-- 检查 process_rules 表的工艺代码
-- 用于诊断工艺代码不匹配的问题

-- 1. 查看所有线切割工艺规则
SELECT 
    id,
    version_id,
    feature_type,
    name,
    description,
    conditions AS process_code,  -- 这个字段存储工艺代码
    priority,
    is_active
FROM process_rules
WHERE feature_type = 'wire'
  AND is_active = true
ORDER BY priority DESC;

-- 2. 检查是否有 fast_cut 工艺代码
SELECT 
    id,
    name,
    description,
    conditions AS process_code
FROM process_rules
WHERE conditions LIKE '%fast_cut%'
   OR conditions = 'fast_cut';

-- 3. 检查是否有 fast_and_one 工艺代码
SELECT 
    id,
    name,
    description,
    conditions AS process_code
FROM process_rules
WHERE conditions LIKE '%fast_and_one%'
   OR conditions = 'fast_and_one';

-- 4. 如果需要修改工艺代码（将 fast_cut 改为 fast_and_one）
-- 取消注释下面的 UPDATE 语句：

-- UPDATE process_rules
-- SET conditions = 'fast_and_one'
-- WHERE conditions = 'fast_cut'
--   AND feature_type = 'wire';

-- 5. 验证修改结果
-- SELECT 
--     id,
--     name,
--     conditions AS process_code
-- FROM process_rules
-- WHERE feature_type = 'wire'
--   AND is_active = true;
