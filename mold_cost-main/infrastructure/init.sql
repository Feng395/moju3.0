-- ============================================
-- 迁移来源: mold_cost/backend_main/infrastructure/init-db.sql
-- 迁移日期: 2026-02-06
-- 说明: 数据库初始化脚本，创建所有表结构和索引
-- 改进说明:
--   - 整合到统一的 infrastructure 目录
--   - 包含完整的数据库schema定义
--   - 支持Docker容器初始化
-- ============================================

/*
 Navicat Premium Dump SQL

 Source Server         : moju
 Source Server Type    : PostgreSQL
 Source Server Version : 170006 (170006)
 Source Host           : 192.168.1.54:5432
 Source Catalog        : mold_cost_db
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 170006 (170006)
 File Encoding         : 65001

 Date: 06/02/2026 13:39:58
*/


-- ----------------------------
-- Sequence structure for audit_logs_audit_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."audit_logs_audit_id_seq";
CREATE SEQUENCE "public"."audit_logs_audit_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for audit_logs_audit_id_seq1
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."audit_logs_audit_id_seq1";
CREATE SEQUENCE "public"."audit_logs_audit_id_seq1" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for chat_messages_message_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."chat_messages_message_id_seq";
CREATE SEQUENCE "public"."chat_messages_message_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for features_feature_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."features_feature_id_seq";
CREATE SEQUENCE "public"."features_feature_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for job_price_snapshots_snapshot_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."job_price_snapshots_snapshot_id_seq";
CREATE SEQUENCE "public"."job_price_snapshots_snapshot_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for job_price_snapshots_snapshot_id_seq1
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."job_price_snapshots_snapshot_id_seq1";
CREATE SEQUENCE "public"."job_price_snapshots_snapshot_id_seq1" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for job_process_snapshots_snapshot_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."job_process_snapshots_snapshot_id_seq";
CREATE SEQUENCE "public"."job_process_snapshots_snapshot_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for job_process_snapshots_snapshot_id_seq1
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."job_process_snapshots_snapshot_id_seq1";
CREATE SEQUENCE "public"."job_process_snapshots_snapshot_id_seq1" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for login_logs_log_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."login_logs_log_id_seq";
CREATE SEQUENCE "public"."login_logs_log_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for login_logs_log_id_seq1
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."login_logs_log_id_seq1";
CREATE SEQUENCE "public"."login_logs_log_id_seq1" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for operation_logs_log_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."operation_logs_log_id_seq";
CREATE SEQUENCE "public"."operation_logs_log_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for operation_logs_log_id_seq1
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."operation_logs_log_id_seq1";
CREATE SEQUENCE "public"."operation_logs_log_id_seq1" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for price_histories_history_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."price_histories_history_id_seq";
CREATE SEQUENCE "public"."price_histories_history_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for price_histories_history_id_seq1
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."price_histories_history_id_seq1";
CREATE SEQUENCE "public"."price_histories_history_id_seq1" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for processing_cost_calculation_details_detail_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."processing_cost_calculation_details_detail_id_seq";
CREATE SEQUENCE "public"."processing_cost_calculation_details_detail_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Table structure for archives
-- ----------------------------
DROP TABLE IF EXISTS "public"."archives";
CREATE TABLE "public"."archives" (
  "archive_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "archive_path" varchar(500) COLLATE "pg_catalog"."default" NOT NULL,
  "file_size" int8 NOT NULL,
  "checksum" varchar(64) COLLATE "pg_catalog"."default" NOT NULL,
  "archived_at" timestamp(6) NOT NULL DEFAULT now(),
  "expires_at" timestamp(6)
)
;
COMMENT ON COLUMN "public"."archives"."archive_id" IS '归档唯一标识';
COMMENT ON COLUMN "public"."archives"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."archives"."archive_path" IS 'MinIO归档路径';
COMMENT ON COLUMN "public"."archives"."file_size" IS '文件大小（字节）';
COMMENT ON COLUMN "public"."archives"."checksum" IS 'MD5校验和';
COMMENT ON COLUMN "public"."archives"."archived_at" IS '归档时间';
COMMENT ON COLUMN "public"."archives"."expires_at" IS '过期时间（7年后）';
COMMENT ON TABLE "public"."archives" IS '归档表，记录归档数据';

