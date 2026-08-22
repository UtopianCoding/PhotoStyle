"""
全局配置模块

使用 Pydantic Settings 从 .env 文件加载配置，所有配置项按业务域分组管理。
每个子配置组本身也是一个 BaseSettings，通过各自的环境变量前缀加载对应字段，
主 Settings 类负责将各子配置组合为单一全局配置对象。
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================================
# 应用配置
# ============================================================
class AppConfig(BaseSettings):
    """应用基础配置"""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用名称
    name: str = "PhotoStyle"
    # 运行环境：development / staging / production
    env: str = "development"
    # 监听地址
    host: str = "0.0.0.0"
    # 监听端口
    port: int = 8000

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.env == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.env == "production"


# ============================================================
# 数据库配置（MySQL）
# ============================================================
class DatabaseConfig(BaseSettings):
    """MySQL 数据库配置"""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库连接串（使用 aiomysql 异步驱动）
    # 格式：mysql+aiomysql://用户名:密码@主机:端口/数据库名
    url: str = "mysql+aiomysql://root:password@localhost:3306/photostyle"

    @property
    def async_url(self) -> str:
        """异步数据库连接 URL（已使用异步驱动，直接返回）"""
        return self.url


# ============================================================
# Redis 配置
# ============================================================
class RedisConfig(BaseSettings):
    """Redis 缓存配置"""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Redis 连接串
    url: str = "redis://localhost:6379/0"


# ============================================================
# 阿里云 DashScope（千问）配置
# ============================================================
class DashScopeConfig(BaseSettings):
    """阿里云 DashScope（千问大模型）配置"""

    model_config = SettingsConfigDict(
        env_prefix="DASHSCOPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DashScope API Key（敏感信息）
    api_key: SecretStr = SecretStr("")
    # 视觉理解模型名（用于分析图片内容）
    model_vision: str = "qwen-vl-plus"
    # 图像生成模型名（用于图生图/文生图）
    model_image: str = "qwen-image-3.0-pro"
    # 百炼工作空间 ID（用于拼接 base_url，sk-ws- Key 前缀中提取）
    workspace_id: str = ""
    # 区域（cn-beijing / ap-southeast-1 等）
    region: str = "cn-beijing"


# ============================================================
# 火山引擎（豆包）配置
# ============================================================
class DoubaoConfig(BaseSettings):
    """火山引擎豆包（Doubao）配置"""

    model_config = SettingsConfigDict(
        env_prefix="DOUBAO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 火山引擎 Access Key（敏感信息）
    access_key: SecretStr = SecretStr("")
    # 火山引擎 Secret Key（敏感信息）
    secret_key: SecretStr = SecretStr("")


# ============================================================
# OpenAI（DALL-E）配置
# ============================================================
class DalleConfig(BaseSettings):
    """OpenAI DALL-E 配置"""

    model_config = SettingsConfigDict(
        env_prefix="DALLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI API Key（敏感信息）
    api_key: SecretStr = SecretStr("")
    # OpenAI 接口基础地址（可替换为兼容代理）
    base_url: str = "https://api.openai.com/v1"
    # 图像生成模型名（如 dall-e-3）
    model_image: str = "dall-e-3"


# ============================================================
# MiniMax 配置
# ============================================================
class MinimaxConfig(BaseSettings):
    """MiniMax 图像生成配置"""

    model_config = SettingsConfigDict(
        env_prefix="MINIMAX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MiniMax API Key（敏感信息）
    api_key: SecretStr = SecretStr("")
    # MiniMax 接口基础地址
    base_url: str = "https://api.minimax.chat/v1"
    # 图像生成模型名
    model_image: str = "image-01"


# ============================================================
# 模型路由配置
# ============================================================
class ModelRoutingConfig(BaseSettings):
    """模型路由配置（决定默认使用哪个图像生成 Provider）"""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 默认图像生成 Provider ID：qianwen / dalle / minimax / doubao
    default_provider: str = "qianwen"


# ============================================================
# 存储类型配置
# ============================================================
class StorageConfig(BaseSettings):
    """对象存储类型选择配置"""

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 存储类型：minio / oss
    type: str = "minio"


# ============================================================
# MinIO 对象存储配置
# ============================================================
class MinIOConfig(BaseSettings):
    """MinIO 对象存储配置"""

    model_config = SettingsConfigDict(
        env_prefix="MINIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MinIO 访问端点（不含协议，如 localhost:9000）
    endpoint: str = "localhost:9000"
    # MinIO Access Key（敏感信息）
    access_key: SecretStr = SecretStr("minioadmin")
    # MinIO Secret Key（敏感信息）
    secret_key: SecretStr = SecretStr("minioadmin")
    # 存储桶名称
    bucket: str = "photostyle"
    # 是否使用 HTTPS
    secure: bool = False
    # 对外访问基地址（用于生成公开 URL，如 http://localhost:9000）
    public_base_url: str = "http://localhost:9000"

    @property
    def endpoint_with_protocol(self) -> str:
        """返回带协议的端点地址"""
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}"


# ============================================================
# 阿里云 OSS 配置
# ============================================================
class OSSConfig(BaseSettings):
    """阿里云对象存储 OSS 配置"""

    model_config = SettingsConfigDict(
        env_prefix="OSS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OSS Access Key ID（敏感信息）
    access_key_id: SecretStr = SecretStr("")
    # OSS Access Key Secret（敏感信息）
    access_key_secret: SecretStr = SecretStr("")
    # OSS 存储桶名称
    bucket: str = "photostyle"
    # OSS 访问端点
    endpoint: str = "https://oss-cn-hangzhou.aliyuncs.com"


# ============================================================
# JWT 配置
# ============================================================
class JWTConfig(BaseSettings):
    """JWT 认证配置"""

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # JWT 签名密钥（敏感信息，生产环境务必修改）
    secret_key: SecretStr = SecretStr("")
    # 签名算法
    algorithm: str = "HS256"
    # Access Token 过期时间（分钟）
    access_token_expire_minutes: int = 120
    # Refresh Token 过期时间（天）
    refresh_token_expire_days: int = 7


# ============================================================
# CORS 配置
# ============================================================
class CORSConfig(BaseSettings):
    """跨域资源共享（CORS）配置"""

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 允许的跨域来源列表（逗号分隔字符串，避免 pydantic-settings JSON 解析问题）
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        """解析逗号分隔的字符串为列表"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


