"""
数据库初始化（开发环境便捷建表）

项目生产环境使用 Alembic 迁移（server/migrations/*.sql）；
为保障开发环境零手动操作，这里在应用启动时以 CREATE TABLE IF NOT EXISTS
方式确保 model_interactions 表存在（幂等、与迁移不冲突）。
"""

from sqlalchemy import text

from app.core.permissions import (
    ALL_PERMISSIONS,
    DEFAULT_USER_PERMISSIONS,
    serialize_permissions,
)
from app.database import engine

# model_interactions 建表语句（与 migrations/002_add_model_interactions.sql 保持一致）
_CREATE_MODEL_INTERACTIONS = """
CREATE TABLE IF NOT EXISTS `model_interactions` (
  `id`                 INT            NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `interaction_id`     VARCHAR(64)    NOT NULL                COMMENT '交互记录ID',
  `task_id`            VARCHAR(64)    NOT NULL                COMMENT '任务ID',
  `user_id`            VARCHAR(64)    NOT NULL                COMMENT '用户ID',
  `skill_id`           VARCHAR(64)    NOT NULL                COMMENT '技能ID',
  `provider`           VARCHAR(32)    NOT NULL DEFAULT 'qianwen' COMMENT 'AI提供商',
  `input_image_url`    TEXT           NOT NULL                COMMENT '输入原图地址',
  `prompt_sent`        TEXT           NOT NULL                COMMENT '实际发送给模型的提示词',
  `extra_prompt`       TEXT           NULL                    COMMENT '用户额外提示词',
  `feedback`           TEXT           NULL                    COMMENT '重新生成修改意见',
  `location`           VARCHAR(128)   NULL                    COMMENT '拍摄地点',
  `output_image_urls`  TEXT           NOT NULL                COMMENT '输出结果图地址(JSON列表)',
  `output_count`       INT            NOT NULL DEFAULT 0      COMMENT '输出结果数量',
  `provider_response`  TEXT           NULL                    COMMENT '服务商原始响应',
  `status`             VARCHAR(32)    NOT NULL DEFAULT 'success' COMMENT '交互状态',
  `error_message`      TEXT           NULL                    COMMENT '错误信息',
  `duration_ms`        INT            NULL                    COMMENT '耗时(毫秒)',
  `created_at`         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_interaction_id` (`interaction_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_task` (`task_id`),
  KEY `idx_skill` (`skill_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created` (`created_at`),
  KEY `idx_user_filter` (`user_id`, `skill_id`, `status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型交互记录表';
"""


async def ensure_model_interactions_table() -> None:
    """确保 model_interactions 表存在（幂等）"""
    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_MODEL_INTERACTIONS))

    # 确保复合索引存在（加速筛选查询）
    async with engine.begin() as conn:
        # 检查复合索引是否已存在
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'model_interactions' "
            "AND INDEX_NAME = 'idx_user_filter'"
        ))
        count = result.scalar_one()
        if count == 0:
            await conn.execute(text(
                "ALTER TABLE `model_interactions` "
                "ADD INDEX `idx_user_filter` (`user_id`, `skill_id`, `status`, `created_at`)"
            ))


# IP 贴纸相关建表语句（与 migrations/004_add_ip_sticker_tables.sql 保持一致）
_CREATE_IP_CHAT_SESSIONS = """
CREATE TABLE IF NOT EXISTS `ip_chat_sessions` (
  `id`               INT         NOT NULL AUTO_INCREMENT,
  `session_id`       VARCHAR(64) NOT NULL,
  `user_id`          VARCHAR(64) NOT NULL,
  `source_image_id`  VARCHAR(64) NULL,
  `status`           VARCHAR(32) NOT NULL DEFAULT 'awaiting_photo',
  `current_step`     INT         NOT NULL DEFAULT 0,
  `metadata_json`    TEXT        NULL,
  `created_at`       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `completed_at`     DATETIME    NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_id` (`session_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_CREATE_IP_CHAT_MESSAGES = """
