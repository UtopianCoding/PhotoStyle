"""
用户相关请求/响应模式

所有响应模型使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class UserRegister(BaseModel):
    """用户注册请求"""

    # 邮箱
    email: EmailStr = Field(..., description="邮箱")
    # 密码
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    # 昵称
    nickname: str | None = Field(default=None, description="昵称")


class UserLogin(BaseModel):
    """用户登录请求"""

    # 邮箱
    email: EmailStr = Field(..., description="邮箱")
    # 密码
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 访问令牌
    access_token: str = Field(..., description="访问令牌")
    # 刷新令牌
    refresh_token: str = Field(..., description="刷新令牌")
    # 令牌类型
    token_type: str = Field(default="bearer", description="令牌类型")
    # 过期时间（秒）
    expires_in: int = Field(..., description="过期时间(秒)")


class UserInfo(BaseModel):
    """用户信息"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 对外用户ID
    user_id: str
    # 邮箱
    email: str
    # 昵称
    nickname: str | None = None
    # 头像地址
    avatar_url: str | None = None
    # 积分余额
    credits: int = 0
    # 今日已用次数
    usage_today: int = 0
    # 每日上限
    usage_limit: int = 10
    # 账号状态
    status: str = "active"
    # 是否为管理员
    is_admin: bool = False
    # 创建时间
    created_at: datetime | None = None


class AuthResponse(BaseModel):
    """登录 / 注册统一响应（包含 token 与用户信息）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 访问令牌
    access_token: str = Field(..., description="访问令牌")
    # 刷新令牌
    refresh_token: str = Field(..., description="刷新令牌")
    # 令牌类型
    token_type: str = Field(default="bearer", description="令牌类型")
    # 过期时间（秒）
    expires_in: int = Field(..., description="过期时间(秒)")
    # 用户信息
    user: UserInfo = Field(..., description="用户信息")
