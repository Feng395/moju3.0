-- 创建自动同步触发器
-- 当 subgraphs 表的 total_cost 更新时，自动更新 jobs 表

-- 1. 创建触发器函数
CREATE OR REPLACE FUNCTION sync_job_total_cost()
RETURNS TRIGGER AS $$
DECLARE
    v_job_id UUID;
    v_total_cost DECIMAL(12,2);
BEGIN
    -- 获取 job_id（INSERT/UPDATE 使用 NEW，DELETE 使用 OLD）
    IF TG_OP = 'DELETE' THEN
        v_job_id := OLD.job_id;
    ELSE
        v_job_id := NEW.job_id;
    END IF;
    
    -- 计算该任务的总成本
    SELECT COALESCE(SUM(total_cost), 0)
    INTO v_total_cost
    FROM subgraphs
    WHERE job_id = v_job_id;
    
    -- 更新 jobs 表
    UPDATE jobs
    SET 
        total_cost = v_total_cost,
        updated_at = NOW()
    WHERE job_id = v_job_id;
    
    RETURN NULL; -- AFTER 触发器返回值被忽略
END;
$$ LANGUAGE plpgsql;

-- 2. 删除旧触发器（如果存在）
DROP TRIGGER IF EXISTS trigger_sync_job_total_cost_insert ON subgraphs;
DROP TRIGGER IF EXISTS trigger_sync_job_total_cost_update ON subgraphs;
DROP TRIGGER IF EXISTS trigger_sync_job_total_cost_delete ON subgraphs;

-- 3. 创建触发器（INSERT）
CREATE TRIGGER trigger_sync_job_total_cost_insert
AFTER INSERT ON subgraphs
FOR EACH ROW
EXECUTE FUNCTION sync_job_total_cost();

-- 4. 创建触发器（UPDATE）- 仅当 total_cost 变化时触发
CREATE TRIGGER trigger_sync_job_total_cost_update
AFTER UPDATE OF total_cost ON subgraphs
FOR EACH ROW
WHEN (OLD.total_cost IS DISTINCT FROM NEW.total_cost)
EXECUTE FUNCTION sync_job_total_cost();

-- 5. 创建触发器（DELETE）
CREATE TRIGGER trigger_sync_job_total_cost_delete
AFTER DELETE ON subgraphs
FOR EACH ROW
EXECUTE FUNCTION sync_job_total_cost();

-- 添加注释
COMMENT ON FUNCTION sync_job_total_cost() IS '自动同步 jobs.total_cost 的触发器函数';

-- 6. 立即同步所有现有数据
UPDATE jobs j
SET 
    total_cost = COALESCE(s.total_cost, 0),
    updated_at = NOW()
FROM (
    SELECT 
        job_id,
        SUM(total_cost) as total_cost
    FROM subgraphs
    GROUP BY job_id
) s
WHERE j.job_id = s.job_id
  AND COALESCE(j.total_cost, 0) != COALESCE(s.total_cost, 0);

-- 显示同步结果
DO $$
DECLARE
    v_updated_count INTEGER;
BEGIN
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE '已同步 % 个任务的 total_cost', v_updated_count;
END $$;
