"""
后台配置管理服务

提供系统配置的读取（脱敏）与更新。
- 模型配置：持久化到数据库 + 内存缓存，运行时修改立即生效，无需重启
- 存储/应用配置：写入 .env 文件，需重启后端服务生效
"""

import logging
from pathlib import Path

from dotenv import set_key
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    PERMISSION_CATALOG,
    ROLE_PRESETS,
    normalize_permissions,
)
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
    VolcengineConfigRead,
)
from app.schemas.user import (
    PermissionCatalog,
    PermissionItem,
    RolePreset,
)
from app.services.model_config_store import model_config_store

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


def _sanitize_url(value: str | None) -> str | None:
    """清洗 URL：去除反引号、多余空白、尾部重复路径"""
    if not value:
        return value
    # 去除反引号和首尾空白
    cleaned = value.strip().strip("`").strip()
    # 去除尾部多余的斜杠
    cleaned = cleaned.rstrip("/")
    return cleaned


def _sanitize_config(config: dict) -> dict:
    """清洗配置字典中的 URL 和字符串字段"""
    for key in ("base_url", "model_image", "workspace_id", "region", "model_vision"):
        if key in config and isinstance(config[key], str):
            if key == "base_url":
                config[key] = _sanitize_url(config[key])
            else:
                config[key] = config[key].strip()
    return config


