CREATE TABLE IF NOT EXISTS ai_user_permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL DEFAULT 0,
    username VARCHAR(64) NOT NULL DEFAULT '',
    permission_code VARCHAR(128) NOT NULL DEFAULT '',
    granted_by BIGINT NULL,
    granted_by_name VARCHAR(64) NOT NULL DEFAULT '',
    expires_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ai_user_permission_user_code (user_id, permission_code),
    INDEX idx_ai_user_permission_username (username),
    INDEX idx_ai_user_permission_code_expires (permission_code, expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
