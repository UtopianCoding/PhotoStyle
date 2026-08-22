-- ====================================================================
-- 迁移：新增 model_interactions 表（模型交互记录）
--
-- 用途：记录每次与 AI 图像生成模型的交互过程，包含
--       输入（原图地址、最终提示词、额外要求、重新生成意见、拍摄地点）
--       输出（结果图地址列表、服务商原始响应）
--       元数据（关联任务、耗时、成功/失败、错误信息、创建时间）
--
-- 执行方式（任选其一）：
--   A. 在 MySQL 客户端中直接执行以下 CREATE TABLE 语句
--   B. 应用启动时已通过 CREATE TABLE IF NOT EXISTS 自动建表（见 app/init_db.py）
--
--      mysql -u root -p photostyle < server/migrations/002_add_model_interactions.sql
-- ====================================================================

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
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型交互记录表';
