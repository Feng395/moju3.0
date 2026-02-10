-- 添加 wire_process 字段到 subgraphs 表
-- 用于存储线切割工艺代码（替代 process_snapshots 表）

-- 1. 添加 wire_process 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'subgraphs' 
        AND column_name = 'wire_process'
    ) THEN
        ALTER TABLE public.subgraphs 
        ADD COLUMN wire_process VARCHAR(255);
        
        RAISE NOTICE '✅ 已添加 wire_process 字段';
    ELSE
        RAISE NOTICE '⚠️  wire_process 字段已存在';
    END IF;
END $$;

-- 2. 添加注释
COMMENT ON COLUMN public.subgraphs.wire_process IS '线切割工艺代码（如 slow_and_one, fast_and_one 等）';

-- 3. 查看结果
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'subgraphs'
  AND column_name IN ('wire_process', 'wire_process_note')
ORDER BY column_name;

-- 4. 显示统计信息
SELECT 
    COUNT(*) as total_records,
    COUNT(wire_process) as has_wire_process,
    COUNT(wire_process_note) as has_wire_process_note
FROM public.subgraphs;
