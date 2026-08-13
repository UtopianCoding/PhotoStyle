"""
图片数据访问层

提供按图片ID、用户ID查询图片，及创建、删除图片等操作。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import Image
from app.repositories.base import BaseRepository


class ImageRepository(BaseRepository[Image]):
    """图片仓储"""

    model = Image

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_image_id(self, image_id: str) -> Image | None:
        """根据对外图片ID获取记录"""
        stmt = select(Image).where(Image.image_id == image_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: str, offset: int = 0, limit: int = 20
    ) -> list[Image]:
        """获取用户图片列表（按创建时间倒序）"""
        stmt = (
            select(Image)
            .where(Image.user_id == user_id)
            .order_by(Image.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_image(self, **kwargs) -> Image:
        """创建图片记录"""
        image = Image(**kwargs)
        return await self.create(image)

    async def delete_by_image_id(self, image_id: str) -> bool:
        """根据对外图片ID删除记录"""
        image = await self.get_by_image_id(image_id)
        if image is None:
            return False
        await self.delete(image)
        return True
