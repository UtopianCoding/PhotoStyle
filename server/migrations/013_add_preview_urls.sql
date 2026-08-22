-- 添加 preview_urls 字段到 skill_configs 表
ALTER TABLE `skill_configs` ADD COLUMN `preview_urls` TEXT NULL COMMENT '多张预览图URL(JSON数组)';
