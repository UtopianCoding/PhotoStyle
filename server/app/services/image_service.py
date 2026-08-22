"""
图片服务

编排图片上传、查询与删除的完整流程：
- 上传：EXIF 处理 -> 压缩 -> 生成缩略图 -> 对象存储上传 -> 落库
- 查询：按图片ID获取信息
- 删除：删除存储对象与数据库记录

通过 StorageProvider 抽象层操作对象存储（MinIO / OSS），
所有存储操作通过 asyncio.to_thread 放入线程池。
"""

import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    ForbiddenException,
    ImageNotFoundException,
    ValidationException,
)
from app.core.image_processor import ImageProcessor
from app.core.storage import get_storage_provider
from app.core.storage.base import StorageProvider
from app.models.image import Image as ImageModel
from app.repositories.image_repo import ImageRepository
from app.schemas.image import ImageDeleteResponse, ImageInfo, ImageUploadResponse

logger = logging.getLogger(__name__)


class ImageService:
    """图片服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ImageRepository(db)
        self.processor = ImageProcessor()
        self.storage: StorageProvider = get_storage_provider()

    # -------------------- 工具方法 --------------------

    @staticmethod
    def _object_key(user_id: str, ext: str, prefix: str = "images") -> str:
        """生成对象存储 key：{prefix}/{user_id}/{date}/{uuid}.{ext}"""
        date = datetime.utcnow().strftime("%Y%m%d")
        return f"{prefix}/{user_id}/{date}/{uuid.uuid4().hex}.{ext}"

    @staticmethod
    def _mime_to_ext(mime: str) -> str:
        """MIME 类型转扩展名"""
        mapping = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/bmp": "bmp",
        }
        return mapping.get(mime, "jpg")

    # -------------------- 上传 --------------------

    async def upload_image(
        self,
        user_id: str,
        file_bytes: bytes,
        mime_type: str,
        filename: str | None = None,
    ) -> ImageUploadResponse:
        """
        上传图片：压缩、生成缩略图、对象存储上传、落库。

        Args:
            user_id: 用户ID
            file_bytes: 图片字节流
            mime_type: MIME 类型
            filename: 原始文件名（可选）

        Returns:
            ImageUploadResponse 上传响应
        """
        if not file_bytes:
            raise ValidationException("上传文件为空")

        # 1. 提取图片信息
        info = self.processor.get_image_info(file_bytes)
        if not mime_type:
            mime_type = info.mime_type

        # 2. 压缩原图 + 生成缩略图（两者均基于 file_bytes，可并行）
        compressed_bytes, thumbnail_bytes = await asyncio.gather(
            asyncio.to_thread(self.processor.compress_image, file_bytes),
            asyncio.to_thread(self.processor.generate_thumbnail, file_bytes),
        )
        compressed = len(compressed_bytes) < len(file_bytes)
        compressed_ratio = (
            round(len(compressed_bytes) / len(file_bytes), 4) if file_bytes else None
        )

        # 3. 对象存储上传原图与缩略图（两者互不依赖，可并行）
        ext = self._mime_to_ext(mime_type)
        original_key = self._object_key(user_id, ext, prefix="images")
        thumb_key = self._object_key(user_id, "jpg", prefix="thumbnails")

        original_url, thumbnail_url = await asyncio.gather(
            asyncio.to_thread(self.storage.upload, original_key, compressed_bytes, mime_type),
            asyncio.to_thread(self.storage.upload, thumb_key, thumbnail_bytes, "image/jpeg"),
        )

        # 5. 落库
        image = await self.repo.create_image(
            image_id=uuid.uuid4().hex,
            user_id=user_id,
            original_url=original_url,
            thumbnail_url=thumbnail_url,
            mime_type=mime_type,
            width=info.width,
            height=info.height,
            size=len(compressed_bytes),
            compressed=compressed,
            compressed_ratio=compressed_ratio,
        )
        await self.db.commit()

        return ImageUploadResponse(
            image_id=image.image_id,
            original_url=image.original_url,
            thumbnail_url=image.thumbnail_url,
            mime_type=image.mime_type,
            width=image.width,
            height=image.height,
            size=image.size,
            compressed=image.compressed,
            compressed_ratio=image.compressed_ratio,
            created_at=image.created_at,
        )

    # -------------------- 头像上传 --------------------

    async def upload_avatar(
        self,
        user_id: str,
        file_bytes: bytes,
        mime_type: str,
    ) -> str:
        """
        上传用户头像：压缩后存入 avatars 前缀，不创建图片库记录，返回可访问 URL。

        Args:
            user_id: 用户ID
            file_bytes: 图片字节流
            mime_type: MIME 类型

        Returns:
            头像可访问地址
        """
        if not file_bytes:
            raise ValidationException("上传文件为空")

        info = self.processor.get_image_info(file_bytes)
        if not mime_type:
            mime_type = info.mime_type

        compressed_bytes = await asyncio.to_thread(
            self.processor.compress_image, file_bytes
        )
        ext = self._mime_to_ext(mime_type)
        key = self._object_key(user_id, ext, prefix="avatars")
        url = await asyncio.to_thread(
            self.storage.upload, key, compressed_bytes, mime_type
        )
        return url

    # -------------------- 查询 --------------------

    async def list_user_images(
        self, user_id: str, limit: int = 24
    ) -> list[ImageInfo]:
        """列出当前用户的图片（按创建时间倒序），用于「选择已上传图片」"""
        images = await self.repo.get_by_user(user_id, offset=0, limit=limit)
        return [
            ImageInfo(
                image_id=img.image_id,
                original_url=img.original_url,
                thumbnail_url=img.thumbnail_url,
                mime_type=img.mime_type,
                width=img.width,
                height=img.height,
                size=img.size,
                compressed=img.compressed,
                compressed_ratio=img.compressed_ratio,
                created_at=img.created_at,
            )
            for img in images
        ]

    async def get_image(self, user_id: str, image_id: str) -> ImageInfo:
        """获取图片信息（校验归属）"""
        image = await self.repo.get_by_image_id(image_id)
        if image is None:
            raise ImageNotFoundException(f"图片 [{image_id}] 不存在")
        if image.user_id != user_id:
            raise ForbiddenException("无权访问该图片")
        return ImageInfo(
            image_id=image.image_id,
            original_url=image.original_url,
            thumbnail_url=image.thumbnail_url,
            mime_type=image.mime_type,
            width=image.width,
            height=image.height,
            size=image.size,
            compressed=image.compressed,
            compressed_ratio=image.compressed_ratio,
            created_at=image.created_at,
        )

    # -------------------- 删除 --------------------

    async def delete_image(self, user_id: str, image_id: str) -> ImageDeleteResponse:
        """删除图片：先删存储对象，再删数据库记录"""
        image = await self.repo.get_by_image_id(image_id)
        if image is None:
            raise ImageNotFoundException(f"图片 [{image_id}] 不存在")
        if image.user_id != user_id:
            raise ForbiddenException("无权删除该图片")

        # 删除存储中的原图与缩略图
        await asyncio.to_thread(
            self.storage.delete, self.storage.extract_key_from_url(image.original_url)
        )
        if image.thumbnail_url:
            await asyncio.to_thread(
                self.storage.delete, self.storage.extract_key_from_url(image.thumbnail_url)
            )

        await self.repo.delete(image)
        await self.db.commit()
        return ImageDeleteResponse(success=True, image_id=image_id)
