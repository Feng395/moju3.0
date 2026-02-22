CREATE TABLE "public"."subgraphs" (
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "part_name" varchar(100) COLLATE "pg_catalog"."default",
  "part_code" varchar(100) COLLATE "pg_catalog"."default",
  "subgraph_file_url" varchar(500) COLLATE "pg_catalog"."default",
  "weight_kg" numeric(10,3),
  "material_unit_price" numeric(10,2),
  "material_cost" numeric(12,2),
  "heat_treatment_unit_price" numeric(10,2),
  "heat_treatment_cost" numeric(12,2),
  "process_description" varchar(200) COLLATE "pg_catalog"."default",
  "nc_z_time" numeric(10,2),
  "nc_b_time" numeric(10,2),
  "nc_c_time" numeric(10,2),
  "nc_c_b_time" numeric(10,2),
  "large_grinding_time" numeric(10,2),
  "small_grinding_time" numeric(10,2),
  "edm_time" numeric(10,2),
  "engraving_time" numeric(10,2),
  "slow_wire_length" numeric(12,3),
  "slow_wire_side_length" numeric(12,3),
  "mid_wire_length" numeric(12,3),
  "fast_wire_length" numeric(12,3),
  "separate_item" varchar(200) COLLATE "pg_catalog"."default",
  "total_cost" numeric(12,2),
  "wire_process_note" text COLLATE "pg_catalog"."default",
  "nc_z_fee" numeric(12,2),
  "nc_b_fee" numeric(12,2),
  "nc_c_fee" numeric(12,2),
  "nc_c_b_fee" numeric(12,2),
  "large_grinding_cost" numeric(12,2),
  "small_grinding_cost" numeric(12,2),
  "slow_wire_cost" numeric(12,2),
  "slow_wire_side_cost" numeric(12,2),
  "mid_wire_cost" numeric(12,2),
  "fast_wire_cost" numeric(12,2),
  "edm_cost" numeric(12,2),
  "engraving_cost" numeric(12,2),
  "separate_item_cost" numeric(12,2),
  "processing_cost_total" numeric(12,2),
  "applied_snapshot_ids" text[] COLLATE "pg_catalog"."default",
  "rule_reason" text COLLATE "pg_catalog"."default",
  "override_by_user" bool DEFAULT false,
  "cost_calculation_method" varchar(20) COLLATE "pg_catalog"."default",
  "has_sheet_line" bool DEFAULT false,
  "sheet_area_mm2" numeric(12,3),
  "sheet_perimeter_mm" numeric(12,3),
  "sheet_line_data" jsonb,
  "has_single_nc_calc" bool DEFAULT false,
  "single_prt_file" varchar(500) COLLATE "pg_catalog"."default",
  "process_changed" bool DEFAULT false,
  "original_process" varchar(20) COLLATE "pg_catalog"."default",
  "prt_3d_file" varchar(500) COLLATE "pg_catalog"."default",
  "recalc_count" int4 DEFAULT 0,
  "last_recalc_at" timestamp(6),
  "last_recalc_by" varchar(50) COLLATE "pg_catalog"."default",
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'pending'::character varying,
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "updated_at" timestamp(6) NOT NULL DEFAULT now(),
  "metadata" jsonb,
  "wire_process" varchar(255) COLLATE "pg_catalog"."default",
  "small_grinding_count" int4,
  "nc_z_view_time" numeric(10,2),
  "nc_b_view_time" numeric(10,2),
  "nc_z_view_fee" numeric(10,2),
  "nc_b_view_fee" numeric(10,2),
  CONSTRAINT "subgraphs_pkey" PRIMARY KEY ("subgraph_id"),
  CONSTRAINT "subgraphs_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION
)
;

ALTER TABLE "public"."subgraphs" 
  OWNER TO "root";

CREATE INDEX "idx_subgraph_job_id" ON "public"."subgraphs" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

CREATE INDEX "idx_subgraph_job_id_order" ON "public"."subgraphs" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

CREATE INDEX "idx_subgraphs_job_id" ON "public"."subgraphs" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

CREATE INDEX "idx_subgraphs_job_subgraph" ON "public"."subgraphs" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

CREATE INDEX "idx_subgraphs_status" ON "public"."subgraphs" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

