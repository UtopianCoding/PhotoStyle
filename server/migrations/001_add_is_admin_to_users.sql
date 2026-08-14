-- ====================================================================
-- 迁移：users 表新增 is_admin 字段（后台配置功能权限控制）
--
-- 执行方式：
--   mysql -u root -p photostyle < server/migrations/001_add_is_admin_to_users.sql
-- 或在 MySQL 客户端中直接执行以下语句
--
-- 执行后：将某个用户指定为管理员（替换邮箱为实际管理员邮箱）
-- ====================================================================

-- 1. 新增 is_admin 字段（TINYINT(1)，默认 0 = 非管理员）
ALTER TABLE `users`
  ADD COLUMN `is_admin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否管理员' AFTER `status`;

-- 2. 指定管理员（将下方邮箱替换为实际管理员邮箱后取消注释执行）
-- UPDATE `users` SET `is_admin` = 1 WHERE `email` = 'admin@example.com';

-- 3. 验证
-- SELECT id, user_id, email, nickname, is_admin FROM `users`;
