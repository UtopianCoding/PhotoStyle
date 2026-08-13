"""
认证服务

提供用户注册、登录、令牌签发与校验，基于：
- bcrypt：密码哈希
- python-jose：JWT 签发与验证

Access Token 用于接口鉴权，Refresh Token 用于续签。
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    UnauthorizedException,
    ValidationException,
)
from app.models.user import User
from app.schemas.user import AuthResponse, TokenResponse, UserInfo, UserLogin, UserRegister

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -------------------- 密码 --------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """对明文密码进行 bcrypt 哈希"""
        # bcrypt 限制 72 字节，超出则截断
        pwd_bytes = password.encode("utf-8")[:72]
        return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """校验明文密码与哈希是否匹配"""
        try:
            pwd_bytes = plain.encode("utf-8")[:72]
            return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
        except Exception:
            return False

    # -------------------- 注册 --------------------

    async def register(self, payload: UserRegister) -> AuthResponse:
        """
        注册新用户并签发令牌。

        - 邮箱不可重复
        - 初始积分为 0，每日上限按配置
        """
        # 校验邮箱唯一
        stmt = select(User).where(User.email == payload.email)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise ValidationException("该邮箱已注册")

        from app.config import settings

        user = User(
            user_id=uuid.uuid4().hex,
            email=payload.email,
            password_hash=self.hash_password(payload.password),
            nickname=payload.nickname,
            credits=0,
            usage_today=0,
            usage_limit=settings.rate_limit.free_user_daily_limit,
            status="active",
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        await self.db.commit()

        return self.create_auth_response(user)

    # -------------------- 登录 --------------------

    async def login(self, payload: UserLogin) -> AuthResponse:
        """邮箱 + 密码登录，签发令牌"""
        stmt = select(User).where(User.email == payload.email)
        user = (await self.db.execute(stmt)).scalar_one_or_none()
        if user is None:
            raise UnauthorizedException("邮箱或密码错误")
        if not self.verify_password(payload.password, user.password_hash):
            raise UnauthorizedException("邮箱或密码错误")
        if user.status != "active":
            raise UnauthorizedException("账号已被禁用")

        return self.create_auth_response(user)

    # -------------------- 令牌 --------------------

    def create_token(self, user: User) -> TokenResponse:
        """为用户签发 Access / Refresh Token"""
        from app.config import settings

        now = datetime.now(timezone.utc)
        access_expires = now + timedelta(minutes=settings.jwt.access_token_expire_minutes)
        refresh_expires = now + timedelta(days=settings.jwt.refresh_token_expire_days)

        access_token = self._encode(
            {"sub": user.user_id, "type": "access", "exp": access_expires}
        )
        refresh_token = self._encode(
            {"sub": user.user_id, "type": "refresh", "exp": refresh_expires}
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt.access_token_expire_minutes * 60,
        )

    def create_auth_response(self, user: User) -> AuthResponse:
        """签发令牌并附带用户信息，用于登录/注册响应"""
        token = self.create_token(user)
        return AuthResponse(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            user=self._to_user_info(user),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """使用 Refresh Token 续签"""
        payload = self.verify_token(refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("无效的刷新令牌")

        stmt = select(User).where(User.user_id == user_id)
        user = (await self.db.execute(stmt)).scalar_one_or_none()
        if user is None or user.status != "active":
            raise UnauthorizedException("用户不存在或已禁用")

        return self.create_token(user)

    def verify_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        """
        校验 JWT 并返回 payload。

        Args:
            token: JWT 字符串
            expected_type: 期望的令牌类型（access / refresh）

        Returns:
            JWT payload 字典

        Raises:
            UnauthorizedException: 令牌无效、过期或类型不符
        """
        from app.config import settings

        try:
            payload = jwt.decode(
                token,
                settings.jwt.secret_key.get_secret_value(),
                algorithms=[settings.jwt.algorithm],
            )
        except JWTError as exc:
            raise UnauthorizedException(f"令牌无效: {exc}") from exc

        token_type = payload.get("type")
        if expected_type and token_type != expected_type:
            raise UnauthorizedException(
                f"令牌类型不符，期望 {expected_type}，实际 {token_type}"
            )
        return payload

    async def get_user_by_id(self, user_id: str) -> User | None:
        """按对外 user_id 查询用户"""
        stmt = select(User).where(User.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # -------------------- 工具 --------------------

    @staticmethod
    def _encode(claims: dict[str, Any]) -> str:
        """签发 JWT"""
        from app.config import settings

        return jwt.encode(
            claims,
            settings.jwt.secret_key.get_secret_value(),
            algorithm=settings.jwt.algorithm,
        )

    @staticmethod
    def _to_user_info(user: User) -> UserInfo:
        """User 模型转 UserInfo 模式"""
        return UserInfo(
            user_id=user.user_id,
            email=user.email,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            credits=user.credits,
            usage_today=user.usage_today,
            usage_limit=user.usage_limit,
            status=user.status,
            created_at=user.created_at,
        )
