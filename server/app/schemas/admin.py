"""
后台配置管理 Schema

定义模型、存储、应用配置的读取（脱敏）与更新（可选字段）模型。
模型配置按 provider 分组（dashscope / openai / minimax），存储配置按 storage_type 分组（minio / oss）。
所有响应字段使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ============================================================
# 模型配置 - 读取（脱敏）
# ============================================================
class DashScopeConfigRead(BaseModel):
    """千问 / DashScope 配置（脱敏）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    api_key: str = Field("", description="API Key（脱敏）")
    base_url: str = Field("https://dashscope.aliyuncs.com/api/v1", description="API 基础地址")
    model_vision: str
    model_image: str
    workspace_id: str
    region: str
    watermark: bool | None = Field(None, description="是否添加水印（None=不设置）")
    width: int | None = Field(None, description="图片宽度（像素），为空时不设置")
    height: int | None = Field(None, description="图片高度（像素），为空时不设置")
    seed: int | None = Field(None, description="随机数种子，为空时使用随机种子")
    resolution: str | None = Field(None, description="分辨率（如 1024*1024），优先于宽高")
    timeout: int | None = Field(
        None,
        description="单次调用超时（秒），为空时使用默认值 300",
    )
    prompt_extend: bool | None = Field(
        None,
        description="是否启用提示词自动扩展（None=使用默认 true）",
    )


class OpenAIConfigRead(BaseModel):
    """OpenAI / GPT Image 2 配置（脱敏）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    api_key: str = Field("", description="API Key（脱敏）")
    base_url: str = Field("https://api-direct.boft.ai/v1", description="API 基础地址")
    model_image: str = Field("gpt-image-2", description="图像生成模型名")
    size: str | None = Field(None, description="图片尺寸（auto/比例格式/像素格式）")
    resolution: str | None = Field(None, description="分辨率档位（1K/2K/4K），仅在 size 为比例格式时生效")
    quality: str | None = Field(None, description="渲染质量（low/medium/high）")
    background: str | None = Field(None, description="背景类型（auto/transparent/opaque）")
    output_format: str | None = Field(None, description="输出格式（png/jpeg/webp）")
    output_compression: int | None = Field(None, description="输出压缩率（0-100）")
    moderation: str | None = Field(None, description="内容审核级别（auto/low）")


class MinimaxConfigRead(BaseModel):
    """MiniMax 配置（脱敏）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    api_key: str = Field("", description="API Key（脱敏）")
    base_url: str
    model_image: str
    watermark: bool | None = Field(None, description="是否添加 AI 水印（None=不设置）")
    width: int | None = Field(None, description="图片宽度（像素，512-2048 且为 8 的倍数），为空时不设置")
    height: int | None = Field(None, description="图片高度（像素，512-2048 且为 8 的倍数），为空时不设置")
    seed: int | None = Field(None, description="随机数种子，为空时使用随机种子")
    resolution: str | None = Field(None, description="分辨率（如 1024*1024），优先于宽高")


class VolcengineConfigRead(BaseModel):
    """火山引擎（Seedream）配置（脱敏）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    api_key: str = Field("", description="API Key（脱敏）")
    base_url: str
    model_image: str
    watermark: bool | None = Field(None, description="是否添加 AI 水印（None=不设置）")
    width: int | None = Field(None, description="图片宽度（像素），为空时不设置")
    height: int | None = Field(None, description="图片高度（像素），为空时不设置")
    seed: int | None = Field(None, description="随机数种子，为空时使用随机种子")
    resolution: str | None = Field(None, description="分辨率（如 1024*1024），优先于宽高")


class GeminiConfigRead(BaseModel):
    """Gemini 配置（脱敏）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    api_key: str = Field("", description="API Key（脱敏）")
    base_url: str
    model_image: str
    width: int | None = Field(None, description="图片宽度（像素），为空时不设置")
    height: int | None = Field(None, description="图片高度（像素），为空时不设置")
    seed: int | None = Field(None, description="随机数种子，为空时使用随机种子")
    resolution: str | None = Field(None, description="分辨率（如 1024*1024），优先于宽高")
    aspect_ratio: str | None = Field(None, description="输出比例（如 1:1 / 3:4 / 16:9），Gemini imageConfig.aspectRatio")
    image_size: str | None = Field(None, description="输出尺寸档位（1K/2K/4K），Gemini imageConfig.imageSize")


class VisionConfigRead(BaseModel):
    """视觉理解模型配置（脱敏，独立于图像生成模型）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    enabled: bool = Field(True, description="是否启用视觉理解")
    api_key: str = Field("", description="API Key（脱敏）")
    base_url: str = Field("", description="API 基础地址")
    model_vision: str = Field("", description="视觉理解模型名（如 qwen3-vl-flash）")


class ModelConfig(BaseModel):
    """模型配置（聚合多 provider + 默认路由）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    # 默认图像生成 Provider ID：qianwen / dalle / minimax / volcengine
    default_provider: str
    # 启用的 Provider 列表（多模型并行转换）
    enabled_providers: list[str] = Field(default_factory=lambda: ["qianwen"], description="启用的 Provider ID 列表")
    # 千问配置（provider_id=qianwen）
    qianwen: DashScopeConfigRead
    # OpenAI 配置（provider_id=dalle）
    dalle: OpenAIConfigRead
    # MiniMax 配置（provider_id=minimax）
    minimax: MinimaxConfigRead
    # 火山引擎配置（provider_id=volcengine）
    volcengine: VolcengineConfigRead
    # Gemini 配置（provider_id=gemini）
    gemini: GeminiConfigRead
    # 视觉理解模型配置（独立于图像生成）
    vision: VisionConfigRead


