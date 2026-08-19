"""
图片相关路由

提供图片上传、查询与删除接口。
"""

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import CurrentUser, ImageServiceDep
from app.schemas.common import ApiResponse
from app.schemas.image import ImageDeleteResponse, ImageInfo, ImageUploadResponse

router = APIRouter(prefix="/images", tags=["图片"])


@router.post("/upload", response_model=ApiResponse[ImageUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_image(
    user: CurrentUser,
    service: ImageServiceDep,
    file: UploadFile = File(..., description="待上传图片文件"),
) -> ApiResponse[ImageUploadResponse]:
    """
    上传图片。

    接收 multipart 文件，经过压缩、缩略图生成、OSS 上传后落库。
    返回图片 ID 与可访问地址。
    """
    image_bytes = await file.read()
    result = await service.upload_image(
        user_id=user.user_id,
        file_bytes=image_bytes,
        mime_type=file.content_type or "image/jpeg",
        filename=file.filename,
    )
    return ApiResponse.success(data=result, message="上传成功")


@router.get("", response_model=ApiResponse[list[ImageInfo]])
async def list_images(
    user: CurrentUser,
    service: ImageServiceDep,
    limit: int = 24,
) -> ApiResponse[list[ImageInfo]]:
    """列出当前用户已上传的图片（按创建时间倒序），用于「选择已上传图片」"""
    safe_limit = min(max(limit, 1), 100)
    images = await service.list_user_images(user.user_id, safe_limit)
    return ApiResponse.success(data=images)


@router.get("/{image_id}", response_model=ApiResponse[ImageInfo])
async def get_image(
    image_id: str,
    user: CurrentUser,
    service: ImageServiceDep,
) -> ApiResponse[ImageInfo]:
    """获取图片信息"""
    info = await service.get_image(user.user_id, image_id)
    return ApiResponse.success(data=info)


@router.delete("/{image_id}", response_model=ApiResponse[ImageDeleteResponse])
async def delete_image(
    image_id: str,
    user: CurrentUser,
    service: ImageServiceDep,
) -> ApiResponse[ImageDeleteResponse]:
    """删除图片（同步删除 OSS 对象与数据库记录）"""
    result = await service.delete_image(user.user_id, image_id)
    return ApiResponse.success(data=result, message="删除成功")
