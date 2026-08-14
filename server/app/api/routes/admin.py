"""
后台配置管理路由

提供系统配置的读取与更新、用户列表查询，所有路由仅管理员可访问。
"""

import logging

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import AdminServiceDep, AdminUser, DBSession
from app.models.user import User
from app.schemas.admin import AdminUserItem, SystemConfigRead, SystemConfigUpdate
from app.schemas.common import ApiResponse, PageResponse
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["后台管理"])


@router.get("/config", response_model=ApiResponse[SystemConfigRead])
async def get_config(
    _: AdminUser,
    admin_service: AdminServiceDep,
) -> ApiResponse[SystemConfigRead]:
    """读取当前系统配置（敏感字段脱敏）"""
    data = admin_service.get_config()
    return ApiResponse.success(data=data, message="ok")


@router.put("/config", response_model=ApiResponse[SystemConfigRead])
async def update_config(
    _: AdminUser,
    payload: SystemConfigUpdate,
    admin_service: AdminServiceDep,
) -> ApiResponse[SystemConfigRead]:
    """
    更新系统配置（写入 .env 文件）。

    注意：写入后需重启后端服务才能让新配置在内存中生效。
    """
    logger.info("管理员请求更新系统配置")
    data = admin_service.update_config(payload)
    return ApiResponse.success(data=data, message="配置已写入 .env，请重启后端服务使新配置生效")


@router.get("/users", response_model=ApiResponse[PageResponse[AdminUserItem]])
async def list_users(
    _: AdminUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 20,
) -> ApiResponse[PageResponse[AdminUserItem]]:
    """分页查询用户列表（仅管理员）"""
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)

    # 总数
    total_stmt = select(func.count()).select_from(User)
    total = (await db.execute(total_stmt)).scalar_one()

    # 分页数据
    offset = (page - 1) * page_size
    stmt = select(User).order_by(User.id.desc()).offset(offset).limit(page_size)
    users = (await db.execute(stmt)).scalars().all()

    items = [AdminService.to_admin_user_item(u) for u in users]
    return ApiResponse.success(
        data=PageResponse(total=total, page=page, page_size=page_size, items=items),
        message="ok",
    )
