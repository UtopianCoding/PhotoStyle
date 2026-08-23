"""
用户反馈与建议路由

提供用户提交反馈、查询自己的反馈列表与详情、上传反馈附图等接口。
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import CurrentUser, FeedbackServiceDep, ImageServiceDep
from app.core.exceptions import ValidationException
from app.schemas.common import ApiResponse
from app.schemas.feedback import FeedbackCreate, FeedbackInfo

router = APIRouter(prefix="/feedback", tags=["反馈"])


@router.post("", response_model=ApiResponse[FeedbackInfo], status_code=status.HTTP_201_CREATED)
async def create_feedback(
    user: CurrentUser,
    service: FeedbackServiceDep,
    feedback_data: FeedbackCreate,
) -> ApiResponse[FeedbackInfo]:
    """
    提交反馈与建议

    用户可以提交问题反馈或功能建议，支持附带最多5张图片。
    管理员可在后台查看并回复。
    """
    result = await service.create_feedback(user.user_id, feedback_data)
    return ApiResponse.success(data=result, message="反馈提交成功")


@router.get("", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def list_my_feedbacks(
    user: CurrentUser,
    service: FeedbackServiceDep,
    page: int = 1,
    page_size: int = 20,
) -> ApiResponse[dict]:
    """
    获取我的反馈列表

    返回当前用户提交的所有反馈，按创建时间倒序排列。
    支持分页查询。
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    items, total = await service.list_user_feedbacks(user.user_id, page, page_size)
    return ApiResponse.success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{feedback_id}", response_model=ApiResponse[FeedbackInfo])
async def get_my_feedback(
    feedback_id: str,
    user: CurrentUser,
    service: FeedbackServiceDep,
) -> ApiResponse[FeedbackInfo]:
    """
    获取反馈详情

    返回指定反馈的完整信息，包括管理员回复（如果有）。
    只能查询自己提交的反馈。
    """
    result = await service.get_user_feedback(user.user_id, feedback_id)
    return ApiResponse.success(data=result)


@router.post("/images", response_model=ApiResponse[list[str]], status_code=status.HTTP_201_CREATED)
async def upload_feedback_images(
    user: CurrentUser,
    image_service: ImageServiceDep,
    files: list[UploadFile] = File(..., description="反馈附图（最多5张）"),
) -> ApiResponse[list[str]]:
    """
    上传反馈附图

    上传反馈时附带的图片，返回图片URL列表。
    单次最多上传5张图片，每张图片大小不超过5MB。
    """
    if len(files) > 5:
        raise ValidationException("单次最多上传5张图片")

    # 校验文件大小
    for file in files:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB
            raise ValidationException(f"图片 {file.filename} 超过5MB限制")
        await file.seek(0)  # 重置文件指针

    # 上传图片（复用 image_service 的头像上传逻辑，存入 feedback/ 前缀）
    urls = []
    for file in files:
        content = await file.read()
        mime_type = file.content_type or "image/jpeg"

        # 生成存储路径
        date = datetime.utcnow().strftime("%Y%m%d")
        ext = mime_type.split("/")[-1] if "/" in mime_type else "jpg"
        key = f"feedback/{user.user_id}/{date}/{uuid.uuid4().hex}.{ext}"

        # 上传到对象存储
        from app.core.storage import get_storage_provider
        storage = get_storage_provider()
        import asyncio
        url = await asyncio.to_thread(storage.upload, key, content, mime_type)
        urls.append(url)

    return ApiResponse.success(data=urls, message=f"成功上传{len(urls)}张图片")