# ============================================================
# 日志配置
# ============================================================
class LoggingConfig(BaseSettings):
    """日志配置"""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 日志级别：DEBUG / INFO / WARNING / ERROR / CRITICAL
    level: str = "INFO"


# ============================================================
# SMTP 邮件配置
# ============================================================
class SmtpConfig(BaseSettings):
    """SMTP 邮件发送配置（用于注册验证码等）"""

    model_config = SettingsConfigDict(
        env_prefix="SMTP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SMTP 服务器地址
    host: str = "smtp.gmail.com"
    # SMTP 端口（465=SSL, 587=TLS）
    port: int = 587
    # 发件人邮箱
    username: str = ""
    # 发件人密码 / 授权码（敏感信息）
    password: SecretStr = SecretStr("")
    # 发件人显示名称
    from_name: str = "PhotoStyle"
    # 是否启用 TLS
    use_tls: bool = True


# ============================================================
# 限流配置
# ============================================================
class RateLimitConfig(BaseSettings):
    """速率限制配置"""

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 免费用户每日风格转换次数上限
    free_user_daily_limit: int = 10


# ============================================================
# 支付宝配置
# ============================================================
class AlipayConfig(BaseSettings):
    """支付宝当面付配置"""

    model_config = SettingsConfigDict(
        env_prefix="ALIPAY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 是否启用支付宝支付
    enabled: bool = False
    # 支付宝应用 AppID
    app_id: str = ""
    # 商户私钥（RSA2 私钥，PKCS8 格式）
    private_key: str = ""
    # 支付宝公钥（用于验证回调签名）
    alipay_public_key: str = ""
    # 签名算法：RSA2
    sign_type: str = "RSA2"
    # 编码格式
    charset: str = "utf-8"
    # 支付宝网关
    gateway: str = "https://openapi.alipaydev.com/gateway.do"  # 沙箱网关


# ============================================================
# 全局 Settings 聚合类
# ============================================================
class Settings(BaseSettings):
    """
    全局配置聚合类

    组合所有子配置组，提供统一的配置访问入口。
    各子配置组独立从 .env 文件加载对应前缀的环境变量。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用配置
    app: AppConfig = AppConfig()
    # 数据库配置
    database: DatabaseConfig = DatabaseConfig()
    # Redis 配置
    redis: RedisConfig = RedisConfig()
    # DashScope（千问）配置
    dashscope: DashScopeConfig = DashScopeConfig()
    # 豆包配置
    doubao: DoubaoConfig = DoubaoConfig()
    # DALL-E 配置
    dalle: DalleConfig = DalleConfig()
    # MiniMax 配置
    minimax: MinimaxConfig = MinimaxConfig()
    # 模型路由配置
    model: ModelRoutingConfig = ModelRoutingConfig()
    # 存储类型配置
    storage: StorageConfig = StorageConfig()
    # MinIO 配置
    minio: MinIOConfig = MinIOConfig()
    # OSS 配置
    oss: OSSConfig = OSSConfig()
    # JWT 配置
    jwt: JWTConfig = JWTConfig()
    # CORS 配置
    cors: CORSConfig = CORSConfig()
    # 日志配置
    logging: LoggingConfig = LoggingConfig()
    # SMTP 邮件配置
    smtp: SmtpConfig = SmtpConfig()
    # 限流配置
    rate_limit: RateLimitConfig = RateLimitConfig()
    # 支付宝配置
    alipay: AlipayConfig = AlipayConfig()


# 全局配置单例，供应用各模块直接导入使用
settings = Settings()