CREATE TABLE IF NOT EXISTS `ip_chat_messages` (
  `id`               INT         NOT NULL AUTO_INCREMENT,
  `message_id`       VARCHAR(64) NOT NULL,
  `session_id`       VARCHAR(64) NOT NULL,
  `role`             VARCHAR(16) NOT NULL,
  `message_type`     VARCHAR(32) NOT NULL,
  `content`          TEXT        NULL,
  `images_json`      TEXT        NULL,
  `actions_json`     TEXT        NULL,
  `sequence`         INT         NOT NULL,
  `created_at`       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_message_id` (`message_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_sequence` (`session_id`, `sequence`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_CREATE_IP_MASTER_TEMPLATES = """
CREATE TABLE IF NOT EXISTS `ip_master_templates` (
  `id`                     INT         NOT NULL AUTO_INCREMENT,
  `template_id`            VARCHAR(64) NOT NULL,
  `session_id`             VARCHAR(64) NOT NULL,
  `user_id`                VARCHAR(64) NOT NULL,
  `master_image_url`       VARCHAR(512) NOT NULL,
  `master_thumbnail_url`   VARCHAR(512) NULL,
  `character_prompt`       TEXT        NOT NULL,
  `character_description`  TEXT        NULL,
  `generation_prompt`      TEXT        NOT NULL,
  `version`                INT         NOT NULL DEFAULT 1,
  `is_locked`              TINYINT(1)  NOT NULL DEFAULT 0,
  `version_history_json`   TEXT        NULL,
  `created_at`             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `locked_at`              DATETIME    NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_id` (`template_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_CREATE_IP_STICKER_RESULTS = """
CREATE TABLE IF NOT EXISTS `ip_sticker_results` (
  `id`                INT         NOT NULL AUTO_INCREMENT,
  `sticker_id`        VARCHAR(64) NOT NULL,
  `session_id`        VARCHAR(64) NOT NULL,
  `template_id`       VARCHAR(64) NOT NULL,
  `user_id`           VARCHAR(64) NOT NULL,
  `sticker_index`     INT         NOT NULL,
  `label`             VARCHAR(128) NOT NULL,
  `generation_prompt` TEXT        NOT NULL,
  `result_url`        VARCHAR(512) NOT NULL,
  `thumbnail_url`     VARCHAR(512) NULL,
  `status`            VARCHAR(32) NOT NULL DEFAULT 'pending',
  `batch_type`        VARCHAR(32) NOT NULL,
  `is_favorite`       TINYINT(1)  NOT NULL DEFAULT 0,
  `error_message`     TEXT        NULL,
  `redraw_count`      INT         NOT NULL DEFAULT 0,
  `created_at`        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sticker_id` (`sticker_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_template` (`template_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_batch` (`session_id`, `batch_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


async def ensure_ip_sticker_tables() -> None:
    """确保 IP 贴纸相关表存在（幂等）"""
    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_IP_CHAT_SESSIONS))
        await conn.execute(text(_CREATE_IP_CHAT_MESSAGES))
        await conn.execute(text(_CREATE_IP_MASTER_TEMPLATES))
        await conn.execute(text(_CREATE_IP_STICKER_RESULTS))


async def ensure_user_permissions_column() -> None:
    """
    确保 users 表存在 permissions 列（幂等）。

    生产环境使用 migrations/003_add_user_permissions.sql；
    开发环境为减少手动操作，这里在启动时：
    1. 检查 information_schema，缺列则 ALTER 添加；
    2. 为历史 NULL / 空值行初始化默认权限；管理员补齐全部权限。
    """
    async with engine.begin() as conn:
        # 1. 检查列是否存在
        check = await conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'users'
                  AND COLUMN_NAME = 'permissions'
                """
            )
        )
        exists = check.first() is not None

        # 2. 缺列则添加
        if not exists:
            await conn.execute(
                text(
                    "ALTER TABLE `users` "
                    "ADD COLUMN `permissions` VARCHAR(1024) NULL DEFAULT '[]' "
                    "COMMENT '权限码集合(JSON数组)'"
                )
            )

        # 3. 初始化默认权限（仅覆盖尚未设置的行）
        default_json = serialize_permissions(DEFAULT_USER_PERMISSIONS)
        all_json = serialize_permissions(ALL_PERMISSIONS)
        await conn.execute(
            text(
                "UPDATE `users` SET `permissions` = :p "
                "WHERE (`permissions` IS NULL OR `permissions` = '' OR `permissions` = '[]') "
                "AND `is_admin` = 0"
            ).bindparams(p=default_json)
        )
        await conn.execute(
            text(
                "UPDATE `users` SET `permissions` = :p "
                "WHERE (`permissions` IS NULL OR `permissions` = '' OR `permissions` = '[]') "
                "AND `is_admin` = 1"
            ).bindparams(p=all_json)
        )


# 积分交易记录表建表语句（与 migrations/012_add_credits_system.sql 保持一致）
_CREATE_CREDIT_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS `credit_transactions` (
  `id`                INT            NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `transaction_id`    VARCHAR(64)    NOT NULL                COMMENT '交易ID',
  `user_id`           VARCHAR(64)    NOT NULL                COMMENT '用户ID',
  `transaction_type`  VARCHAR(32)    NOT NULL                COMMENT '交易类型',
  `amount`            INT            NOT NULL                COMMENT '积分变动量',
  `balance_after`     INT            NOT NULL                COMMENT '变动后余额',
  `task_id`           VARCHAR(64)    NULL                    COMMENT '关联任务ID',
  `related_user_id`   VARCHAR(64)    NULL                    COMMENT '关联用户ID',
  `description`       TEXT           NULL                    COMMENT '交易描述',
  `created_at`        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_transaction_id` (`transaction_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_transaction_type` (`transaction_type`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分交易记录表';
"""


async def ensure_credit_transactions_table() -> None:
    """确保 credit_transactions 表存在（幂等）"""
    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_CREDIT_TRANSACTIONS))


async def ensure_user_referral_columns() -> None:
    """
    确保 users 表存在 referral_code 和 inviter_id 列（幂等）。

    生产环境使用 migrations/012_add_credits_system.sql；
    开发环境在启动时自动添加。
    """
    async with engine.begin() as conn:
        # 检查 referral_code 列
        check_referral = await conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'users'
                  AND COLUMN_NAME = 'referral_code'
                """
            )
        )
        if check_referral.first() is None:
            await conn.execute(
                text(
                    "ALTER TABLE `users` "
                    "ADD COLUMN `referral_code` VARCHAR(16) NULL UNIQUE "
                    "COMMENT '邀请码'"
                )
            )

        # 检查 inviter_id 列
        check_inviter = await conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'users'
                  AND COLUMN_NAME = 'inviter_id'
                """
            )
        )
        if check_inviter.first() is None:
            await conn.execute(
                text(
                    "ALTER TABLE `users` "
                    "ADD COLUMN `inviter_id` VARCHAR(64) NULL "
                    "COMMENT '邀请人ID'"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX `idx_inviter_id` ON `users` (`inviter_id`)"
                )
            )


# 技能配置表建表语句（数据库管理的技能配置）
_CREATE_SKILL_CONFIGS = """
CREATE TABLE IF NOT EXISTS `skill_configs` (
  `id`                INT            NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `skill_id`          VARCHAR(64)    NOT NULL                COMMENT '技能ID',
  `name`              VARCHAR(128)   NOT NULL                COMMENT '技能名称',
  `description`       TEXT           NULL                    COMMENT '技能描述',
  `prompt_template`   TEXT           NOT NULL                COMMENT '提示词模板',
  `provider`          VARCHAR(32)    NOT NULL DEFAULT 'qianwen' COMMENT 'AI提供商',
  `ratio`             VARCHAR(16)    NOT NULL DEFAULT '3:4'  COMMENT '输出比例',
  `subject_ratio`     VARCHAR(16)    NOT NULL DEFAULT '10-16%' COMMENT '主体占比',
  `category`          VARCHAR(64)    NOT NULL DEFAULT '默认' COMMENT '技能分类',
  `preview_url`       VARCHAR(512)   NULL                    COMMENT '预览图URL',
  `preview_urls`      TEXT           NULL                    COMMENT '多张预览图URL(JSON数组)',
  `is_active`         TINYINT(1)     NOT NULL DEFAULT 1      COMMENT '是否启用',
  `need_analysis`     TINYINT(1)     NOT NULL DEFAULT 1      COMMENT '是否需要图片分析',
  `sort_order`        INT            NOT NULL DEFAULT 100    COMMENT '排序权重',
  `created_at`        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_skill_id` (`skill_id`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能配置表';
"""


async def ensure_skill_configs_table() -> None:
    """确保 skill_configs 表存在（幂等）"""
    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_SKILL_CONFIGS))
        # 检查并添加 preview_urls 字段（兼容旧表）
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name='skill_configs' AND column_name='preview_urls'
        """))
        if result.scalar() == 0:
            await conn.execute(text("""
                ALTER TABLE `skill_configs`
                ADD COLUMN `preview_urls` TEXT NULL COMMENT '多张预览图URL(JSON数组)'
            """))


# 支付记录表建表语句
_CREATE_PAYMENT_RECORDS = """
CREATE TABLE IF NOT EXISTS `payment_records` (
  `id`            INT          NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `out_trade_no`  VARCHAR(64)  NOT NULL                COMMENT '商户订单号',
  `trade_no`      VARCHAR(64)  NULL                    COMMENT '支付宝交易号',
  `user_id`       VARCHAR(64)  NOT NULL                COMMENT '用户ID',
  `total_amount`  DECIMAL(10,2) NOT NULL DEFAULT 0     COMMENT '支付金额(元)',
  `credits`       INT          NOT NULL DEFAULT 0      COMMENT '购买积分数量',
  `status`        VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT '支付状态',
  `subject`       VARCHAR(256) NULL                    COMMENT '订单标题',
  `notify_data`   TEXT         NULL                    COMMENT '异步通知原始数据',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_out_trade_no` (`out_trade_no`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付记录表';
"""


async def ensure_payment_records_table() -> None:
    """确保 payment_records 表存在（幂等）"""
    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_PAYMENT_RECORDS))
