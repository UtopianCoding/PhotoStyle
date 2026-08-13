"""
认证相关路由

提供注册、登录、令牌刷新、登出与当前用户信息查询。
"""

from fastapi import APIRouter, Body, status

from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas.common import ApiResponse
from app.schemas.user import AuthResponse, TokenResponse, UserInfo, UserLogin, UserRegister
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[AuthResponse], status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    auth_service: AuthServiceDep,
) -> ApiResponse[AuthResponse]:
    """用户注册并签发令牌"""
    data = await auth_service.register(payload)
    return ApiResponse.success(data=data, message="注册成功")


@router.post("/login", response_model=ApiResponse[AuthResponse])
async def login(
    payload: UserLogin,
    auth_service: AuthServiceDep,
) -> ApiResponse[AuthResponse]:
    """用户登录，签发令牌"""
    data = await auth_service.login(payload)
    return ApiResponse.success(data=data, message="登录成功")


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    auth_service: AuthServiceDep,
    refresh_token: str = Body(..., embed=True, description="刷新令牌"),
) -> ApiResponse[TokenResponse]:
    """
    刷新令牌。

    请求体示例：{"refresh_token": "<token>"}
    """
    token = await auth_service.refresh_token(refresh_token)
    return ApiResponse.success(data=token, message="刷新成功")


@router.post("/logout", response_model=ApiResponse)
async def logout() -> ApiResponse:
    """
    登出。

    本服务端为无状态 JWT，登出仅作为协议接口；
    客户端应清除本地令牌。如需服务端失效，可结合 Redis 黑名单实现。
    """
    return ApiResponse.success(message="已登出")


@router.get("/me", response_model=ApiResponse[UserInfo])
async def me(current_user: CurrentUser) -> ApiResponse[UserInfo]:
    """获取当前登录用户信息"""
    user_info = AuthService._to_user_info(current_user)
    return ApiResponse.success(data=user_info)
