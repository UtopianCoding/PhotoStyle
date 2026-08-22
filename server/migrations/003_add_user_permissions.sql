-- 003: 为用户表增加权限字段（RBAC 权限码模型）
-- 新用户默认拥有基础权限；管理员可分配更多权限，不同权限看到不同页面。

ALTER TABLE `users`
  ADD COLUMN `permissions` VARCHAR(1024) NULL DEFAULT '[]' COMMENT '权限码集合(JSON数组)';

-- 为已有管理员补齐全部权限
UPDATE `users`
SET `permissions` = '["home:access","history:view","conversations:view","admin:access","admin:users","admin:config"]'
WHERE `is_admin` = 1 AND (`permissions` IS NULL OR `permissions` = '[]' OR `permissions` = '');

-- 为已有普通用户补齐默认基础权限
UPDATE `users`
SET `permissions` = '["home:access","history:view","conversations:view"]'
WHERE (`permissions` IS NULL OR `permissions` = '[]' OR `permissions` = '')
  AND `is_admin` = 0;
