-- 模型交互记录表新增实际请求体字段
-- 记录每次调用 Provider API 时实际发送的完整请求参数（model、size、watermark、seed、reference_images 等）
ALTER TABLE model_interactions ADD COLUMN provider_request TEXT NULL COMMENT '实际请求体JSON';
