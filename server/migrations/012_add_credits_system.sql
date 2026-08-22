-- 积分系统迁移脚本
-- 1. 创建积分交易记录表
-- 2. 给 users 表添加 referral_code 和 inviter_id 字段

-- 创建积分交易记录表
CREATE TABLE IF NOT EXISTS credit_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(64) NOT NULL,
    transaction_type VARCHAR(32) NOT NULL,
    amount INT NOT NULL,
    balance_after INT NOT NULL,
    task_id VARCHAR(64),
    related_user_id VARCHAR(64),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_credit_transactions_user_id (user_id),
    INDEX idx_credit_transactions_transaction_type (transaction_type),
    INDEX idx_credit_transactions_transaction_id (transaction_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 给 users 表添加邀请码字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(16) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS inviter_id VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_users_inviter_id ON users(inviter_id);
