-- 创建任务成本视图
-- 自动从 subgraphs 表汇总计算，确保数据始终一致

-- 删除旧视图（如果存在）
DROP VIEW IF EXISTS v_job_cost_summary CASCADE;

-- 创建新视图
CREATE OR REPLACE VIEW v_job_cost_summary AS
SELECT 
    j.job_id,
    j.user_id,
    j.dwg_file_name,
    j.prt_file_name,
    j.status,
    j.current_stage,
    j.progress,
    j.created_at,
    j.updated_at,
    j.completed_at,
    j.error_message,
    j.metadata,
    
    -- 子图统计
    COALESCE(s.total_subgraphs, 0) as total_subgraphs,
    
    -- 实时计算的总成本（从 subgraphs 汇总）
    COALESCE(s.total_cost, 0) as total_cost,
    COALESCE(s.material_cost, 0) as material_cost,
    COALESCE(s.heat_treatment_cost, 0) as heat_treatment_cost,
    COALESCE(s.processing_cost_total, 0) as processing_cost_total,
    
    -- 各工艺成本明细
    COALESCE(s.nc_roughing_cost, 0) as nc_roughing_cost,
    COALESCE(s.nc_milling_cost, 0) as nc_milling_cost,
    COALESCE(s.drilling_cost, 0) as drilling_cost,
    COALESCE(s.milling_machine_cost, 0) as milling_machine_cost,
    COALESCE(s.large_grinding_cost, 0) as large_grinding_cost,
    COALESCE(s.small_grinding_cost, 0) as small_grinding_cost,
    COALESCE(s.slow_wire_cost, 0) as slow_wire_cost,
    COALESCE(s.slow_wire_side_cost, 0) as slow_wire_side_cost,
    COALESCE(s.mid_wire_cost, 0) as mid_wire_cost,
    COALESCE(s.fast_wire_cost, 0) as fast_wire_cost,
    COALESCE(s.edm_cost, 0) as edm_cost,
    COALESCE(s.engraving_cost, 0) as engraving_cost,
    COALESCE(s.separate_item_cost, 0) as separate_item_cost,
    
    -- NC 总成本
    COALESCE(s.nc_roughing_cost, 0) + COALESCE(s.nc_milling_cost, 0) + COALESCE(s.drilling_cost, 0) as nc_cost,
    
    -- 磨床总成本
    COALESCE(s.large_grinding_cost, 0) + COALESCE(s.small_grinding_cost, 0) as grinding_cost,
    
    -- 线割总成本
    COALESCE(s.slow_wire_cost, 0) + COALESCE(s.slow_wire_side_cost, 0) + 
    COALESCE(s.mid_wire_cost, 0) + COALESCE(s.fast_wire_cost, 0) as wire_cost

FROM jobs j
LEFT JOIN (
    SELECT 
        job_id,
        COUNT(*) as total_subgraphs,
        SUM(total_cost) as total_cost,
        SUM(material_cost) as material_cost,
        SUM(heat_treatment_cost) as heat_treatment_cost,
        SUM(processing_cost_total) as processing_cost_total,
        SUM(nc_roughing_cost) as nc_roughing_cost,
        SUM(nc_milling_cost) as nc_milling_cost,
        SUM(drilling_cost) as drilling_cost,
        SUM(milling_machine_cost) as milling_machine_cost,
        SUM(large_grinding_cost) as large_grinding_cost,
        SUM(small_grinding_cost) as small_grinding_cost,
        SUM(slow_wire_cost) as slow_wire_cost,
        SUM(slow_wire_side_cost) as slow_wire_side_cost,
        SUM(mid_wire_cost) as mid_wire_cost,
        SUM(fast_wire_cost) as fast_wire_cost,
        SUM(edm_cost) as edm_cost,
        SUM(engraving_cost) as engraving_cost,
        SUM(separate_item_cost) as separate_item_cost
    FROM subgraphs
    GROUP BY job_id
) s ON j.job_id = s.job_id;

-- 添加注释
COMMENT ON VIEW v_job_cost_summary IS '任务成本汇总视图 - 实时从 subgraphs 表计算，确保数据一致性';

-- 授权
GRANT SELECT ON v_job_cost_summary TO PUBLIC;
