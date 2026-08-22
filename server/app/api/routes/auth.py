"""
认证相关路由

提供注册、登录、令牌刷新、登出与当前用户信息查询。
"""

from fastapi import APIRouter, Body, File, Request, UploadFile, status

from app.api.deps import AuthServiceDep, CurrentUser, EmailServiceDep, ImageServiceDep
from app.schemas.common import ApiResponse
from app.schemas.user import (
    AuthResponse,
    SendCodeRequest,
    TokenResponse,
    UserInfo,
    UserLogin,
    UserRegister,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


def _get_client_ip(request: Request) -> str:
    """从请求中提取客户端真实 IP（支持反向代理）"""
    # 优先从 X-Forwarded-For 获取（Nginx/CDN 场景）
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # 备选：X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    # 兜底：直连 IP
    return request.client.host if request.client else ""


@router.post("/send-code", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def send_code(
    payload: SendCodeRequest,
    request: Request,
    email_service: EmailServiceDep,
    auth_service: AuthServiceDep,
) -> ApiResponse:
    """发送邮箱验证码（注册前调用）"""
    # 预检查：邮箱是否已注册
    is_registered = await auth_service.is_email_registered(payload.email)
    if is_registered:
        return ApiResponse.success(message="该邮箱已注册，请直接登录")

    # 提取客户端 IP
    client_ip = _get_client_ip(request)
    
    # 发送验证码（含多维度限流）
    await email_service.send_code(payload.email, client_ip=client_ip)
    return ApiResponse.success(message="验证码已发送")


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
    客户端应清除本地令牌。如需服务端失效，可结合数据库黑名单实现。
    """
    return ApiResponse.success(message="已登出")


@router.get("/me", response_model=ApiResponse[UserInfo])
async def me(current_user: CurrentUser) -> ApiResponse[UserInfo]:
    """获取当前登录用户信息"""
    user_info = AuthService._to_user_info(current_user)
    return ApiResponse.success(data=user_info)


@router.put("/me", response_model=ApiResponse[UserInfo])
async def update_me(
    current_user: CurrentUser,
    payload: UserUpdate,
    auth_service: AuthServiceDep,
) -> ApiResponse[UserInfo]:
    """
    更新个人资料（用户本人可修改：昵称、头像地址）。

    头像图片请先通过 POST /auth/avatar 上传拿到地址，再随昵称一并提交。
    """
    user_info = await auth_service.update_profile(current_user, payload)
    return ApiResponse.success(data=user_info, message="资料已更新")


@router.post("/avatar", response_model=ApiResponse[dict])
async def upload_avatar(
    user: CurrentUser,
    service: ImageServiceDep,
    file: UploadFile = File(..., description="头像图片文件"),
) -> ApiResponse[dict]:
    """
    上传用户头像，返回头像可访问地址。

    拿到 avatarUrl 后，调用 PUT /auth/me 将 avatarUrl 写入个人资料。
    """
    image_bytes = await file.read()
    avatar_url = await service.upload_avatar(
        user_id=user.user_id,
        file_bytes=image_bytes,
        mime_type=file.content_type or "image/jpeg",
    )
    return ApiResponse.success(data={"avatarUrl": avatar_url}, message="头像上传成功")
