"""
风格转换任务与结果数据访问层

封装任务创建、状态更新、结果创建与历史查询等数据操作。
"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import Image
from app.models.style_result import StyleResult
from app.models.style_task import StyleTask
from app.models.user import User
from app.repositories.base import BaseRepository


class StyleRepository(BaseRepository[StyleTask]):
    """风格转换仓储（任务 + 结果）"""

    model = StyleTask

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    # -------------------- 任务 --------------------

    async def create_task(self, **kwargs) -> StyleTask:
        """创建任务"""
        task = StyleTask(**kwargs)
        return await self.create(task)

    async def get_task(self, task_id: str) -> StyleTask | None:
        """根据对外任务ID获取任务"""
        stmt = select(StyleTask).where(StyleTask.task_id == task_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tasks_by_user(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
        favorite: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[StyleTask]:
        """获取用户任务列表（按创建时间倒序）；favorite=True 时仅返回含收藏结果的任务"""
        if favorite:
            stmt = (
                select(StyleTask)
                .join(StyleResult, StyleResult.task_id == StyleTask.task_id)
                .where(StyleTask.user_id == user_id, StyleResult.favorite.is_(True))
                .distinct()
                .order_by(StyleTask.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        else:
            stmt = (
                select(StyleTask)
                .where(StyleTask.user_id == user_id)
                .order_by(StyleTask.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        stmt = self._apply_date_range(stmt, start_date, end_date)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_tasks_by_user(
        self,
        user_id: str,
        favorite: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """统计用户任务总数；favorite=True 时仅统计含收藏结果的任务"""
        from sqlalchemy import func

        if favorite:
            stmt = (
                select(func.count(func.distinct(StyleTask.task_id)))
                .select_from(StyleTask)
                .join(StyleResult, StyleResult.task_id == StyleTask.task_id)
                .where(StyleTask.user_id == user_id, StyleResult.favorite.is_(True))
            )
        else:
            stmt = select(func.count()).select_from(StyleTask).where(StyleTask.user_id == user_id)
        stmt = self._apply_date_range(stmt, start_date, end_date)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    @staticmethod
    def _apply_date_range(stmt, start_date: str | None, end_date: str | None):
        """按创建日期范围过滤任务（start_date/end_date 格式 YYYY-MM-DD，含当天）"""
        from datetime import datetime, timedelta

        if start_date:
            stmt = stmt.where(
                StyleTask.created_at >= datetime.fromisoformat(start_date)
            )
        if end_date:
            stmt = stmt.where(
                StyleTask.created_at < datetime.fromisoformat(end_date) + timedelta(days=1)
            )
        return stmt

    async def update_task_status(
        self,
        task_id: str,
        *,
        status: str | None = None,
        stage: str | None = None,
        progress: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        provider_task_id: str | None = None,
        started_at=None,
        completed_at=None,
    ) -> None:
        """更新任务状态（字段级更新，仅更新非 None 字段）

        自动时间戳填充（当调用方未显式传入时）：
        - 进入 running 时写入 started_at
        - 进入终态（success/failed/canceled）时写入 completed_at
        """
        now = datetime.utcnow()
        if status == "running" and started_at is None:
            started_at = now
        if status in ("success", "failed", "canceled") and completed_at is None:
            completed_at = now

        data: dict = {}
        if status is not None:
            data["status"] = status
        if stage is not None:
            data["stage"] = stage
        if progress is not None:
            data["progress"] = progress
        if error_code is not None:
            data["error_code"] = error_code
        if error_message is not None:
            data["error_message"] = error_message
        if provider_task_id is not None:
            data["provider_task_id"] = provider_task_id
        if started_at is not None:
            data["started_at"] = started_at
        if completed_at is not None:
            data["completed_at"] = completed_at
        if not data:
            return
        stmt = update(StyleTask).where(StyleTask.task_id == task_id).values(**data)
        await self.db.execute(stmt)
        await self.db.flush()

    # -------------------- 结果 --------------------

    async def create_result(self, **kwargs) -> StyleResult:
        """创建结果记录"""
        result = StyleResult(**kwargs)
        self.db.add(result)
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def update_result_urls(
        self, result_id: str, result_url: str, thumbnail_url: str | None = None,
    ) -> bool:
        """更新结果图的 URL（后台异步上传完成后，替换临时 URL 为永久 URL）"""
        data: dict = {"result_url": result_url}
        if thumbnail_url is not None:
            data["thumbnail_url"] = thumbnail_url
        stmt = update(StyleResult).where(StyleResult.result_id == result_id).values(**data)
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.rowcount > 0

    async def deduct_user_credits(self, user_id: str, amount: int = 1) -> bool:
        """
        扣减用户积分并累加今日用量。

        使用原子操作（UPDATE ... SET credits = credits - N, usage_today = usage_today + 1），
        避免并发场景下的竞态问题。

        Args:
            user_id: 用户 ID
            amount: 扣减积分数（默认 1）

        Returns:
            True if a row was updated, False otherwise
        """
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(
                credits=User.credits - amount,
                usage_today=User.usage_today + 1,
            )
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.rowcount > 0

    async def get_result(self, result_id: str) -> StyleResult | None:
        """根据对外结果ID获取结果"""
        stmt = select(StyleResult).where(StyleResult.result_id == result_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_results_by_task(self, task_id: str) -> list[StyleResult]:
        """获取任务下所有结果"""
        stmt = (
            select(StyleResult)
            .where(StyleResult.task_id == task_id)
            .order_by(StyleResult.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_results_by_tasks(self, task_ids: list[str]) -> dict[str, list[StyleResult]]:
        """
        批量获取多个任务的结果（一次 SQL 查询，消除 N+1）。

        Args:
            task_ids: 任务 ID 列表

        Returns:
            {task_id: [StyleResult, ...]} 按 task_id 分组的结果字典
        """
        if not task_ids:
            return {}
        stmt = (
            select(StyleResult)
            .where(StyleResult.task_id.in_(task_ids))
            .order_by(StyleResult.task_id, StyleResult.created_at.asc())
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        grouped: dict[str, list[StyleResult]] = {tid: [] for tid in task_ids}
        for row in rows:
            grouped.setdefault(row.task_id, []).append(row)
        return grouped

    async def get_history(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
        favorite: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[StyleTask]:
        """获取用户历史记录（任务列表）；favorite=True 时仅返回含收藏结果的任务"""
        return await self.get_tasks_by_user(
            user_id,
            offset=offset,
            limit=limit,
            favorite=favorite,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_favorites(
        self, user_id: str, offset: int = 0, limit: int = 20
    ) -> list[StyleResult]:
        """获取用户收藏列表"""
        stmt = (
            select(StyleResult)
            .where(StyleResult.user_id == user_id, StyleResult.favorite.is_(True))
            .order_by(StyleResult.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def toggle_favorite(self, result_id: str, favorite: bool | None = None) -> StyleResult | None:
        """切换收藏状态；favorite 为 None 时取反"""
        result = await self.get_result(result_id)
        if result is None:
            return None
        new_state = (not result.favorite) if favorite is None else favorite
        if result.favorite != new_state:
            result.favorite = new_state
            await self.db.flush()
        return result

    async def delete_result(self, result_id: str) -> bool:
        """删除单条结果"""
        result = await self.get_result(result_id)
        if result is None:
            return False
        await self.delete(result)
        return True

    async def delete_task_and_results(self, task_id: str) -> bool:
        """删除任务及其关联的所有结果"""
        task = await self.get_task(task_id)
        if task is None:
            return False
        results = await self.get_results_by_task(task_id)
        for r in results:
            await self.db.delete(r)
        await self.db.delete(task)
        await self.db.flush()
        return True

    async def batch_delete(self, result_ids: list[str]) -> int:
        """批量删除结果，返回删除条数"""
        if not result_ids:
            return 0
        stmt = select(StyleResult).where(StyleResult.result_id.in_(result_ids))
        result = await self.db.execute(stmt)
        deleted = 0
        for row in result.scalars().all():
            await self.db.delete(row)
            deleted += 1
        await self.db.flush()
        return deleted

    async def batch_delete_tasks(self, task_ids: list[str]) -> int:
        """批量删除任务及其关联结果，返回删除的任务条数"""
        if not task_ids:
            return 0
        stmt = select(StyleTask).where(StyleTask.task_id.in_(task_ids))
        result = await self.db.execute(stmt)
        tasks = list(result.scalars().all())
        deleted = 0
        for task in tasks:
            results = await self.get_results_by_task(task.task_id)
            for r in results:
                await self.db.delete(r)
            await self.db.delete(task)
            deleted += 1
        await self.db.flush()
        return deleted

    # -------------------- 图片（按 image_id 查询原图地址） --------------------

    async def get_images_map(self, image_ids: list[str]) -> dict[str, Image]:
        """批量根据 image_id 获取图片实体，返回 {image_id: Image}"""
        if not image_ids:
            return {}
        stmt = select(Image).where(Image.image_id.in_(image_ids))
        result = await self.db.execute(stmt)
        return {img.image_id: img for img in result.scalars().all()}

    async def get_image(self, image_id: str) -> Image | None:
        """根据 image_id 获取图片实体"""
        stmt = select(Image).where(Image.image_id == image_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
