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
    # API 基础地址（共享端点；配置了 Workspace ID 时自动切换为专属端点）
    base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    # 视觉理解模型名（用于分析图片内容）
    model_vision: str = "qwen3-vl-flash"
    # 图像生成模型名（用于图生图/文生图）
    model_image: str = "qwen-image-3.0-pro"
    # 百炼工作空间 ID（用于拼接 base_url，从 API Key 前缀中提取）
    workspace_id: str = "llm-qiqf68qtx7wjzdvx"
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
# OpenAI（GPT Image 2）配置
# ============================================================
class DalleConfig(BaseSettings):
    """OpenAI GPT Image 2 配置"""

    model_config = SettingsConfigDict(
        env_prefix="DALLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    # OpenAI API Key（敏感信息）
    api_key: SecretStr = SecretStr("")
    # API 基础地址（默认使用 GPT Image 2 代理）
    base_url: str = "https://api-direct.boft.ai/v1"
    # 图像生成模型名（默认 gpt-image-2）
    model_image: str = "gpt-image-2"


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
        protected_namespaces=(),
    )

    # MiniMax API Key（敏感信息）
    api_key: SecretStr = SecretStr("")
    # MiniMax 接口基础地址
    base_url: str = "https://api.minimaxi.com/v1"
    # 图像生成模型名：image-01 / image-01-live
    model_image: str = "image-01"
    # 是否在生成图片中添加 AI 生成水印，默认 false
    watermark: bool = False


