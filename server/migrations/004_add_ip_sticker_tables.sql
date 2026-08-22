-- 004: IP 贴纸聊天功能
-- 新增 4 张表：ip_chat_sessions, ip_chat_messages, ip_master_templates, ip_sticker_results

CREATE TABLE IF NOT EXISTS `ip_chat_sessions` (
  `id`               INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `session_id`       VARCHAR(64) NOT NULL                COMMENT '会话ID',
  `user_id`          VARCHAR(64) NOT NULL                COMMENT '用户ID',
  `source_image_id`  VARCHAR(64) NULL                    COMMENT '源图片ID',
  `status`           VARCHAR(32) NOT NULL DEFAULT 'awaiting_photo' COMMENT '状态',
  `current_step`     INT         NOT NULL DEFAULT 0      COMMENT '当前步骤号',
  `metadata_json`    TEXT        NULL                    COMMENT '扩展元数据JSON',
  `created_at`       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `completed_at`     DATETIME    NULL                    COMMENT '完成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_id` (`session_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IP贴纸聊天会话表';

CREATE TABLE IF NOT EXISTS `ip_chat_messages` (
  `id`               INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `message_id`       VARCHAR(64) NOT NULL                COMMENT '消息ID',
  `session_id`       VARCHAR(64) NOT NULL                COMMENT '会话ID',
  `role`             VARCHAR(16) NOT NULL                COMMENT '消息角色',
  `message_type`     VARCHAR(32) NOT NULL                COMMENT '消息类型',
  `content`          TEXT        NULL                    COMMENT '文本内容',
  `images_json`      TEXT        NULL                    COMMENT '图片内容JSON',
  `actions_json`     TEXT        NULL                    COMMENT '操作指令JSON',
  `sequence`         INT         NOT NULL                COMMENT '排序序号',
  `created_at`       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_message_id` (`message_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_sequence` (`session_id`, `sequence`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IP贴纸聊天消息表';

CREATE TABLE IF NOT EXISTS `ip_master_templates` (
  `id`                     INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `template_id`            VARCHAR(64) NOT NULL                COMMENT '母版ID',
  `session_id`             VARCHAR(64) NOT NULL                COMMENT '会话ID',
  `user_id`                VARCHAR(64) NOT NULL                COMMENT '用户ID',
  `master_image_url`       VARCHAR(512) NOT NULL               COMMENT '母版图URL',
  `master_thumbnail_url`   VARCHAR(512) NULL                   COMMENT '母版缩略图URL',
  `character_prompt`       TEXT        NOT NULL                COMMENT '角色特征英文提示词',
  `character_description`  TEXT        NULL                    COMMENT '角色特征中文描述',
  `generation_prompt`      TEXT        NOT NULL                COMMENT '完整生成提示词',
  `version`                INT         NOT NULL DEFAULT 1      COMMENT '版本号',
  `is_locked`              TINYINT(1)  NOT NULL DEFAULT 0      COMMENT '是否已锁定',
  `version_history_json`   TEXT        NULL                    COMMENT '历史版本URL数组',
  `created_at`             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `locked_at`              DATETIME    NULL                    COMMENT '锁定时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_id` (`template_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IP母版表';

CREATE TABLE IF NOT EXISTS `ip_sticker_results` (
  `id`                INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `sticker_id`        VARCHAR(64) NOT NULL                COMMENT '贴纸ID',
  `session_id`        VARCHAR(64) NOT NULL                COMMENT '会话ID',
  `template_id`       VARCHAR(64) NOT NULL                COMMENT '母版ID',
  `user_id`           VARCHAR(64) NOT NULL                COMMENT '用户ID',
  `sticker_index`     INT         NOT NULL                COMMENT '贴纸序号',
  `label`             VARCHAR(128) NOT NULL               COMMENT '表情/姿态描述',
  `generation_prompt` TEXT        NOT NULL                COMMENT '生成提示词',
  `result_url`        VARCHAR(512) NOT NULL               COMMENT '贴纸图片URL',
  `thumbnail_url`     VARCHAR(512) NULL                   COMMENT '缩略图URL',
  `status`            VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '状态',
  `batch_type`        VARCHAR(32) NOT NULL                COMMENT '批次类型',
  `is_favorite`       TINYINT(1)  NOT NULL DEFAULT 0      COMMENT '是否收藏',
  `error_message`     TEXT        NULL                    COMMENT '错误信息',
  `redraw_count`      INT         NOT NULL DEFAULT 0      COMMENT '重绘次数',
  `created_at`        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sticker_id` (`sticker_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_template` (`template_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_batch` (`session_id`, `batch_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IP贴纸结果表';
