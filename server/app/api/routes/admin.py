"""
后台配置管理路由

提供系统配置的读取与更新、用户列表查询、反馈管理，所有路由仅管理员可访问。
"""

import logging

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import AdminServiceDep, AdminUser, AuthServiceDep, DBSession, FeedbackServiceDep
from app.models.user import User
from app.schemas.admin import AdminUserItem, SystemConfigRead, SystemConfigUpdate
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.feedback import AdminFeedbackItem, FeedbackReply, FeedbackStatusUpdate
from app.schemas.user import AdminUserUpdate, PermissionCatalog
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService

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
    更新系统配置。

    模型配置写入数据库立即生效；存储/应用配置写入 .env 需重启后端服务。
    """
    logger.info("管理员请求更新系统配置")
    data = await admin_service.update_config(payload)
    return ApiResponse.success(data=data, message="模型配置已立即生效，存储/应用配置需重启后端服务")


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


@router.get("/permissions", response_model=ApiResponse[PermissionCatalog])
async def permission_catalog(
    _: AdminUser,
    admin_service: AdminServiceDep,
) -> ApiResponse[PermissionCatalog]:
    """获取权限目录（权限项 + 角色预设），用于用户权限分配界面"""
    return ApiResponse.success(data=admin_service.get_permission_catalog(), message="ok")


@router.put("/users/{user_id}", response_model=ApiResponse[AdminUserItem])
async def update_user(
    user_id: str,
    _: AdminUser,
    payload: AdminUserUpdate,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminUserItem]:
    """
    管理员更新用户（仅管理员可调用）。

    可修改昵称、头像、账号状态、管理员标记，并全量分配权限码。
    """
    user = await auth_service.update_user_by_admin(user_id, payload)
    if user is None:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("用户不存在")
    return ApiResponse.success(
        data=AdminService.to_admin_user_item(user), message="用户已更新"
    )


# ==================== 反馈管理 ====================

@router.get("/feedbacks", response_model=ApiResponse[PageResponse[AdminFeedbackItem]])
async def list_feedbacks(
    _: AdminUser,
    service: FeedbackServiceDep,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> ApiResponse[PageResponse[AdminFeedbackItem]]:
    """
    分页查询所有用户反馈（仅管理员）。

    支持按状态过滤：pending/replied/resolved/closed
    """
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)

    items, total = await service.list_all_feedbacks(page, page_size, status)
    return ApiResponse.success(
        data=PageResponse(total=total, page=page, page_size=page_size, items=items),
        message="ok",
    )


@router.get("/feedbacks/{feedback_id}", response_model=ApiResponse[AdminFeedbackItem])
async def get_feedback(
    feedback_id: str,
    _: AdminUser,
    service: FeedbackServiceDep,
) -> ApiResponse[AdminFeedbackItem]:
    """获取反馈详情（仅管理员）"""
    item = await service.get_feedback_detail(feedback_id)
    return ApiResponse.success(data=item, message="ok")


@router.put("/feedbacks/{feedback_id}/reply", response_model=ApiResponse[AdminFeedbackItem])
async def reply_feedback(
    feedback_id: str,
    admin_user: AdminUser,
    payload: FeedbackReply,
    service: FeedbackServiceDep,
) -> ApiResponse[AdminFeedbackItem]:
    """
    管理员回复用户反馈（仅管理员）。

    回复后状态自动变更为 replied。
    """
    logger.info(f"管理员 {admin_user.user_id} 回复反馈 {feedback_id}")
    item = await service.reply_feedback(feedback_id, admin_user.user_id, payload)
    return ApiResponse.success(data=item, message="回复成功")


@router.patch("/feedbacks/{feedback_id}/status", response_model=ApiResponse[AdminFeedbackItem])
async def update_feedback_status(
    feedback_id: str,
    _: AdminUser,
    payload: FeedbackStatusUpdate,
    service: FeedbackServiceDep,
) -> ApiResponse[AdminFeedbackItem]:
    """
    更新反馈状态（仅管理员）。

    状态可选值：pending/replied/resolved/closed
    """
    logger.info(f"更新反馈 {feedback_id} 状态为 {payload.status}")
    item = await service.update_feedback_status(feedback_id, payload)
    return ApiResponse.success(data=item, message="状态已更新")