# ============================================================
# 火山引擎（Seedream 图像生成）配置
# ============================================================
class VolcengineConfig(BaseSettings):
    """火山引擎 Seedream 图像生成配置"""

    model_config = SettingsConfigDict(
        env_prefix="VOLCENGINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    # 火山引擎 API Key（敏感信息，在方舟平台获取）
    api_key: SecretStr = SecretStr("")
    # 接口基础地址
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    # 图像生成模型名（如 seedream-5-0-pro / seedream-5-0-lite / seedream-4-5 / seedream-4-0）
    model_image: str = "seedream-5-0-pro"
    # 是否在生成图片右下角添加「AI 生成」水印（false = 不加水印）
    watermark: bool = False


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

    # MinIO 端点（不含协议）
    endpoint: str = "localhost:9000"
    # Access Key（敏感信息）
    access_key: SecretStr = SecretStr("")
    # Secret Key（敏感信息）
    secret_key: SecretStr = SecretStr("")
    # Bucket 名称
    bucket: str = "photostyle"
    # 是否启用 HTTPS
    secure: bool = False
    # 对外访问基地址（公开域名，用于拼接可访问 URL）
    public_base_url: str = ""


# ============================================================
# 阿里云 OSS 配置
# ============================================================
class OSSConfig(BaseSettings):
    """阿里云 OSS 配置"""

    model_config = SettingsConfigDict(
        env_prefix="OSS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OSS AccessKey ID（敏感信息）
    access_key_id: SecretStr = SecretStr("")
    # OSS AccessKey Secret（敏感信息）
    access_key_secret: SecretStr = SecretStr("")
    # Bucket 名称
    bucket: str = "photostyle"
    # OSS 端点
    endpoint: str = "https://oss-cn-hangzhou.aliyuncs.com"


# ============================================================
# JWT 配置
# ============================================================
class JWTConfig(BaseSettings):
    """JWT 令牌配置"""

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # JWT 密钥（敏感信息）
    secret_key: SecretStr = SecretStr("your-secret-key-change-in-production")
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
    """跨域资源共享配置"""

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 允许的源列表（逗号分隔字符串）
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        """解析为列表"""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


# ============================================================
# 日志配置
# ============================================================
class LoggingConfig(BaseSettings):
    """日志配置"""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 日志级别
    level: str = "INFO"


# ============================================================
# 存储配置
# ============================================================
class StorageConfig(BaseSettings):
    """对象存储选择配置"""

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 存储类型：minio / oss
    type: str = "minio"


# ============================================================
# SMTP 邮件配置
# ============================================================
class SMTPConfig(BaseSettings):
    """SMTP 邮件配置"""

    model_config = SettingsConfigDict(
        env_prefix="SMTP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SMTP 服务器地址
    host: str = "smtp.gmail.com"
    # SMTP 端口
    port: int = 465
    # 用户名
    username: str = ""
    # 密码（敏感信息）
    password: SecretStr = SecretStr("")
    # 发件人名称
    from_name: str = "PhotoStyle"
    # 是否使用 TLS
    use_tls: bool = True


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

    # 是否启用支付宝
    enabled: bool = False
    # 应用 AppID
    app_id: str = ""
    # 商户 RSA2 私钥（敏感信息）
    private_key: SecretStr = SecretStr("")
    # 支付宝公钥
    alipay_public_key: str = ""
    # 签名算法
    sign_type: str = "RSA2"
    # 编码格式
    charset: str = "utf-8"
    # 支付宝网关
    gateway: str = "https://openapi.alipaydev.com/gateway.do"


# ============================================================
# 限流 / 积分配置
# ============================================================
class RateLimitConfig(BaseSettings):
    """限流与积分相关配置"""

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 每次风格转换扣除的积分数
    credit_cost_per_convert: int = 4


# ============================================================
# 主配置聚合
# ============================================================
class Settings:
    """
    全局配置聚合类

    将各子配置组合为单一配置对象，通过属性访问。
    使用懒加载模式，首次访问时才实例化各子配置。
    """

    def __init__(self) -> None:
        self._app: AppConfig | None = None
        self._database: DatabaseConfig | None = None
        self._redis: RedisConfig | None = None
        self._dashscope: DashScopeConfig | None = None
        self._doubao: DoubaoConfig | None = None
        self._dalle: DalleConfig | None = None
        self._minimax: MinimaxConfig | None = None
        self._volcengine: VolcengineConfig | None = None
        self._minio: MinIOConfig | None = None
        self._oss: OSSConfig | None = None
        self._jwt: JWTConfig | None = None
        self._cors: CORSConfig | None = None
        self._logging: LoggingConfig | None = None
        self._storage: StorageConfig | None = None
        self._smtp: SMTPConfig | None = None
        self._alipay: AlipayConfig | None = None
        self._rate_limit: RateLimitConfig | None = None

    @property
    def app(self) -> AppConfig:
        if self._app is None:
            self._app = AppConfig()
        return self._app

    @property
    def database(self) -> DatabaseConfig:
        if self._database is None:
            self._database = DatabaseConfig()
        return self._database

    @property
    def redis(self) -> RedisConfig:
        if self._redis is None:
            self._redis = RedisConfig()
        return self._redis

    @property
    def dashscope(self) -> DashScopeConfig:
        if self._dashscope is None:
            self._dashscope = DashScopeConfig()
        return self._dashscope

    @property
    def doubao(self) -> DoubaoConfig:
        if self._doubao is None:
            self._doubao = DoubaoConfig()
        return self._doubao

    @property
    def dalle(self) -> DalleConfig:
        if self._dalle is None:
            self._dalle = DalleConfig()
        return self._dalle

    @property
    def minimax(self) -> MinimaxConfig:
        if self._minimax is None:
            self._minimax = MinimaxConfig()
        return self._minimax

    @property
    def volcengine(self) -> VolcengineConfig:
        if self._volcengine is None:
            self._volcengine = VolcengineConfig()
        return self._volcengine

    @property
    def minio(self) -> MinIOConfig:
        if self._minio is None:
            self._minio = MinIOConfig()
        return self._minio

    @property
    def oss(self) -> OSSConfig:
        if self._oss is None:
            self._oss = OSSConfig()
        return self._oss

    @property
    def jwt(self) -> JWTConfig:
        if self._jwt is None:
            self._jwt = JWTConfig()
        return self._jwt

    @property
    def cors(self) -> CORSConfig:
        if self._cors is None:
            self._cors = CORSConfig()
        return self._cors

    @property
    def logging(self) -> LoggingConfig:
        if self._logging is None:
            self._logging = LoggingConfig()
        return self._logging

    @property
    def storage(self) -> StorageConfig:
        if self._storage is None:
            self._storage = StorageConfig()
        return self._storage

    @property
    def smtp(self) -> SMTPConfig:
        if self._smtp is None:
            self._smtp = SMTPConfig()
        return self._smtp

    @property
    def alipay(self) -> AlipayConfig:
        if self._alipay is None:
            self._alipay = AlipayConfig()
        return self._alipay

    @property
    def rate_limit(self) -> RateLimitConfig:
        if self._rate_limit is None:
            self._rate_limit = RateLimitConfig()
        return self._rate_limit


# 全局单例
settings = Settings()