# ============================================================
# 存储配置 - 读取（脱敏）
# ============================================================
class MinIOConfigRead(BaseModel):
    """MinIO 配置（脱敏）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    endpoint: str
    access_key: str = Field("", description="Access Key（脱敏）")
    secret_key: str = Field("", description="Secret Key（脱敏）")
    bucket: str
    secure: bool
    public_base_url: str


class OSSConfigRead(BaseModel):
    """阿里云 OSS 配置（脱敏）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    access_key_id: str = Field("", description="Access Key ID（脱敏）")
    access_key_secret: str = Field("", description="Access Key Secret（脱敏）")
    bucket: str
    endpoint: str


class StorageConfig(BaseModel):
    """存储配置（按 storage_type 切换使用 minio 或 oss）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    # 存储类型：minio / oss
    storage_type: str
    # MinIO 配置
    minio: MinIOConfigRead
    # OSS 配置
    oss: OSSConfigRead


class AppConfigRead(BaseModel):
    """应用配置"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    log_level: str
    cors_allowed_origins: list[str]
    rate_limit_credit_cost_per_convert: int
    access_token_expire_minutes: int


class SystemConfigRead(BaseModel):
    """系统配置只读视图（聚合三组配置）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    model: ModelConfig
    storage: StorageConfig
    app: AppConfigRead


# ============================================================
# 更新模型（所有字段可选，仅传入需修改的字段）
# ============================================================
class DashScopeConfigUpdate(BaseModel):
    """千问配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    api_key: str | None = None
    base_url: str | None = None
    model_vision: str | None = None
    model_image: str | None = None
    workspace_id: str | None = None
    region: str | None = None
    watermark: bool | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = None
    resolution: str | None = None
    timeout: int | None = None
    prompt_extend: bool | None = None


class OpenAIConfigUpdate(BaseModel):
    """OpenAI / GPT Image 2 配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    api_key: str | None = None
    base_url: str | None = None
    model_image: str | None = None
    size: str | None = None
    resolution: str | None = None
    quality: str | None = None
    background: str | None = None
    output_format: str | None = None
    output_compression: int | None = None
    moderation: str | None = None


class MinimaxConfigUpdate(BaseModel):
    """MiniMax 配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    api_key: str | None = None
    base_url: str | None = None
    model_image: str | None = None
    watermark: bool | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = None
    resolution: str | None = None


class VolcengineConfigUpdate(BaseModel):
    """火山引擎（Seedream）配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    api_key: str | None = None
    base_url: str | None = None
    model_image: str | None = None
    watermark: bool | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = None
    resolution: str | None = None


class GeminiConfigUpdate(BaseModel):
    """Gemini 配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    api_key: str | None = None
    base_url: str | None = None
    model_image: str | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = None
    resolution: str | None = None
    aspect_ratio: str | None = None
    image_size: str | None = None


class VisionConfigUpdate(BaseModel):
    """视觉理解模型配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    enabled: bool | None = None
    api_key: str | None = None
    base_url: str | None = None
    model_vision: str | None = None


class ModelConfigUpdate(BaseModel):
    """模型配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    default_provider: str | None = None
    enabled_providers: list[str] | None = None
    qianwen: DashScopeConfigUpdate | None = None
    dalle: OpenAIConfigUpdate | None = None
    minimax: MinimaxConfigUpdate | None = None
    volcengine: VolcengineConfigUpdate | None = None
    gemini: GeminiConfigUpdate | None = None
    vision: VisionConfigUpdate | None = None


class MinIOConfigUpdate(BaseModel):
    """MinIO 配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    endpoint: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    bucket: str | None = None
    secure: bool | None = None
    public_base_url: str | None = None


class OSSConfigUpdate(BaseModel):
    """OSS 配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    access_key_id: str | None = None
    access_key_secret: str | None = None
    bucket: str | None = None
    endpoint: str | None = None


class StorageConfigUpdate(BaseModel):
    """存储配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    storage_type: str | None = None
    minio: MinIOConfigUpdate | None = None
    oss: OSSConfigUpdate | None = None


class AppConfigUpdate(BaseModel):
    """应用配置更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    log_level: str | None = None
    cors_allowed_origins: list[str] | None = None
    rate_limit_credit_cost_per_convert: int | None = None
    access_token_expire_minutes: int | None = None


class SystemConfigUpdate(BaseModel):
    """系统配置更新（聚合三组可选更新）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    model: ModelConfigUpdate | None = None
    storage: StorageConfigUpdate | None = None
    app: AppConfigUpdate | None = None


# ============================================================
# 背景音乐配置
# ============================================================
class BgmConfigUpdate(BaseModel):
    """背景音乐 URL 更新"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    music_url: str = Field("", description="背景音乐 URL，留空表示使用内置 mp3")


# ============================================================
# 用户列表
# ============================================================
class AdminUserItem(BaseModel):
    """管理员视角的用户列表项"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    user_id: str
    email: str
    nickname: str | None = None
    avatar_url: str | None = None
    status: str
    is_admin: bool
    permissions: list[str] = Field(default_factory=list, description="权限码集合")
    credits: int
    usage_today: int
    usage_limit: int
    created_at: str | None = None