CREATE TRIGGER "trigger_sync_job_total_cost_delete" AFTER DELETE ON "public"."subgraphs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."sync_job_total_cost"();

CREATE TRIGGER "trigger_sync_job_total_cost_insert" AFTER INSERT ON "public"."subgraphs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."sync_job_total_cost"();

CREATE TRIGGER "trigger_sync_job_total_cost_update" AFTER UPDATE OF "total_cost" ON "public"."subgraphs"
FOR EACH ROW
WHEN ((old.total_cost IS DISTINCT FROM new.total_cost))
EXECUTE PROCEDURE "public"."sync_job_total_cost"();

CREATE TRIGGER "update_subgraphs_updated_at" BEFORE UPDATE ON "public"."subgraphs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

COMMENT ON COLUMN "public"."subgraphs"."subgraph_id" IS '子图唯一标识，如UP01、UP02';

COMMENT ON COLUMN "public"."subgraphs"."job_id" IS '所属任务ID';

COMMENT ON COLUMN "public"."subgraphs"."part_name" IS '零件名称（报表第2列）';

COMMENT ON COLUMN "public"."subgraphs"."part_code" IS '零件编号（报表第3列）';

COMMENT ON COLUMN "public"."subgraphs"."subgraph_file_url" IS '子图文件URL';

COMMENT ON COLUMN "public"."subgraphs"."weight_kg" IS '实际重量/kg（报表第9列）';

COMMENT ON COLUMN "public"."subgraphs"."material_unit_price" IS '材料单价（元/kg）';

COMMENT ON COLUMN "public"."subgraphs"."material_cost" IS '材料费（元）';

COMMENT ON COLUMN "public"."subgraphs"."heat_treatment_unit_price" IS '热处理单价（元）';

COMMENT ON COLUMN "public"."subgraphs"."heat_treatment_cost" IS '热处理费（元）';

COMMENT ON COLUMN "public"."subgraphs"."process_description" IS '工艺说明，如S-Z-WC-QC（报表第14列）';

COMMENT ON COLUMN "public"."subgraphs"."nc_z_time" IS 'nc主视图时间';

COMMENT ON COLUMN "public"."subgraphs"."nc_b_time" IS 'nc背面时间';

COMMENT ON COLUMN "public"."subgraphs"."nc_c_time" IS 'nc侧面正面时间';

COMMENT ON COLUMN "public"."subgraphs"."nc_c_b_time" IS 'nc侧背时间';

COMMENT ON COLUMN "public"."subgraphs"."large_grinding_time" IS '大水磨时间（小时）（报表第19列）';

COMMENT ON COLUMN "public"."subgraphs"."small_grinding_time" IS '小磨床时间（小时）（报表第20列）';

COMMENT ON COLUMN "public"."subgraphs"."edm_time" IS '放电时间（小时）（报表第25列）';

COMMENT ON COLUMN "public"."subgraphs"."engraving_time" IS '雕刻时间（小时）（报表第26列）';

COMMENT ON COLUMN "public"."subgraphs"."slow_wire_length" IS '慢丝长度（mm）（报表第21列）';

COMMENT ON COLUMN "public"."subgraphs"."slow_wire_side_length" IS '侧割长度（mm）（报表第22列）';

COMMENT ON COLUMN "public"."subgraphs"."mid_wire_length" IS '中丝长度（mm）（报表第23列）';

COMMENT ON COLUMN "public"."subgraphs"."fast_wire_length" IS '快丝长度（mm）（报表第24列）';

COMMENT ON COLUMN "public"."subgraphs"."separate_item" IS '单独项说明（报表第27列）';

COMMENT ON COLUMN "public"."subgraphs"."total_cost" IS '费用总计（元）（报表第28列）';

COMMENT ON COLUMN "public"."subgraphs"."wire_process_note" IS '线割工艺说明（报表第29列）';

COMMENT ON COLUMN "public"."subgraphs"."nc_z_fee" IS 'nc主视图费用（元）（报表第30列）';

COMMENT ON COLUMN "public"."subgraphs"."nc_b_fee" IS 'nc背面费用（元）（报表第31列）';

COMMENT ON COLUMN "public"."subgraphs"."nc_c_fee" IS 'nc侧面正面费用（元）（报表第32列）';

COMMENT ON COLUMN "public"."subgraphs"."nc_c_b_fee" IS 'nc侧背费用（元）（报表第33列）';

