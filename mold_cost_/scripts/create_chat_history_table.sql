-- 聊天会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',  -- active, archived
    metadata JSONB  -- 存储额外信息（如文件名、任务信息等）
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_chat_sessions_job_id ON chat_sessions(job_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);

-- 聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,  -- 存储额外信息（如文件信息、修改记录等）
    
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp);

-- 添加注释
COMMENT ON TABLE chat_sessions IS '聊天会话表，记录每个审核任务的会话';
COMMENT ON TABLE chat_messages IS '聊天消息表，记录会话中的所有消息';

COMMENT ON COLUMN chat_sessions.session_id IS '会话ID，通常与job_id相同';
COMMENT ON COLUMN chat_sessions.job_id IS '关联的任务ID';
COMMENT ON COLUMN chat_sessions.user_id IS '用户ID';
COMMENT ON COLUMN chat_sessions.metadata IS '额外信息，如文件名、任务描述等';

COMMENT ON COLUMN chat_messages.role IS '消息角色：user(用户), assistant(AI助手), system(系统)';
COMMENT ON COLUMN chat_messages.content IS '消息内容';
COMMENT ON COLUMN chat_messages.metadata IS '额外信息，如修改记录、文件信息等';
