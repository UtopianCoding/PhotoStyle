-- ============================================================
-- 014: 新增 provider_configs 表
-- 将 AI 模型 Provider 配置持久化到数据库，支持运行时动态修改
-- ============================================================

CREATE TABLE IF NOT EXISTS `provider_configs` (
  `id`            INT          NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `provider_id`   VARCHAR(32)  NOT NULL                COMMENT 'Provider唯一标识',
  `config_json`   TEXT         NOT NULL                COMMENT '配置内容(JSON)',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_provider_id` (`provider_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Provider配置表';