class AdminService:
    """后台配置管理服务"""

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db

    # -------------------- 读取 --------------------

    def get_config(self) -> SystemConfigRead:
        """从缓存（模型配置）+ settings（存储/应用配置）构造脱敏只读视图"""
        from app.config import settings

        return self._build_read_view(settings)

    @staticmethod
    def _build_read_view(settings) -> SystemConfigRead:
        """根据缓存 + settings 构造脱敏只读视图"""
        # 模型配置从内存缓存读取（DB 持久化，运行时可热更新）
        store = model_config_store
        qw = store.get_config("qianwen") or {}
        dl = store.get_config("dalle") or {}
        mm = store.get_config("minimax") or {}
        vc = store.get_config("volcengine") or {}

        return SystemConfigRead(
            model=ModelConfig(
                default_provider=store.get_default_provider(),
                enabled_providers=store.get_enabled_providers(),
                qianwen=DashScopeConfigRead(
                    api_key=mask_secret(qw.get("api_key", "")),
                    base_url=qw.get("base_url", "https://dashscope.aliyuncs.com/api/v1"),
                    model_vision=qw.get("model_vision", ""),
                    model_image=qw.get("model_image", ""),
                    workspace_id=qw.get("workspace_id", ""),
                    region=qw.get("region", ""),
                    watermark=qw.get("watermark"),
                    width=qw.get("width"),
                    height=qw.get("height"),
                    seed=qw.get("seed"),
                    resolution=qw.get("resolution"),
                    timeout=qw.get("timeout"),
                    # prompt_extend 默认 true：未显式配置时返回开启状态
                    prompt_extend=qw.get("prompt_extend", True),
                ),
                dalle=OpenAIConfigRead(
                    api_key=mask_secret(dl.get("api_key", "")),
                    base_url=dl.get("base_url", "https://api-direct.boft.ai/v1"),
                    model_image=dl.get("model_image", "gpt-image-2"),
                    size=dl.get("size"),
                    resolution=dl.get("resolution"),
                    quality=dl.get("quality"),
                    background=dl.get("background"),
                    output_format=dl.get("output_format"),
                    output_compression=dl.get("output_compression"),
                    moderation=dl.get("moderation"),
                ),
                minimax=MinimaxConfigRead(
                    api_key=mask_secret(mm.get("api_key", "")),
                    base_url=mm.get("base_url", ""),
                    model_image=mm.get("model_image", ""),
                    watermark=mm.get("watermark"),
                    width=mm.get("width"),
                    height=mm.get("height"),
                    seed=mm.get("seed"),
                    resolution=mm.get("resolution"),
                ),
                volcengine=VolcengineConfigRead(
                    api_key=mask_secret(vc.get("api_key", "")),
                    base_url=vc.get("base_url", ""),
                    model_image=vc.get("model_image", ""),
                    watermark=vc.get("watermark"),
                    width=vc.get("width"),
                    height=vc.get("height"),
                    seed=vc.get("seed"),
                    resolution=vc.get("resolution"),
                ),
            ),
            # 存储 / 应用配置仍从 settings（.env）读取
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
                cors_allowed_origins=settings.cors.allowed_origins_list,
                rate_limit_credit_cost_per_convert=settings.rate_limit.credit_cost_per_convert,
                access_token_expire_minutes=settings.jwt.access_token_expire_minutes,
            ),
        )

    # -------------------- 更新 --------------------

    async def update_config(self, data: SystemConfigUpdate) -> SystemConfigRead:
        """
        更新系统配置：
        - 模型配置写入 DB + 刷新内存缓存，立即生效无需重启
        - 存储/应用配置仍写入 .env，需重启后端服务生效
        """
        from app.config import settings

        env_path = str(ENV_PATH)

        if data.model is not None:
            await self._write_model(data.model)

        if data.storage is not None:
            self._write_storage(env_path, data.storage)

        if data.app is not None:
            self._write_app(env_path, data.app)

        logger.info("管理员已更新系统配置")

        # 模型配置已从缓存生效，存储/应用配置基于最新 .env 构造
        from app.config import Settings

        fresh = Settings()
        return self._build_read_view(fresh)

    # -------------------- 模型配置写入 DB --------------------

    @staticmethod
    async def _write_model(model) -> None:
        """将模型配置写入 DB 并刷新内存缓存"""
        store = model_config_store

        # 默认 provider
        if model.default_provider is not None:
            await store.save_default_provider(model.default_provider)

        # 启用 provider 列表
        if model.enabled_providers is not None:
            await store.save_enabled_providers(model.enabled_providers)

        # 千问 / DashScope
        if model.qianwen is not None:
            d = model.qianwen
            current = dict(store.get_config("qianwen") or {})
            if not _should_skip_secret(d.api_key):
                current["api_key"] = d.api_key
            if d.base_url is not None:
                current["base_url"] = d.base_url
            if d.model_vision is not None:
                current["model_vision"] = d.model_vision
            if d.model_image is not None:
                current["model_image"] = d.model_image
            if d.workspace_id is not None:
                current["workspace_id"] = d.workspace_id
            if d.region is not None:
                current["region"] = d.region
            # 原可选字段：仅在传值时写入，None 视为"不修改"
            if d.watermark is not None:
                current["watermark"] = d.watermark
            if d.width is not None:
                current["width"] = d.width
            if d.height is not None:
                current["height"] = d.height
            if d.seed is not None:
                current["seed"] = d.seed
            if d.resolution is not None:
                current["resolution"] = d.resolution.strip()
            # timeout：传 0 或 None 则删除字段（恢复默认 300），否则写入
            if d.timeout:  # > 0 才写入
                if d.timeout < 30:
                    raise ValueError("千问 timeout 必须 >= 30 秒")
                current["timeout"] = d.timeout
            elif "timeout" in current:
                del current["timeout"]
            # prompt_extend：始终覆盖写入（前端必发 true/false）
            if d.prompt_extend is not None:
                current["prompt_extend"] = bool(d.prompt_extend)
            await store.save_provider_config("qianwen", _sanitize_config(current))

        # OpenAI / GPT Image 2
        if model.dalle is not None:
            o = model.dalle
            current = dict(store.get_config("dalle") or {})
            if not _should_skip_secret(o.api_key):
                current["api_key"] = o.api_key
            if o.base_url is not None:
                current["base_url"] = o.base_url
            if o.model_image is not None:
                current["model_image"] = o.model_image
            # GPT Image 2 特有参数
            if o.size is not None:
                current["size"] = o.size
            if o.resolution is not None:
                current["resolution"] = o.resolution
            if o.quality is not None:
                current["quality"] = o.quality
            if o.background is not None:
                current["background"] = o.background
            if o.output_format is not None:
                current["output_format"] = o.output_format
            if o.output_compression is not None:
                current["output_compression"] = o.output_compression
            if o.moderation is not None:
                current["moderation"] = o.moderation
            await store.save_provider_config("dalle", _sanitize_config(current))

        # MiniMax
        if model.minimax is not None:
            m = model.minimax
            current = dict(store.get_config("minimax") or {})
            if not _should_skip_secret(m.api_key):
                current["api_key"] = m.api_key
            if m.base_url is not None:
                current["base_url"] = m.base_url
            if m.model_image is not None:
                current["model_image"] = m.model_image
            if m.watermark is not None:
                current["watermark"] = m.watermark
            if m.width is not None:
                current["width"] = m.width
            if m.height is not None:
                current["height"] = m.height
            if m.seed is not None:
                current["seed"] = m.seed
            if m.resolution is not None:
                current["resolution"] = m.resolution.strip()
            await store.save_provider_config("minimax", _sanitize_config(current))

        # 火山引擎（Seedream）
        if model.volcengine is not None:
            v = model.volcengine
            current = dict(store.get_config("volcengine") or {})
            if not _should_skip_secret(v.api_key):
                current["api_key"] = v.api_key
            if v.base_url is not None:
                current["base_url"] = v.base_url
            if v.model_image is not None:
                current["model_image"] = v.model_image
            if v.watermark is not None:
                current["watermark"] = v.watermark
            if v.width is not None:
                current["width"] = v.width
            if v.height is not None:
                current["height"] = v.height
            if v.seed is not None:
                current["seed"] = v.seed
            if v.resolution is not None:
                current["resolution"] = v.resolution.strip()
            await store.save_provider_config("volcengine", _sanitize_config(current))

    # -------------------- 存储/应用配置写入 .env --------------------

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
        if app.rate_limit_credit_cost_per_convert is not None:
            set_key(env_path, "RATE_LIMIT_CREDIT_COST_PER_CONVERT", str(app.rate_limit_credit_cost_per_convert))
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
            avatar_url=user.avatar_url,
            status=user.status,
            is_admin=user.is_admin,
            permissions=normalize_permissions(user.permissions),
            credits=user.credits,
            usage_today=user.usage_today,
            usage_limit=user.usage_limit,
            created_at=created_at.isoformat() if created_at else None,
        )

    @staticmethod
    def get_permission_catalog() -> PermissionCatalog:
        """返回权限目录（权限项 + 角色预设），用于前端渲染分配界面"""
        permissions = [
            PermissionItem(
                code=p.code, label=p.label, group=p.group, description=p.description
            )
            for p in PERMISSION_CATALOG
        ]
        role_presets = [
            RolePreset(
                key=key,
                label=val["label"],
                permissions=list(val["permissions"]),
                is_admin=val.get("is_admin", False),
            )
            for key, val in ROLE_PRESETS.items()
        ]
        return PermissionCatalog(permissions=permissions, role_presets=role_presets)
