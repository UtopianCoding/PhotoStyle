"""
用户 ORM 模型

记录账号信息、积分余额与每日用量，用于鉴权与免费额度限流。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 对外暴露的用户唯一标识（UUID 形式字符串）
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="对外用户ID")
    # 邮箱（登录账号）
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="邮箱")
    # bcrypt 密码哈希
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    # 昵称
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="昵称")
    # 头像地址
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="头像URL")
    # 积分余额（用于风格转换扣费）
    credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="积分余额")
    # 邀请码（唯一，用于邀请好友注册）
    referral_code: Mapped[str | None] = mapped_column(String(16), unique=True, index=True, nullable=True, comment="邀请码")
    # 邀请人ID（记录是谁邀请注册的）
    inviter_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="邀请人ID")
    # 今日已使用次数（用于每日免费额度限流）
    usage_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="今日使用次数")
    # 每日使用上限
    usage_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False, comment="每日使用上限")
    # 账号状态：active / disabled
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, comment="账号状态")
    # 是否为管理员（用于后台配置功能权限控制）
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否管理员")
    # 权限码集合（JSON 数组字符串），如 ["home:access","history:view"]
    # 超级管理员(is_admin=True)隐式拥有全部权限；仅管理员可分配
    permissions: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default="[]", comment="权限码集合(JSON数组)"
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} user_id={self.user_id} email={self.email}>"