-- ----------------------------
-- Table structure for audit_logs
-- ----------------------------
DROP TABLE IF EXISTS "public"."audit_logs";
CREATE TABLE "public"."audit_logs" (
  "audit_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "user_id" uuid,
  "action" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "resource_type" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "resource_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "changes" jsonb,
  "ip_address" varchar(50) COLLATE "pg_catalog"."default",
  "user_agent" varchar(255) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."audit_logs"."audit_id" IS '审计ID，自增主键';
COMMENT ON COLUMN "public"."audit_logs"."user_id" IS '用户ID';
COMMENT ON COLUMN "public"."audit_logs"."action" IS '操作类型';
COMMENT ON COLUMN "public"."audit_logs"."resource_type" IS '资源类型：job-任务, subgraph-子图, price-价格, rule-规则';
COMMENT ON COLUMN "public"."audit_logs"."resource_id" IS '资源ID';
COMMENT ON COLUMN "public"."audit_logs"."changes" IS '变更内容，JSON格式，包含before和after';
COMMENT ON COLUMN "public"."audit_logs"."ip_address" IS 'IP地址';
COMMENT ON COLUMN "public"."audit_logs"."user_agent" IS '用户代理字符串';
COMMENT ON COLUMN "public"."audit_logs"."created_at" IS '创建时间';
COMMENT ON TABLE "public"."audit_logs" IS '审计日志表，记录所有数据变更';

-- ----------------------------
-- Table structure for batch_recalculations
-- ----------------------------
DROP TABLE IF EXISTS "public"."batch_recalculations";
CREATE TABLE "public"."batch_recalculations" (
  "batch_recalc_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "subgraph_ids" text[] COLLATE "pg_catalog"."default" NOT NULL,
  "reason" text COLLATE "pg_catalog"."default" NOT NULL,
  "total_count" int4 NOT NULL,
  "completed_count" int4 DEFAULT 0,
  "failed_count" int4 DEFAULT 0,
  "old_total_cost" numeric(12,2),
  "new_total_cost" numeric(12,2),
  "cost_diff" numeric(12,2),
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'pending'::character varying,
  "created_by" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "completed_at" timestamp(6)
)
;
COMMENT ON COLUMN "public"."batch_recalculations"."batch_recalc_id" IS '批量重算唯一标识';
COMMENT ON COLUMN "public"."batch_recalculations"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."batch_recalculations"."subgraph_ids" IS '子图ID列表';
COMMENT ON COLUMN "public"."batch_recalculations"."reason" IS '重算原因';
COMMENT ON COLUMN "public"."batch_recalculations"."total_count" IS '总数';
COMMENT ON COLUMN "public"."batch_recalculations"."completed_count" IS '完成数';
COMMENT ON COLUMN "public"."batch_recalculations"."failed_count" IS '失败数';
COMMENT ON COLUMN "public"."batch_recalculations"."old_total_cost" IS '旧总成本（元）';
COMMENT ON COLUMN "public"."batch_recalculations"."new_total_cost" IS '新总成本（元）';
COMMENT ON COLUMN "public"."batch_recalculations"."cost_diff" IS '成本差异（元）';
COMMENT ON COLUMN "public"."batch_recalculations"."status" IS '状态：pending-待处理, processing-处理中, completed-已完成, failed-失败';
COMMENT ON COLUMN "public"."batch_recalculations"."created_by" IS '创建人';
COMMENT ON COLUMN "public"."batch_recalculations"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."batch_recalculations"."completed_at" IS '完成时间';
COMMENT ON TABLE "public"."batch_recalculations" IS '批量重算表，记录批量重算任务';

-- ----------------------------
-- Table structure for chat_messages
-- ----------------------------
DROP TABLE IF EXISTS "public"."chat_messages";
CREATE TABLE "public"."chat_messages" (
  "message_id" int4 NOT NULL DEFAULT nextval('chat_messages_message_id_seq'::regclass),
  "session_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "role" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "content" text COLLATE "pg_catalog"."default" NOT NULL,
  "timestamp" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "metadata" jsonb
)
;
COMMENT ON COLUMN "public"."chat_messages"."role" IS '消息角色：user(用户), assistant(AI助手), system(系统)';
COMMENT ON COLUMN "public"."chat_messages"."content" IS '消息内容';
COMMENT ON COLUMN "public"."chat_messages"."metadata" IS '额外信息，如修改记录、文件信息等';
COMMENT ON TABLE "public"."chat_messages" IS '聊天消息表，记录会话中的所有消息';

-- ----------------------------
-- Table structure for chat_sessions
-- ----------------------------
DROP TABLE IF EXISTS "public"."chat_sessions";
CREATE TABLE "public"."chat_sessions" (
  "session_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "user_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'active'::character varying,
  "metadata" jsonb,
  "name" varchar(255) COLLATE "pg_catalog"."default"
)
;
COMMENT ON COLUMN "public"."chat_sessions"."session_id" IS '会话ID，通常与job_id相同';
COMMENT ON COLUMN "public"."chat_sessions"."job_id" IS '关联的任务ID';
COMMENT ON COLUMN "public"."chat_sessions"."user_id" IS '用户ID';
COMMENT ON COLUMN "public"."chat_sessions"."metadata" IS '额外信息，如文件名、任务描述等';
COMMENT ON COLUMN "public"."chat_sessions"."name" IS '标题';
COMMENT ON TABLE "public"."chat_sessions" IS '聊天会话表，记录每个审核任务的会话';

-- ----------------------------
-- Table structure for features
-- ----------------------------
DROP TABLE IF EXISTS "public"."features";
CREATE TABLE "public"."features" (
  "feature_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "version" int4 NOT NULL DEFAULT 1,
  "length_mm" numeric(10,2),
  "width_mm" numeric(10,2),
  "thickness_mm" numeric(10,3),
  "quantity" int4 DEFAULT 1,
  "material" varchar(50) COLLATE "pg_catalog"."default",
  "heat_treatment" varchar(100) COLLATE "pg_catalog"."default",
  "calculated_weight_kg" numeric(10,3),
  "top_view_wire_length" numeric(10,3),
  "front_view_wire_length" numeric(10,3),
  "side_view_wire_length" numeric(10,3),
  "has_auto_material" bool DEFAULT false,
  "needs_heat_treatment" bool DEFAULT false,
  "boring_length_mm" numeric(10,3),
  "processing_instructions" jsonb,
  "is_complete" bool DEFAULT false,
  "missing_params" text[] COLLATE "pg_catalog"."default",
  "abnormal_situation" jsonb,
  "created_by" varchar(50) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "metadata" jsonb,
  "slider_angle" varchar(255) COLLATE "pg_catalog"."default",
  "boring_num" int4,
  "nc_time_cost" jsonb,
  "tooth_hole" jsonb,
  "water_mill" jsonb,
  "has_material_preparation" varchar(255) COLLATE "pg_catalog"."default"
)
;
COMMENT ON COLUMN "public"."features"."feature_id" IS '特征唯一标识，自增主键';
COMMENT ON COLUMN "public"."features"."subgraph_id" IS '所属子图ID';
COMMENT ON COLUMN "public"."features"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."features"."version" IS '特征版本号，支持历史版本追溯';
COMMENT ON COLUMN "public"."features"."length_mm" IS '长度（毫米）（报表第5列）';
COMMENT ON COLUMN "public"."features"."width_mm" IS '宽度（毫米）（报表第6列）';
COMMENT ON COLUMN "public"."features"."thickness_mm" IS '厚度（毫米）（报表第7列）';
COMMENT ON COLUMN "public"."features"."quantity" IS '数量（报表第8列）';
COMMENT ON COLUMN "public"."features"."material" IS '材质，如45# (报表第4列)';
COMMENT ON COLUMN "public"."features"."heat_treatment" IS '热处理要求';
COMMENT ON COLUMN "public"."features"."calculated_weight_kg" IS '计算重量（千克）';
COMMENT ON COLUMN "public"."features"."top_view_wire_length" IS '俯视图线割长度（毫米）';
COMMENT ON COLUMN "public"."features"."front_view_wire_length" IS '正视图线割长度（毫米）';
COMMENT ON COLUMN "public"."features"."side_view_wire_length" IS '侧视图线割长度（毫米）';
COMMENT ON COLUMN "public"."features"."has_auto_material" IS '是否有自找料';
COMMENT ON COLUMN "public"."features"."needs_heat_treatment" IS '是否需要热处理';
COMMENT ON COLUMN "public"."features"."boring_length_mm" IS '镗孔长度（毫米）';
COMMENT ON COLUMN "public"."features"."processing_instructions" IS '加工说明，JSON格式，包含所有提取到的加工说明';
COMMENT ON COLUMN "public"."features"."is_complete" IS '特征数据是否完整';
COMMENT ON COLUMN "public"."features"."missing_params" IS '缺失的参数列表';
COMMENT ON COLUMN "public"."features"."abnormal_situation" IS '异常情况记录，JSON格式';
COMMENT ON COLUMN "public"."features"."created_by" IS '创建人';
COMMENT ON COLUMN "public"."features"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."features"."metadata" IS '线割加工工艺说明，JSON格式';
COMMENT ON COLUMN "public"."features"."slider_angle" IS '滑块角度';
COMMENT ON COLUMN "public"."features"."boring_num" IS '孔的个数';
COMMENT ON COLUMN "public"."features"."nc_time_cost" IS 'NC时间详细数据，格式: {"nc_details": [{"code": "L", "value": "5"}, {"code": "ZXZ", "value": "5"}, {"code": "开粗", "value": "5"}, {"code": "精铣", "value": "5"}]}';
COMMENT ON COLUMN "public"."features"."tooth_hole" IS '牙孔数据，JSON格式';
COMMENT ON COLUMN "public"."features"."water_mill" IS '水磨数据，JSON格式';
COMMENT ON COLUMN "public"."features"."has_material_preparation" IS '是否备料于';
COMMENT ON TABLE "public"."features" IS '特征表，存储从CAD提取的原始特征数据，支持历史版本';

-- ----------------------------
-- Table structure for job_price_snapshots
-- ----------------------------
DROP TABLE IF EXISTS "public"."job_price_snapshots";
CREATE TABLE "public"."job_price_snapshots" (
  "snapshot_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "job_id" uuid NOT NULL,
  "original_price_id" varchar(50) COLLATE "pg_catalog"."default",
  "version_id" varchar(50) COLLATE "pg_catalog"."default",
  "category" varchar(100) COLLATE "pg_catalog"."default",
  "sub_category" varchar(200) COLLATE "pg_catalog"."default",
  "price" varchar(50) COLLATE "pg_catalog"."default",
  "unit" varchar(50) COLLATE "pg_catalog"."default",
  "work_hours" varchar(50) COLLATE "pg_catalog"."default",
  "min_num" varchar(50) COLLATE "pg_catalog"."default",
  "add_price" varchar(50) COLLATE "pg_catalog"."default",
  "weight_num" varchar(50) COLLATE "pg_catalog"."default",
  "note" varchar(500) COLLATE "pg_catalog"."default",
  "instruction" varchar(500) COLLATE "pg_catalog"."default",
  "is_modified" bool DEFAULT false,
  "modified_by" varchar(50) COLLATE "pg_catalog"."default",
  "modified_at" timestamp(6),
  "modification_reason" text COLLATE "pg_catalog"."default",
  "snapshot_created_at" timestamp(6) NOT NULL DEFAULT now(),
  "metadata" jsonb
)
;
COMMENT ON COLUMN "public"."job_price_snapshots"."snapshot_id" IS '快照唯一标识，自增主键';
COMMENT ON COLUMN "public"."job_price_snapshots"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."job_price_snapshots"."original_price_id" IS '原始价格项ID（VARCHAR类型），用于追溯，如P001';
COMMENT ON COLUMN "public"."job_price_snapshots"."version_id" IS '价格版本号（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."category" IS '类别（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."sub_category" IS '子类（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."price" IS '单价（VARCHAR类型，用户可修改）';
COMMENT ON COLUMN "public"."job_price_snapshots"."unit" IS '单位（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."work_hours" IS '工时（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."min_num" IS '最低计费标准（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."add_price" IS '附加费（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."weight_num" IS '重量计算系数（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."note" IS '备注（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."instruction" IS '计算说明（VARCHAR类型）';
COMMENT ON COLUMN "public"."job_price_snapshots"."is_modified" IS '是否被用户修改';
COMMENT ON COLUMN "public"."job_price_snapshots"."modified_by" IS '修改人';
COMMENT ON COLUMN "public"."job_price_snapshots"."modified_at" IS '修改时间';
COMMENT ON COLUMN "public"."job_price_snapshots"."modification_reason" IS '修改原因';
COMMENT ON COLUMN "public"."job_price_snapshots"."snapshot_created_at" IS '快照创建时间';
COMMENT ON COLUMN "public"."job_price_snapshots"."metadata" IS '扩展元数据，JSON格式';
COMMENT ON TABLE "public"."job_price_snapshots" IS '任务价格快照表，每个任务创建时从price_items复制';

-- ----------------------------
-- Table structure for job_process_snapshots
-- ----------------------------
DROP TABLE IF EXISTS "public"."job_process_snapshots";
CREATE TABLE "public"."job_process_snapshots" (
  "snapshot_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "job_id" uuid NOT NULL,
  "original_rule_id" varchar(50) COLLATE "pg_catalog"."default",
  "version_id" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "feature_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "priority" int4 DEFAULT 0,
  "conditions" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "output_params" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "is_modified" bool DEFAULT false,
  "modified_by" varchar(50) COLLATE "pg_catalog"."default",
  "modified_at" timestamp(6),
  "modification_reason" text COLLATE "pg_catalog"."default",
  "snapshot_created_at" timestamp(6) NOT NULL DEFAULT now(),
  "metadata" jsonb
)
;
COMMENT ON COLUMN "public"."job_process_snapshots"."snapshot_id" IS '快照唯一标识，自增主键';
COMMENT ON COLUMN "public"."job_process_snapshots"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."job_process_snapshots"."original_rule_id" IS '原始规则ID（VARCHAR类型），用于追溯，如R001';
COMMENT ON COLUMN "public"."job_process_snapshots"."version_id" IS '规则版本号';
COMMENT ON COLUMN "public"."job_process_snapshots"."feature_type" IS '特征类型';
COMMENT ON COLUMN "public"."job_process_snapshots"."name" IS '规则名称';
COMMENT ON COLUMN "public"."job_process_snapshots"."description" IS '规则描述';
COMMENT ON COLUMN "public"."job_process_snapshots"."priority" IS '优先级';
COMMENT ON COLUMN "public"."job_process_snapshots"."conditions" IS '规则条件，字符串格式（<=255）（用户可修改）';
COMMENT ON COLUMN "public"."job_process_snapshots"."output_params" IS '输出参数，字符串格式（<=255）（用户可修改）';
COMMENT ON COLUMN "public"."job_process_snapshots"."is_modified" IS '是否被用户修改';
COMMENT ON COLUMN "public"."job_process_snapshots"."modified_by" IS '修改人';
COMMENT ON COLUMN "public"."job_process_snapshots"."modified_at" IS '修改时间';
COMMENT ON COLUMN "public"."job_process_snapshots"."modification_reason" IS '修改原因';
COMMENT ON COLUMN "public"."job_process_snapshots"."snapshot_created_at" IS '快照创建时间';
COMMENT ON COLUMN "public"."job_process_snapshots"."metadata" IS '扩展元数据，JSON格式';
COMMENT ON TABLE "public"."job_process_snapshots" IS '任务工艺快照表，每个任务创建时从process_rules复制';

-- ----------------------------
-- Table structure for jobs
-- ----------------------------
DROP TABLE IF EXISTS "public"."jobs";
CREATE TABLE "public"."jobs" (
  "job_id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "dwg_file_id" varchar(100) COLLATE "pg_catalog"."default",
  "dwg_file_name" varchar(255) COLLATE "pg_catalog"."default",
  "dwg_file_path" varchar(500) COLLATE "pg_catalog"."default",
  "dwg_file_size" int8,
  "prt_file_id" varchar(100) COLLATE "pg_catalog"."default",
  "prt_file_name" varchar(255) COLLATE "pg_catalog"."default",
  "prt_file_path" varchar(500) COLLATE "pg_catalog"."default",
  "prt_file_size" int8,
  "status" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'pending'::character varying,
  "current_stage" varchar(50) COLLATE "pg_catalog"."default",
  "progress" int4 DEFAULT 0,
  "total_subgraphs" int4 DEFAULT 0,
  "total_cost" numeric(12,2),
  "currency" varchar(10) COLLATE "pg_catalog"."default" DEFAULT 'CNY'::character varying,
  "processes_used" text[] COLLATE "pg_catalog"."default",
  "material_cost" numeric(12,2),
  "heat_treatment_cost" numeric(12,2),
  "fast_wire_cost" numeric(12,2),
  "mid_wire_cost" numeric(12,2),
  "slow_wire_cost" numeric(12,2),
  "nc_cost" numeric(12,2),
  "grinding_cost" numeric(12,2),
  "edm_cost" numeric(12,2),
  "processing_cost_total" numeric(12,2),
  "price_version_locked" varchar(20) COLLATE "pg_catalog"."default",
  "process_version_locked" varchar(20) COLLATE "pg_catalog"."default",
  "snapshot_created_at" timestamp(6),
  "report_id" varchar(100) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "updated_at" timestamp(6) NOT NULL DEFAULT now(),
  "completed_at" timestamp(6),
  "archived_at" timestamp(6),
  "error_message" text COLLATE "pg_catalog"."default",
  "metadata" jsonb
)
;
COMMENT ON COLUMN "public"."jobs"."job_id" IS '任务唯一标识UUID';
COMMENT ON COLUMN "public"."jobs"."user_id" IS '创建任务的用户ID';
COMMENT ON COLUMN "public"."jobs"."dwg_file_id" IS 'DWG文件ID';
COMMENT ON COLUMN "public"."jobs"."dwg_file_name" IS 'DWG文件名';
COMMENT ON COLUMN "public"."jobs"."dwg_file_path" IS 'DWG文件在MinIO中的路径';
COMMENT ON COLUMN "public"."jobs"."dwg_file_size" IS 'DWG文件大小（字节）';
COMMENT ON COLUMN "public"."jobs"."prt_file_id" IS 'PRT文件ID';
COMMENT ON COLUMN "public"."jobs"."prt_file_name" IS 'PRT文件名';
COMMENT ON COLUMN "public"."jobs"."prt_file_path" IS 'PRT文件在MinIO中的路径';
COMMENT ON COLUMN "public"."jobs"."prt_file_size" IS 'PRT文件大小（字节）';
COMMENT ON COLUMN "public"."jobs"."status" IS '任务状态：pending-待处理, processing-处理中, need_user_input-等待用户输入, completed-已完成, failed-失败, archived-已归档';
COMMENT ON COLUMN "public"."jobs"."current_stage" IS '当前执行阶段：initializing, cad_parsing, feature_recognition等';
COMMENT ON COLUMN "public"."jobs"."progress" IS '任务进度百分比（0-100）';
COMMENT ON COLUMN "public"."jobs"."total_subgraphs" IS '子图总数';
COMMENT ON COLUMN "public"."jobs"."total_cost" IS '总成本（元）';
COMMENT ON COLUMN "public"."jobs"."currency" IS '货币单位，默认CNY';
COMMENT ON COLUMN "public"."jobs"."processes_used" IS '使用的工艺列表';
COMMENT ON COLUMN "public"."jobs"."material_cost" IS '材料费合计（元）';
COMMENT ON COLUMN "public"."jobs"."heat_treatment_cost" IS '热处理费合计（元）';
COMMENT ON COLUMN "public"."jobs"."fast_wire_cost" IS '快丝线割费用合计（元）';
COMMENT ON COLUMN "public"."jobs"."mid_wire_cost" IS '中丝线割费用合计（元）';
COMMENT ON COLUMN "public"."jobs"."slow_wire_cost" IS '慢丝线割费用合计（元）';
COMMENT ON COLUMN "public"."jobs"."nc_cost" IS 'NC加工费用合计（元）';
COMMENT ON COLUMN "public"."jobs"."grinding_cost" IS '磨床加工费用合计（元）';
COMMENT ON COLUMN "public"."jobs"."edm_cost" IS '放电加工费用合计（元）';
COMMENT ON COLUMN "public"."jobs"."processing_cost_total" IS '加工费用总合计（元）';
COMMENT ON COLUMN "public"."jobs"."price_version_locked" IS '锁定的价格版本号，如v1.0';
COMMENT ON COLUMN "public"."jobs"."process_version_locked" IS '锁定的工艺版本号，如v1.0';
COMMENT ON COLUMN "public"."jobs"."snapshot_created_at" IS '快照创建时间';
COMMENT ON COLUMN "public"."jobs"."report_id" IS '生成的报表ID';
COMMENT ON COLUMN "public"."jobs"."created_at" IS '任务创建时间';
COMMENT ON COLUMN "public"."jobs"."updated_at" IS '任务更新时间';
COMMENT ON COLUMN "public"."jobs"."completed_at" IS '任务完成时间';
COMMENT ON COLUMN "public"."jobs"."archived_at" IS '任务归档时间';
COMMENT ON COLUMN "public"."jobs"."error_message" IS '错误信息';
COMMENT ON COLUMN "public"."jobs"."metadata" IS '扩展元数据，JSON格式';
COMMENT ON TABLE "public"."jobs" IS '任务表，存储任务的基本信息和状态';

-- ----------------------------
-- Table structure for login_logs
-- ----------------------------
DROP TABLE IF EXISTS "public"."login_logs";
CREATE TABLE "public"."login_logs" (
  "log_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "user_id" uuid,
  "username" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "login_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "status" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "ip_address" varchar(50) COLLATE "pg_catalog"."default",
  "user_agent" varchar(255) COLLATE "pg_catalog"."default",
  "failure_reason" varchar(255) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."login_logs"."log_id" IS '日志ID，自增主键';
COMMENT ON COLUMN "public"."login_logs"."user_id" IS '用户ID';
COMMENT ON COLUMN "public"."login_logs"."username" IS '用户名';
COMMENT ON COLUMN "public"."login_logs"."login_type" IS '登录类型：login-登录, logout-登出, token_refresh-令牌刷新';
COMMENT ON COLUMN "public"."login_logs"."status" IS '状态：success-成功, failed-失败';
COMMENT ON COLUMN "public"."login_logs"."ip_address" IS 'IP地址';
COMMENT ON COLUMN "public"."login_logs"."user_agent" IS '用户代理字符串';
COMMENT ON COLUMN "public"."login_logs"."failure_reason" IS '失败原因';
COMMENT ON COLUMN "public"."login_logs"."created_at" IS '日志创建时间';
COMMENT ON TABLE "public"."login_logs" IS '登录日志表，记录用户登录历史';

-- ----------------------------
-- Table structure for nc_calculations
-- ----------------------------
DROP TABLE IF EXISTS "public"."nc_calculations";
CREATE TABLE "public"."nc_calculations" (
  "calc_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default",
  "calc_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "prt_file" varchar(500) COLLATE "pg_catalog"."default" NOT NULL,
  "drilling_time" numeric(10,2),
  "roughing_time" numeric(10,2),
  "milling_time" numeric(10,2),
  "total_cost" numeric(12,2),
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."nc_calculations"."calc_id" IS '计算唯一标识';
COMMENT ON COLUMN "public"."nc_calculations"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."nc_calculations"."subgraph_id" IS '子图ID（可选）';
COMMENT ON COLUMN "public"."nc_calculations"."calc_type" IS '计算类型：complete-完整计算, single-单独计算';
COMMENT ON COLUMN "public"."nc_calculations"."prt_file" IS 'PRT文件路径';
COMMENT ON COLUMN "public"."nc_calculations"."drilling_time" IS '钻孔时间（分钟）';
COMMENT ON COLUMN "public"."nc_calculations"."roughing_time" IS '开粗时间（分钟）';
COMMENT ON COLUMN "public"."nc_calculations"."milling_time" IS '精铣时间（分钟）';
COMMENT ON COLUMN "public"."nc_calculations"."total_cost" IS '总成本（元）';
COMMENT ON COLUMN "public"."nc_calculations"."created_at" IS '创建时间';
COMMENT ON TABLE "public"."nc_calculations" IS 'NC计算记录表，记录单独NC计算';

-- ----------------------------
-- Table structure for operation_logs
-- ----------------------------
DROP TABLE IF EXISTS "public"."operation_logs";
CREATE TABLE "public"."operation_logs" (
  "log_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "job_id" uuid,
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default",
  "agent" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "action" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "input_data" jsonb,
  "output_data" jsonb,
  "status" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "duration_ms" int4,
  "error_message" text COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."operation_logs"."log_id" IS '日志ID，自增主键';
COMMENT ON COLUMN "public"."operation_logs"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."operation_logs"."subgraph_id" IS '子图ID（可选）';
COMMENT ON COLUMN "public"."operation_logs"."agent" IS 'Agent名称';
COMMENT ON COLUMN "public"."operation_logs"."action" IS '操作名称';
COMMENT ON COLUMN "public"."operation_logs"."input_data" IS '输入数据，JSON格式';
COMMENT ON COLUMN "public"."operation_logs"."output_data" IS '输出数据，JSON格式';
COMMENT ON COLUMN "public"."operation_logs"."status" IS '状态：success-成功, failed-失败, warning-警告';
COMMENT ON COLUMN "public"."operation_logs"."duration_ms" IS '执行时长（毫秒）';
COMMENT ON COLUMN "public"."operation_logs"."error_message" IS '错误信息';
COMMENT ON COLUMN "public"."operation_logs"."created_at" IS '创建时间';
COMMENT ON TABLE "public"."operation_logs" IS '操作日志表，记录所有Agent操作';

-- ----------------------------
-- Table structure for price_histories
-- ----------------------------
DROP TABLE IF EXISTS "public"."price_histories";
CREATE TABLE "public"."price_histories" (
  "history_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "job_id" uuid,
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default",
  "old_params" jsonb,
  "new_params" jsonb,
  "old_cost" numeric(12,2),
  "new_cost" numeric(12,2),
  "change_type" varchar(50) COLLATE "pg_catalog"."default",
  "changed_by" varchar(50) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."price_histories"."history_id" IS '历史记录ID，自增主键';
COMMENT ON COLUMN "public"."price_histories"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."price_histories"."subgraph_id" IS '子图ID';
COMMENT ON COLUMN "public"."price_histories"."old_params" IS '旧参数，JSON格式';
COMMENT ON COLUMN "public"."price_histories"."new_params" IS '新参数，JSON格式';
COMMENT ON COLUMN "public"."price_histories"."old_cost" IS '旧成本（元）';
COMMENT ON COLUMN "public"."price_histories"."new_cost" IS '新成本（元）';
COMMENT ON COLUMN "public"."price_histories"."change_type" IS '变更类型';
COMMENT ON COLUMN "public"."price_histories"."changed_by" IS '变更人';
COMMENT ON COLUMN "public"."price_histories"."created_at" IS '创建时间';
COMMENT ON TABLE "public"."price_histories" IS '价格历史表，记录价格变更历史';

-- ----------------------------
-- Table structure for price_items
-- ----------------------------
DROP TABLE IF EXISTS "public"."price_items";
CREATE TABLE "public"."price_items" (
  "id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "version_id" varchar(50) COLLATE "pg_catalog"."default",
  "category" varchar(100) COLLATE "pg_catalog"."default",
  "sub_category" varchar(200) COLLATE "pg_catalog"."default",
  "price" varchar(50) COLLATE "pg_catalog"."default",
  "unit" varchar(50) COLLATE "pg_catalog"."default",
  "work_hours" varchar(50) COLLATE "pg_catalog"."default",
  "min_num" varchar(50) COLLATE "pg_catalog"."default",
  "add_price" varchar(50) COLLATE "pg_catalog"."default",
  "weight_num" varchar(50) COLLATE "pg_catalog"."default",
  "note" varchar(500) COLLATE "pg_catalog"."default",
  "instruction" varchar(500) COLLATE "pg_catalog"."default",
  "is_active" bool DEFAULT true,
  "created_by" varchar(100) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "updated_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."price_items"."id" IS '价格项唯一标识（VARCHAR类型），如P001';
COMMENT ON COLUMN "public"."price_items"."version_id" IS '价格版本号（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."category" IS '类别（wire线割 、special特殊加工费、base基本加工费）';
COMMENT ON COLUMN "public"."price_items"."sub_category" IS '子类（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."price" IS '单价（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."unit" IS '单位（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."work_hours" IS '工时（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."min_num" IS '最低计费标准（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."add_price" IS '附加费（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."weight_num" IS '重量计算系数（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."note" IS '备注（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."instruction" IS '计算说明（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."is_active" IS '是否激活';
COMMENT ON COLUMN "public"."price_items"."created_by" IS '创建人（VARCHAR类型）';
COMMENT ON COLUMN "public"."price_items"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."price_items"."updated_at" IS '更新时间';
COMMENT ON TABLE "public"."price_items" IS '价格项表（全局模板），支持版本管理';

-- ----------------------------
-- Table structure for process_changes
-- ----------------------------
DROP TABLE IF EXISTS "public"."process_changes";
CREATE TABLE "public"."process_changes" (
  "change_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "from_process" varchar(20) COLLATE "pg_catalog"."default",
  "to_process" varchar(20) COLLATE "pg_catalog"."default",
  "reason" text COLLATE "pg_catalog"."default",
  "cost_impact" numeric(12,2),
  "extrusion_height" numeric(10,2),
  "created_by" varchar(50) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."process_changes"."change_id" IS '变更唯一标识';
COMMENT ON COLUMN "public"."process_changes"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."process_changes"."subgraph_id" IS '子图ID';
COMMENT ON COLUMN "public"."process_changes"."from_process" IS '原工艺类型';
COMMENT ON COLUMN "public"."process_changes"."to_process" IS '新工艺类型';
COMMENT ON COLUMN "public"."process_changes"."reason" IS '变更原因';
COMMENT ON COLUMN "public"."process_changes"."cost_impact" IS '成本影响（元）';
COMMENT ON COLUMN "public"."process_changes"."extrusion_height" IS '拉伸高度（毫米）';
COMMENT ON COLUMN "public"."process_changes"."created_by" IS '创建人';
COMMENT ON COLUMN "public"."process_changes"."created_at" IS '创建时间';
COMMENT ON TABLE "public"."process_changes" IS '工艺变更表，记录工艺变更';

-- ----------------------------
-- Table structure for process_rules
-- ----------------------------
DROP TABLE IF EXISTS "public"."process_rules";
CREATE TABLE "public"."process_rules" (
  "id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "version_id" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "feature_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "priority" int4 DEFAULT 0,
  "is_active" bool DEFAULT true,
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "conditions" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "output_params" varchar(255) COLLATE "pg_catalog"."default" NOT NULL
)
;
COMMENT ON COLUMN "public"."process_rules"."id" IS '规则唯一标识，如R001';
COMMENT ON COLUMN "public"."process_rules"."version_id" IS '规则版本号，如v1.0';
COMMENT ON COLUMN "public"."process_rules"."feature_type" IS '特征类型：WIRE-线割, NC-数控等';
COMMENT ON COLUMN "public"."process_rules"."name" IS '规则名称';
COMMENT ON COLUMN "public"."process_rules"."description" IS '规则描述';
COMMENT ON COLUMN "public"."process_rules"."priority" IS '优先级，数值越大优先级越高';
COMMENT ON COLUMN "public"."process_rules"."is_active" IS '是否激活';
COMMENT ON COLUMN "public"."process_rules"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."process_rules"."conditions" IS '规则条件，字符串格式（<=255）';
COMMENT ON COLUMN "public"."process_rules"."output_params" IS '输出参数，字符串格式（<=255）';
COMMENT ON TABLE "public"."process_rules" IS '工艺规则表（全局模板），支持版本管理';

-- ----------------------------
-- Table structure for processing_cost_calculation_details
-- ----------------------------
DROP TABLE IF EXISTS "public"."processing_cost_calculation_details";
CREATE TABLE "public"."processing_cost_calculation_details" (
  "detail_id" int8 NOT NULL GENERATED BY DEFAULT AS IDENTITY (
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1
),
  "job_id" uuid NOT NULL,
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "process_type" varchar(50) COLLATE "pg_catalog"."default",
  "adjusted_thickness" numeric(12,3),
  "weight" numeric(12,3),
  "multiplier_coefficient" numeric(12,3),
  "standard_hours" numeric(12,3),
  "actual_hours" numeric(12,3),
  "basic_processing_cost" numeric(12,2),
  "special_base_cost" numeric(12,2),
  "standard_base_cost" numeric(12,2),
  "selected_base_cost" numeric(12,2),
  "base_cost_selection" varchar(100) COLLATE "pg_catalog"."default",
  "material_additional_cost" numeric(12,2) DEFAULT 0,
  "material_cost" numeric(12,2) DEFAULT 0,
  "heat_treatment_cost" numeric(12,2) DEFAULT 0,
  "additional_cost_total" numeric(12,2) DEFAULT 0,
  "final_cost" numeric(12,2),
  "calculation_steps" jsonb,
  "calculated_at" timestamp(6) NOT NULL DEFAULT now(),
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "heat_additional_cost" numeric(12,2),
  "thread_ends_cost" varchar(255) COLLATE "pg_catalog"."default",
  "hanging_table_cost" varchar(255) COLLATE "pg_catalog"."default",
  "chamfer_cost" varchar(255) COLLATE "pg_catalog"."default",
  "bevel_cost" varchar(255) COLLATE "pg_catalog"."default",
  "oil_tank_cost" varchar(255) COLLATE "pg_catalog"."default",
  "grinding_cost" varchar(255) COLLATE "pg_catalog"."default",
  "water_mill_cost" varchar(255) COLLATE "pg_catalog"."default",
  "high_cost" varchar(255) COLLATE "pg_catalog"."default",
  "plate_cost" varchar(255) COLLATE "pg_catalog"."default",
  "long_strip_cost" varchar(255) COLLATE "pg_catalog"."default",
  "component_cost" varchar(255) COLLATE "pg_catalog"."default",
  "tooth_hole_cost" varchar(255) COLLATE "pg_catalog"."default",
  "tooth_hole_time_cost" varchar(255) COLLATE "pg_catalog"."default",
  "nc_roughing_cost" varchar(255) COLLATE "pg_catalog"."default",
  "nc_milling_cost" varchar(255) COLLATE "pg_catalog"."default",
  "nc_drilling_cost" varchar(255) COLLATE "pg_catalog"."default",
  "nc_base_roughing_cost" varchar(255) COLLATE "pg_catalog"."default",
  "nc_base_milling_cost" varchar(255) COLLATE "pg_catalog"."default",
  "nc_base_drilling_cost" varchar(255) COLLATE "pg_catalog"."default"
)
;
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."detail_id" IS '主键，自增';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."job_id" IS '任务ID';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."subgraph_id" IS '子图ID';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."process_type" IS '工艺类型: slow_wire/mid_wire/fast_wire/large_grinding/small_grinding/nc_roughing/nc_milling/drilling';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."adjusted_thickness" IS '调整后厚度(mm)，线割：不足15mm按15mm';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."weight" IS '材料重量(kg)或面积(mm²)，根据工艺不同';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."multiplier_coefficient" IS '系数：线割滑块系数/大水磨材料单价/小磨床单价/NC时薪';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."standard_hours" IS '标准工时(小时)，NC/大水磨';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."actual_hours" IS '实际工时(小时)，NC/大水磨';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."basic_processing_cost" IS '基本加工费用';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."special_base_cost" IS '特殊基本费：线割特殊工艺基本费/NC最低计费标准';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."standard_base_cost" IS '标准基本费：线割加工基本费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."selected_base_cost" IS '选中的基础成本';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."base_cost_selection" IS '基础成本选择逻辑';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."material_additional_cost" IS '材料附加费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."material_cost" IS '材料费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."heat_treatment_cost" IS '热处理费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."additional_cost_total" IS '附加费合计';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."final_cost" IS '最终费用';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."calculation_steps" IS '计算步骤详情(JSON数组)';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."calculated_at" IS '计算时间';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."heat_additional_cost" IS '热处理附加费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."thread_ends_cost" IS '线头费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."hanging_table_cost" IS '挂台费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."chamfer_cost" IS '倒角费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."bevel_cost" IS '斜面耗时';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."oil_tank_cost" IS '油槽耗时';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."grinding_cost" IS '研磨费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."water_mill_cost" IS '磨床费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."high_cost" IS '高度费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."plate_cost" IS '大水磨板费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."long_strip_cost" IS '大水磨长条费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."component_cost" IS '大水磨零件费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."tooth_hole_cost" IS '放电牙孔费';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."tooth_hole_time_cost" IS '放电时间';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."nc_roughing_cost" IS 'nc开粗费用';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."nc_milling_cost" IS 'nc精铣费用';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."nc_drilling_cost" IS 'nc钻床费用';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."nc_base_roughing_cost" IS 'nc开粗基本费用';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."nc_base_milling_cost" IS 'nc精铣基本费用';
COMMENT ON COLUMN "public"."processing_cost_calculation_details"."nc_base_drilling_cost" IS 'nc钻床基本费用';
COMMENT ON TABLE "public"."processing_cost_calculation_details" IS '加工费用计算明细表，统一存储各工艺计算过程中的中间结果';

-- ----------------------------
-- Table structure for recalculations
-- ----------------------------
DROP TABLE IF EXISTS "public"."recalculations";
CREATE TABLE "public"."recalculations" (
  "recalc_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "subgraph_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "batch_recalc_id" varchar(100) COLLATE "pg_catalog"."default",
  "reason" text COLLATE "pg_catalog"."default" NOT NULL,
  "modifications" jsonb,
  "old_cost" numeric(12,2),
  "new_cost" numeric(12,2),
  "cost_diff" numeric(12,2),
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'pending'::character varying,
  "created_by" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "completed_at" timestamp(6)
)
;
COMMENT ON COLUMN "public"."recalculations"."recalc_id" IS '重算唯一标识';
COMMENT ON COLUMN "public"."recalculations"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."recalculations"."subgraph_id" IS '子图ID';
COMMENT ON COLUMN "public"."recalculations"."batch_recalc_id" IS '批量重算ID（可选）';
COMMENT ON COLUMN "public"."recalculations"."reason" IS '重算原因';
COMMENT ON COLUMN "public"."recalculations"."modifications" IS '修改的参数，JSON格式';
COMMENT ON COLUMN "public"."recalculations"."old_cost" IS '旧成本（元）';
COMMENT ON COLUMN "public"."recalculations"."new_cost" IS '新成本（元）';
COMMENT ON COLUMN "public"."recalculations"."cost_diff" IS '成本差异（元）';
COMMENT ON COLUMN "public"."recalculations"."status" IS '状态：pending-待处理, processing-处理中, completed-已完成, failed-失败';
COMMENT ON COLUMN "public"."recalculations"."created_by" IS '创建人';
COMMENT ON COLUMN "public"."recalculations"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."recalculations"."completed_at" IS '完成时间';
COMMENT ON TABLE "public"."recalculations" IS '重算记录表，记录单个子图重算';

-- ----------------------------
-- Table structure for report_summary
-- ----------------------------
DROP TABLE IF EXISTS "public"."report_summary";
CREATE TABLE "public"."report_summary" (
  "summary_id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "report_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "total_material_cost" numeric(12,2),
  "total_heat_treatment_cost" numeric(12,2),
  "total_nc_roughing_cost" numeric(12,2),
  "total_nc_milling_cost" numeric(12,2),
  "total_drilling_cost" numeric(12,2),
  "total_milling_machine_cost" numeric(12,2),
  "total_large_grinding_cost" numeric(12,2),
  "total_small_grinding_cost" numeric(12,2),
  "total_slow_wire_cost" numeric(12,2),
  "total_slow_wire_side_cost" numeric(12,2),
  "total_mid_wire_cost" numeric(12,2),
  "total_fast_wire_cost" numeric(12,2),
  "total_edm_cost" numeric(12,2),
  "total_engraving_cost" numeric(12,2),
  "total_separate_item_cost" numeric(12,2),
  "total_processing_cost" numeric(12,2),
  "grand_total" numeric(12,2),
  "management_fee" numeric(12,2),
  "final_total" numeric(12,2),
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."report_summary"."summary_id" IS '汇总唯一标识UUID';
COMMENT ON COLUMN "public"."report_summary"."report_id" IS '报表ID';
COMMENT ON COLUMN "public"."report_summary"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."report_summary"."total_material_cost" IS '材料费合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_heat_treatment_cost" IS '热处理费合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_nc_roughing_cost" IS 'NC开粗费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_nc_milling_cost" IS 'NC精铣费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_drilling_cost" IS '钻床费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_milling_machine_cost" IS '铣床费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_large_grinding_cost" IS '大磨床费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_small_grinding_cost" IS '小磨床费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_slow_wire_cost" IS '慢丝费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_slow_wire_side_cost" IS '慢丝侧割费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_mid_wire_cost" IS '中丝费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_fast_wire_cost" IS '快丝费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_edm_cost" IS '放电费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_engraving_cost" IS '雕刻费用合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_separate_item_cost" IS '单独计费合计（元）';
COMMENT ON COLUMN "public"."report_summary"."total_processing_cost" IS '加工费总合计（元）';
COMMENT ON COLUMN "public"."report_summary"."grand_total" IS '总费用（材料+热处理+加工）';
COMMENT ON COLUMN "public"."report_summary"."management_fee" IS '管理费（元）';
COMMENT ON COLUMN "public"."report_summary"."final_total" IS '最终总计（元）';
COMMENT ON COLUMN "public"."report_summary"."created_at" IS '创建时间';
COMMENT ON TABLE "public"."report_summary" IS '报表汇总表，存储报表的汇总信息';

-- ----------------------------
-- Table structure for reports
-- ----------------------------
DROP TABLE IF EXISTS "public"."reports";
CREATE TABLE "public"."reports" (
  "report_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "job_id" uuid NOT NULL,
  "file_type" varchar(10) COLLATE "pg_catalog"."default" NOT NULL,
  "file_path" varchar(500) COLLATE "pg_catalog"."default" NOT NULL,
  "file_size" int8 NOT NULL,
  "download_url" varchar(1000) COLLATE "pg_catalog"."default",
  "url_expires_at" timestamp(6),
  "checksum" varchar(64) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now()
)
;
COMMENT ON COLUMN "public"."reports"."report_id" IS '报表唯一标识';
COMMENT ON COLUMN "public"."reports"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."reports"."file_type" IS '文件类型：xlsx-Excel, pdf-PDF';
COMMENT ON COLUMN "public"."reports"."file_path" IS 'MinIO文件路径';
COMMENT ON COLUMN "public"."reports"."file_size" IS '文件大小（字节）';
COMMENT ON COLUMN "public"."reports"."download_url" IS '下载URL（预签名）';
COMMENT ON COLUMN "public"."reports"."url_expires_at" IS 'URL过期时间';
COMMENT ON COLUMN "public"."reports"."checksum" IS '文件MD5校验和';
COMMENT ON COLUMN "public"."reports"."created_at" IS '创建时间';
COMMENT ON TABLE "public"."reports" IS '报表表，记录生成的报表文件';

-- ----------------------------
-- Table structure for subgraphs
-- ----------------------------
DROP TABLE IF EXISTS "public"."subgraphs";
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
  "nc_roughing_time" numeric(10,2),
  "nc_milling_time" numeric(10,2),
  "drilling_time" numeric(10,2),
  "milling_machine_time" numeric(10,2),
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
  "nc_roughing_cost" numeric(12,2),
  "nc_milling_cost" numeric(12,2),
  "drilling_cost" numeric(12,2),
  "milling_machine_cost" numeric(12,2),
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
  "small_grinding_count" int4
)
;
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
COMMENT ON COLUMN "public"."subgraphs"."nc_roughing_time" IS '开粗时间（分钟）';
COMMENT ON COLUMN "public"."subgraphs"."nc_milling_time" IS '精铣时间（分钟）';
COMMENT ON COLUMN "public"."subgraphs"."drilling_time" IS '钻孔时间（分钟）';
COMMENT ON COLUMN "public"."subgraphs"."milling_machine_time" IS '铣床时间（小时）（报表第18列）';
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
COMMENT ON COLUMN "public"."subgraphs"."nc_roughing_cost" IS 'NC开粗费用（元）（报表第30列）';
COMMENT ON COLUMN "public"."subgraphs"."nc_milling_cost" IS 'NC精铣费用（元）（报表第31列）';
COMMENT ON COLUMN "public"."subgraphs"."drilling_cost" IS '钻床费用（元）（报表第32列）';
COMMENT ON COLUMN "public"."subgraphs"."milling_machine_cost" IS '铣床费用（元）（报表第33列）';
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
COMMENT ON TABLE "public"."subgraphs" IS '子图表，存储每个子图的业务数据和成本信息';

-- ----------------------------
-- Table structure for user_interactions
-- ----------------------------
DROP TABLE IF EXISTS "public"."user_interactions";
CREATE TABLE "public"."user_interactions" (
  "interaction_id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "job_id" uuid NOT NULL,
  "card_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "card_type" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "card_data" jsonb NOT NULL,
  "user_response" jsonb,
  "action" varchar(50) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "responded_at" timestamp(6),
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'pending'::character varying
)
;
COMMENT ON COLUMN "public"."user_interactions"."interaction_id" IS '交互唯一标识UUID';
COMMENT ON COLUMN "public"."user_interactions"."job_id" IS '所属任务ID';
COMMENT ON COLUMN "public"."user_interactions"."card_id" IS '卡片ID';
COMMENT ON COLUMN "public"."user_interactions"."card_type" IS '卡片类型：missing_input-缺失输入, choice-选择, review-复核';
COMMENT ON COLUMN "public"."user_interactions"."card_data" IS '卡片数据，JSON格式';
COMMENT ON COLUMN "public"."user_interactions"."user_response" IS '用户响应数据，JSON格式';
COMMENT ON COLUMN "public"."user_interactions"."action" IS '用户操作：submit-提交, re_recognize-重新识别, skip-跳过';
COMMENT ON COLUMN "public"."user_interactions"."created_at" IS '卡片创建时间';
COMMENT ON COLUMN "public"."user_interactions"."responded_at" IS '用户响应时间';
COMMENT ON COLUMN "public"."user_interactions"."status" IS '状态：pending-待处理, responded-已响应, expired-已过期';
COMMENT ON TABLE "public"."user_interactions" IS '用户交互表，记录用户交互历史';

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS "public"."users";
CREATE TABLE "public"."users" (
  "user_id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "username" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "password_hash" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "email" varchar(100) COLLATE "pg_catalog"."default",
  "real_name" varchar(50) COLLATE "pg_catalog"."default",
  "role" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'operator'::character varying,
  "department" varchar(50) COLLATE "pg_catalog"."default",
  "is_active" bool DEFAULT true,
  "is_locked" bool DEFAULT false,
  "failed_login_attempts" int4 DEFAULT 0,
  "last_login_at" timestamp(6),
  "last_login_ip" varchar(50) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) NOT NULL DEFAULT now(),
  "updated_at" timestamp(6) NOT NULL DEFAULT now(),
  "created_by" uuid,
  "metadata" jsonb
)
;
COMMENT ON COLUMN "public"."users"."user_id" IS '用户唯一标识UUID';
COMMENT ON COLUMN "public"."users"."username" IS '用户名，唯一，用于登录';
COMMENT ON COLUMN "public"."users"."password_hash" IS '密码哈希值，使用bcrypt加密';
COMMENT ON COLUMN "public"."users"."email" IS '用户邮箱，唯一';
COMMENT ON COLUMN "public"."users"."real_name" IS '真实姓名';
COMMENT ON COLUMN "public"."users"."role" IS '用户角色：admin-管理员, operator-操作员, viewer-查看者';
COMMENT ON COLUMN "public"."users"."department" IS '所属部门';
COMMENT ON COLUMN "public"."users"."is_active" IS '账号是否激活，false表示禁用';
COMMENT ON COLUMN "public"."users"."is_locked" IS '账号是否锁定，连续登录失败会锁定';
COMMENT ON COLUMN "public"."users"."failed_login_attempts" IS '连续登录失败次数';
COMMENT ON COLUMN "public"."users"."last_login_at" IS '最后登录时间';
COMMENT ON COLUMN "public"."users"."last_login_ip" IS '最后登录IP地址';
COMMENT ON COLUMN "public"."users"."created_at" IS '账号创建时间';
COMMENT ON COLUMN "public"."users"."updated_at" IS '账号更新时间';
COMMENT ON COLUMN "public"."users"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."users"."metadata" IS '扩展元数据，JSON格式';
COMMENT ON TABLE "public"."users" IS '用户表，存储用户信息和权限';

-- ----------------------------
-- Function structure for sync_job_total_cost
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sync_job_total_cost"();
CREATE OR REPLACE FUNCTION "public"."sync_job_total_cost"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
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
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
COMMENT ON FUNCTION "public"."sync_job_total_cost"() IS '自动同步 jobs.total_cost 的触发器函数';

-- ----------------------------
-- Function structure for update_updated_at_column
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."update_updated_at_column"();
CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- View structure for v_job_details
-- ----------------------------
DROP VIEW IF EXISTS "public"."v_job_details";
CREATE VIEW "public"."v_job_details" AS  SELECT j.job_id,
    j.user_id,
    u.username,
    u.real_name,
    u.department,
    j.dwg_file_name,
    j.prt_file_name,
    j.status,
    j.current_stage,
    j.progress,
    j.total_subgraphs,
    j.total_cost,
    j.currency,
    j.created_at,
    j.updated_at,
    j.completed_at
   FROM jobs j
     LEFT JOIN users u ON j.user_id = u.user_id;

-- ----------------------------
-- View structure for v_subgraph_summary
-- ----------------------------
DROP VIEW IF EXISTS "public"."v_subgraph_summary";
CREATE VIEW "public"."v_subgraph_summary" AS  SELECT job_id,
    count(*) AS total_subgraphs,
    sum(total_cost) AS total_cost,
    sum(material_cost) AS total_material_cost,
    sum(heat_treatment_cost) AS total_heat_treatment_cost,
    sum(processing_cost_total) AS total_processing_cost,
    sum(slow_wire_cost) AS total_slow_wire_cost,
    sum(mid_wire_cost) AS total_mid_wire_cost,
    sum(fast_wire_cost) AS total_fast_wire_cost,
    sum(nc_roughing_cost + nc_milling_cost) AS total_nc_cost
   FROM subgraphs s
  GROUP BY job_id;

-- ----------------------------
-- View structure for v_job_cost_summary
-- ----------------------------
DROP VIEW IF EXISTS "public"."v_job_cost_summary";
CREATE VIEW "public"."v_job_cost_summary" AS  SELECT j.job_id,
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
    COALESCE(s.total_subgraphs, 0::bigint) AS total_subgraphs,
    COALESCE(s.total_cost, 0::numeric) AS total_cost,
    COALESCE(s.material_cost, 0::numeric) AS material_cost,
    COALESCE(s.heat_treatment_cost, 0::numeric) AS heat_treatment_cost,
    COALESCE(s.processing_cost_total, 0::numeric) AS processing_cost_total,
    COALESCE(s.nc_roughing_cost, 0::numeric) AS nc_roughing_cost,
    COALESCE(s.nc_milling_cost, 0::numeric) AS nc_milling_cost,
    COALESCE(s.drilling_cost, 0::numeric) AS drilling_cost,
    COALESCE(s.milling_machine_cost, 0::numeric) AS milling_machine_cost,
    COALESCE(s.large_grinding_cost, 0::numeric) AS large_grinding_cost,
    COALESCE(s.small_grinding_cost, 0::numeric) AS small_grinding_cost,
    COALESCE(s.slow_wire_cost, 0::numeric) AS slow_wire_cost,
    COALESCE(s.slow_wire_side_cost, 0::numeric) AS slow_wire_side_cost,
    COALESCE(s.mid_wire_cost, 0::numeric) AS mid_wire_cost,
    COALESCE(s.fast_wire_cost, 0::numeric) AS fast_wire_cost,
    COALESCE(s.edm_cost, 0::numeric) AS edm_cost,
    COALESCE(s.engraving_cost, 0::numeric) AS engraving_cost,
    COALESCE(s.separate_item_cost, 0::numeric) AS separate_item_cost,
    COALESCE(s.nc_roughing_cost, 0::numeric) + COALESCE(s.nc_milling_cost, 0::numeric) + COALESCE(s.drilling_cost, 0::numeric) AS nc_cost,
    COALESCE(s.large_grinding_cost, 0::numeric) + COALESCE(s.small_grinding_cost, 0::numeric) AS grinding_cost,
    COALESCE(s.slow_wire_cost, 0::numeric) + COALESCE(s.slow_wire_side_cost, 0::numeric) + COALESCE(s.mid_wire_cost, 0::numeric) + COALESCE(s.fast_wire_cost, 0::numeric) AS wire_cost
   FROM jobs j
     LEFT JOIN ( SELECT subgraphs.job_id,
            count(*) AS total_subgraphs,
            sum(subgraphs.total_cost) AS total_cost,
            sum(subgraphs.material_cost) AS material_cost,
            sum(subgraphs.heat_treatment_cost) AS heat_treatment_cost,
            sum(subgraphs.processing_cost_total) AS processing_cost_total,
            sum(subgraphs.nc_roughing_cost) AS nc_roughing_cost,
            sum(subgraphs.nc_milling_cost) AS nc_milling_cost,
            sum(subgraphs.drilling_cost) AS drilling_cost,
            sum(subgraphs.milling_machine_cost) AS milling_machine_cost,
            sum(subgraphs.large_grinding_cost) AS large_grinding_cost,
            sum(subgraphs.small_grinding_cost) AS small_grinding_cost,
            sum(subgraphs.slow_wire_cost) AS slow_wire_cost,
            sum(subgraphs.slow_wire_side_cost) AS slow_wire_side_cost,
            sum(subgraphs.mid_wire_cost) AS mid_wire_cost,
            sum(subgraphs.fast_wire_cost) AS fast_wire_cost,
            sum(subgraphs.edm_cost) AS edm_cost,
            sum(subgraphs.engraving_cost) AS engraving_cost,
            sum(subgraphs.separate_item_cost) AS separate_item_cost
           FROM subgraphs
          GROUP BY subgraphs.job_id) s ON j.job_id = s.job_id;
COMMENT ON VIEW "public"."v_job_cost_summary" IS '任务成本汇总视图 - 实时从 subgraphs 表计算，确保数据一致性';

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."audit_logs_audit_id_seq"
OWNED BY "public"."audit_logs"."audit_id";
SELECT setval('"public"."audit_logs_audit_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."audit_logs_audit_id_seq1"
OWNED BY "public"."audit_logs"."audit_id";
SELECT setval('"public"."audit_logs_audit_id_seq1"', 1043, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."chat_messages_message_id_seq"
OWNED BY "public"."chat_messages"."message_id";
SELECT setval('"public"."chat_messages_message_id_seq"', 8608, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."features_feature_id_seq"
OWNED BY "public"."features"."feature_id";
SELECT setval('"public"."features_feature_id_seq"', 21491, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."job_price_snapshots_snapshot_id_seq"
OWNED BY "public"."job_price_snapshots"."snapshot_id";
SELECT setval('"public"."job_price_snapshots_snapshot_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."job_price_snapshots_snapshot_id_seq1"
OWNED BY "public"."job_price_snapshots"."snapshot_id";
SELECT setval('"public"."job_price_snapshots_snapshot_id_seq1"', 94165, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."job_process_snapshots_snapshot_id_seq"
OWNED BY "public"."job_process_snapshots"."snapshot_id";
SELECT setval('"public"."job_process_snapshots_snapshot_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."job_process_snapshots_snapshot_id_seq1"
OWNED BY "public"."job_process_snapshots"."snapshot_id";
SELECT setval('"public"."job_process_snapshots_snapshot_id_seq1"', 5717, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."login_logs_log_id_seq"
OWNED BY "public"."login_logs"."log_id";
SELECT setval('"public"."login_logs_log_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."login_logs_log_id_seq1"
OWNED BY "public"."login_logs"."log_id";
SELECT setval('"public"."login_logs_log_id_seq1"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."operation_logs_log_id_seq"
OWNED BY "public"."operation_logs"."log_id";
SELECT setval('"public"."operation_logs_log_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."operation_logs_log_id_seq1"
OWNED BY "public"."operation_logs"."log_id";
SELECT setval('"public"."operation_logs_log_id_seq1"', 2206, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."price_histories_history_id_seq"
OWNED BY "public"."price_histories"."history_id";
SELECT setval('"public"."price_histories_history_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."price_histories_history_id_seq1"
OWNED BY "public"."price_histories"."history_id";
SELECT setval('"public"."price_histories_history_id_seq1"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."processing_cost_calculation_details_detail_id_seq"
OWNED BY "public"."processing_cost_calculation_details"."detail_id";
SELECT setval('"public"."processing_cost_calculation_details_detail_id_seq"', 99909, true);

-- ----------------------------
-- Indexes structure for table archives
-- ----------------------------
CREATE INDEX "idx_archives_archived_at" ON "public"."archives" USING btree (
  "archived_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_archives_job_id" ON "public"."archives" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table archives
-- ----------------------------
ALTER TABLE "public"."archives" ADD CONSTRAINT "archives_pkey" PRIMARY KEY ("archive_id");

-- ----------------------------
-- Indexes structure for table audit_logs
-- ----------------------------
CREATE INDEX "idx_audit_logs_created_at" ON "public"."audit_logs" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_audit_logs_resource" ON "public"."audit_logs" USING btree (
  "resource_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "resource_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_audit_logs_user_id" ON "public"."audit_logs" USING btree (
  "user_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table audit_logs
-- ----------------------------
ALTER TABLE "public"."audit_logs" ADD CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("audit_id");

-- ----------------------------
-- Indexes structure for table batch_recalculations
-- ----------------------------
CREATE INDEX "idx_batch_recalculations_created_at" ON "public"."batch_recalculations" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_batch_recalculations_job_id" ON "public"."batch_recalculations" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_batch_recalculations_status" ON "public"."batch_recalculations" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table batch_recalculations
-- ----------------------------
ALTER TABLE "public"."batch_recalculations" ADD CONSTRAINT "batch_recalculations_pkey" PRIMARY KEY ("batch_recalc_id");

-- ----------------------------
-- Indexes structure for table chat_messages
-- ----------------------------
CREATE INDEX "idx_chat_messages_session_id" ON "public"."chat_messages" USING btree (
  "session_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_chat_messages_timestamp" ON "public"."chat_messages" USING btree (
  "timestamp" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table chat_messages
-- ----------------------------
ALTER TABLE "public"."chat_messages" ADD CONSTRAINT "chat_messages_pkey" PRIMARY KEY ("message_id");

-- ----------------------------
-- Indexes structure for table chat_sessions
-- ----------------------------
CREATE INDEX "idx_chat_sessions_created_at" ON "public"."chat_sessions" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_chat_sessions_job_id" ON "public"."chat_sessions" USING btree (
  "job_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_chat_sessions_user_id" ON "public"."chat_sessions" USING btree (
  "user_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table chat_sessions
-- ----------------------------
ALTER TABLE "public"."chat_sessions" ADD CONSTRAINT "chat_sessions_pkey" PRIMARY KEY ("session_id");

-- ----------------------------
-- Indexes structure for table features
-- ----------------------------
CREATE INDEX "idx_feature_job_subgraph" ON "public"."features" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_feature_job_subgraph_version" ON "public"."features" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "version" "pg_catalog"."int4_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_feature_subgraph_version" ON "public"."features" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "version" "pg_catalog"."int4_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_features_auto_material" ON "public"."features" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "has_auto_material" "pg_catalog"."bool_ops" ASC NULLS LAST
) WHERE has_auto_material = true;
CREATE INDEX "idx_features_extended_features" ON "public"."features" USING gin (
  "abnormal_situation" "pg_catalog"."jsonb_ops"
);
CREATE INDEX "idx_features_heat_treatment" ON "public"."features" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "needs_heat_treatment" "pg_catalog"."bool_ops" ASC NULLS LAST
) WHERE needs_heat_treatment = true;
CREATE INDEX "idx_features_job_id" ON "public"."features" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_features_job_subgraph" ON "public"."features" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_features_nc_time_cost" ON "public"."features" USING gin (
  "nc_time_cost" "pg_catalog"."jsonb_ops"
);
CREATE INDEX "idx_features_processing_instructions" ON "public"."features" USING gin (
  "processing_instructions" "pg_catalog"."jsonb_ops"
);
CREATE INDEX "idx_features_subgraph_id" ON "public"."features" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "idx_features_subgraph_version" ON "public"."features" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "version" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_features_version" ON "public"."features" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "version" "pg_catalog"."int4_ops" DESC NULLS FIRST
);

-- ----------------------------
-- Primary Key structure for table features
-- ----------------------------
ALTER TABLE "public"."features" ADD CONSTRAINT "features_pkey" PRIMARY KEY ("feature_id");

-- ----------------------------
-- Indexes structure for table job_price_snapshots
-- ----------------------------
CREATE INDEX "idx_job_price_job_category" ON "public"."job_price_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_price_snapshots_category" ON "public"."job_price_snapshots" USING btree (
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_price_snapshots_full" ON "public"."job_price_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "sub_category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_price_snapshots_is_modified" ON "public"."job_price_snapshots" USING btree (
  "is_modified" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_price_snapshots_job_category" ON "public"."job_price_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_price_snapshots_job_id" ON "public"."job_price_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table job_price_snapshots
-- ----------------------------
ALTER TABLE "public"."job_price_snapshots" ADD CONSTRAINT "job_price_snapshots_pkey" PRIMARY KEY ("snapshot_id");

-- ----------------------------
-- Indexes structure for table job_process_snapshots
-- ----------------------------
CREATE INDEX "idx_job_process_job_feature" ON "public"."job_process_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "feature_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_process_snapshots_feature_type" ON "public"."job_process_snapshots" USING btree (
  "feature_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_process_snapshots_is_modified" ON "public"."job_process_snapshots" USING btree (
  "is_modified" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_process_snapshots_job_feature" ON "public"."job_process_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "feature_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_process_snapshots_job_id" ON "public"."job_process_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_process_snapshots_job_type" ON "public"."job_process_snapshots" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "feature_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table job_process_snapshots
-- ----------------------------
ALTER TABLE "public"."job_process_snapshots" ADD CONSTRAINT "job_process_snapshots_pkey" PRIMARY KEY ("snapshot_id");

-- ----------------------------
-- Indexes structure for table jobs
-- ----------------------------
CREATE INDEX "idx_job_id" ON "public"."jobs" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_job_status_created" ON "public"."jobs" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_jobs_created_at" ON "public"."jobs" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_jobs_status" ON "public"."jobs" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_jobs_user_id" ON "public"."jobs" USING btree (
  "user_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table jobs
-- ----------------------------
CREATE TRIGGER "update_jobs_updated_at" BEFORE UPDATE ON "public"."jobs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Checks structure for table jobs
-- ----------------------------
ALTER TABLE "public"."jobs" ADD CONSTRAINT "chk_at_least_one_file" CHECK (dwg_file_id IS NOT NULL OR prt_file_id IS NOT NULL);

-- ----------------------------
-- Primary Key structure for table jobs
-- ----------------------------
ALTER TABLE "public"."jobs" ADD CONSTRAINT "jobs_pkey" PRIMARY KEY ("job_id");

-- ----------------------------
-- Indexes structure for table login_logs
-- ----------------------------
CREATE INDEX "idx_login_logs_created_at" ON "public"."login_logs" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_login_logs_user_id" ON "public"."login_logs" USING btree (
  "user_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table login_logs
-- ----------------------------
ALTER TABLE "public"."login_logs" ADD CONSTRAINT "login_logs_pkey" PRIMARY KEY ("log_id");

-- ----------------------------
-- Indexes structure for table nc_calculations
-- ----------------------------
CREATE INDEX "idx_nc_calculations_created_at" ON "public"."nc_calculations" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_nc_calculations_job_id" ON "public"."nc_calculations" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_nc_calculations_subgraph_id" ON "public"."nc_calculations" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table nc_calculations
-- ----------------------------
ALTER TABLE "public"."nc_calculations" ADD CONSTRAINT "nc_calculations_pkey" PRIMARY KEY ("calc_id");

-- ----------------------------
-- Indexes structure for table operation_logs
-- ----------------------------
CREATE INDEX "idx_operation_logs_agent" ON "public"."operation_logs" USING btree (
  "agent" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_operation_logs_created_at" ON "public"."operation_logs" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_operation_logs_job_created" ON "public"."operation_logs" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "created_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_operation_logs_job_id" ON "public"."operation_logs" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table operation_logs
-- ----------------------------
ALTER TABLE "public"."operation_logs" ADD CONSTRAINT "operation_logs_pkey" PRIMARY KEY ("log_id");

-- ----------------------------
-- Indexes structure for table price_histories
-- ----------------------------
CREATE INDEX "idx_price_histories_created_at" ON "public"."price_histories" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_price_histories_job_id" ON "public"."price_histories" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_price_histories_subgraph_id" ON "public"."price_histories" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table price_histories
-- ----------------------------
ALTER TABLE "public"."price_histories" ADD CONSTRAINT "price_histories_pkey" PRIMARY KEY ("history_id");

-- ----------------------------
-- Indexes structure for table price_items
-- ----------------------------
CREATE INDEX "idx_price_items_sub_category" ON "public"."price_items" USING btree (
  "sub_category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_price_items_version_category" ON "public"."price_items" USING btree (
  "version_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table price_items
-- ----------------------------
CREATE TRIGGER "update_price_items_updated_at" BEFORE UPDATE ON "public"."price_items"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table price_items
-- ----------------------------
ALTER TABLE "public"."price_items" ADD CONSTRAINT "price_items_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table process_changes
-- ----------------------------
CREATE INDEX "idx_process_changes_job_id" ON "public"."process_changes" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_process_changes_subgraph_id" ON "public"."process_changes" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table process_changes
-- ----------------------------
ALTER TABLE "public"."process_changes" ADD CONSTRAINT "process_changes_pkey" PRIMARY KEY ("change_id");

-- ----------------------------
-- Indexes structure for table process_rules
-- ----------------------------
CREATE INDEX "idx_process_rules_version_feature" ON "public"."process_rules" USING btree (
  "version_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "feature_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table process_rules
-- ----------------------------
ALTER TABLE "public"."process_rules" ADD CONSTRAINT "process_rules_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table processing_cost_calculation_details
-- ----------------------------
CREATE INDEX "idx_calc_details_job_subgraph" ON "public"."processing_cost_calculation_details" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_proc_calc_calculated_at" ON "public"."processing_cost_calculation_details" USING btree (
  "calculated_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_proc_calc_job_id" ON "public"."processing_cost_calculation_details" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_proc_calc_job_subgraph" ON "public"."processing_cost_calculation_details" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_proc_calc_process_type" ON "public"."processing_cost_calculation_details" USING btree (
  "process_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_proc_calc_subgraph_id" ON "public"."processing_cost_calculation_details" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_processing_cost_job_subgraph" ON "public"."processing_cost_calculation_details" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table processing_cost_calculation_details
-- ----------------------------
ALTER TABLE "public"."processing_cost_calculation_details" ADD CONSTRAINT "processing_cost_calculation_details_job_subgraph_unique" UNIQUE ("job_id", "subgraph_id");

-- ----------------------------
-- Checks structure for table processing_cost_calculation_details
-- ----------------------------
ALTER TABLE "public"."processing_cost_calculation_details" ADD CONSTRAINT "chk_process_type" CHECK (process_type::text = ANY (ARRAY['slow_wire'::character varying, 'mid_wire'::character varying, 'fast_wire'::character varying, 'large_grinding'::character varying, 'small_grinding'::character varying, 'nc_roughing'::character varying, 'nc_milling'::character varying, 'drilling'::character varying]::text[]));

-- ----------------------------
-- Primary Key structure for table processing_cost_calculation_details
-- ----------------------------
ALTER TABLE "public"."processing_cost_calculation_details" ADD CONSTRAINT "processing_cost_calculation_details_pkey" PRIMARY KEY ("detail_id");

-- ----------------------------
-- Indexes structure for table recalculations
-- ----------------------------
CREATE INDEX "idx_recalculations_batch_id" ON "public"."recalculations" USING btree (
  "batch_recalc_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_recalculations_job_id" ON "public"."recalculations" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_recalculations_status" ON "public"."recalculations" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_recalculations_subgraph_id" ON "public"."recalculations" USING btree (
  "subgraph_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table recalculations
-- ----------------------------
ALTER TABLE "public"."recalculations" ADD CONSTRAINT "recalculations_pkey" PRIMARY KEY ("recalc_id");

-- ----------------------------
-- Indexes structure for table report_summary
-- ----------------------------
CREATE INDEX "idx_report_summary_job_id" ON "public"."report_summary" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_report_summary_report_id" ON "public"."report_summary" USING btree (
  "report_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table report_summary
-- ----------------------------
ALTER TABLE "public"."report_summary" ADD CONSTRAINT "report_summary_pkey" PRIMARY KEY ("summary_id");

-- ----------------------------
-- Indexes structure for table reports
-- ----------------------------
CREATE INDEX "idx_reports_created_at" ON "public"."reports" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_reports_job_id" ON "public"."reports" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table reports
-- ----------------------------
ALTER TABLE "public"."reports" ADD CONSTRAINT "reports_pkey" PRIMARY KEY ("report_id");

-- ----------------------------
-- Indexes structure for table subgraphs
-- ----------------------------
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

-- ----------------------------
-- Triggers structure for table subgraphs
-- ----------------------------
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

-- ----------------------------
-- Primary Key structure for table subgraphs
-- ----------------------------
ALTER TABLE "public"."subgraphs" ADD CONSTRAINT "subgraphs_pkey" PRIMARY KEY ("subgraph_id");

-- ----------------------------
-- Indexes structure for table user_interactions
-- ----------------------------
CREATE INDEX "idx_user_interactions_created_at" ON "public"."user_interactions" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_user_interactions_job_id" ON "public"."user_interactions" USING btree (
  "job_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_user_interactions_status" ON "public"."user_interactions" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table user_interactions
-- ----------------------------
ALTER TABLE "public"."user_interactions" ADD CONSTRAINT "user_interactions_pkey" PRIMARY KEY ("interaction_id");

-- ----------------------------
-- Indexes structure for table users
-- ----------------------------
CREATE INDEX "idx_users_department" ON "public"."users" USING btree (
  "department" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_email" ON "public"."users" USING btree (
  "email" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_is_active" ON "public"."users" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_role" ON "public"."users" USING btree (
  "role" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_username" ON "public"."users" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table users
-- ----------------------------
CREATE TRIGGER "update_users_updated_at" BEFORE UPDATE ON "public"."users"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_username_key" UNIQUE ("username");
ALTER TABLE "public"."users" ADD CONSTRAINT "users_email_key" UNIQUE ("email");

-- ----------------------------
-- Checks structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "chk_role" CHECK (role::text = ANY (ARRAY['admin'::character varying::text, 'operator'::character varying::text, 'viewer'::character varying::text]));

-- ----------------------------
-- Primary Key structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY ("user_id");

-- ----------------------------
-- Foreign Keys structure for table archives
-- ----------------------------
ALTER TABLE "public"."archives" ADD CONSTRAINT "archives_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table audit_logs
-- ----------------------------
ALTER TABLE "public"."audit_logs" ADD CONSTRAINT "audit_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("user_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table batch_recalculations
-- ----------------------------
ALTER TABLE "public"."batch_recalculations" ADD CONSTRAINT "batch_recalculations_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table chat_messages
-- ----------------------------
ALTER TABLE "public"."chat_messages" ADD CONSTRAINT "chat_messages_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."chat_sessions" ("session_id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table features
-- ----------------------------
ALTER TABLE "public"."features" ADD CONSTRAINT "features_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."features" ADD CONSTRAINT "features_subgraph_id_fkey" FOREIGN KEY ("subgraph_id") REFERENCES "public"."subgraphs" ("subgraph_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table job_price_snapshots
-- ----------------------------
ALTER TABLE "public"."job_price_snapshots" ADD CONSTRAINT "job_price_snapshots_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table job_process_snapshots
-- ----------------------------
ALTER TABLE "public"."job_process_snapshots" ADD CONSTRAINT "job_process_snapshots_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table jobs
-- ----------------------------
ALTER TABLE "public"."jobs" ADD CONSTRAINT "jobs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("user_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table login_logs
-- ----------------------------
ALTER TABLE "public"."login_logs" ADD CONSTRAINT "login_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("user_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table nc_calculations
-- ----------------------------
ALTER TABLE "public"."nc_calculations" ADD CONSTRAINT "nc_calculations_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table operation_logs
-- ----------------------------
ALTER TABLE "public"."operation_logs" ADD CONSTRAINT "operation_logs_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table price_histories
-- ----------------------------
ALTER TABLE "public"."price_histories" ADD CONSTRAINT "price_histories_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table process_changes
-- ----------------------------
ALTER TABLE "public"."process_changes" ADD CONSTRAINT "process_changes_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table processing_cost_calculation_details
-- ----------------------------
ALTER TABLE "public"."processing_cost_calculation_details" ADD CONSTRAINT "processing_cost_calculation_details_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."processing_cost_calculation_details" ADD CONSTRAINT "processing_cost_calculation_details_subgraph_id_fkey" FOREIGN KEY ("subgraph_id") REFERENCES "public"."subgraphs" ("subgraph_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table recalculations
-- ----------------------------
ALTER TABLE "public"."recalculations" ADD CONSTRAINT "recalculations_batch_recalc_id_fkey" FOREIGN KEY ("batch_recalc_id") REFERENCES "public"."batch_recalculations" ("batch_recalc_id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."recalculations" ADD CONSTRAINT "recalculations_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table report_summary
-- ----------------------------
ALTER TABLE "public"."report_summary" ADD CONSTRAINT "report_summary_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table reports
-- ----------------------------
ALTER TABLE "public"."reports" ADD CONSTRAINT "reports_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table subgraphs
-- ----------------------------
ALTER TABLE "public"."subgraphs" ADD CONSTRAINT "subgraphs_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table user_interactions
-- ----------------------------
ALTER TABLE "public"."user_interactions" ADD CONSTRAINT "user_interactions_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs" ("job_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users" ("user_id") ON DELETE NO ACTION ON UPDATE NO ACTION;
