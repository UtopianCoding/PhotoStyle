"""
模型交互记录数据访问层

封装交互记录的写入与按用户分页查询（支持技能 / 状态筛选）。
"""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.orm import defer

from app.models.conversation import ModelInteraction
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[ModelInteraction]):
    """模型交互记录仓储"""

    model = ModelInteraction

    def __init__(self, db) -> None:
        super().__init__(db)

    def _build_filter_stmt(self, stmt, user_id: str, skill_id: str | None, status: str | None):
        """构建带筛选条件的查询语句"""
        stmt = stmt.where(ModelInteraction.user_id == user_id)
        if skill_id:
            stmt = stmt.where(ModelInteraction.skill_id == skill_id)
        if status:
            stmt = stmt.where(ModelInteraction.status == status)
        return stmt

    async def list_and_count(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
        skill_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[ModelInteraction], int]:
        """
        同时获取分页列表和总数（并发查询，延迟加载大 TEXT 字段）。
        
        优化点：
        1. defer provider_response（最大字段，列表不需要）
        2. 两个查询并发执行，减少总等待时间
        """
        # 列表查询：defer 大 TEXT 字段
        list_stmt = select(ModelInteraction)
        list_stmt = self._build_filter_stmt(list_stmt, user_id, skill_id, status)
        list_stmt = list_stmt.order_by(ModelInteraction.created_at.desc())
        list_stmt = list_stmt.offset(offset).limit(limit)
        # 延迟加载 provider_response（通常最大，列表不需要）
        list_stmt = list_stmt.options(defer(ModelInteraction.provider_response))

        # 计数查询
        count_stmt = select(func.count()).select_from(ModelInteraction)
        count_stmt = self._build_filter_stmt(count_stmt, user_id, skill_id, status)

        # 并发执行两个查询
        list_result, count_result = await asyncio.gather(
            self.db.execute(list_stmt),
            self.db.execute(count_stmt),
        )

        records = list(list_result.scalars().all())
        total = int(count_result.scalar_one())
        return records, total

    async def get_by_interaction_id(
        self, interaction_id: str, user_id: str
    ) -> ModelInteraction | None:
        """根据对外交互ID获取记录，并校验归属"""
        stmt = select(ModelInteraction).where(
            ModelInteraction.interaction_id == interaction_id,
            ModelInteraction.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
