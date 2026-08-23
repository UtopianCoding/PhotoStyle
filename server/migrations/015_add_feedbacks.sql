-- 用户反馈与建议表
CREATE TABLE IF NOT EXISTS feedbacks (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    feedback_id   VARCHAR(64)  NOT NULL,
    user_id       VARCHAR(64)  NOT NULL,
    content       TEXT         NOT NULL,
    images        TEXT         NULL,
    status        VARCHAR(32)  NOT NULL DEFAULT 'pending',
    admin_reply   TEXT         NULL,
    replied_by    VARCHAR(64)  NULL,
    replied_at    DATETIME     NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_feedback_id (feedback_id),
    KEY idx_user_id (user_id),
    KEY idx_status (status)
);
