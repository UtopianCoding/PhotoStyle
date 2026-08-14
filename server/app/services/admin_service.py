"""
后台配置管理服务

提供系统配置的读取（脱敏）与更新（写入 .env 文件）。

模型配置按 provider 分组（dashscope / openai / minimax），存储配置按 storage_type 分组（minio / oss）。
生效方式：写入 .env 后，需重启后端服务才能让新配置生效（不做内存热更新，更安全）。
"""

import logging
from pathlib import Path

from dotenv import set_key

from app.schemas.admin import (
    AdminUserItem,
    AppConfigRead,
    DashScopeConfigRead,
    MinIOConfigRead,
    MinimaxConfigRead,
    ModelConfig,
    OSSConfigRead,
    OpenAIConfigRead,
    StorageConfig,
    SystemConfigRead,
    SystemConfigUpdate,
)

logger = logging.getLogger(__name__)

# .env 文件路径：server/app/services/admin_service.py → parents[2] = server/
ENV_PATH: Path = Path(__file__).resolve().parents[2] / ".env"

# 敏感字段脱敏标识，用于识别前端回传的"未修改"敏感字段
_MASK_TOKEN = "****"


def mask_secret(value: str) -> str:
    """
    脱敏处理：保留前 4 + 后 4，中间替换为 ****。
    过短或为空时返回空串，避免泄露长度信息。
    """
    if not value:
        return ""
    if len(value) <= 8:
        return _MASK_TOKEN
    return f"{value[:4]}{_MASK_TOKEN}{value[-4:]}"


def _should_skip_secret(value: str | None) -> bool:
    """判断敏感字段是否应跳过写入（值为空或仍为脱敏形态）"""
    if value is None:
        return True
    if value == "":
        return True
    return _MASK_TOKEN in value


