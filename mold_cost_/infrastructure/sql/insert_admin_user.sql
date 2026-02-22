-- ========================================
-- 创建管理员用户
-- ========================================
-- 用户名: admin
-- 密码: 123456
-- 角色: admin (管理员)
-- ⚠️  警告: 请在生产环境中修改默认密码！
-- ========================================

-- 插入管理员用户
INSERT INTO "public"."users" (
    "user_id",
    "username",
    "password_hash",
    "email",
    "real_name",
    "role",
    "department",
    "is_active",
    "is_locked",
    "failed_login_attempts",
    "created_at",
    "updated_at"
) VALUES (
    gen_random_uuid(),
    'admin',
    '$2b$12$/bOhy9e8FQXXqgPpKbsd2u3NPvUei8Arst9cYYHtHcQcJ/0/AWWL.',  -- 密码: 123456
    'admin@example.com',
    '系统管理员',
    'admin',
    NULL,
    true,
    false,
    0,
    now(),
    now()
);

-- 验证插入
SELECT 
    user_id,
    username,
    email,
    real_name,
    role,
    is_active,
    created_at
FROM "public"."users"
WHERE username = 'admin';

-- ========================================
-- 使用说明
-- ========================================
-- 1. 执行此SQL文件:
--    psql -h localhost -U postgres -d mold_cost -f insert_admin_user.sql
--
-- 2. 登录系统:
--    用户名: admin
--    密码: 123456
--
-- 3. 修改密码:
--    登录后在系统中修改密码
--    或使用 API: POST /api/change-password
-- ========================================
