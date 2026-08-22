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
    # 邮箱验证码
    code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")
    # 邀请码（可选，由邀请人提供）
    referral_code: str | None = Field(default=None, max_length=16, description="邀请码")


class SendCodeRequest(BaseModel):
    """发送验证码请求"""

    email: EmailStr = Field(..., description="目标邮箱")


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
    # 邀请码
    referral_code: str | None = None
    # 今日已用次数
    usage_today: int = 0
    # 每日上限
    usage_limit: int = 10
    # 账号状态
    status: str = "active"
    # 是否为管理员
    is_admin: bool = False
    # 权限码集合
    permissions: list[str] = Field(default_factory=list, description="权限码集合")
    # 创建时间
    created_at: datetime | None = None


class UserUpdate(BaseModel):
    """个人资料更新（用户本人可修改的字段）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    # 昵称
    nickname: str | None = Field(default=None, description="昵称")
    # 头像地址
    avatar_url: str | None = Field(default=None, description="头像地址")


class AdminUserUpdate(BaseModel):
    """管理员更新用户（可分配权限、状态、管理员标记等）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    # 昵称
    nickname: str | None = Field(default=None, description="昵称")
    # 头像地址
    avatar_url: str | None = Field(default=None, description="头像地址")
    # 账号状态：active / disabled
    status: str | None = Field(default=None, description="账号状态")
    # 是否管理员
    is_admin: bool | None = Field(default=None, description="是否管理员")
    # 权限码集合（全量覆盖）
    permissions: list[str] | None = Field(default=None, description="权限码集合")


class PermissionItem(BaseModel):
    """权限目录项（用于前端渲染分配界面）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 权限码
    code: str
    # 展示名
    label: str
    # 分组
    group: str
    # 说明
    description: str


class RolePreset(BaseModel):
    """角色预设（便于管理员快速分配权限）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 角色键
    key: str
    # 展示名
    label: str
    # 权限码集合
    permissions: list[str]
    # 是否为超级管理员角色
    is_admin: bool = False


class PermissionCatalog(BaseModel):
    """权限目录响应（权限项 + 角色预设）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 权限项列表
    permissions: list[PermissionItem]
    # 角色预设列表
    role_presets: list[RolePreset]


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
