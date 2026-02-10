-- 将 NC 时间字段从小时转换为分钟
-- 只修改：nc_roughing_time, nc_milling_time, drilling_time
-- 执行前请备份数据库！

-- ============================================================================
-- 重要提示：
-- 1. 此脚本会将现有数据乘以 60（小时转分钟）
-- 2. 如果数据已经是分钟，请勿执行此脚本！
-- 3. 执行前请先备份数据库
-- ============================================================================

-- 1. 查看当前数据（执行前）
SELECT 
  '执行前数据示例' as stage,
  subgraph_id,
  nc_roughing_time,
  nc_milling_time,
  drilling_time
FROM subgraphs
WHERE nc_roughing_time IS NOT NULL OR nc_milling_time IS NOT NULL OR drilling_time IS NOT NULL
ORDER BY updated_at DESC
LIMIT 5;

-- 2. 更新 subgraphs 表的 NC 时间字段（小时 -> 分钟）
-- 将现有数据乘以 60 转换为分钟
UPDATE subgraphs
SET 
  nc_roughing_time = CASE WHEN nc_roughing_time IS NOT NULL THEN nc_roughing_time * 60 ELSE NULL END,
  nc_milling_time = CASE WHEN nc_milling_time IS NOT NULL THEN nc_milling_time * 60 ELSE NULL END,
  drilling_time = CASE WHEN drilling_time IS NOT NULL THEN drilling_time * 60 ELSE NULL END,
  updated_at = NOW()
WHERE 
  nc_roughing_time IS NOT NULL 
  OR nc_milling_time IS NOT NULL 
  OR drilling_time IS NOT NULL;

-- 3. 添加注释说明单位
COMMENT ON COLUMN subgraphs.nc_roughing_time IS '开粗时间（分钟）';
COMMENT ON COLUMN subgraphs.nc_milling_time IS '精铣时间（分钟）';
COMMENT ON COLUMN subgraphs.drilling_time IS '钻孔时间（分钟）';

-- 4. 验证转换结果
SELECT 
  '转换统计' as info,
  COUNT(*) as total_records,
  COUNT(CASE WHEN nc_roughing_time IS NOT NULL THEN 1 END) as nc_roughing_count,
  COUNT(CASE WHEN nc_milling_time IS NOT NULL THEN 1 END) as nc_milling_count,
  COUNT(CASE WHEN drilling_time IS NOT NULL THEN 1 END) as drilling_count,
  ROUND(AVG(nc_roughing_time), 2) as avg_nc_roughing_minutes,
  ROUND(AVG(nc_milling_time), 2) as avg_nc_milling_minutes,
  ROUND(AVG(drilling_time), 2) as avg_drilling_minutes,
  ROUND(MAX(nc_roughing_time), 2) as max_nc_roughing_minutes,
  ROUND(MAX(nc_milling_time), 2) as max_nc_milling_minutes,
  ROUND(MAX(drilling_time), 2) as max_drilling_minutes
FROM subgraphs;

-- 5. 查看转换后的示例数据（应该是原来的 60 倍）
SELECT 
  '执行后数据示例' as stage,
  subgraph_id,
  nc_roughing_time as nc_roughing_minutes,
  nc_milling_time as nc_milling_minutes,
  drilling_time as drilling_minutes,
  ROUND(nc_roughing_time / 60.0, 2) as nc_roughing_hours,
  ROUND(nc_milling_time / 60.0, 2) as nc_milling_hours,
  ROUND(drilling_time / 60.0, 2) as drilling_hours
FROM subgraphs
WHERE nc_roughing_time IS NOT NULL OR nc_milling_time IS NOT NULL OR drilling_time IS NOT NULL
ORDER BY updated_at DESC
LIMIT 5;

-- 6. 检查是否有异常大的值（可能是重复执行了转换）
SELECT 
  '异常检查' as info,
  COUNT(*) as records_with_large_values
FROM subgraphs
WHERE 
  nc_roughing_time > 10000  -- 超过 10000 分钟（约 166 小时）可能异常
  OR nc_milling_time > 10000
  OR drilling_time > 10000;