COMMENT ON COLUMN "public"."subgraphs"."large_grinding_cost" IS '大磨床费用（元）（报表第34列）';

COMMENT ON COLUMN "public"."subgraphs"."small_grinding_cost" IS '小磨床费用（元）（报表第35列）';

COMMENT ON COLUMN "public"."subgraphs"."slow_wire_cost" IS '慢丝费用（元）（报表第36列）';

COMMENT ON COLUMN "public"."subgraphs"."slow_wire_side_cost" IS '慢丝侧割费用（元）（报表第37列）';

COMMENT ON COLUMN "public"."subgraphs"."mid_wire_cost" IS '中丝费用（元）（报表第38列）';

COMMENT ON COLUMN "public"."subgraphs"."fast_wire_cost" IS '快丝费用（元）（报表第39列）';

COMMENT ON COLUMN "public"."subgraphs"."edm_cost" IS '放电费用（元）（报表第40列）';

COMMENT ON COLUMN "public"."subgraphs"."engraving_cost" IS '雕刻费用（元）（报表第41列）';

COMMENT ON COLUMN "public"."subgraphs"."separate_item_cost" IS '单独计费（元）（报表第42列）';

COMMENT ON COLUMN "public"."subgraphs"."processing_cost_total" IS '加工费合计（元）（报表第43列）';

COMMENT ON COLUMN "public"."subgraphs"."applied_snapshot_ids" IS '应用的快照ID列表';

COMMENT ON COLUMN "public"."subgraphs"."rule_reason" IS '工艺规则应用原因';

COMMENT ON COLUMN "public"."subgraphs"."override_by_user" IS '是否被用户手动覆盖';

COMMENT ON COLUMN "public"."subgraphs"."cost_calculation_method" IS '成本计算方法';

COMMENT ON COLUMN "public"."subgraphs"."has_sheet_line" IS '是否有板料线（Phase 2功能）';

COMMENT ON COLUMN "public"."subgraphs"."sheet_area_mm2" IS '板料面积（平方毫米）';

COMMENT ON COLUMN "public"."subgraphs"."sheet_perimeter_mm" IS '板料周长（毫米）';

COMMENT ON COLUMN "public"."subgraphs"."sheet_line_data" IS '板料线数据，JSON格式';

COMMENT ON COLUMN "public"."subgraphs"."has_single_nc_calc" IS '是否有单独NC计算';

COMMENT ON COLUMN "public"."subgraphs"."single_prt_file" IS '单独的PRT文件路径';

COMMENT ON COLUMN "public"."subgraphs"."process_changed" IS '工艺是否变更';

COMMENT ON COLUMN "public"."subgraphs"."original_process" IS '原始工艺类型';

COMMENT ON COLUMN "public"."subgraphs"."prt_3d_file" IS '3D PRT文件路径';

COMMENT ON COLUMN "public"."subgraphs"."recalc_count" IS '重算次数';

COMMENT ON COLUMN "public"."subgraphs"."last_recalc_at" IS '最后重算时间';

COMMENT ON COLUMN "public"."subgraphs"."last_recalc_by" IS '最后重算人';

COMMENT ON COLUMN "public"."subgraphs"."status" IS '子图状态';

COMMENT ON COLUMN "public"."subgraphs"."created_at" IS '创建时间';

COMMENT ON COLUMN "public"."subgraphs"."updated_at" IS '更新时间';

COMMENT ON COLUMN "public"."subgraphs"."metadata" IS '扩展元数据，JSON格式';

COMMENT ON COLUMN "public"."subgraphs"."wire_process" IS '线割工艺';

COMMENT ON COLUMN "public"."subgraphs"."small_grinding_count" IS '小磨床数量（个）（报表第20列）';

COMMENT ON COLUMN "public"."subgraphs"."nc_z_view_time" IS 'nc正面时间';

COMMENT ON COLUMN "public"."subgraphs"."nc_b_view_time" IS 'nc正面的背面时间
';

COMMENT ON COLUMN "public"."subgraphs"."nc_z_view_fee" IS 'nc正面金额';

COMMENT ON COLUMN "public"."subgraphs"."nc_b_view_fee" IS 'nc正面的背面金额';

COMMENT ON TABLE "public"."subgraphs" IS '子图表，存储每个子图的业务数据和成本信息';