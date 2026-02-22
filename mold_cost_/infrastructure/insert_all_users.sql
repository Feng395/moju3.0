-- ========================================
-- 创建系统用户（开发/测试环境）
-- ========================================
-- 默认密码: 123456
-- ⚠️  警告: 仅用于开发和测试环境！
-- ⚠️  生产环境请修改所有默认密码！
-- ========================================

-- 1. 管理员用户 (admin)
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
    '技术部',
    true,
    false,
    0,
    now(),
    now()
);

-- 2. 操作员用户 (operator)
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
    'operator',
    '$2b$12$/bOhy9e8FQXXqgPpKbsd2u3NPvUei8Arst9cYYHtHcQcJ/0/AWWL.',  -- 密码: 123456
    'operator@example.com',
    '操作员',
    'operator',
    '生产部',
    true,
    false,
    0,
    now(),
    now()
);

-- 3. 查看者用户 (viewer)
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
    'viewer',
    '$2b$12$/bOhy9e8FQXXqgPpKbsd2u3NPvUei8Arst9cYYHtHcQcJ/0/AWWL.',  -- 密码: 123456
    'viewer@example.com',
    '查看者',
    'viewer',
    '财务部',
    true,
    false,
    0,
    now(),
    now()
);

-- 4. 测试用户 (test)
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
    'test',
    '$2b$12$/bOhy9e8FQXXqgPpKbsd2u3NPvUei8Arst9cYYHtHcQcJ/0/AWWL.',  -- 密码: 123456
    'test@example.com',
    '测试用户',
    'operator',
    '测试部',
    true,
    false,
    0,
    now(),
    now()
);

-- 验证插入结果
SELECT 
    username,
    email,
    real_name,
    role,
    department,
    is_active,
    created_at
FROM "public"."users"
ORDER BY 
    CASE role
        WHEN 'admin' THEN 1
        WHEN 'operator' THEN 2
        WHEN 'viewer' THEN 3
        ELSE 4
    END,
    username;

-- ========================================
-- 用户列表
-- ========================================
-- 1. admin (管理员)
--    - 密码: 123456
--    - 权限: 所有权限
--    - 部门: 技术部
--
-- 2. operator (操作员)
--    - 密码: 123456
--    - 权限: 创建任务、上传文件、查看结果
--    - 部门: 生产部
--
-- 3. viewer (查看者)
--    - 密码: 123456
--    - 权限: 仅查看
--    - 部门: 财务部
--
-- 4. test (测试用户)
--    - 密码: 123456
--    - 权限: 操作员权限
--    - 部门: 测试部
-- ========================================

-- ========================================
-- 使用说明
-- ========================================
-- 1. 执行此SQL文件:
--    psql -h localhost -U postgres -d mold_cost -f insert_all_users.sql
--
-- 2. 登录测试:
--    curl -X POST http://localhost:8000/api/login \
--      -H "Content-Type: application/json" \
--      -d '{"username": "admin", "password": "123456"}'
--
-- 3. 修改密码:
--    POST /api/change-password
--    {
--      "new_password": "your-new-password"
--    }
--
-- 4. 删除测试用户（生产环境）:
--    DELETE FROM "public"."users" WHERE username IN ('test');
-- ========================================