class AdminService:
    """后台配置管理服务"""

    # -------------------- 读取 --------------------

    def get_config(self) -> SystemConfigRead:
        """从 settings 单例读取当前配置，敏感字段脱敏后返回"""
        from app.config import settings

        return self._build_read_view(settings)

    @staticmethod
    def _build_read_view(settings) -> SystemConfigRead:
        """根据 settings 构造脱敏只读视图"""
        return SystemConfigRead(
            model=ModelConfig(
                default_provider=settings.model.default_provider,
                qianwen=DashScopeConfigRead(
                    api_key=mask_secret(settings.dashscope.api_key.get_secret_value()),
                    model_vision=settings.dashscope.model_vision,
                    model_image=settings.dashscope.model_image,
                    workspace_id=settings.dashscope.workspace_id,
                    region=settings.dashscope.region,
                ),
                dalle=OpenAIConfigRead(
                    api_key=mask_secret(settings.dalle.api_key.get_secret_value()),
                    base_url=settings.dalle.base_url,
                    model_image=settings.dalle.model_image,
                ),
                minimax=MinimaxConfigRead(
                    api_key=mask_secret(settings.minimax.api_key.get_secret_value()),
                    base_url=settings.minimax.base_url,
                    model_image=settings.minimax.model_image,
                ),
            ),
            storage=StorageConfig(
                storage_type=settings.storage.type,
                minio=MinIOConfigRead(
                    endpoint=settings.minio.endpoint,
                    access_key=mask_secret(settings.minio.access_key.get_secret_value()),
                    secret_key=mask_secret(settings.minio.secret_key.get_secret_value()),
                    bucket=settings.minio.bucket,
                    secure=settings.minio.secure,
                    public_base_url=settings.minio.public_base_url,
                ),
                oss=OSSConfigRead(
                    access_key_id=mask_secret(settings.oss.access_key_id.get_secret_value()),
                    access_key_secret=mask_secret(settings.oss.access_key_secret.get_secret_value()),
                    bucket=settings.oss.bucket,
                    endpoint=settings.oss.endpoint,
                ),
            ),
            app=AppConfigRead(
                log_level=settings.logging.level,
                cors_allowed_origins=list(settings.cors.allowed_origins),
                rate_limit_free_user_daily_limit=settings.rate_limit.free_user_daily_limit,
                access_token_expire_minutes=settings.jwt.access_token_expire_minutes,
            ),
        )

    # -------------------- 更新 --------------------

    def update_config(self, data: SystemConfigUpdate) -> SystemConfigRead:
        """
        将更新写入 .env 文件。

        - 敏感字段（API Key / Secret）若仍为脱敏形态则跳过，避免覆盖为脏值
        - 列表类型字段（CORS 来源）以英文逗号拼接
        - 布尔类型字段（MINIO_SECURE）转为 'true' / 'false'
        - 写入后重新读取 settings（单例不重建，仅返回最新 .env 内容的脱敏视图）

        注意：内存中的 settings 单例不会自动更新，需重启后端服务生效。
        """
        env_path = str(ENV_PATH)

        if data.model is not None:
            self._write_model(env_path, data.model)

        if data.storage is not None:
            self._write_storage(env_path, data.storage)

        if data.app is not None:
            self._write_app(env_path, data.app)

        logger.info("管理员已更新系统配置，需重启后端服务使新配置生效")

        # 重新读取（基于最新 .env 文件构造新 Settings，避免返回脏数据）
        from app.config import Settings

        fresh = Settings()
        return self._build_read_view(fresh)

    # -------------------- 写入分组 --------------------

    @staticmethod
    def _write_model(env_path: str, model) -> None:
        # 默认 provider
        if model.default_provider is not None:
            set_key(env_path, "MODEL_DEFAULT_PROVIDER", model.default_provider)

        # 千问 / DashScope
        if model.qianwen is not None:
            d = model.qianwen
            if not _should_skip_secret(d.api_key):
                set_key(env_path, "DASHSCOPE_API_KEY", d.api_key)
            if d.model_vision is not None:
                set_key(env_path, "DASHSCOPE_MODEL_VISION", d.model_vision)
            if d.model_image is not None:
                set_key(env_path, "DASHSCOPE_MODEL_IMAGE", d.model_image)
            if d.workspace_id is not None:
                set_key(env_path, "DASHSCOPE_WORKSPACE_ID", d.workspace_id)
            if d.region is not None:
                set_key(env_path, "DASHSCOPE_REGION", d.region)

        # OpenAI / DALL-E
        if model.dalle is not None:
            o = model.dalle
            if not _should_skip_secret(o.api_key):
                set_key(env_path, "DALLE_API_KEY", o.api_key)
            if o.base_url is not None:
                set_key(env_path, "DALLE_BASE_URL", o.base_url)
            if o.model_image is not None:
                set_key(env_path, "DALLE_MODEL_IMAGE", o.model_image)

        # MiniMax
        if model.minimax is not None:
            m = model.minimax
            if not _should_skip_secret(m.api_key):
                set_key(env_path, "MINIMAX_API_KEY", m.api_key)
            if m.base_url is not None:
                set_key(env_path, "MINIMAX_BASE_URL", m.base_url)
            if m.model_image is not None:
                set_key(env_path, "MINIMAX_MODEL_IMAGE", m.model_image)

    @staticmethod
    def _write_storage(env_path: str, storage) -> None:
        if storage.storage_type is not None:
            set_key(env_path, "STORAGE_TYPE", storage.storage_type)

        # MinIO
        if storage.minio is not None:
            mn = storage.minio
            if mn.endpoint is not None:
                set_key(env_path, "MINIO_ENDPOINT", mn.endpoint)
            if not _should_skip_secret(mn.access_key):
                set_key(env_path, "MINIO_ACCESS_KEY", mn.access_key)
            if not _should_skip_secret(mn.secret_key):
                set_key(env_path, "MINIO_SECRET_KEY", mn.secret_key)
            if mn.bucket is not None:
                set_key(env_path, "MINIO_BUCKET", mn.bucket)
            if mn.secure is not None:
                set_key(env_path, "MINIO_SECURE", "true" if mn.secure else "false")
            if mn.public_base_url is not None:
                set_key(env_path, "MINIO_PUBLIC_BASE_URL", mn.public_base_url)

        # OSS
        if storage.oss is not None:
            os_ = storage.oss
            if not _should_skip_secret(os_.access_key_id):
                set_key(env_path, "OSS_ACCESS_KEY_ID", os_.access_key_id)
            if not _should_skip_secret(os_.access_key_secret):
                set_key(env_path, "OSS_ACCESS_KEY_SECRET", os_.access_key_secret)
            if os_.bucket is not None:
                set_key(env_path, "OSS_BUCKET", os_.bucket)
            if os_.endpoint is not None:
                set_key(env_path, "OSS_ENDPOINT", os_.endpoint)

    @staticmethod
    def _write_app(env_path: str, app) -> None:
        if app.log_level is not None:
            set_key(env_path, "LOG_LEVEL", app.log_level)
        if app.cors_allowed_origins is not None:
            set_key(env_path, "CORS_ALLOWED_ORIGINS", ",".join(app.cors_allowed_origins))
        if app.rate_limit_free_user_daily_limit is not None:
            set_key(env_path, "RATE_LIMIT_FREE_USER_DAILY_LIMIT", str(app.rate_limit_free_user_daily_limit))
        if app.access_token_expire_minutes is not None:
            set_key(env_path, "ACCESS_TOKEN_EXPIRE_MINUTES", str(app.access_token_expire_minutes))

    # -------------------- 用户列表 --------------------

    @staticmethod
    def to_admin_user_item(user) -> AdminUserItem:
        """User 模型转管理员视角的用户列表项"""
        created_at = user.created_at
        return AdminUserItem(
            user_id=user.user_id,
            email=user.email,
            nickname=user.nickname,
            status=user.status,
            is_admin=user.is_admin,
            credits=user.credits,
            usage_today=user.usage_today,
            usage_limit=user.usage_limit,
            created_at=created_at.isoformat() if created_at else None,
        )
