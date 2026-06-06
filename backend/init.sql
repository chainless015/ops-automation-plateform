-- 运维平台数据库表结构

-- ===== 用户管理 =====
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== 服务器管理 =====
CREATE TABLE IF NOT EXISTS servers (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) UNIQUE NOT NULL,
    ssh_port INTEGER DEFAULT 22,
    ssh_username VARCHAR(50),
    ssh_password VARCHAR(255),
    purpose VARCHAR(200),
    owner VARCHAR(50),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_servers_ip ON servers(ip_address);
CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);

-- ===== 脚本管理 =====
CREATE TABLE IF NOT EXISTS scripts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== 执行历史 =====
CREATE TABLE IF NOT EXISTS execution_history (
    id SERIAL PRIMARY KEY,
    script_id INTEGER REFERENCES scripts(id),
    server_id INTEGER REFERENCES servers(id),
    status VARCHAR(20) NOT NULL,
    return_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    duration_seconds FLOAT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    execution_type VARCHAR(20) DEFAULT 'manual'
);

CREATE INDEX IF NOT EXISTS idx_execution_server ON execution_history(server_id);
CREATE INDEX IF NOT EXISTS idx_execution_script ON execution_history(script_id);
CREATE INDEX IF NOT EXISTS idx_execution_time ON execution_history(executed_at);
CREATE INDEX IF NOT EXISTS idx_execution_finished_at ON execution_history(finished_at);
CREATE INDEX IF NOT EXISTS idx_execution_type ON execution_history(execution_type);

-- ===== 定时任务 =====
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    script_id INTEGER REFERENCES scripts(id),
    server_id INTEGER REFERENCES servers(id),
    cron_expression VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    notify_on_success BOOLEAN DEFAULT false,
    notify_on_failure BOOLEAN DEFAULT false,
    last_run_at TIMESTAMP,
    last_run_status VARCHAR(20),
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled ON scheduled_tasks(enabled);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_script ON scheduled_tasks(script_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_server ON scheduled_tasks(server_id);

-- ===== 告警人管理 =====
CREATE TABLE IF NOT EXISTS alert_contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===== 告警组管理 =====
CREATE TABLE IF NOT EXISTS alert_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES alert_groups(id) ON DELETE CASCADE,
    contact_id INTEGER NOT NULL REFERENCES alert_contacts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, contact_id)
);

-- ===== 告警规则 =====
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    server_id INTEGER REFERENCES servers(id),
    metric_type VARCHAR(50) NOT NULL,
    metric_label VARCHAR(255),
    operator VARCHAR(10) NOT NULL,
    threshold FLOAT NOT NULL,
    duration INTEGER DEFAULT 5,
    repeat_interval INTEGER DEFAULT 30,
    severity VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_server ON alert_rules(server_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled);

CREATE TABLE IF NOT EXISTS alert_rule_notifications (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES alert_contacts(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES alert_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK ((contact_id IS NOT NULL) OR (group_id IS NOT NULL))
);

-- ===== 告警记录 =====
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES alert_rules(id) ON DELETE SET NULL,
    rule_name VARCHAR(100),
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,
    metric_label VARCHAR(255),
    current_value FLOAT NOT NULL,
    threshold FLOAT NOT NULL,
    operator VARCHAR(10),
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('firing', 'resolved')),
    fired_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_occurred_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    last_notified_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_alerts_server ON alerts(server_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_fired_at ON alerts(fired_at);
CREATE INDEX IF NOT EXISTS idx_alerts_last_occurred_at ON alerts(last_occurred_at);

-- ===== 告警屏蔽 =====
CREATE TABLE IF NOT EXISTS alert_silences (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id) ON DELETE CASCADE,
    rule_id INTEGER REFERENCES alert_rules(id) ON DELETE CASCADE,
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    reason TEXT,
    silenced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_alert_silences_active ON alert_silences(is_active);
CREATE INDEX IF NOT EXISTS idx_alert_silences_expires ON alert_silences(expires_at);

-- ===== 定时任务通知 =====
CREATE TABLE IF NOT EXISTS scheduled_task_notifications (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES alert_contacts(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES alert_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK ((contact_id IS NOT NULL) OR (group_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_scheduled_task_notifications_task ON scheduled_task_notifications(task_id);

