"""
API 依赖注入

提供数据库会话、当前用户与各业务服务的依赖工厂，供路由函数注入。
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.history_service import HistoryService
from app.services.image_service import ImageService
from app.services.style_service import StyleService

# Bearer Token 提取器（不自动报错，由 get_current_user 统一处理）
bearer_scheme = HTTPBearer(auto_error=False)

# 常用依赖类型别名，便于路由函数签名引用
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DBSession,
) -> User:
    """
    解析 Bearer Token 并返回当前登录用户。

    流程：
    1. 校验 Authorization 头格式与 scheme；
    2. 校验 JWT 并取出 user_id；
    3. 查询用户并校验状态。

    Raises:
        UnauthorizedException: 缺少令牌、令牌无效或用户不可用
    """
    if creds is None or creds.scheme.lower() != "bearer":
        raise UnauthorizedException("缺少有效的认证令牌")

    auth_service = AuthService(db)
    try:
        payload = auth_service.verify_token(creds.credentials, expected_type="access")
    except UnauthorizedException:
        raise

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("令牌中缺少用户标识")

    user = await auth_service.get_user_by_id(user_id)
    if user is None:
        raise UnauthorizedException("用户不存在")
    if user.status != "active":
        raise UnauthorizedException("账号已被禁用")
    return user


# 当前用户依赖类型别名
CurrentUser = Annotated[User, Depends(get_current_user)]


# -------------------- 服务工厂 --------------------

async def get_auth_service(db: DBSession) -> AuthService:
    """认证服务依赖"""
    return AuthService(db)


async def get_image_service(db: DBSession) -> ImageService:
    """图片服务依赖"""
    return ImageService(db)


async def get_style_service(db: DBSession) -> StyleService:
    """风格转换服务依赖"""
    return StyleService(db)


async def get_history_service(db: DBSession) -> HistoryService:
    """历史记录服务依赖"""
    return HistoryService(db)


# 服务依赖类型别名
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]
StyleServiceDep = Annotated[StyleService, Depends(get_style_service)]
HistoryServiceDep = Annotated[HistoryService, Depends(get_history_service)]
