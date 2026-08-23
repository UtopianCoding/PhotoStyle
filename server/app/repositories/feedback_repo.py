"""
反馈仓储

提供反馈数据的增删改查操作。
"""

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback


class FeedbackRepository:
    """反馈数据仓储"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, feedback: Feedback) -> Feedback:
        """创建反馈"""
        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    async def get_by_id(self, feedback_id: str) -> Feedback | None:
        """根据反馈ID查询"""
        stmt = select(Feedback).where(Feedback.feedback_id == feedback_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[Feedback], int]:
        """获取用户反馈列表（分页）"""
        # 查询总数
        count_stmt = select(func.count()).select_from(Feedback).where(
            Feedback.user_id == user_id
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 查询分页数据
        offset = (page - 1) * page_size
        stmt = (
            select(Feedback)
            .where(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Feedback], int]:
        """获取所有反馈列表（管理员用，支持状态过滤）"""
        # 构建查询条件
        base_condition = []
        if status:
            base_condition.append(Feedback.status == status)

        # 查询总数
        count_stmt = select(func.count()).select_from(Feedback)
        if base_condition:
            count_stmt = count_stmt.where(*base_condition)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 查询分页数据
        offset = (page - 1) * page_size
        stmt = (
            select(Feedback)
            .order_by(Feedback.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        if base_condition:
            stmt = stmt.where(*base_condition)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def update(self, feedback: Feedback) -> Feedback:
        """更新反馈"""
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    async def update_reply(
        self,
        feedback: Feedback,
        admin_reply: str,
        replied_by: str,
        status: str = "replied",
    ) -> Feedback:
        """更新管理员回复"""
        feedback.admin_reply = admin_reply
        feedback.replied_by = replied_by
        feedback.replied_at = datetime.utcnow()
        feedback.status = status
        return await self.update(feedback)

    async def update_status(self, feedback: Feedback, status: str) -> Feedback:
        """更新反馈状态"""
        feedback.status = status
        return await self.update(feedback)

    async def count_by_user_id(self, user_id: str) -> int:
        """统计用户的反馈总数（用于判断是否首次反馈）"""
        stmt = select(func.count()).select_from(Feedback).where(
            Feedback.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
